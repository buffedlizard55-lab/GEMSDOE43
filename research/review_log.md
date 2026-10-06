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
