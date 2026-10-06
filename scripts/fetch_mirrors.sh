#!/usr/bin/env bash
# Fetch every hash-pinned competition mirror and FAIL CLOSED on any digest mismatch.
#
# Why this script exists: the competition's own data download page
# (https://www.drivendata.org/competitions/306/competition-doe-gems/data/) requires a
# DrivenData login, which this environment does not have (IR-43-001).  The bytes used here
# come from owner-maintained public GitHub blobs that were exported from the competition
# bundle by earlier GEMSDOE sites.  They are therefore NOT organizer-authenticated bytes:
# the only thing that makes them usable is that every file is pinned by sha256 in
# registry/data_manifest.json.  A fetch that does not verify is worthless, so this script
# verifies digests and exits non-zero on any mismatch.
#
# Requires: `gh` authenticated for github.com (or GH_TOKEN in the environment).
# No DrivenData credentials are ever used and drivendata.org is never contacted.
#
# Usage:  bash scripts/fetch_mirrors.sh [DEST]        (default DEST=.cache/gems_data)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/.cache/gems_data}"
MANIFEST="$ROOT/registry/data_manifest.json"
mkdir -p "$DEST" "$DEST/external" "$DEST/inputs"

python3 - "$MANIFEST" "$DEST" <<'PY'
import json, subprocess, sys, hashlib, os
from pathlib import Path

manifest, dest = Path(sys.argv[1]), Path(sys.argv[2])
spec = json.loads(manifest.read_text())
fail = []


def gh(repo, ref, path, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                        "-H", "Accept: application/vnd.github.raw"],
                       stdout=fh, check=True)


for f in spec["files"]:
    target = dest / f["dest"]
    if target.exists() and target.stat().st_size == f["bytes"]:
        got = hashlib.sha256(target.read_bytes()).hexdigest()
        if got == f["sha256"]:
            print(f"CACHED {f['id']:24s} {f['bytes']:>12,} bytes  {got[:16]}...")
            continue
    if "parts" in f:
        chunks = []
        for i, p in enumerate(f["parts"]):
            c = dest / f"_part-{i:03d}"
            gh(f["repo"], f["ref"], p, c)
            chunks.append(c)
        with target.open("wb") as out:
            for c in chunks:
                out.write(c.read_bytes())
        for c in chunks:
            c.unlink()
    else:
        gh(f["repo"], f["ref"], f["path"], target)
    got = hashlib.sha256(target.read_bytes()).hexdigest()
    nbytes = os.path.getsize(target)
    ok = (got == f["sha256"]) and (nbytes == f["bytes"])
    print(("PASS " if ok else "FAIL ") +
          f"{f['id']:24s} {nbytes:>12,} bytes  {got[:16]}...")
    if not ok:
        fail.append(f["id"])

print(json.dumps({"verified": len(spec["files"]) - len(fail), "failed": fail}, indent=1))
sys.exit(1 if fail else 0)
PY
