"""Spatially blocked validation frames.

The competition's own test set is a set of faults that the *published catalogue does not contain*.
No local frame can reproduce that, and the parent project measured how badly catalogue-based
frames rank against the live board (Spearman rho ~= +0.51 over n=12 artifacts, i.e. a screen, not
evidence).  Three frames are therefore reported side by side, each with its own stated bias, and
no promotion decision rests on a single one.

Frame A -- **catalogue spatial holdout** (the parent project's frame).
    The catalogue is split into 8-connected components; the **in-block portion** of every component
    that reaches into the held-out spatial block becomes the truth, and the rest of the catalogue
    is deleted from every metric term.  Components are therefore *deliberately* cut at the block
    boundary: the truth is then exactly the catalogue pixels withheld from that fold's training
    set, which is what makes the out-of-fold supervised surface honest.  (Holding out *whole*
    components instead would put pixels the fold trained on into its own truth -- a leak.)
    Measures: can the method find a withheld *piece of the same inventory*?
    Bias: the truth is old news -- it is the style of fault that was already mappable.

Frame B -- **off-catalogue external inventory** (introduced here).
    Truth = SGMC fault pixels that the competition catalogue does not contain (79,615 px);
    the whole competition catalogue is the masked "known" set.  This is a literal
    "faults missing from the catalogue" set and is the closest available proxy for the hidden
    test set.  Bias: the SGMC compilation includes pre-Quaternary and inferred faults, so it is
    broader than an expert's "new active fault" list.

Frame C -- **catalogue-flank transfer**.
    Truth = catalogue pixels; every dot within ``buffer`` px of the *training* half is deleted
    before scoring, so the measurement is about generalising away from mapped traces rather than
    re-finding them.

Scoring convention (matches the organizer's stated treatment of known faults, community thread
11516): masked "known" pixels are removed from the prediction before any term is computed, and
the kernel maxima are taken over the held-out truth only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from .grid import KERNEL_W, OFFSETS, shift
from .metric import dti_components, dti_from_components

STRUCT = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]], bool)

__all__ = ["blocks", "connected_components", "Frame", "make_frames", "score_frame",
           "score_dots", "frame_kernel", "dots_from_pred"]


def blocks(shape, n_side: int = 2) -> np.ndarray:
    """Integer block id per pixel, ``n_side`` x ``n_side`` equal-area spatial blocks."""
    H, W = shape
    out = np.zeros(shape, dtype=np.int32)
    for i in range(n_side):
        for j in range(n_side):
            r0 = H * i // n_side
            r1 = H * (i + 1) // n_side
            c0 = W * j // n_side
            c1 = W * (j + 1) // n_side
            out[r0:r1, c0:c1] = i * n_side + j
    return out


def connected_components(mask: np.ndarray):
    lab, n = label(mask, structure=STRUCT)
    return lab, int(n)


@dataclass
class Frame:
    name: str
    truth: np.ndarray          # scored truth pixels
    masked: np.ndarray         # pixels deleted from the prediction before scoring
    note: str

    @property
    def n_truth(self) -> int:
        return int(self.truth.sum())


def make_frames(foot, catalogue, sgmc=None, n_side: int = 2) -> list[Frame]:
    """Build every validation frame."""
    frames: list[Frame] = []
    blk = blocks(foot.shape, n_side)
    lab, ncomp = connected_components(catalogue)

    # ---- Frame A: whole catalogue components held out by spatial block
    for b in range(n_side * n_side):
        in_block = blk == b
        comp_ids = np.unique(lab[in_block & catalogue])
        comp_ids = comp_ids[comp_ids > 0]
        truth = np.isin(lab, comp_ids) & in_block
        masked = catalogue & ~truth
        if truth.sum() < 200:
            continue
        frames.append(Frame(
            name=f"A_block{b}",
            truth=truth,
            masked=masked,
            note=("Frame A: the in-block portion of every catalogue component reaching into block "
                  f"{b}; the remaining catalogue ({int(masked.sum()):,} px), including the "
                  "continuation of the same components outside the block, is deleted from every "
                  "metric term. Bias: the truth is part of the same inventory."),
        ))

    # ---- Frame B: faults present in an independent compilation but absent from the catalogue
    if sgmc is not None:
        off = (sgmc > 0) & foot & ~catalogue
        for b in range(n_side * n_side):
            in_block = blk == b
            truth = off & in_block
            if truth.sum() < 200:
                continue
            frames.append(Frame(
                name=f"B_block{b}",
                truth=truth,
                masked=catalogue.copy(),
                note=(f"Frame B: {int(truth.sum()):,} SGMC fault pixels in block {b} that the "
                      "competition catalogue does not contain; the entire catalogue is masked. "
                      "Closest available proxy for the hidden test set; broader than an expert "
                      "'new active fault' list."),
            ))

    # ---- Frame C: catalogue, with a 3-pixel flank around the training half deleted
    for b in range(n_side * n_side):
        in_block = blk == b
        comp_ids = np.unique(lab[in_block & catalogue])
        comp_ids = comp_ids[comp_ids > 0]
        truth = np.isin(lab, comp_ids) & in_block
        train = catalogue & ~truth
        masked = train.copy()
        d = distance_transform_edt(~train)
        masked |= (d <= 3) & foot
        masked &= ~truth
        if truth.sum() < 200:
            continue
        frames.append(Frame(
            name=f"C_block{b}",
            truth=truth,
            masked=masked,
            note=(f"Frame C: the in-block portion of every catalogue component reaching into "
                  f"block {b}, with the rest of the catalogue plus a 300 m flank deleted from "
                  "the prediction. Measures generalisation away from mapped traces."),
        ))
    return frames


def frame_kernel(frame: Frame, cache_dir=None) -> np.ndarray:
    """``Tk[x] = max_{g in truth} k(d(x, g))`` -- the FP-w kernel image of one frame.

    Computed once per frame (29 shifted passes) and cached, because it does not depend on the
    prediction.  Every scoring call then costs O(K) instead of O(grid).
    """
    import pickle
    from pathlib import Path
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        f = cache_dir / f"{frame.name}.npy"
        if f.exists():
            return np.load(f)
    out = np.zeros(frame.truth.shape, dtype=np.float32)
    m = frame.truth.astype(np.float32)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        if w <= 0.0:
            continue
        np.maximum(out, w * shift(m, -dr, -dc), out=out)
    if cache_dir is not None:
        np.save(f, out)
    return out


def dots_from_pred(pred: np.ndarray, frame: Frame | None = None):
    """Flat indices of the called pixels of ``pred``, after deleting masked pixels."""
    p = np.asarray(pred)
    if frame is not None:
        p = p.copy()
        p[frame.masked] = 0.0
    return np.flatnonzero((p > 0).ravel())


def score_dots(dots: np.ndarray, frame: Frame, frame_k: np.ndarray | None = None,
               cache_dir=None, radius_px: float = 3.0) -> dict:
    """Exact DW-Tversky of a sparse dot set against one frame, in O((K + |G|) log K) time.

    The exact identities used:

        TP_w = sum_{g in truth} max_{i in S} k(d(i, g))     -- a *max*, not a sum, so it is
               evaluated with a KD-tree ball query from each truth pixel to the dots inside the
               300 m kernel support;
        FP_w = sum_{i in S} (1 - Tk[i])                     with ``Tk`` the cached truth-kernel
               image ``Tk[x] = max_{g in truth} k(d(x, g))``, which is independent of the
               prediction and is computed once per frame;
        FN_w = |truth| - TP_w.

    Verified against the dense reference ``metric.dti_components`` in ``tests/test_holdout.py``.
    """
    from scipy.spatial import cKDTree

    if frame_k is None:
        frame_k = frame_kernel(frame, cache_dir)
    H, W = frame.truth.shape
    dots = np.asarray(dots, dtype=np.int64)
    if dots.size == 0:
        return {"frame": frame.name, "n_truth": frame.n_truth, "n_emitted": 0,
                "tp_w": 0.0, "fp_w": 0.0, "fn_w": float(frame.n_truth), "dti": 0.0,
                "weighted_recall": 0.0, "credit_per_dot": 0.0}
    r, c = np.divmod(dots, W)

    # --- TP_w : for every truth pixel, the best kernel credit offered by any dot
    tree = cKDTree(np.stack([r, c], axis=1).astype(np.float64))
    tr, tc = np.nonzero(frame.truth)
    tp = 0.0
    if tr.size:
        nbr = tree.query_ball_point(np.stack([tr, tc], axis=1).astype(np.float64), radius_px)
        flat_d = dots
        for g_i, lst in enumerate(nbr):
            if not lst:
                continue
            idx = flat_d[np.asarray(lst, dtype=np.int64)]
            dr = (idx // W) - tr[g_i]
            dc = (idx % W) - tc[g_i]
            d = np.hypot(dr, dc)
            tp += float(np.max(np.maximum(0.0, 1.0 - d / radius_px)))

    fp = float(dots.size) - float(frame_k[r, c].sum())
    n_truth = frame.n_truth
    fn = float(n_truth) - tp
    d = dti_from_components(tp, fp, fn)
    return {
        "frame": frame.name,
        "n_truth": n_truth,
        "n_emitted": int(dots.size),
        "tp_w": float(tp), "fp_w": fp, "fn_w": fn,
        "dti": d,
        "weighted_recall": tp / n_truth if n_truth else 0.0,
        "credit_per_dot": tp / dots.size,
    }


def score_frame(pred: np.ndarray, frame: Frame, n_emitted_cap: int | None = None,
                frame_k: np.ndarray | None = None, cache_dir=None) -> dict:
    """DW-Tversky of a prediction against one frame, with masked pixels removed."""
    p = np.asarray(pred, dtype=np.float64).copy()
    p[frame.masked] = 0.0
    dots = np.flatnonzero((p > 0).ravel())
    if frame_k is None and cache_dir is None:
        c = dti_components(p, frame.truth)          # reference path (used by the tests)
        return {
            "frame": frame.name, "n_truth": frame.n_truth, "n_emitted": c.n_emitted,
            "tp_w": c.tp, "fp_w": c.fp, "fn_w": c.fn, "dti": c.dti,
            "weighted_recall": c.weighted_recall,
            "credit_per_dot": (c.tp / c.n_emitted) if c.n_emitted else 0.0,
        }
    return score_dots(dots, frame, frame_k, cache_dir)


def fold_summary(rows: list[dict]) -> dict:
    """Pooled index and per-fold win count for a list of ``score_frame`` dictionaries."""
    if not rows:
        return {}
    d = [r["dti"] for r in rows]
    return {
        "folds": len(rows),
        "mean_dti": float(np.mean(d)),
        "min_dti": float(np.min(d)),
        "max_dti": float(np.max(d)),
        "std_dti": float(np.std(d)),
        "mean_recall": float(np.mean([r["weighted_recall"] for r in rows])),
        "mean_credit_per_dot": float(np.mean([r["credit_per_dot"] for r in rows])),
    }
