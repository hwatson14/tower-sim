from __future__ import annotations

from collections import defaultdict
from itertools import combinations, permutations, product
from math import ceil, inf, log

from .domain import (
    BanState,
    DuplicatePolicy,
    EffectSpec,
    ModuleState,
    ModuleSlot,
    Rarity,
    RARITY_ORDER,
    RerollMechanicsConfig,
)


class ImpossibleRerollError(ValueError):
    pass


def allowed_effect_pool(
    state: ModuleState,
    locked_effect_ids: frozenset[str],
    ban_state: BanState,
    effect_specs: dict[str, EffectSpec],
    duplicate_policy: DuplicatePolicy,
) -> tuple[str, ...]:
    if ban_state.family != state.family:
        raise ValueError("ban state family must match module state family")
    pool = set(effect_specs)
    pool -= ban_state.all_banned_effect_ids
    if duplicate_policy.exclude_locked_effects_from_pool:
        pool -= locked_effect_ids
    if duplicate_policy.exclude_existing_effects_from_pool:
        # Existing locked effects are covered above when that policy is enabled; unlocked
        # current effects are excluded here so already-held effects cannot reappear in
        # newly rolled open slots under this explicit assumption.
        pool -= set(state.effect_ids())
        if not duplicate_policy.exclude_locked_effects_from_pool:
            pool |= locked_effect_ids - ban_state.all_banned_effect_ids
    ordered = tuple(sorted(effect_id for effect_id in pool if effect_id in effect_specs))
    if not ordered:
        raise ImpossibleRerollError("reroll effect pool is empty under the selected duplicate/ban policy")
    return ordered


def _effect_draws(pool: tuple[str, ...], open_count: int, policy: DuplicatePolicy) -> list[tuple[tuple[str, ...], float]]:
    if open_count == 0:
        return [((), 1.0)]
    if policy.dedupe_within_roll and open_count > len(pool):
        raise ImpossibleRerollError(
            f"cannot draw {open_count} deduped effects from pool of size {len(pool)}"
        )
    if policy.dedupe_within_roll:
        if policy.slot_draw_order == "ordered":
            draws = list(permutations(pool, open_count))
        else:
            draws = list(combinations(pool, open_count))
    else:
        draws = list(product(pool, repeat=open_count))
    probability = 1.0 / len(draws)
    return [(tuple(draw), probability) for draw in draws]


def enumerate_reroll_outcomes(
    state: ModuleState,
    locked_slot_indices: frozenset[int],
    ban_state: BanState,
    mechanics: RerollMechanicsConfig,
    effect_specs: dict[str, EffectSpec],
) -> dict[ModuleState, float]:
    if any(index < 0 or index >= len(state.slots) for index in locked_slot_indices):
        raise IndexError("locked slot index outside module state")
    if len(locked_slot_indices) == len(state.slots):
        raise ImpossibleRerollError("at least one slot must remain open for a reroll")
    locked_effect_ids = frozenset(state.slots[index].effect_id for index in locked_slot_indices)
    pool = allowed_effect_pool(state, locked_effect_ids, ban_state, effect_specs, mechanics.duplicate_policy)
    open_indices = tuple(index for index in range(len(state.slots)) if index not in locked_slot_indices)
    effect_draws = _effect_draws(pool, len(open_indices), mechanics.duplicate_policy)
    rarity_items = tuple(sorted(mechanics.rarity_probabilities.items(), key=lambda item: RARITY_ORDER[item[0]]))

    distribution: dict[ModuleState, float] = defaultdict(float)
    for effects, effect_probability in effect_draws:
        for rarity_draw in product(rarity_items, repeat=len(open_indices)):
            slots = list(state.slots)
            probability = effect_probability
            for open_index, effect_id, (rarity, rarity_probability) in zip(open_indices, effects, rarity_draw):
                slots[open_index] = ModuleSlot(effect_id=effect_id, rarity=rarity)
                probability *= rarity_probability
            next_state = ModuleState(
                family=state.family,
                slots=tuple(slots),
                module_name=state.module_name,
                is_assist=state.is_assist,
                assist_efficiency=state.assist_efficiency,
            )
            distribution[next_state] += probability
    total = sum(distribution.values())
    if abs(total - 1.0) > 1e-9:
        raise AssertionError(f"reroll distribution probability sum was {total}")
    return dict(distribution)


def acceptable_rarity_probability(
    rarity_probabilities: dict[Rarity, float],
    min_rarity: Rarity,
) -> float:
    minimum = RARITY_ORDER[min_rarity]
    return sum(probability for rarity, probability in rarity_probabilities.items() if RARITY_ORDER[rarity] >= minimum)


def expected_tail_cost_single_slot(
    pool_size: int,
    acceptable_effect_count: int,
    acceptable_rarity_probability: float,
    cost_per_roll: int,
) -> float:
    if pool_size <= 0 or acceptable_effect_count <= 0 or acceptable_rarity_probability <= 0 or cost_per_roll < 0:
        return inf
    p = acceptable_rarity_probability * acceptable_effect_count / pool_size
    return inf if p <= 0 else cost_per_roll / p


def success_probability_by_budget(p_per_roll: float, cost_per_roll: int, budget: int) -> float:
    if p_per_roll <= 0 or cost_per_roll <= 0 or budget <= 0:
        return 0.0
    if p_per_roll >= 1:
        return 1.0
    rolls = budget // cost_per_roll
    return 1 - (1 - p_per_roll) ** rolls


def budget_for_success_probability(p_per_roll: float, cost_per_roll: int, target_probability: float) -> int:
    if not 0 <= target_probability <= 1:
        raise ValueError("target_probability must be between 0 and 1")
    if target_probability == 0:
        return 0
    if p_per_roll <= 0:
        return inf  # type: ignore[return-value]
    if p_per_roll >= 1:
        return cost_per_roll
    rolls = ceil(log(1 - target_probability) / log(1 - p_per_roll))
    return rolls * cost_per_roll


def one_roll_success_probability(
    distribution: dict[ModuleState, float],
    predicate,
) -> float:
    return sum(probability for state, probability in distribution.items() if predicate(state))
