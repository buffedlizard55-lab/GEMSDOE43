"""Lazy-greedy maximum expected coverage (Church-ReVelle MCLP) placement.

Objective: given demand weights p_j in [0,1] and the triangular kernel
k(d) = max(1 - d/3, 0) with d in grid cells (the official 300-m kernel on the
100-m grid), select S with |S| = budget maximizing
    F(S) = sum_j p_j * max_{i in S} k(d_ij).
F is monotone submodular (a facility-location / weighted-coverage function), so the
greedy algorithm achieves at least (1 - 1/e) of the optimum over the candidate set
(Nemhauser-Wolsey-Fisher 1978). This module implements the exact lazy (accelerated)
greedy variant (Minoux 1978): cached marginal gains are upper bounds, so a popped
candidate whose recomputed gain still beats every cached bound is the true argmax.

Determinism: ties break by ascending flat index everywhere (candidate truncation,
heap order, and argmax comparison).
"""
from __future__ import annotations

import heapq
import math

import numpy as np
from scipy.ndimage import convolve

RADIUS_PX = 3.0
PAD = int(math.ceil(RADIUS_PX))
MAX_RECOMPUTES_DEFAULT = 20_000_000


def triangular_kernel_2d(radius_px: float = RADIUS_PX) -> np.ndarray:
    """Return the (2*ceil(r)+1)^2 triangular kernel sampled at cell centers."""
    half = int(math.ceil(radius_px))
    size = 2 * half + 1
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1]
    dist = np.hypot(yy, xx).astype(np.float64)
    return np.maximum(1.0 - dist / radius_px, 0.0)


def _neighbor_table(padded_width: int, radius_px: float = RADIUS_PX,
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Flat-index offsets and kernel weights for neighbors with strictly positive k."""
    half = int(math.ceil(radius_px))
    offsets: list[int] = []
    weights: list[float] = []
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            weight = max(1.0 - math.hypot(dy, dx) / radius_px, 0.0)
            if weight > 0.0:
                offsets.append(dy * padded_width + dx)
                weights.append(weight)
    order = np.argsort(np.asarray(offsets), kind="stable")
    return (np.asarray(offsets, dtype=np.int64)[order],
            np.asarray(weights, dtype=np.float64)[order])


def coverage_objective(selected: np.ndarray, demand: np.ndarray,
                       radius_px: float = RADIUS_PX) -> float:
    """Exact F(S) by direct neighborhood maximization (for tests and receipts)."""
    selected = np.asarray(selected, dtype=bool)
    demand = np.asarray(demand, dtype=np.float64)
    if selected.shape != demand.shape or selected.ndim != 2:
        raise ValueError("selected and demand must be same-shape 2-D arrays")
    height, width = demand.shape
    pad = int(math.ceil(radius_px))
    padded_width = width + 2 * pad
    pflat = np.zeros((height + 2 * pad) * padded_width, dtype=np.float64)
    pflat.reshape(height + 2 * pad, padded_width)[pad:pad + height, pad:pad + width] = np.where(
        np.isfinite(demand), np.clip(demand, 0.0, 1.0), 0.0)
    offsets, weights = _neighbor_table(padded_width, radius_px)
    best = np.zeros_like(pflat)
    rows, cols = np.nonzero(selected)
    for row, col in zip(rows.tolist(), cols.tolist()):
        center = (row + pad) * padded_width + (col + pad)
        nbrs = center + offsets
        # NB: fancy indexing never writes back through `out=`; ufunc.at does.
        np.maximum.at(best, nbrs, weights)
    return float(np.sum(pflat * best, dtype=np.float64))


def initial_gains(demand: np.ndarray, eligible: np.ndarray,
                  radius_px: float = RADIUS_PX) -> np.ndarray:
    """Exact empty-set marginal gain of every cell: demand convolved with the kernel."""
    demand = np.asarray(demand, dtype=np.float64)
    eligible = np.asarray(eligible, dtype=bool)
    if demand.shape != eligible.shape or demand.ndim != 2:
        raise ValueError("demand and eligible must be same-shape 2-D arrays")
    clean = np.where(np.isfinite(demand), np.clip(demand, 0.0, 1.0), 0.0)
    gains = convolve(clean, triangular_kernel_2d(radius_px), mode="constant", cval=0.0)
    gains[~eligible] = -np.inf
    return gains


def lazy_greedy_cover(
    demand: np.ndarray,
    eligible: np.ndarray,
    budget: int,
    candidate_cap: int = 300_000,
    max_recomputes: int = MAX_RECOMPUTES_DEFAULT,
    radius_px: float = RADIUS_PX,
) -> tuple[np.ndarray, dict]:
    """Select `budget` eligible cells by exact lazy-greedy maximum coverage.

    Returns (selected_mask, stats) where stats records the candidate count,
    marginal-gain recomputes, and the final objective value.
    """
    demand = np.asarray(demand, dtype=np.float64)
    eligible = np.asarray(eligible, dtype=bool)
    if demand.shape != eligible.shape or demand.ndim != 2:
        raise ValueError("demand and eligible must be same-shape 2-D arrays")
    if budget < 0 or candidate_cap <= 0 or max_recomputes <= 0:
        raise ValueError("budget/candidate_cap/max_recomputes out of range")
    height, width = demand.shape
    selected = np.zeros((height, width), dtype=bool)
    if budget == 0:
        return selected, {"candidates": 0, "recomputes": 0, "objective": 0.0,
                          "selected": 0, "budget": 0}

    gains0 = initial_gains(demand, eligible, radius_px)
    flat_eligible = np.flatnonzero(eligible.ravel())
    if flat_eligible.size == 0:
        return selected, {"candidates": 0, "recomputes": 0, "objective": 0.0,
                          "selected": 0, "budget": budget}
    # Deterministic candidate truncation: gain desc, flat index asc.
    order = np.lexsort((flat_eligible, -gains0.ravel()[flat_eligible]))
    candidates = flat_eligible[order[:candidate_cap]]

    pad = int(math.ceil(radius_px))
    padded_width = width + 2 * pad
    padded_height = height + 2 * pad
    pflat = np.zeros(padded_height * padded_width, dtype=np.float64)
    clean = np.where(np.isfinite(demand), np.clip(demand, 0.0, 1.0), 0.0)
    pflat.reshape(padded_height, padded_width)[pad:pad + height, pad:pad + width] = clean
    offsets, weights = _neighbor_table(padded_width, radius_px)
    # Map unpadded flat index -> padded flat index for candidates.
    cand_rows, cand_cols = np.divmod(candidates, width)
    cand_padded = (cand_rows + pad) * padded_width + (cand_cols + pad)

    best = np.zeros_like(pflat)
    heap: list[tuple[float, int, int]] = [
        (-float(gains0.ravel()[idx]), int(pos), int(idx))
        for pos, idx in enumerate(candidates.tolist())
    ]
    # Heap entry: (-cached_gain, candidate_position, unpadded_flat_index). Position
    # preserves the deterministic truncation order as the final tie-break; because
    # truncation order is (gain desc, index asc), position order agrees with it.
    heapq.heapify(heap)
    selected_count = 0
    recomputes = 0
    target = min(budget, int(candidates.size))

    def marginal(padded_center: int) -> float:
        nbrs = padded_center + offsets
        residual = weights - best[nbrs]
        np.maximum(residual, 0.0, out=residual)
        return float(np.sum(pflat[nbrs] * residual, dtype=np.float64))

    while heap and selected_count < target:
        neg_cached, pos, idx = heapq.heappop(heap)
        cached = -neg_cached
        true_gain = marginal(int(cand_padded[pos]))
        recomputes += 1
        if recomputes > max_recomputes:
            raise RuntimeError(
                f"lazy greedy exceeded {max_recomputes} recomputes; aborting without a partial selection"
            )
        effective = true_gain if true_gain < cached else cached
        if heap:
            neg_top, pos_top, _ = heap[0]
            # (gain, -position) comparison: popped candidate wins ties by lower
            # position, matching the deterministic truncation order.
            if effective > -neg_top or (effective == -neg_top and pos <= pos_top):
                pass  # argmax confirmed
            else:
                heapq.heappush(heap, (-effective, pos, idx))
                continue
        row, col = divmod(idx, width)
        selected[row, col] = True
        selected_count += 1
        nbrs = int(cand_padded[pos]) + offsets
        # NB: fancy indexing never writes back through `out=`; ufunc.at does.
        np.maximum.at(best, nbrs, weights)

    objective = float(np.sum(pflat * best, dtype=np.float64))
    stats = {
        "candidates": int(candidates.size),
        "eligible_cells": int(flat_eligible.size),
        "recomputes": int(recomputes),
        "objective": objective,
        "selected": int(selected_count),
        "budget": int(budget),
    }
    return selected, stats
