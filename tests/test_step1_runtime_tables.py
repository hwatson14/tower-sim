from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tower_sim.libs import step1_tables


ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = ROOT / "tables"
REFERENCE_STEP1_DIR = ROOT / "reference" / "step1_dump_docs"


def _read_fieldnames(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    return header


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def test_step1_tables_present() -> None:
    required = [
        "battle_condition_magnitudes.csv",
        "tournament_more_bosses_static.csv",
        "tier_wave_damage.csv",
        "tournament_wave_damage.csv",
        "tier_battle_conditions.csv",
        "dag.json",
    ]
    for filename in required:
        assert (TABLES_DIR / filename).exists(), f"Missing {filename} in {TABLES_DIR}"


def test_heat_wave_scalar_promoted_if_present() -> None:
    reference_files = list(REFERENCE_STEP1_DIR.rglob("heat_wave_scalar.csv"))
    if reference_files:
        assert (TABLES_DIR / "heat_wave_scalar.csv").exists()


def test_battle_condition_magnitudes_schema_and_keys() -> None:
    path = TABLES_DIR / "battle_condition_magnitudes.csv"
    assert _read_fieldnames(path) == ["bc_id", "league", "wave", "magnitude"]
    rows = _read_rows(path)
    keys = {(row["bc_id"], row["league"], row["wave"]) for row in rows}
    assert len(keys) == len(rows)


def test_tournament_more_bosses_schema_and_keys() -> None:
    path = TABLES_DIR / "tournament_more_bosses_static.csv"
    assert _read_fieldnames(path) == ["league", "boss_every_n_waves"]
    rows = _read_rows(path)
    keys = {row["league"] for row in rows}
    assert len(keys) == len(rows)


def test_tier_wave_damage_schema_and_keys() -> None:
    path = TABLES_DIR / "tier_wave_damage.csv"
    assert _read_fieldnames(path) == ["tier", "wave", "wave_damage"]
    rows = _read_rows(path)
    keys = {(row["tier"], row["wave"]) for row in rows}
    assert len(keys) == len(rows)


def test_tournament_wave_damage_schema_and_keys() -> None:
    path = TABLES_DIR / "tournament_wave_damage.csv"
    assert _read_fieldnames(path) == ["tournament_league", "wave", "wave_damage"]
    rows = _read_rows(path)
    keys = {(row["tournament_league"], row["wave"]) for row in rows}
    assert len(keys) == len(rows)


def test_tier_battle_conditions_schema_and_keys() -> None:
    path = TABLES_DIR / "tier_battle_conditions.csv"
    assert _read_fieldnames(path) == ["tier", "bc", "kind", "value", "unit", "notes"]
    rows = _read_rows(path)
    keys = {(row["tier"], row["bc"], row["kind"]) for row in rows}
    assert len(keys) == len(rows)


def test_step1_table_loaders() -> None:
    bc_rows = _read_rows(TABLES_DIR / "battle_condition_magnitudes.csv")
    if bc_rows:
        assert step1_tables.load_battle_condition_magnitudes()
    else:
        with pytest.raises(ValueError):
            step1_tables.load_battle_condition_magnitudes()
    assert step1_tables.load_tournament_more_bosses_static()
    assert step1_tables.load_tier_wave_damage_rows()
    assert step1_tables.load_tournament_wave_damage_rows()
    assert step1_tables.load_tier_battle_condition_rows()
    assert step1_tables.load_dag_table()


def test_heat_wave_loader_if_present() -> None:
    if (TABLES_DIR / "heat_wave_scalar.csv").exists():
        assert step1_tables.load_heat_wave_scalars()
    else:
        pytest.skip("heat_wave_scalar.csv not available in runtime tables")
