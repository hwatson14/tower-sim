from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from compilers.account_state_compiler import _parse_player_meta, compile_account_state
from parsers.ids_parser import parse_ids


@pytest.mark.quarantine  # hardcodes player-specific tier data (Tier 19 == 52) that does not match current ids.csv
def test_account_state_compiles_tier_progression_fields_from_ids() -> None:
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)

    assert state.tier_progression_waves["Tier 19"] == 52
    assert state.tier_progression_waves["Tier 20"] == 0
    assert state.highest_tier_unlocked_number == 19
    assert state.highest_tier_unlocked_label == "Tier 19"


def test_parse_player_meta_returns_no_highest_tier_when_all_waves_are_zero() -> None:
    rows = [
        ["Tier", "Wave", "P", "", "Stat", "Value"],
        ["Tier", "Tier 1", "0", "", "", ""],
        ["Tier", "Tier 2", "0", "", "", ""],
    ]

    player_meta, tier_progression_waves, highest_tier_unlocked_number, highest_tier_unlocked_label = _parse_player_meta(rows)

    assert player_meta == {}
    assert tier_progression_waves == {"Tier 1": 0, "Tier 2": 0}
    assert highest_tier_unlocked_number is None
    assert highest_tier_unlocked_label is None
