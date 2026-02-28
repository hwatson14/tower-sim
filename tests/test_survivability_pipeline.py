from __future__ import annotations

from pathlib import Path

import pytest
import pandas as pd

from tower_sim.engines.survivability_pipeline import (
    _StatAccumulator,
    _apply_unique_effects,
    _parse_module_blocks,
    ModuleRecord,
    build_survivability_report,
    compile_survivability_loadout_stat_inputs,
)
from tower_sim.libs.modules_library import Rarity, UNIQUE_EFFECTS
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.registry.naming_contract import resolve_named_entity


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

    baseline_damage_mult = (
        baseline_by_stat["tower_damage"].enhancement_multiplier
        if "tower_damage" in baseline_by_stat
        and baseline_by_stat["tower_damage"].enhancement_multiplier is not None
        else 1.0
    )
    baseline_attack_speed_mult = (
        baseline_by_stat["tower_attack_speed"].enhancement_multiplier
        if "tower_attack_speed" in baseline_by_stat
        and baseline_by_stat["tower_attack_speed"].enhancement_multiplier is not None
        else 1.0
    )
    baseline_crit_delta = (
        baseline_by_stat["tower_crit_chance"].loadout_delta
        if "tower_crit_chance" in baseline_by_stat
        and baseline_by_stat["tower_crit_chance"].loadout_delta is not None
        else 0.0
    )

    assert with_damage_by_stat["tower_damage"].enhancement_multiplier is not None
    assert with_damage_by_stat["tower_damage"].enhancement_multiplier > baseline_damage_mult
    assert with_damage_by_stat["tower_attack_speed"].enhancement_multiplier is not None
    assert (
        with_damage_by_stat["tower_attack_speed"].enhancement_multiplier
        > baseline_attack_speed_mult
    )
    assert with_damage_by_stat["tower_crit_chance"].loadout_delta is not None
    assert with_damage_by_stat["tower_crit_chance"].loadout_delta > baseline_crit_delta


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

    baseline_package_delta = (
        baseline_by_stat["workshop_package_chance"].loadout_delta
        if "workshop_package_chance" in baseline_by_stat
        and baseline_by_stat["workshop_package_chance"].loadout_delta is not None
        else 0.0
    )
    baseline_range_mult = (
        baseline_by_stat["workshop_range_meters"].enhancement_multiplier
        if "workshop_range_meters" in baseline_by_stat
        and baseline_by_stat["workshop_range_meters"].enhancement_multiplier is not None
        else 1.0
    )
    baseline_cash_mult = (
        baseline_by_stat["workshop_cash_bonus"].enhancement_multiplier
        if "workshop_cash_bonus" in baseline_by_stat
        and baseline_by_stat["workshop_cash_bonus"].enhancement_multiplier is not None
        else 1.0
    )
    baseline_coin_mult = (
        baseline_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier
        if "workshop_coins_per_kill_bonus" in baseline_by_stat
        and baseline_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier is not None
        else 1.0
    )
    baseline_free_upgrades_mult = (
        baseline_by_stat["workshop_free_upgrades"].enhancement_multiplier
        if "workshop_free_upgrades" in baseline_by_stat
        and baseline_by_stat["workshop_free_upgrades"].enhancement_multiplier is not None
        else 1.0
    )

    assert with_utility_by_stat["workshop_package_chance"].loadout_delta is not None
    assert with_utility_by_stat["workshop_package_chance"].loadout_delta > baseline_package_delta

    assert with_utility_by_stat["workshop_range_meters"].enhancement_multiplier is not None
    assert with_utility_by_stat["workshop_range_meters"].enhancement_multiplier > baseline_range_mult

    assert with_utility_by_stat["workshop_cash_bonus"].enhancement_multiplier is not None
    assert with_utility_by_stat["workshop_cash_bonus"].enhancement_multiplier > baseline_cash_mult

    assert (
        with_utility_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier
        is not None
    )
    assert (
        with_utility_by_stat["workshop_coins_per_kill_bonus"].enhancement_multiplier
        > baseline_coin_mult
    )

    assert with_utility_by_stat["workshop_free_upgrades"].enhancement_multiplier is not None
    assert (
        with_utility_by_stat["workshop_free_upgrades"].enhancement_multiplier
        > baseline_free_upgrades_mult
    )


def test_fortress_card_feeds_defense_absolute_loadout_stat_input() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )

    baseline = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon"],
        allow_provisional=True,
    )
    with_fortress = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Testing",
        selected_cards=["Plasma Cannon", "Fortress"],
        allow_provisional=True,
    )

    baseline_by_stat = {item.stat_id: item for item in baseline}
    with_fortress_by_stat = {item.stat_id: item for item in with_fortress}

    baseline_def_abs_mult = (
        baseline_by_stat["defense_absolute"].enhancement_multiplier
        if "defense_absolute" in baseline_by_stat
        and baseline_by_stat["defense_absolute"].enhancement_multiplier is not None
        else 1.0
    )

    assert with_fortress_by_stat["defense_absolute"].enhancement_multiplier is not None
    assert with_fortress_by_stat["defense_absolute"].enhancement_multiplier > baseline_def_abs_mult


def test_tourney_card_set_with_unmodeled_cards_is_deterministic_noop_not_error() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )

    compiled = compile_survivability_loadout_stat_inputs(
        ids_snapshot,
        module_context="Tourney",
        allow_provisional=True,
    )

    assert compiled


def test_all_cached_cards_are_explicitly_classified_for_survivability_pipeline() -> None:
    from tower_sim.engines import survivability_pipeline as pipeline

    cache_dir = Path("tables/cache/wiki")
    frames = [
        pd.read_csv(cache_dir / "cards_common.csv"),
        pd.read_csv(cache_dir / "cards_rare.csv"),
        pd.read_csv(cache_dir / "cards_epic.csv"),
    ]
    names = sorted(set(pd.concat(frames, ignore_index=True)["Name"].astype(str)))

    mapped_canonicals = {
        "CARD_ATTACK_SPEED",
        "CARD_BERSERKER",
        "CARD_CASH",
        "CARD_COINS",
        "CARD_CRITICAL_CHANCE",
        "CARD_DAMAGE",
        "CARD_EXTRA_DEFENSE",
        "CARD_FORTRESS",
        "CARD_FREE_UPGRADES",
        "CARD_HEALTH",
        "CARD_HEALTH_REGEN",
        "CARD_PLASMA_CANNON",
        "CARD_RANGE",
        "CARD_RECOVERY_PACKAGE_CHANCE",
        "CARD_ULTIMATE_CRIT",
    }
    classified = mapped_canonicals | set(pipeline._CARD_NOOP_CANONICALS)

    unresolved: list[str] = []
    unclassified: list[str] = []
    for name in names:
        lookup = "Plasma Cannon" if name == "Plasma Canon" else name
        try:
            canonical = resolve_named_entity("cards", lookup)
        except KeyError:
            unresolved.append(name)
            continue
        if canonical not in classified:
            unclassified.append(f"{name}:{canonical}")

    assert unresolved == []
    assert unclassified == []


def test_berserker_and_ultimate_crit_cards_feed_tower_damage() -> None:
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
        selected_cards=["Plasma Cannon", "Berserker", "Ultimate Crit"],
        allow_provisional=True,
    )

    baseline_by_stat = {item.stat_id: item for item in baseline}
    with_damage_by_stat = {item.stat_id: item for item in with_damage_cards}

    baseline_mult = (
        baseline_by_stat["tower_damage"].enhancement_multiplier
        if "tower_damage" in baseline_by_stat
        and baseline_by_stat["tower_damage"].enhancement_multiplier is not None
        else 1.0
    )
    boosted = with_damage_by_stat["tower_damage"].enhancement_multiplier
    assert boosted is not None
    assert boosted > baseline_mult * 8.0


def test_all_module_unique_effects_are_wired_into_unique_layer() -> None:
    assert len(UNIQUE_EFFECTS) == 24

    for module_name, effect in UNIQUE_EFFECTS.items():
        module = ModuleRecord(
            name=module_name,
            slot=effect.slot,
            rarity=Rarity.ANCESTRAL,
            level=1,
            main_effect=1.0,
            substats=[],
        )
        accumulator = _StatAccumulator()
        applied = _apply_unique_effects(
            accumulator,
            module,
            is_assist=False,
            assist_cap=None,
            slot=effect.slot,
            placement="primary",
        )
        assert applied is True
        ledger = accumulator.module_contribution_ledger()

        if effect.effect_name == "wall_health_regen_mult_x":
            by_target = {row["target"]: row for row in ledger}
            assert set(by_target.keys()) == {"wall_hp", "wall_regen"}
            assert by_target["wall_hp"]["kind"] == "multiplier"
            assert by_target["wall_regen"]["kind"] == "multiplier"
            assert by_target["wall_hp"]["value"] == pytest.approx(effect.value[Rarity.ANCESTRAL])
            assert by_target["wall_regen"]["value"] == pytest.approx(effect.value[Rarity.ANCESTRAL])
        elif effect.effect_name == "bot_range_bonus_m":
            assert len(ledger) == 1
            row = ledger[0]
            assert row["layer"] == "unique"
            assert row["kind"] == "delta"
            assert row["target"] == "bot_range"
            assert row["value"] == pytest.approx(effect.value[Rarity.ANCESTRAL])
        else:
            assert len(ledger) == 1
            row = ledger[0]
            assert row["layer"] == "unique"
            assert row["kind"] == "behavior_binding"
            assert row["target"] == f"uw_behavior:{effect.effect_name}"
            assert row["value"] == pytest.approx(effect.value[Rarity.ANCESTRAL])


def test_assist_unique_effects_obey_rarity_cap_when_wired() -> None:
    module = ModuleRecord(
        name="Galaxy Compressor",
        slot="Generator",
        rarity=Rarity.ANCESTRAL,
        level=1,
        main_effect=1.0,
        substats=[],
    )
    accumulator = _StatAccumulator()

    applied = _apply_unique_effects(
        accumulator,
        module,
        is_assist=True,
        assist_cap=Rarity.EPIC,
        slot="Generator",
        placement="assist",
    )

    assert applied is True
    ledger = accumulator.module_contribution_ledger()
    assert len(ledger) == 1
    row = ledger[0]
    assert row["target"] == "uw_behavior:uw_cooldown_reduction_per_package_s"
    assert row["value"] == pytest.approx(UNIQUE_EFFECTS["Galaxy Compressor"].value[Rarity.EPIC])
