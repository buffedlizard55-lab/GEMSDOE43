#!/usr/bin/env python3
"""Calibrate the local validation frames against owner-reported live scores.

Why this exists
---------------
A holdout number means nothing on its own.  The only way to know whether a frame is a usable
*ranker* is to score artifacts whose live competition score is already known and measure the rank
correlation.  The parent project did exactly this for its own instrument and found Spearman
rho ~= +0.51 over n = 12 -- a screen, not evidence.  This script repeats the measurement for the
three frames introduced here and reports it honestly, alongside the reference bar: **a candidate
must beat the best previously-scored artifact on the same frame before it is promoted.**

The live scores below are **owner-reported** (`docs/score-ledger.csv`, evidence class
`owner-report`); no organizer receipt links any of them to a file hash.

Usage
-----
    PYTHONPATH=src python3 scripts/calibrate_instrument.py
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np
from scipy.stats import spearmanr

from gems43 import bands, holdout, paths

# owner-reported live DW-Tversky scores, keyed by a regex matched against the artifact filename
# Artifacts whose live competition score is owner-reported.  Patterns are ordered: the first
# match wins, so the more specific pattern must come first (H19-4 and H19-5 have different scores).
LIVE = [
    (r"h33-2-b2|h33-h33-2-b2", 0.2778, "GEMSDOE32 H33-2-B2"),
    (r"h27-4-r1-solo-d2-8|h27-4-solo-d28", 0.2708, "GEMSDOE28 / GEMSDOE31 H27-4"),
    (r"dotted-h19-5-d2-8|d28-poisson300m-offcat", 0.2600, "GEMSDOE25 / GEMSDOE30 D2.8"),
    (r"dotted-h19-5-d1-5|h25-1-dotted", 0.2477, "GEMSDOE24 D1.5"),
    (r"topo-gap-closure-t-v2", 0.2449, "GEMSDOE27 TGC"),
    (r"h19-5-powerlaw", 0.1922, "GEMSDOE19 H19-5"),
    (r"h19-4-multiline", 0.1894, "GEMSDOE19 H19-4"),
    (r"h16-1-topo-geophys", 0.1855, "GEMSDOE16 H16-1"),
    (r"h28-dotted-ridge", 0.1839, "GEMSDOE10 H28"),
    (r"r13-lattice-s5", 0.0904, "GEMSDOE13 lattice"),
    (r"Hedge-v2|ens12-adopted", 0.1563, "GEMSDOE / 8GEMSDOE ensemble"),
    (r"PLACEHOLDER-2314b599", 0.0107, "GEMSDOE9 placeholder"),
]


SCORED_ONLY = True          # only artifacts with a known live score can calibrate anything

_ENCODING_SUFFIX = re.compile(
    r"(-nan|-zeros|-nanmask|-allfinite|\.zip|\.tif|\.TIF)+$")


def _layout_key(name: str) -> str:
    """Strip the outside-encoding suffix so identical layouts collapse to one row."""
    prev = None
    while prev != name:
        prev = name
        name = _ENCODING_SUFFIX.sub("", name)
    return name


def main() -> int:
    foot = bands.footprint()
    cat = bands.catalogue()
    sgmc, _ = bands.external("derived_sgmc_faults_100m_u8.tif")
    frames = holdout.make_frames(foot, cat, sgmc=sgmc[0], n_side=2)
    fk_dir = paths.work_dir() / "framek"
    fk_dir.mkdir(parents=True, exist_ok=True)

    prior_dir = paths.work_dir().parent / "prior_submissions"
    if not prior_dir.exists():
        prior_dir = paths.work_dir() / "prior_submissions"
    man_p = prior_dir / "manifest.json"
    man = json.loads(man_p.read_text()) if man_p.exists() else {}

    import rasterio
    from pathlib import Path

    rows = []
    seen_digest: set[str] = set()          # the same file is published by several sites
    seen_layout: set[tuple] = set()        # identical layouts reached through different repos
    for f in files_in(prior_dir):
        meta = man.get(f.name, {})
        label = f"{meta.get('repo','?')}::{meta.get('path', f.name)}"
        live = None
        live_name = None
        for pat, sc, nm in LIVE:
            if re.search(pat, f.name, re.I):
                live, live_name = sc, nm
                break
        if live is None and SCORED_ONLY:
            continue
        if live is None and SCORED_ONLY:
            continue
        # De-duplicate on the *layout*, not on the bytes: the same prediction is published as a
        # -nan.tif, a -zeros.tif and a .zip, which are different files with identical dots.
        digest = _layout_key(f.name)
        if digest in seen_digest:
            continue
        seen_digest.add(digest)
        try:
            with rasterio.open(f) as src:
                if (src.height, src.width) != foot.shape:
                    continue
                v = src.read(1)
        except Exception:
            continue
        v = np.where(np.isfinite(v), v, 0.0)
        dots = np.flatnonzero(((v > 0) & foot).ravel())
        if dots.size < 500:
            continue
        layout_id = (int(dots.size), live)
        if layout_id in seen_layout:
            continue
        seen_layout.add(layout_id)
        rec = {"artifact": f.name, "label": label, "live_score": live,
               "live_name": live_name, "n_dots": int(dots.size), "frames": {}}
        for fr in frames:
            fk = np.load(fk_dir / f"{fr.name}.npy") if (fk_dir / f"{fr.name}.npy").exists() \
                else holdout.frame_kernel(fr, cache_dir=fk_dir)
            keep = ~fr.masked[dots // foot.shape[1], dots % foot.shape[1]]
            rec["frames"][fr.name] = holdout.score_dots(dots[keep], fr, frame_k=fk)
        rows.append(rec)
        print(f"  {f.name[:64]:64s} dots={dots.size:>7,} live={live}", flush=True)

    # ------------------------------------------------------------------ rank calibration
    out = {"artifacts": rows, "frames": {}, "correlations": {}}
    for fam in ("A", "B", "C"):
        fam_frames = [f.name for f in frames if f.name.startswith(fam)]
        per_artifact = []
        for r in rows:
            vals = [r["frames"][k]["dti"] for k in fam_frames if k in r["frames"]]
            if vals:
                per_artifact.append((np.mean(vals), r["live_score"], r["artifact"]))
        scored = [(m, l, a) for m, l, a in per_artifact if l is not None]
        corr = None
        if len(scored) >= 4:
            rho, p = spearmanr([s[0] for s in scored], [s[1] for s in scored])
            corr = {"n": len(scored), "spearman_rho": float(rho), "p_value": float(p)}
        out["frames"][fam] = {
            "frames": fam_frames,
            "n_artifacts": len(per_artifact),
            "best_artifact": max(per_artifact)[2] if per_artifact else None,
            "best_mean_dti": float(max(per_artifact)[0]) if per_artifact else None,
        }
        out["correlations"][fam] = corr

    # the reference bar: best mean DTI achieved by an artifact with a known live score
    for fam in ("A", "B", "C"):
        vals = []
        for r in rows:
            if r["live_score"] is None:
                continue
            v = [r["frames"][k]["dti"] for k in r["frames"] if k.startswith(fam)]
            if v:
                vals.append((np.mean(v), r["live_score"], r["live_name"]))
        if vals:
            out.setdefault("reference_bar", {})[fam] = {
                "best_scored_artifact": max(vals)[2],
                "best_scored_live": float(max(vals)[1]),
                "best_scored_mean_dti": float(max(vals)[0]),
            }

    dest = paths.evidence_dir() / "instrument_calibration.json"
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps({"correlations": out["correlations"],
                      "reference_bar": out.get("reference_bar", {})}, indent=1))
    print(f"wrote {dest}")
    return 0


def files_in(d):
    from pathlib import Path
    p = Path(d)
    return sorted([f for f in p.glob("*.tif")] + [f for f in p.glob("*.TIF")])


if __name__ == "__main__":
    raise SystemExit(main())
