# Local input data

Place the competition files in this directory by running `bash scripts/download_competition_data.sh`.
The script restores hash-pinned, owner-published mirrors through the GitHub CLI; this is **not** an authenticated DrivenData download and the pins prove mirror consistency, not organizer provenance. The official competition data page requires DrivenData login. See `registry/data_sources.json` and `research/data_access.md` for the exact source paths, hashes, and limitations.

Raw rasters are git-ignored and must not be committed. Only a candidate that passes the registered holdout, novelty, provenance, format, and rules gates may be published in `docs/downloads/`. At present no candidate passes, so that directory contains no submission GeoTIFF.
