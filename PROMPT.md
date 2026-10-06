# GEMSDOE43 project brief — persistent owner instructions

Read `README.md` and this file at the start of every project session. This is the standing charter, not a prompt for a one-off answer.

## Core Values

- **Maximize P(Win)**
- **Own the Outcome**

## Full project brief

Review and develop GEMSDOE43 into an auditable DOE GEMS research and submission project. Explain the reported H33-2-B2 result without presenting owner reports as organizer-confirmed scores; inspect the current official leaderboard; propose and rank 3–5 new geological hypotheses naming layers, targeted physical signatures, rationale for finding faults absent from the USGS/INGENIOUS catalogue, differences from prior approaches, expected improvement, cost, and any official external data needed. Validate the best candidate on the spatial holdout before using a submission slot. Aim to generate a genuinely unique, usable single-band GeoTIFF with an obvious download, unique submission name, short portal comment, and executive summary/submission guide. Include the user’s full project brief in README and treat it as the starting point each session. Research official sources, give review links, state limitations and irregularities, improve the research/system autonomously, run multiple implementation/review passes, and request a PR/merge only after work is verifiable.

## Standing requirements and corrections

1. **Unique artifact:** produce a new, genuinely usable TIF submission; do not copy or rename any prior GEMSDOE submission. Prior results and artifacts may be examined for learning and comparison only.
2. **Holdout gate:** do not use a submission slot for a candidate that has not beaten the current best on the frozen, spatially blocked holdout. A failed candidate is a no-go; report it honestly and do not make it look like a winner.
3. **Before implementation:** formulate and rank 3–5 untried geological hypotheses. For every one name the layers, physical signature, why it could find faults absent from the USGS/INGENIOUS catalogue, distinction from prior repository approaches, expected improvement, implementation cost, and availability of any official external data. Record and timestamp the selection before scoring.
4. **Submission workflow:** if and only if a candidate passes the gate, provide a valid single-band float32 GeoTIFF, a clear one-click download, a unique file/submission name, a short portal comment, and an executive summary and submission guide near the site entrance.
5. **Complete README charter:** keep this full brief and the Core Values in `README.md`; read README at the start of every subsequent project session.
6. **Evidence quality:** prefer official/trusted sources, link them for review, verify claims against the source text, distinguish official statements from owner reports and model estimates, and state limits, unresolved data provenance, and irregularities. Never state an owner-reported leaderboard or projected score as organizer-confirmed.
7. **Leaderboard access:** inspect an official snapshot only when permitted. Do not build an automated leaderboard feed, scraper, polling job, or manual copying workflow without an authorized API or prior written permission. The DrivenData Terms of Use currently prohibit both automatic and manual monitoring/copying without prior written consent; follow those terms even if a leaderboard refresh is requested. Keep the last permitted/previously recorded snapshot dated and clearly historical.
8. **Autonomous project improvement:** improve the research and system, tests, validation, documentation, provenance receipts, website, and submission workflow without waiting for the owner to prescribe each step. Do not imply that external data or portal access exists when it does not.
9. **Three review passes before a release/PR:**
   - Pass 1 — implement and run reproducible verification;
   - Pass 2 — review bugs, assumptions, data leakage, edge cases, and portal/format risks; fix them and rerun affected tests;
   - Pass 3 — check every requirement in this brief line by line, fix omissions, and rerun the complete validation suite.
10. **PR and merge:** open/request a PR and merge to `main` only after the work is verifiable. Never claim that a PR is open, merged, or deployed unless GitHub confirms that exact state. Preserve negative results and no-go decisions in the evidence trail.

## Current active evidence state (refresh this section when facts change)

- Core competition inputs and the baseline-only H42 LiDAR layer are restored from owner-published GitHub mirrors and match pinned byte counts and SHA-256 hashes. They are **not organizer-authenticated**.
- The mirrored `sample_submission.tif` has 60,988 ones exactly on the known-label positive mask, contrary to the task page's description of it as a total-absence example. It is used only for geometry/footprint, never as a prediction template.
- The selected experiment at initial registration was G43-CG01 (RTP magnetic versus isostatic-gravity multiscale cross-gradient concordance). The independent H42 four-colour 20-km holdout and CG01 results are recorded in `evidence/holdout_g43_cg01.json`. Current gate status: **CG01 does not beat H42; no submission TIF or portal slot is authorized**.
- The H42 owner report's mean DTI 0.250744 is reproduced locally; this is a local withheld-catalogue CV score, not a competition leaderboard result.
- H33-2-B2's 0.2747 is an owner-model projection from owner-reported anchors, not an organizer-confirmed score. See `research/h33_result_review.md`.
- H46-A's USGS NGB source gate failed (451 eligible samples; 447 with at least three usable assays in-footprint) and it was stopped before scoring.
- H46-B passed source gates for pinned USGS SGMC v1.1, then failed its registered public-catalogue proxy promotion rule: mean ΔDTI +0.000923, 2/4 wins; required +0.005 and at least 3/4. The H42 control reproduced exactly. No private-set validation, leaderboard score, slot, or current download is authorized. See `research/AMENDMENT-2026-10-06-H46B-holdout.md` and `evidence/h46b/`.
- The H46-B runner produced a distinct, format-checked GeoTIFF, but the failed candidate was removed from the current tree and is not linked from the current project site. An earlier public branch commit and unexpired GitHub Actions artifact retain it; a deletion request returned HTTP 403 for insufficient integration permission. No DrivenData upload occurred. See `evidence/h46b/publication_status.json`; do not download or submit the historical file.
- The pinned 2017 SGMC v1.1 release used by H46-B now has a 2026 GeMS successor recommended by USGS (DOI `10.5066/P1A3DQZK`). It was not fetched or audited; any future source version change requires a new audit and fresh confirmation regions.
- The last previously recorded public leaderboard snapshot is 2026-10-05 (rank 1: 0.3345); it was not refreshed on 2026-10-06 because DrivenData Terms of Use prohibit automated/manual monitoring or copying without prior written consent. Do not refresh or reproduce rows unless permitted. See `research/source_register.md`.
