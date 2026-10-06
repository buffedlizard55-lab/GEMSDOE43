# Data access and provenance audit

**Audit date:** 2026-10-06 UTC

## What was verified

1. The official DrivenData data URL resolves to its login page in this environment. No DrivenData session or competition data authorization was available here. The site states that competition registration is required to receive the training data and labels ([official rules §3.1](https://docs.nlr.gov/docs/fy26osti/96647.pdf); [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)).
2. To avoid stopping at that blocker, the three GEMS inputs were restored from public, owner-published GitHub mirrors pinned in `registry/data_sources.json`. Each final file's byte count and SHA-256 matched that prior-project manifest. This establishes mirror integrity only; it is not an organizer-issued checksum, nor proof that the mirror is byte-identical to the DrivenData download. Raw files remain git-ignored.
3. The training raster reopened as 19 float32 bands, 3,730 × 3,292, EPSG:32611, 100-m pixels, with transform `(100, 0, 243350; 0, -100, 4508550)`. Band names were read from each band's own `band_name` tag. The manifest hash is `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`.
4. The labels and sample have matching dimensions, CRS, transform, and footprint. The labels contain 60,988 positives and 7,111,787 outside-footprint cells marked `-1`. The provided `sample_submission.tif` has 60,988 values equal to 1, and those positives coincide pixel-for-pixel with the label positives; it is **not** an all-zero absence raster in the mirrored bytes. The competition describes the sample as a total-fault-absence example. This apparent mismatch is flagged as **IR-DATA-01**. The sample is used only to recover grid geometry and the finite in-footprint mask; its prediction values are never copied.
5. The training raster's finite nodata sentinel is `-3.4028234663852886e+38`. A future prediction writer must not leak this sentinel into output values. The official output description requires a single-band float32 GeoTIFF, [0,1] values on the region and null/NaN outside. No candidate submission writer or submission raster is currently released because G43-CG01 failed the holdout gate.
6. For a local reproduction of the published H42 holdout best, the public 3DEP-derived 12-band `lidar_scarp_features_u8.tif` mirror was restored from GEMSDOE24, with byte count and hash recorded in the input audit. It is **baseline-only**, not an input to G43-CG01. Its full 1-m tile lineage has not been independently recreated in this checkout. The local decoder's evidence array matched the public GEMSDOE41 `load_products` implementation pixel-for-pixel; this checks implementation consistency, not the mirror's original tile lineage.
7. `scripts/audit_inputs.py` now runs successfully. The receipt reports the expected 3,730 × 3,292 EPSG:32611 grid, 5,167,373 finite footprint cells, 7,111,787 outside cells, 60,988 known positive labels, and the exact sample/label mask match. The only registered data irregularity is IR-DATA-01; the baseline-only scarp raster exactly matches the competition grid.

## Current constraints

- Competition files are not organizer-authenticated here. Before a prize submission, compare hashes and metadata with a fresh, authorized DrivenData download if account access is available.
- No external 1-m DEM mosaic was downloaded. The official rules and competition description identify 1-m DEM data, but the exact `1m_DEM_links.csv` inventory remains an authenticated competition input.
- USGS public layers are source-available, but any use in a final prize package must also be documented with license, processing, alignment, coverage, and shareability for evaluation.
- DrivenData's [Terms of Use §Prohibited Uses](https://www.drivendata.org/termsofuse/) prohibit using a robot, spider, or other automatic means to access the site for monitoring/copying, and prohibit manual monitoring/copying without prior written consent. Therefore this project does **not** implement an automated leaderboard scraper or polling workflow and does not refresh/copy leaderboard values. The last previously recorded snapshot remains historical only; a refresh requires prior written permission or an authorized API.
- DrivenData staff clarified that known USGS/INGENIOUS fault pixels are masked from official scoring and re-evaluation ([staff reply](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)). The G43 local holdout does not use that mask, because it would remove its withheld known-fault truth. This distinction is recorded in `evidence/holdout_g43_cg01.json`.
- DrivenData staff declined to disclose the sources, types and coverage used for hidden faults ([staff reply](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7)); geological signatures in the hypothesis slate must therefore be treated as candidate mechanisms, not known characteristics of the hidden set.

## Reproducible audit

```bash
bash scripts/download_competition_data.sh
.venv/bin/python scripts/audit_inputs.py
```

The local receipt is `evidence/input_audit.json`; the restore receipt is `evidence/data_restore_receipt.json`.
