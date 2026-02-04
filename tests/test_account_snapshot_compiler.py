from __future__ import annotations

from pathlib import Path

from tower_sim.loaders.account_snapshot_compiler import (
    _parse_module_presets,
    compile_account_snapshot,
    resolve_loadout,
)
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.util.account_snapshot import PRESET_NAMES, SLOT_TYPES


def test_cards_mastery_and_presets_from_fixture() -> None:
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))

    damage_card = snapshot.cards_inventory["Damage"]
    assert damage_card.mastery_unlocked is False
    assert damage_card.mastery_lab_level == snapshot.labs.get("Damage Mastery")
    assert set(snapshot.card_presets.keys()) == set(PRESET_NAMES)


def test_modules_system_state_and_presets_from_fixture() -> None:
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))

    assert snapshot.module_system_state["Cannon"].assist_unlocked is False
    assert snapshot.module_system_state["Cannon"].assist_level == 0
    assert snapshot.module_system_state["Armor"].assist_unlocked is True
    assert snapshot.module_system_state["Armor"].assist_level == 41

    assert snapshot.module_presets["Farming"]["Cannon"].primary == "Amplifying Strike"
    assert snapshot.module_presets["Testing"]["Cannon"].primary == "Being Annihilator"
    assert set(snapshot.module_presets.keys()) == set(PRESET_NAMES)
    for preset in PRESET_NAMES:
        assert set(snapshot.module_presets[preset].keys()) == set(SLOT_TYPES)
    assert snapshot.module_presets["Preset 4"]["Cannon"].primary is None
    assert snapshot.module_presets["Preset 5"]["Cannon"].primary is None


def test_module_allocations_and_shard_budgets() -> None:
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))

    allocations = snapshot.allocation_levels
    budgets = snapshot.inferred_shard_budgets
    assert allocations["Cannon"].primary_level == 155
    assert allocations["Cannon"].assist_level == 0
    assert allocations["Armor"].primary_level == 152
    assert allocations["Armor"].assist_level == 41
    assert budgets["Cannon"] == 138588
    assert budgets["Armor"] == 128296

    resolved = resolve_loadout(snapshot, "Farming")
    assert resolved.preset_name == "Farming"
    assert resolved.allocation_levels["Generator"].primary_level == 141


def test_module_preset_parsing_handles_blank_rows() -> None:
    slot_rows = [
        ["Farming", "", "", "", ""],
        ["", "", "", "", ""],
        ["Primary Slot", "Alpha", "", "", ""],
        ["Assist Slot", "Beta", "", "", ""],
        ["Placeholder 4th preset", "", "", "", ""],
        ["", "", "", "", ""],
        ["Placeholder 5th preset", "", "", "", ""],
        ["Testing", "", "", "", ""],
        ["Primary Slot", "Gamma", "", "", ""],
        ["Tourney", "", "", "", ""],
        ["Primary Slot", "Delta", "", "", ""],
        ["Module One", "", "", "", ""],
        ["Rarity", "Level", "Stat", "", ""],
    ]

    presets = _parse_module_presets(slot_rows, "Cannon")
    assert presets["Farming"].primary == "Alpha"
    assert presets["Farming"].assist == "Beta"
    assert presets["Preset 4"].primary is None
    assert presets["Preset 5"].assist is None
    assert presets["Testing"].primary == "Gamma"
    assert presets["Tourney"].primary == "Delta"
