from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import compilers.account_state_compiler as asc


def test_bot_parser_respects_layout_contract_columns(monkeypatch):
    contract = {
        "bots": {
            "name_column": 1,
            "attribute_column": 3,
            "resolved_value_column": 4,
            "display_token_column": 5,
            "truthy_name_tokens": ["true", "false"],
        }
    }

    monkeypatch.setattr(
        asc,
        "load_section_layout_contract",
        lambda: {"uw": {"block_size": 4}, "bots": contract["bots"], "guardians": contract["bots"], "workshop": {}, "cards": {}, "modules": {}},
    )
    rows = [
        ["", "Golden Bot", "", "Bonus", "6.2", "21 | x6.2 | Cost 900 ? | Next 940 ?"],
        ["", "true", "", "Range", "50", "15 | 50m | Cost 660 ? | Maxed"],
    ]
    bots, bot_upgrades, bot_tracks = asc._parse_bots(rows)
    assert bots == ["Golden Bot"]
    assert bot_upgrades["Golden Bot"]["Bonus"] == 21
    assert bot_tracks["Golden Bot"][0].resolved_unit == "x"


def test_uw_parser_respects_layout_contract_columns(monkeypatch):
    monkeypatch.setattr(
        asc,
        "load_section_layout_contract",
        lambda: {
            "uw": {
                "name_column": 1,
                "attribute_column": 3,
                "resolved_value_column": 4,
                "display_token_column": 5,
                "block_size": 4,
                "stat_rows_per_block": 3,
                "plus_row_index": 3,
            },
            "bots": {},
            "guardians": {},
            "workshop": {},
            "cards": {},
            "modules": {},
        },
    )
    rows = [
        ["", "Golden Tower", "", "Multiplier", "17.9", "17 | x17.9"],
        ["", "", "", "Duration", "48", "33 | 48s"],
        ["", "true", "", "Cooldown", "120", "20 | 120s"],
        ["", "", "", "Coins Bonus", "2.5", "05 | x2.5"],
    ]
    _, uw_tracks, uw_plus_tracks = asc._parse_uws(rows)
    assert [track.track_name for track in uw_tracks["Golden Tower"]] == ["Multiplier", "Duration", "Cooldown"]
    assert "Golden Tower::Coins Bonus" in uw_plus_tracks
