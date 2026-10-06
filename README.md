# GEMSDOE43 — Maximal-covering (MCLP) emission for the DOE GEMS Prize Challenge

**Competition:** [The Geologic Enhanced Mapping System (GEMS) Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/) (DrivenData #306)
**Metric:** distance-weighted Tversky index, `k(d) = max(1 − d/300 m, 0)`, `α = 0.2`, `β = 0.8`
**This repository's method:** solve the *placement* problem as the **Maximal Covering Location
Problem** (Church & ReVelle, 1974) on a continuous probability surface, with the number of points
derived from the metric's own marginal-credit rule instead of a swept spacing constant.

> ## ⬇ Download the submission
>
> **`docs/downloads/` → the `…-zeros.tif` file at the top of
> [Executive summary](docs/executive-summary.html).**
> Single-band float32 GeoTIFF, EPSG:32611, 100 m, 3730 × 3292, values in `[0, 1]`, NaN outside the
> footprint. A `.zip` and a NaN-outside twin with bit-identical in-footprint values are next to it.
> Copy the *submission note* from the same page into the portal's "Note" field.

---

## 🧭 Read this first, every session — the standing owner brief (verbatim)

The following is the owner's standing brief for this project. It is reproduced here so that every
session starts from the same target.

> Review the repo.
>
> **THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!**
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
> UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. The
> submission must be different than the collection of gemsdoe sites below.
>
> There should be an easy to download submission tif file as described by the prompt. Read the
> entire prompt.
>
> **Stop guessing spacing constants — solve the actual placement optimization.** Your own data
> already shows this matters: every "d2-8"-labeled variant beats its "d1-5" sibling, and
> GEMSDOE32's best result is itself just one more hand-picked constant. The underlying problem has
> a name and a formal solution: Church and ReVelle's Maximal Covering Location Problem (Papers in
> Regional Science, 1974) asks exactly this question — given a fixed number of points and a
> coverage radius, which locations maximize the demand covered — and it maps onto this
> competition's scoring almost exactly, since DTI's true-positive credit is a max over the same
> kind of fixed radius (300 m) around each predicted point. Don't sweep spacing constants; solve
> the covering problem directly on your continuous probability surface using the submodular greedy
> algorithm Church and ReVelle describe, which carries a proven (1 − 1/e) ≈ 63% worst-case
> guarantee relative to the true optimum — a formal floor no hand-picked spacing constant carries.
> Normalize to [0,1], write the required single-band float32 GeoTIFF (EPSG:32611, 100 m, matching
> shape/geotransform, NaN outside the footprint), and verify the chosen point set isn't a
> near-duplicate of any prior submission's layout before presenting it for download.
>
> … **WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMSDOE SITE** —
> `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778` — **Why and how did this get the highest
> score and are we able to generate a submission that scores higher than 0.2778?**
>
> Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each
> naming: the specific layer(s) involved, the physical signature being targeted (e.g., an
> edge-detection or curvature transform), why it should catch a fault missing from the
> USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already
> implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate
> the top candidate on our spatially-blocked holdout set before touching a weekly submission slot
> — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a
> candidate can't be validated without new external data, name the specific free, official source
> needed and check it's obtainable before proposing the idea as viable.
>
> Work line by line verifying from official verified trusted sources, provide links for manual
> review. There should be no manual input, work on your own to complete tasks. Flag any
> irregularities for review. **No hallucinations.** Verify no hallucinations.
>
> **0.3195 is the highest score right now** so we need to design a new strategy … We need to come up
> with distinct and unique strategies to score higher in this competition leaderboard. We need to
> start doing heavy and deep research into the part of the project that matters the most, which is
> the scientific discovery of geothermal vents. We should store all of our information and
> knowledge that we can gather from official verified sources. We need to think outside the box
> but still be grounded in proper scientific research … We need to find sources of data that
> others are overlooking or areas of the project when it comes to geothermal vents.
>
> Put this prompt into the repo readme and read it everytime we work on the project as a starting
> point …
>
> We need to focus on being able to generate a submission into the competition. The site should be
> able to generate a TIF file that is required for submission. It should be as easy as download to
> click a File to submit into the competition. This needs to be in the executive summary or the
> very beginning of the site. It should be obvious when you visit the site.
>
> I tried to submit the document that i downloaded from the site but it returned this error on the
> submission form: **"Predicted values must be in range [0, 1]"**. Also we need to give it a unique
> name and A short comment to help you or your team tell submissions apart later.
>
> Create a executive summary subpage that explains exactly how to make a submission into the
> contest.
>
> Work on the next steps from the previous sessions first. … Tell me what are your limitations and
> what you need access to during this project. We will need to find free publicly available sources
> and data from official and verified sources if we are to use 3rd party or external data.
>
> Run this task through multiple passes. Pass 1: Implement the task completely and verify the
> result. Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge
> cases. Fix everything you find. Pass 3: Re-check the entire implementation against the original
> request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.
> Do not stop after the first pass. … Go ahead and create a pull request and then merge the pull
> request onto the main. Make suggestions for what work still needs to be done and any limitations
> that is in the way of a successful project.

### Arena core values applied to this project

* **Maximize P(win).** Every decision is weighed against the probability of a top-5 finish. The
  binding constraint is not code quality, it is *which geological hypothesis survives contact with
  an unknown label set* — so the budget goes there first, and every submission is gated on a
  measured holdout margin rather than on a plausible story.
* **Own the outcome.** The pipeline is end-to-end and fail-closed: data fetch → channels → prior
  surface → MCLP placement → blocked validation → GeoTIFF → independent re-read audit →
  near-duplicate screen. If a stage cannot verify itself it aborts rather than shipping.

---

## 1. What the competition asks, and the exact metric

[OFFICIAL, read 2026-10-06](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

```
k(d)  = max(1 - d/R, 0),                       R = 300 m
TP_w  = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
FP_w  = sum_{x: p(x) > 0} p(x) [1 - max_{g in G} k(d(x,g))]
FN_w  = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) k(d(x,g))]
DTI   = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)
```

Implemented verbatim in [`src/gems43/metric.py`](src/gems43/metric.py) and tested against the
organizer's own worked example (`TP_w=3.00, FP_w=1.89, FN_w=2.00 → 0.60`) and against a
brute-force `O(N·M)` re-derivation (`tests/test_metric.py`).

Three consequences drive the whole design (all proved in
[`docs/research/metric-algebra.md`](docs/research/metric-algebra.md) and unit-tested):

| # | Consequence | Use |
|---|---|---|
| 1 | `FN_w = \|G\| − TP_w`, so `DTI = T / (0.2T + 0.2F + 0.8\|G\|)` | the index is a ratio of two functions of the emitted set |
| 2 | Adding a pixel of weight `p` raises the denominator by **exactly `0.2 p`** whatever its credit, so the move pays iff **credit `k > 0.2·DTI`** — independent of `p` | binary (`p=1`) emission is optimal; gives the stopping rule with no tuned threshold |
| 3 | `FP_w = \|S\| − Σ_i k_i` is **modular** in the emitted set; under the disjoint-credit hypothesis the index reduces to `T/(0.2\|S\| + 0.8\|G\|)` | for a fixed dot count the problem is **exactly** MCLP |

## 2. Why MCLP, and why it is not a metaphor

Church, R. and ReVelle, C. (1974) *The maximal covering location problem*, Papers of the Regional
Science Association 32: 101–118 — <https://link.springer.com/article/10.1007/BF01942293>.

The competition's `TP_w` is `Σ_g max_i k(d(i,g))` with a fixed 300 m support: literally "demand
covered by a set of facilities of service radius R". Substituting the unknown truth set by its
posterior mean `π(x)` gives the demand field

```
T(S) = Σ_x π(x) · max_{i∈S} k(d(i,x))
```

which is **monotone submodular**, so Church & ReVelle's greedy inherits the
Nemhauser–Wolsey–Fisher `(1 − 1/e) = 0.6321` worst-case guarantee against the true optimum. No
hand-picked spacing constant carries any such floor.

What is **not** textbook here, and is this repository's contribution:

1. The demand is a *continuous probability field*, not discrete demand nodes, and coverage is a
   **graded triangular kernel**, so the solver tracks the exact residual credit
   `max(0, k(δ) − C(x))` at every pixel — two overlapping facilities are credited only once.
2. The cardinality **K is derived, not swept**. Consequence 2 gives the rule "emit while marginal
   coverage `> 0.2·s`"; since `s` depends on where we stop, the operating point is the fixed point
   of a **Dinkelbach** stationarity condition. One greedy pass produces the whole marginal-gain
   path, and the budget is read off it — see [`src/gems43/mclp.py`](src/gems43/mclp.py).
3. The candidate sites are constrained to an arbitrary mask (scoring footprint, off the catalogue).

## 3. Why the previous best (0.2778) scored, and where the headroom is

`GEMSDOE32 / h33-h33-2-b2` = 37,654 dots, 0 within 200 m of the catalogue, owner-reported 0.2778.
Inverting the metric through that project's live anchor gives
`TP_w ≈ 5,073`, `|G| ≈ 12,226` hidden truth pixels, weighted recall **0.415**, mean credit per dot
**0.126**.

A dot sitting *on* a hidden fault delivers `1 + 2(2/3) + 2(1/3) = 3.0` credit along a straight
trace. The shipped emission realises **0.126** per dot — about **4 % of what a well-placed dot is
worth**. The ceiling, with perfect knowledge and dots every 3 px along the traces (≈ 4,200 dots),
is `DTI ≈ 0.92`.

So the gap between 0.2778 and the top of the board is **not an emission-quality gap and not a
spacing-constant gap — it is a coverage gap**. That is exactly what MCLP optimises, and it is why
the placement solver, not another thinning radius, is the lever.

## 4. Repository layout

```
registry/data_manifest.json   23 hash-pinned input mirrors (sha256, byte count, source repo@ref)
registry/channels.json        provenance of every derived channel (band -> transform -> hypothesis)
scripts/fetch_mirrors.sh      download + verify every input; exits non-zero on any digest mismatch
scripts/build_channels.py     19 official bands + external rasters -> 62 named channels
scripts/run_pipeline.py       surfaces -> MCLP -> blocked validation -> evidence JSON
scripts/build_submission.py   write + verify + audit the GeoTIFF(s), novelty screen
scripts/fetch_prior_submissions.sh   collect prior GEMSDOE artifacts for the duplicate screen
src/gems43/                   metric, grid, bands, features, channels, surface, mclp,
                              holdout, submission, novelty
docs/                         GitHub Pages site (executive summary first)
evidence/                     machine-readable receipts for every experiment
```

## 5. Reproduce

```bash
bash scripts/fetch_mirrors.sh                                   # 23/23 sha256-verified
PYTHONPATH=src python3 scripts/build_channels.py                # ~75 s, 62 channels
PYTHONPATH=src python3 scripts/run_pipeline.py --k-max 60000    # MCLP + blocked validation
PYTHONPATH=src python3 scripts/build_submission.py              # GeoTIFF + audit + novelty screen
PYTHONPATH=src python3 -m pytest tests -q                       # unit + property tests
```

Data placement: `bash scripts/fetch_mirrors.sh` fetches the hash-pinned mirrors into
`.cache/gems_data/` (no DrivenData login is used; see §7).

## 6. Current status

**Shipped:** `docs/downloads/gemsdoe43-mclp-supoof-51053-20261006T114256Z-zeros.tif`
(820,001 bytes, sha256 `63c9239a7eb473c3…`). 51,053 dots, 0 of them on a known catalogue pixel,
0 of them outside the scoring footprint. All 12 required format checks pass on an independent
re-read of the written bytes (`evidence/submission.json`), including `bounds_match_template`:
the written raster's bounds are `(243350, 4135550, 572550, 4508550)`, identical to the
organizer's `sample_submission.tif`.

> **A geotransform bug was found and fixed in review (pass 2).** `TRANSFORM` is stored in
> rasterio `Affine` order `(a, b, c, d, e, f)`; passing it to `Affine.from_gdal` permutes it into
> a silently valid but wrong geotransform whose bounds reach `1.7e10`. It shipped once because
> the check compared `transform.to_gdal()` back against `TRANSFORM` — and `to_gdal` is the
> inverse permutation, so it round-tripped the error and always matched. Both the writer and the
> check are fixed, and `tests/test_submission.py::test_transform_matches_the_template` asserts
> the numeric bounds against the mirrored template so it cannot recur.

* Leaderboard read **2026-10-06**: #1 `alexoktaba` **0.3345**, #2 `nchuzhoy` 0.3262, #3
  `kinghorton42` 0.3222, #4 Batik Shirt Brothers 0.3218, #5 `DARD` **0.3195**.
  **Irregularities:** the brief says "0.3195 is the highest score right now"; on today's page
  0.3195 is rank 5 (IR-43-001). No GEMSDOE\* team appears in the visible top 25, so the
  brief's own-best 0.2778 cannot be matched to a board row (IR-43-010).
* Group best (owner-reported, not organizer-authenticated): **0.2778** (`GEMSDOE32/h33-2-b2`).

### Measured holdout margins of the shipped layout

Reference bar = the mean blocked-holdout DTI of the best artifact that carries a known live
score, measured on the same frames.

| frame family | what is withheld | shipped `sup_oof` | reference bar | margin |
|---|---|---:|---:|---:|
| A | catalogue components, held out by spatial block | **0.1446** | 0.1087 (`D2.8`, live 0.2600) | **+33 %** |
| B | SGMC faults absent from the catalogue | 0.2258 | 0.0870 (`TGC`, live 0.2449) | +160 % |
| C | catalogue components with a 300 m flank deleted | **0.1583** | 0.1160 (`D2.8`) | **+36 %** |

Frame B is **excluded from selection**: its truth set *is* the SGMC external inventory, so any
surface built from SGMC scores well on it by construction. `lf_ext_sgmc` tops the raw
14 × 6 grid at 0.1968 for exactly that reason and is **not** shipped.

The instrument itself is published with its p-value rather than asserted: Spearman ρ of each
frame against the known live scores over n = 8 distinct scored artifacts is A +0.18 (p = 0.67),
B +0.46 (p = 0.26), C +0.18 (p = 0.67). **None is significant at n = 8.** These are screens that
order candidates, not evidence of a leaderboard gain, and nothing here is described as a
predicted score. (An earlier run counted duplicate copies of the same file and reported
B ρ = +0.67, p = 4e-5; those numbers were double-counting and are not quoted.)

### Did it clear the repository's preregistered promotion gate?

The repo already carried a preregistered four-fold protocol with a promotion gate
(`registry/experiment.json`) and a **NO_GO** record for a different arm, G43-CG01 (0.2116 vs the
reproduced H42 baseline 0.2507; 0/4 fold wins). This submission's prior was scored on that *same*
protocol — 200-cell blocks, 3-px edge guard, 2-px training-trace guard, official 300 m
triangular-kernel DTI — at **equal mass 40,000** on the **same** allowed emission domain:

| arm | mean DTI | min fold | max fold | folds won |
|---|---:|---:|---:|---:|
| `sup_oof` prior, `sep3.0`, N=40,000 | **0.286388** | 0.275090 | 0.297811 | **4 / 4** |
| `SH_basin_strong\|sep4.0\|N40000` (H42 baseline) | 0.250744 | — | 0.258025 | — |

Both substantive gate conditions pass (mean strictly exceeds the reference; ≥3 of 4 fold wins),
and the candidate's worst fold (0.2751) is above the reference's best fold (0.2580).

**Two caveats, both material.**

1. An earlier comparison of the shipped 51,053-dot full-grid layout against the same reference
   scored 0.219994 and won 0/4 folds — but it had only ~13.7k of its dots inside each fold's
   allowed domain against the reference's 40,000, so that was a **mass artefact, not a result**.
   It is recorded rather than quietly dropped.
2. The shipped file is emitted by the maximal-covering solver with **no separation constraint**
   and a Dinkelbach-derived budget; *that exact emission has not yet been scored at equal mass on
   this protocol.* The prior is validated; the specific placement is not. This is the top item of
   remaining work.

Both records are kept in `evidence/submission_status.json` — the earlier NO_GO is preserved under
`superseded_by` rather than overwritten. Truth here is withheld *published-catalogue* faults, not
the hidden competition label set: a screen, not a score forecast.

### Uniqueness of the point set

221 prior GEMSDOE rasters of the correct grid were collected from 45 `GEMSDOE*` repositories and
compared: 175 published submissions, 20 inputs/derived assets, 26 experiment intermediates.

| class | n | worst coverage IoU | worst excess containment | verdict |
|---|---:|---:|---:|---|
| submissions | 175 | **0.181** | 0.26 | **PASS — no near-duplicate** |
| inputs / assets | 20 | 0.214 | 0.47 | overlap expected, not a duplicate |
| intermediates | 26 | 0.172 | 0.14 | PASS |

The deciding statistic is the **coverage IoU** — both dot sets dilated by the competition's own
300 m kernel, then compared — thresholded at 0.50. A 1-pixel translation or a 10 % dot jitter both
score above 0.90, so a re-upload wearing a different hash would be caught. Raw 300 m containment
is reported but not thresholded, because with K dots of 29-cell support in N eligible cells two
unrelated layouts already overlap by `1 − (1 − 29/N)^K`, which is 0.25 at K = 51k and 0.63 at
K = 176k; a flat 0.60 containment threshold flagged 26 unrelated artifacts before it was retired
in favour of the **excess over chance**, `(observed − chance)/(1 − chance)`.

## 7. Limitations and what is needed to remove them

| Limitation | Status | What would remove it |
|---|---|---|
| DrivenData login | **absent**; the official data page redirects to login | the organizer's `training_features.tif`/`labels.tif`; we use owner-maintained public mirrors pinned by sha256 (§Sources). Every conclusion is labelled `[MIRROR, hash-pinned]` rather than `[OFFICIAL]`. |
| GPU / RAM | 2 vCPU, ~3.9 GB, no GPU | a GPU would allow a U-Net on the 19 bands; the reference solution's approach. Currently a gradient-boosted model over 62 derived channels. |
| The hidden label set | **by design unknowable** | nothing. Every local instrument is a proxy and is labelled as such. |
| Outbound network | `curl` to `drivendata.org`, `usgs.gov`, `openei.org`, `docs.nlr.gov`, `earthquake.usgs.gov` all return HTTP 000 from this sandbox | a machine without the egress allow-list, for: the official rules PDF, the USGS FDSN earthquake catalogue (hypothesis H43-3 upgrade), and the INGENIOUS 2 m temperature-probe archive. Fetchers are provided; nothing is fabricated in their absence. |

## 8. Sources (official, for manual review)

| Fact | Source |
|---|---|
| Metric, submission format, competition structure | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| Public leaderboard | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |
| Known faults masked from scoring | DrivenData staff `chrisk-dd`, <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516> |
| Official rules PDF | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (host unreachable from this sandbox — URL recorded, contents `[UNVERIFIED]`) |
| Reference solution (writes an all-finite, nodata-free raster) | <https://github.com/drivendataorg/gems-prize-reference-solution> |
| GeoDAWN survey (the study area) | <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>, <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> |
| INGENIOUS project (labels + thermal data) | <https://gbcge.org/current-projects/ingenious/>, <https://gdr.openei.org/submissions/1391> |
| Church & ReVelle (1974) | <https://link.springer.com/article/10.1007/BF01942293> |
| Analytic signal (contact mapping) | Nabighian (1972) *Geophysics* 37(6); Roest, Verhoef & Pilkington (1992) *Geophysics* 57(1) |
| Frangi vesselness | Frangi et al. (1998), MICCAI / *IEEE TMI* 17(4) |
| Tilt angle / tilt-depth | Miller & Singh (1994) *Geophysics*; Salem et al. (2007) *Geophysics* 72(2) |
| Submodular greedy guarantee | Nemhauser, Wolsey & Fisher (1978), *Math. Programming* 14 |

*Last verified: 2026-10-06.*
