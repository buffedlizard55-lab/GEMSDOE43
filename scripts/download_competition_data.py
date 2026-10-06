#!/usr/bin/env python3
"""Restore hash-pinned owner-published mirrors of the GEMS competition input rasters.

This does not authenticate to DrivenData or prove organizer provenance. It uses the
GitHub CLI to fetch files pinned to public commits in the source manifest, verifies
all final bytes, and leaves the large raw inputs out of Git.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_sources.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def gh_fetch(repository: str, commit: str, source_path: str, destination: Path) -> None:
    """Fetch one raw object through `gh api`, retrying transient failures."""
    if not shutil.which("gh"):
        raise RuntimeError("GitHub CLI `gh` is required to restore the published mirrors")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    endpoint = f"repos/{repository}/contents/{source_path}?ref={commit}"
    last_error = None
    for attempt in range(1, 4):
        try:
            with partial.open("wb") as output:
                subprocess.run(
                    ["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"],
                    stdout=output,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            if partial.stat().st_size == 0:
                raise RuntimeError("GitHub API returned an empty object")
            partial.replace(destination)
            return
        except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt)
    if isinstance(last_error, subprocess.CalledProcessError):
        detail = (last_error.stderr or b"").decode("utf-8", errors="replace").strip()
        # Do not print environment variables or credential-bearing command details.
        raise RuntimeError(f"GitHub API fetch failed for {source_path}: {detail[:500]}") from last_error
    raise RuntimeError(f"GitHub API fetch failed for {source_path}: {last_error}")


def restore_file(entry: dict, target_dir: Path) -> dict:
    relative = Path(entry["destination"]).relative_to("data")
    destination = target_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_size = int(entry["bytes"])
    expected_sha = entry["sha256"]

    if destination.is_file() and destination.stat().st_size == expected_size and sha256(destination) == expected_sha:
        return {"id": entry["id"], "path": str(destination.relative_to(ROOT)), "status": "already_verified",
                "bytes": expected_size, "sha256": expected_sha}

    staging = target_dir / ".restore_staging"
    staging.mkdir(parents=True, exist_ok=True)
    assembled = staging / (entry["id"] + ".assembling")
    try:
        if "parts" in entry:
            with assembled.open("wb") as output:
                for index, source_path in enumerate(entry["parts"]):
                    part = staging / f"{entry['id']}.part-{index:03d}"
                    print(f"  fetching {source_path}", flush=True)
                    gh_fetch(entry["repository"], entry["commit"], source_path, part)
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output, 1 << 20)
                    part.unlink()
        else:
            source_path = entry["path"]
            print(f"  fetching {source_path}", flush=True)
            gh_fetch(entry["repository"], entry["commit"], source_path, assembled)

        if not assembled.is_file():
            raise RuntimeError("download did not produce an assembled file")
        actual_size = assembled.stat().st_size
        actual_sha = sha256(assembled)
        if actual_size != expected_size or actual_sha != expected_sha:
            raise RuntimeError(
                f"integrity failure for {entry['id']}: expected {expected_size} bytes / {expected_sha}; "
                f"received {actual_size} bytes / {actual_sha}"
            )
        os.replace(assembled, destination)
        return {"id": entry["id"], "path": str(destination.relative_to(ROOT)), "status": "restored_and_verified",
                "bytes": actual_size, "sha256": actual_sha}
    finally:
        assembled.unlink(missing_ok=True)
        for leftover in staging.glob(f"{entry['id']}.part-*"):
            leftover.unlink(missing_ok=True)
        try:
            staging.rmdir()
        except OSError:
            pass


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    target_dir = Path(os.environ.get("GEMS_DATA_DIR", ROOT / "data")).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_manifest": str(MANIFEST.relative_to(ROOT)),
        "provenance_warning": manifest["mirror_caveat"],
        "files": [],
    }
    try:
        for entry in manifest["files"]:
            result = restore_file(entry, target_dir)
            receipt["files"].append(result)
            print(f"[{result['status']}] {result['id']}: {result['bytes']:,} bytes, sha256 {result['sha256']}", flush=True)
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        out = ROOT / "evidence" / "data_restore_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: {receipt['error']}", file=sys.stderr)
        print(f"Partial receipt written to {out.relative_to(ROOT)}", file=sys.stderr)
        return 1

    receipt["all_files_verified"] = len(receipt["files"]) == len(manifest["files"])
    receipt["organizer_authenticated"] = False
    out = ROOT / "evidence" / "data_restore_receipt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"\nReceipt: {out.relative_to(ROOT)}")
    print("Mirror integrity: PASS; organizer provenance: NOT VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
