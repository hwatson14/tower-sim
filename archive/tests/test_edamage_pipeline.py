from __future__ import annotations

from tower_sim.engines.edamage_pipeline import EDamageInputError, EDamageInputs, compute_edamage_outputs, inputs_from_canonical_values


def test_edamage_baseline_outputs() -> None:
    inputs = EDamageInputs(
        tower_damage=10.0,
        tower_attack_speed=1.0,
        tower_crit_chance=0.0,
        tower_crit_factor=2.0,
        being_annihilator_stacks=0.0,
        super_crit_chance=0.0,
        super_crit_mult=0.0,
    )
    outputs = compute_edamage_outputs(inputs)

    expected_attack_speed = 1.0
    expected_crit_chance = 0.0
    expected_crit_multiplier = 1.0
    expected_bps = ((0.01413 * expected_attack_speed**2) + (4.01278 * expected_attack_speed) + 92.8885) * 1.3
    expected_dps = 10.0 * expected_crit_multiplier * expected_bps

    assert outputs.attack_speed == expected_attack_speed
    assert outputs.crit_chance == expected_crit_chance
    assert outputs.crit_multiplier == expected_crit_multiplier
    assert outputs.bullets_per_second == expected_bps
    assert outputs.tower_dps == expected_dps


def test_edamage_with_cards_perks_and_substats() -> None:
    inputs = EDamageInputs(
        tower_damage=17.25,
        tower_attack_speed=0.9774597775301548,
        tower_crit_chance=0.0,
        tower_crit_factor=2.0,
        being_annihilator_stacks=0.0,
        super_crit_chance=0.0,
        super_crit_mult=0.0,
    )
    outputs = compute_edamage_outputs(inputs)

    expected_attack_speed = 0.9774597775301548
    expected_damage = 17.25

    assert outputs.attack_speed == expected_attack_speed
    assert outputs.tower_damage == expected_damage

def test_inputs_from_canonical_values_missing_stat_errors() -> None:
    try:
        inputs_from_canonical_values({"tower_damage": 10.0})
    except EDamageInputError as exc:
        assert "Missing canonical edamage stat values" in str(exc)
    else:
        raise AssertionError("Expected missing canonical stat error")
