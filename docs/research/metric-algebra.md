# Metric algebra — every claim this repository relies on, proved and tested

**Status:** proved here, and each identity is enforced by a unit test so a future refactor cannot
silently break it. Read 2026-10-06.

Official definition
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>, "Performance
metric"):

```
k(d)  = max(1 - d/R, 0),                       R = 300 m
TP_w  = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
FP_w  = sum_{x: p(x) > 0} p(x) [1 - max_{g in G} k(d(x,g))]
FN_w  = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) k(d(x,g))]
DTI   = TP_w / (TP_w + alpha FP_w + beta FN_w + eps),   alpha = 0.2, beta = 0.8
```

Write `T = TP_w`, `F = FP_w`, `G = |truth|`, `S = {x : p(x) > 0}`, `K = |S|`.

---

## Identity 1 — `FN_w = G − T`, so `DTI = T / (0.2T + 0.2F + 0.8G)`

`FN_w = Σ_{g∈G} (1 − m_g)` with `m_g = max_x p(x)k(d(x,g))`, and `T = Σ_{g∈G} m_g`. Summing the
two gives `G`. ∎ (`tests/test_metric.py::test_fn_equals_g_minus_tp`, verified against a
brute-force `O(N·M)` recomputation on three random grids.)

## Identity 2 — one emitted pixel raises the denominator by exactly `0.2 p`, whatever its credit

Emit a pixel at `x` with weight `p` whose best kernel credit against the truth is `k`.

* If `x` is the first pixel to claim that truth, `T → T + pk`.
* Its false-positive contribution is `p(1 − k)`, so `F → F + p(1 − k)`.
* By Identity 1, `D = 0.2T + 0.2F + 0.8G`, hence `ΔD = 0.2pk + 0.2p(1 − k) = 0.2p`.

The new index exceeds the old one iff

```
(T + pk) / (D + 0.2p)  >  T / D
  <=>  pk D > 0.2 p T
  <=>  k > 0.2 T/D  =  0.2 * DTI.
```

Two consequences, both used by the pipeline:

* **The rule does not depend on `p`.** Scaling the whole support by `λ ∈ (0,1]` gives
  `DTI(λ) = λT / (0.2λ(T+F) + 0.8G)` whose derivative in `λ` is
  `0.8 T G / (0.2λ(T+F) + 0.8G)² > 0`, so a graded probability map is **strictly dominated by its
  own thresholded support**: emit `p = 1`.
* **The stopping rule needs no tuned threshold.** Emit while the marginal credit exceeds
  `0.2 × DTI` — and since `DTI` itself depends on where we stop, the operating point is a fixed
  point (§Dinkelbach below).

(`tests/test_metric.py::test_denominator_identity_and_marginal_cost` constructs an isolated truth
pixel and checks `ΔD = 0.2p` exactly and the `k > 0.2s` decision rule for
`p ∈ {1.0, 0.7, 0.4}` at `k ∈ {1, 2/3, 1/3}`.)

## Identity 3 — `FP_w` is modular, and the disjoint-credit *reduction*

For a binary emission (`p = 1` on `S`),

```
F(S) = Σ_{i∈S} (1 − k_i),     k_i = max_{g∈G} k(d(i,g)).
```

`k_i` depends only on the truth set, never on which other dots were placed, so **`F` is a modular
function of `S`.** This is what makes the placement problem tractable.

Under the **disjoint-credit hypothesis** — each dot is credited against a distinct truth pixel, so
`Σ_i k_i = T` — the index reduces to

```
DTI_red = T / (0.2 K + 0.8 G).
```

### The reduction is *not* a bound (correction: IR-43-007)

It is tempting to read the reduction as a bound. It is not, and the sign of its error is known:

```
DTI = T / (0.2 T + 0.2 (K − Σ_i k_i) + 0.8 G)
```

* `Σ_i k_i > T` — several dots competing for the same truth pixel, the regime at `K > G` — makes the
  denominator **smaller** than `0.2K + 0.8G`, so the reduction is **pessimistic**;
* `Σ_i k_i < T` — fewer dots than truth pixels — makes the reduction **optimistic**.

Both regimes are pinned by tests
(`tests/test_metric.py::test_disjoint_credit_reduction_and_its_error_sign`). The quantity is
reported everywhere in this repository as the **reduction**, never as a bound and never as a
predicted score. The exact index from `Σ_i k_i` is available as
`metric.exact_dti_from_dot_credits`.

---

## Dinkelbach: deriving the cardinality instead of sweeping it

Maximise `R(S) = T(S)/D(S)` with `D(S) = 0.2T(S) + 0.2F(S) + 0.8G`. Dinkelbach's theorem for
fractional programs says that at the optimum value `s*` the maximiser of `R` also maximises the
parametric subproblem

```
max_S  T(S) − s* D(S)
     = (1 − 0.2 s*) T(S) − 0.2 s* Σ_{i∈S} (1 − k_i) − 0.8 s* G .
```

The last term is constant and `Σ_{i∈S}(1 − k_i)` is modular, so the subproblem is
**submodular + modular**: greedy is the natural solver, and the marginal condition for adding dot
`i` collapses to

```
accept  <=>  (1 − 0.2s) ΔT_i + 0.2 s k_i − 0.2 s  >  0
        <=>  ΔT_i > 0.2 s          (using ΔT_i = k_i for genuinely new credit)
```

which is exactly Identity 2's rule. Solved self-consistently by bisection on the monotone map
`s ↦ DTI(K(s))` in `mclp.emission_plan`.

**With the demand field substituted for the unknown truth** (`T̂(S) = Σ_x π(x) max_{i∈S} k(d(i,x))`)
the expected cost per dot is `0.2(ΔT̂ + 1 − E[k_i]) ≤ 0.2`, so the rule is conservative: it will
under-emit rather than over-emit relative to the true optimum.

---

## What a dot is worth, and where the headroom is

A dot sitting exactly on a straight fault trace delivers, along the trace,

```
k(0) + 2k(1) + 2k(2)  =  1 + 2(2/3) + 2(1/3)  =  3.0
```

of weighted credit. The group's best artifact (`GEMSDOE32 / h33-2-b2`, 37,654 dots,
owner-reported 0.2778) realises **0.126 per dot** — about **4 %** of that. The ceiling, with
perfect knowledge and dots spaced 3 px along the traces (≈ 4,200 dots for
`|G| ≈ 12,226`), is `T ≈ 0.8G` and `DTI ≈ 0.92`.

Inverting the index for the required weighted coverage `c = T/G` at false-positive ratio
`ρ = F/G`:

```
c = s (0.2 ρ + 0.8) / (1 − 0.2 s)
```

| target `s` | `ρ=0` | `ρ=0.5` | `ρ=1` | `ρ=2` |
|---:|---:|---:|---:|---:|
| 0.2778 (group best) | 23.5 % | 26.5 % | 29.4 % | 35.3 % |
| 0.3195 (brief's target) | 27.3 % | 30.7 % | 34.1 % | 41.0 % |
| **0.3345 (current #1)** | **28.7 %** | 32.3 % | 35.9 % | 43.1 % |

So the step from 0.2778 to 0.3345 is roughly **+22 % relative weighted coverage** of the hidden
fault set. That is a geology problem, which is why
[`h43-hypotheses.md`](h43-hypotheses.md) is the substantive part of this repository.

---

## Reproduction

```bash
PYTHONPATH=src python3 -m pytest tests/test_metric.py -q      # 12 tests
python3 - <<'PY'
def c(s, r): return s*(0.2*r+0.8)/(1-0.2*s)
for s in (0.2778, 0.3195, 0.3345):
    print(s, [round(100*c(s, r), 1) for r in (0, 0.5, 1, 2)])
print([round(0.2*s, 4) for s in (0.2778, 0.3195, 0.3345)])     # the marginal-credit bars
PY
```
