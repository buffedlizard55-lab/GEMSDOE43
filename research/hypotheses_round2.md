# G43 round-2 candidate slate — preregistered before implementation or scoring

**Registered:** 2026-10-06 UTC (round 2; round 1 was G43-CG01, a documented no-go).
**Checkout state at registration:** H42 four-colour 20-km holdout independently reproduced
(mean 0.250744 for `SH_basin_strong|sep4.0|N40000`); G43-CG01 scored 0.211567 (0/4 folds).
No round-2 holdout score has been computed or inspected at the time of writing.
**Decision rule:** same frozen protocol as round 1 (four-colour 20-km blocks, 3-px held-edge
guard, 2-px training-trace guard, equal 40,000-px mass, official 300-m triangular DTI without
the known-mask because held-out catalogue positives are the truth). A round-2 arm passes only
if its mean strictly exceeds the locally recomputed H42 reference mean **and** it wins at
least 3 of 4 folds. Passing is a necessary screen, not a public/private score forecast.
**“Novel” scope:** no identical operator was found in the bounded review of sibling GEMSDOE
repositories and this checkout; it is not a claim that no other competitor has tried it.

## Ranked candidates

Ranks are qualitative expected-value judgments (expected local-holdout gain per
implementation cost), not measured DTI forecasts. All five use only bands already present in
the mirrored `training_features.tif`; no new external download is required for any of them,
so every candidate is viable in this checkout today.

| Rank | ID / hypothesis | Inputs / physical signature | Why it may find faults absent from USGS/INGENIOUS | Difference from audited prior work | Expected DTI change / cost / data check |
|---|---|---|---|---|---|
| **1** | **G43-MCLP01 — lazy-greedy maximum expected coverage placement (Church–ReVelle)** | Any continuous [0,1] surface. Objective: expected covered demand Σ_j p_j · max_{i∈S} k(d_ij) with the official triangular kernel k(d)=max(1−d/3,0), d in 100-m cells; cardinality \|S\|=40,000. Solver: exact lazy (accelerated) greedy, Minoux 1978. | Placement, not geology: fixed-separation constants waste budget where the surface is broad and starve narrow ridges. Covering the probability surface optimally converts the *same* geology into more expected kernel credit per dot, including dots that land on blind structures the surface already highlights but fixed packing skips. | All G43 arms so far use fixed-separation `greedy_pack`. Siblings tried max-cover variants on other surfaces/validators: GEMSDOE32's smooth-maxcov was quarantined defective (57.8% of dots off its belief field; IR-34); GEMSDOE28 H37-1 passed interleaved (+0.0073) but tied on LOSFO far-field (−0.00004) and its projection was withdrawn. This test is distinct: 20-km blocked folds (far-field-like), exact lazy greedy on H42-SH and on a new triple-gradient surface, matched mass, preregistered gate. | **Highest expected value per cost**; medium cost (solver + 4-fold compute). No new data. Validate first (Arms A/B/C below). |
| **2** | **G43-MG01 — magnetic triple-gradient ridge conjunction** | Competition bands `tmi_hg`, `tmi_vg`, `rtp`. Mask-aware Gaussian σ=2 px; response = H42-style geometric mean (0.05 floor) of norm01(HG), norm01(\|VG\|), norm01(\|∇RTP\|). Rewards locations strong in horizontal gradient, vertical gradient, and RTP edge simultaneously. | A fault-juxtaposed susceptibility contact produces a magnetic edge visible in several derivatives at once; requiring triple agreement suppresses shallow noise, survey artifacts, and single-derivative ghosts, retaining weak/deep contacts under cover that never got mapped. | H42 used `tmi_hg` magnitude alone (+slope+scarp); CG01 used RTP-vs-gravity *vector alignment*; no audited operator required triple magnetic-derivative conjunction. | **Low-to-moderate**; low cost; bands in hand. Validated as Arms B (MCLP) and C (fixed packing) in this round. |
| **3** | **G43-BG01 — basement-step × gravity-gradient coupling** | Bands `depth_to_base_surf`, `iso_grav_anom`. Mask-aware Gaussian σ ∈ {2,4,8} px; per-scale sqrt(strength product) × \|cosine\| exactly as CG01, median across scales. | Basin-bounding normal faults step the basement under sedimentary cover where no scarp exists; the step appears jointly in basement depth and gravity. Independent of magnetics, so it catches non-magnetic cover faults CG01 is blind to. | CG01 coupled RTP-vs-gravity; this couples basement-depth-vs-gravity with the same frozen multi-scale form. | **Low-to-moderate**; low cost; bands in hand. Backup; run only after Arms A–C are decided. |
| **4** | **G43-GT01 — gravity structure-tensor lineament coherence** | Band `iso_grav_anom` (plus `iso_grav_anom_hg` as corroboration). Gradient structure tensor over a 7×7 window; response = linearity (λ1−λ2)/(λ1+λ2) × normalized gradient strength. | Fault-controlled density steps are straight and through-going; tensor linearity rejects circular/point anomalies (plutons, basins) that fool magnitude detectors, isolating unmapped linear boundaries. | All audited gravity uses are pointwise magnitudes or vector alignment; none use tensor geometry. | **Low, uncertain** (gravity is smooth at 100 m); low cost; bands in hand. Backup. |
| **5** | **G43-SC01 — dilational-strain × conductivity pathway conjunction** | Bands `geod_dilaterate`, `geod_shearrate`, `geod_2ndinv`, `cond_surf`. Positive-dilatation fraction × normalized shear × normalized 2nd invariant × upper-quantile conductivity, geometric mean with 0.05 floor. | Blind geothermal faults are permeable fluid pathways: active extension opens fractures and fluids raise conductivity. Targets transtensional conductive corridors with no mapped trace. | Prior work used earthquake density only as a covariate; H38-1 used heat-flow residual + Euler clusters; none combined the strain-rate tensor with MT conductance. | **Low, uncertain** (regional fields are smooth); low cost; bands in hand. Backup. |

## Preregistered round-2 validation (Arms A–C)

Only these three arms are authorized in this round. Surfaces, solver, folds, guards, mass,
metric, and gate are frozen in `registry/experiment_g43_mclp.json`:

- **Arm A (placement isolation):** H42 `SH_basin_strong` surface (rebuilt exactly as in round 1)
  + MCLP lazy-greedy @ N=40,000. Tests whether optimal covering beats fixed sep-4.0 packing
  on the *same* surface.
- **Arm B (new geology + placement):** MG01 triple-gradient surface + MCLP lazy-greedy
  @ N=40,000. Tests the most unique combination.
- **Arm C (geology isolation):** MG01 surface + existing fixed `greedy_pack` sep-4.0 @ N=40,000.
  Cheap control separating geology from placement.

**Reference:** recomputed `SH_basin_strong|sep4.0|N40000` in the same script run; the run aborts
unless it matches the frozen round-1 receipt (mean/min/max within 1e-6), guarding against
protocol drift. Historical H42 numbers are reused from `evidence/holdout_g43_cg01.json`
only after that match passes.

**Gate:** an arm passes iff (mean strictly greater than the recomputed H42 reference mean)
AND (fold wins ≥ 3/4). If several pass, the submission primary is the passing arm with the
highest mean (tie-break within 1e-6 prefers the new-geology arm for uniqueness). If none
pass, the round is a no-go for slot use; the owner-directed downloadable research artifact
policy is documented in the experiment registry entry.

## Scope and evidence limits

- Same limits as round 1: catalogue-blocked CV tests recovery of withheld *mapped* faults,
  not hidden organizer truth; organizer staff declined to disclose hidden-fault sources,
  types, or coverage. A holdout win licenses packaging, never a score claim.
- The MCLP (1−1/e) guarantee (Nemhauser–Wolsey–Fisher 1978) is relative to the optimum
  *over the preregistered candidate set* (top 300,000 cells by initial coverage gain) for
  covering the *surface*, not relative to covering hidden truth. It is a formal floor on
  placement quality, not a DTI forecast.
- Sibling max-cover history (G32 quarantine, G28 LOSFO tie) is a caution, not a verdict:
  both used different surfaces and different validators. The 20-km blocks here are the
  far-field-like instrument; results will be reported as measured.

## Source notes

1. Church, R.L. & ReVelle, C.S. (1974), “The Maximal Covering Location Problem,”
   *Papers in Regional Science* 32:101–118 — problem framing. Verified via the
   [2016 retrospective abstract](https://journals.sagepub.com/doi/abs/10.1177/0160017615600222)
   and [Springer reference record](https://link.springer.com/article/10.1007/BF01939922).
2. Nemhauser, Wolsey & Fisher (1978) — greedy (1−1/e) for monotone submodular maximization
   under a cardinality constraint. Verified via
   [Chekuri (UIUC) summary](http://chekuri.cs.illinois.edu/talks/crm_submodular.pdf) and
   [arXiv:2411.05553](https://arxiv.org/abs/2411.05553).
3. Minoux, M. (1978), “Accelerated greedy algorithms for maximizing submodular set
   functions” — lazy evaluation. Verified via
   [submodlib optimizer docs](https://submodlib.readthedocs.io/en/latest/optimizers/lazyGreedy.html)
   and [Mirzasoleiman et al. (AAAI-15) references](https://dl.acm.org/doi/10.5555/2886521.2886572).
4. Sibling evidence: [GEMSDOE32 docs](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
   (maxcov quarantine, credit-bar theory), [GEMSDOE32 PR #9](https://github.com/buffedlizard55-lab/GEMSDOE32/pull/9)
   (removal rule), [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) (H37-1 LOSFO result),
   [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) (H28 scatter model, dotting sweep).
5. Official task/metric/format: [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/);
   known-masked scoring: [staff reply](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2);
   hidden-truth non-disclosure: [staff reply](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7).
