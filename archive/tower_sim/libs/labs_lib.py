from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from functools import lru_cache
from typing import Dict, List


class UnknownLabError(KeyError):
    pass


class InvalidLabLevelError(ValueError):
    pass


@dataclass(frozen=True)
class LabLevels:
    canonical_id: str
    primary_name: str
    unit: str
    levels: Dict[int, float]


REQUIRED_HEADERS = {
    "lab_canonical_id",
    "lab_primary_name",
    "level",
    "value",
    "unit",
    "source_path",
    "source_sha256",
    "source_modified_utc",
}
ALLOWED_UNITS = {"percent_points", "percent", "raw_number"}


def _default_table_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return resolve_table_path("labs_values")


def _parse_level(value: str) -> int:
    candidate = value.strip()
    if candidate == "":
        raise ValueError("Missing level value")
    try:
        numeric = float(candidate)
    except ValueError as exc:
        raise ValueError(f"Invalid level value: {value}") from exc
    if not numeric.is_integer():
        raise ValueError(f"Non-integer level value: {value}")
    return int(numeric)


def _parse_value(value: str) -> float:
    candidate = value.strip()
    if candidate == "":
        raise ValueError("Missing value")
    return float(candidate)


def load_labs_values(path: Path | None = None) -> Dict[str, LabLevels]:
    table_path = path or _default_table_path()
    if not table_path.exists():
        raise FileNotFoundError(f"Missing labs values table: {table_path}")

    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Labs values table missing headers")
        missing = REQUIRED_HEADERS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Labs values table missing columns: {sorted(missing)}")

        labs: Dict[str, LabLevels] = {}
        for row in reader:
            lab_name = row["lab_primary_name"].strip()
            lab_id = row["lab_canonical_id"].strip()
            unit = row["unit"].strip()
            if unit not in ALLOWED_UNITS:
                raise ValueError(f"Unsupported unit {unit!r} for lab {lab_name}")
            level = _parse_level(row["level"])
            value = _parse_value(row["value"])

            existing = labs.get(lab_name)
            if existing is None:
                labs[lab_name] = LabLevels(
                    canonical_id=lab_id,
                    primary_name=lab_name,
                    unit=unit,
                    levels={level: value},
                )
                continue
            if existing.canonical_id != lab_id:
                raise ValueError(f"Lab {lab_name} has mismatched canonical IDs")
            if existing.unit != unit:
                raise ValueError(f"Lab {lab_name} has mismatched units")
            if level in existing.levels:
                raise ValueError(f"Duplicate level {level} for lab {lab_name}")
            existing.levels[level] = value

    if not labs:
        raise ValueError("Labs values table is empty")

    return labs


@lru_cache(maxsize=1)
def _load_default_labs() -> Dict[str, LabLevels]:
    return load_labs_values()


def list_labs() -> List[str]:
    return sorted(_load_default_labs().keys())


def max_level(lab_name: str) -> int:
    labs = _load_default_labs()
    if lab_name not in labs:
        raise UnknownLabError(f"Unknown lab: {lab_name!r}")
    return max(labs[lab_name].levels)


def get_effects(lab_name: str, level: int) -> Dict[str, float]:
    labs = _load_default_labs()
    if lab_name not in labs:
        raise UnknownLabError(f"Unknown lab: {lab_name!r}")
    if level <= 0:
        raise InvalidLabLevelError(f"Invalid lab level {level} for {lab_name!r}")
    lab = labs[lab_name]
    if level not in lab.levels:
        raise InvalidLabLevelError(f"Invalid lab level {level} for {lab_name!r}")
    return {lab.canonical_id: lab.levels[level]}


def labs_from_table(path: Path | None = None) -> Dict[str, LabLevels]:
    return load_labs_values(path)


__all__ = [
    "InvalidLabLevelError",
    "LabLevels",
    "UnknownLabError",
    "get_effects",
    "labs_from_table",
    "list_labs",
    "load_labs_values",
    "max_level",
]
