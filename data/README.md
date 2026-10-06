# Data intake policy

Raw competition and external source files are deliberately not committed. Do not put data files, credentials, private organizer labels, or submission tokens in Git.

- The USGS NGB geochemistry source, exact official URL, metadata caveats and preregistered processing are recorded in [`../research/PREREGISTRATION-2026-10-06.md`](../research/PREREGISTRATION-2026-10-06.md). Its official source gate failed on footprint counts; see the NGB stop amendment. Do not run H46-A's holdout.
- H46-B uses the official USGS SGMC v1.1 California/Nevada polygons and the same-release all-state age/lithology tables. Their verified byte counts and SHA-256 values are pinned in `scripts/download_sgmc.sh`; run `bash scripts/download_sgmc.sh` to store the archives under ignored `data/raw/external/sgmc/`. The source-only coverage audit is `.github/workflows/audit-sgmc.yml`. The audit passed without reading labels or sample-template pixel values; see the dated SGMC amendments.
- The pinned owner-mirrored sample template, features, public-catalogue labels and LiDAR are restored with `scripts/download_inputs.sh`. The competition mirrors are integrity-pinned, not organizer-authenticated. Do not commit the raw rasters or SGMC archives.
- The completed H46-B proxy run records exact paths, byte counts, SHA-256 values and provenance caveats in [`../evidence/h46b/data_manifest.json`](../evidence/h46b/data_manifest.json). The private challenge labels were not accessed; the public catalogue labels were used only for the registered proxy fold/guard/DTI operations.
- Ignored local inputs belong under `data/raw/`; derived scratch products belong under `data/work/`. Do not place scratch products or raw inputs in `docs/downloads/`.
