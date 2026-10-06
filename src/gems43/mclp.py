"""Church & ReVelle's Maximal Covering Location Problem, solved on the continuous demand field.

Reference
---------
Church, R. and ReVelle, C. (1974), "The maximal covering location problem",
*Papers of the Regional Science Association* 32, 101--118.
<https://link.springer.com/article/10.1007/BF01942293>

The fit to this competition is exact rather than metaphorical, and it is worth stating precisely
because the rest of the package depends on it.  The official index is

    DTI(S) = T(S) / (0.2*T(S) + 0.2*F(S) + 0.8*|G|),   T = TP_w,  F = FP_w

(see ``gems43.metric``).  Two facts turn this into MCLP:

1. ``F(S) = sum_{i in S} (1 - k_i)`` with ``k_i = max_{g in G} k(d(i,g))`` is a *modular*
   function of S -- it does not depend on which other dots were placed -- and it satisfies
   ``F(S) <= |S| - T(S)``, with equality whenever distinct dots are credited against distinct
   truth pixels.  Hence

       DTI(S) <= T(S) / (0.2*|S| + 0.8*|G|)                                        (bound)

   and for a **fixed** number of dots ``|S| = K`` the placement problem is *exactly* "maximise
   the demand covered by K facilities of service radius R" -- MCLP.

2. ``T(S) = sum_x pi(x) * max_{i in S} k(d(i,x))`` is a weighted max-coverage function of the
   demand field ``pi``: non-negative, monotone and **submodular**.  Church & ReVelle's greedy
   therefore inherits the Nemhauser--Wolsey--Fisher ``(1 - 1/e) = 0.6321`` worst-case guarantee
   against the true optimum -- a formal floor that no hand-picked spacing constant carries.

What is not textbook here
-------------------------
* The demand is a continuous probability field, not a discrete list of demand nodes, and the
  coverage is a **graded triangular kernel** rather than an all-or-nothing disc.  The solver
  tracks the exact residual credit ``max(0, k(delta) - C(x))`` at every demand pixel, so two
  overlapping facilities are credited only once.
* The facility sites are constrained to an arbitrary candidate mask (footprint, off-catalogue).
* The cardinality ``K`` is **derived, not swept**.  Because the denominator rises by exactly
  ``0.2`` per emitted dot whatever the dot's credit, a dot is worth emitting iff its marginal
  coverage exceeds ``0.2 * DTI``.  That is a Dinkelbach stationarity condition on the ratio
  objective; solving it self-consistently (``emission_plan``) removes the last free constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .grid import KERNEL_W, OFFSETS, SHAPE, shift

NEG_INF = -np.inf
RAD = 3                       # Chebyshev radius of the 300 m kernel on a 100 m grid
UPD = 2 * RAD                 # candidates whose marginal gain a new dot can change: +-6 px

__all__ = ["CoverSolution", "greedy_cover", "emission_plan", "dinkelbach_budget"]


@dataclass
class CoverSolution:
    """Result of one greedy covering run."""

    order: np.ndarray                  # (K,) flat indices, in acceptance order
    marginal: np.ndarray               # (K,) marginal coverage gained by each acceptance
    cumulative: np.ndarray             # (K,) cumulative covered demand T(1..K)
    total_demand: float                # sum of the demand field (the assumed |G|)
    n_candidates: int
    guarantee: float = 1.0 - np.e ** -1
    meta: dict = field(default_factory=dict)

    @property
    def k(self) -> int:
        return int(self.order.size)

    def dti_bound(self, n_truth: float | None = None, k: int | None = None) -> float:
        """Consequence-3 bound ``T(K) / (0.2*K + 0.8*|G|)`` evaluated at cardinality ``k``."""
        kk = self.k if k is None else int(k)
        G = self.total_demand if n_truth is None else float(n_truth)
        return float(self.cumulative[kk - 1] / (0.2 * kk + 0.8 * G))


def _offsets_active():
    return [(int(dr), int(dc), float(w)) for (dr, dc), w in zip(OFFSETS, KERNEL_W) if w > 0.0]


def coverage_potential(prior32: np.ndarray) -> np.ndarray:
    """``P[j] = sum_delta w(delta) * prior(j + delta)`` -- demand a single isolated dot covers."""
    out = np.zeros(prior32.shape, dtype=np.float32)
    buf = np.empty(prior32.shape, dtype=np.float32)
    for dr, dc, w in _offsets_active():
        np.multiply(shift(prior32, dr, dc, out=buf), w, out=buf)
        out += buf
    return out


def marginal_gain(prior32: np.ndarray, credit32: np.ndarray) -> np.ndarray:
    """``G[j] = sum_delta prior(j+delta) * max(0, w(delta) - C(j+delta))`` for every pixel."""
    out = np.zeros(prior32.shape, dtype=np.float32)
    sp = np.empty(prior32.shape, dtype=np.float32)
    sc = np.empty(prior32.shape, dtype=np.float32)
    tmp = np.empty(prior32.shape, dtype=np.float32)
    for dr, dc, w in _offsets_active():
        shift(prior32, dr, dc, out=sp)
        shift(credit32, dr, dc, out=sc)
        np.subtract(w, sc, out=tmp)
        np.maximum(tmp, 0.0, out=tmp)
        tmp *= sp
        out += tmp
    return out


def greedy_cover(
    prior,
    candidate,
    k_max: int,
    *,
    min_potential: float = 0.0,
    max_candidates: int = 700_000,
    verbose: bool = False,
    log_every: int = 5000,
    strict_grid: bool = True,
) -> CoverSolution:
    """Church--ReVelle greedy for graded-kernel weighted max coverage (exact, not lazy).

    Parameters
    ----------
    prior : (H, W) float
        Non-negative demand field.  ``prior.sum()`` should equal the expected number of truth
        pixels ``|G|`` so the marginal-credit rule is on the metric's own scale.
    candidate : (H, W) bool
        Pixels eligible to host a dot (typically: inside the footprint, off the catalogue).
    k_max : int
        Maximum number of dots to place.
    min_potential : float
        Drop candidates whose isolated coverage potential is below this value.  Sound because
        marginal gains are non-increasing in the accepted set (submodularity): a pixel that
        cannot clear the bar with an empty accepted set can never clear it later.
    max_candidates : int
        Compute guard on the candidate pool; the ``(1-1/e)`` guarantee holds for the pool that
        is actually searched, which is reported in ``CoverSolution.n_candidates``.
    """
    prior32 = np.ascontiguousarray(prior, dtype=np.float32)
    H, W = prior32.shape
    if strict_grid:
        assert (H, W) == SHAPE, f"prior must be on the frozen grid {SHAPE}, got {(H, W)}"
    cand = np.asarray(candidate, dtype=bool)
    assert cand.shape == (H, W), "candidate mask must match the prior grid"

    # ------------------------------------------------------------------ candidate pool
    potential = coverage_potential(prior32)
    elig = cand & (potential > min_potential)
    n_elig = int(elig.sum())
    if n_elig == 0:
        raise ValueError("no eligible candidates")
    if n_elig > max_candidates:
        pv = potential[elig]
        thresh = np.partition(pv, n_elig - max_candidates)[n_elig - max_candidates]
        elig &= potential >= thresh
    cand_flat = np.flatnonzero(elig.ravel()).astype(np.int64)
    n_cand = int(cand_flat.size)

    inv = np.full(H * W, -1, dtype=np.int64)
    inv[cand_flat] = np.arange(n_cand, dtype=np.int64)

    credit = np.zeros((H, W), dtype=np.float32)        # C(x): best credit delivered so far
    gain = marginal_gain(prior32, credit)
    g = gain.ravel()[cand_flat].astype(np.float32).copy()   # compact view over the pool
    del gain, potential, elig

    off = _offsets_active()
    k_max = min(int(k_max), n_cand)
    order = np.empty(k_max, dtype=np.int64)
    marg = np.empty(k_max, dtype=np.float64)
    cum = np.empty(k_max, dtype=np.float64)
    running = 0.0
    n_done = k_max


    for step in range(k_max):
        pos = int(np.argmax(g))
        best = float(g[pos])
        if not np.isfinite(best) or best <= 0.0:
            n_done = step
            break
        idx = int(cand_flat[pos])
        r, c = divmod(idx, W)

        # ---- accept: raise the credit field across this dot's kernel support
        for dr, dc, w in off:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and w > credit[rr, cc]:
                credit[rr, cc] = w

        running += best
        order[step] = idx
        marg[step] = best
        cum[step] = running

        # ---- refresh the compact gains of every candidate whose disc can see the new credit
        br0, br1 = max(0, r - UPD), min(H, r + UPD + 1)
        bc0, bc1 = max(0, c - UPD), min(W, c + UPD + 1)
        nr, nc = br1 - br0, bc1 - bc0
        rows = np.arange(br0, br1)[:, None]
        cols = np.arange(bc0, bc1)[None, :]
        newgain = np.zeros((nr, nc), dtype=np.float32)
        for dr, dc, w in off:
            sr = np.clip(rows + dr, 0, H - 1)
            sc_ = np.clip(cols + dc, 0, W - 1)
            valid = ((rows + dr >= 0) & (rows + dr < H) & (cols + dc >= 0) & (cols + dc < W))
            diff = w - credit[sr, sc_]          # residual credit per unit demand
            np.maximum(diff, 0.0, out=diff)
            diff *= prior32[sr, sc_]
            diff[~valid] = 0.0
            newgain += diff
        flat = (rows * W + cols).ravel()
        posn = inv[flat]
        m = posn >= 0
        g[posn[m]] = newgain.ravel()[m]
        g[pos] = NEG_INF            # a pixel is emitted at most once

        if verbose and (step + 1) % log_every == 0:
            print(f"  [mclp] {step + 1:>7d} dots | cumulative demand covered {running:,.1f}",
                  flush=True)

    return CoverSolution(
        order=order[:n_done], marginal=marg[:n_done], cumulative=cum[:n_done],
        total_demand=float(prior32.sum()), n_candidates=n_cand,
        meta={"min_potential": min_potential, "n_eligible_before_cap": n_elig,
              "k_max_requested": k_max},
    )


def emission_plan(
    sol: CoverSolution,
    n_truth: float | None = None,
    target: float | None = None,
    tol: float = 1e-7,
    max_iter: int = 80,
) -> dict:
    """Choose the cardinality from the metric's own marginal rule, self-consistently.

    A dot is worth emitting iff its marginal coverage exceeds ``0.2 * DTI`` (metric consequence 2;
    independent of the dot's weight).  Since ``DTI`` depends on where we stop, the operating point
    is the fixed point of

        K*     = max { K : marginal[K] > 0.2 * s* }
        s*     = T(K*) / (0.2*K* + 0.8*|G|)

    a Dinkelbach stationarity condition for the ratio objective, solved by bisection on the
    monotone map ``s -> DTI(K(s))``.  If ``target`` is given, the bar is evaluated at that
    design score instead -- a stated target, not a fitted constant.
    """
    G = sol.total_demand if n_truth is None else float(n_truth)
    K = sol.k
    T = sol.cumulative
    ks = np.arange(1, K + 1, dtype=np.float64)
    dti_at = T / (0.2 * ks + 0.8 * G)

    if target is not None:
        bar = 0.2 * float(target)
        k_star = int(np.sum(sol.marginal > bar))
        s_used = float(target)
    else:
        lo, hi, s = 0.0, 1.0, 0.3
        for _ in range(max_iter):
            s = 0.5 * (lo + hi)
            k_star = int(np.sum(sol.marginal > 0.2 * s))
            if k_star == 0:
                hi = s
                continue
            s_new = float(dti_at[k_star - 1])
            if abs(s_new - s) < tol:
                s = s_new
                break
            if s_new > s:
                lo = s
            else:
                hi = s
        bar = 0.2 * s
        s_used = s
    k_star = int(np.clip(k_star, 1, K))
    k_argmax = int(np.argmax(dti_at)) + 1
    return {
        "n_truth_assumed": G,
        "target_score": None if target is None else float(target),
        "k_star": k_star,
        "marginal_bar": bar,
        "t_at_k_star": float(T[k_star - 1]),
        "dti_bound_at_k_star": float(dti_at[k_star - 1]),
        "k_argmax_ratio": k_argmax,
        "dti_bound_max": float(dti_at.max()),
        "self_consistent_score": s_used,
    }


def dinkelbach_budget(sol: CoverSolution, n_truth_grid) -> list[dict]:
    """Optimal cardinality as a function of the assumed hidden-truth size ``|G|``.

    Reported as a sensitivity table rather than a single number because ``|G|`` is not
    observable; the parent project's live-anchor inversion put it near 12,200 px.
    """
    ks = np.arange(1, sol.k + 1, dtype=np.float64)
    out = []
    for G in n_truth_grid:
        v = sol.cumulative / (0.2 * ks + 0.8 * float(G))
        k_opt = int(np.argmax(v)) + 1
        k_bar = int(np.sum(sol.marginal > 0.2 * float(v[k_opt - 1])))
        k_bar = int(np.clip(k_bar, 1, sol.k))
        out.append({
            "n_truth": float(G),
            "k_argmax_ratio": k_opt,
            "dti_bound_at_argmax": float(v[k_opt - 1]),
            "k_marginal_rule": k_bar,
            "dti_bound_at_marginal_rule": float(v[k_bar - 1]),
        })
    return out
