"""
tests/live/test_evaluators_core.py -- Evaluator and advisor core correctness gate.

Verifies: evaluators/ and advisors/ layers are importable and expose expected public API.
Gate: fails if evaluator/advisor core path is broken.

Implemented in T7 (after T5A evaluator/advisor extraction is confirmed complete).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_evaluators_scorer_is_importable():
    from evaluators.scorer import (
        MissingGovernedSurfaceError,
        compute_ehp,
        compute_edamage,
        compute_eecon,
        compute_optimizer_scores,
        optimizer_consumption_contract_snapshot,
    )
    assert callable(compute_optimizer_scores)
    assert callable(optimizer_consumption_contract_snapshot)


def test_evaluators_ranker_is_importable():
    from evaluators.ranker import rank_lab_path, EHP_LABS, EDAMAGE_LABS, EECON_LABS
    assert callable(rank_lab_path)
    assert isinstance(EHP_LABS, list) and len(EHP_LABS) > 0


def test_advisors_upgrade_advisor_is_importable():
    from advisors.upgrade_advisor import (
        LabAdvisoryRow,
        get_lab_advisory_row,
        load_lab_advisory_rows,
    )
    assert callable(get_lab_advisory_row)
    assert callable(load_lab_advisory_rows)


def test_evaluators_scorer_consumption_contract_is_sane():
    from evaluators.scorer import optimizer_consumption_contract_snapshot
    contract = optimizer_consumption_contract_snapshot()
    assert contract["missing_surface_policy"] == "fail_closed"
    assert contract["local_canonical_formula_fallback"] is False
    required = contract["required_objective_surfaces"]
    assert "derived::ehp" in required
    assert "derived::edamage" in required
    assert "derived::eecon" in required
