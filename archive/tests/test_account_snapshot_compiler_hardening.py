from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.util.ids_raw import IdsRaw


_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def test_fixture_uws_compile_into_expected_names_and_unlock_flags() -> None:
    snapshot = compile_account_snapshot(parse_ids(_FIXTURE))

    assert set(snapshot.ultimate_weapons.keys()) == {
        "Chain Lightning",
        "Smart Missiles",
        "Death Wave",
        "Chrono Field",
        "Inner Land Mines",
        "Golden Tower",
        "Poison Swamp",
        "Black Hole",
        "Spotlight",
    }
    assert snapshot.ultimate_weapons["Chain Lightning"].unlocked == "true"
    assert snapshot.ultimate_weapons["Smart Missiles"].unlocked == "false"
    assert snapshot.ultimate_weapons["Black Hole"].track_levels == ["09", "17", "15"]


def test_fixture_player_and_stuff_right_hand_columns_are_preserved() -> None:
    snapshot = compile_account_snapshot(parse_ids(_FIXTURE))

    assert snapshot.player_meta["Player ID"] == "4C64DCF66976FD33"
    assert snapshot.player_meta["Farming Tier"] == "Tier 14"
    assert snapshot.player_meta["Tourney League"] == "Legends"
    assert snapshot.player_meta["Lifetime Coins"] == "3570000000000"
    assert snapshot.player_meta["Stones"] == "200"
    assert snapshot.player_meta["Gems"] == "326"


def test_compiler_fails_closed_when_uw_block_length_is_not_multiple_of_four() -> None:
    ids_raw = parse_ids(_FIXTURE)
    mutated = deepcopy(ids_raw.raw_sections)
    mutated["UWs"] = mutated["UWs"][:-1]
    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match="Malformed UWs section: expected 4-row blocks"):
        compile_account_snapshot(bad_ids)


def test_compiler_fails_closed_when_uw_plus_marker_is_corrupted() -> None:
    ids_raw = parse_ids(_FIXTURE)
    mutated = deepcopy(ids_raw.raw_sections)
    mutated["UWs"][3][0] = "not-uw-plus"
    bad_ids = IdsRaw(ids_path=ids_raw.ids_path, header=ids_raw.header, raw_sections=mutated)

    with pytest.raises(ValueError, match=r"expected row 4 marker 'UW\+'"):
        compile_account_snapshot(bad_ids)
