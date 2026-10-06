# GEMSDOE43 — Auditable GEMS research and submission project

> **Start every project session by reading this README in full and then `PROMPT.md`.** The owner’s persistent brief is recorded below and in `PROMPT.md`. Do not discard the project’s Core Values: **Maximize P(Win)** and **Own the Outcome**.

**Current decision: SLOT-ELIGIBLE (live-UNSCRED).** The round-2 supervised ranker SUP01
(HGB on 21 features + sep-4.0 packing, 40,000 dots) beat the reproduced H42 baseline
**0.262666 vs 0.250744 (+0.011922)** with **4/4 fold wins** on the frozen 20-km
spatial holdout, passed the corrected gate, format audit, and novelty audit
(Jaccard ≈ 0.01 vs three prior layouts). The submission GeoTIFF is packaged with a
one-click download, unique name, portal note, and narrative draft. No organizer score
exists for it; the holdout does not forecast public/private scores.

**Download:** [`docs/downloads/gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan.tif`](docs/downloads/gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan.tif)
(sha256 `41216d099db0e077…9c38`) · [fallback twin](docs/downloads/gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-zeros.tif) ·
[submission guide](docs/executive-summary.html) · name `GEMSDOE43-SUP01-HGB21-SE40`.

**Project site:** [GEMSDOE43 research overview](https://buffedlizard55-lab.github.io/GEMSDOE43/) (root entry redirects to the documented site in `docs/`).

## Persistent owner brief (project charter)

Review and develop GEMSDOE43 into an auditable DOE GEMS research and submission project. Explain the reported H33-2-B2 result without presenting owner reports as organizer-confirmed scores; inspect the current official leaderboard; propose and rank 3–5 new geological hypotheses naming layers, targeted physical signatures, rationale for finding faults absent from the USGS/INGENIOUS catalogue, differences from prior approaches, expected improvement, cost, and any official external data needed. Validate the best candidate on the spatial holdout before using a submission slot. Aim to generate a genuinely unique, usable single-band GeoTIFF with an obvious download, unique submission name, short portal comment, and executive summary/submission guide. Include the user’s full project brief in README and treat it as the starting point each session. Research official sources, give review links, state limitations and irregularities, improve the research/system autonomously, run multiple implementation/review passes, and request a PR/merge only after work is verifiable.

A standing owner directive further requires solving placement as a formal covering
optimization (Church–ReVelle MCLP with submodular greedy) instead of sweeping spacing
constants, then verifying the layout is not a near-duplicate of any prior submission.
G43 implemented that program exactly — and the frozen holdout falsified it on these
surfaces (see findings). The directive's evidence (code, tests, receipts, mechanism
analysis) is preserved; the shipped file follows the validated placer.

### Non-negotiable execution rules

1. **New output only.** Do not copy, rename, or submit a previous GEMSDOE raster. Prior files and scores are evidence for analysis, not candidate inputs. The shipped layout shares ~2% of dots with any checked prior.
2. **No holdout win, no slot.** A candidate must strictly beat the current best spatially blocked holdout at equal mass, win at least 3/4 folds (3/3 of clean folds for post-exploration arms), and pass input, novelty, GeoTIFF, provenance, and rules checks. A local holdout does not forecast the organizer’s hidden score.
3. **Hypotheses before implementation.** Rank 3–5 new geological hypotheses before coding/scoring. For each document the exact layers, targeted physical signature, why it may reveal faults absent from the public USGS/INGENIOUS catalogue, difference from prior repository work, expected improvement, implementation cost, and official external-data availability. Timestamp the frozen candidate and parameters. Amendments before scoring must be timestamped with a selection-corrected gate.
4. **Submission workflow when eligible.** Publish one valid single-band float32 GeoTIFF on the competition grid, an obvious one-click download, a unique filename/submission name, a short portal comment, plus an executive summary and submission guide close to the site entrance. Disclose any generative-AI use in the required narrative.
5. **Evidence and attribution.** Ground claims in official/trusted sources and provide review links. Verify claims against source text; keep organizer statements, owner reports, model estimates, and local measurements distinctly labeled. Record limits and irregularities rather than smoothing them over.
6. **Leaderboard terms.** The previous public snapshot is dated **2026-10-05** (rank 1: 0.3345); it was not refreshed on 2026-10-06. DrivenData’s Terms of Use prohibit automatic monitoring/copying and manual monitoring/copying without prior written consent. No scraper, poller, or refreshed copied snapshot may be added unless authorized API access or written permission exists. The official page is linked below for permitted browser review. Competing historical claims (0.3195, 0.3262) are flagged unresolved (IR-REPORT-02).
7. **Three release passes.** (1) Implement and run reproducible verification. (2) Review bugs, assumptions, leakage, edge cases, provenance, and portal risks; fix and rerun. (3) Recheck every requirement in this charter line by line, fix omissions, and rerun the full validation suite.
8. **PR discipline.** Request a PR/merge only after the work is verifiable. Do not claim a PR, merge, deployment, organizer score, or submission unless the corresponding official system confirms it.

For the full persistent owner instructions and active evidence state, see [`PROMPT.md`](PROMPT.md). The hypothesis slates are [`research/hypotheses.md`](research/hypotheses.md) (round 1) and [`research/hypotheses_round2.md`](research/hypotheses_round2.md) + [`research/amendment_round2b.md`](research/amendment_round2b.md) (round 2).

## Executive summary and current findings

- **Project goal:** build and validate algorithms that map geological faults indicative of geothermal resources, using public competition layers while accounting for incomplete known-fault labels.
- **Official task and output:** the organizer specifies a distance-weighted Tversky metric (α=0.2, β=0.8; triangular kernel with 300-m support) and a single-layer float32 GeoTIFF at EPSG:32611, 100-m resolution, same bounds, values in [0,1], null/NaN outside. Official task and rules say public leaderboard, private Phase 1, and expert-updated Phase 2 results differ. See [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [September 2026 Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- **Leaderboard:** last recorded historical observation is 2026-10-05 (rank 1: 0.3345). No current refresh is claimed; DrivenData’s Terms of Use restrict monitoring/copying without prior written consent. [Official leaderboard page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Competing historical claims are flagged in [`research/mclp_strategy.md`](research/mclp_strategy.md) (IR-REPORT-02).
- **H33-2-B2:** GEMSDOE32 PR #9 describes it as pruning 2,545 catalogue-adjacent pixels from a 40,199-pixel owner-reported B=1 base, leaving 37,654 pixels. The owner reports a calibrated four-fold mean of 0.2679205 and a separate **model-projected** live value 0.2746732 (rounded to 0.2747) from owner-reported leaderboard anchors. The PR explicitly says no organizer score exists. A conflicting owner-brief report of 0.2778 is flagged (IR-REPORT-01). Read [`research/h33_result_review.md`](research/h33_result_review.md) and [PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9); do not cite 0.2747 or 0.2778 as an official score.
- **Scoring economics:** each unit of emitted mass adds exactly 0.2 to the DTI denominator, so a marginal dot must earn credit above 0.2·DTI (≈0.052 at DTI 0.26). This bar explains the dotted-file lineage (121k→60k→44k→40k→37.6k dots) and prices future prunes. Derivation in [`research/mclp_strategy.md`](research/mclp_strategy.md).
- **Inputs:** four raster files were restored and hash-verified against prior-project GitHub manifests. This verifies mirror integrity, **not** organizer provenance. See [`registry/data_sources.json`](registry/data_sources.json), [`evidence/data_restore_receipt.json`](evidence/data_restore_receipt.json), and [`research/data_access.md`](research/data_access.md).
- **IR-DATA-01:** the mirrored `sample_submission.tif` has 60,988 pixels equal to 1, matching every positive pixel in the mirrored labels. This conflicts with the task page’s description of an absence template. G43 uses the sample only for grid/footprint and never copies its prediction values. Full measurements are in [`evidence/input_audit.json`](evidence/input_audit.json).
- **H42 baseline:** G43 independently reproduced the owner-reported four-colour, 20-km spatial holdout twice (rounds 1 and 2, drift guard PASS): mean 0.250744 for `SH_basin_strong|sep4.0|N40000`. This is a **local catalogue holdout score**, not a public or private competition score.
- **Round-1 G43-CG01:** preregistered cross-gradient concordance scored mean 0.211567 (0/4 folds). Rejected; not shipped.
- **Round-2 MCLP (owner-directed placement program):** exact lazy-greedy maximum expected coverage (Church–ReVelle, (1−1/e) for surface coverage, brute-force-verified solver) scored 0.211122 on the H42 surface and 0.150107 on MG01 — 0/4 wins each. Seven demand variants also failed on fold-0 exploration. Verdict: optimal covering of a miscalibrated surface loses to fixed packing; placement is downstream of probability quality. Independently replicates GEMSDOE28's H37-1 LOSFO lesson. Preserved in [`research/amendment_round2b.md`](research/amendment_round2b.md) and [`research/mclp_strategy.md`](research/mclp_strategy.md).
- **Round-2 MG01 / ENS01:** triple-gradient surface + packing 0.205756 (0/4); 50/50 SH/MG01 ensemble + packing 0.241241 (0/3 clean folds). Rejected.
- **Round-2 SUP01 (PRIMARY):** per-fold histogram gradient boosting on 21 features (19 bands + scarp evidence + validity flag; no coordinates; training-block labels only) + sep-4.0 packing at N=40,000. Mean **0.262666** (+0.011922), 4/4 folds; corrected gate (folds 1–3): 3/3, mean 0.263590 vs 0.253568. Slot-eligible; live-UNSCRED.
- **Submission:** `gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan.tif` (40,000 dots, none within 200 m of the catalogue; NaN outside; audits PASS) plus an all-finite `-zeros` twin. Novelty: Jaccard ≈ 0.011 vs each of three hash-verified priors (d2.8, H36-1, H33-2-B2). Name `GEMSDOE43-SUP01-HGB21-SE40`; 152-char portal note and narrative draft on the [submission guide](docs/executive-summary.html).
- **Unknown-test uncertainty:** DrivenData staff have said they will not share the sources, fault types, or coverage used for hidden test faults ([staff reply](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7)). The blocked catalogue holdout is therefore a necessary screen—not a forecast of hidden-score performance.

### Top priority / next research decision

Submit the SUP01 file (one slot), then use the live score to calibrate the mass operating point (0.2·DTI bar). Next detector work, in order: calibrated SUP01 + MCLP (the principled untested combination), corroborated above-bar additions (heat-flow/Euler family), and the untouched backup hypotheses (BG01/GT01/SC01/CH01/SEIS01/RAD01/MT01), each preregistered before scoring. Do not weaken any failed arm's gate post hoc.

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

# Run the 30 unit tests (metric-vs-brute-force, MCLP-vs-enumeration, surfaces,
# HGB-helper equivalence, synthetic cross-gradient, static-site checks).
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v

# Round-1 holdout: reproduce H42 and evaluate preregistered G43-CG01.
PYTHONPATH=src .venv/bin/python scripts/run_holdout.py

# Round-2 holdout: MCLP/MG01/SUP01/ensemble arms with drift guard (~15 min; CPU HGB).
PYTHONPATH=src .venv/bin/python scripts/run_holdout_mclp.py

# Build the winning full-footprint submission + independent audits (~6 min, 4 GB RAM).
PYTHONPATH=src:scripts .venv/bin/python scripts/build_submission.py
```

Dependencies are listed in [`requirements.txt`](requirements.txt) (adds `scikit-learn==1.9.1` for SUP01, CPU-only). The audits write `evidence/input_audit.json`; holdout receipts are `evidence/holdout_g43_cg01.json` and `evidence/holdout_g43_mclp.json`; the builder writes `docs/downloads/` plus per-file audit receipts. Raw rasters are git-ignored and are not redistributed by this repository; the shipped submission TIFs (~620 KB total) are committed for the GitHub Pages download.

## Working site and research navigation

- **Landing page / download:** [`docs/index.html`](docs/index.html) — one-click submission download with hash, fallback twin, and audit receipts.
- **Executive summary and submission guide:** [`docs/executive-summary.html`](docs/executive-summary.html) — decision memo, exact upload steps, portal note, narrative draft with AI disclosure.
- **Hypotheses and candidate decisions:** [`docs/hypotheses.html`](docs/hypotheses.html), backed by [`research/hypotheses.md`](research/hypotheses.md), [`research/hypotheses_round2.md`](research/hypotheses_round2.md), and [`research/amendment_round2b.md`](research/amendment_round2b.md).
- **Validation record:** [`docs/research.html`](docs/research.html) — H42 reproduction, round-1/2 holdouts, MCLP falsification, credit-bar analysis, submission record.
- **Placement strategy memo:** [`research/mclp_strategy.md`](research/mclp_strategy.md) — why dotted/pruned files won, what beating the leaders requires, MCLP verdict, flagged report conflicts.
- **Data access and irregularities:** [`research/data_access.md`](research/data_access.md).
- **Source register and line-by-line claim attribution:** [`research/source_register.md`](research/source_register.md).
- **H33-2-B2 attribution review:** [`research/h33_result_review.md`](research/h33_result_review.md).
- **Reproducibility receipts:** [`evidence/holdout_g43_cg01.json`](evidence/holdout_g43_cg01.json), [`evidence/holdout_g43_mclp.json`](evidence/holdout_g43_mclp.json).

## Evidence and policy links

1. [Official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — target, layers, metric, and output format.
2. [GEMS Prize Official Rules (September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — registration, GeoTIFF, AI disclosure, and private/final evaluation requirements.
3. [DrivenData staff scoring clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) — known-catalogue mask.
4. [DrivenData staff note on hidden-test information](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) — sources, fault types and coverage not disclosed.
5. [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) — leaderboard-access boundary.
6. [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — dynamic; no refreshed score is asserted here.
7. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [ScienceBase conductance product](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b), and [USGS FDSN](https://earthquake.usgs.gov/fdsnws/event/1/) — official external-data sources reviewed for the slate, with unresolved coverage noted.
8. [Organizer-linked GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — supervised U-Net/ResNet18 example using random patch MC-CV; a different method family and validation design from SUP01's blocked per-fold boosting.
9. [Church & ReVelle (1974) retrospective](https://journals.sagepub.com/doi/abs/10.1177/0160017615600222), [Nemhauser–Wolsey–Fisher summary](http://chekuri.cs.illinois.edu/talks/crm_submodular.pdf), [Minoux lazy-greedy docs](https://submodlib.readthedocs.io/en/latest/optimizers/lazyGreedy.html) — placement-theory citations for the MCLP experiment.

## Code map

```text
PROMPT.md                         persistent owner brief and current evidence state
README.md                         this charter, runbook, status and navigation
AGENTS.md                         future-session requirements to read the charter first
index.html                        root GitHub Pages redirect to docs/index.html
registry/data_sources.json       source pins and provenance caveats
registry/experiment.json         preregistered G43-CG01 operator and gate (round 1)
registry/experiment_g43_mclp.json preregistered MCLP/MG01 + round-2b amendment (round 2)
research/hypotheses.md           ranked round-1 slate and result
research/hypotheses_round2.md    ranked round-2 slate (MCLP01/MG01/BG01/GT01/SC01)
research/amendment_round2b.md    MCLP falsification log + SUP01/ENS01 backup + corrected gate
research/mclp_strategy.md        credit-bar economics, H33 analysis, MCLP verdict, next paths
research/data_access.md          input, licensing and sample irregularity audit
research/source_register.md      source-by-source claim attribution
research/h33_result_review.md   owner-projection explanation and limits
scripts/audit_inputs.py          raster, hash, footprint and irregularity receipt
scripts/run_holdout.py           H42 reproduction and G43-CG01 holdout (round 1)
scripts/run_holdout_mclp.py      round-2 holdout: MCLP/MG01/SUP01/ensemble + drift guard
scripts/build_submission.py      full-footprint winning-arm build into docs/downloads/
scripts/audit_submission.py      independent format + novelty audit (portal contract)
src/gemsdoe43/                    metric, I/O, H42 baseline, packing, MCLP, surfaces, SUP01
tests/                             offline, synthetic and site-consistency tests (30)
evidence/                          machine-readable input, validation and release receipts
docs/                              user-facing site + audited submission downloads
```
