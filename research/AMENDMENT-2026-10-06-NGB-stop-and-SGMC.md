# Source-gate decision and H46-B preregistration amendment — 2026-10-06

## Decision on H46-A

The source-only audit for the frozen H46-A arm completed before any holdout run. GitHub Actions run [`37446554478`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37446554478) fetched the official USGS Open-File Report 2002-227 CSV over HTTPS and checksum-verified the pinned sample-template mirror. The audit read only the template's finite footprint mask and georeferencing; it did not read template sample values, labels, or any fault-score layer.

- CSV: 2,318,363 bytes; SHA-256 `cb3b0603efa558e84dfd33ff74efd14e005596060bf7fd964ecc413914e3a8e6`.
- The source contains 10,261 data rows. The parser found 4,563 eligible stream-sediment records with coordinates and 4,290 with at least three of the six locked clean assays.
- Only **451** eligible stream locations and **447** samples with at least three clean assays land on the finite target footprint. This fails the predeclared minimums of 1,000 and 500, respectively. The in-footprint samples cover 48 distinct 20 km blocks, with mapped studies Hum (253 eligible; 250 assay-qualified) and WS (198; 197); none are mapped to MJA in the footprint.
- The fixed 2 km source-only rasterizer reports geochemical support on 1,492,379 finite-footprint cells (28.9%) and no nonzero cells outside the footprint. This does not override the two failed sample-count gates.
- The source's first header cell is literally `'ID` and is normalized only to the documented `ID` field. The selected `Zn(part)_ppm` field has no separate blank-name qualifier column in this CSV; this is recorded, and inline `*` values would still be rejected. The audit found zero inline substitutions for Zn.

**H46-A is stopped before holdout.** The source/coverage promotion gate is false. No H46-A candidate raster, fold score, or submission artifact was generated, and no submission slot was spent. This is an explicit recorded source failure, not an implicit switch to another dataset. The full machine-readable counts and schema diagnostics are in the check summary for the run above.

## H46-B: explicit next hypothesis, source gate passed

Because H46-A failed its frozen source gate, H46-B was promoted to the first *eligible-to-audit* hypothesis; this was a documented re-ranking, not evidence that H46-B is better. H46-C remains lower-priority and was not silently substituted. The separately downloaded official SGMC source/schema/footprint gates have since passed; see [`AMENDMENT-2026-10-06-SGMC-table-archive.md`](AMENDMENT-2026-10-06-SGMC-table-archive.md). H46-B is now eligible for its preregistered blocked holdout after the implementation/tests are frozen, but no holdout score is available yet.

### Official source and availability verified from USGS pages

Use only the official USGS State Geologic Map Compilation (SGMC), version 1.1, for California and Nevada:

- Download index: https://mrdata.usgs.gov/geology/state/
- California polygons/attribute tables: https://mrdata.usgs.gov/geology/state/shp/CA.zip (the USGS page lists 23.8 MB)
- Nevada polygons/attribute tables: https://mrdata.usgs.gov/geology/state/shp/NV.zip (the USGS page lists 65.9 MB)
- USGS data release DOI: https://doi.org/10.5066/F7WH2N65
- SGMC metadata: https://mrdata.usgs.gov/geology/state/USGS_SGMC_Metadata.html
- USGS database field descriptions: https://mrdata.usgs.gov/geology/state/about.php?tblname=geol_poly, https://mrdata.usgs.gov/geology/state/about.php?tblname=age, and https://mrdata.usgs.gov/geology/state/about.php?tblname=lith
- USGS credit guidance: https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs

The official metadata describes SGMC as a compilation of state maps with source scales ranging from 1:50,000 to 1:1,000,000, intended for standardized regional/national GIS analysis; it cautions that map units are not reconciled across state boundaries. The documented polygon `unit_link` join key, `lith1`/`lith_rank` fields, and `min_era`/`max_era` age fields motivate the fixed test below. Actual archive bytes, CRS declarations, field presence, joins, geometries, and competition-footprint coverage still require direct verification. Credit the source as USGS SGMC version 1.1 (Horton, 2017; DOI 10.5066/F7WH2N65); do not imply that every mapped contact is a fault.

### Frozen source audit and signal recipe

1. Retrieve the two named state archives directly over verified HTTPS. Record exact byte counts and SHA-256 values. The input template may be used only for its finite mask and grid; no sample or label values are read during this source audit.
2. Use the SGMC geologic-unit polygon layer and its tabular `age` and `lith` attributes joined by `state + unit_link`. Do **not** use the SGMC `Structure` layer, any known-fault geometry, catalogue labels, or prior submission pixels. Require a declared source CRS and transform the polygons to the exact template CRS/grid. Record the per-state CRS and all schema/join irregularities.
3. The source gate passes only if (a) the official downloads parse; (b) at least 90% of finite-footprint pixel centers fall inside a mapped unit polygon; (c) at least 60% of finite-footprint cells have a polygon joined to both a nonempty major `lith1` descriptor and a nonempty `(min_era, max_era)` pair; and (d) at least 5,000 finite-footprint cells have a nonzero unit-contact contrast after rasterization. If any criterion fails, stop H46-B and file another explicit amendment before choosing or scoring any other source.
4. A map unit's lithology signature is the sorted set of nonempty `lith1` values attached to that `unit_link` with `lith_rank` equal to `major` (case-insensitive). Its age signature is the pair `(min_era, max_era)`. For each horizontal or vertical adjacency between different rasterized unit IDs, define lithology contrast as 1 only when both signatures are known and differ; define age contrast as 1 only when both pairs are known and differ. The boundary strength is the mean of the known contrast components (0–1); if neither component is known it is zero. Assign the maximum adjacent-boundary strength to each touching cell. No label-derived or fault-derived information enters this surface.
5. Compute the empirical percentile of the smoothed competition TMI horizontal-gradient feature (band 3, Gaussian sigma 1 pixel) over the finite footprint. The auxiliary contact evidence is `contact_strength × tmi_hg_percentile`. Form the H46-B candidate by combining that auxiliary surface with the unchanged H42 incumbent surface using the project's geometric mean with fixed weights `H42 = 0.75`, `contact evidence = 0.25` and the already-frozen 0.05 geometric-mean floor. No fitted weights, parameter search, catalogue masking, or post-hoc edits.
6. Before the first H46-B fold result is computed, freeze the source-audit output, code/tests, and a same-run H42 control. Use the registered four spatial folds, 40,000 predictions per fold, 4-pixel minimum separation, 300 m fold-edge exclusion, and 2-pixel training-trace guard in `PREREGISTRATION-2026-10-06.md`. Keep the pre-existing promotion thresholds: reproduce the four historical H42 folds to within 1e-5; improve same-run mean DTI by at least 0.005; win at least three of four folds; and have no fold more than 0.010 worse. A proxy result is not private-set validation, a leaderboard score, or automatic permission to spend a submission slot.

## Current ranking after the source stop

The original pre-data prior ranking remains preserved in the preregistration. For the next source audit only, H46-B is the highest-priority *remaining testable hypothesis* (prior expected upside low-to-moderate, implementation cost medium); H46-C, persistent Landsat alteration margins, remains second (prior upside low-to-moderate with higher uncertainty and higher acquisition/processing cost). Neither has an observed score. No replacement test is authorized if the SGMC data gate fails without a further dated amendment.
