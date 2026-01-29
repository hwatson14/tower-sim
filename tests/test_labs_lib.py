from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tower_sim.libs.labs_lib import (
    InvalidLabLevelError,
    UnknownLabError,
    get_effects,
    list_labs,
    max_level,
)
from tower_sim.registry.stat_registry import default_registry


def _load_expected_value(lab_name: str, level: int) -> float:
    table_path = Path(__file__).resolve().parents[1] / "tables" / "labs_values_v1.csv"
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["lab_primary_name"] == lab_name and int(row["level"]) == level:
                return float(row["value"])
    raise AssertionError(f"Missing value for {lab_name} level {level}")


def test_labs_lib_lookup() -> None:
    assert "Health" in list_labs()
    value = get_effects("Health", 1)
    assert value["LAB_HEALTH"] == _load_expected_value("Health", 1)


def test_labs_lib_bounds() -> None:
    with pytest.raises(InvalidLabLevelError):
        get_effects("Health", 0)
    with pytest.raises(InvalidLabLevelError):
        get_effects("Health", max_level("Health") + 1)
    with pytest.raises(UnknownLabError):
        max_level("Not A Lab")


def test_labs_effects_stat_keys_are_valid() -> None:
    registry = default_registry()
    effects = get_effects("Health", 1)
    for key in effects:
        if key.startswith("LAB_"):
            continue
        registry.validate_stat_id(key)
