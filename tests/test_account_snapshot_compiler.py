from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

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
    assert snapshot.module_system_state["Armor"].assist_level == 63

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
    assert allocations["Cannon"].primary_level == 157
    assert allocations["Cannon"].assist_level == 0
    assert allocations["Armor"].primary_level == 154
    assert allocations["Armor"].assist_level == 63
    assert budgets["Cannon"] == 146588
    assert budgets["Armor"] == 139926

    resolved = resolve_loadout(snapshot, "Farming")
    assert resolved.preset_name == "Farming"
    assert resolved.allocation_levels["Generator"].primary_level == 150


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


def test_bot_upgrades_are_typed_levels() -> None:
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    assert snapshot.bot_upgrades["Flame Bot"]["Damage R."] == 8
    assert snapshot.bot_upgrades["Golden Bot"]["Bonus"] == 18
    assert snapshot.bot_upgrades["Amplify Bot"]["Bonus"] == 0


def test_compile_account_snapshot_fails_closed_on_unmapped_workshop_name() -> None:
    ids_raw = parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    mutated = deepcopy(ids_raw.raw_sections)
    replaced = False
    for row in mutated["WS"]:
        if row and row[0].strip() == "Health":
            row[0] = "Health_UNKNOWN_ALIAS"
            replaced = True
            break
    assert replaced

    from tower_sim.util.ids_raw import IdsRaw

    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match="Naming contract violations in IDS snapshot"):
        compile_account_snapshot(bad_ids)


def test_compile_account_snapshot_uses_selected_workshop_preset_levels() -> None:
    ids_raw = parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    mutated = deepcopy(ids_raw.raw_sections)
    updated = False
    for row in mutated["WS"]:
        if row and row[0].strip() == "Damage":
            row[1] = "111"
            row[2] = "112"
            row[3] = "211"
            row[4] = "212"
            row[11] = "999"
            updated = True
            break
    assert updated

    from tower_sim.util.ids_raw import IdsRaw

    modified = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    farming = compile_account_snapshot(modified, default_preset="Farming")
    assert farming.workshop["Damage"].coin_level == 111
    assert farming.workshop["Damage"].end_level == 112
    assert farming.workshop["Damage"].max_level == 999

    tourney = compile_account_snapshot(modified, default_preset="Tourney")
    assert tourney.workshop["Damage"].coin_level == 211
    assert tourney.workshop["Damage"].end_level == 212
    assert tourney.workshop["Damage"].max_level == 999


def test_relic_values_preserve_fractional_bonuses() -> None:
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    assert snapshot.relics["Attack Speed"] == pytest.approx(0.05, rel=1e-12)
    assert snapshot.relics["Defense %"] == pytest.approx(0.04, rel=1e-12)
    assert snapshot.relics["Thorns"] == pytest.approx(0.09, rel=1e-12)
