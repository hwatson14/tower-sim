"""Evaluator/advisor smoke tests for core public imports."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_scorer_public_api_is_importable__callables_exposed():
    from evaluators.scorer import (
        compute_optimizer_scores,
        optimizer_consumption_contract_snapshot,
    )

    assert callable(compute_optimizer_scores)
    assert callable(optimizer_consumption_contract_snapshot)


def test_ranker_public_api_is_importable__list_constants_present():
    from evaluators.ranker import EDAMAGE_LABS, EECON_LABS, EHP_LABS, rank_lab_path

    assert callable(rank_lab_path)
    assert isinstance(EHP_LABS, list) and len(EHP_LABS) > 0
    assert isinstance(EDAMAGE_LABS, list)
    assert isinstance(EECON_LABS, list)


def test_upgrade_advisor_public_api_is_importable__callables_exposed():
    from advisors.upgrade_advisor import get_lab_advisory_row, load_lab_advisory_rows

    assert callable(get_lab_advisory_row)
    assert callable(load_lab_advisory_rows)


def test_scorer_contract_snapshot_is_loaded__required_surfaces_present():
    from evaluators.scorer import optimizer_consumption_contract_snapshot

    contract = optimizer_consumption_contract_snapshot()
    assert contract["missing_surface_policy"] == "fail_closed"
    assert contract["local_canonical_formula_fallback"] is False
    required = contract["required_objective_surfaces"]
    assert "derived::ehp" in required
    assert "derived::edamage" in required
    assert "derived::eecon" in required


def test_compare_builder_reuses_equivalent_qe_requests():
    from types import SimpleNamespace

    import evaluators.compare as compare
    from qe.models import StatBook, StatRow

    class FakePlanner:
        def __init__(self) -> None:
            self.calls = 0

        def resolve_report_snapshot(self, account_state, **kwargs):
            self.calls += 1
            statbook = StatBook(
                rows={
                    "state::tower.hp": StatRow(
                        stat_name="state::tower.hp",
                        final_value=123.0,
                        value_type="scalar",
                        source_count=1,
                        contributors=[],
                    )
                },
                diagnostics={},
            )
            return SimpleNamespace(statbook=statbook, stat_inputs=tuple())

    fake_state = SimpleNamespace(
        active_perk_preset="Farming",
        card_presets={"Farming": []},
        module_presets={"Farming": {}},
        modules_inventory={},
        labs={},
    )

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(compare, "build_runtime_state", lambda *args, **kwargs: fake_state)
        monkeypatch.setattr(compare, "publish_phase3_query_surfaces", lambda *args, **kwargs: None)
        monkeypatch.setattr(compare, "_annotate_display_fields", lambda *args, **kwargs: None)
        monkeypatch.setattr(compare, "_build_publishable_statbook", lambda statbook_dict, formula_ledger: {"rows": dict(statbook_dict["rows"])})
        monkeypatch.setattr(compare, "_formula_contract", lambda *args, **kwargs: {})

        planner = FakePlanner()
        _, rows_by_preset, _, _ = compare._build_compare_rows_by_preset(
            ids_raw=None,
            loadout_config={},
            perk_config={},
            formula_ledger={},
            state_mode="max_progression",
            default_preset="Farming",
            ep_oracle={"state::tower.hp": {}},
            perk_state="on",
            snapshot_planner=planner,
        )
    finally:
        monkeypatch.undo()

    assert set(rows_by_preset) == {"Farming", "Farming__perks_on"}
    assert planner.calls == 1


def test_compare_builder_normalizes_row_keys_to_active_contract():
    from types import SimpleNamespace

    import evaluators.compare as compare
    from qe.models import StatBook, StatRow

    class FakePlanner:
        def resolve_report_snapshot(self, account_state, **kwargs):
            statbook = StatBook(
                rows={
                    "canonical_stat::tower_defense_pct": StatRow(
                        stat_name="canonical_stat::tower_defense_pct",
                        final_value=98.0,
                        value_type="pct",
                        source_count=1,
                        contributors=[],
                    )
                },
                diagnostics={},
            )
            return SimpleNamespace(statbook=statbook, stat_inputs=tuple())

    fake_state = SimpleNamespace(
        active_perk_preset="Farming",
        card_presets={"Farming": []},
        module_presets={"Farming": {}},
        modules_inventory={},
        labs={},
    )

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(compare, "build_runtime_state", lambda *args, **kwargs: fake_state)
        monkeypatch.setattr(compare, "publish_phase3_query_surfaces", lambda *args, **kwargs: None)
        monkeypatch.setattr(compare, "_annotate_display_fields", lambda *args, **kwargs: None)
        monkeypatch.setattr(compare, "_build_publishable_statbook", lambda statbook_dict, formula_ledger: {"rows": dict(statbook_dict["rows"])})
        monkeypatch.setattr(compare, "_formula_contract", lambda *args, **kwargs: {})

        _, rows_by_preset, publishable_rows_by_preset, _ = compare._build_compare_rows_by_preset(
            ids_raw=None,
            loadout_config={},
            perk_config={},
            formula_ledger={},
            state_mode="max_progression",
            default_preset="Farming",
            ep_oracle={"state::tower.defense_pct": {}},
            perk_state="auto",
            snapshot_planner=FakePlanner(),
        )
    finally:
        monkeypatch.undo()

    assert "state::tower.defense_pct" in rows_by_preset["Farming"]
    assert "state::tower.defense_pct" in publishable_rows_by_preset["Farming"]
