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
