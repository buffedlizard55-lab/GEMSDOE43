# Three-pass implementation and release review

**Review date:** 2026-10-06 UTC
**Branch:** `arena/df8c2e0c-gemsdoe43`
**Scope:** audit inputs, register and test G43-CG01, independently reproduce H42's four-colour holdout, create a status/research site, and determine whether a submission is authorized.

## Pass 1 — implementation and verification

Implemented the pinned-input restore/audit flow, exact input metadata/footprint receipt, official DTI calculation plus a deliberately direct small-array test implementation, the H42 reference feature and emission logic, a frozen multi-scale cross-gradient candidate, four-fold holdout runner, and a static user-facing research site. Recorded the full project brief and stop rules in README/PROMPT; ranked five geological hypotheses before candidate evaluation.

**Measured checks:**

- Restore script reported all four registered files already verified by byte count/SHA-256 against owner-maintained manifests; organizer provenance remains unverified.
- Input audit passed: 3,730×3,292 EPSG:32611; 5,167,373 footprint cells; 60,988 label positives; exact sample-ones/label-positive mask match (IR-DATA-01).
- Scarp evidence decoder matched the public GEMSDOE41 `load_products` output pixel-for-pixel; this validates reimplementation consistency, not original tile lineage.
- All 12 unit tests passed after site tests were added: metric vs brute force, known-pixel masking, kernel boundaries, packing separation, synthetic gradient alignment, link/fragment checks and download gating.
- Final local holdout reproduced the selected H42 arm and all 20 clean reference arms/controls within 1e-6; only the owner report's `historical_h33_CONTAMINATED` arm was excluded because the owner marked it contaminated and the raster was unavailable.
- G43-CG01 scored mean 0.211567 vs local H42 0.250744, winning 0/4 folds. Gate failed; no candidate submission raster was created.

## Pass 2 — bug, assumptions, leakage and edge-case review

### Findings fixed

1. **Random-control reproducibility:** the first expanded holdout implementation used one RNG stream for both the 20k reference random control and an added 40k control. The extra draw changed later-fold random controls. Split these controls into independent, seeded streams and added comparison of every clean arm/control. The final 20k random control now exactly matches the owner report (mean 0.121243; min 0.115356; max 0.126855).
2. **Contaminated owner arm:** the original report includes a historical H33 arm marked contaminated. It was initially treated as a required reference arm, causing a false reproduction FAIL because its source raster was not present. The final reproducer explicitly excludes that arm, records the exclusion, and checks the 20 clean arms/controls; final reproduction is PASS.
3. **Invalid CG01 source cells:** the candidate emitter now intersects the fold's allowed mask with both feature-band validity masks, preventing emissions on no-data cells. The valid footprint count (5,164,312) is included in the receipt.
4. **Premature data-audit command:** `scripts/audit_inputs.py` was implemented, fixed for nonfinite nodata metadata, run successfully, and `research/data_access.md` now matches the actual script/result.
5. **Pages-root mismatch:** GitHub Pages currently uses legacy `main:/`, while the site content lives in `docs/`. Added a root `index.html` fallback redirect to `docs/index.html` and a test so the existing Pages entrance reaches the no-go status and executive guide.
6. **False-output language:** changed the data documentation to state that no output writer or submission TIF currently exists; a future writer must meet official format requirements.

### Assumptions and edge cases recorded

- Local holdout truth is withheld published-catalogue positives. The official-known-fault mask is intentionally not passed into this separate CV, otherwise its truth would be masked. Real submission scoring has an explicit `known`-mask path in `src/gemsdoe43/metric.py` and a unit test.
- The source raster mirrors are hash-consistent but not organizer-authenticated; no external 1-m mosaic or exact DEM tile inventory is in the checkout.
- DrivenData staff declined to reveal hidden-fault source/type/coverage, so candidate signatures are hypotheses, not descriptions of hidden labels.
- A raster-level novelty comparison was not run: the failed candidate was never materialized as a full-grid download artifact. The site has no TIF link. Do not describe CG01 as a unique submission.
- Leaderboard page was not refreshed; the Terms of Use prohibit automated and manual monitoring/copying without prior written consent. The 2026-10-05 rank-1 observation remains dated historical context only.

## Pass 3 — requirement-by-requirement final check

| Charter requirement | Final state | Evidence / caveat |
|---|---|---|
| Preserve full owner brief and Core Values in README; read each session | **Done** | `README.md`, `PROMPT.md`, and `AGENTS.md` |
| Explain H33-2-B2 without calling projection official | **Done** | `research/h33_result_review.md`, executive summary and source register; 0.2747 clearly attributed as owner-model projection |
| Inspect/record official leaderboard responsibly | **Historical only** | Last prior snapshot 2026-10-05, rank 1 0.3345. No 2026-10-06 refresh because of Terms of Use |
| Rank 3–5 hypotheses with layers/signatures/off-catalogue rationale/prior-work difference/expected lift/cost/external sources | **Done** | Five-entry `research/hypotheses.md`, `registry/experiment.json`, and site; untested backup candidates stay marked untested |
| Validate best preregistered candidate against spatial holdout before using slot | **Done; candidate failed** | `evidence/holdout_g43_cg01.json`; H42 reproduced, CG01 0/4 wins |
| Unique, usable, downloadable single-band GeoTIFF | **Not produced by design** | No-go gate failed. No raster novelty audit, download, portal comment, or slot. This primary deliverable remains outstanding until a later candidate passes. |
| Executive summary/submission guide near site entrance | **Done conditionally** | `docs/index.html`, `docs/executive-summary.html`, root redirect; guide states no current file is eligible |
| Official/trusted sources, review links, limits/irregularities | **Done** | `research/source_register.md`, `research/data_access.md`, site sources page |
| Three implementation/review passes | **Done** | This log; affected tests and final holdout rerun after fixes |
| Request PR/merge only after verifiable work | **Ready for PR** | Input audit, 12 tests, and final holdout receipt pass. The requested submission TIF is not satisfied because no candidate passed; any PR must say so and make no submission claim. |

## Release conclusion

The project software, provenance receipts, H42 reproduction and candidate no-go are verifiable. The central **submission** objective is still incomplete: no unique TIF exists because the candidate failed. Any PR should be framed as a reproducible research/no-go improvement, not as a winning or portal-ready submission. A future candidate needs a new pre-registered experiment and the same or stronger holdout gate.

---

# Round 2 — three-pass release log (2026-10-06 UTC)

Scope: round-2 hypothesis slate, MCLP/MG01/SUP01/ensemble experiment, submission
build, site promotion to slot-eligible, and all supporting receipts. Full detail:
`research/hypotheses_round2.md`, `research/amendment_round2b.md`,
`research/mclp_strategy.md`, `evidence/holdout_g43_mclp.json`,
`evidence/submission_status.json`.

## Pass 1 — implement + verify

- Registered round 2 (MCLP01/MG01/BG01/GT01/SC01) with frozen runner
  `scripts/run_holdout_mclp.py` + registry `experiment_g43_mclp.json` before any
  scored run. Fold-0 exploration falsified MCLP (seven demand variants, all
  trailing); timestamped amendment added SUP01/ENS01 backups with a corrected
  folds-1–3 gate (3/3 + mean).
- Scored 4-fold run finished exit 0 (838 s). Drift guard PASS (REF matched
  round-1 ×8 within 1e-6). SUP01: 0.262666, 4/4; A/B/C/E all 0 wins. All
  exploration numbers are in the amendment — no post-hoc tuning.
- Built the full-footprint submission after an OOM (exit 137 on 3.9 GB) was
  fixed by adding `fit_predict_in_sample` and releasing the 1 GB stack before
  the 261 s CPU fit. Both twins pass `audit_submission.py`; novelty Jaccard
  ≈ 0.011 vs three hash-verified priors.
- 30/30 unit tests pass, including new MCLP-vs-enumeration, HGB-helper
  equivalence, frozen-hyperparameter, and eligibility-aware site tests.

## Pass 2 — bug / leakage / edge-case review

- Verified SUP01 trains per fold on training-block cells only; no held-fold
  labels, no coordinates, early stopping on training split; `fit_predict_in_sample`
  proven byte-exact vs the CV path on fold-size data.
- Verified MCLP demand uses training-guarded surfaces; eval truth uses raw
  held blocks; candidate shortlist is deterministic; greedy solver checked
  against brute-force optima (greedy ≥ (1−1/e)·OPT on all randomized trials).
- Radius-derived padding fix in `mclp.py` (was spacing-hardcoded); scored
  behavior unchanged. Pipe exit-masking lesson recorded; reruns use
  `> log 2>&1; echo PY_EXIT:$?`.
- Format audit independently re-verifies CRS/shape/dtype/range/count/flank
  rules; receipt hashes match shipped bytes (asserted by `test_site.py`).
- Leakage review conclusion: the local instrument knows only training-block
  catalogue labels; the owner-mirror sample file (IR-DATA-01) is used for
  geometry only in every path. No train/eval label leakage found.

## Pass 3 — charter line-by-line recheck

| Requirement | Status | Evidence |
|---|---|---|
| Unique TIF submission, not a copy | **Done** | `docs/downloads/gems43-*-bc2e4e9a8d6f-{nan,zeros}.tif`, build receipt, novelty table (Jaccard < 0.80, overlap < 0.90, hashes differ) |
| MCLP covering optimization, not spacing sweep | **Done (tested, falsified)** | `src/gemsdoe43/mclp.py`, `tests/test_mclp.py`, amendment log; shipped file follows the validated placer |
| Portal format contract ([0,1], float32, EPSG:32611, 100 m, NaN outside) | **Done** | Per-file audit receipts; zeros twin for NaN-handling fallback |
| Near-duplicate layout check | **Done** | 3-prior corpus, Jaccard ≈ 0.011, ~2% dot overlap |
| 3–5 ranked hypotheses + holdout validation before slot | **Done** | Two slates (5 + 5 + 2 backups), ranked with layers/signature/rationale/cost; best validated 4-fold before release |
| Official sources, review links, flagged irregularities | **Done** | `research/source_register.md` (DD/P/EXT/LIT/SOFT IDs), IR-DATA-01, IR-REPORT-01/02 unresolved |
| Obvious download + unique name + portal note + guide | **Done** | Landing hero + executive-summary guide, `GEMSDOE43-SUP01-HGB21-SE40`, 152-char note, narrative draft with AI disclosure |
| H33 0.2747 attribution without organizer-score claims | **Done** | `research/h33_result_review.md`, exec-summary/site sections, IR-REPORT-01 flag |
| Leaderboard terms compliance (no refresh/scrape) | **Done** | Dated 2026-10-05 snapshot only, links out, IR-REPORT-02 flag |
| Three passes + PR only when verifiable | **Done** | This log; 30/30 tests; scored exit-0 receipts; PR may open |

## Release conclusion (round 2)

SUP01 passed the frozen gate and every release audit; it is **slot-eligible and
live-UNSCRED**. All other round-2 arms are rejected with mechanisms preserved.
A PR may now be opened and merged as a research + submission-release change,
framed honestly: one eligible but unscored file plus a falsified placement
program — not a winning or leaderboard-verified submission.

---

# Merge reconciliation — main (PR #3, MCLP line) + arena/dffca7c2 (PR #4, SUP01 line), 2026-10-06

While PR #4 was open, main merged PR #3: a parallel MCLP-emission line with its
own package (`src/gems43/`), pipeline, H46 records, generated site, leaderboard
read, and shipped file `gemsdoe43-mclp-supoof-51053-*` (51,053 dots, portal name
`GEMSDOE43-MCLP-sup_oof-51053`). Both lines were reconciled instead of picking
one blindly. All of main's evidence is preserved verbatim; nothing was deleted.

## What each line established (kept side by side)

- **MCLP line (main):** supervised out-of-fold prior over 62 channels, packed
  sep-3.0/N40000, scores **0.286388 mean, 4/4 folds** vs same-run H42 0.250744
  on the shared four-fold protocol (`evidence/holdout_g43_cg01.json`, EXT arm).
  Frames-A/C selection vs a live-anchored reference bar (+33%/+36%); frame B
  excluded (SGMC-truth circularity). Novelty PASS vs 221 artifacts (coverage
  IoU 0.181). Leaderboard read 2026-10-06 (top-10 table) resolves IR-REPORT-02.
- **SUP01 line (PR #4):** per-fold HGB ranker on 21 features + sep-4.0 packing
  scores **0.262666 mean, 4/4 folds** vs reproduced H42 (`evidence/
  holdout_g43_mclp.json`); MCLP placement independently falsified on tested
  surfaces (0.211122, 0/4). Format + novelty audits PASS on the shipped twins.

## The decision both lines' evidence forces

The MCLP line's own status record (`superseded_by.measurement_caveat`) states
its shipped maximal-covering placement was **never scored at equal mass**, its
channel stack and OOF surface were **lost with gitignored .cache/** (the
shipped file is currently irreproducible), and its prescribed next step is to
score the shipped emission or emit validated packing instead. Round 2
independently predicts that test fails (MCLP 0/4 on two surfaces). Therefore:

- **PRIMARY (slot recommendation):** the SUP01 file — the only shipped layout
  whose exact emission family was validated at equal mass, with a reproducible
  build (`scripts/build_submission_sup01.py`).
- **ALTERNATIVE (retained with caveat):** the MCLP sup_oof file — validated
  prior, unvalidated placement, irreproducible until rebuilt.
- **Top next step:** rebuild the supervised prior + validated sep-3.0/N40000
  packing into a shippable file (0.286388 on the same protocol exceeds 0.262666);
  score any MCLP emission at equal mass before promoting it.

Recorded in `evidence/submission_status.json` (`primary_release` + `decision`;
the CG01 NO_GO base and the MCLP `superseded_by` record are untouched).

## Mechanical merge notes

- Main's generated site backbone is kept for MCLP-line detail
  (`docs/mclp-line.html`, `docs/irregularities.html`, `docs/research/*`,
  `docs/data/*`, `docs/score-ledger.csv`); the six charter-required pages are
  hand-maintained merged versions in the light theme, with `docs/assets/
  site.css` restored to the base theme (main's pages are inline-styled and
  unaffected). `scripts/build_site.py` was patched to stop overwriting the
  merged pages (it now renders MCLP-line detail + data feeds only).
- Colliding adds were renamed, not overwritten: `scripts/
  build_submission_sup01.py`, `tests/test_mclp_greedy.py` (SUP01 line) alongside
  main's `scripts/build_submission.py`, `tests/test_mclp.py` (MCLP line).
- `evidence/holdout_g43_cg01.json` on main dropped the round-1 CG01 arms when
  the EXT grid was added; the original bytes are preserved verbatim as
  `evidence/holdout_g43_cg01_round1.json`.
- `tests/test_site.py` now asserts the two-file decision state (both downloads
  present with PASS audits, primary/decision tokens on the landing page and
  guide, both gate receipts reproducible). Full suite (pytest + unittest),
  `scripts/check_site_links.py`, `compileall`, and `git diff --check` all pass.
