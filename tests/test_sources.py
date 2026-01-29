from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.sources import (  # noqa: E402
    DatasetBundle,
    IdsOnlyBundle,
    SnapshotPriority,
    load_ids_only_bundle,
    load_snapshot_bundle,
)


def _write_manifest(path: Path) -> None:
    manifest = {
        "generated_utc": "2026-01-27T00:00:00Z",
        "files": {"_IDS.csv": {"bytes": 1}},
    }
    (path / "manifest.json").write_text(json.dumps(manifest))
    (path / "_IDS.csv").write_text("stub")


def _set_mtime(path: Path, seconds_ago: int) -> None:
    ts = (path.stat().st_mtime - seconds_ago) if path.exists() else None
    if ts is None:
        raise FileNotFoundError(path)
    os.utime(path, (ts, ts))


def test_load_snapshot_bundle_prefers_fresh_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_manifest(cache_dir)

    git_dir = tmp_path / "git"
    git_dir.mkdir()
    _write_manifest(git_dir)

    bundle = load_snapshot_bundle([cache_dir], git_dir=git_dir, priority=SnapshotPriority())

    assert isinstance(bundle, DatasetBundle)
    assert bundle.snapshot_dir == cache_dir
    assert bundle.resolved_from == "cache:fresh"
    assert bundle.files["_IDS.csv"] == cache_dir / "_IDS.csv"


def test_load_snapshot_bundle_uses_git_when_cache_stale(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_manifest(cache_dir)
    _set_mtime(cache_dir, seconds_ago=60 * 60 * 25)

    git_dir = tmp_path / "git"
    git_dir.mkdir()
    _write_manifest(git_dir)

    bundle = load_snapshot_bundle([cache_dir], git_dir=git_dir, priority=SnapshotPriority())

    assert bundle.snapshot_dir == git_dir
    assert bundle.resolved_from == "git"


def test_load_snapshot_bundle_uses_stale_cache_without_git(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_manifest(cache_dir)
    _set_mtime(cache_dir, seconds_ago=60 * 60 * 26)

    bundle = load_snapshot_bundle([cache_dir], git_dir=None, priority=SnapshotPriority())

    assert bundle.snapshot_dir == cache_dir
    assert bundle.resolved_from == "cache:stale"


def test_load_snapshot_bundle_raises_without_snapshots(tmp_path: Path) -> None:
    empty_cache = tmp_path / "empty"
    empty_cache.mkdir()

    with pytest.raises(FileNotFoundError):
        load_snapshot_bundle([empty_cache], git_dir=None, priority=SnapshotPriority())


def test_load_ids_only_bundle_resolves_fixture(tmp_path: Path) -> None:
    ids_path = tmp_path / "_IDS.csv"
    ids_path.write_text("stub")

    bundle = load_ids_only_bundle([ids_path])

    assert isinstance(bundle, IdsOnlyBundle)
    assert bundle.ids_path == ids_path
    assert bundle.resolved_from == "ids_only"
