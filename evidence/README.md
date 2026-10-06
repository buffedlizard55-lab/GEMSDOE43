# Machine-readable audit evidence

These compact JSON records were extracted from the corresponding completed GitHub Actions check summaries and include the official run/check IDs and links. Raw inputs are intentionally not stored here.

- [`ngb_source_audit.json`](ngb_source_audit.json) — official USGS NGB CSV record, assay-quality and footprint counts. The audit completed, but the frozen H46-A sample-count gates failed; no holdout was run.
- [`sgmc_source_audit.json`](sgmc_source_audit.json) — official USGS SGMC v1.1 archive checksums, schema/join report, projected polygon coverage and H46-B source-gate result. All source gates passed; this is not a holdout score.

The Actions summaries are the origin of these records: [NGB run 37446554478](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37446554478) and the latest pinned, polygon-only [SGMC run 37455479306](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479306). The sample-submission raster is an owner-supplied mirror and was inspected only for its finite footprint and grid metadata.
