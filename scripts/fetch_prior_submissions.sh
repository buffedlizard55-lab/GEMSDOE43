#!/usr/bin/env bash
# Collect prior GEMSDOE submission GeoTIFFs (for the near-duplicate screen only).
#
# These are the group's own previously-uploaded artifacts, re-read from the public GitHub Pages
# repositories that publish them.  They are used for ONE purpose: to prove the new layout is not
# a near-duplicate of an earlier one.  They are never used as input to any model.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/.cache/prior_submissions}"
mkdir -p "$DEST"

REPOS="GEMSDOE 6GEMSDOE GEMSDOE3 GEMSDOE2 GEMSDOE4 5GEMSDOE 7GEMSDOE 8GEMSDOE GEMSDOE9 11GEMSDOE 12GEMSDOE 15GEMSDOE 14GEMSDOE 17GEMSDOE 18GEMSDOE 19GEMSDOE GEMSDOE10 13GEMSDOE 16GEMSDOE GEMSDOE21 20GEMSDOE GEMSDOE22 GEMSDOE23 GEMSDOE24 GEMSDOE25 GEMSDOE26 GEMSDOE27 GEMSDOE28 GEMSDOE29 GEMSDOE30 GEMSDOE31 GEMSDOE32 GEMSDOE33 GEMSDOE34 GEMSDOE35 GEMSDOE36 GEMSDOE37 GEMSDOE38 GEMSDOE39 GEMSDOE40 GEMSDOE41 GEMSDOE42 GEMSDOE43"

python3 - "$DEST" $REPOS <<'PY'
import json, subprocess, sys, hashlib, os
from pathlib import Path

dest = Path(sys.argv[1])
repos = sys.argv[2:]
manifest = {}
if (dest / "manifest.json").exists():
    manifest = json.loads((dest / "manifest.json").read_text())

def gh(*args):
    return subprocess.run(["gh", "api", *args], capture_output=True, check=True).stdout

for repo in repos:
    full = f"buffedlizard55-lab/{repo}"
    try:
        branches = json.loads(gh(f"repos/{full}/branches"))
    except Exception as e:
        print(f"SKIP {repo}: {e}")
        continue
    if not branches:
        continue
    ref = branches[0]["name"]
    try:
        tree = json.loads(gh(f"repos/{full}/git/trees/{ref}?recursive=1"))
    except Exception as e:
        print(f"SKIP {repo} tree: {e}")
        continue
    items = [t for t in tree.get("tree", [])
             if t["path"].lower().endswith((".tif", ".zip"))
             and t.get("size", 0) > 1000
             and t.get("size", 0) < 30_000_000]
    for it in items:
        name = f"{repo}__" + it["path"].replace("/", "_")
        out = dest / name
        if name in manifest and out.exists() and out.stat().st_size == it["size"]:
            continue
        try:
            data = subprocess.run(
                ["gh", "api", f"repos/{full}/git/blobs/{it['sha']}",
                 "-H", "Accept: application/vnd.github.raw"],
                capture_output=True, check=True).stdout
        except Exception as e:
            print(f"  fail {repo}:{it['path']}: {e}")
            continue
        out.write_bytes(data)
        manifest[name] = {
            "repo": repo, "path": it["path"], "branch": ref,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
    print(f"{repo}: {len(items)} artifacts")

(dest / "manifest.json").write_text(json.dumps(manifest, indent=1))
print(f"TOTAL {len(manifest)} prior artifacts in {dest}")
PY
