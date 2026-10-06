# GEMSDOE43 project brief — persistent owner instructions

Read `README.md` and this file at the start of every project session. This is the standing charter, not a prompt for a one-off answer.

## Core Values

- **Maximize P(Win)**
- **Own the Outcome**

## Full project brief

Review and develop GEMSDOE43 into an auditable DOE GEMS research and submission project. Explain the reported H33-2-B2 result without presenting owner reports as organizer-confirmed scores; inspect the current official leaderboard; propose and rank 3–5 new geological hypotheses naming layers, targeted physical signatures, rationale for finding faults absent from the USGS/INGENIOUS catalogue, differences from prior approaches, expected improvement, cost, and any official external data needed. Validate the best candidate on the spatial holdout before using a submission slot. Aim to generate a genuinely unique, usable single-band GeoTIFF with an obvious download, unique submission name, short portal comment, and executive summary/submission guide. Include the user’s full project brief in README and treat it as the starting point each session. Research official sources, give review links, state limitations and irregularities, improve the research/system autonomously, run multiple implementation/review passes, and request a PR/merge only after work is verifiable.

A standing owner directive further requires solving placement as a formal covering optimization (Church–ReVelle MCLP with submodular greedy) instead of sweeping spacing constants, then verifying the layout is not a near-duplicate of any prior submission. G43 implemented that program exactly — and the frozen holdout falsified it on the tested surfaces; the evidence is preserved and the shipped file follows the validated placer.

## Standing requirements and corrections

1. **Unique artifact:** produce a new, genuinely usable TIF submission; do not copy or rename any prior GEMSDOE submission. Prior results and artifacts may be examined for learning and comparison only. Verify novelty at the array level (hash, Jaccard, overlap) against a stated prior corpus.
2. **Holdout gate:** do not use a submission slot for a candidate that has not beaten the current best on the frozen, spatially blocked holdout. Arms specified before any score inspection use the 4-fold gate (strictly greater mean + ≥3/4 wins); arms selected after exploration use a selection-corrected gate (folds 1–3 only, 3/3 + mean). A failed candidate is reported honestly with its mechanism, never disguised or re-tuned post hoc.
3. **Before implementation:** formulate and rank 3–5 untried geological hypotheses. For every one name the layers, physical signature, why it could find faults absent from the USGS/INGENIOUS catalogue, distinction from prior repository approaches, expected improvement, implementation cost, and availability of any official external data. Record and timestamp the selection before scoring. Timestamped amendments before the scored run are allowed with a corrected gate and a full exploration log.
4. **Submission workflow:** if and only if a candidate passes the gate, provide a valid single-band float32 GeoTIFF, a clear one-click download, a unique file/submission name, a short portal comment, and an executive summary and submission guide near the site entrance. Always ship a fallback twin, per-file audit receipts, a narrative draft, and explicit AI-use disclosure.
5. **Complete README charter:** keep this full brief and the Core Values in `README.md`; read README at the start of every subsequent project session.
6. **Evidence quality:** prefer official/trusted sources, link them for review, verify claims against the source text, distinguish official statements from owner reports and model estimates, and state limits, unresolved data provenance, and irregularities. Never state an owner-reported leaderboard or projected score as organizer-confirmed. Flag report conflicts (IR-REPORT-*) for manual review.
7. **Leaderboard access:** inspect an official snapshot only when permitted. Do not build an automated leaderboard feed, scraper, polling job, or manual copying workflow without an authorized API or prior written permission. The DrivenData Terms of Use currently prohibit both automatic and manual monitoring/copying without prior written consent; follow those terms even if a leaderboard refresh is requested. Keep the last permitted/previously recorded snapshot dated and clearly historical.
8. **Autonomous project improvement:** improve the research and system, tests, validation, documentation, provenance receipts, website, and submission workflow without waiting for the owner to prescribe each step. Do not imply that external data or portal access exists when it does not.
9. **Three review passes before a release/PR:**
   - Pass 1 — implement and run reproducible verification;
   - Pass 2 — review bugs, assumptions, data leakage, edge cases, and portal/format risks; fix them and rerun affected tests;
   - Pass 3 — check every requirement in this brief line by line, fix omissions, and rerun the complete validation suite.
10. **PR and merge:** open/request a PR and merge to `main` only after the work is verifiable. Never claim that a PR is open, merged, or deployed unless GitHub confirms that exact state. Preserve negative results and no-go decisions in the evidence trail.

## Current active evidence state (refresh this section when facts change)

- Core competition inputs and the H42/SUP01 LiDAR layer are restored from owner-published GitHub mirrors and match pinned byte counts and SHA-256 hashes. They are **not organizer-authenticated**.
- The mirrored `sample_submission.tif` has 60,988 ones exactly on the known-label positive mask, contrary to the task page's description of it as a total-absence example (IR-DATA-01). It is used only for geometry/footprint, never as a prediction template.
- Round 1: H42 reproduced (mean 0.250744); G43-CG01 failed (0.211567, 0/4). Receipt: `evidence/holdout_g43_cg01.json`.
- Round 2 (receipt `evidence/holdout_g43_mclp.json`, drift guard PASS): MCLP arms A/B failed (0.211122 / 0.150107, 0/4 each); MG01 packing C failed (0.205756, 0/4); ensemble E failed (0.241241, 0/3 clean folds). **SUP01 passed**: 4-fold mean 0.262666 (+0.011922), 4/4 folds; corrected gate folds 1–3: 3/3, mean 0.263590 vs 0.253568.
- Submission `gems43-sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f` (40,000 dots, d>2px off-catalogue) is built, format-audited (both twins PASS), and novelty-checked (Jaccard ≈ 0.011 vs three hash-verified priors). Status: **SLOT_ELIGIBLE, live-UNSCRED**. Name `GEMSDOE43-SUP01-HGB21-SE40`; 152-char portal note in `evidence/submission_status.json`.
- H33-2-B2's 0.2747 is an owner-model projection from owner-reported anchors, not an organizer-confirmed score; a conflicting 0.2778 report is flagged (IR-REPORT-01). See `research/h33_result_review.md` and `research/mclp_strategy.md`.
- The last previously recorded public leaderboard snapshot is 2026-10-05 (rank 1: 0.3345); it was not refreshed on 2026-10-06 because of the DrivenData Terms of Use. Competing historical claims (0.3195, 0.3262) are flagged (IR-REPORT-02). See `research/source_register.md`.
