# Data intake policy

Raw competition and external source files are deliberately not committed. Do not put data files, credentials, private organizer labels, or submission tokens in Git.

- The USGS NGB geochemistry source, exact official URL, metadata caveats and preregistered processing are recorded in [`../research/PREREGISTRATION-2026-10-06.md`](../research/PREREGISTRATION-2026-10-06.md).
- Use `.github/workflows/fetch-nbg.yml` only to retrieve the official CSV as a short-lived GitHub Actions artifact. The job prints the downloaded bytes, row count and SHA-256; the artifact expires after one day. Do not commit the CSV.
- Competition mirrors are owner-supplied and integrity-pinned, not organizer-authenticated. Their exact paths, hashes and caveats will be recorded in `evidence/data_manifest.json` if needed for the reproducible holdout.
- Ignored local inputs belong under `data/raw/`; derived scratch products belong under `data/work/`. Do not place scratch products or raw inputs in `docs/downloads/`.
