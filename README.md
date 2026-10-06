# GEMSDOE43 — Auditable GEMS research and submission project

> **Start every project session by reading this README in full and then `PROMPT.md`.** The owner’s persistent brief is recorded below and in `PROMPT.md`. Do not discard the project’s Core Values: **Maximize P(Win)** and **Own the Outcome**.

**Current decision: NO-GO for a competition submission.** The H42 spatial holdout was independently reproduced, but G43-CG01 scored **0.211567 mean DTI** versus H42’s **0.250744** (0/4 fold wins). Separately, H46-B passed the source-only SGMC v1.1 audit but its preregistered public-catalogue proxy reached only **+0.000923 mean ΔDTI** and **2/4 fold wins**, below its +0.005 / 3-of-4 promotion gate. A research GeoTIFF was generated in the experiment runner, but after the gate failed it was removed from the current tree and is **not linked from the current project site**. An earlier public branch commit retains it, and the associated GitHub Actions artifact was still unexpired when checked; a deletion request returned HTTP 403 because the GitHub integration lacks permission. See [`evidence/h46b/publication_status.json`](evidence/h46b/publication_status.json) for the expiry/access caveat. No DrivenData upload occurred; no submission slot has been used or authorized. These are distinct local no-go results, not competition scores.

**Project site:** [GEMSDOE43 research overview](https://buffedlizard55-lab.github.io/GEMSDOE43/) (root entry redirects to the documented site in `docs/`; current download control is intentionally closed).

## Persistent owner brief (project charter)

Review and develop GEMSDOE43 into an auditable DOE GEMS research and submission project. Explain the reported H33-2-B2 result without presenting owner reports as organizer-confirmed scores; inspect the current official leaderboard; propose and rank 3–5 new geological hypotheses naming layers, targeted physical signatures, rationale for finding faults absent from the USGS/INGENIOUS catalogue, differences from prior approaches, expected improvement, cost, and any official external data needed. Validate the best candidate on the spatial holdout before using a submission slot. Aim to generate a genuinely unique, usable single-band GeoTIFF with an obvious download, unique submission name, short portal comment, and executive summary/submission guide. Include the user’s full project brief in README and treat it as the starting point each session. Research official sources, give review links, state limitations and irregularities, improve the research/system autonomously, run multiple implementation/review passes, and request a PR/merge only after work is verifiable.

### Non-negotiable execution rules

1. **New output only.** Do not copy, rename, or submit a previous GEMSDOE raster. Prior files and scores are evidence for analysis, not candidate inputs.
2. **No holdout win, no slot.** A candidate must strictly beat the current best spatially blocked holdout at equal mass, win at least 3/4 folds, and pass input, novelty, GeoTIFF, provenance, and rules checks. A local holdout does not forecast the organizer’s hidden score.
3. **Hypotheses before implementation.** Rank 3–5 new geological hypotheses before coding/scoring. For each document the exact layers, targeted physical signature, why it may reveal faults absent from the public USGS/INGENIOUS catalogue, difference from prior repository work, expected improvement, implementation cost, and official external-data availability. Timestamp the frozen candidate and parameters.
4. **Submission workflow when eligible.** Publish one valid single-band float32 GeoTIFF on the competition grid, an obvious one-click download, a unique filename/submission name, a short portal comment, plus an executive summary and submission guide close to the site entrance. Disclose any generative-AI use in the required narrative.
5. **Evidence and attribution.** Ground claims in official/trusted sources and provide review links. Verify claims against source text; keep organizer statements, owner reports, model estimates, and local measurements distinctly labeled. Record limits and irregularities rather than smoothing them over.
6. **Leaderboard terms.** The previous public snapshot is dated **2026-10-05** (rank 1: 0.3345); it was not refreshed on 2026-10-06. DrivenData’s Terms of Use prohibit automatic monitoring/copying and manual monitoring/copying without prior written consent. No scraper, poller, or refreshed copied snapshot may be added unless authorized API access or written permission exists. The official page is linked below for permitted browser review.
7. **Three release passes.** (1) Implement and run reproducible verification. (2) Review bugs, assumptions, leakage, edge cases, provenance, and portal risks; fix and rerun. (3) Recheck every requirement in this charter line by line, fix omissions, and rerun the full validation suite.
8. **PR discipline.** Request a PR/merge only after the work is verifiable. Do not claim a PR, merge, deployment, organizer score, or submission unless the corresponding official system confirms it.

For the full persistent owner instructions and active evidence state, see [`PROMPT.md`](PROMPT.md). The registered hypothesis slate is [`research/hypotheses.md`](research/hypotheses.md).

## Executive summary and current findings

- **Project goal:** build and validate algorithms that map geological faults indicative of geothermal resources, using public competition layers while accounting for incomplete known-fault labels.
- **Official task and output:** the organizer specifies a distance-weighted Tversky metric (α=0.2, β=0.8; triangular kernel with 300-m support) and a single-layer float32 GeoTIFF at EPSG:32611, 100-m resolution, same bounds, values in [0,1], null/NaN outside. Official task and rules say public leaderboard, private Phase 1, and expert-updated Phase 2 results differ. See [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [September 2026 Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- **Leaderboard:** last recorded historical observation is 2026-10-05 (rank 1: 0.3345). No current refresh is claimed; DrivenData’s Terms of Use restrict monitoring/copying without prior written consent. [Official leaderboard page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- **H33-2-B2:** GEMSDOE32 PR #9 describes it as pruning 2,545 catalogue-adjacent pixels from a 40,199-pixel owner-reported B=1 base, leaving 37,654 pixels. The owner reports a calibrated four-fold mean of 0.2679205 and a separate **model-projected** live value 0.2746732 (rounded to 0.2747) from owner-reported leaderboard anchors. The PR explicitly says no organizer score exists. Read [`research/h33_result_review.md`](research/h33_result_review.md) and [PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9); do not cite 0.2747 as an official score.
- **Inputs:** four raster files were restored and hash-verified against prior-project GitHub manifests. This verifies mirror integrity, **not** organizer provenance. See [`registry/data_sources.json`](registry/data_sources.json), [`evidence/data_restore_receipt.json`](evidence/data_restore_receipt.json), and [`research/data_access.md`](research/data_access.md).
- **IR-DATA-01:** the mirrored `sample_submission.tif` has 60,988 pixels equal to 1, matching every positive pixel in the mirrored labels. This conflicts with the task page’s description of an absence template. G43 uses the sample only for grid/footprint and never copies its prediction values. Full measurements are in [`evidence/input_audit.json`](evidence/input_audit.json).
- **H42 baseline:** G43 independently reproduced the owner-reported four-colour, 20-km spatial holdout. For `SH_basin_strong|sep4.0|N40000`, all four fold scores and summary match the saved owner report within 1e-6: mean 0.250744, min 0.242272, max 0.258025. This is a **local catalogue holdout score**, not a public or private competition score. The H42 LiDAR layer is an owner mirror used for this baseline only.
- **G43-CG01:** preregistered multiscale cross-gradient concordance between RTP magnetics and isostatic gravity scored mean 0.211567, min 0.204019. It lost to H42 in all four folds, so it fails the promotion gate. It is not made downloadable and no slot should be used for it.
- **H46-A:** official USGS Northern Great Basin stream geochemistry failed its preregistered source-coverage gates (451 eligible in-footprint stream samples; 447 with at least three usable assays versus 1,000 / 500 required). It stopped before holdout scoring.
- **H46-B:** official USGS SGMC v1.1 polygon/table source gates passed. Its frozen map-unit contact × TMI-edge recipe was compared once with H42 on the registered four 20-km public-catalogue blocks: H42 mean DTI 0.250744; H46-B 0.251667; mean Δ +0.000923; 2/4 wins; worst fold −0.000051. H42 reproduced all prior folds exactly. The +0.005 mean and ≥3/4 win gates failed, so H46-B is not promoted. A unique file was generated by the runner and format/hash-checked, but the failed candidate is **not offered as a download or submission**. See [`research/AMENDMENT-2026-10-06-H46B-holdout.md`](research/AMENDMENT-2026-10-06-H46B-holdout.md) and [`evidence/h46b/`](evidence/h46b/); these are public-catalogue proxy metrics, not private-set or leaderboard scores.
- **H46 source-version caveat:** the official SGMC catalog now recommends a newer 2026 GeMS release ([DOI 10.5066/P1A3DQZK](https://doi.org/10.5066/P1A3DQZK)). H46-B used preregistered, hash-pinned 2017 v1.1 archives only; the newer release was not fetched or audited. Any future source change needs a new source gate and fresh confirmation folds.
- **Unknown-test uncertainty:** DrivenData staff have said they will not share the sources, fault types, or coverage used for hidden test faults ([staff reply](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7)). The blocked catalogue holdout is therefore a necessary screen—not a forecast of hidden-score performance.

### Top priority / next research decision

Do not weaken the G43-CG01 gate or turn a failed candidate into a submission. If continuing, pick the next candidate from the ranked slate, preregister its operator and expected-value rationale before scoring, then compare it to the locally reproduced H42 arm at equal mass on the same frozen protocol. Any candidate that fails remains a no-go. The per-hypothesis details and external-data gaps are in [`research/hypotheses.md`](research/hypotheses.md).

## Reproducible workflow

This checkout's local virtual environment is `.venv/` (ignored by Git). From the repository root:

```bash
# One-time environment setup (Python 3.11+).
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Restore inputs from pinned owner-maintained mirrors; hashes do not authenticate the organizer source.
bash scripts/download_competition_data.sh

# Recompute metadata, masks, hashes, band coverage, and documented irregularities.
.venv/bin/python scripts/audit_inputs.py

# Run the 12 unit tests (including metric-vs-brute-force, synthetic cross-gradient, and static-site checks).
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v

# Reproduce H42 and evaluate preregistered G43-CG01 against the same four spatial folds.
PYTHONPATH=src .venv/bin/python scripts/run_holdout.py
```

Dependencies are listed in [`requirements.txt`](requirements.txt). The full spatial run takes about one minute on the checked environment. The audit writes `evidence/input_audit.json`; holdout results are written to `evidence/holdout_g43_cg01.json`. Raw rasters are git-ignored and are not redistributed by this repository.

## Working site and research navigation

- **Landing page / executive status:** [`docs/index.html`](docs/index.html) — the submission download remains disabled because no candidate passes the gate.
- **Executive summary and no-go decision:** [`docs/executive-summary.html`](docs/executive-summary.html).
- **Hypotheses and candidate decision:** [`docs/hypotheses.html`](docs/hypotheses.html), backed by [`research/hypotheses.md`](research/hypotheses.md) and the H46 amendments.
- **Supplemental H46 research/source knowledge base:** [`knowledge-base.html`](knowledge-base.html).
- **H46-B holdout decision:** [`research/AMENDMENT-2026-10-06-H46B-holdout.md`](research/AMENDMENT-2026-10-06-H46B-holdout.md); no-go publication status: [`evidence/h46b/publication_status.json`](evidence/h46b/publication_status.json).
- **Data access and irregularities:** [`research/data_access.md`](research/data_access.md).
- **Source register and line-by-line claim attribution:** [`research/source_register.md`](research/source_register.md).
- **H33-2-B2 attribution review:** [`research/h33_result_review.md`](research/h33_result_review.md).
- **Reproducibility receipts:** [`evidence/holdout_g43_cg01.json`](evidence/holdout_g43_cg01.json) and [`evidence/h46b/holdout.json`](evidence/h46b/holdout.json).

## Evidence and policy links

1. [Official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — target, layers, metric, and output format.
2. [GEMS Prize Official Rules (September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — registration, GeoTIFF, AI disclosure, and private/final evaluation requirements.
3. [DrivenData staff scoring clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) — known-catalogue mask.
4. [DrivenData staff note on hidden-test information](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) — sources, fault types and coverage not disclosed.
5. [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) — leaderboard-access boundary.
6. [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — dynamic; no refreshed score is asserted here.
7. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [ScienceBase conductance product](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b), and [USGS FDSN](https://earthquake.usgs.gov/fdsnws/event/1/) — official external-data sources reviewed for the slate, with unresolved coverage noted.
8. [Organizer-linked GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — supervised U-Net/ResNet18 example using random patch MC-CV; a different method family from CG01 and not reproduced or score-compared here.

## Code map

```text
PROMPT.md                         persistent owner brief and current evidence state
README.md                         this charter, runbook, status and navigation
AGENTS.md                         future-session requirements to read the charter first
index.html                        root GitHub Pages redirect to docs/index.html
registry/data_sources.json       source pins and provenance caveats
registry/experiment.json         preregistered G43-CG01 operator and gate
research/hypotheses.md           ranked 5-hypothesis slate and result
research/data_access.md          input, licensing and sample irregularity audit
research/source_register.md      source-by-source claim attribution
research/h33_result_review.md   owner-projection explanation and limits
scripts/audit_inputs.py          raster, hash, footprint and irregularity receipt
scripts/run_holdout.py           H42 reproduction and G43-CG01 holdout
src/gemsdoe43/                    metric, I/O, H42 baseline, packing and CG01 code
tests/                             offline and synthetic correctness tests
evidence/                          machine-readable input, validation and no-go receipts
docs/                              user-facing site; no failed candidate download
```
