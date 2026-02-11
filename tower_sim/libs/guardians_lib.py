from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, List, Optional


class UnknownGuardianError(KeyError):
    pass


class UnknownGuardianAttributeError(KeyError):
    pass


class InvalidGuardianLevelError(ValueError):
    pass


@dataclass(frozen=True)
class GuardianAttributeLevels:
    guardian: str
    attribute: str
    values: Dict[int, float]
    costs: Dict[int, Optional[float]]
    max_levels: set[int]


REQUIRED_HEADERS = {
    "guardian",
    "attribute",
    "level",
    "value",
    "cost",
    "is_max",
    "source_path",
    "source_sha256",
    "source_modified_utc",
    "source_sheet",
}


def _default_table_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return resolve_table_path("guardian_upgrades")


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


def _parse_cost(value: str) -> Optional[float]:
    candidate = value.strip()
    if candidate == "":
        return None
    return float(candidate)


def _parse_is_max(value: str) -> bool:
    candidate = value.strip().lower()
    if candidate not in {"true", "false"}:
        raise ValueError(f"Invalid is_max value: {value}")
    return candidate == "true"


def load_guardian_upgrades(
    path: Path | None = None,
) -> Dict[str, Dict[str, GuardianAttributeLevels]]:
    table_path = path or _default_table_path()
    if not table_path.exists():
        raise FileNotFoundError(f"Missing guardian upgrades table: {table_path}")

    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Guardian upgrades table missing headers")
        missing = REQUIRED_HEADERS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Guardian upgrades table missing columns: {sorted(missing)}")

        guardians: Dict[str, Dict[str, GuardianAttributeLevels]] = {}
        for row in reader:
            guardian = row["guardian"].strip()
            attribute = row["attribute"].strip()
            level = _parse_level(row["level"])
            value = _parse_value(row["value"])
            cost = _parse_cost(row["cost"])
            is_max = _parse_is_max(row["is_max"])

            guardian_attrs = guardians.setdefault(guardian, {})
            existing = guardian_attrs.get(attribute)
            if existing is None:
                guardian_attrs[attribute] = GuardianAttributeLevels(
                    guardian=guardian,
                    attribute=attribute,
                    values={level: value},
                    costs={level: cost},
                    max_levels={level} if is_max else set(),
                )
                continue

            if level in existing.values:
                raise ValueError(
                    f"Duplicate level {level} for guardian {guardian} attribute {attribute}"
                )
            existing.values[level] = value
            existing.costs[level] = cost
            if is_max:
                existing.max_levels.add(level)

    if not guardians:
        raise ValueError("Guardian upgrades table is empty")

    return guardians


@lru_cache(maxsize=1)
def _load_default_guardian_upgrades() -> Dict[str, Dict[str, GuardianAttributeLevels]]:
    return load_guardian_upgrades()


def list_guardians() -> List[str]:
    return sorted(_load_default_guardian_upgrades().keys())


def list_guardian_attributes(guardian: str) -> List[str]:
    guardians = _load_default_guardian_upgrades()
    if guardian not in guardians:
        raise UnknownGuardianError(f"Unknown guardian: {guardian!r}")
    return sorted(guardians[guardian].keys())


def get_guardian_attribute(
    guardian: str, attribute: str, level: int
) -> tuple[float, Optional[float], bool]:
    guardians = _load_default_guardian_upgrades()
    if guardian not in guardians:
        raise UnknownGuardianError(f"Unknown guardian: {guardian!r}")
    guardian_attrs = guardians[guardian]
    if attribute not in guardian_attrs:
        raise UnknownGuardianAttributeError(
            f"Unknown guardian attribute: {attribute!r} for guardian {guardian!r}"
        )
    if level <= 0 and level not in guardian_attrs[attribute].values:
        raise InvalidGuardianLevelError(
            f"Invalid level {level} for guardian {guardian!r} attribute {attribute!r}"
        )
    entry = guardian_attrs[attribute]
    if level not in entry.values:
        raise InvalidGuardianLevelError(
            f"Invalid level {level} for guardian {guardian!r} attribute {attribute!r}"
        )
    return entry.values[level], entry.costs[level], level in entry.max_levels


def guardians_from_table(path: Path | None = None) -> Dict[str, Dict[str, GuardianAttributeLevels]]:
    return load_guardian_upgrades(path)


__all__ = [
    "GuardianAttributeLevels",
    "InvalidGuardianLevelError",
    "UnknownGuardianAttributeError",
    "UnknownGuardianError",
    "guardians_from_table",
    "get_guardian_attribute",
    "list_guardian_attributes",
    "list_guardians",
    "load_guardian_upgrades",
]
