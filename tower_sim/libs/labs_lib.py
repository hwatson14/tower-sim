from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class LabsTable:
    lab_key: str
    levels: Dict[int, str]


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def load_labs_tables(cache_dir: Path = Path("tower_sim/wiki/cache")) -> Dict[str, LabsTable]:
    tables: Dict[str, LabsTable] = {}
    for path in sorted(cache_dir.glob("*.csv")):
        if not (path.stem.startswith("lab_") or path.stem.startswith("wall_lab_")):
            continue
        rows = _read_csv(path)
        if not rows:
            continue
        header = [cell.strip() for cell in rows[0]]
        if "Level" not in header or "Value" not in header:
            continue
        level_idx = header.index("Level")
        value_idx = header.index("Value")
        levels: Dict[int, str] = {}
        for row in rows[1:]:
            if level_idx >= len(row) or value_idx >= len(row):
                continue
            level_str = row[level_idx].strip()
            value = row[value_idx].strip()
            if level_str == "" or value == "":
                continue
            levels[int(level_str)] = value
        tables[path.stem] = LabsTable(lab_key=path.stem, levels=levels)
    return tables


def lab_value(lab_key: str, level: int, tables: Dict[str, LabsTable]) -> str:
    if lab_key not in tables:
        raise KeyError(f"Lab key not found: {lab_key!r}")
    table = tables[lab_key]
    if level not in table.levels:
        raise KeyError(f"Lab level {level} missing for {lab_key!r}")
    return table.levels[level]
