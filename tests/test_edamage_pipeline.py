from __future__ import annotations

from tower_sim.engines.edamage_pipeline import (
    CardConfig,
    EDamageInputs,
    ModuleSubstatSelection,
    PerkConfig,
    compute_edamage_outputs,
    lookup_lab_multiplier,
)


def test_edamage_baseline_outputs() -> None:
    inputs = EDamageInputs(
        base_damage=10.0,
        base_crit_factor=2.0,
        attack_speed_ws_level=0.0,
        attack_speed_wsp_level=0.0,
        attack_speed_lab_level=0.0,
        crit_chance_ws_level=0.0,
        damage_lab_level=0.0,
        damage_ws_plus_multiplier=1.0,
        relic_attack_speed_bonus=0.0,
        relic_crit_chance_bonus=0.0,
        vault_attack_speed_bonus=0.0,
        vault_crit_chance_bonus=0.0,
        card_config=CardConfig(),
        perk_config=PerkConfig(picks={}, standard_perk_bonus=0.0),
        module_substats=(),
        being_annihilator_stacks=0.0,
        super_crit_chance=0.0,
        super_crit_mult=0.0,
    )
    outputs = compute_edamage_outputs(inputs)

    expected_attack_speed = 1.0
    expected_crit_chance = 0.01
    expected_crit_multiplier = 1.01
    expected_bps = ((0.01413 * expected_attack_speed**2) + (4.01278 * expected_attack_speed) + 92.8885) * 1.3
    expected_dps = 10.0 * expected_crit_multiplier * expected_bps

    assert outputs.attack_speed == expected_attack_speed
    assert outputs.crit_chance == expected_crit_chance
    assert outputs.crit_multiplier == expected_crit_multiplier
    assert outputs.bullets_per_second == expected_bps
    assert outputs.tower_dps == expected_dps


def test_edamage_with_cards_perks_and_substats() -> None:
    inputs = EDamageInputs(
        base_damage=10.0,
        base_crit_factor=2.0,
        attack_speed_ws_level=0.0,
        attack_speed_wsp_level=0.0,
        attack_speed_lab_level=0.0,
        crit_chance_ws_level=0.0,
        damage_lab_level=0.0,
        damage_ws_plus_multiplier=1.0,
        relic_attack_speed_bonus=0.0,
        relic_crit_chance_bonus=0.0,
        vault_attack_speed_bonus=0.0,
        vault_crit_chance_bonus=0.0,
        card_config=CardConfig(
            damage_level=1,
            attack_speed_level=1,
        ),
        perk_config=PerkConfig(picks={"x1.15 Damage": 1}, standard_perk_bonus=0.0),
        module_substats=(
            ModuleSubstatSelection(
                slot="Cannon",
                substat="Attack Speed",
                rarity="Common",
            ),
        ),
        being_annihilator_stacks=0.0,
        super_crit_chance=0.0,
        super_crit_mult=0.0,
    )
    outputs = compute_edamage_outputs(inputs)

    expected_attack_speed = 1.253
    expected_damage = 10.0 * 1.5 * 1.15

    assert outputs.attack_speed == expected_attack_speed
    assert outputs.tower_damage == expected_damage


def test_lookup_lab_multiplier_health() -> None:
    assert lookup_lab_multiplier("Health", 1) == 1.03
