import pytest

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.models import StatInput
from qe.routing import QEResolutionPlanner, resolve_bounded_bucket


def test_damage_bucket_applies_perk_multipliers_in_canonical_resolution() -> None:
    contributors = [
        StatInput(
            stat_name='Damage',
            source_family='workshop',
            source_name='Damage',
            value=100.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Damage Lab',
            source_family='lab',
            source_name='Damage Lab',
            value=2.0,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Damage Perk',
            source_family='perk',
            source_name='Damage Perk',
            value=1.5,
            value_type='multiplier',
            stage='perk',
        ),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_damage',
        contributors,
        {'unit': 'damage', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == 300.0


def test_force_bucket_applies_perk_multipliers_in_canonical_resolution() -> None:
    contributors = [
        StatInput(
            stat_name='Knockback Force',
            source_family='workshop',
            source_name='Knockback Force',
            value=6.08,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Knockback Module',
            source_family='module_substat',
            source_name='Knockback Module',
            value=0.9,
            value_type='resolved_value',
            stage='loadout',
        ),
        StatInput(
            stat_name='Knockback Relic',
            source_family='relic',
            source_name='Knockback Relic',
            value=0.26,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Knockback Perk',
            source_family='perk',
            source_name='Knockback Perk',
            value=0.3,
            value_type='multiplier',
            stage='perk',
        ),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_knockback_force',
        contributors,
        {'unit': 'force', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx(6.08 * 1.9 * 1.26 * 0.3)


def test_multiplier_bucket_applies_perk_multipliers_in_canonical_resolution() -> None:
    contributors = [
        StatInput(
            stat_name='Cash Bonus',
            source_family='workshop',
            source_name='Cash Bonus',
            value=2.49,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Cash Lab',
            source_family='lab',
            source_name='Cash Lab',
            value=1.66,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Cash Card',
            source_family='card',
            source_name='Cash Card',
            value=4.56,
            value_type='resolved_value',
            stage='loadout',
        ),
        StatInput(
            stat_name='Cash Enhancement',
            source_family='enhancement',
            source_name='Cash Enhancement',
            value=1.3,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Cash Relic',
            source_family='relic',
            source_name='Cash Relic',
            value=0.06,
            value_type='resolved_value',
            stage='account_state',
        ),
        StatInput(
            stat_name='Cash Perk',
            source_family='perk',
            source_name='Cash Perk',
            value=2.1875,
            value_type='multiplier',
            stage='perk',
        ),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'cash_kill_multiplier',
        contributors,
        {'unit': 'multiplier', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx(2.49 * 1.66 * 4.56 * 1.3 * 1.06 * 2.1875)


def test_enemy_skip_max_progression_uses_single_enhancement_and_correct_assist_scaling() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )

    snapshot = QEResolutionPlanner().resolve_report_snapshot(
        state,
        preset_name='Farming',
        state_mode='max_progression',
        perks_enabled=bool(state.active_perk_preset),
    )

    attack_row = snapshot.statbook.rows['state::tower.enemy_attack_level_skip_pct']
    health_row = snapshot.statbook.rows['state::tower.enemy_health_level_skip_pct']

    attack_enhancements = [c for c in attack_row.contributors if c.get('source_class') == 'enhancement']
    health_enhancements = [c for c in health_row.contributors if c.get('source_class') == 'enhancement']
    attack_modules = [c for c in attack_row.contributors if c.get('source_class') == 'module_substat']
    health_modules = [c for c in health_row.contributors if c.get('source_class') == 'module_substat']

    assert len(attack_enhancements) == 1
    assert len(health_enhancements) == 1
    assert sorted(c.get('value') for c in attack_modules) == pytest.approx([0.6, 8.0])
    assert sorted(c.get('value') for c in health_modules) == pytest.approx([0.6, 6.0])
    assert attack_row.final_value == pytest.approx(55.216)
    assert health_row.final_value == pytest.approx(52.896)
