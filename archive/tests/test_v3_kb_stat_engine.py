from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_stat_connection_map import build_connection_rows, write_csv
from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase
from v3.kb_access import load_yaml
from v3.kb_stat_engine import (
    V3KBStatEngine,
    V3KBStatEngineError,
    load_stat_connection_map,
    load_stat_connection_map_from_csv,
)


def test_build_stat_connection_rows_contains_workshop_health_route() -> None:
    rows = build_connection_rows()
    assert rows
    assert any(
        row["source_family"] == "workshop"
        and row["destination_object_type"] == "canonical_stat"
        and row["destination_id"] == "tower_hp"
        for row in rows
    )


def test_connection_map_roundtrip_from_generated_csv(tmp_path: Path) -> None:
    rows = build_connection_rows()
    out = tmp_path / "stat_connection_map.csv"
    write_csv(rows, out)
    loaded = load_stat_connection_map_from_csv(out)
    assert "workshop" in loaded.allowed_by_family
    assert "tower_hp" in loaded.allowed_by_family["workshop"]
    assert "tower_hp" in loaded.canonical_stats


def test_connection_map_can_auto_generate_csv(tmp_path: Path) -> None:
    out = tmp_path / "stat_connection_map.csv"
    loaded = load_stat_connection_map(csv_path=out, generate_if_missing=True)
    assert out.exists()
    assert "workshop" in loaded.allowed_by_family


def test_v3_kb_stat_engine_accepts_kb_routed_stat_input() -> None:
    engine = V3KBStatEngine()
    result = engine.build(
        [
            StatInput(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                base_value=100.0,
                provenance="workshop_alias:Health->tower_hp",
                contributor_family="workshop",
            )
        ]
    )
    assert result.rows


def test_v3_kb_stat_engine_rejects_unwired_canonical_stat_for_family() -> None:
    engine = V3KBStatEngine()
    with pytest.raises(V3KBStatEngineError, match="kb_unwired:workshop:lab_speed_multiplier"):
        engine.build(
            [
                StatInput(
                    stat_id="lab_speed_multiplier",
                    phase=Phase.START_OF_RUN,
                    base_value=100.0,
                    provenance="workshop_table:Health",
                    contributor_family="workshop",
                )
            ]
        )


def test_connection_map_relic_routes_match_kb_contract(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    contract = load_yaml("kb/global-rules/contracts/contributor-mappings-full.yaml")
    relic_rows = contract["source_families"]["relic"]
    expected = {
        str(row["destination_id"])
        for row in relic_rows
        if str(row.get("destination_object_type") or "") == "canonical_stat"
    }
    assert len(expected) == 26
    assert loaded.allowed_by_family["relic"] == expected


def test_v3_kb_stat_engine_accepts_all_relic_canonical_routes(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    relic_stats = sorted(loaded.allowed_by_family["relic"])
    engine = V3KBStatEngine(connection_map=loaded, strict=True)
    inputs = [
        StatInput(
            stat_id=stat_id,
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance=f"relics:test:{stat_id}",
            contributor_family="relic",
        )
        for stat_id in relic_stats
    ]
    result = engine.build(inputs)
    assert result.rows
    assert {row.stat_id for row in result.rows} == set(relic_stats)


def test_connection_map_card_routes_match_kb_contract(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    contract = load_yaml("kb/global-rules/contracts/contributor-mappings-full.yaml")
    card_rows = contract["source_families"]["card"]
    expected = {
        str(row["destination_id"])
        for row in card_rows
        if str(row.get("destination_object_type") or "") == "canonical_stat"
    }
    assert loaded.allowed_by_family["card"] == expected


def test_v3_kb_stat_engine_accepts_all_card_canonical_routes(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    card_stats = sorted(loaded.allowed_by_family["card"])
    engine = V3KBStatEngine(connection_map=loaded, strict=True)
    inputs = [
        StatInput(
            stat_id=stat_id,
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance=f"cards:test:{stat_id}",
            contributor_family="card",
        )
        for stat_id in card_stats
    ]
    result = engine.build(inputs)
    assert result.rows
    assert {row.stat_id for row in result.rows} == set(card_stats)


def test_connection_map_module_routes_include_main_unique_substats(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    module_routes = loaded.allowed_by_family["module"]
    assert "tower_damage" in module_routes  # main effect
    assert "wall_regen" in module_routes  # unique effect
    assert "tower_attack_speed" in module_routes  # substat
    assert "tower_regen" in module_routes  # substat
    assert "tower_crit_multiplier" in module_routes  # substat
    assert "tower_knockback_force" in module_routes  # substat
    assert "tower_defense_pct" in module_routes  # substat
    assert "tower_defense_absolute" in module_routes  # substat
    assert "tower_range_m" in module_routes  # substat
    assert "tower_knockback_chance_pct" in module_routes  # substat
    assert "package_chance_pct" in module_routes  # substat
    assert "recovery_amount_pct" in module_routes  # substat
    assert "max_recovery_multiplier" in module_routes  # substat
    assert "tower_orb_speed_rpm" in module_routes  # substat
    assert "tower_orb_count" in module_routes  # substat
    assert "tower_shockwave_interval_seconds" in module_routes  # substat
    assert "tower_shockwave_size_m" in module_routes  # substat
    assert "tower_thorns_damage_pct" in module_routes  # substat
    assert "cash_kill_multiplier" in module_routes  # substat
    assert "cash_per_wave" in module_routes  # substat
    assert "coins_per_wave" in module_routes  # substat
    assert "enemy_attack_level_skip_pct" in module_routes  # substat
    assert "enemy_health_level_skip_pct" in module_routes  # substat
    assert "free_attack_upgrade_chance_pct" in module_routes  # substat
    assert "free_defense_upgrade_chance_pct" in module_routes  # substat
    assert "free_utility_upgrade_chance_pct" in module_routes  # substat




def test_connection_map_module_routes_match_kb_contract(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    contract = load_yaml("kb/global-rules/contracts/contributor-mappings-full.yaml")
    module_rows = contract["source_families"]["module"]
    expected = {
        str(row["destination_id"])
        for row in module_rows
        if str(row.get("destination_object_type") or "") == "canonical_stat"
    }
    assert loaded.allowed_by_family["module"] == expected


def test_v3_kb_stat_engine_accepts_all_module_canonical_routes(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    module_stats = sorted(loaded.allowed_by_family["module"])
    engine = V3KBStatEngine(connection_map=loaded, strict=True)
    inputs = [
        StatInput(
            stat_id=stat_id,
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance=f"modules:test:{stat_id}",
            contributor_family="module",
        )
        for stat_id in module_stats
    ]
    result = engine.build(inputs)
    assert result.rows
    assert {row.stat_id for row in result.rows} == set(module_stats)
def test_v3_kb_stat_engine_accepts_module_main_unique_substat_routes(tmp_path: Path) -> None:
    loaded = load_stat_connection_map(csv_path=tmp_path / "stat_connection_map.csv", generate_if_missing=True)
    engine = V3KBStatEngine(connection_map=loaded, strict=True)
    target_stats = [
        "tower_damage",
        "wall_regen",
        "tower_attack_speed",
        "tower_regen",
        "tower_crit_multiplier",
        "tower_knockback_force",
    ]
    inputs = [
        StatInput(
            stat_id=stat_id,
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance=f"modules:test:{stat_id}",
            contributor_family="module",
        )
        for stat_id in target_stats
    ]
    result = engine.build(inputs)
    assert {row.stat_id for row in result.rows} == set(target_stats)
