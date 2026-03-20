
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Dict, Iterable, Optional
import zipfile

import pandas as pd
from tower_sim.loaders.ids_parser import DEFAULT_IDS_PATHS, resolve_ids_path

DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "tower-sim-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class SnapshotPriority:
    # Priority order:
    # 1) git snapshot pulled within last 24h (stored locally)
    # 2) live git pull (NOT used in this offline package)
    # 3) older snapshot (stored locally)
    # 4) fallback (explicit local file paths)
    fresh_hours: int = 24


@dataclass(frozen=True)
class DatasetBundle:
    snapshot_dir: Path
    manifest_path: Path
    manifest: Dict[str, object]
    files: Dict[str, Path]
    resolved_from: str


@dataclass(frozen=True)
class IdsOnlyBundle:
    ids_path: Path
    resolved_from: str

def is_fresh(path: Path, hours: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=hours)


def _find_snapshot_dirs(parent: Path) -> list[Path]:
    if not parent.exists():
        return []
    if (parent / MANIFEST_FILENAME).exists():
        return [parent]
    return sorted(
        [
            path
            for path in parent.iterdir()
            if path.is_dir() and (path / MANIFEST_FILENAME).exists()
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _select_snapshot_dir(
    cache_dirs: Iterable[Path],
    git_dir: Optional[Path],
    priority: SnapshotPriority,
) -> tuple[Path, str]:
    candidates = []
    for cache_dir in cache_dirs:
        candidates.extend(_find_snapshot_dirs(cache_dir))
    if candidates:
        freshest = candidates[0]
        if is_fresh(freshest, priority.fresh_hours):
            return freshest, "cache:fresh"

    if git_dir is not None:
        git_snapshots = _find_snapshot_dirs(git_dir)
        if git_snapshots:
            return git_snapshots[0], "git"

    if candidates:
        return candidates[0], "cache:stale"

    raise FileNotFoundError(
        "No snapshot directories found. "
        "Checked cache dirs: "
        + ", ".join(str(path) for path in cache_dirs)
        + (f" and git dir: {git_dir}" if git_dir else "")
    )


def load_snapshot_bundle(
    cache_dirs: Iterable[Path],
    git_dir: Optional[Path] = None,
    priority: SnapshotPriority = SnapshotPriority(),
) -> DatasetBundle:
    snapshot_dir, resolved_from = _select_snapshot_dir(cache_dirs, git_dir, priority)
    manifest_path = snapshot_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.json in snapshot: {snapshot_dir}")
    manifest = json.loads(manifest_path.read_text())
    files = {}
    for name, metadata in manifest.get("files", {}).items():
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid manifest entry for {name!r}.")
        files[name] = snapshot_dir / name
    return DatasetBundle(
        snapshot_dir=snapshot_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        files=files,
        resolved_from=resolved_from,
    )


def load_ids_only_bundle(
    paths: Iterable[Path] = DEFAULT_IDS_PATHS,
) -> IdsOnlyBundle:
    ids_path = resolve_ids_path(tuple(paths))
    return IdsOnlyBundle(ids_path=ids_path, resolved_from="ids_only")

def ensure_snapshot_unzipped(snapshot_zip: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        return
    with zipfile.ZipFile(snapshot_zip, "r") as z:
        z.extractall(out_dir)

def load_csv(name: str, snapshot_dir: Path) -> pd.DataFrame:
    path = snapshot_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV in snapshot: {path}")
    return pd.read_csv(path)
