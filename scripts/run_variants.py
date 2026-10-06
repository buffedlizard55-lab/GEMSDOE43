#!/usr/bin/env python3
"""Focused variant sweep: prior surface x catalogue-flank buffer, MCLP-placed and blocked-scored.

The run_pipeline stage showed the supervised out-of-fold prior dominates every label-free surface
on all three frame families. Two questions remain that the first pass did not answer:

  * does a **catalogue flank** help here, the way the B=2 prune helped GEMSDOE32?  (buffer 0/1/2 px)
  * does fusing the supervised prior with an independent structural inventory (SGMC) or with the
    multi-physics lineament surface help, once each is normalised to the same demand mass?

Usage: PYTHONPATH=src python3 scripts/run_variants.py [--k-max 60000]
"""
from __future__ import annotations

import argparse, gc, json, time
import numpy as np
from gems43 import bands, holdout, mclp, paths, surface

T0 = time.time()
def log(m): print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-max", type=int, default=60_000)
    ap.add_argument("--mass", type=float, default=12_226.0)
    ap.add_argument("--tag", default="variants")
    a = ap.parse_args()

    foot = bands.footprint(); cat = bands.catalogue()
    dcat = bands.dist_to_catalogue_px()
    from scipy.ndimage import distance_transform_edt
    ch, names, _ = surface.load_channels()

    sd = paths.work_dir() / "surfaces"
    sup = np.load(sd / "sup_oof.npy")
    lf = {k: np.load(sd / f"{k}.npy") for k in
          ("lf_ext_sgmc", "lf_line_agreement", "lf_h431_multiphysics", "lf_h432_concealed",
           "lf_h434_fluids", "lf_h435_gravity", "lf_h431_mag_edge", "lf_h432_subsurface")}
    def u(n):
        return np.asarray(lf[n], dtype=np.float32)

    def soft(x): return 0.35 + 0.65 * np.sqrt(np.maximum(x, 0.0))
    surfaces = {
        "sup": sup.astype(np.float32),
        "sup_x_sgmc": (sup * soft(u("lf_ext_sgmc"))).astype(np.float32),
        "sup_x_line": (sup * soft(u("lf_line_agreement"))).astype(np.float32),
        "sup_x_mp": (sup * soft(u("lf_h431_multiphysics"))).astype(np.float32),
        "sup_x_conc": (sup * soft(u("lf_h432_concealed"))).astype(np.float32),
        "sup_x_all": (sup * soft(u("lf_ext_sgmc")) * soft(u("lf_line_agreement"))
                      * soft(u("lf_h434_fluids"))).astype(np.float32),
    }
    del ch, lf, sup
    gc.collect()

    sgmc, _ = bands.external("derived_sgmc_faults_100m_u8.tif")
    frames = holdout.make_frames(foot, cat, sgmc=sgmc[0], n_side=2)
    del sgmc
    fk_dir = paths.work_dir() / "framek"
    fks = {f.name: np.load(fk_dir / f"{f.name}.npy") for f in frames}

    out = {"tag": a.tag, "k_max": a.k_max, "mass": a.mass, "variants": {}}
    for b in (0, 1, 2):
        cand = surface.candidate_mask(foot, cat, buffer_px=float(b), dcat=dcat)
        log(f"buffer={b}px  candidates={int(cand.sum()):,}")
        for sname, raw in surfaces.items():
            pi = surface.normalise_to_mass(raw, foot, a.mass)
            sol = mclp.greedy_cover(pi, cand, a.k_max, min_potential=0.0,
                                    max_candidates=700_000, verbose=False)
            plan = mclp.emission_plan(sol)
            ks = sorted({int(plan["k_star"]), int(plan["k_argmax_ratio"]),
                         20_000, 30_000, 40_000, 50_000, 60_000})
            ks = [k for k in ks if 1 <= k <= sol.k]
            res = {}
            for k in ks:
                per = []
                for f in frames:
                    sel = sol.order[:k]
                    keep = ~f.masked[sel // foot.shape[1], sel % foot.shape[1]]
                    per.append(holdout.score_dots(sel[keep], f, frame_k=fks[f.name]))
                fam = {}
                for p in "ABC":
                    v = [r for r in per if r["frame"][0] == p]
                    fam[p] = holdout.fold_summary(v)
                alls = holdout.fold_summary(per)
                res[str(k)] = {"A": fam["A"]["mean_dti"], "B": fam["B"]["mean_dti"],
                               "C": fam["C"]["mean_dti"], "all": alls["mean_dti"],
                               "mean_ABC": float(np.mean([fam[p]["mean_dti"] for p in "ABC"])),
                               "recall_B": float(np.mean([r["weighted_recall"] for r in per
                                                          if r["frame"][0] == "B"]))}
            key = f"{sname}|buffer{b}"
            out["variants"][key] = {"k_star": int(plan["k_star"]),
                                    "marginal_bar": plan["marginal_bar"],
                                    "dti_bound_at_k_star": plan["dti_bound_at_k_star"],
                                    "frames": res}
            np.save(paths.work_dir() / f"order_{sname}_b{b}.npy", sol.order)
            best = max(res.items(), key=lambda kv: kv[1]["mean_ABC"])
            log(f"   {key:22s} best K={best[0]:>6s} meanABC={best[1]['mean_ABC']:.4f} "
                f"A={best[1]['A']:.4f} B={best[1]['B']:.4f} C={best[1]['C']:.4f} "
                f"K*={plan['k_star']:,}")
    dest = paths.evidence_dir() / f"variants_{a.tag}.json"
    dest.write_text(json.dumps(out, indent=1))
    log(f"wrote {dest}")

if __name__ == "__main__":
    main()
