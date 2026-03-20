from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

_CACHE_DIR = Path(__file__).resolve().parents[3] / "tables" / "cache" / "wiki"

@dataclass(frozen=True)
class LabEffect:
    lab: str
    level: int
    value: float
    value_raw: str
    unit: str  # 'mult', 'percent', 'flat', 'unknown'

"""Cached Lab level tables.

We intentionally cache wiki tables as CSVs so the simulator can run without
network access.

Cache convention
----------------
Each cached lab file is named ``lab_<slug>.csv`` where slug is a safe
lowercase/underscore rendering of the lab title.

Legacy cache names (from early prototypes) are still supported.
"""

_LEGACY_LAB_FILES = {
    "Health": "lab_health.csv",
    "Health Regen": "lab_health_regen.csv",
    "Recovery Package Chance": "lab_recovery_package_chance.csv",
    "Wall Health": "wall_lab_wall_health.csv",
    "Wall Regen": "wall_lab_wall_regen.csv",
}

_LABS_DF: dict[str, pd.DataFrame] = {}

def _infer_unit(s: str) -> str:
    s = str(s).strip()
    if s.endswith("%"):
        return "percent"
    if s.lower().endswith("x"):
        return "mult"
    # many labs use numeric multiplier without 'x' (e.g., 1.03)
    try:
        v = float(s)
        if v >= 0.5 and v <= 10:
            return "mult"
    except Exception:
        pass
    return "unknown"

def _parse_value(s: str) -> float:
    s = str(s).strip().replace(",", "")
    if s.endswith("%"):
        return float(s[:-1]) / 100.0
    if s.lower().endswith("x"):
        return float(s[:-1])
    return float(s)

def _load_lab_df(lab_name: str) -> pd.DataFrame:
    # 1) New convention: lab_<slug>.csv
    from .labs_ingest_all import slugify
    slug = slugify(lab_name)
    p = _CACHE_DIR / f"lab_{slug}.csv"
    if p.exists():
        return pd.read_csv(p)

    # 2) Legacy convention (kept for backwards compatibility)
    if lab_name in _LEGACY_LAB_FILES:
        p2 = _CACHE_DIR / _LEGACY_LAB_FILES[lab_name]
        if p2.exists():
            return pd.read_csv(p2)

    raise KeyError(
        f"Lab not cached yet: {lab_name!r}. "
        f"Expected {p.name} in {_CACHE_DIR}"
    )

def get_lab_effect(lab_name: str, level: int) -> LabEffect:
    """Return the lab's Value at a given level, from cached fandom tables."""
    # 0) Formula-backed labs (exact closed-form, verified against wiki tables)
    try:
        from .labs_formula import has_formula, eval_formula
        if has_formula(lab_name) and level >= 0:
            if level == 0:
                return LabEffect(lab=lab_name, level=0, value=1.0, value_raw="0", unit="mult")
            val, raw, unit = eval_formula(lab_name, level)
            return LabEffect(lab=lab_name, level=level, value=val, value_raw=raw, unit=unit)
    except Exception:
        # If anything goes wrong, fall back to cached tables (safer)
        pass

    if lab_name not in _LABS_DF:
        _LABS_DF[lab_name] = _load_lab_df(lab_name)
    df = _LABS_DF[lab_name]
    if level < 0:
        raise ValueError("Lab level must be >= 0")
    if level == 0:
        # neutral effect
        return LabEffect(lab=lab_name, level=0, value=1.0, value_raw="0", unit="mult")
    # wiki tables start at level 1
    row = df[df["Level"] == level]
    if row.empty:
        raise KeyError(f"Level {level} not found for lab {lab_name}")
    raw = row.iloc[0]["Value"]
    unit = _infer_unit(raw)
    val = _parse_value(raw)
    return LabEffect(lab=lab_name, level=level, value=val, value_raw=str(raw), unit=unit)
