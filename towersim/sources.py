
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import zipfile
import os
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

@dataclass(frozen=True)
class SnapshotPriority:
    # Priority order:
    # 1) git snapshot pulled within last 24h (stored locally)
    # 2) live git pull (NOT used in this offline package)
    # 3) older snapshot (stored locally)
    # 4) fallback (explicit local file paths)
    fresh_hours: int = 24

def is_fresh(path: Path, hours: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=hours)

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
