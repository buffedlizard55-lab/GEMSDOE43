# Round-2b amendment — MCLP falsified on fold-0 exploration; supervised + ensemble arms added

**Amended:** 2026-10-06 UTC, **before** any scored 4-fold round-2 run.
**Reason:** single-fold (fold 0) full-budget exploration showed every MCLP placement
variant trailing fixed packing by 0.01–0.05 DTI on the same surface. The preregistered
Arms A/B/C still run exactly as frozen; two backup arms (D/E) are added and judged on a
corrected gate because fold 0 was used for exploration.

## Fold-0 exploration log (development only; budget N=40,000 unless noted)

All runs use the frozen fold-0 geometry (evaluation interior, 2-px training guard) and the
official DTI without the known-mask. `REF` reproduces round 1 exactly (0.242272).

| Variant | Budget | TP | DTI (fold 0) | Verdict |
|---|---|---|---|---|
| REF: SH + sep4.0 packing | 40,000 | 4,878.3 | 0.242272 | reference |
| A-dev: SH + MCLP (raw surface demand) | 40,000 | 3,873.8 | 0.194901 | −0.0474, falsified |
| SH + MCLP (squared demand) | 40,000 | 3,803.4 | 0.191442 | sharpening hurts |
| SH + MCLP (σ=1.0/1.85/3.0 blurred demand) | 2,000 | 229/220/207 | 0.0191/0.0184/0.0172 | blur hurts monotonically (REF@2k: 0.0239) |
| SH + MCLP (floor-subtracted demand) | 2,000 | 240.6 | 0.0207 | ≈ raw (243.4), no fix |
| SH + MCLP (top-200k binary demand) | 2,000 | 128.1 | 0.0111 | diffusion, rejected |
| SH + MCLP (training-calibrated P(truth\|score) demand) | 40,000 | 4,083.4 | 0.205123 | best MCLP, still −0.037 |
| B-dev: MG01 + MCLP (raw) | 40,000 | 2,934.8 | 0.148401 | falsified |
| C-dev: MG01 + sep4.0 packing | 40,000 | 4,124.9 | 0.205849 | trails SH+sep4 |
| ENS(SH,MG01 50/50 geo-mean) + sep4.0 | 40,000 | 4,785.4 | 0.237797 | −0.0045, backup arm E |
| ENS + MCLP (raw) | 40,000 | 3,450.5 | 0.174000 | falsified |

## Mechanism (why MCLP loses here)

MCLP maximizes expected covered *surface mass* Σ p·coverage. The hand-built surfaces are
uninformative in magnitude: SH's top score decile has only ~2% training-truth rate versus
~0.5–1% elsewhere, and most surface mass sits in broad mid-value areas while catalogue
truth concentrates on sharp top-score ridges. Covering mass therefore spreads dots over
mid-value flats (and leaves zero-coverage gaps between ~6-px-spaced dots), while
score-descending packing with 4-px exclusion concentrates all 40k dots on the extreme
score tail where truth density is highest. Calibration helps (0.195→0.205) but cannot fix
the flatness: P(truth\|score) varies only ~4× across deciles. The (1−1/e) guarantee is
honored — it covers the *surface* near-optimally — but the surface is the wrong objective
for catalogue truth. This replicates GEMSDOE28's H37-1 lesson (max-coverage gains were a
catalogue-adjacency effect, tied on LOSFO far-field) on an independent surface and on
20-km blocks.

## Added arms (frozen here, before the scored run)

- **Arm D — G43-SUP01:** per-fold supervised ranker. Features (21): the 19 competition
  bands in band order + LiDAR scarp evidence (0-imputed where invalid) + scarp-validity
  flag. Train cells: training region ∩ bands-valid; labels: training catalogue.
  Model: `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06,
  max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0,
  class_weight='balanced', early_stopping=True, validation_fraction=0.1,
  n_iter_no_change=20, random_state=20261006)`. Emission: `greedy_pack(P(truth),
  allowed ∩ bands-valid, sep=4.0, N=40,000)`. Rationale: supervised ranking can learn
  band interactions (incl. scarp) that hand-built geometric means miss; ranks only, so no
  calibration step is needed for packing. No coordinates (useless 20 km from training
  data), no labels outside the training region, early-stopping split drawn from training
  data only.
- **Arm E — G43-ENS01:** 50/50 H42-style geometric mean of SH and MG01 surfaces (both
  [0.05,1] on valid cells), `greedy_pack(sep=4.0, N=40,000)` on `allowed ∩ mg_valid`.
  Rationale: closest fold-0 backup (−0.0045); tests whether magnetic triple-gradient adds
  recall where scarp is weak. Weights fixed at 50/50 here (no weight tuning — the single
  tested value is frozen to avoid further selection).

## Corrected gate (selective-inference correction)

Fold 0 was used to *select* arms D/E, so its scores are optimistic for them. Arms D/E are
therefore judged on folds 1–3 only: pass requires winning **3/3 of folds 1–3** against the
recomputed H42 reference **and** mean(folds 1–3) strictly greater than the reference
mean(folds 1–3). Fold 0 is reported for all arms but excluded from the D/E gate.
Preregistered arms A/B/C (specified before any round-2 score was inspected) keep the
original gate: mean(4 folds) strictly greater + ≥3/4 fold wins. Primary selection: among
all passing arms, highest 4-fold mean (tie within 1e-6 prefers the newest geology:
D > E > B > A).

## Provenance note

`scikit-learn==1.9.1` (CPU `HistGradientBoostingClassifier`, BSD-3 license) is added to
`requirements.txt` for Arm D. The scarp layer's owner-mirror caveat still applies; Arm D
uses it as a model feature with the same documented provenance as the H42 baseline.
