import pytest

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.models import StatInput
from qe.routing import QEResolutionPlanner, resolve_bounded_bucket
from qe.stat_input_compiler import compile_stat_inputs


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

    attack_row = next(
        row
        for surface_id, row in snapshot.statbook.rows.items()
        if surface_id.endswith('enemy_attack_level_skip_pct')
    )
    health_row = next(
        row
        for surface_id, row in snapshot.statbook.rows.items()
        if surface_id.endswith('enemy_health_level_skip_pct')
    )

    attack_enhancements = [c for c in attack_row.contributors if c.get('source_class') == 'enhancement']
    health_enhancements = [c for c in health_row.contributors if c.get('source_class') == 'enhancement']
    attack_modules = [c for c in attack_row.contributors if c.get('source_class') == 'module_substat']
    health_modules = [c for c in health_row.contributors if c.get('source_class') == 'module_substat']

    assert len(attack_enhancements) == 1
    assert len(health_enhancements) == 1
    attack_primary = next(c for c in attack_modules if c.get('notes', '').endswith('_primary'))
    attack_assist = next(c for c in attack_modules if c.get('notes', '').endswith('_assist'))
    health_primary = next(c for c in health_modules if c.get('notes', '').endswith('_primary'))
    health_assist = next(c for c in health_modules if c.get('notes', '').endswith('_assist'))
    assist_scale = state.module_system_state['generator'].substat_cap
    assert assist_scale is not None
    assert attack_assist['value'] == pytest.approx(attack_primary['value'] * assist_scale)
    assert health_assist['value'] == pytest.approx(health_primary['value'] * assist_scale)
    assert attack_primary['value'] == pytest.approx(health_primary['value'])
    assert attack_assist['value'] == pytest.approx(health_assist['value'])
    assert attack_row.final_value > 0.0
    assert health_row.final_value == pytest.approx(attack_row.final_value)


def test_damage_per_meter_uses_base_one_plus_decimal_bonus_family() -> None:
    contributors = [
        StatInput(stat_name='Damage / Meter', source_family='workshop', source_name='Damage / Meter', value=59.0, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Damage / Meter Lab', source_family='lab', source_name='Damage / Meter', value=1.32, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Damage / Meter Enhancement', source_family='enhancement', source_name='Damage / Meter +', value=1.2, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Damage / Meter Relic', source_family='relic', source_name='Damage / Meter', value=0.45, value_type='resolved_value', stage='account_state'),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_damage_per_meter_multiplier',
        contributors,
        {'unit': 'multiplier', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx(1.1355112)


def test_flat_cannon_crit_substats_compile_as_flat_values_not_multiplier_displays() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )

    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='max_progression',
    )

    crit_rows = [
        row
        for row in rows
        if row.source_family == 'module_substat'
        and row.source_name == 'Amplifying Strike'
        and row.stat_name in {'Critical Factor', 'Super Crit Multi'}
    ]
    keyed = {row.stat_name: row for row in crit_rows}

    assert keyed['Critical Factor'].value == pytest.approx(15.0)
    assert keyed['Critical Factor'].destination_id == 'tower_crit_multiplier'
    assert keyed['Super Crit Multi'].value == pytest.approx(7.0)
    assert keyed['Super Crit Multi'].destination_id == 'tower_supercrit_multiplier'


def test_crit_multiplier_uses_flat_additive_base_then_post_multipliers() -> None:
    contributors = [
        StatInput(stat_name='Critical Factor', source_family='workshop', source_name='Critical Factor', value=16.2, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Critical Factor Lab', source_family='lab', source_name='Critical Factor', value=3.55, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Critical Factor +', source_family='enhancement', source_name='Critical Factor +', value=1.6, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Critical Factor Relic', source_family='relic', source_name='Critical Factor', value=0.5, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Critical Factor Module', source_family='module_substat', source_name='Amplifying Strike', value=15.0, value_type='resolved_value', stage='loadout'),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_crit_multiplier',
        contributors,
        {'unit': 'multiplier', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx((16.2 + 15.0 + 0.5) * 3.55 * 1.6)


def test_supercrit_multiplier_uses_flat_additive_base_then_post_multipliers() -> None:
    contributors = [
        StatInput(stat_name='Super Crit Multi', source_family='workshop', source_name='Super Crit Multi', value=13.2, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Super Crit Multi Lab', source_family='lab', source_name='Super Crit Multi', value=1.26, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Super Crit Multi +', source_family='enhancement', source_name='Super Crit Multi +', value=1.56, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Super Crit Multi Relic', source_family='relic', source_name='Super Crit Multi', value=0.05, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Super Crit Multi Module', source_family='module_substat', source_name='Amplifying Strike', value=5.0, value_type='resolved_value', stage='loadout'),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_supercrit_multiplier',
        contributors,
        {'unit': 'multiplier', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx((13.2 + 5.0 + 0.05) * 1.26 * 1.56)


def test_shockwave_size_uses_workshop_plus_selected_lab_slider_bonus() -> None:
    contributors = [
        StatInput(stat_name='Shockwave Size', source_family='workshop', source_name='Shockwave Size', value=2.35, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Shockwave Size', source_family='lab', source_name='Shockwave Size', value=1.0, value_type='resolved_value', stage='loadout_resolved'),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_shockwave_size_m',
        contributors,
        {'unit': 'm', 'resolver': 'generic'},
    )

    assert status == 'resolved'
    assert final == pytest.approx(3.35)


def test_shockwave_interval_uses_module_substat_seconds_delta_with_floor() -> None:
    contributors = [
        StatInput(stat_name='Shockwave Frequency', source_family='workshop', source_name='Shockwave Frequency', value=14.0, value_type='resolved_value', stage='account_state'),
        StatInput(stat_name='Shockwave Frequency', source_family='module_substat', source_name='Anti-Cube Portal', value=-4.0, value_type='resolved_value', stage='loadout_resolved'),
    ]

    final, status, *_ = resolve_bounded_bucket(
        'canonical_stat',
        'tower_shockwave_interval_seconds',
        contributors,
        {'unit': 'seconds', 'resolver': 'standard_scalar_stat'},
    )

    assert status == 'resolved'
    assert final == pytest.approx(10.0)
