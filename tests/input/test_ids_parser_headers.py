from __future__ import annotations

import pytest

from pathlib import Path

from input.ids_parser import SECTION_SPECS, _fail_unknown_sections, parse_ids
from input.runtime_state import build_runtime_state


ROOT = Path(__file__).resolve().parents[2]


def _base_rows() -> list[list[str]]:
    width = max(spec.header_col for spec in SECTION_SPECS) + 1
    header = [""] * width
    for spec in SECTION_SPECS:
        header[spec.header_col] = spec.name
    values = [""] * width
    return [header, values]


def test_fail_unknown_sections__accepts_valid_version_token_header() -> None:
    rows = _base_rows()
    rows[0][43] = "v1.2.3"
    _fail_unknown_sections(rows)


def test_fail_unknown_sections__rejects_non_version_v_prefixed_header() -> None:
    rows = _base_rows()
    rows[0][43] = "vNext-release"
    rows[1][43] = "payload"

    with pytest.raises(ValueError, match=r"'vNext-release' at column 43"):
        _fail_unknown_sections(rows)


def test_fail_unknown_sections__reports_unknown_header_and_column_context() -> None:
    rows = _base_rows()
    rows[0][43] = "Mystery Header"
    rows[1][43] = "payload"

    with pytest.raises(ValueError, match=r"'Mystery Header' at column 43\. First row value: 'payload'"):
        _fail_unknown_sections(rows)


def test_fail_unknown_sections__accepts_v28_ref_placeholders_inside_known_header_width() -> None:
    rows = _base_rows()
    rows[0].extend([""] * 4)
    rows[1].extend([""] * 4)
    rows[0][2] = "#REF!"
    rows[0][80] = "#REF!"
    _fail_unknown_sections(rows)


def test_fail_unknown_sections__accepts_v28_ref_placeholders_in_shifted_trailing_columns() -> None:
    rows = _base_rows()
    rows[0].extend([""] * 9)
    rows[1].extend([""] * 9)
    rows[0][85] = "#REF!"

    _fail_unknown_sections(rows)


def test_fail_unknown_sections__accepts_named_module_preset_headers() -> None:
    rows = _base_rows()
    modules_col = next(spec.header_col for spec in SECTION_SPECS if spec.name == "Modules")
    rows[0][modules_col + 3] = "Farming"
    rows[0][modules_col + 4] = "Tourney"
    rows[0][modules_col + 5] = "Testing"
    rows[0][modules_col + 6] = "Preset 4"
    rows[0][modules_col + 7] = "Preset 5"

    _fail_unknown_sections(rows)


def test_fail_unknown_sections__accepts_trailing_perks_preset_helper_header() -> None:
    rows = _base_rows()
    rows[0].extend([""] * 24)
    rows[1].extend([""] * 24)
    rows[0][96] = "Perks Preset"
    rows[1][96] = "Farming"

    _fail_unknown_sections(rows)


def test_parse_ids_accepts_current_v28_import_shifted_header_layout() -> None:
    parsed = parse_ids(ROOT / "input" / "imports" / "ids.csv")

    assert parsed.raw_sections["Labs"]
    assert parsed.raw_sections["WS"]
    assert parsed.raw_sections["Cards"]
    assert parsed.raw_sections["Player & Stuff"]


def test_runtime_state_parses_v28_dissonant_pbs_from_player_stuff() -> None:
    parsed = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = build_runtime_state(parsed)

    assert "Tier 1" in state.dissonance_pbs_by_tier
    assert set(state.dissonance_pbs_by_tier["Tier 1"]) == {"attack", "defense", "utility", "ultimate_weapons"}
    assert state.dissonance_pbs_by_tier["Tier 1"]["attack"] == 5000
    assert state.dissonance_pbs_by_tier["Tier 14"] == {
        "attack": 5000,
        "defense": 5000,
        "utility": 3915,
        "ultimate_weapons": 4310,
    }
    assert state.tier_progression_waves["Tier 1"] == 10210
    assert state.tier_progression_waves["Tier 19"] == 303
    assert state.highest_tier_unlocked_number == 20
    assert state.highest_tier_unlocked_label == "Tier 20"
    assert "Utility" not in state.player_meta
    assert "0" not in state.player_meta
