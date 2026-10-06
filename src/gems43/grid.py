"""The frozen competition grid and the kernel geometry of the official metric.

Every constant here is [OFFICIAL] or [MEASURED]:

* CRS / transform / shape / dtype — read from the hash-pinned ``sample_submission.tif``
  (sha256 ``2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc``).
* R = 300 m, alpha = 0.2, beta = 0.8, k(d) = max(1 - d/R, 0) — verbatim from
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
  ("Performance metric"), read 2026-10-06.
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------------------
# Grid identity
# --------------------------------------------------------------------------------------
EPSG = 32611
WIDTH = 3292          # rasterio width  (columns)
HEIGHT = 3730         # rasterio height (rows)
SHAPE = (HEIGHT, WIDTH)
PIXEL_SIZE_M = 100.0

# The submission template's geotransform, as rasterio reports it: these are the six members of
# ``rasterio.transform.Affine`` **in Affine order (a, b, c, d, e, f)**, i.e.
#
#     x' = a*col + b*row + c        y' = d*col + e*row + f
#
# so a = 100 (pixel width), c = 243350 (x origin), e = -100 (row step), f = 4508550 (y origin).
#
# *** Do NOT pass these to ``Affine.from_gdal``. ***  ``from_gdal`` expects GDAL's order
# (origin_x, pixel_width, rot_x, origin_y, rot_y, pixel_height), which is a rotation of this one;
# feeding it this tuple produces a silently valid but wildly wrong geotransform, and the mistake
# is invisible to a check that compares ``to_gdal()`` output back against this constant, because
# ``to_gdal`` is the inverse permutation and round-trips the error.  That exact bug shipped once
# and is pinned by ``tests/test_submission.py::test_transform_matches_the_template``.
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)

# Golden bounds derived from TRANSFORM and SHAPE; asserted against written files so that a
# transposed geotransform cannot pass unnoticed.  left = c, top = f, right = c + a*WIDTH,
# bottom = f + e*HEIGHT.
BOUNDS = (243350.0, 4135550.0, 572550.0, 4508550.0)     # left, bottom, right, top
DTYPE = "float32"

# --------------------------------------------------------------------------------------
# Official metric constants
# --------------------------------------------------------------------------------------
R_METRES = 300.0
ALPHA = 0.2
BETA = 0.8
R_PIXELS = R_METRES / PIXEL_SIZE_M          # 3.0
EPS = 1e-12                                  # the page writes "+ eps" without a value


def kernel_offsets() -> tuple[np.ndarray, np.ndarray]:
    """Integer offsets (dr, dc) with Euclidean distance <= R, and their kernel weights.

    Returns ``(offsets, weights)`` where ``offsets`` is ``(M, 2)`` int and ``weights`` is
    ``(M,)`` float64 with ``weights[i] = max(1 - d_i / R_pixels, 0)``.
    """
    rad = int(np.floor(R_PIXELS))
    dr, dc = np.meshgrid(np.arange(-rad, rad + 1), np.arange(-rad, rad + 1), indexing="ij")
    d = np.sqrt(dr.astype(float) ** 2 + dc.astype(float) ** 2)
    m = d <= R_PIXELS
    offsets = np.stack([dr[m], dc[m]], axis=1)
    weights = np.maximum(0.0, 1.0 - d[m] / R_PIXELS)
    return offsets, weights


OFFSETS, KERNEL_W = kernel_offsets()
# Offsets that can actually deliver non-zero credit (d < R strictly).
_ACTIVE = KERNEL_W > 0


def shift(arr: np.ndarray, dr: int, dc: int, fill=0.0, out: np.ndarray | None = None) -> np.ndarray:
    """Shift a 2-D array by ``(dr, dc)`` rows/columns, zero- or ``fill``-padding.

    ``shift(a, dr, dc)[r, c] == a[r + dr, c + dc]`` (out-of-range -> ``fill``).
    """
    if out is None:
        out = np.full_like(arr, fill)
    else:
        out[...] = fill
    r_src0 = max(0, dr)
    r_src1 = min(arr.shape[0], arr.shape[0] + dr)
    c_src0 = max(0, dc)
    c_src1 = min(arr.shape[1], arr.shape[1] + dc)
    r_dst0 = max(0, -dr)
    r_dst1 = min(arr.shape[0], arr.shape[0] - dr)
    c_dst0 = max(0, -dc)
    c_dst1 = min(arr.shape[1], arr.shape[1] - dc)
    if r_src1 <= r_src0 or c_src1 <= c_src0:
        return out
    out[r_dst0:r_dst1, c_dst0:c_dst1] = arr[r_src0:r_src1, c_src0:c_src1]
    return out
