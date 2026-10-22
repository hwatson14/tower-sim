from __future__ import annotations

from pathlib import Path
from math import isinf

from qe.module_reroll.domain import BanState, FixedTargetPolicy, ModuleFamily, ModuleSlot, ModuleState, Rarity, RerollMechanicsConfig, TargetRequirement
from qe.module_reroll.kb_loader import load_effect_specs, load_lock_costs, load_rarity_probabilities
from qe.module_reroll.tail_cost import fixed_target_tail_cost

ROOT = Path(__file__).resolve().parents[3]


def test_real_cannon_one_slot_fixed_target_is_finite() -> None:
    effects = load_effect_specs(ROOT)[ModuleFamily.CANNON]
    mechanics = RerollMechanicsConfig(load_rarity_probabilities(ROOT), load_lock_costs(ROOT))
    state = ModuleState(ModuleFamily.CANNON, tuple(ModuleSlot(effect_id, Rarity.ANCESTRAL) for effect_id in list(effects)[:6]))
    target_effect = next(effect_id for effect_id in effects if effect_id not in state.effect_ids())
    target = FixedTargetPolicy((TargetRequirement(target_effect, Rarity.ANCESTRAL),), preserved_effect_ids=frozenset(state.effect_ids()[:5]))
    result = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CANNON), mechanics, effects, allowed_lock_counts=(5,))
    assert result.possible
    assert result.expected_shards > 0
    assert result.best_locked_slot_indices == frozenset(range(5))


def test_real_impossible_target_handling() -> None:
    effects = load_effect_specs(ROOT)[ModuleFamily.CORE]
    mechanics = RerollMechanicsConfig(load_rarity_probabilities(ROOT), load_lock_costs(ROOT))
    state = ModuleState(ModuleFamily.CORE, tuple(ModuleSlot(effect_id, Rarity.COMMON) for effect_id in list(effects)[:2]))
    target = FixedTargetPolicy((TargetRequirement("not_a_core_effect", Rarity.ANCESTRAL),))
    result = fixed_target_tail_cost(state, target, BanState(ModuleFamily.CORE), mechanics, effects)
    assert not result.possible
    assert isinf(result.expected_shards)
