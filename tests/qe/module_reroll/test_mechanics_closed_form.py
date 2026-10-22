from __future__ import annotations

from pathlib import Path

import pytest

from qe.module_reroll.domain import BanState, ModuleFamily, ModuleSlot, ModuleState, Rarity, RerollMechanicsConfig
from qe.module_reroll.kb_loader import load_effect_specs, load_lock_costs, load_rarity_probabilities
from qe.module_reroll.mechanics import (
    acceptable_rarity_probability,
    allowed_effect_pool,
    enumerate_reroll_outcomes,
    expected_tail_cost_single_slot,
    one_roll_success_probability,
)

ROOT = Path(__file__).resolve().parents[3]


def _mechanics() -> RerollMechanicsConfig:
    return RerollMechanicsConfig(load_rarity_probabilities(ROOT), load_lock_costs(ROOT))


def test_five_lock_one_target_ancestral_tail_anchor() -> None:
    assert expected_tail_cost_single_slot(12, 1, 0.003, 1600) == pytest.approx(6_400_000)


def test_five_lock_two_target_ancestral_tail_anchor() -> None:
    assert expected_tail_cost_single_slot(12, 2, 0.003, 1600) == pytest.approx(3_200_000)


def test_core_four_bans_five_locks_two_target_mythic_plus_anchor() -> None:
    expected = 1600 / (0.013 * 2 / 17)
    assert expected_tail_cost_single_slot(17, 2, 0.013, 1600) == pytest.approx(expected)


def test_ban_sensitivity_on_one_slot_tails() -> None:
    no_bans = expected_tail_cost_single_slot(12, 1, 0.003, 1600)
    with_bans = expected_tail_cost_single_slot(8, 1, 0.003, 1600)
    assert with_bans < no_bans


def test_core_four_bans_four_locks_two_open_exact_probability_under_no_duplicate_policy() -> None:
    effects = load_effect_specs(ROOT)[ModuleFamily.CORE]
    mechanics = _mechanics()
    state = ModuleState(
        ModuleFamily.CORE,
        tuple(ModuleSlot(effect_id, Rarity.ANCESTRAL) for effect_id in list(effects)[:6]),
    )
    bans = BanState(ModuleFamily.CORE, frozenset(list(effects)[6:10]))
    distribution = enumerate_reroll_outcomes(state, frozenset(range(4)), bans, mechanics, effects)
    targets = set(list(effects)[10:12])
    mythic_plus = acceptable_rarity_probability(mechanics.rarity_probabilities, Rarity.MYTHIC)
    p = one_roll_success_probability(
        distribution,
        lambda s: any(slot.effect_id in targets and slot.rarity in {Rarity.MYTHIC, Rarity.ANCESTRAL} for slot in s.slots[4:]),
    )
    # Pool: 26 total - 4 bans - 6 current = 16 under the default existing-effect exclusion.
    total_combinations = (16 * 15) / 2
    failure_probability = ((14 * 13) / 2) / total_combinations
    failure_probability += (2 * 14) / total_combinations * (1 - mythic_plus)
    failure_probability += 1 / total_combinations * (1 - mythic_plus) ** 2
    assert p == pytest.approx(1 - failure_probability)
