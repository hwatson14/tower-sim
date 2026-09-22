from __future__ import annotations

from itertools import combinations, product

import pytest

from qe.module_reroll.domain import (
    BanState,
    DuplicatePolicy,
    EffectSpec,
    FixedTargetPolicy,
    ModuleFamily,
    ModuleSlot,
    ModuleState,
    Rarity,
    RerollMechanicsConfig,
    TargetRequirement,
)
from qe.module_reroll.mechanics import enumerate_reroll_outcomes, one_roll_success_probability
from qe.module_reroll.tail_cost import fixed_target_tail_cost, target_satisfied


def _toy_specs(n: int) -> dict[str, EffectSpec]:
    return {
        f"toy_{i}": EffectSpec(ModuleFamily.CANNON, f"toy_{i}", f"Toy {i}", {Rarity.COMMON: i, Rarity.ANCESTRAL: i + 10})
        for i in range(n)
    }


def _toy_mechanics(policy: DuplicatePolicy | None = None) -> RerollMechanicsConfig:
    return RerollMechanicsConfig(
        {Rarity.COMMON: 0.75, Rarity.RARE: 0.0, Rarity.EPIC: 0.0, Rarity.LEGENDARY: 0.0, Rarity.MYTHIC: 0.0, Rarity.ANCESTRAL: 0.25},
        {0: 2, 1: 5, 2: 11},
        policy or DuplicatePolicy(),
    )


def _brute_distribution(state: ModuleState, locked: frozenset[int], mechanics: RerollMechanicsConfig, effects: dict[str, EffectSpec]):
    open_indices = [i for i in range(len(state.slots)) if i not in locked]
    locked_effects = {state.slots[i].effect_id for i in locked}
    pool = sorted(set(effects) - set(state.effect_ids()))
    if not mechanics.duplicate_policy.exclude_existing_effects_from_pool:
        pool = sorted(set(effects) - (locked_effects if mechanics.duplicate_policy.exclude_locked_effects_from_pool else set()))
    if mechanics.duplicate_policy.dedupe_within_roll:
        effect_draws = list(combinations(pool, len(open_indices)))
    else:
        effect_draws = list(product(pool, repeat=len(open_indices)))
    out = {}
    rarity_items = list(mechanics.rarity_probabilities.items())
    for draw in effect_draws:
        for rarities in product(rarity_items, repeat=len(open_indices)):
            slots = list(state.slots)
            p = 1 / len(effect_draws)
            for idx, effect_id, (rarity, rp) in zip(open_indices, draw, rarities):
                slots[idx] = ModuleSlot(effect_id, rarity)
                p *= rp
            ns = ModuleState(state.family, tuple(slots))
            out[ns] = out.get(ns, 0.0) + p
    return out


def test_toy_transition_enumeration_matches_exhaustive_bruteforce() -> None:
    effects = _toy_specs(5)
    mechanics = _toy_mechanics()
    state = ModuleState(ModuleFamily.CANNON, (ModuleSlot("toy_0", Rarity.COMMON), ModuleSlot("toy_1", Rarity.COMMON), ModuleSlot("toy_2", Rarity.COMMON)))
    engine = enumerate_reroll_outcomes(state, frozenset({0}), BanState(ModuleFamily.CANNON), mechanics, effects)
    brute = _brute_distribution(state, frozenset({0}), mechanics, effects)
    assert engine == pytest.approx(brute)


def test_toy_fixed_target_one_effect_expected_cost_matches_bruteforce_tail() -> None:
    effects = _toy_specs(3)
    mechanics = _toy_mechanics()
    state = ModuleState(ModuleFamily.CANNON, (ModuleSlot("toy_0", Rarity.COMMON), ModuleSlot("toy_1", Rarity.COMMON)))
    target = FixedTargetPolicy((TargetRequirement("toy_2", Rarity.ANCESTRAL),), preserved_effect_ids=frozenset({"toy_0"}))
    result = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CANNON), mechanics, effects, allowed_lock_counts=(1,))
    distribution = _brute_distribution(state, frozenset({0}), mechanics, effects)
    p = one_roll_success_probability(distribution, lambda s: target_satisfied(s, target))
    assert result.possible
    assert result.expected_shards == pytest.approx(mechanics.lock_costs[1] / p)


def test_toy_fixed_target_two_effects_and_ban_impossible() -> None:
    effects = _toy_specs(4)
    mechanics = _toy_mechanics()
    state = ModuleState(ModuleFamily.CANNON, (ModuleSlot("toy_0", Rarity.COMMON), ModuleSlot("toy_1", Rarity.COMMON)))
    target = FixedTargetPolicy((TargetRequirement("toy_2", Rarity.ANCESTRAL), TargetRequirement("toy_3", Rarity.ANCESTRAL)))
    possible = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CANNON), mechanics, effects, allowed_lock_counts=(0,))
    impossible = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CANNON, frozenset({"toy_3"})), mechanics, effects, allowed_lock_counts=(0,))
    assert possible.possible
    assert impossible.possible is False


def test_target_already_satisfied_zero_cost() -> None:
    effects = _toy_specs(3)
    mechanics = _toy_mechanics()
    state = ModuleState(ModuleFamily.CANNON, (ModuleSlot("toy_2", Rarity.ANCESTRAL), ModuleSlot("toy_1", Rarity.COMMON)))
    target = FixedTargetPolicy((TargetRequirement("toy_2", Rarity.ANCESTRAL),))
    result = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CANNON), mechanics, effects)
    assert result.target_satisfied
    assert result.expected_shards == 0
