from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.util.ids_raw import IdsRaw


_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _snapshot():
    return compile_account_snapshot(parse_ids(_FIXTURE))


def test_compiler_fixture_surface_counts_are_stable() -> None:
    snapshot = _snapshot()
    assert len(snapshot.labs) == 212
    assert len(snapshot.workshop) == 48
    assert len(snapshot.workshop_enhancements.rows) == 19
    assert len(snapshot.ultimate_weapons) == 9
    assert len(snapshot.uw_plus_tracks) == 9
    assert len(snapshot.relics) == 37
    assert len(snapshot.vault) == 67
    assert len(snapshot.bots) == 4
    assert len(snapshot.bot_upgrades) == 4
    assert len(snapshot.guardians.rows) == 17
    assert len(snapshot.player_meta) == 34
    assert len(snapshot.cards_inventory) == 31
    assert len(snapshot.module_system_state) == 4
    assert len(snapshot.module_presets) == 5
    assert len(snapshot.modules_inventory) == 32


def test_compiler_labs_and_workshop_values_are_parsed_correctly() -> None:
    snapshot = _snapshot()
    assert snapshot.labs["Game Speed"] == 7
    assert snapshot.labs["Workshop Utility Discount"] == 41
    assert snapshot.workshop["Damage"].coin_level == 5750
    assert snapshot.workshop["Damage"].end_level == 6000
    assert snapshot.workshop["Damage"].max_level == 6000
    assert snapshot.workshop["Attack Speed"].coin_level == 99
    assert snapshot.workshop["Bounce Shot Targets"].end_level == 7


def test_compiler_workshop_enhancements_table_is_preserved() -> None:
    snapshot = _snapshot()
    assert snapshot.workshop_enhancements.header == [
        "Workshop Enhancement",
        "Column 2",
        "Farming",
        "Tourney",
        "Preset 3",
        "Preset 4",
        "Preset 5",
        "7 q",
    ]
    assert snapshot.workshop_enhancements.rows[0] == ["", "", "WS+", "WS+", "WS+", "WS+", "WS+", "Max"]
    assert snapshot.workshop_enhancements.rows[1][0] == "Damage +"
    assert snapshot.workshop_enhancements.rows[-1][0] == "Enemy Level Skips +"


def test_compiler_uw_and_uw_plus_surfaces_are_parsed_correctly() -> None:
    snapshot = _snapshot()
    assert snapshot.ultimate_weapons["Chain Lightning"].track_levels == ["19", "03", "08"]
    assert snapshot.ultimate_weapons["Smart Missiles"].unlocked == "false"
    assert snapshot.ultimate_weapons["Black Hole"].track_levels == ["09", "17", "15"]
    assert snapshot.uw_plus_tracks["Black Hole::Consume"].current_state == "Locked"
    assert snapshot.uw_plus_tracks["Spotlight::Light Range"].display_token == "Lo | Locked"


def test_compiler_relics_vault_bots_and_guardians_are_preserved() -> None:
    snapshot = _snapshot()
    assert snapshot.relics["Attack Speed"] == pytest.approx(0.05)
    assert snapshot.relics["Defense %"] == pytest.approx(0.04)
    assert snapshot.vault["Keys spent"] == 0
    assert snapshot.vault["Bot Range"] == 0
    assert snapshot.bots == ["Flame Bot", "Thunder Bot", "Golden Bot", "Amplify Bot"]
    assert snapshot.bot_upgrades["Golden Bot"]["Range"] == 15
    assert snapshot.guardians.header == ["Attack", "Column 2", "Percentage", "0.01", "00 | 1% | Cost 0 ? | Next 25 ?"]
    assert snapshot.guardians.rows[-1] == ["false", "Locked", "Duration", "5", "00 | 5s | Cost 0 ? | Next 10 ?"]


def test_compiler_player_meta_cards_and_modules_are_parsed_correctly() -> None:
    snapshot = _snapshot()
    assert snapshot.player_meta["Player ID"] == "4C64DCF66976FD33"
    assert snapshot.player_meta["Farming Tier"] == "Tier 14"
    assert snapshot.player_meta["Tier 18"] == "310"
    assert snapshot.cards_inventory["Damage"].level == 7
    assert snapshot.cards_inventory["Cash"].mastery_unlocked is True
    assert snapshot.card_presets["Farming"][:5] == ["Enemy Balance", "Extra Defense", "Health", "Coins", "Plasma Cannon"]
    assert snapshot.card_presets["Tourney"][:5] == ["Attack Speed", "Damage", "Berserker", "Critical Chance", "Health"]
    assert snapshot.card_presets["Testing"] == []
    assert snapshot.module_system_state["Cannon"].assist_unlocked is False
    assert snapshot.module_system_state["Armor"].assist_level == 41
    assert snapshot.module_presets["Farming"]["Core"].assist == "Dimension Core"
    assert snapshot.modules_inventory["Amplifying Strike"].level == 164
    assert snapshot.modules_inventory["Amplifying Strike"].slot_type == "Cannon"
    assert len(snapshot.modules_inventory["Amplifying Strike"].substats) == 5


def test_compiler_fails_closed_when_uw_row3_state_label_is_corrupted() -> None:
    ids_raw = parse_ids(_FIXTURE)
    mutated = deepcopy(ids_raw.raw_sections)
    mutated["UWs"][2][1] = "bad-row-3-label"
    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match=r"expected row 3 label 'UW Unlocked' or 'UW Locked'"):
        compile_account_snapshot(bad_ids)


def test_compiler_fails_closed_when_uw_plus_track_name_is_missing() -> None:
    ids_raw = parse_ids(_FIXTURE)
    mutated = deepcopy(ids_raw.raw_sections)
    mutated["UWs"][3][2] = ""
    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match=r"missing UW\+ track name"):
        compile_account_snapshot(bad_ids)


def test_compiler_fails_closed_when_required_module_preset_slot_reference_is_missing() -> None:
    ids_raw = parse_ids(_FIXTURE)
    mutated = deepcopy(ids_raw.raw_sections)
    # Armor slot, Farming preset block, replace primary slot with a missing module name.
    mutated["Modules"][6][6] = "Goblin Armor Module"
    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match="references missing module"):
        compile_account_snapshot(bad_ids)
