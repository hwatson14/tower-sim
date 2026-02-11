from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.engines.survivability_pipeline import (
    _parse_module_blocks,
    build_survivability_report,
    compile_survivability_loadout_stat_inputs,
)
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def test_survivability_pipeline_snapshots() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )

    snapshots = report["snapshots"]
    assert "base_only" in snapshots
    assert "start_of_run" in snapshots
    assert "at_wave" in snapshots
    assert "wave_state" in snapshots["at_wave"]
    assert "orb_damage_mult" in snapshots["at_wave"]["applied_bc"]

    verdict = report["survivability_verdict"]
    assert isinstance(verdict["ttk_seconds"], float)
    assert isinstance(verdict["ttd_seconds"], float)


def test_module_override_changes_armor_effects() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))
    armor_block = _parse_module_blocks(ids_snapshot)["Armor"]
    modules = list(armor_block.inventory.values())
    primary = modules[0]
    alternate = next(
        module for module in modules if module.main_effect != primary.main_effect
    )

    base_report = build_survivability_report(
        ids_snapshot,
        spec,
        module_context="Testing",
        module_overrides={"Armor": {"primary": primary.name}},
        allow_provisional=True,
    )
    alt_report = build_survivability_report(
        ids_snapshot,
        spec,
        module_context="Testing",
        module_overrides={"Armor": {"primary": alternate.name}},
        allow_provisional=True,
    )
    assert (
        base_report["snapshots"]["start_of_run"]["tower_hp"]
        != alt_report["snapshots"]["start_of_run"]["tower_hp"]
    )


def test_base_only_matches_effective_paths_fixture() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )
    base_only = report["snapshots"]["base_only"]
    assert base_only["tower_hp"] == pytest.approx(11314998536.23848, rel=1e-9)
    assert base_only["tower_regen"] == pytest.approx(30919400339.730965, rel=1e-9)
    assert base_only["def_pct"] == pytest.approx(0.551, rel=1e-9)
    assert base_only["wall_hp"] == pytest.approx(28740096282.04574, rel=1e-9)
    assert base_only["wall_regen"] == pytest.approx(64930740713.43503, rel=1e-9)


def test_thorns_and_plasma_cannon_inputs() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )
    base_only = report["snapshots"]["base_only"]
    assert base_only["thorns_damage_mult"] == pytest.approx(0.0701415, rel=1e-9)

    plasma_report = build_survivability_report(
        ids_snapshot,
        spec,
        module_context="Testing",
        selected_cards=["Plasma Cannon"],
        allow_provisional=True,
    )
    start_snapshot = plasma_report["snapshots"]["start_of_run"]
    assert start_snapshot["plasma_cannon_damage_mult"] == pytest.approx(
        0.54, rel=1e-9
    )


def test_enemy_level_skip_uses_lab_plus_workshop_plus_enhancement_multiplier() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )
    base_only = report["snapshots"]["base_only"]

    assert base_only["eals_pct"] == pytest.approx(0.21275, rel=1e-9)
    assert base_only["ehls_pct"] == pytest.approx(0.207, rel=1e-9)


def test_damage_attack_speed_and_crit_chance_cards_feed_loadout_stat_inputs() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )

    baseline = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon"],
        allow_provisional=True,
    )
    with_damage_cards = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon", "Damage", "Attack Speed", "Critical Chance"],
        allow_provisional=True,
    )

    baseline_by_stat = {item.stat_id: item for item in baseline}
    with_damage_by_stat = {item.stat_id: item for item in with_damage_cards}

    assert "tower_damage" not in baseline_by_stat
    assert "tower_attack_speed" not in baseline_by_stat
    assert "tower_crit_chance" not in baseline_by_stat

    assert with_damage_by_stat["tower_damage"].enhancement_multiplier is not None
    assert with_damage_by_stat["tower_damage"].enhancement_multiplier > 1.0
    assert with_damage_by_stat["tower_attack_speed"].enhancement_multiplier is not None
    assert with_damage_by_stat["tower_attack_speed"].enhancement_multiplier > 1.0
    assert with_damage_by_stat["tower_crit_chance"].loadout_delta is not None
    assert with_damage_by_stat["tower_crit_chance"].loadout_delta > 0.0


def test_utility_cards_feed_loadout_stat_inputs() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )

    baseline = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon"],
        allow_provisional=True,
    )
    with_utility_cards = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=[
            "Plasma Cannon",
            "Recovery Package Chance",
            "Range",
            "Cash",
            "Coins",
            "Free Upgrades",
        ],
        allow_provisional=True,
    )

    baseline_by_stat = {item.stat_id: item for item in baseline}
    with_utility_by_stat = {item.stat_id: item for item in with_utility_cards}

    assert "workshop_package_chance" not in baseline_by_stat
    assert "workshop_range_meters" not in baseline_by_stat
    assert "workshop_cash_bonus" not in baseline_by_stat
    assert "workshop_coins_per_kill_bonus" not in baseline_by_stat
    assert "workshop_free_upgrades" not in baseline_by_stat

    assert with_utility_by_stat["workshop_package_chance"].loadout_delta is not None
    assert with_utility_by_stat["workshop_package_chance"].loadout_delta > 0.0

    assert with_utility_by_stat["workshop_range_meters"].enhancement_multiplier is not None
    assert with_utility_by_stat["workshop_range_meters"].enhancement_multiplier > 1.0

    assert with_utility_by_stat["workshop_cash_bonus"].enhancement_multiplier is not None
    assert with_utility_by_stat["workshop_cash_bonus"].enhancement_multiplier > 1.0

    assert (
        with_utility_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier
        is not None
    )
    assert (
        with_utility_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier
        > 1.0
    )

    assert with_utility_by_stat["workshop_free_upgrades"].enhancement_multiplier is not None
    assert with_utility_by_stat["workshop_free_upgrades"].enhancement_multiplier > 1.0
