"""
Optimizer scenario runner.

Supports:
- conditional mode: evaluate objective under a single battle-condition set_id
- robust mode: evaluate expected objective over a scenario set with weights

This module does not implement the full optimizer search; it provides evaluation wrappers
so the optimizer can be context-correct (tournament BC variability, perks disabled, etc).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Callable, Tuple


@dataclass(frozen=True)
class Scenario:
    set_id: str
    weight: float


def validate_weights(scenarios: List[Scenario], tol: float = 1e-9) -> None:
    if not scenarios:
        raise ValueError("scenario list empty")
    s = sum(sc.weight for sc in scenarios)
    if abs(s - 1.0) > tol:
        raise ValueError(f"scenario weights must sum to 1.0 (got {s})")
    for sc in scenarios:
        if sc.weight < 0:
            raise ValueError("scenario weight negative")


def run_conditional(
    evaluate_fn: Callable[[Dict[str, Any]], float],
    base_context: Dict[str, Any],
    battle_conditions_set_id: str,
) -> float:
    ctx = dict(base_context)
    ctx["battle_conditions"] = dict(ctx.get("battle_conditions", {}))
    ctx["battle_conditions"]["set_id"] = battle_conditions_set_id
    return float(evaluate_fn(ctx))


def run_robust_expected(
    evaluate_fn: Callable[[Dict[str, Any]], float],
    base_context: Dict[str, Any],
    scenarios: List[Scenario],
) -> float:
    validate_weights(scenarios)
    exp = 0.0
    for sc in scenarios:
        v = run_conditional(evaluate_fn, base_context, sc.set_id)
        exp += sc.weight * v
    return float(exp)
