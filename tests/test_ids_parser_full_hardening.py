from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tower_sim.loaders.ids_parser import SECTION_SPECS, parse_ids


_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")
_EXPECTED_SECTION_COUNTS = {
    "Labs": 212,
    "WS": 50,
    "WS+": 20,
    "UWs": 36,
    "Cards": 31,
    "Relics": 37,
    "Vault": 67,
    "Bots": 16,
    "Themes & Songs": 1,
    "Modules": 80,
    "Guardians": 18,
    "Player & Stuff": 22,
}


def _fixture_rows() -> list[list[str]]:
    with _FIXTURE.open(newline="") as handle:
        return list(csv.reader(handle))


def test_fixture_header_matches_declared_section_specs() -> None:
    rows = _fixture_rows()
    header = rows[0]
    for spec in SECTION_SPECS:
        assert header[spec.header_col] == spec.name


def test_fixture_section_counts_are_stable() -> None:
    ids_raw = parse_ids(_FIXTURE)
    assert {name: len(rows) for name, rows in ids_raw.raw_sections.items()} == _EXPECTED_SECTION_COUNTS


def test_fixture_sections_preserve_expected_first_rows() -> None:
    ids_raw = parse_ids(_FIXTURE)
    assert ids_raw.raw_sections["Labs"][0] == ["Game Speed", "7", "7", "7"]
    assert ids_raw.raw_sections["WS"][0][0] == "Workshop Upgrade"
    assert ids_raw.raw_sections["WS+"][0][0] == "Workshop Enhancement"
    assert ids_raw.raw_sections["UWs"][0][0] == "Chain Lightning"
    assert ids_raw.raw_sections["Cards"][0][0] == "Damage"
    assert ids_raw.raw_sections["Relics"][0][0] == "Relics"
    assert ids_raw.raw_sections["Vault"][0][0] == "Keys spent"
    assert ids_raw.raw_sections["Bots"][0][0] == "Flame Bot"
    assert ids_raw.raw_sections["Themes & Songs"][0] == ["1.666", ""]
    assert ids_raw.raw_sections["Modules"][0][:5] == ["Assist Slot", "false", "0", "", ""]
    assert ids_raw.raw_sections["Guardians"][0][:5] == ["Attack", "", "Percentage", "0.01", "00 | 1% | Cost 0 ? | Next 25 ?"]
    assert ids_raw.raw_sections["Player & Stuff"][0] == ["Tier", "Wave", "P", "", "Stat", "Value"]


def test_parse_ids_rejects_unknown_header_in_header_row(tmp_path: Path) -> None:
    rows = _fixture_rows()
    rows[0][60] = "Goblin Section"
    path = tmp_path / "bad_ids.csv"
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(ValueError, match="Unknown section header"):
        parse_ids(path)


def test_parse_ids_rejects_missing_required_section_header(tmp_path: Path) -> None:
    rows = _fixture_rows()
    rows[0][25] = "Not UWs"
    path = tmp_path / "bad_ids.csv"
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(ValueError, match="expected 'UWs' at column 25"):
        parse_ids(path)


def test_parse_ids_pads_short_rows_without_losing_sections(tmp_path: Path) -> None:
    rows = _fixture_rows()
    rows[3] = rows[3][:10]
    path = tmp_path / "short_rows.csv"
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    ids_raw = parse_ids(path)
    assert ids_raw.raw_sections["Labs"][2] == ["Workshop Attack Discount", "27", "", "99"]
    assert ids_raw.raw_sections["WS"][2][:6] == ["Damage", "5750", "6000", "5750", "6000", ""]


def test_parse_ids_keeps_allowed_cards_metadata_columns() -> None:
    ids_raw = parse_ids(_FIXTURE)
    assert ids_raw.header[35] == "16"
    assert ids_raw.header[34] == "v2.2.3"
    assert ids_raw.header[33] == "Cards Presets"
