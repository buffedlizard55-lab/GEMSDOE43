# Root cause of the `Predicted values must be in range [0, 1]` rejection

**Why this page exists.** A submission can be geospatially perfect and still be refused by the
portal with the message `Predicted values must be in range [0, 1]`. This page is the reference for
what causes that, what is verified and what is inference, and which of the two files this project
publishes you should actually upload.

---

## What the specification says (verified)

From the official submission-format page, read 2026-10-06
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>):

> Make sure your predictions are in the correct format: single band, **float32**, with predicted
> values in **[0, 1]**, in the same CRS (EPSG:32611), resolution (100m) and bounds as the training
> data. Use **null (NaN) values outside of the bounds**.

Three separate requirements are fused in that sentence, and they pull in different directions:

| # | Requirement | Reading |
|---|---|---|
| 1 | one band, float32 | unambiguous |
| 2 | EPSG:32611, 100 m, training bounds | unambiguous |
| 3 | predicted values in `[0, 1]` | **ambiguous — is the predicate applied to every cell, or only to predicted cells?** |
| 4 | null / NaN outside the bounds | **contradicts (3) if (3) is applied to every cell**, because `NaN` satisfies no range predicate |

That contradiction is the root cause. Any validator that evaluates `(raster >= 0) & (raster <= 1)`
over the **whole array** will reject a file that honours requirement 4 literally, because
`np.nan >= 0` is `False`.

## What the organizers' own reference code does (verified)

The official reference solution repository,
<https://github.com/drivendataorg/gems-prize-reference-solution>, writes its output with
**no nodata value at all** and **no NaN** — every cell in the raster is a finite float32. The
reference therefore satisfies requirement 3 under *either* reading, and satisfies requirement 4
only in the weak sense that there is no predicted fault outside the bounds.

**Inference (labelled as such):** the safest reading is that the validator applies the range
predicate to the whole array, and that the reference solution is nodata-free *because of that*.
This is consistent with the reported rejection text, but I have not read the validator source,
which is not public.

## Failure modes observed in this lineage

| Encoding outside the footprint | Whole-array `(v>=0)&(v<=1)` | Literal-spec compliance | Outcome |
|---|---|---|---|
| `0.0` (this project's **primary** file) | **passes** | satisfies it in spirit: "no fault predicted outside" | accepted |
| `NaN` (this project's **twin**) | **fails** | satisfies it literally | rejected if the validator is whole-array |
| float32 sentinel `-3.4028234663852886e+38` | **fails** | neither | rejected |
| unmasked model output (e.g. softmax tails outside the bounds) | **fails** | neither | rejected |

The sentinel row matters: GDAL will happily round-trip `-3.4028234663852886e+38` as a nodata
value, and a reader that replaces nodata with NaN produces the same rejection by a different
route. Never pass a nodata value to the writer.

## What this project does about it

`src/gems43/submission.py` is written **fail-closed** and produces **two** files, byte-identical
inside the footprint:

* **`…-zeros.tif`** — outside-footprint cells are `0.0`. **Download this one.** It can never trip a
  whole-array range predicate, it matches the organizer's own reference encoding, and it costs
  nothing in score: the official metric only sums over cells with `p(x) > 0`, so an outside cell
  holding `0.0` contributes to neither `TP_w` nor `FP_w`.
* **`…-nan.tif`** — outside-footprint cells are `NaN`, the literal wording of requirement 4. Upload
  this only if DrivenData support confirms the validator masks before checking the range.

Both files are re-read from disk after writing and verified against twelve named checks
(`single_band`, `dtype_float32`, `dimensions_3730x3292`, `crs_epsg_32611`, `transform_matches`,
`in_footprint_all_finite`, `in_footprint_zero_nan`, `in_footprint_zero_inf`,
`in_footprint_zero_sentinel`, `in_footprint_range_0_1`, `outside_footprint_compliant`), and the
writer **raises** rather than emitting a file that fails. The whole-array predicate
(`whole_raster_range_0_1`) is reported for both files but is *not* a required check, precisely
because the NaN twin cannot satisfy it by construction — that asymmetry is recorded in
`evidence/submission.json` rather than hidden.

## If the portal rejects your file anyway

1. Confirm the value encoding: `gdalinfo -stats <file>` and check `Min/Max`. If `Min` is
   `-3.4028234663852886e+38` or `nan`, you uploaded a nodata-encoded file. Re-upload the
   `-zeros` twin.
2. Confirm the band count and dtype: `gdalinfo` must show `Type=Float32` and `Band 1` only. A
   2-band or `Byte`/`UInt16` raster is rejected before the range check.
3. Confirm the grid: `gdalinfo` must show `Size is 3292, 3730` and
   `Origin = (…)` matching the template, with `Pixel Size = (100.0000000000000000,-100.0000000000000000)`.
4. Confirm the CRS is `EPSG:32611` (UTM zone 11N, WGS 84).

`scripts/build_submission.py` prints all four of these from the written bytes after every build,
so the audit in `evidence/submission.json` is the first thing to check.

## Line-by-line verification commands

```bash
cd /home/user/GEMSDOE43
gdalinfo -stats docs/downloads/*-zeros.tif | grep -Ei 'size is|type=|origin|pixel size|min/max|nodata'
PYTHONPATH=src python3 - <<'PY'
import json, numpy as np, rasterio
from gems43 import paths
j = json.loads((paths.repo_root()/'evidence'/'submission.json').read_text())
print(json.dumps(j['files']['zeros']['checks'], indent=1))
PY
```
