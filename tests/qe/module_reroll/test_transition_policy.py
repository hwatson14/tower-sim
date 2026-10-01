from __future__ import annotations

from pathlib import Path

import pytest

from qe.module_reroll.domain import (
    BanState,
    DuplicatePolicy,
    EffectSpec,
    ModuleFamily,
    ModuleSlot,
    ModuleState,
    Rarity,
    RerollMechanicsConfig,
)
from qe.module_reroll.kb_loader import load_effect_specs, load_lock_costs, load_rarity_probabilities
from qe.module_reroll.mechanics import ImpossibleRerollError, allowed_effect_pool, enumerate_reroll_outcomes

ROOT = Path(__file__).resolve().parents[3]


def _real_state(open_slots: int) -> tuple[ModuleState, dict[str, EffectSpec], RerollMechanicsConfig]:
    effects = load_effect_specs(ROOT)[ModuleFamily.CANNON]
    slots = tuple(ModuleSlot(effect_id, Rarity.COMMON) for effect_id in list(effects)[: open_slots + 1])
    return ModuleState(ModuleFamily.CANNON, slots), effects, RerollMechanicsConfig(load_rarity_probabilities(ROOT), load_lock_costs(ROOT))


@pytest.mark.parametrize("open_slots", [1, 2, 3])
def test_distribution_probabilities_sum_for_open_slot_counts(open_slots: int) -> None:
    state, effects, mechanics = _real_state(open_slots)
    locked = frozenset({0})
    distribution = enumerate_reroll_outcomes(state, locked, BanState(ModuleFamily.CANNON), mechanics, effects)
    assert sum(distribution.values()) == pytest.approx(1.0)


def test_bans_and_locked_effects_are_removed_from_pool() -> None:
    state, effects, mechanics = _real_state(1)
    locked_effect = state.slots[0].effect_id
    banned = next(effect_id for effect_id in effects if effect_id not in state.effect_ids())
    pool = allowed_effect_pool(state, frozenset({locked_effect}), BanState(ModuleFamily.CANNON, frozenset({banned})), effects, mechanics.duplicate_policy)
    assert locked_effect not in pool
    assert banned not in pool


def test_existing_effects_excluded_when_configured() -> None:
    state, effects, _mechanics = _real_state(1)
    pool = allowed_effect_pool(state, frozenset(), BanState(ModuleFamily.CANNON), effects, DuplicatePolicy(exclude_existing_effects_from_pool=True))
    assert not set(state.effect_ids()) & set(pool)


def test_within_roll_duplicates_impossible_when_deduped() -> None:
    state, effects, mechanics = _real_state(2)
    distribution = enumerate_reroll_outcomes(state, frozenset({0}), BanState(ModuleFamily.CANNON), mechanics, effects)
    for next_state in distribution:
        open_effects = [slot.effect_id for slot in next_state.slots[1:]]
        assert len(open_effects) == len(set(open_effects))


def test_duplicate_states_possible_only_when_policy_permits() -> None:
    state, effects, mechanics = _real_state(2)
    permissive = RerollMechanicsConfig(
        mechanics.rarity_probabilities,
        mechanics.lock_costs,
        DuplicatePolicy(exclude_existing_effects_from_pool=False, exclude_locked_effects_from_pool=False, dedupe_within_roll=False),
    )
    distribution = enumerate_reroll_outcomes(state, frozenset({0}), BanState(ModuleFamily.CANNON), permissive, effects)
    assert any(next_state.slots[1].effect_id == next_state.slots[2].effect_id for next_state in distribution)


def test_impossible_pools_raise_clear_error() -> None:
    state, effects, mechanics = _real_state(1)
    with pytest.raises(ImpossibleRerollError, match="empty"):
        allowed_effect_pool(state, frozenset(), BanState(ModuleFamily.CANNON, frozenset(effects)), effects, mechanics.duplicate_policy)
