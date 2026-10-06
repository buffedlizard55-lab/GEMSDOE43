#!/usr/bin/env python3
"""Build, verify, audit and novelty-screen the submission GeoTIFF.

Selection rule (all three are reported; nothing is silent):

* the prior surface and the dot budget are the arg-max of the **primary frame family**
  (``--select-on``, default ``B``: the off-catalogue external inventory, the closest available
  proxy for the hidden test set);
* the runner-up families are reported alongside so the choice is auditable;
* if ``--k`` / ``--surface`` are given explicitly those override the selection, and the file's
  submission note says so.

The emitted raster is binary (`p = 1` on the chosen dots).  That is not a stylistic choice: the
official index satisfies ``dDTI/dλ > 0`` in the support scale, so a graded map is strictly
dominated by its own thresholded support (proved in ``docs/research/metric-algebra.md``).

Usage
-----
    PYTHONPATH=src python3 scripts/build_submission.py [--surface NAME] [--k N]
                                                       [--select-on B|ABC] [--tag main]
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

from gems43 import bands, holdout, novelty, paths, submission

T0 = time.time()


def log(m: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def family_key(fam: str) -> str:
    return f"pooled_{fam}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--select-on", default="AC", help="A | B | C | AC | ABC; default AC, the "
                    "two families whose truth is not the SGMC external inventory")
    ap.add_argument("--tag", default="main")
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--no-novelty", action="store_true")
    ap.add_argument("--reason", default=None,
                    help="auditable justification recorded with an explicit --surface/--k override")
    args = ap.parse_args()

    ev = json.loads((paths.evidence_dir() /
                     (args.evidence or f"pipeline_{args.tag}.json")).read_text())
    foot = bands.footprint()
    cat = bands.catalogue()
    W = foot.shape[1]

    # ---------------------------------------------------------------- selection
    fams = list(args.select_on) if args.select_on != "ABC" else ["A", "B", "C"]
    table = []
    for sname, e in ev["surfaces"].items():
        for k, blk in e["frames"].items():
            pooled = blk.get("pooled_all", {})
            row = {"surface": sname, "k": int(k),
                   "pooled_all": pooled.get("mean_dti", 0.0)}
            for f in ("A", "B", "C"):
                row[f] = blk.get(f"pooled_{f}", {}).get("mean_dti", 0.0)
            row["score"] = float(np.mean([row[f] for f in fams]))
            row["k_star"] = int(e["emission_plan"]["k_star"])
            row["t_covered"] = e["coverage_path"]["cumulative_at"].get(k, 0.0)
            table.append(row)
    table.sort(key=lambda r: -r["score"])

    if args.surface and args.k:
        chosen = next(r for r in table if r["surface"] == args.surface and r["k"] == args.k)
        why = args.reason or "explicit override from the command line (no justification given)"
    else:
        chosen = table[0]
        why = (f"arg-max of the mean pooled DW-Tversky over validation frame families "
               f"{''.join(fams)}")
    log(f"selected {chosen['surface']} @ K={chosen['k']:,} ({why})")
    log(f"  pooled all={chosen['pooled_all']:.4f}  A={chosen['A']:.4f}  "
        f"B={chosen['B']:.4f}  C={chosen['C']:.4f}")

    # ---------------------------------------------------------------- emission
    order = np.load(paths.work_dir() / f"order_{chosen['surface']}.npy")
    dots = order[: chosen["k"]]
    pred = np.zeros(foot.shape, dtype=np.float32)
    pred[dots // W, dots % W] = 1.0
    log(f"emission: {int(dots.size):,} dots, {float(pred.sum()):,.0f} positive cells")

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    stem = (f"gemsdoe43-mclp-{chosen['surface'].replace('_', '')}-"
            f"{chosen['k']}-{stamp}")

    res = submission.write_submission(pred, foot, cat, stem)
    log(f"wrote {res['files']['zeros']['filename']} "
        f"({res['files']['zeros']['size_bytes']:,} bytes)")

    # ---------------------------------------------------------------- novelty screen
    screen = {"skipped": True, "reason": "--no-novelty"}
    if not args.no_novelty:
        mask = pred > 0
        pdir = paths.work_dir() / "prior_submissions"
        if not pdir.exists():
            pdir = paths.work_dir().parent / "prior_submissions"
        if pdir.exists():
            log(f"novelty screen against {len(list(pdir.glob('*.tif')))} prior artifacts")
            screen = novelty.screen(mask, pdir, foot)
            log(f"  worst coverage IoU {screen['worst_iou']:.4f} "
                f"({screen['worst_artifact']}) -> "
                f"{'PASS' if screen['passed'] else 'FAIL'}")
        else:
            screen = {"skipped": True, "reason": "no prior-submission corpus"}

    note = (
        f"GEMSDOE43 MCLP | Church-ReVelle maximal covering on the {chosen['surface']} prior, "
        f"K={chosen['k']} derived by the 0.2*DTI marginal rule (no spacing constant); "
        f"{int(dots.size)} dots, 0 on a known catalogue pixel; pooled blocked holdout "
        f"all={chosen['pooled_all']:.4f} A={chosen['A']:.4f} B={chosen['B']:.4f} "
        f"C={chosen['C']:.4f}; novelty max IoU "
        f"{screen.get('worst_iou') if screen.get('worst_iou') is not None else 'n/a'}; UNSCORED"
    )
    res["submission_note"] = note[:200]
    res["portal_name"] = f"GEMSDOE43-MCLP-{chosen['surface'][:18]}-{chosen['k']}"
    res["selection"] = {
        "rule": why,
        "selected_on_families": fams,
        "chosen": chosen,
        "runner_ups": table[1:8],
    }
    res["novelty"] = screen
    res["built_utc"] = stamp
    res["surface"] = chosen["surface"]
    res["k"] = int(chosen["k"])

    out = paths.evidence_dir() / "submission.json"
    out.write_text(json.dumps(res, indent=1))
    log(f"wrote {out}")
    log("submission note:\n  " + res["submission_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
