#!/usr/bin/env python3
"""Run the near-duplicate screen for the built submission and write it into evidence/.

Split out of ``build_submission.py`` because the screen walks a 242-file corpus and is the one
stage whose cost is dominated by I/O rather than by the algorithm.
"""
from __future__ import annotations

import gc
import json
import time

import numpy as np

from gems43 import bands, novelty, paths

T0 = time.time()
def log(m): print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)


def main():
    ev = json.loads((paths.evidence_dir() / "submission.json").read_text())
    foot = bands.footprint()
    stem = ev["stem"]
    W = foot.shape[1]

    import rasterio
    with rasterio.open(paths.downloads_dir() / f"{stem}-zeros.tif") as s:
        v = s.read(1)
    mask = np.isfinite(v) & (v > 0)
    del v
    gc.collect()
    log(f"new layout: {int(mask.sum()):,} positive cells")

    pdir = paths.work_dir() / "prior_submissions"
    if not pdir.exists():
        pdir = paths.work_dir().parent / "prior_submissions"
    files = sorted(pdir.glob("*.tif")) + sorted(pdir.glob("*.TIF"))
    log(f"screening against {len(files)} prior artifacts in {pdir}")

    res = novelty.screen(mask, pdir, foot)
    log(f"compared {res['n_compared']}; worst IoU {res['worst_iou']:.4f} "
        f"({res['worst_artifact']}) -> {'PASS' if res['passed'] else 'FAIL'}")
    log(f"sampled (IoU not decisive): {len(res['sampled_artifacts'])}")
    log(f"near-duplicates: {res['dupes'] or 'none'}")

    ev["novelty"] = res
    (paths.evidence_dir() / "submission.json").write_text(json.dumps(ev, indent=1))
    log("wrote evidence/submission.json")
    for r in res["top"][:6]:
        log(f"  {r['coverage_iou']:.3f} IoU | contain {r['new_within_300m_of_prior']:.3f}"
            f"/{r['prior_within_300m_of_new']:.3f} | nn {r['median_nn_distance_px']:.1f}px"
            f" | corr {r['block_correlation']:+.2f} | {r['prior_dots']:,} dots | {r['artifact'][:58]}")


if __name__ == "__main__":
    main()
