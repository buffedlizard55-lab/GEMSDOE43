# Machine-readable audit evidence

These compact JSON records were extracted from the corresponding completed GitHub Actions check summaries and include the official run/check IDs and links. Raw inputs are intentionally not stored here.

- [`ngb_source_audit.json`](ngb_source_audit.json) — official USGS NGB CSV record, assay-quality and footprint counts. The audit completed, but the frozen H46-A sample-count gates failed; no holdout was run.
- [`sgmc_source_audit.json`](sgmc_source_audit.json) — official USGS SGMC v1.1 archive checksums, schema/join report, projected polygon coverage and H46-B source-gate result. All source gates passed; this is not a holdout score.
- [`h46b/`](h46b/) — aggregate experiment, four-fold public-catalogue proxy result, input manifest, and distinct GeoTIFF format/hash receipt. The promotion gate failed, so no private-set validation, leaderboard score, or submission slot is claimed.
- [`leaderboard_observation.json`](leaderboard_observation.json) — dated 2026-10-06 official leaderboard-row observations (0.2778 rank #13; 0.3345 rank #1). No file/hash crosswalk or archived screenshot exists; the later page fetch returned a JavaScript loading shell, so do not use these as an undated current snapshot or attribute a file.

The Actions summaries are the origin of the source-audit records: [NGB run 37446554478](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37446554478) and the latest pinned, polygon-only [SGMC run 37455479306](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479306). The blocked experiment receipt is from [run 37455686781](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455686781). The sample-submission raster is an owner-supplied mirror and was inspected only for its finite footprint and grid metadata.
