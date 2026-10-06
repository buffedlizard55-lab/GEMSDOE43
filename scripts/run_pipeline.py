#!/usr/bin/env python3
"""End-to-end pipeline: channels -> prior surfaces -> MCLP emission -> blocked validation.

Usage
-----
    PYTHONPATH=src python3 scripts/run_pipeline.py [--k-max 120000] [--mass 12226]
                                                   [--no-supervised] [--tag NAME]

Outputs
-------
``evidence/pipeline_<tag>.json``   every number this script produces
``.cache/gems_work/surfaces/*.npy`` cached prior surfaces (regenerable)
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

from gems43 import bands, holdout, mclp, paths, surface
from gems43.grid import ALPHA

T0 = time.time()


def log(m: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-max", type=int, default=120_000)
    ap.add_argument("--mass", type=float, default=12_226.0,
                    help="assumed number of hidden truth pixels |G| (live-anchor estimate)")
    ap.add_argument("--n-side", type=int, default=2)
    ap.add_argument("--no-supervised", action="store_true")
    ap.add_argument("--tag", default="main")
    ap.add_argument("--budgets", default="",
                    help="comma-separated explicit dot budgets to report (default: derived)")
    ap.add_argument("--buffer", type=float, default=0.0,
                    help="candidate-mask flank around the catalogue, in 100 m pixels")
    args = ap.parse_args()

    foot = bands.footprint()
    cat = bands.catalogue()
    log(f"grid: footprint {foot.sum():,} px, catalogue {cat.sum():,} px")

    ch, names, cmeta = surface.load_channels()
    log(f"channels: {ch.shape} -> {len(names)} named channels")

    sgmc, _ = bands.external("derived_sgmc_faults_100m_u8.tif")
    sgmc = sgmc[0]

    # ------------------------------------------------------------------ candidate mask
    cand = surface.candidate_mask(foot, cat, buffer_px=args.buffer)
    log(f"candidate pixels: {cand.sum():,}")

    # ------------------------------------------------------------------ prior surfaces
    surf_dir = paths.work_dir() / "surfaces"
    surf_dir.mkdir(parents=True, exist_ok=True)

    surfaces: dict[str, np.ndarray] = {}
    surfaces.update(surface.labelfree_surfaces(ch, names, foot))
    log(f"label-free surfaces: {sorted(surfaces)}")

    if not args.no_supervised:
        cache = surf_dir / "sup_oof.npy"
        if cache.exists():
            surfaces["sup_oof"] = np.load(cache)
            log("supervised OOF surface: loaded from cache")
        else:
            blk = holdout.blocks(foot.shape, args.n_side)
            oof = np.zeros(foot.shape, dtype=np.float32)
            trained = 0
            for b in range(args.n_side ** 2):
                in_block = blk == b
                rows, cols, y = surface._sample_pixels(
                    foot, cat, n_neg=250_000, seed=b, block=~in_block)
                if np.unique(y).size < 2 or y.sum() < 50:
                    continue
                p, _ = surface.supervised_surface(
                    ch, foot, cat, rows=rows, cols=cols, y=y, seed=b,
                    max_iter=150, learning_rate=0.1, verbose=False)
                # write only this block's out-of-fold predictions
                oof[in_block] = p[in_block]
                trained += 1
                log(f"  supervised fold {b}: {int(y.sum()):,} positives, "
                    f"{int((y == 0).sum()):,} negatives")
            surfaces["sup_oof"] = oof
            np.save(cache, oof)
            log(f"supervised OOF surface built from {trained} folds")

    # fusions of the supervised surface with the physical surfaces
    if "sup_oof" in surfaces:
        s = surfaces["sup_oof"].astype(np.float64)
        surfaces["sup_x_multiphysics"] = s * np.sqrt(
            np.maximum(surfaces.get("lf_h431_multiphysics", 1.0), 0.0))
        surfaces["sup_x_concealed"] = s * (
            0.4 + 0.6 * np.maximum(surfaces.get("lf_h432_concealed", 0.0), 0.0))
        if "lf_fused" in surfaces:
            surfaces["sup_x_fused"] = s * np.sqrt(np.maximum(surfaces["lf_fused"], 0.0))
        if "lf_h434_fluids" in surfaces:
            surfaces["sup_x_fluids"] = s * (
                0.5 + 0.5 * np.sqrt(np.maximum(surfaces["lf_h434_fluids"], 0.0)))

    for k in list(surfaces):
        surfaces[k] = np.asarray(surfaces[k], dtype=np.float32)
        np.save(surf_dir / f"{k}.npy", surfaces[k])

    del ch
    import gc
    gc.collect()

    # ------------------------------------------------------------------ validation frames
    frames = holdout.make_frames(foot, cat, sgmc=sgmc, n_side=args.n_side)
    log(f"validation frames: {[f.name for f in frames]}")
    fk_dir = paths.work_dir() / "framek"
    for f in frames:
        holdout.frame_kernel(f, cache_dir=fk_dir)      # 29 shifted passes, done once per frame
        log(f"  frame {f.name}: {f.n_truth:,} truth px")
    del sgmc
    gc.collect()

    # ------------------------------------------------------------------ MCLP per surface
    budgets = ([int(b) for b in args.budgets.split(",") if b.strip()]
               if args.budgets else None)
    report: dict = {
        "tag": args.tag,
        "grid": {"footprint": int(foot.sum()), "catalogue": int(cat.sum()),
                 "candidates": int(cand.sum()), "buffer_px": args.buffer},
        "mass_assumed": args.mass,
        "k_max": args.k_max,
        "surfaces": {},
        "frames": {f.name: {"n_truth": f.n_truth, "note": f.note} for f in frames},
    }

    for sname, raw in surfaces.items():
        pi = surface.normalise_to_mass(raw, foot, args.mass)
        log(f"MCLP on {sname!r} (sum pi = {pi.sum():,.1f})")
        sol = mclp.greedy_cover(pi, cand, args.k_max, min_potential=0.0,
                                max_candidates=700_000, verbose=True, log_every=10000)
        plan = mclp.emission_plan(sol)
        tbl = mclp.dinkelbach_budget(sol, [6_000, 12_226, 25_000, 50_000])
        ks = budgets or sorted(set(
            [int(plan["k_star"]), int(plan["k_argmax_ratio"])] +
            [int(t["k_argmax_ratio"]) for t in tbl] +
            [20_000, 40_000, 60_000, 90_000]))
        ks = [k for k in ks if 1 <= k <= sol.k]

        entry = {
            "coverage_path": {
                "k": int(sol.k),
                "cumulative_at": {str(k): float(sol.cumulative[k - 1]) for k in ks},
                "marginal_at": {str(k): float(sol.marginal[k - 1]) for k in ks},
                "total_demand": sol.total_demand,
                "n_candidates": sol.n_candidates,
                "guarantee_1_minus_1_over_e": sol.guarantee,
            },
            "emission_plan": plan,
            "dinkelbach_sensitivity": tbl,
            "frames": {},
        }

        rows_by_k: dict[int, list] = {}
        for f in frames:
            fk = np.load(fk_dir / f"{f.name}.npy")
            # dots of every requested prefix, after deleting this frame's masked pixels
            order_r, order_c = np.divmod(sol.order, foot.shape[1])
            keep = ~f.masked[order_r, order_c]
            for k in ks:
                sel = sol.order[:k][keep[:k]]
                rows_by_k.setdefault(k, []).append(holdout.score_dots(sel, f, frame_k=fk))
            del fk
        for k in ks:
            rows = rows_by_k[k]
            by_prefix: dict[str, list] = {}
            for r in rows:
                by_prefix.setdefault(r["frame"][0], []).append(r)
            entry["frames"][str(k)] = {
                "per_frame": rows,
                "by_family": {p: holdout.fold_summary(v) for p, v in by_prefix.items()},
                "pooled_A": holdout.fold_summary(by_prefix.get("A", [])),
                "pooled_B": holdout.fold_summary(by_prefix.get("B", [])),
                "pooled_C": holdout.fold_summary(by_prefix.get("C", [])),
                "pooled_all": holdout.fold_summary(rows),
            }
        # keep the winning order for the submission builder
        np.save(paths.work_dir() / f"order_{sname}.npy", sol.order)
        report["surfaces"][sname] = entry
        log(f"  {sname}: k*={plan['k_star']:,} bound={plan['dti_bound_at_k_star']:.4f} "
            f"| A={entry['frames'][str(ks[0])]['pooled_A'].get('mean_dti', 0):.4f}")

    out = paths.evidence_dir() / f"pipeline_{args.tag}.json"
    out.write_text(json.dumps(report, indent=1))
    log(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
