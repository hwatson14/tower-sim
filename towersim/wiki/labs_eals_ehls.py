from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from pathlib import Path

@dataclass(frozen=True)
class LabEffect:
    name: str
    level: int
    value: float
    unit: str  # 'pp' percent-points, 'mult', etc.

def load_lab_table(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path)

def get_eals_lab_pp(level: int, cache_dir: Path) -> float:
    df = load_lab_table(cache_dir / "lab_enemy_attack_level_skip.csv")
    row = df.loc[df["level"] == level]
    if row.empty:
        raise ValueError(f"EALS lab level {level} not in cache.")
    return float(row["value_percent_points"].iloc[0])

def get_ehls_lab_pp(level: int, cache_dir: Path) -> float:
    df = load_lab_table(cache_dir / "lab_enemy_health_level_skip.csv")
    row = df.loc[df["level"] == level]
    if row.empty:
        raise ValueError(f"EHLS lab level {level} not in cache.")
    return float(row["value_percent_points"].iloc[0])