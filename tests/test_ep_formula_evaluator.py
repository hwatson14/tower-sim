from __future__ import annotations

import math

import pytest

from tower_sim.evaluators.ep_formula_evaluator import (
    FormulaEvalError,
    UnknownParameterError,
    evaluate_lambda,
)


def test_eph_max_rcvr_formula() -> None:
    result = evaluate_lambda(
        "EPH_MAX_RCVR",
        {
            "ws_val": 100.0,
            "lab_lvl": 10.0,
            "stone_sac": 2.0,
            "lab_sac": 3.0,
            "prim_sub": 5.0,
            "ass_sub": 10.0,
            "wse_lvl": 20.0,
            "vault_pct": 0.15,
        },
    )
    assert math.isclose(result, 145.866, rel_tol=1e-6)


def test_eph_wall_regen_formula() -> None:
    result = evaluate_lambda(
        "EPH_WALL_REGEN",
        {
            "lab_lvl": 5.0,
            "prim_effect": 0.0,
            "ass_effect": 0.0,
        },
    )
    assert math.isclose(result, 0.5, rel_tol=1e-6)


def test_unknown_identifier_errors() -> None:
    with pytest.raises(UnknownParameterError):
        evaluate_lambda("EPH_WALL_REGEN", {"lab_lvl": 1.0, "prim_effect": 1.0})


def test_eval_lambda_case_insensitive_identifier_resolution() -> None:
    result = evaluate_lambda(
        "EPD_CRITICAL",
        {
            "cc": 0.2,
            "cf": 4.0,
            "scc": 0.1,
            "scm": 8.0,
            "being_annihilator": 0.0,
        },
    )
    assert result > 1.0
