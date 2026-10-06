# H46-B blocked holdout result and no-promotion decision — 2026-10-06

## Decision

H46-B's preregistered source gates passed, so the frozen recipe was run once against the registered public-catalogue spatial-transfer proxy. **It did not pass the preregistered promotion gate. Do not submit this artifact or spend a submission slot on H46-B.** No private-set validation or leaderboard score was produced. The format/hash receipt is retained, but the raster is removed from the current tree and is not linked from the project site. An earlier public branch commit and an unexpired Actions artifact may still expose the bytes; a deletion request was denied by GitHub's integration permissions. See [`publication_status.json`](../evidence/h46b/publication_status.json) before accessing any historical artifact.

This amendment supersedes the earlier “holdout not yet run” status in the source-audit notes; it does not alter the frozen recipe, the registered fold design, or the original thresholds. After the gate failed, the runner-generated file was removed from the current repository tree and no current project-site page links to it. The automated output had already been committed to public branch commit `e7592729ee9f20f28733edaee87242a78221ef2c` and uploaded as an Actions artifact for run `37455686781`. A deletion request for artifact `11408883292` returned HTTP 403 (“Resource not accessible by integration”); when checked, that artifact had not expired and was due to expire 2027-01-04. GitHub may also retain the earlier commit/PR history. [`evidence/h46b/publication_status.json`](../evidence/h46b/publication_status.json) records the access caveat; no DrivenData upload occurred.

## Frozen implementation and execution receipt

- H46-B implementation/recipe freeze: commit [`e020a9692f5263f958dff05910bb081dae50cc69`](https://github.com/buffedlizard55-lab/GEMSDOE43/commit/e020a9692f5263f958dff05910bb081dae50cc69).
- Frozen source-only SGMC audit: [Actions run `37455479306`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479306); all source gates passed.
- Test/compile check at the frozen implementation: [Actions run `37455479404`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479404); local suite had 17 passing tests.
- One blocked experiment execution: [Actions run `37455686781`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455686781), at workflow trigger commit `438852f6db39652c7cf5d52b46c53b04379e1d28`. No experiment code changed after the frozen implementation; the later commit only registered the workflow and refreshed documentation/evidence.
- Full machine-readable receipts: [`evidence/h46b/experiment.json`](../evidence/h46b/experiment.json), [`holdout.json`](../evidence/h46b/holdout.json), [`data_manifest.json`](../evidence/h46b/data_manifest.json), and [`submission_receipt.json`](../evidence/h46b/submission_receipt.json).

## Locked proxy design and label boundary

The four spatial folds use 20 km four-colour blocks:

```text
fold_id = ((row // 200) + 2 * (col // 200)) % 4
```

Each arm emitted 40,000 predictions per fold with equal binary mass, a 400 m minimum separation, a 300 m fold-edge exclusion, and the frozen two-pixel training-trace guard. Labels were used only for fold assignment, the emission guard, and scoring against the **public catalogue**. The H42 incumbent and H46-B signal surfaces were constructed before labels were loaded. The held-out proxy tests transfer to unseen geographic blocks in that catalogue; it is not the challenge's expert-labelled private set of new faults.

The unchanged incumbent is `H42 SH_basin_strong|sep4.0|N40000`. Its same-run four-fold DTI exactly reproduced the registered prior values (maximum per-fold error `0.0`, tolerance `1e-5`). H46-B's frozen surface combined that incumbent with major-lithology and `(min_era, max_era)` map-unit-contact contrast multiplied by the empirical TMI horizontal-gradient percentile, using the fixed `0.75 / 0.25` geometric-mean weights and the registered `0.05` floor.

## Results

`Δ DTI = H46-B DTI − same-run H42 DTI`.

| Fold | H42 incumbent | H46-B | Δ DTI | Fold result |
|---:|---:|---:|---:|---|
| 0 | 0.242272 | 0.242266 | −0.000006 | H42 |
| 1 | 0.247658 | 0.247607 | −0.000051 | H42 |
| 2 | 0.255021 | 0.256993 | +0.001972 | H46-B |
| 3 | 0.258025 | 0.259801 | +0.001776 | H46-B |
| **Mean** | **0.250744** | **0.251667** | **+0.000923** | **2 / 4 wins** |

| Preregistered decision gate | Required | Observed | Result |
|---|---:|---:|---|
| Reproduce H42 on every fold | within `1e-5` | all four exact; max error `0.0` | Pass |
| H46-B mean improvement | at least `+0.005` | `+0.000923` | **Fail** |
| H46-B fold wins | at least `3 / 4` | `2 / 4` | **Fail** |
| Worst fold regression | no worse than `−0.010` | `−0.000051` | Pass |
| **Overall promotion** | all required gates | two improvement gates fail | **Fail — no slot** |

This small positive mean is a public-catalogue proxy observation, not evidence that H46-B improves detection of new faults. The method was not tuned on these folds after seeing the result. These folds are spent for this registered confirmation; any materially different recipe needs a new dated preregistration and fresh confirmation regions before a slot is considered.

## Runner artifact receipt and current publication status

The workflow generated a new artifact from the pinned feature inputs and frozen code; it was not copied from a sibling. The failed promotion gate means the GeoTIFF is **not present in the current repository tree and is not linked from the current project site**. However, an earlier public branch commit contains it, and the Actions artifact from run `37455686781` was still unexpired when checked on 2026-10-06; GitHub denied the deletion request due to integration permissions. Access to that historical artifact depends on repository visibility and GitHub permissions. The receipt records what the runner produced:

- Runner filename (identification only): `GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006.tif`
- Distinct identifier: `GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006`
- Runner-reported size: `381,558` bytes
- SHA-256: `c51cf006c19f1993606a0b0b55467f0a74f0a1c13e747c3f592d55690d93a6f6`
- Format receipt: one-band `float32`; shape `3730 × 3292`; EPSG:32611; transform `(100, 0, 243350, 0, -100, 4508550)`; 40,000 positive prediction pixels; finite in-footprint values within `[0,1]`; `NaN` nodata outside the `5,167,373`-cell footprint. Receipt booleans are in `evidence/h46b/submission_receipt.json`; an independent local Rasterio read reproduced the file size, hash, grid, mask, and value range before the no-go publication decision.
- [`evidence/h46b/publication_status.json`](../evidence/h46b/publication_status.json) records the current-tree/site removal, historical-commit and Actions-artifact exposure, and denied artifact-deletion attempt. No organizer upload was made and no slot was used. The runner receipt sets `holdout_proxy_gate_passed=false`, `private_set_validation=false`, and `leaderboard_score=null`.

The short research-status note and explicit non-submission instructions are [`submission/FORM-NOTE.txt`](../submission/FORM-NOTE.txt) and [`submission/INSTRUCTIONS.md`](../submission/INSTRUCTIONS.md). They are not an invitation to upload this file.

## Sources and access caveats

The geologic signal uses the official USGS State Geologic Map Compilation (SGMC) v1.1 CA/NV `geol_poly` polygons and the same-release all-state age/lithology tables. The source audit verified the archive hashes and schemas, transformed 12,469 grid-intersecting geometries from declared EPSG:4326 to EPSG:32611, mapped every finite-footprint cell to a unit, and found 96.3289% joint major-lithology/age support plus 476,338 positive-contact cells. It extracted/opened only polygon components and the needed tables; neither SGMC Structure layer was opened. See the [source-audit amendment](AMENDMENT-2026-10-06-SGMC-table-archive.md) and the linked check summary.

During final source review on 2026-10-06, the official 2017 SGMC ScienceBase record was found to carry a notice that a newer 2026 GeMS version is available and recommended: [USGS release DOI 10.5066/P1A3DQZK](https://doi.org/10.5066/P1A3DQZK), documented on this [NGMDB product page](https://ngmdb.usgs.gov/Prodesc/proddesc_119417.htm). This run remains tied to the preregistered, pinned v1.1 archives; it did not retrieve or audit the newer release. No source version was changed after the holdout. A future study must audit the new release and preregister fresh confirmation regions rather than treat v1.1 coverage as a current-version gate.

The competition feature rasters and public-catalogue labels were obtained through integrity-pinned owner-supplied mirrors, not authenticated organizer originals; their provenance and SHA-256 values are recorded in the data manifest. The challenge's private test labels were not accessed. The SGMC source audit never read labels or sample-template pixel values.

## Subsequent hypotheses

H46-A remains stopped at its failed NGB source gate and was not scored. H46-C, the persistent Landsat alteration-margin hypothesis, was not tested. No further candidate or submission slot is authorized by this result. Preserve **“Maximize P(Win)”** and **“Own the Outcome.”**
