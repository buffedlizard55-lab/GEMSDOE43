# GEMSDOE43 — GEMS geological-fault mapping research

> **Maximize P(Win). Own the Outcome.**

## Project brief

Develop and document genuinely new geological-fault hypotheses for the GEMS Prize Challenge, compare a viable candidate against a defined incumbent with spatially blocked testing, and only promote an artifact when preregistered evidence supports it. Never copy a sibling submission. Preserve exact source provenance, grid/format checks, a distinct artifact name and concise form note. A local public-catalogue transfer proxy is not validation against the organizer's private set of expert-labelled new faults, not a leaderboard score, and not proof of winning.

## Current decision — 2026-10-06

**H46-B did not pass its preregistered promotion gate. Do not submit the artifact below; no submission slot has been used or authorized.**

The source-only gate for H46-B passed using official USGS SGMC v1.1 California/Nevada geology polygons and same-release lithology/age tables. During final source review, the official ScienceBase item was found to recommend a newer 2026 GeMS release (DOI [10.5066/P1A3DQZK](https://doi.org/10.5066/P1A3DQZK)); this frozen test did not audit or silently substitute that data. The frozen v1.1 recipe was then evaluated once against the registered four-fold, 20 km block public-catalogue proxy. The unchanged H42 control reproduced all four historical DTI values exactly. H46-B's proxy mean was `0.251667` versus `0.250744` for H42 (`Δ=+0.000923`); it won **2/4** folds. The gate required `Δ≥+0.005` and at least 3/4 wins. It also required no fold worse than `−0.010`; the worst H46-B fold was `−0.000051`. Thus two of the four promotion checks passed, while the mean-improvement and win-count checks failed. **This is a public-catalogue proxy result only—not private-set validation and not a DrivenData score.**

The run generated a distinct GeoTIFF for reproducibility, not as a promoted submission:

- [Download the research-only GeoTIFF](docs/downloads/GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006.tif)
- **Name:** `GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006`
- **Size / SHA-256:** 381,558 bytes / `c51cf006c19f1993606a0b0b55467f0a74f0a1c13e747c3f592d55690d93a6f6`
- **Format checks:** one-band float32, 3,730 × 3,292, EPSG:32611, exact 100 m transform, 40,000 positive prediction pixels, inside-footprint values finite and in `[0,1]`, outside-footprint nodata `NaN`. The receipt and a separate local Rasterio/hash verification are linked below.
- **Submission status:** not cleared; do not upload. No private-set score, leaderboard score, or slot exists for this file.

The precise form note is [`submission/FORM-NOTE.txt`](submission/FORM-NOTE.txt); its warning is intentional. Conditional instructions for a future separately authorized artifact are in [`submission/INSTRUCTIONS.md`](submission/INSTRUCTIONS.md). No further H46-B tuning on these folds is authorized; a materially different recipe needs a new dated amendment and fresh confirmation regions.

## Hypotheses and research knowledge base

The original ranked slate contains three genuinely different evidence families. Its expected-DTI ranking was a **prior**, not a measurement; see [`research/PREREGISTRATION-2026-10-06.md`](research/PREREGISTRATION-2026-10-06.md) for the full recipes, costs and source gates, and the [public research knowledge base](knowledge-base.html) for a concise summary.

| Prior rank | Hypothesis | Prior expected proxy-DTI direction / implementation cost | Current evidence |
|---:|---|---|---|
| 1 | **H46-A — NGB stream-geochemistry pathfinder enrichment × TMI edge** | Highest relative prior; modest positive expectation but high uncertainty. Medium cost. | Stopped before scoring: official NGB source/coverage gates failed (451 eligible stream samples; 447 with at least three usable assays in the footprint, below frozen 1,000 / 500 gates). |
| 2 | **H46-B — SGMC lithology/age unit-contact contrast × TMI edge** | Low-to-moderate prior. Medium cost. | Source gates passed; public-catalogue blocked proxy returned mean `ΔDTI=+0.000923`, 2/4 wins; failed promotion gate. No slot. |
| 3 | **H46-C — persistent Landsat alteration margins × lineament agreement** | Low-to-moderate, less certain prior. High cost. | Not tested or source-verified. It was not silently substituted after H46-B. |

A source gate or proxy result is not evidence of private-set performance. The hypotheses are not calibrated to the private labels, and no public score is inferred.

## Evidence and reproducibility

- **H46-B holdout decision:** [dated amendment](research/AMENDMENT-2026-10-06-H46B-holdout.md); [Actions run `37455686781`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455686781).
- **Machine-readable experiment receipts:** [`evidence/h46b/experiment.json`](evidence/h46b/experiment.json), [`holdout.json`](evidence/h46b/holdout.json), [`data_manifest.json`](evidence/h46b/data_manifest.json), [`submission_receipt.json`](evidence/h46b/submission_receipt.json).
- **Official SGMC source audit:** [Actions run `37455479306`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479306), with [checked-in receipt](evidence/sgmc_source_audit.json). It verified the three pinned official archive hashes, all preregistered source gates, and did not open either Structure layer.
- **Frozen implementation tests/compile:** [Actions run `37455479404`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479404); 17 local unit/synthetic tests passed. These are engineering checks, not private-set validation.
- **Three release-review passes:** [`research/RELEASE-REVIEW-2026-10-06.md`](research/RELEASE-REVIEW-2026-10-06.md).

Competition feature and public-catalogue-label rasters came through integrity-pinned **owner-supplied mirrors**, not authenticated organizer originals. The checksums and that limitation are recorded in the data manifest. The sample template was used only for its grid/finite mask; the private challenge labels were not accessed.

## Score-attribution caution

The official DrivenData leaderboard displayed **0.2778 at rank #13** and **0.3345 at rank #1** when independently checked on **2026-10-06**. These are dated leaderboard-row observations only; no verified TIFF receipt/hash crosswalk ties the 0.2778 row to a file, and the 0.3345 observation likewise does not identify its file. The later link-review fetch returned a JavaScript “Loading” shell and a sandbox `curl` attempt failed TLS, so these figures are not presented as a refreshed current snapshot. See [`evidence/leaderboard_observation.json`](evidence/leaderboard_observation.json); do not attribute either number to this repository or a sibling artifact. [Open the official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

## Website and AI-use disclosure

The static public-site source is [`index.html`](index.html), with the [knowledge base](knowledge-base.html). GitHub Pages for this repository is configured at [`buffedlizard55-lab.github.io/GEMSDOE43`](https://buffedlizard55-lab.github.io/GEMSDOE43/); content from this branch is public only after it is merged and the Pages deployment completes.

AI coding assistance was used for source synthesis, implementation drafting, tests, experiment orchestration and documentation. The TIFF is a deterministic output of the documented numerical workflow, not a generative image or hand-labelled fault map. Sources, access caveats, code, hashes, fold results and the no-promotion decision are recorded here. No private challenge labels were accessed.

## Project map

- [`knowledge-base.html`](knowledge-base.html) — public research, ranked hypotheses, official sources, access caveats and decision record.
- [`research/PREREGISTRATION-2026-10-06.md`](research/PREREGISTRATION-2026-10-06.md) — original incumbent, spatial folds, thresholds and hypothesis recipes.
- [`research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md`](research/AMENDMENT-2026-10-06-NGB-stop-and-SGMC.md) — H46-A source-gate stop and H46-B source-audit authorization.
- [`research/AMENDMENT-2026-10-06-SGMC-table-archive.md`](research/AMENDMENT-2026-10-06-SGMC-table-archive.md) — official SGMC archive/table irregularity, hashes and source-only results.
- [`research/AMENDMENT-2026-10-06-H46B-holdout.md`](research/AMENDMENT-2026-10-06-H46B-holdout.md) — measured blocked-proxy outcome and no-promotion decision.
- [`research/RELEASE-REVIEW-2026-10-06.md`](research/RELEASE-REVIEW-2026-10-06.md) — three review passes and release checklist.
- [`data/README.md`](data/README.md) — raw-input handling and integrity policy.
- [`submission/INSTRUCTIONS.md`](submission/INSTRUCTIONS.md) and [`submission/FORM-NOTE.txt`](submission/FORM-NOTE.txt) — explicit do-not-upload status and conditional future instructions.

## Official sources

- [GEMS Prize Challenge rules and submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- H46-A source, stopped at its source gate: USGS [Open-File Report 2002-227 data](https://pubs.usgs.gov/of/2002/0227/data.html), [CSV](https://pubs.usgs.gov/of/2002/0227/ngb.csv), [metadata](https://pubs.usgs.gov/of/2002/0227/metadata.html), and [quality notes](https://pubs.usgs.gov/of/2002/0227/quality.html).
- H46-B source, audited: USGS [SGMC v1.1 download index](https://mrdata.usgs.gov/geology/state/), [data-release DOI 10.5066/F7WH2N65](https://doi.org/10.5066/F7WH2N65), [metadata](https://mrdata.usgs.gov/geology/state/USGS_SGMC_Metadata.html), and official [polygon](https://mrdata.usgs.gov/geology/state/about.php?tblname=geol_poly), [age](https://mrdata.usgs.gov/geology/state/about.php?tblname=age), and [lithology](https://mrdata.usgs.gov/geology/state/about.php?tblname=lith) field descriptions.

Raw inputs, private labels, credentials and runner scratch files do not belong in Git. See [`data/README.md`](data/README.md) and the experiment manifest for the acquisition route and integrity checks.
