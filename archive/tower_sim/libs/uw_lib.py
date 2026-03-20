from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class UWTable:
    name: str
    columns: Dict[str, list[str]]



_FIXTURE_DATA_DIRS = (
    Path("tests/fixtures/tower-sim-data"),
    Path("tests/fixtures"),
)


def resolve_data_file(filename: str) -> Path:
    for directory in _FIXTURE_DATA_DIRS:
        candidate = directory / filename
        if candidate.exists():
            return candidate
    candidates = ", ".join(str(directory / filename) for directory in _FIXTURE_DATA_DIRS)
    raise FileNotFoundError(f"Missing data file {filename}. Tried: {candidates}")


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def load_uw_table(filename: str, name: Optional[str] = None) -> UWTable:
    path = resolve_data_file(filename)
    rows = _read_csv(path)
    if not rows:
        raise ValueError(f"UW table {filename} is empty.")
    header = [cell.strip() for cell in rows[0]]
    columns: Dict[str, list[str]] = {col: [] for col in header if col}
    for row in rows[1:]:
        for idx, col in enumerate(header):
            if not col:
                continue
            value = row[idx].strip() if idx < len(row) else ""
            columns[col].append(value)
    return UWTable(name=name or filename, columns=columns)


def uw_value(uw_table: UWTable, column: str, row_index: int) -> str:
    if column not in uw_table.columns:
        raise KeyError(f"UW column not found: {column!r}")
    values = uw_table.columns[column]
    if row_index < 0 or row_index >= len(values):
        raise KeyError(f"UW row index {row_index} out of range for column {column!r}")
    value = values[row_index]
    if value == "":
        raise KeyError(f"UW value missing at row {row_index} for column {column!r}")
    return value
