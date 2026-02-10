from __future__ import annotations

import pytest

from tower_sim.loaders.ep_export_loader import load_ep_export_dataset, parse_human_number


def test_parse_human_number_supported_formats() -> None:
    assert parse_human_number("3.34 O") == pytest.approx(3.34e27)
    assert parse_human_number("651.02 B") == pytest.approx(651.02e9)
    assert parse_human_number("85.37 q") == pytest.approx(85.37e15)
    assert parse_human_number("x35.66") == pytest.approx(35.66)
    assert parse_human_number("0.7799999999999999") == pytest.approx(0.7799999999999999)


def test_ep_export_loader_parses_value_column_with_presets_and_sources() -> None:
    dataset = load_ep_export_dataset()

    assert dataset.verification_presets == {
        "edmg": "tournament",
        "ehp": "farming",
        "eecon": "farming",
    }
    assert len(dataset.rows) == 31

    for row in dataset.rows:
        assert row.preset == dataset.verification_presets[row.suite]
        assert isinstance(row.value_numeric, float)
        assert row.source_ref
        assert row.verification_path


def test_ep_export_loader_has_definitive_formula_sources_for_current_rows() -> None:
    dataset = load_ep_export_dataset()

    assert dataset.rows_without_definitive_formulas == ()
    assert len(dataset.rows) == 31


def test_ep_export_loader_uses_sheet_formula_sources_for_aggregate_rows() -> None:
    dataset = load_ep_export_dataset()
    by_key = {(row.suite, row.key): row for row in dataset.rows}

    assert by_key[("ehp", "ehp")].source_ref == "ep_sheet:eHP!CG5"
    assert by_key[("eecon", "cpk_average")].source_ref == "ep_sheet:eEcon!AO26"
