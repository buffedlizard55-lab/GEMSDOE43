"""The channel stack: one entry per named physical transform, grouped by hypothesis.

Channel provenance is written to ``registry/channels.json`` every time the stack is built, so the
site can show exactly which band produced which channel and which hypothesis it belongs to.

Hypothesis map (full write-up in ``docs/research/h43-hypotheses.md``):

``H43-1``  Magnetic source-edge lineaments.  The organizer supplies ``tc`` (band 6) -- literally
           "tilt angle ... magnetic field derivative for edge detection" -- and nobody in the
           GEMSDOE lineage has derived anything from it: GEMSDOE32's own audit records bands
           **6, 9, 10 and 16** as having no derived transform at all.  Here it is combined with
           the **analytic signal amplitude** ``sqrt(tmi_hg^2 + tmi_vg^2)`` (Nabighian 1972;
           Roest, Verhoef & Pilkington 1992), whose peaks locate magnetic contacts *independently
           of the magnetization direction* -- the standard tool for contacts hidden under cover.
``H43-2``  Concealed basin-bounding faults.  Three-way coincidence of a basement-depth step, a
           conductivity step and a geodetic shear-rate ridge, multiplied by a **concealment gate**
           that asks where a surface mapper would be blind.
``H43-3``  Seismicity residual.  GEMSDOE32 measured ``ieq`` as 0.9935 self-correlated at 3 km lag,
           i.e. useless at the metric's 300 m scale; a large-scale high-pass is the only way any
           fault-scale information can survive.
``H43-4``  Geothermal-fluid conduit alignment.  Thermal springs in the GDR inventory sit a median
           2.4 km from the nearest mapped fault.  Used here as **orientation evidence**: a Hough
           accumulator over the discrete point pattern infers conduit strike, which a proximity
           decay cannot express.
``H43-5``  Gravity source-parameter imaging.  Tilt-depth (Salem et al. 2007) from the analytic
           signal of the isostatic anomaly gives depth-to-density-contrast; its ridges mark
           fault-bounded blocks under basin fill.
"""

from __future__ import annotations

import gc
import json
import math

import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter

from . import bands, features as F, paths

F32 = np.float32

# which official band feeds each line-detector hypothesis, and at what scales
_LINE_PHYSICS = {
    "mag": ("tmi", (1.2, 2.5)),
    "rtp": ("rtp", (1.2, 2.5)),
    "tilt": ("tc", (1.2, 2.5)),
    "grav": ("iso_grav_anom", (1.5, 3.0)),
    "elev": ("det_elev", (1.2, 2.5)),
    "cond": ("cond_surf", (1.5, 3.0)),
    "base": ("depth_to_base_surf", (1.5, 3.0)),
    "shear": ("geod_shearrate", (2.0, 4.0)),
}


class Stack:
    """Accumulates named channels on the frozen grid, spilling them straight to a disk memmap.

    The full stack is ~50 x 3730 x 3292 bytes, far too large to hold in RAM alongside the 19
    float32 source bands on this machine, so channels are quantised to uint8 and written out as
    they are produced.
    """

    MAX_C = 80

    def __init__(self, foot: np.ndarray):
        self.foot = foot
        self.names: list[str] = []
        self.hyp: dict[str, str] = {}
        self.notes: dict[str, str] = {}
        self._mm = np.lib.format.open_memmap(
            paths.work_dir() / "_channels_u8.npy", mode="w+",
            dtype=np.uint8, shape=(self.MAX_C, *foot.shape))
        paths.work_dir().mkdir(parents=True, exist_ok=True)

    def add(self, name: str, arr, hyp: str = "base", note: str = "") -> None:
        a = np.asarray(arr, dtype=np.float64)
        u = np.zeros(a.shape, dtype=np.uint8)
        v = a[self.foot]
        v = v[np.isfinite(v)]
        if v.size and np.isfinite(v).any():
            lo = float(np.percentile(v, 0.5))
            hi = float(np.percentile(v, 99.5))
            if hi <= lo:
                hi = lo + 1e-9
            u = np.round(np.clip((a - lo) / (hi - lo), 0.0, 1.0) * 255.0).astype(np.uint8)
        u[~self.foot] = 0
        i = len(self.names)
        if i >= self.MAX_C:
            raise RuntimeError(f"channel overflow: raise Stack.MAX_C (currently {self.MAX_C})")
        self._mm[i] = u
        self.names.append(name)
        self.hyp[name] = hyp
        self.notes[name] = note

    def as_array(self) -> np.ndarray:
        return np.asarray(self._mm[: len(self.names)])

    def save(self, stem: str = "channels") -> dict:
        out = paths.work_dir() / f"{stem}.u8.npy"
        arr = self.as_array().astype(np.uint8)
        np.save(out, arr)
        meta = {
            "file": str(out),
            "shape": list(arr.shape),
            "dtype": "uint8",
            "channels": [
                {"index": i + 1, "name": n, "hypothesis": self.hyp[n], "note": self.notes[n]}
                for i, n in enumerate(self.names)
            ],
        }
        paths.registry_dir().mkdir(parents=True, exist_ok=True)
        (paths.registry_dir() / "channels.json").write_text(json.dumps(meta, indent=1))
        return meta


def _point_density(rows, cols, foot, weights=None, sigma_px: float = 1.0):
    d = np.zeros(foot.shape, dtype=F32)
    w = np.ones(len(rows), dtype=F32) if weights is None else np.asarray(weights, dtype=F32)
    np.add.at(d, (rows, cols), w)
    return F.gsmooth(d, sigma_px)


def point_alignment_lineaments(rows, cols, weights, shape, r_max: float = 25.0,
                               min_pts: int = 3, elong_min: float = 0.75,
                               extend: float = 12.0, sigma_px: float = 1.4):
    """Locality-constrained lineament inference from a discrete point pattern.

    A global Hough accumulator over ~2,000 springs is dominated by *chance* collinearity: with
    72 orientation bins the expected number of accidental triples exceeds the real ones by orders
    of magnitude, which is why this routine constrains each fit to a neighbourhood of radius
    ``r_max`` (a fault segment is a *local* object) before running a weighted PCA.

    For every point whose ``r_max``-neighbourhood contains at least ``min_pts`` features:

    * weighted PCA gives the principal axis and the elongation ``1 - l2/l1``;
    * neighbourhoods with elongation below ``elong_min`` are isotropic clusters (a geothermal
      *field*, not a conduit) and are rejected;
    * the accepted axis is painted as a Gaussian-cross-section segment, extended by ``extend``
      pixels beyond the data along strike -- the along-strike extrapolation is exactly the
      information an isotropic proximity decay cannot carry.
    """
    from scipy.spatial import cKDTree

    H, W = shape
    pts = np.stack([np.asarray(rows, dtype=np.float64), np.asarray(cols, dtype=np.float64)], 1)
    w = np.asarray(weights, dtype=np.float64).copy()
    w[~np.isfinite(w)] = 0.3
    w = np.clip(w, 0.02, 5.0)
    if pts.shape[0] < min_pts:
        return np.zeros((H, W), dtype=np.float32)

    tree = cKDTree(pts)
    nbrs = tree.query_ball_point(pts, r_max)
    out = np.zeros((H, W), dtype=np.float32)
    ys = np.arange(H, dtype=np.float64)
    xs = np.arange(W, dtype=np.float64)

    for i, nb in enumerate(nbrs):
        nb = np.asarray(nb, dtype=int)
        if nb.size < min_pts:
            continue
        p = pts[nb]
        ww = w[nb]
        sw = ww.sum()
        mu = (p * ww[:, None]).sum(0) / sw
        q = p - mu
        cov = (q * ww[:, None]).T @ q / sw
        evals, evecs = np.linalg.eigh(cov)
        l1, l2 = float(evals[1]), float(evals[0])
        if l1 <= 1e-9:
            continue
        elong = 1.0 - l2 / l1
        if elong < elong_min:
            continue
        axis = evecs[:, 1]                                   # principal (along-strike) direction
        proj = q @ axis
        half = float(np.abs(proj).max()) + float(extend)
        strength = float(elong * sw)

        t = np.arange(-half, half + 0.5, 0.5, dtype=np.float64)
        cy = mu[0] + axis[0] * t
        cx = mu[1] + axis[1] * t
        keep = (cy >= -3) & (cy < H + 3) & (cx >= -3) & (cx < W + 3)
        cy, cx = cy[keep], cx[keep]
        if cy.size == 0:
            continue
        # Gaussian cross-section of half-width 3*sigma around the painted centre line
        span = int(np.ceil(3 * sigma_px))
        for oy in range(-span, span + 1):
            for ox in range(-span, span + 1):
                yi = np.rint(cy).astype(int) + oy
                xi = np.rint(cx).astype(int) + ox
                m = (yi >= 0) & (yi < H) & (xi >= 0) & (xi < W)
                if not m.any():
                    continue
                dy = yi[m] - cy[m]
                dx = xi[m] - cx[m]
                g = np.exp(-(dy * dy + dx * dx) / (2.0 * sigma_px ** 2))
                np.add.at(out, (yi[m], xi[m]), (strength * g).astype(np.float32))
    return out


def build(foot: np.ndarray, catalogue: np.ndarray, verbose: bool = True) -> Stack:
    """Build the full channel stack.  Returns the ``Stack`` (uint8 channels + provenance)."""
    st = Stack(foot)
    B = {n: bands.band(n) for n in
         ["mag_anom", "rtp", "tmi", "tmi_hg", "tmi_vg", "tc", "iso_grav_anom",
          "iso_grav_anom_hg", "iso_grav_anom_vg", "iso_grav_anom_slope", "det_elev",
          "det_elev_slope", "cond_surf", "depth_to_base_surf", "geod_2ndinv",
          "geod_shearrate", "geod_dilaterate", "ieq_n100a15", "deq_n100a15"]}

    def log(m):
        if verbose:
            print(f"  [channels] {m}", flush=True)

    # ---------------------------------------------------------------- raw official bands
    for n, a in B.items():
        st.add(f"raw_{n}", a, "base", f"official band {n!r}, sentinel-filled, robust 0.5/99.5 pct")

    # ---------------------------------------------------------------- H43-1  magnetic edges
    log("H43-1 magnetic source-edge lineaments")
    asa = np.sqrt(B["tmi_hg"].astype(np.float64) ** 2 + B["tmi_vg"].astype(np.float64) ** 2)
    st.add("h431_analytic_signal", F.robust_norm(asa.astype(F32), foot), "H43-1",
           "sqrt(tmi_hg^2 + tmi_vg^2): contact locator independent of magnetization direction")
    st.add("h431_asa_ridge", F.nms_ridge(F.robust_norm(asa.astype(F32), foot)), "H43-1",
           "non-max-suppressed ridge of the analytic signal amplitude")
    tc64 = B["tc"].astype(np.float64)
    st.add("h431_tilt_grad", F.robust_norm(F.grad_mag(B["tc"], 1.0), foot), "H43-1",
           "|grad tc|: the horizontal gradient of the tilt angle peaks over source edges")
    st.add("h431_tilt_zero_band", np.exp(-np.abs(tc64) / 0.15), "H43-1",
           "narrow band around the tilt-angle zero contour, which outlines the source body")
    st.add("h431_tilt_abs", np.abs(tc64), "H43-1", "|tc|: total-curvature / tilt magnitude")

    # ---------------------------------------------------------------- multi-scale lineaments
    log("multi-scale Frangi line responses")
    line_v, line_th = {}, {}
    for key, (bn, sigmas) in _LINE_PHYSICS.items():
        v = np.zeros(foot.shape, dtype=F32)
        th = np.zeros(foot.shape, dtype=F32)
        z = F.zscore_robust(B[bn], foot)          # unit robust scale -> Frangi's c is meaningful
        for s in sigmas:
            Hxx, Hyy, Hxy = F.hessian(z, s)
            vv, tt, _ = F.frangi(Hxx, Hyy, Hxy, polarity="both")
            vv = F.robust_norm(vv, foot)
            m = vv > v
            v = np.where(m, vv, v)
            th = np.where(m, tt, th)
        line_v[key] = v
        line_th[key] = th
        st.add(f"line_{key}", v, "H43-1" if key in ("mag", "rtp", "tilt") else
               ("H43-2" if key in ("cond", "base", "shear") else
                ("H43-5" if key == "grav" else "base")),
               f"Frangi vesselness (both polarities) of {bn} at sigma={sigmas}, 0.5/99.5 pct")

    # ------------------------------------------- orientation agreement across physics (H43-1)
    log("multi-physics orientation order parameter")
    keys = ["mag", "rtp", "tilt", "grav", "elev", "cond", "base"]
    R = F.orientation_order([line_v[k] for k in keys], [line_th[k] for k in keys])
    st.add("h431_orient_order", R, "H43-1",
           "R = |sum_p w_p exp(2i theta_p)| / sum_p w_p over "
           f"{keys}: do independent physics agree on the strike?")
    or_fused = np.max(np.stack([line_v[k] for k in keys]), axis=0)
    st.add("h431_multi_physics_fused", or_fused * R, "H43-1",
           "OR-fusion of the per-physics line responses, gated by strike agreement")
    del or_fused, R
    gc.collect()

    # ---------------------------------------------------------------- H43-2  concealed faults
    log("H43-2 concealed basin-bounding faults")
    base_step = F.robust_norm(F.grad_mag(B["depth_to_base_surf"], 1.5), foot)
    cond_step = F.robust_norm(F.grad_mag(np.log1p(np.abs(B["cond_surf"])), 1.5), foot)
    st.add("h432_base_step", base_step, "H43-2",
           "|grad depth_to_base_surf|: a step in the sedimentary cover thickness = basin fault")
    st.add("h432_cond_step", cond_step, "H43-2",
           "|grad log cond_surf|: MT conductivity step = buried lithologic/fluid boundary")
    st.add("h432_coincidence", np.sqrt(base_step * cond_step * line_v["shear"]), "H43-2",
           "geometric mean of basement step, conductivity step and geodetic shear ridge")

    # concealment gate: where would a surface mapper be blind?
    surf_expr = F.robust_norm(
        F.gsmooth(np.abs(B["det_elev"]).astype(F32), 2.0), foot)
    slope_expr = F.robust_norm(F.gsmooth(B["det_elev_slope"], 2.0), foot)
    conceal = np.clip(1.0 - 0.5 * (surf_expr + slope_expr), 0.0, 1.0)
    st.add("h432_conceal_gate", conceal, "H43-2",
           "1 - mean(local relief, local slope): high where no scarp could be mapped")
    st.add("h432_concealed_coincidence", conceal * np.sqrt(base_step * cond_step), "H43-2",
           "subsurface coincidence weighted by the concealment gate")

    # ---------------------------------------------------------------- H43-3  seismicity
    log("H43-3 seismicity residual")
    ieq_hp = F.highpass(B["ieq_n100a15"], 12.0)
    st.add("h433_seis_resid", np.abs(ieq_hp), "H43-3",
           "|ieq - smooth(ieq, 12 px)|: the supplied band is 0.9935 self-correlated at 3 km, "
           "so only the high-pass residual can carry fault-scale information")
    st.add("h433_deq_min", -B["deq_n100a15"].astype(np.float64), "H43-3",
           "negative distance-to-earthquake: local minima line up along active structures")

    # ---------------------------------------------------------------- H43-5  gravity SPI
    log("H43-5 gravity source-parameter imaging")
    gtilt = np.arctan2(B["iso_grav_anom_vg"].astype(np.float64),
                       B["iso_grav_anom_hg"].astype(np.float64) + 1e-30)
    ghg = np.sqrt(B["iso_grav_anom_hg"].astype(np.float64) ** 2
                  + B["iso_grav_anom_vg"].astype(np.float64) ** 2)
    st.add("h435_grav_analytic_signal", F.robust_norm(ghg.astype(F32), foot), "H43-5",
           "analytic signal amplitude of the isostatic gravity anomaly")
    st.add("h435_grav_tilt_depth", F.robust_norm(
        np.abs(1.0 / (F.grad_mag(np.asarray(gtilt, dtype=F32), 1.0) + 1e-6)), foot), "H43-5",
        "tilt-depth SPI: 1/|grad(tilt)| estimates depth to the density contrast")

    # ---------------------------------------------------------------- geodetic strain
    st.add("strain_second_invariant", F.robust_norm(F.gsmooth(B["geod_2ndinv"], 2.0), foot),
           "base", "geodetic second invariant, smoothed")
    st.add("strain_dilat_abs", np.abs(B["geod_dilaterate"].astype(np.float64)), "base",
           "|dilatation rate|")

    # ---------------------------------------------------------------- external rasters
    log("external rasters (GeoDAWN radiometrics, LiDAR scarps, SGMC)")
    rad, rad_desc = bands.external("geodawn_rad_u8.tif")
    for i, d in enumerate(rad_desc or []):
        st.add(f"rad_{d}", F.gsmooth(rad[i].astype(F32), 0.8), "base",
               f"GeoDAWN radiometric band {d!r}")
    ext, ext_desc = bands.external("geodawn_extensions_u8.tif")
    for i, d in enumerate(ext_desc or []):
        st.add(f"radx_{d}", F.gsmooth(ext[i].astype(F32), 0.8), "base",
               f"GeoDAWN extension band {d!r}")
    lid, lid_desc = bands.external("lidar_scarp_features_u8.tif")
    for i, d in enumerate(lid_desc or []):
        if d in ("ex_max", "step_max", "downface_max", "relief", "coh100"):
            st.add(f"lidar_{d}", F.gsmooth(lid[i].astype(F32), 0.8), "base",
                   f"1 m LiDAR scarp product band {d!r}")

    sgmc, _ = bands.external("derived_sgmc_faults_100m_u8.tif")
    sgmc_prox = np.exp(-distance_transform_edt(sgmc[0] == 0).astype(np.float64) / 400.0)
    st.add("ext_sgmc_prox", sgmc_prox, "external",
           "exp(-d/400 m) to the SGMC fault inventory (an independent compilation)")

    # ---------------------------------------------------------------- H43-4  fluids
    log("H43-4 geothermal fluid conduit alignment")
    sp = bands.points_from_csv("gdr_wellspring_in_footprint.csv")
    hot = sp[sp["thermalclass"].astype(str).str.strip().str.lower() == "hot"]
    temp = np.asarray(sp.get("temp_c", pd_nan(len(sp))), dtype=np.float64)
    wt = np.where(np.isfinite(temp), np.clip((temp - 20.0) / 60.0, 0.05, 3.0), 0.3)
    rows = np.clip(sp["row"].to_numpy().astype(int), 0, foot.shape[0] - 1)
    cols = np.clip(sp["col"].to_numpy().astype(int), 0, foot.shape[1] - 1)
    st.add("h434_spring_density", F.robust_norm(
        _point_density(rows, cols, foot, wt, 1.2), foot), "H43-4",
        "GDR well/spring density weighted by measured temperature")
    # unique spring/well locations, weighted by measured temperature, used for the alignment fit
    ukey = sp[["row", "col"]].drop_duplicates()
    ur = np.clip(ukey["row"].to_numpy().astype(int), 0, foot.shape[0] - 1)
    uc = np.clip(ukey["col"].to_numpy().astype(int), 0, foot.shape[1] - 1)
    lut = {(int(r), int(c)): float(w) for r, c, w in
           zip(sp["row"].to_numpy().astype(int), sp["col"].to_numpy().astype(int), wt)}
    uw = np.array([max(lut.get((int(r), int(c)), 0.3), 0.02) for r, c in zip(ur, uc)])
    if len(ur) >= 3:
        hl = point_alignment_lineaments(ur, uc, uw, foot.shape, r_max=25.0, min_pts=3,
                                        elong_min=0.80, extend=12.0)
        st.add("h434_spring_lines", F.robust_norm(hl, foot), "H43-4",
               "locality-constrained PCA lineaments through clusters of >=3 thermal features "
               "(radius 25 px, elongation >= 0.80), extended 12 px along strike: orientation "
               "evidence that an isotropic proximity decay cannot express")
        del hl
        gc.collect()
    vents = bands.points_from_csv("gdr_volcanic_vents_in_footprint.csv")
    if len(vents):
        vr = np.clip(vents["row"].to_numpy().astype(int), 0, foot.shape[0] - 1)
        vc = np.clip(vents["col"].to_numpy().astype(int), 0, foot.shape[1] - 1)
        st.add("ext_vent_prox", np.exp(-distance_transform_edt(
            _mask_from_points(vr, vc, foot.shape)).astype(np.float64) / 800.0), "external",
            "exp(-d/800 m) to GDR volcanic vents")

    log(f"{len(st.names)} channels built")
    return st


def pd_nan(n):
    return np.full(n, np.nan)


def _mask_from_points(rows, cols, shape):
    m = np.zeros(shape, dtype=bool)
    m[rows, cols] = True
    return ~m
