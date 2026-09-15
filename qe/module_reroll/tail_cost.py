from __future__ import annotations

from math import inf

from .domain import (
    BanState,
    EffectSpec,
    ExpectedCostResult,
    FixedTargetPolicy,
    ModuleState,
    RARITY_ORDER,
    RerollMechanicsConfig,
)
from .mechanics import ImpossibleRerollError, enumerate_reroll_outcomes, one_roll_success_probability


def target_satisfied(state: ModuleState, target: FixedTargetPolicy) -> bool:
    by_effect = {slot.effect_id: slot.rarity for slot in state.slots}
    for effect_id in target.preserved_effect_ids:
        if effect_id not in by_effect:
            return False
    for requirement in target.requirements:
        rarity = by_effect.get(requirement.effect_id)
        if rarity is None or RARITY_ORDER[rarity] < RARITY_ORDER[requirement.min_rarity]:
            return False
    return True


def fixed_target_tail_cost(
    initial_state: ModuleState,
    target_policy: FixedTargetPolicy,
    ban_state: BanState,
    mechanics: RerollMechanicsConfig,
    effect_specs: dict[str, EffectSpec],
    allowed_lock_counts: tuple[int, ...] | None = None,
) -> ExpectedCostResult:
    """Solve a fixed-target geometric tail under a single repeated best action.

    Tranche 1 deliberately keeps this standalone and narrow: it compares legal first
    lock sets, computes the exact one-roll probability that the fixed target is
    satisfied after that action, and returns cost / p for repeating that action.
    Dynamic multi-stage locking is a later certification concern.
    """
    assumptions = {
        "solver": "single_action_geometric_fixed_target_v1",
        "certification_status": "experimental_uncertified",
        "duplicate_policy": mechanics.duplicate_policy.as_dict(),
    }
    if target_satisfied(initial_state, target_policy):
        return ExpectedCostResult(True, True, 0.0, 0.0, None, 1.0, assumptions)

    allowed = set(allowed_lock_counts or tuple(mechanics.lock_costs))
    best: tuple[float, float, frozenset[int], int] | None = None
    warnings: list[str] = []
    for mask in range(1 << len(initial_state.slots)):
        locked = frozenset(i for i in range(len(initial_state.slots)) if mask & (1 << i))
        if len(locked) not in allowed or len(locked) not in mechanics.lock_costs:
            continue
        if len(locked) == len(initial_state.slots):
            continue
        locked_effects = {initial_state.slots[i].effect_id for i in locked}
        if not target_policy.preserved_effect_ids <= locked_effects:
            continue
        try:
            distribution = enumerate_reroll_outcomes(initial_state, locked, ban_state, mechanics, effect_specs)
        except ImpossibleRerollError as exc:
            warnings.append(str(exc))
            continue
        p = one_roll_success_probability(distribution, lambda state: target_satisfied(state, target_policy))
        if p <= 0:
            continue
        cost = mechanics.lock_costs[len(locked)]
        ev = cost / p
        if best is None or ev < best[0]:
            best = (ev, p, locked, cost)

    if best is None:
        return ExpectedCostResult(
            False,
            False,
            inf,
            None,
            None,
            0.0,
            assumptions,
            tuple(warnings) or ("target cannot be reached under the selected policy/action set",),
        )
    ev, p, locked, cost = best
    return ExpectedCostResult(False, True, ev, ev / cost, locked, p, assumptions, tuple(warnings))
