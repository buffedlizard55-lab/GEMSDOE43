"""Prior (demand) surfaces pi(x) -- the "where would an expert draw a new fault?" field.

All surfaces are **label-free with respect to the hidden test set**: the supervised one is trained
only on the published catalogue and is always produced out-of-fold for validation, and every
other surface is a physical transform of the official bands plus public external inventories.

Every surface is returned as a float32 field on the frozen grid with

    sum_x pi(x) = n_truth_hat

the assumed number of hidden truth pixels.  That normalisation is what puts the MCLP marginal
gains on the metric's own scale, so the "emit while marginal credit > 0.2*s" rule is meaningful
rather than a tuned threshold (see ``gems43.mclp.emission_plan``).
"""

from __future__ import annotations

import json

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from . import bands, paths

F32 = np.float32


# --------------------------------------------------------------------------------------
# channel stack access
# --------------------------------------------------------------------------------------
def load_channels():
    meta = json.loads((paths.registry_dir() / "channels.json").read_text())
    arr = np.load(paths.work_dir() / "channels.u8.npy", mmap_mode="r")
    names = [c["name"] for c in meta["channels"]]
    return arr, names, meta


def channel_index(names, name: str) -> int:
    return names.index(name)


def as_float(ch_u8: np.ndarray) -> np.ndarray:
    return ch_u8.astype(F32) / 255.0


# --------------------------------------------------------------------------------------
# candidate mask
# --------------------------------------------------------------------------------------
def candidate_mask(foot, catalogue, buffer_px: float = 0.0, dcat=None) -> np.ndarray:
    """Pixels eligible to host a dot.

    Known USGS/INGENIOUS pixels are **removed from evaluation** (DrivenData staff, community
    thread 11516), so a dot placed on one contributes nothing to any metric term.  ``buffer_px``
    additionally clears a flank around the catalogue: the parent project's best artifact
    (``H33-2-B2``) used a 2-pixel flank, but here the flank is a *reported parameter of the
    emitted file*, not a tuned spacing constant, and the covering solver decides how many dots
    to place inside the surviving area.
    """
    from scipy.ndimage import distance_transform_edt

    m = foot & ~catalogue
    if buffer_px and buffer_px > 0:
        if dcat is None:
            dcat = distance_transform_edt(~catalogue).astype(F32)
        m &= dcat > buffer_px
    return m


# --------------------------------------------------------------------------------------
# supervised surface
# --------------------------------------------------------------------------------------
def _sample_pixels(foot, catalogue, n_neg: int, seed: int, block=None):
    """Balanced pixel sample: all catalogue positives in ``block`` plus random negatives."""
    rng = np.random.default_rng(seed)
    pos_mask = catalogue & (foot if block is None else (catalogue & block))
    pr, pc = np.nonzero(pos_mask)
    neg_pool = np.flatnonzero((foot & ~catalogue).ravel())
    if block is not None:
        neg_pool = np.flatnonzero((foot & ~catalogue & block).ravel())
    neg = rng.choice(neg_pool, size=min(n_neg, neg_pool.size), replace=False)
    nr, nc = np.unravel_index(neg, foot.shape)
    rows = np.concatenate([pr, nr])
    cols = np.concatenate([pc, nc])
    y = np.concatenate([np.ones(pr.size, np.uint8), np.zeros(nr.size, np.uint8)])
    return rows.astype(np.int64), cols.astype(np.int64), y


def supervised_surface(ch, foot, catalogue, *, rows=None, cols=None, y=None,
                       n_neg: int = 400_000, seed: int = 0, block=None,
                       max_iter: int = 250, learning_rate: float = 0.08,
                       exclude_names=(), verbose: bool = True):
    """HistGradientBoosting fault-probability surface.

    ``rows/cols/y`` override the internal sampling (used for out-of-fold training).  Returns
    ``(probability surface, fitted model, feature names used)``.
    """
    names_all = None
    if rows is None:
        rows, cols, y = _sample_pixels(foot, catalogue, n_neg, seed, block)
    C = ch.shape[0]
    X = np.empty((rows.size, C), dtype=F32)
    step = 200_000
    for a in range(0, rows.size, step):
        b = min(a + step, rows.size)
        blk = ch[:, rows[a:b], cols[a:b]]           # (C, n)
        X[a:b] = (blk.T.astype(F32) / 255.0)
    if exclude_names:
        raise ValueError("exclude_names requires the name list; handled by the caller")

    clf = HistGradientBoostingClassifier(
        max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=31,
        min_samples_leaf=40, l2_regularization=1.0, max_bins=255,
        early_stopping=False, random_state=seed,
    )
    if verbose:
        print(f"  [surface] HGB on {X.shape[0]:,} rows x {X.shape[1]} channels", flush=True)
    clf.fit(X, y)
    del X

    out = np.zeros(foot.shape, dtype=F32)
    H = foot.shape[0]
    step = 128
    for r0 in range(0, H, step):
        r1 = min(r0 + step, H)
        rows_f = np.flatnonzero(foot[r0:r1].ravel())
        if rows_f.size == 0:
            continue
        rr, cc = np.unravel_index(rows_f, (r1 - r0, foot.shape[1]))
        blk = ch[:, r0 + rr, cc].T.astype(F32) / 255.0
        out[r0 + rr, cc] = clf.predict_proba(blk)[:, 1].astype(F32)
    out[~foot] = 0.0
    return out, clf


# --------------------------------------------------------------------------------------
# label-free surfaces
# --------------------------------------------------------------------------------------
def labelfree_surfaces(ch, names, foot) -> dict[str, np.ndarray]:
    """Physical prior surfaces, each built only from named channels + public inventories."""
    def g(n):
        return as_float(ch[channel_index(names, n)])

    out: dict[str, np.ndarray] = {}

    def has(*ns):
        return all(n in names for n in ns)

    if has("h431_multi_physics_fused"):
        v = g("h431_multi_physics_fused")
        out["lf_h431_multiphysics"] = v * v            # sharpen: agreement is already the gate
    if has("line_mag", "line_rtp", "line_tilt", "h431_orient_order"):
        lines = np.max(np.stack([g("line_mag"), g("line_rtp"), g("line_tilt"),
                                 g("line_grav"), g("line_elev")]), axis=0)
        out["lf_line_agreement"] = lines * g("h431_orient_order")
    if has("h432_concealed_coincidence"):
        out["lf_h432_concealed"] = g("h432_concealed_coincidence") ** 1.5
    if has("h432_coincidence"):
        out["lf_h432_subsurface"] = g("h432_coincidence")
    if has("h431_asa_ridge"):
        out["lf_h431_mag_edge"] = g("h431_asa_ridge") * g("h431_tilt_grad")
    if has("h435_grav_tilt_depth", "h435_grav_analytic_signal"):
        out["lf_h435_gravity"] = g("h435_grav_analytic_signal") * g("line_grav")
    if has("h434_spring_lines", "h434_spring_density"):
        out["lf_h434_fluids"] = np.sqrt(g("h434_spring_lines") * g("h434_spring_density"))
    if has("ext_sgmc_prox"):
        out["lf_ext_sgmc"] = g("ext_sgmc_prox")

    # a physics-and-evidence fusion: what the structural transforms agree on, sharpened by
    # the independent fault inventory and by hydrothermal fluid evidence
    parts = [out[k] for k in ("lf_line_agreement", "lf_h432_subsurface") if k in out]
    if parts:
        fused = np.ones(foot.shape, dtype=F32)
        for p in parts:
            fused = fused * np.sqrt(np.maximum(p, 0.0))
        if "lf_ext_sgmc" in out:
            fused = fused * (0.35 + 0.65 * out["lf_ext_sgmc"])
        if "lf_h434_fluids" in out:
            fused = fused * (0.45 + 0.55 * np.sqrt(np.maximum(out["lf_h434_fluids"], 0.0)))
        out["lf_fused"] = fused

    for k in list(out):
        out[k] = np.where(foot, np.nan_to_num(out[k], nan=0.0, posinf=0.0, neginf=0.0),
                          0.0).astype(F32)
    return out


# --------------------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------------------
def normalise_to_mass(prior, foot, mass: float, floor: float = 0.0,
                      power: float = 1.0) -> np.ndarray:
    """Rescale a non-negative score field so that ``sum(pi) == mass`` inside the footprint.

    ``power`` sharpens or flattens the field *before* normalisation; it changes the *shape* of
    the demand, so it is a reported modelling choice, not a free constant of the emission.
    """
    a = np.where(foot, np.maximum(np.asarray(prior, dtype=np.float64), 0.0), 0.0)
    if power != 1.0:
        a = a ** power
    if floor > 0:
        a = a + floor * (a > 0)
    s = a.sum()
    if s <= 0:
        raise ValueError("prior has no mass inside the footprint")
    return ((a / s) * float(mass)).astype(F32)


def blend(surfaces: dict[str, np.ndarray], weights: dict[str, float], foot) -> np.ndarray:
    """Weighted geometric mean of named surfaces (exponents sum is irrelevant after normalising)."""
    acc = np.ones(foot.shape, dtype=np.float64)
    tw = sum(abs(w) for w in weights.values())
    if tw == 0:
        raise ValueError("all blend weights are zero")
    for k, w in weights.items():
        if w == 0:
            continue
        v = np.maximum(np.asarray(surfaces[k], dtype=np.float64), 1e-9)
        acc = acc * v ** (w / tw)
    return np.where(foot, acc, 0.0).astype(F32)
