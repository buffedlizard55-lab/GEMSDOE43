"""Derived geophysical channels for the GeoDAWN region.

Design rule for this module: **every channel is a named physical transform of a named band**, and
the band names are read from the GeoTIFF metadata rather than assumed
(``gems43.bands.band_descriptions()``).  Nothing here reads ``labels.tif``, so every channel is
safe to evaluate on a spatial holdout without retrospective leakage.

The three identities used repeatedly
------------------------------------
``hessian_eig``      closed-form eigenvalues/orientation of the Gaussian-smoothed Hessian.  For a
                     2x2 symmetric matrix the eigenvalues are available in closed form, so a
                     multi-scale line (Frangi) response costs three separable Gaussian passes and
                     no eigen-solver loop.
``frangi``           Frangi et al. (1998) vesselness: anisotropy x structureness, evaluated for
                     bright ridges and dark valleys separately.  A magnetic low and a magnetic high
                     are equally good contact markers, so both polarities are kept.
``directional_2nd``  the second derivative along direction ``u`` is ``u^T H u``.  Because the
                     Hessian is computed once, the response at *any* orientation is a closed-form
                     combination of ``Hxx, Hyy, Hxy`` -- so a 16-direction maximum costs 16 cheap
                     array expressions instead of 16 convolutions.  This is what makes an
                     along-strike lineament term affordable on a 3730x3292 grid.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter, uniform_filter

from . import bands, paths

F32 = np.float32

# --------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------


def robust_norm(a: np.ndarray, foot: np.ndarray, pct: float = 99.5, clip: float = 1.0) -> np.ndarray:
    """Robust [0, 1] normalisation of a non-negative score, computed inside the footprint only."""
    v = a[foot]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros_like(a, dtype=F32)
    hi = float(np.percentile(v, pct))
    lo = float(np.percentile(v, 1.0))
    if hi <= lo:
        hi = float(v.max()) or 1.0
    out = (a - lo) / (hi - lo)
    np.clip(out, 0.0, clip, out=out)
    out[~foot] = 0.0
    return out.astype(F32)


def gsmooth(a: np.ndarray, sigma: float) -> np.ndarray:
    return gaussian_filter(a.astype(F32), sigma, mode="nearest")


def zscore_robust(a: np.ndarray, foot: np.ndarray | None = None) -> np.ndarray:
    """Robust z-score (median / 1.4826*MAD) so scale-free transforms behave identically
    across bands whose physical units differ by orders of magnitude."""
    v = a if foot is None else a[foot]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros_like(a, dtype=F32)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) * 1.4826
    return ((a - med) / (mad if mad > 0 else 1.0)).astype(F32)


def hessian(a: np.ndarray, sigma: float):
    """Gaussian second derivatives at scale ``sigma``: ``(Hxx, Hyy, Hxy)``."""
    f = a.astype(F32)
    Hxx = gaussian_filter(f, sigma, order=[2, 0], mode="nearest")
    Hyy = gaussian_filter(f, sigma, order=[0, 2], mode="nearest")
    Hxy = gaussian_filter(f, sigma, order=[1, 1], mode="nearest")
    return Hxx.astype(F32), Hyy.astype(F32), Hxy.astype(F32)


def hessian_eig(Hxx, Hyy, Hxy):
    """Closed-form eigenvalues and principal orientation of a field of 2x2 symmetric matrices.

    Returns ``(l1, l2, theta)`` with ``|l1| <= |l2|`` and ``theta`` the orientation of the
    eigenvector of ``l1`` (the along-line direction for a ridge).
    """
    tr = Hxx + Hyy
    det = Hxx * Hyy - Hxy * Hxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    la = tr / 2.0 + disc
    lb = tr / 2.0 - disc
    swap = np.abs(la) > np.abs(lb)
    l1 = np.where(swap, lb, la).astype(F32)     # small magnitude  -> along the line
    l2 = np.where(swap, la, lb).astype(F32)     # large magnitude  -> across the line
    theta = 0.5 * np.arctan2(2.0 * Hxy, (Hxx - Hyy) + 1e-30)   # orientation of the l1 axis
    return l1, l2, theta.astype(F32)


def frangi(Hxx, Hyy, Hxy, beta: float = 0.5, c: float = 12.0, polarity: str = "both"):
    """Frangi vesselness from a precomputed Hessian.

    ``polarity='ridge'`` keeps bright lineaments (``l2 < 0``), ``'valley'`` dark ones
    (``l2 > 0``), ``'both'`` returns ``max(ridge, valley)`` -- which is what geophysics wants,
    because a magnetic low and a magnetic high are equally good contact markers.
    """
    l1, l2, theta = hessian_eig(Hxx, Hyy, Hxy)
    a2 = l2 * l2
    rb = (np.abs(l1) / (np.abs(l2) + 1e-30)).astype(F32)
    s = np.sqrt(l1 * l1 + a2).astype(F32)
    aniso = np.exp(-(rb ** 2) / (2.0 * beta ** 2))
    struct = 1.0 - np.exp(-(s ** 2) / (2.0 * c ** 2))
    v = (aniso * struct).astype(F32)
    if polarity == "ridge":
        v = np.where(l2 < 0, v, 0.0)
    elif polarity == "valley":
        v = np.where(l2 > 0, v, 0.0)
    else:
        v = np.where(l2 != 0, v, 0.0)
    return v.astype(F32), theta, l2


def directional_second(Hxx, Hyy, Hxy, n_dir: int = 16):
    """``max_theta |u^T H u|`` and the argmax direction index -- the steerable line response.

    ``u^T H u = Hxx cos^2 + 2 Hxy cos sin + Hyy sin^2``; the max over ``theta`` is taken over
    ``n_dir`` half-circle directions with **no extra convolutions**.
    """
    th = np.arange(n_dir, dtype=np.float64) * np.pi / n_dir
    best = None
    arg = None
    for i, t in enumerate(th):
        ct, st = np.cos(t), np.sin(t)
        r = Hxx.astype(np.float64) * ct * ct + 2.0 * Hxy.astype(np.float64) * ct * st \
            + Hyy.astype(np.float64) * st * st
        if best is None:
            best = r
            arg = np.full(r.shape, i, dtype=np.int16)
        else:
            m = np.abs(r) > np.abs(best)
            best = np.where(m, r, best)
            arg = np.where(m, i, arg)
    return np.abs(best).astype(F32), arg.astype(np.int16)


def structure_tensor_coherence(a: np.ndarray, sigma: float = 2.0):
    """Local orientation coherence ``(l1-l2)/(l1+l2)`` of the gradient structure tensor.

    Near 1 where the field is locally one-dimensional -- i.e. where there is a single, consistent
    line orientation.  This is the cheap, local counterpart of an along-strike collinearity vote.
    """
    gx = np.zeros_like(a, dtype=F32)
    gy = np.zeros_like(a, dtype=F32)
    gaussian_filter(a.astype(F32), sigma, order=[0, 1], output=gx, mode="nearest")
    gaussian_filter(a.astype(F32), sigma, order=[1, 0], output=gy, mode="nearest")
    Jxx = gaussian_filter(gx * gx, sigma * 2, mode="nearest")
    Jyy = gaussian_filter(gy * gy, sigma * 2, mode="nearest")
    Jxy = gaussian_filter(gx * gy, sigma * 2, mode="nearest")
    tr = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = (tr / 2.0 + disc).astype(F32)
    l2 = (tr / 2.0 - disc).astype(F32)
    return (np.maximum(l1 - l2, 0) / (l1 + l2 + 1e-30)).astype(F32)


def grad_mag(a: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    gx = gaussian_filter(a.astype(F32), sigma, order=[0, 1], mode="nearest")
    gy = gaussian_filter(a.astype(F32), sigma, order=[1, 0], mode="nearest")
    return np.sqrt(gx * gx + gy * gy).astype(F32)


def highpass(a: np.ndarray, sigma: float) -> np.ndarray:
    """``a - smooth(a, sigma)`` -- removes the regional field and keeps the local anomaly."""
    return (a - gsmooth(a, sigma)).astype(F32)


def nms_ridge(resp: np.ndarray) -> np.ndarray:
    """Non-maximum suppression of a ridge response across the local gradient direction."""
    gy = np.zeros_like(resp)
    gx = np.zeros_like(resp)
    gaussian_filter(resp, 1.0, order=[1, 0], output=gy, mode="nearest")
    gaussian_filter(resp, 1.0, order=[0, 1], output=gx, mode="nearest")
    mag = np.hypot(gx, gy) + 1e-30
    ux = (gx / mag).astype(F32)
    uy = (gy / mag).astype(F32)
    from scipy.ndimage import map_coordinates
    H, W = resp.shape
    rr, cc = np.meshgrid(np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32),
                         indexing="ij")
    f = resp.astype(F32)
    a1 = map_coordinates(f, [rr + uy, cc + ux], order=1, mode="nearest")
    a2 = map_coordinates(f, [rr - uy, cc - ux], order=1, mode="nearest")
    return np.where((f >= a1) & (f >= a2), f, 0.0).astype(F32)


def orientation_order(weights: list[np.ndarray], thetas: list[np.ndarray]) -> np.ndarray:
    """Second-order orientation order parameter ``R = |sum_p w_p e^{2i theta_p}| / sum_p w_p``.

    ``R = 1`` when every physics that responded agrees on the strike; ``R = 0`` when their strikes
    are uniformly scattered.  Requiring agreement is the mechanism that selects structures an
    expert would accept and rejects single-dataset artefacts.
    """
    num_r = np.zeros_like(weights[0], dtype=np.float64)
    num_i = np.zeros_like(num_r)
    den = np.zeros_like(num_r)
    for w, t in zip(weights, thetas):
        wd = w.astype(np.float64)
        num_r += wd * np.cos(2.0 * t.astype(np.float64))
        num_i += wd * np.sin(2.0 * t.astype(np.float64))
        den += wd
    return (np.sqrt(num_r ** 2 + num_i ** 2) / (den + 1e-30)).astype(F32)


def dilate_max(a: np.ndarray, size: int) -> np.ndarray:
    from scipy.ndimage import maximum_filter
    return maximum_filter(a, size=size, mode="nearest").astype(F32)


def smooth_mean(a: np.ndarray, size: int) -> np.ndarray:
    return uniform_filter(a, size=size, mode="nearest").astype(F32)


# --------------------------------------------------------------------------------------
# channel builders -- one function per channel, each documented by the physics it measures
# --------------------------------------------------------------------------------------


def _line_pack(a: np.ndarray, foot: np.ndarray, sigmas=(1.2, 2.5)):
    """Multi-scale Frangi response + orientation for one field."""
    best_v = np.zeros(a.shape, dtype=F32)
    best_th = np.zeros(a.shape, dtype=F32)
    best_l2 = np.zeros(a.shape, dtype=F32)
    for s in sigmas:
        Hxx, Hyy, Hxy = hessian(a, s)
        v, th, l2 = frangi(Hxx, Hyy, Hxy, polarity="both")
        v = robust_norm(v, foot)
        m = v > best_v
        best_v = np.where(m, v, best_v)
        best_th = np.where(m, th, best_th)
        best_l2 = np.where(m, l2, best_l2)
    return best_v, best_th, best_l2
