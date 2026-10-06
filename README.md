# GEMSDOE43 — GEMS geological-fault mapping research

> **Maximize P(Win). Own the Outcome.**

## Project brief

Develop one genuinely new, reproducible geological-fault detector and, only if the evidence supports it, deliver a unique, easy-to-download GeoTIFF for the GEMS Prize Challenge. Do not copy a sibling submission. State the hypothesis, source provenance and caveats; compare it with a clearly defined incumbent using spatially blocked validation before considering a submission slot. A local catalogue-transfer proxy is not validation against the organizer's private test set, a leaderboard score, or proof of winning.

The project also maintains a clean public website with an explicit executive summary and a linked research, hypothesis, and source knowledge base. Any deliverable must include a distinct submission name, short form note, unambiguous upload instructions, and the required AI-use disclosure. The GeoTIFF must preserve the official grid, CRS, transform and dimensions, be one-band float32 with inside-footprint values in `[0,1]`, and represent outside-footprint cells correctly as nodata. No file may be described as validated or scored without the corresponding evidence. Link claims to trusted sources and manually review links. Review code and public claims in three passes before release.

## Current status — 2026-10-06

- The original leading idea, **H46-A** (USGS Northern Great Basin stream-sediment pathfinder enrichment), failed its preregistered source-coverage gates and was stopped **before holdout scoring**. The official CSV was retrieved and hashed; only 451 eligible stream samples and 447 samples with at least three usable assays intersect the competition footprint, below the frozen 1,000/500 thresholds. See [`research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md`](research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md) and the official-source check summary for Actions run `37446554478`.
- **H46-B** (map-unit lithology/age contacts that coincide with a magnetic edge, used only as auxiliary evidence on the H42-style incumbent) is the next hypothesis authorized for a **source-only audit**, not yet approved for a holdout. Direct CA/NV state archives were retrieved and hashed, but the first audit stopped because those ZIPs do not contain the standard `age.csv`; no polygon coverage was calculated. A follow-up now adds the official same-release SGMC all-state table archive before the source gates can be evaluated. See both SGMC amendments below.
- No candidate GeoTIFF has been generated, no H46-A or H46-B holdout has run, no submission slot has been spent, and no candidate is currently validated or scored. The source-audit workflow reads only the sample-template finite mask/grid, never its pixel values or labels.
- The public website, completed source audit, README-linked evidence, final form note, and submission artifact remain to be completed. See [`research/PREREGISTRATION-2026-10-06.md`](research/PREREGISTRATION-2026-10-06.md) and the amendments in `research/` for the frozen protocol and subsequent decisions.

## Evidence and score-attribution caution

The official DrivenData leaderboard displayed **0.2778 at rank #13** and **0.3345 at rank #1** when independently checked on **2026-10-06**. These are leaderboard-row observations only: there is no verified TIFF receipt/hash crosswalk tying the 0.2778 row to a particular file. The 0.3345 observation likewise does not identify the file that earned it. Do not infer that either score belongs to this repository or to a particular sibling artifact. [Open the official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

## Session-start and release discipline

At the start of every project session:

1. Read this README and the current preregistration plus the latest dated amendment.
2. Check `git status`, confirm the session branch is `arena/7bd177bc-gemsdoe43`, and inspect the newest source/experiment evidence before doing work.
3. Do not repeat a failed audit unchanged, rerun a failed source gate as if it passed, or silently replace a hypothesis/source. File and review a dated amendment before a materially new experiment.
4. Run tests, format/grid/independence checks, and the three review passes before release. Open a PR and merge only when the actual diff and checks are ready; report the PR/merge only if GitHub confirms it.

## Research map

- [`research/PREREGISTRATION-2026-10-06.md`](research/PREREGISTRATION-2026-10-06.md) — initial ranked hypothesis slate, H42 comparator, blocked-fold protocol, and promotion/stop rules.
- [`research/AMENDMENT-2026-10-06-assays.md`](research/AMENDMENT-2026-10-06-assays.md) — locked H46-A assay-method choice.
- [`research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md`](research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md) — official NGB coverage failure and explicit H46-B source-audit amendment.
- [`research/AMENDMENT-2026-10-06-SGMC-table-archive.md`](research/AMENDMENT-2026-10-06-SGMC-table-archive.md) — CA/NV download receipts and the missing-age-table correction.
- [`data/README.md`](data/README.md) — raw-input handling and integrity policy.
- [`docs/`](docs/) — public project website and the reviewed, downloadable candidate (to be added only after the source and validation decisions are complete).

## Trusted source links

- Official competition: [GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- Official H46-A source, stopped at the source gate: [USGS Open-File Report 2002-227 CSV](https://pubs.usgs.gov/of/2002/0227/ngb.csv), [metadata](https://pubs.usgs.gov/of/2002/0227/metadata.html), and [quality notes](https://pubs.usgs.gov/of/2002/0227/quality.html).
- Official H46-B source, pending byte and coverage verification: [USGS SGMC download index](https://mrdata.usgs.gov/geology/state/) and [data release DOI](https://doi.org/10.5066/F7WH2N65).

Competition input rasters in this repository's research workflow are integrity-pinned owner-supplied mirrors, not organizer-authenticated originals. The acquisition scripts and experiment receipts must preserve that distinction. Raw inputs, private labels, credentials, and scratch products do not belong in Git.
