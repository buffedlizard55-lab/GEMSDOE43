# Placement, credit, and what could beat the leaders — G43 analysis

**Written:** 2026-10-06 UTC. Numbers below are either official formulas, G43 local
measurements, or explicitly-labeled owner reports. No live score is claimed for any G43
artifact. Two report conflicts are flagged at the end for manual review.

## 1. The scoring arithmetic (official, verified in `src/gemsdoe43/metric.py`)

The organizer scores DTI = TP / (TP + 0.2·FP + 0.8·FN) with a triangular distance kernel
k(d) = max(1 − d/300m, 0) ([task page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
Staff clarified that known USGS/INGENIOUS pixels are masked from evaluation
([staff reply](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)).

**Marginal credit bar (derived, matches GEMSDOE32's published derivation).**
Adding one binary dot with kernel credit c changes TP by +c, FP by +(1−c), FN by −c,
so the denominator changes by c + 0.2(1−c) − 0.8c = **0.2 exactly**, independent of c.
The dot raises DTI iff (TP+c)/(D+0.2) > TP/D, i.e. iff **c > 0.2·DTI**.
At DTI ≈ 0.26 the bar is ≈ 0.052 mean credit per dot. Dots below the bar destroy score;
this single inequality explains the entire dotted-file lineage.

## 2. Why the dotted + pruned files won (owner-reported live anchors, UNVERIFIED)

Treating the sibling owner reports as claims (not organizer receipts):

| File (owner claim) | Dots | Claimed live DTI |
|---|---|---|
| H19-5 solid (G19) | 121,131 | 0.1922 |
| d1.5 thinning (G24) | 60,069 | 0.2477 |
| d2.8 thinning (G25) | 44,090 | 0.2600 |
| B=1 prune, d≤1px removed (G31/G32 base) | 40,199 | 0.2708 |
| H33-2-B2, d≤2px removed (G32) | 37,654 | **projected 0.2747, UNSCORED** |

Mechanism, per step: (a) Thinning 121k→60k→44k removes dots whose kernel credit was
already covered by neighbors (redundant mass costs 0.2/dot in the denominator while
adding ~0 TP) — mean credit per dot rises toward the bar. (b) The B=1 prune deletes
3,891 dots within 100 m of the catalogue; they were unmasked (only exact catalogue
pixels are masked) yet earned below-bar credit, because hidden truth near the catalogue
is evidently sparse there — removing them shrinks the denominator by 0.2×3,891 ≈ 778
while costing little TP. (c) H33-2-B2 extends the prune to 2 px (2,545 more dots) with a
live-anchor-calibrated safety factor of 2.08; its 0.2747 is a MODEL projection from two
owner anchors, and the PR states no organizer score exists
([PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9)).

**PhD-level summary:** every winning step was *mass discipline under the 0.2·DTI bar*,
not new geology. The detector (H19-5 multiline surface) stayed fixed from 0.1922 to the
0.2747 projection; all gains came from emitting fewer, better-placed dots.

## 3. What it takes to beat the leaders (conditional arithmetic, not a forecast)

At fixed mass M, DTI = TP/(0.2·M + 0.8·|G|). Conditional on the owner-inferred hidden
count |G| ≈ 12,691 (G25 H28 model — a fitted latent parameter, not verified truth):
at M = 40,000, DTI 0.27 needs TP ≈ 4,900 (0.123/dot); DTI 0.32 needs TP ≈ 5,810
(0.145/dot), i.e. **+18% credit density at the same mass**. There are only three ways
to get it: (i) dots closer to hidden faults (better detector); (ii) less mass (only if
marginal dots are below bar — the H33 direction, nearly exhausted at safety ≈ 2);
(iii) a different operating point on a better surface. No placement trick on the same
surface can manufacture credit that the surface does not imply — which is exactly what
the G43 MCLP experiment below confirms.

## 4. The MCLP experiment: exact implementation, honest falsification

G43 implemented Church–ReVelle maximum coverage (Church & ReVelle 1974,
*Papers in Regional Science* 32:101–118) with the official triangular kernel as the
coverage function and an exact lazy-greedy solver (Minoux 1978) carrying the
Nemhauser–Wolsey–Fisher (1−1/e) guarantee *over the candidate set for covering the
surface*. Unit tests verify the solver against brute-force optima on tiny grids
(`tests/test_mclp.py`: greedy ≥ (1−1/e)·OPT on all 6 randomized trials).

**Result on the frozen 20-km catalogue holdout (Arms A/B/C + fold-0 development):**
MCLP placement trails fixed sep-4.0 packing on the *same* surface by 0.01–0.05 DTI in
every variant tried (raw, squared, floor-subtracted, σ∈{1,1.85,3} blurred,
top-200k binary, and training-calibrated demand). Best MCLP (calibrated, fold 0):
0.2051 vs packing 0.2423. Full 4-fold numbers are in `evidence/holdout_g43_mclp.json`.

**Mechanism (optimizer's curse on a miscalibrated map).** The hand-built surfaces are
rank-informative but magnitude-miscalibrated: SH's top score decile has only ~2%
training-truth rate versus ~0.5–1% elsewhere, while most surface mass sits in broad
mid-value flats and truth concentrates on sharp top-score ridges. MCLP faithfully covers
*mass* (spreading dots over flats, leaving zero-coverage gaps between ~6-px-spaced
dots); packing concentrates all 40k dots on the extreme score tail where truth density
is highest. The guarantee is honored — the surface is covered near-optimally — but the
surface is the wrong objective. This independently replicates GEMSDOE28's H37-1 lesson
(max-coverage gains were a catalogue-adjacency effect; tied on LOSFO far-field) on a
different surface and validator.

**Consequence for the research program:** placement optimization is downstream of
probability quality. The binding constraint is the DETECTOR (a calibrated P(fault)),
not the placer. A calibrated supervised surface + MCLP remains untested and is the
principled future combination; this round tests the supervised ranker with packing
(Arm D) because packing is the validated placer on this holdout.

## 5. Ranked paths to a higher live score (judgment, not measurement)

1. **Better detector, then mass discipline.** A supervised, calibrated multi-physics
   ranker (Arm D family) that beats H19-5/H42 at ranking, thinned/pruned to the
   0.2·DTI bar with live calibration. Only path with headroom to +18% credit density.
2. **Corroborated additions that clear the bar.** G28 H38-1 (heat-flow residual + Euler
   clusters) was the first addition arm to earn above-bar credit on far-field truth
   (0.069–0.077/dot vs bar ≈ 0.055). Additions must be this specific; generic layers
   earn 0.002–0.008/dot (G32 H33-1/H33-5, falsified).
3. **Operating-point pruning with live calibration.** The H33 direction; needs weekly
   slots to calibrate (each prune's safety factor comes from live anchors, not holdouts).
4. **Two-round objective.** Phase 2 adds expert review of Phase 1 submissions
   ([rules PDF §§3–5](https://docs.nlr.gov/docs/fy26osti/96647.pdf)); geologically
   coherent, interpretable submissions may survive review better than pure
   emission-geometry plays. Unquantifiable, but a tie-break argument for detector-first
   work.

## 6. Flagged report conflicts (manual review required)

- **IR-REPORT-01:** the owner brief lists H33-2-B2 at **0.2778** as scored, but
  GEMSDOE32's own site and PR #9 label H33-2-B2 **projected 0.2747, UNSCORED**, with no
  organizer score in the repository. Unresolved; do not cite either as organizer-confirmed.
- **IR-REPORT-02:** competing "highest score" claims: owner brief 0.3195; GEMSDOE32's
  2026-10-04 leaderboard read #1 0.3262 (nchuzhoy); G43 README's 2026-10-05 snapshot
  rank-1 0.3345. Different dates, different values, none current. The leaderboard was not
  re-read here per the DrivenData Terms of Use; check the
  [official page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
  directly in a browser.
