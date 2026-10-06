"""Path resolution for GEMSDOE43."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Directory holding the hash-pinned competition inputs."""
    env = os.environ.get("GEMS_DATA_DIR")
    if env:
        return Path(env).expanduser()
    return ROOT / ".cache" / "gems_data"


def work_dir() -> Path:
    """Scratch directory for regenerable numpy caches (never committed)."""
    env = os.environ.get("GEMS_WORK_DIR")
    if env:
        return Path(env).expanduser()
    return ROOT / ".cache" / "gems_work"


def bands_dir() -> Path:
    d = work_dir() / "bands"
    d.mkdir(parents=True, exist_ok=True)
    return d


def docs_dir() -> Path:
    d = ROOT / "docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def downloads_dir() -> Path:
    d = ROOT / "docs" / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def evidence_dir() -> Path:
    d = ROOT / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def registry_dir() -> Path:
    d = ROOT / "registry"
    d.mkdir(parents=True, exist_ok=True)
    return d
