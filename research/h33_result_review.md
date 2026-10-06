# H33-2-B2 result review: what 0.2747 does and does not mean

**Reviewed:** 2026-10-06 UTC
**Primary source:** [GEMSDOE32 PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9) and the linked owner-maintained `evidence/h33_validation.json` / `src/gems32/hypotheses33.py`. These are the submitting group's reports, not organizer confirmations.

## Reported mechanism

H33-2-B2 is an **emission-removal rule**, not a newly discovered geological layer or an organizer-scored result. The source code describes H33-2 as deleting every emitted point within a chosen pixel buffer of the published fault catalogue. H33-2-B2 removes all points with catalogue distance `<= 2` pixels from a 40,199-dot B=1 base, leaving **37,654 dots**. The PR reports **2,545 removals** (6.3% of the base mass), no points on the catalogue itself, and a four-fold local/LM-calibrated mean of **0.2679205**.

The code and PR say the removal arm improves the group's calibrated four-fold comparison by **+0.0048695** over its B=1 base and wins its local comparison in 4/4 folds. The owner's holdout summary gives a minimum fold of 0.1784544 and maximum of 0.4228785. Those are reported research measurements, not DrivenData scores.

## Where 0.2747 comes from

The PR labels **0.2747** as a *projected live score*. The evidence JSON reports the more precise modeled value **0.2746732**, rounded to four decimals. It is derived from the group's live-anchor model, not from a new organizer evaluation. The PR discusses owner-reported live anchors of **0.2600** (a 44,090-dot emission) and **0.2708** (a 40,199-dot B=1 prune). Its H33-2-B2 projection additionally reports a 2,545-dot deletion, estimated credit terms, a safety factor of approximately 2.08, and an estimated 0.2746732 score if the calibration assumptions hold.

The displayed 0.2747 is therefore **not** the 0.2679205 calibrated fold mean, **not** a score observed for H33-2-B2 on the official public leaderboard in the linked evidence, and **not** an organizer-confirmed result. The PR explicitly states that the repository has no organizer score for its artifacts. G43 will keep that attribution visible anywhere the result is mentioned.

## Why the method is plausible—and why the inference is limited

- Official DrivenData staff clarified that pixels corresponding to known USGS/INGENIOUS faults are masked from scoring ([staff reply](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)). Predicting at those exact pixels is therefore inert under that clarification; nearby, unmasked predictions still have ordinary metric consequences.
- Removing a narrow catalogue-adjacent halo could remove weak or redundant mass, but its value is an emission-geometry observation—not evidence that the removed locations are not geological faults.
- The 0.2747 projection depends on transfer/calibration from a small number of owner-reported live anchors and a spatial holdout. The PR itself confines its calibration and warns that an unrelated 0.4413 extrapolation was outside the method's validity domain.
- A local catalogue CV can test whether a spatial pattern recovers withheld known catalogue traces. It cannot verify hidden organizer truth, the leaderboard projection, or the competition's private/final score.

## G43 treatment

G43 uses H33-2-B2 as a documented methodological clue (small catalogue-adjacent removals may be worth testing), not as a score claim or a raster to copy. The G43 H42 reproduction and candidate are recomputed from input layers; no H33 output raster is used. Any future catalogue-flank experiment must be preregistered, evaluated fold-consistently against the reproduced H42 control, and pass the same improvement gate before it can become a submission candidate.
