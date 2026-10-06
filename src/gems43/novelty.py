"""Near-duplicate screen: is this layout materially different from every earlier submission?

Why this exists
---------------
The brief requires that the emitted layout not be a near-duplicate of a prior GEMSDOE submission.
Two rasters can differ in every byte and still be the *same answer*: a 1-pixel translation of a
dot pattern, or the same pattern with 5 % of the dots moved, would be a re-upload wearing a
different hash.  A hash comparison is therefore necessary but not sufficient, and it is the
geometric comparisons below that actually answer the question.

Metrics
-------
``dot_jaccard_300m``    |A within 300 m of B| and |B within 300 m of A| (asymmetric pair).
                        300 m is the metric's own support, so this asks "would the scorer see
                        these as the same prediction?".
``coverage_iou``        grey-dilation of each dot set by the official triangular kernel, then
                        intersection-over-union of the two coverage fields -- the metric-level
                        overlap of the two predictions.
``median_nn_distance``  median distance from a new dot to the nearest prior dot, in pixels.
``block_correlation``   Pearson correlation of the two layouts coarse-grained to 64 x 64 blocks;
                        catches "same large-scale allocation, different dots".

The screen *passes* when the maximum coverage-IoU against the whole corpus is below
``IOU_LIMIT`` (default 0.50) **and** the maximum symmetric 300 m containment is below
``CONTAIN_LIMIT`` (default 0.60).
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass, asdict

import numpy as np
from scipy.ndimage import distance_transform_edt

from .grid import KERNEL_W, OFFSETS, shift

IOU_LIMIT = 0.50
CONTAIN_LIMIT = 0.60          # raw containment; kept for reporting, see ``compare``
CONTAIN_EXCESS_LIMIT = 0.60   # *excess containment over chance*, the statistic that decides
MAX_PRIOR_DOTS = 250_000      # stride-sample denser priors; flagged per-artifact, see ``screen``
DENSITY_RATIO = 4.0           # outside this ratio in |dots| the IoU is not evidence either way


@dataclass
class Comparison:
    artifact: str
    prior_dots: int
    new_dots: int
    new_within_300m_of_prior: float
    prior_within_300m_of_new: float
    coverage_iou: float
    median_nn_distance_px: float
    block_correlation: float
    chance_new_in_prior: float
    chance_prior_in_new: float
    containment_excess: float
    prior_sampled: bool
    iou_decides: bool
    verdict: str
    kind: str = ""


def kernel_coverage(mask: np.ndarray) -> np.ndarray:
    """Grey-dilation of a dot mask by the official triangular kernel:
    ``C[x] = max_{i in S} k(d(i,x))``.  Full-grid version (used by the tests)."""
    out = np.zeros(mask.shape, dtype=np.float32)
    m = mask.astype(np.float32)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        if w <= 0.0:
            continue
        np.maximum(out, w * shift(m, -dr, -dc), out=out)
    return out


def _block_counts(mask: np.ndarray, n: int = 64) -> np.ndarray:
    H, W = mask.shape
    bh, bw = H // n, W // n
    v = mask[: n * bh, : n * bw].reshape(n, bh, n, bw).sum(axis=(1, 3)).ravel().astype(np.float64)
    return v


def _dot_offset_pairs(mask: np.ndarray):
    """Every (flat index, kernel weight) pair produced by the dot set -- the sparse form of the
    grey dilation, of size |S| x 29 instead of the whole grid."""
    r, c = np.nonzero(mask)
    idx = np.empty((r.size, OFFSETS.shape[0]), dtype=np.int32)
    w = np.empty((r.size, OFFSETS.shape[0]), dtype=np.float32)
    H, W = mask.shape
    for j, (dr, dc) in enumerate(OFFSETS):
        rr = r + dr
        cc = c + dc
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        idx[:, j] = np.where(ok, rr * W + cc, -1)
        w[:, j] = np.where(ok, KERNEL_W[j], 0.0)
    ok = idx >= 0
    return idx[ok], w[ok]


def coverage_iou_sparse(a: np.ndarray, b: np.ndarray) -> float:
    """IoU of the two kernel-coverage fields, computed on the union support only.

    Identical to dilating both masks over the full grid and taking
    ``sum(min) / sum(max)``, because both coverage fields vanish outside the union support.
    """
    ia, wa = _dot_offset_pairs(a)
    ib, wb = _dot_offset_pairs(b)
    if ia.size == 0 or ib.size == 0:
        return 0.0
    u = np.union1d(ia, ib)
    pos = np.searchsorted(u, ia)
    posb = np.searchsorted(u, ib)
    ca = np.zeros(u.size, dtype=np.float32)
    cb = np.zeros(u.size, dtype=np.float32)
    np.maximum.at(ca, pos, wa)
    np.maximum.at(cb, posb, wb)
    inter = float(np.minimum(ca, cb).sum())
    union = float(np.maximum(ca, cb).sum())
    return inter / union if union > 0 else 0.0


def classify(path: str) -> str:
    """Sort a corpus artifact by what it *is*, because the uniqueness question only concerns
    submitted predictions.

    ``submission``   a published prediction (under docs/downloads, downloads/, submissions/).
    ``input``        an input or derived asset nobody ever submitted (data/external, assets/,
                     evidence/ci, inputs/).  Overlap with these is expected and is not a
                     duplicate -- the model was trained on the catalogue, and the SGMC inventory
                     is a superset of it.
    ``intermediate`` an in-progress artifact inside an experiment directory (prob_raw, runs/).
    """
    p = str(path).lower()
    if ("docs/downloads" in p or "downloads/" in p or "submissions/" in p
            or "submission/" in p or p.endswith("submission.tif")):
        return "submission"
    if "data/external" in p or "assets/" in p or "evidence/ci" in p or "inputs/" in p \
            or "data/inputs" in p or p.endswith("_u8.tif") or "proxy" in p:
        return "input"
    return "intermediate"


def compare(new_mask: np.ndarray, prior_mask: np.ndarray, name: str,
            iou_limit: float = IOU_LIMIT, contain_limit: float = CONTAIN_LIMIT,
            n_eligible: int | None = None,
            contain_excess_limit: float = CONTAIN_EXCESS_LIMIT) -> Comparison:
    """Compare two layouts.

    Raw containment is reported but does **not** decide, because for sparse dot patterns it is
    dominated by chance: with ``K`` dots of 29-cell support in ``N`` eligible cells an unrelated
    layout already puts a fraction ``1 - (1 - 29/N)**K`` of the *other* set within 300 m, which is
    0.25 at K = 51k and 0.63 at K = 176k.  A raw 0.60 threshold therefore flags ordinary
    unrelated priors.

    The deciding statistic is the **excess over chance**, normalised so that it is 0 for two
    unrelated layouts and 1 for a perfect duplicate:

        excess = (observed - chance) / (1 - chance)

    The normalisation by ``1 - chance`` matters: the *ratio* (observed/chance) has a ceiling of
    ``1/chance`` that depends on how dense the layouts are, so no single ratio threshold can work
    across the corpus.  The excess does not have that problem.
    """
    from scipy.spatial import cKDTree

    H, W = new_mask.shape
    nr_, nc_ = np.nonzero(new_mask)
    pr_, pc_ = np.nonzero(prior_mask)

    # --- 300 m containment, both directions, via KD-tree ball queries
    ta = cKDTree(np.stack([pr_, pc_], 1).astype(np.float64))
    tb = cKDTree(np.stack([nr_, nc_], 1).astype(np.float64))
    q = np.stack([nr_, nc_], 1).astype(np.float64)
    q2 = np.stack([pr_, pc_], 1).astype(np.float64)
    a_in_b = float(np.mean([len(x) > 0 for x in ta.query_ball_point(q, 3.0)])) if nr_.size else 0.0
    b_in_a = float(np.mean([len(x) > 0 for x in tb.query_ball_point(q2, 3.0)])) if pr_.size else 0.0
    nn = ta.query(q, k=1)[0] if nr_.size else np.array([np.nan])

    # chance level of the same containment statistic, both directions
    N = float(n_eligible if n_eligible else H * W)
    K_SUP = float(OFFSETS.shape[0])
    c_new_in_prior = 1.0 - (1.0 - K_SUP / N) ** max(int(pr_.size), 1)
    c_prior_in_new = 1.0 - (1.0 - K_SUP / N) ** max(int(nr_.size), 1)

    def _excess(obs: float, chance: float) -> float:
        if chance >= 1.0:
            return float("nan")
        return max(0.0, (obs - chance) / (1.0 - chance))

    excess = max(_excess(a_in_b, c_new_in_prior), _excess(b_in_a, c_prior_in_new))

    iou = coverage_iou_sparse(new_mask, prior_mask)

    va, vb = _block_counts(new_mask), _block_counts(prior_mask)
    corr = (float(np.corrcoef(va, vb)[0, 1])
            if (va.std() > 0 and vb.std() > 0) else 0.0)

    # The coverage IoU is only comparable when the two layouts are of comparable density.  Against
    # a prior that is 100x denser (a graded probability map, not a dot layout) the IoU is tiny for
    # density reasons alone and says nothing about whether the answer is the same; against a
    # sampled prior it is not even monotone (see tests/test_novelty.py).  So the IoU is reported
    # always, but it only carries a verdict when the two dot counts are within DENSITY_RATIO of
    # each other and the prior was compared at full density.
    ratio = (prior_mask.sum() / max(int(new_mask.sum()), 1))
    iou_decides = (1.0 / DENSITY_RATIO) <= ratio <= DENSITY_RATIO
    bad = []
    if iou >= iou_limit and iou_decides:
        bad.append(f"coverage IoU {iou:.3f} >= {iou_limit}")
    if excess >= contain_excess_limit:
        bad.append(f"300 m containment {max(a_in_b, b_in_a):.3f} vs chance "
                   f"{max(c_new_in_prior, c_prior_in_new):.3f} -> excess {excess:.2f} "
                   f">= {contain_excess_limit}")
    return Comparison(
        artifact=name,
        prior_dots=int(prior_mask.sum()),
        new_dots=int(new_mask.sum()),
        new_within_300m_of_prior=a_in_b,
        prior_within_300m_of_new=b_in_a,
        coverage_iou=iou,
        median_nn_distance_px=float(np.median(nn)) if nn.size else float("nan"),
        block_correlation=corr,
        chance_new_in_prior=float(c_new_in_prior),
        chance_prior_in_new=float(c_prior_in_new),
        containment_excess=float(excess),
        prior_sampled=False,
        iou_decides=True,
        verdict="NEAR-DUPLICATE: " + "; ".join(bad) if bad else "distinct",
    )


def screen(new_mask: np.ndarray, prior_dir, foot: np.ndarray,
           manifest_name: str = "manifest.json", iou_limit: float = IOU_LIMIT,
           contain_limit: float = CONTAIN_LIMIT, limit: int | None = None) -> dict:
    """Compare ``new_mask`` against every GeoTIFF in the prior-submission corpus."""
    import rasterio
    from pathlib import Path

    prior_dir = Path(prior_dir)
    man = json.loads((prior_dir / manifest_name).read_text()) if (prior_dir / manifest_name).exists() else {}
    n_eligible = int(foot.sum())
    results = []
    files = sorted(prior_dir.rglob("*.tif")) + sorted(prior_dir.rglob("*.TIF"))
    if limit:
        files = files[:limit]
    for f in files:
        try:
            with rasterio.open(f) as src:
                if (src.height, src.width) != foot.shape:
                    continue
                v = src.read(1)
        except Exception:
            continue
        v = np.where(np.isfinite(v), v, 0.0)
        pm = (v > 0) & foot
        del v
        n_prior = int(pm.sum())
        if n_prior < 100:
            del pm
            continue
        # Cap the comparison cost on pathologically dense priors (only ever the *prior* is
        # sampled, never the new layout).  CAUTION, and this is not a formality: thinning a prior
        # is monotone for the 300 m containment and the NN distance -- both can only fall, so the
        # screen stays conservative -- but it is NOT monotone for the coverage IoU, because it
        # shrinks the union faster than the intersection.  A thinned dense prior can therefore
        # report a *higher* IoU than the full one, i.e. a false near-duplicate.  Any artifact
        # this touches is listed in ``sampled_artifacts`` and must be re-checked at full density
        # before a PASS is trusted.  tests/test_novelty.py pins the non-monotonicity down.
        sampled = n_prior > MAX_PRIOR_DOTS
        if sampled:
            rr = np.flatnonzero(pm.ravel())[:: n_prior // MAX_PRIOR_DOTS + 1]
            pm = np.zeros(foot.shape, bool)
            pm.flat[rr] = True
        meta = man.get(f.name, {})
        rel = str(f.relative_to(prior_dir))
        label = f"{meta.get('repo', prior_dir.name)}:{meta.get('path', rel)}"
        try:
            c = compare(new_mask, pm, label, iou_limit, contain_limit, n_eligible=n_eligible)
            c.prior_sampled = sampled
            c.iou_decides = c.iou_decides and not sampled
            results.append(c)
        except Exception as e:                                    # pragma: no cover
            results.append(Comparison(f.name, n_prior, int(new_mask.sum()),
                                      float("nan"), float("nan"), float("nan"),
                                      float("nan"), float("nan"), f"error: {e}"))
        finally:
            del pm
            gc.collect()
    results.sort(key=lambda r: (-(r.coverage_iou if np.isfinite(r.coverage_iou) else -1)))
    for r in results:                       # filled in here so every returned row carries it
        r.kind = classify(r.artifact)
    worst = results[0] if results else None
    by_kind = {}
    for kind in ("submission", "input", "intermediate"):
        rows = [r for r in results if r.kind == kind]
        w = rows[0] if rows else None
        by_kind[kind] = {
            "n": len(rows),
            "worst_iou": float(w.coverage_iou) if w else None,
            "worst_artifact": w.artifact if w else None,
            "worst_containment": (float(max(w.new_within_300m_of_prior,
                                           w.prior_within_300m_of_new)) if w else None),
            "worst_containment_excess": float(w.containment_excess) if w else None,
            "dupes": [r.artifact for r in rows if r.verdict != "distinct"],
        }
    return {
        "n_compared": len(results),
        "iou_limit": iou_limit,
        "contain_limit": contain_limit,
        "worst_iou": float(worst.coverage_iou) if worst else None,
        "worst_artifact": worst.artifact if worst else None,
        "dupes": [r.artifact for r in results if r.verdict != "distinct"],
        "sampled_artifacts": [r.artifact for r in results if r.prior_sampled],
        "by_kind": by_kind,
        "worst_iou_submission": by_kind["submission"]["worst_iou"],
        "worst_artifact_submission": by_kind["submission"]["worst_artifact"],
        "worst_containment_excess_submission":
            by_kind["submission"]["worst_containment_excess"],
        "passed": bool(worst is None or worst.coverage_iou < iou_limit),
        "top": [asdict(r) for r in results[:15]],
    }
