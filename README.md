# GEMSDOE43 — Auditable GEMS research and submission project

> **Start every project session by reading this README in full and then `PROMPT.md`.** The owner’s standing brief is reproduced verbatim below; the project’s Core Values are **Maximize P(Win)** and **Own the Outcome**.

**Current decision (2026-10-06 merge of PR #3 + PR #4): two slot-track files, one primary.**

- **PRIMARY — SUP01:** `docs/downloads/gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan.tif` (40,000 dots; sha256 `41216d099db0e077…9c38`). The only shipped layout whose **exact emission family** was validated at equal mass on the frozen protocol: **0.262666 vs H42 0.250744 (+0.011922), 4/4 folds**. Reproducible build. Live-UNSCRED. Name `GEMSDOE43-SUP01-HGB21-SE40`.
- **ALTERNATIVE — MCLP sup_oof:** `docs/downloads/gemsdoe43-mclp-supoof-51053-20261006T114256Z-zeros.tif` (51,053 dots; sha256 `63c9239a7eb473c3…`). Validated **prior** (0.286388 sep-3.0 packing, 4/4 folds) but the shipped maximal-covering **placement was never scored at equal mass**, and its channel stack + OOF surface were lost with `.cache/` (irreproducible until rebuilt). Live-UNSCRED. Name `GEMSDOE43-MCLP-sup_oof-51053`.

The two layouts are mutually distinct (Jaccard 0.011). Full decision record: `evidence/submission_status.json` (`primary_release` + `decision`), [submission guide](docs/executive-summary.html), [MCLP-line detail](docs/mclp-line.html).

**Project site:** [GEMSDOE43 research overview](https://buffedlizard55-lab.github.io/GEMSDOE43/) (root entry redirects to the documented site in `docs/`).

## Standing owner brief (verbatim)

The following is the owner's standing brief for this project. It is reproduced so that every session starts from the same target. (Stale score claims inside it are flagged where they occur; see IR-43-001/IR-43-010 and the leaderboard note.)

> Review the repo.
>
> **THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!**
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. The submission must be different than the collection of gemsdoe sites below.
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.
>
> **Stop guessing spacing constants — solve the actual placement optimization.** Your own data already shows this matters: every "d2-8"-labeled variant beats its "d1-5" sibling, and GEMSDOE32's best result is itself just one more hand-picked constant. The underlying problem has a name and a formal solution: Church and ReVelle's Maximal Covering Location Problem (Papers in Regional Science, 1974) asks exactly this question — given a fixed number of points and a coverage radius, which locations maximize the demand covered — and it maps onto this competition's scoring almost exactly, since DTI's true-positive credit is a max over the same kind of fixed radius (300 m) around each predicted point. Don't sweep spacing constants; solve the covering problem directly on your continuous probability surface using the submodular greedy algorithm Church and ReVelle describe, which carries a proven (1 − 1/e) ≈ 63% worst-case guarantee relative to the true optimum — a formal floor no hand-picked spacing constant carries. Normalize to [0,1], write the required single-band float32 GeoTIFF (EPSG:32611, 100 m, matching shape/geotransform, NaN outside the footprint), and verify the chosen point set isn't a near-duplicate of any prior submission's layout before presenting it for download.
>
> … **WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMSDOE SITE** — `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778` — **Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?**
>
> Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. **No hallucinations.** Verify no hallucinations.
>
> **0.3195 is the highest score right now** so we need to design a new strategy … We need to come up with distinct and unique strategies to score higher in this competition leaderboard. We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents. …
>
> Put this prompt into the repo readme and read it everytime we work on the project as a starting point …
>
> We need to focus on being able to generate a submission into the competition. The site should be able to generate a TIF file that is required for submission. It should be as easy as download to click a File to submit into the competition. This needs to be in the executive summary or the very beginning of the site. It should be obvious when you visit the site.
>
> I tried to submit the document that i downloaded from the site but it returned this error on the submission form: **"Predicted values must be in range [0, 1]"**. Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later.
>
> Create a executive summary subpage that explains exactly how to make a submission into the contest.
>
> Work on the next steps from the previous sessions first. … Tell me what are your limitations and what you need access to during this project. We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.
>
> Run this task through multiple passes. Pass 1: Implement the task completely and verify the result. Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find. Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues. Do not stop after the first pass. … Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.

### Non-negotiable execution rules

1. **New output only.** Do not copy, rename, or submit a previous GEMSDOE raster. Prior files and scores are evidence for analysis, not candidate inputs. Both shipped layouts are verified distinct from priors and from each other.
2. **No holdout win, no slot.** A candidate's **exact emission** must beat the current best on the frozen, spatially blocked holdout at equal mass (strictly greater mean + ≥3/4 folds; 3/3 of clean folds for post-exploration arms) and pass input, novelty, GeoTIFF, provenance, and rules checks. A validated surface with an unvalidated placement is an alternative, not the primary. A local holdout does not forecast the organizer’s hidden score.
3. **Hypotheses before implementation.** Rank 3–5 new geological hypotheses before coding/scoring, with layers, signature, off-catalogue rationale, prior-work difference, expected improvement, cost, and official external-data availability. Timestamp the frozen candidate and parameters. Timestamped amendments before scoring are allowed with a selection-corrected gate.
4. **Submission workflow when eligible.** Publish one valid single-band float32 GeoTIFF per release line, an obvious one-click download, a unique filename/submission name, a short portal comment, plus an executive summary and submission guide close to the site entrance. Ship a fallback twin, per-file audit receipts, a narrative draft, and explicit AI-use disclosure.
5. **Evidence and attribution.** Ground claims in official/trusted sources and provide review links. Verify claims against source text; keep organizer statements, owner reports, model estimates, and local measurements distinctly labeled. Record limits and irregularities rather than smoothing them over.
6. **Leaderboard terms.** The current record is the merged **2026-10-06 read** (top 10 table in `docs/data/leaderboard.json`: #1 alexoktaba 0.3345 … #5 DARD 0.3195). It is a dated snapshot, not a live feed. DrivenData’s Terms of Use prohibit automatic monitoring/copying and manual monitoring/copying without prior written consent: no scraper, poller, or refresh workflow may be added without an authorized route; future reads are a manual, authorized act only. The official page is linked for permitted browser review.
7. **Three release passes.** (1) Implement and run reproducible verification. (2) Review bugs, assumptions, leakage, edge cases, provenance, and portal risks; fix and rerun. (3) Recheck every requirement in this charter line by line, fix omissions, and rerun the full validation suite.
8. **PR discipline.** Request a PR/merge only after the work is verifiable. Do not claim a PR, merge, deployment, organizer score, or submission unless the corresponding official system confirms it. Preserve negative results and no-go decisions in the evidence trail.

For the full persistent owner instructions and active evidence state, see [`PROMPT.md`](PROMPT.md).

## Executive summary and current findings

- **Official task and output:** distance-weighted Tversky (α=0.2, β=0.8; triangular 300-m kernel) and a single-layer float32 GeoTIFF at EPSG:32611, 100-m, same bounds, [0,1], null/NaN outside. Public, private Phase 1, and expert-updated Phase 2 results differ. See [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [September 2026 Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- **Leaderboard (merged read 2026-10-06):** #1 alexoktaba 0.3345, #2 nchuzhoy 0.3262, #3 kinghorton42 0.3222, #4 Batik Shirt Brothers 0.3218, #5 DARD 0.3195 ([official page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [snapshot](docs/data/leaderboard.json)). This resolves the old IR-REPORT-02: the brief's "0.3195 is the highest" is stale (IR-43-001). No GEMSDOE\* team is in the visible top 25, so the brief's 0.2778 cannot be matched to a board row (IR-43-010 / IR-REPORT-01).
- **H33-2-B2:** GEMSDOE32 PR #9 describes pruning 2,545 catalogue-adjacent pixels from a 40,199-pixel base, leaving 37,654. The owner reports a calibrated four-fold mean of 0.2679205 and a separate **model-projected** live value 0.2746732 (≈0.2747) from owner-reported anchors — explicitly not an organizer score. Read [`research/h33_result_review.md`](research/h33_result_review.md) and [PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9); do not cite 0.2747 or 0.2778 as official scores.
- **Scoring economics:** each unit of emitted mass adds exactly 0.2 to the DTI denominator, so a marginal dot must earn credit above 0.2·DTI (≈0.052 at DTI 0.26); binary (p=1) emission is optimal; for fixed dot count the problem is MCLP under the disjoint-credit hypothesis (a hypothesis, not a bound — IR-43-007). Proofs in [`docs/research/metric-algebra.md`](docs/research/metric-algebra.md); strategy use in [`research/mclp_strategy.md`](research/mclp_strategy.md).
- **Inputs:** competition rasters restored from owner-published GitHub mirrors and hash-verified — mirror integrity, **not** organizer provenance (`registry/data_sources.json`, `registry/data_manifest.json`, `evidence/data_restore_receipt.json`, [`research/data_access.md`](research/data_access.md)).
- **IR-DATA-01:** the mirrored `sample_submission.tif` has 60,988 ones exactly on the known-label mask, contrary to the task page's total-absence description. Used for grid/footprint only, never as a prediction template.
- **H42 baseline:** independently reproduced twice (rounds 1–2, drift guard PASS): mean 0.250744 for `SH_basin_strong|sep4.0|N40000`. A local catalogue-holdout score, not a competition score.
- **Round-1 CG01:** preregistered cross-gradient concordance, mean 0.211567 (0/4 folds). Rejected; original receipt preserved at `evidence/holdout_g43_cg01_round1.json`.
- **H46 line:** H46-A stopped before scoring (failed USGS NGB source gate: 451 eligible samples); H46-B passed SGMC v1.1 source gates then failed promotion (+0.000923 mean, 2/4 wins; required +0.005 and 3/4). Records in `research/AMENDMENT-2026-10-06-*.md` and `evidence/h46b/`. Its raster was removed from the tree (see `evidence/h46b/publication_status.json`); do not submit it.
- **Supervised priors win on this protocol.** The MCLP line's supervised out-of-fold prior (62 channels) packed sep-3.0/N40000 scores **0.286388, 4/4 folds** (`evidence/holdout_g43_cg01.json`, EXT arm). The SUP01 HGB ranker (21 features) + sep-4.0 packing scores **0.262666, 4/4 folds** (`evidence/holdout_g43_mclp.json`). Both strictly beat H42 with worst fold above H42's best.
- **MCLP placement is unvalidated-as-shipped in one line and falsified in the other.** The shipped 51,053-dot maximal-covering emission was never scored at equal mass (unequal-mass probe: 0.219994, 0/4 — a mass artefact, recorded not dropped). Round 2 scored exact MCLP placement on two surfaces: 0.211122 and 0.150107, 0/4 each, plus seven failed demand variants. Mechanism: optimal covering of a miscalibrated surface loses to tail packing; placement is downstream of probability quality. Preserved in [`research/amendment_round2b.md`](research/amendment_round2b.md).
- **Round-2 rejections:** MG01 triple-gradient packing 0.205756 (0/4); 50/50 ensemble 0.241241 (0/3 clean folds). All mechanisms preserved.
- **Submissions (both live-UNSCRED):** PRIMARY SUP01 (40,000 dots, d>200 m off-catalogue; audits PASS; novelty Jaccard ≈0.011 vs 3 priors) and ALTERNATIVE MCLP sup_oof (51,053 dots, 0 on-catalogue; 12/12 format checks; novelty PASS vs 221 artifacts, coverage IoU 0.181). Merge cross-audit: both MCLP twins pass the independent auditor; layouts mutually distinct (Jaccard 0.011). See `evidence/merge_cross_audit.json` and the [submission guide](docs/executive-summary.html).
- **Unknown-test uncertainty:** DrivenData staff will not disclose hidden-test sources, fault types, or coverage ([staff reply](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7)). Blocked catalogue holdouts are necessary screens, not hidden-score forecasts. The MCLP line publishes its frames-vs-live calibration with p-values (n=8, none significant) rather than asserting it.

### Top priority / next research decision

Rebuild the supervised prior + validated sep-3.0/N40000 packing into a shippable file (0.286388 on the shared protocol exceeds the primary's 0.262666); score any maximal-covering emission at equal mass before promoting it. Then: live-score calibration of the mass operating point (0.2·DTI bar), calibrated-surface + MCLP as one arm, and the untouched backup hypotheses — each preregistered before scoring. Do not weaken any failed arm's gate post hoc.

## Reproducible workflows

This checkout's local virtual environment is `.venv/` (ignored by Git). Raw rasters and pipeline caches are git-ignored and not redistributed; the shipped submission TIFs are committed for the GitHub Pages download.

SUP01 line (from the repository root):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
bash scripts/download_competition_data.sh
.venv/bin/python scripts/audit_inputs.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python scripts/run_holdout.py
PYTHONPATH=src .venv/bin/python scripts/run_holdout_mclp.py   # ~15 min; CPU HGB
PYTHONPATH=src:scripts .venv/bin/python scripts/build_submission_sup01.py  # ~6 min
```

MCLP line (from the repository root; needs its `.cache/` channel stack — the
PR #3 cache was lost, so the first two steps rebuild it):

```bash
bash scripts/fetch_mirrors.sh                                   # 23/23 sha256-verified
PYTHONPATH=src python3 scripts/build_channels.py                # ~75 s, 62 channels
PYTHONPATH=src python3 scripts/run_pipeline.py --k-max 60000    # MCLP + blocked validation
PYTHONPATH=src python3 scripts/build_submission.py              # GeoTIFF + audit + novelty screen
PYTHONPATH=src python3 scripts/build_site.py                    # MCLP-line detail + data feeds only
```

Validation that must pass before any PR:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests -q
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/check_site_links.py
.venv/bin/python -m compileall -q src scripts tests
git diff --check
```

## Working site and research navigation

- **Landing page / download:** [`docs/index.html`](docs/index.html) — primary download with hash, alternative file, decision record.
- **Executive summary and submission guide:** [`docs/executive-summary.html`](docs/executive-summary.html) — exact upload steps, names, portal notes, narrative draft with AI disclosure.
- **MCLP-line detail (preserved PR #3 record):** [`docs/mclp-line.html`](docs/mclp-line.html) — frames, reference bars, channels, selection rule.
- **Hypotheses and candidate decisions:** [`docs/hypotheses.html`](docs/hypotheses.html), backed by [`research/hypotheses.md`](research/hypotheses.md) (round 1), [`research/hypotheses_round2.md`](research/hypotheses_round2.md) + [`research/amendment_round2b.md`](research/amendment_round2b.md) (round 2), [`research/PREREGISTRATION-2026-10-06.md`](research/PREREGISTRATION-2026-10-06.md) + [`research/AMENDMENT-2026-10-06-*.md`](research/AMENDMENT-2026-10-06-H46B-holdout.md) (H46), [`docs/research/h43-hypotheses.md`](docs/research/h43-hypotheses.md) (H43 slate).
- **Validation record:** [`docs/research.html`](docs/research.html) — H42 reproduction, round-1/2 holdouts, MCLP falsification, sup_oof-prior result, credit-bar analysis.
- **Irregularities:** [`docs/irregularities.html`](docs/irregularities.html) — the numbered IR-43 register (stale brief claims, uncalibrated frames, version caveats).
- **Leaderboard note:** [`docs/leaderboard.html`](docs/leaderboard.html) + [`docs/data/leaderboard.json`](docs/data/leaderboard.json) + [`docs/score-ledger.csv`](docs/score-ledger.csv).
- **Source register:** [`research/source_register.md`](research/source_register.md); data/licensing audit: [`research/data_access.md`](research/data_access.md); H33 attribution: [`research/h33_result_review.md`](research/h33_result_review.md); metric proofs: [`docs/research/metric-algebra.md`](docs/research/metric-algebra.md).
- **Reproducibility receipts:** [`evidence/holdout_g43_cg01_round1.json`](evidence/holdout_g43_cg01_round1.json), [`evidence/holdout_g43_cg01.json`](evidence/holdout_g43_cg01.json), [`evidence/holdout_g43_mclp.json`](evidence/holdout_g43_mclp.json), [`evidence/submission.json`](evidence/submission.json), [`evidence/submission_status.json`](evidence/submission_status.json), [`evidence/merge_cross_audit.json`](evidence/merge_cross_audit.json).

## Evidence and policy links

1. [Official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — target, layers, metric, and output format.
2. [GEMS Prize Official Rules (September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — registration, GeoTIFF, AI disclosure, and private/final evaluation requirements.
3. [DrivenData staff scoring clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) — known-catalogue mask.
4. [DrivenData staff note on hidden-test information](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) — sources, fault types and coverage not disclosed.
5. [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) — leaderboard-access boundary.
6. [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — dynamic; the dated 2026-10-06 read is in `docs/data/leaderboard.json`.
7. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [ScienceBase conductance product](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b), [USGS FDSN](https://earthquake.usgs.gov/fdsnws/event/1/), [USGS SGMC](https://mrdata.usgs.gov/geology/state/), [USGS NGB OFR 2002-227](https://pubs.usgs.gov/of/2002/0227/data.html), [GDR submission 1391](https://gdr.openei.org/submissions/1391) — official external-data sources reviewed for the slates, with unresolved coverage noted.
8. [Organizer-linked GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — supervised U-Net/ResNet18 example on random patches; a different method family and validation design from the blocked per-fold approaches here. (It writes an all-finite, nodata-free raster — the precedent for the `-zeros` fallback twins.)
9. [Church & ReVelle (1974)](https://link.springer.com/article/10.1007/BF01942293), [Nemhauser–Wolsey–Fisher summary](http://chekuri.cs.illinois.edu/talks/crm_submodular.pdf), [Minoux lazy-greedy docs](https://submodlib.readthedocs.io/en/latest/optimizers/lazyGreedy.html) — placement-theory citations for the MCLP experiments.

## Code map

```text
PROMPT.md                         persistent owner brief and current evidence state
README.md                         this charter, runbook, status and navigation
AGENTS.md                         future-session requirements to read the charter first
index.html                        root GitHub Pages redirect to docs/index.html
knowledge-base.html               H46-era research knowledge base (root)
registry/data_sources.json       competition-input source pins and provenance caveats
registry/data_manifest.json      23 hash-pinned MCLP-line input mirrors
registry/channels.json           provenance of every derived channel
registry/experiment.json         preregistered CG01 operator and gate (round 1)
registry/experiment_g43_mclp.json preregistered MCLP/MG01 + round-2b amendment (round 2)
research/PREREGISTRATION-2026-10-06.md  H46 slate and locked protocol
research/AMENDMENT-2026-10-06-*.md      H46 source/holdout amendments
research/hypotheses.md           ranked round-1 slate and result
research/hypotheses_round2.md    ranked round-2 slate (MCLP01/MG01/BG01/GT01/SC01)
research/amendment_round2b.md    MCLP falsification log + SUP01/ENS01 backup + corrected gate
research/mclp_strategy.md        credit-bar economics, H33 analysis, MCLP verdict, next paths
research/data_access.md          input, licensing and sample irregularity audit
research/source_register.md      source-by-source claim attribution
research/h33_result_review.md   owner-projection explanation and limits
research/review_log.md          three-pass logs + PR #3/#4 merge reconciliation
scripts/audit_inputs.py          raster, hash, footprint and irregularity receipt
scripts/run_holdout.py           H42 reproduction, CG01, and EXT sup_oof-prior grid
scripts/run_holdout_mclp.py      round-2 holdout: MCLP/MG01/SUP01/ensemble + drift guard
scripts/build_submission_sup01.py full-footprint SUP01 build into docs/downloads/
scripts/audit_submission.py      independent format + novelty audit (portal contract)
scripts/build_channels.py        19 bands + external rasters -> 62 named channels
scripts/run_pipeline.py          MCLP-line surfaces -> MCLP -> blocked validation
scripts/run_variants.py          MCLP-line surface/variant grid
scripts/calibrate_instrument.py  frames-vs-live calibration with p-values
scripts/run_novelty.py           221-artifact near-duplicate screen
scripts/build_submission.py      MCLP-line GeoTIFF write + verify + audit
scripts/build_site.py            MCLP-line detail + data feeds (merged pages are hand-kept)
scripts/check_site_links.py      root-page link/anchor check (CI)
src/gemsdoe43/                    metric, I/O, H42, packing, CG01, MCLP, surfaces, SUP01
src/gems43/                       MCLP-line metric/grid/channels/surface/mclp/holdout/novelty
tests/                             offline, synthetic and site-consistency tests (pytest+unittest)
evidence/                          machine-readable input, validation and release receipts
docs/                              user-facing site + audited submission downloads
```
