from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import pytest

from input.state_types import PerkSelection, ScenarioProjectionState, UltimateWeaponSnapshot
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from evaluators.compare import _build_kb_incomplete_areas
from qe import models as qe_models
from qe.stat_input_compiler import compile_stat_inputs
import qe.stat_input_compiler as stat_input_compiler
from qe.routing import QEResolutionPlanner
from simulators.progression import resolve_progression_consumer_bundle


@lru_cache(maxsize=1)
def _base_account_state():
    bundle = load_inputs()
    return build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )


def _compiled_rows(state):
    return compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )


def _resolved_snapshot(state):
    planner = QEResolutionPlanner()
    return planner.resolve_report_snapshot(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
        perks_enabled=bool(state.active_perk_preset),
    )


def _compiled_rows_with_projection(state, projection: ScenarioProjectionState):
    return compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
        scenario_projection_state=projection,
        perks_enabled=True,
    )


def _single_row(rows, name: str):
    matched = [row for row in rows if row.stat_name == name]
    assert matched, f'missing compiled row for {name!r}'
    assert len(matched) == 1, f'expected one compiled row for {name!r}, got {len(matched)}'
    return matched[0]


def _single_row_by_family(rows, *, name: str, source_family: str):
    matched = [row for row in rows if row.stat_name == name and row.source_family == source_family]
    assert matched, f'missing compiled row for {name!r} in source family {source_family!r}'
    assert len(matched) == 1, f'expected one compiled row for {name!r} in {source_family!r}, got {len(matched)}'
    return matched[0]


def _rows_by_name(rows, name: str):
    matched = [row for row in rows if row.stat_name == name]
    assert matched, f'missing compiled rows for {name!r}'
    return matched


def test_parser_drop_rows_are_omitted() -> None:
    state = _base_account_state()
    mutated = replace(state, labs={**state.labs, 'END OF ARRAY': 1})

    rows = _compiled_rows(mutated)

    assert all(row.stat_name != 'END OF ARRAY' for row in rows)


def test_account_metadata_rows_route_to_metadata_lane() -> None:
    row = _single_row(_compiled_rows(_base_account_state()), 'Keys spent')

    assert row.destination_object_type == 'meta_progression_param'
    assert row.destination_id == 'account_meta.keys_spent'
    assert row.notes == 'account_metadata_routed:Keys spent'


def test_capability_policy_rows_route_to_capability_lane() -> None:
    row = _single_row(_compiled_rows(_base_account_state()), 'Auto Pick Perks')

    assert row.destination_object_type == 'capability'
    assert row.destination_id == 'capability.perks.auto_pick'
    assert row.notes == 'capability_policy_routed:Auto Pick Perks'


def test_governed_numeric_rows_route_without_old_bucket() -> None:
    rows = _compiled_rows(_base_account_state())

    common_drop = _single_row(rows, 'Common Drop Chance')
    basic_ultimate = _single_row(rows, "Basic's Ultimate")
    assist_bonus = _single_row(rows, 'Assist Module Bonus - Armor')
    starting_cash = _single_row(rows, 'Starting Cash')

    assert common_drop.destination_object_type == 'meta_progression_param'
    assert common_drop.destination_id == 'module.lab.common_drop_chance_bonus_pct'
    assert 'non_calculator_scope' not in (common_drop.notes or '')

    assert basic_ultimate.destination_object_type == 'environment_param'
    assert basic_ultimate.destination_id == 'enemy.basic.ultimate_enabled'
    assert basic_ultimate.notes == "governed_numeric_routed:Basic's Ultimate"

    assert assist_bonus.destination_object_type == 'mechanic_param'
    assert assist_bonus.destination_id == 'module.armor.assist_lab_bonus_pct'
    assert 'non_calculator_scope' not in (assist_bonus.notes or '')
    assert assist_bonus.value_type == 'resolved_value'
    assert starting_cash.destination_object_type == 'meta_progression_param'
    assert starting_cash.destination_id == 'economy.starting_cash_bonus'
    assert starting_cash.value_type == 'resolved_value'
    assert 'pending' not in (starting_cash.notes or '')


def test_active_farming_module_uniques_compile_to_unique_effect_values() -> None:
    rows = _compiled_rows(_base_account_state())

    orbital = _single_row_by_family(rows, name='Orbital Augment::unique', source_family='module')
    black_hole = _single_row_by_family(rows, name='Black Hole Digestor::unique', source_family='module')
    primordial = _single_row_by_family(rows, name='Primordial Collapse::unique', source_family='module')

    assert orbital.destination_object_type == 'mechanic_param'
    assert orbital.destination_id == 'module.orbital_augment.electron_count'
    assert orbital.value == 2.0
    assert orbital.value_type == 'count'

    assert black_hole.destination_object_type == 'mechanic_param'
    assert black_hole.destination_id == 'module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'
    assert black_hole.value == 0.30000000000000004
    assert black_hole.value_type == 'pct'

    assert primordial.destination_object_type == 'mechanic_param'
    assert primordial.destination_id == 'module.primordial_collapse.bh_damage_reduction_pct'
    assert primordial.value == 80.0
    assert primordial.value_type == 'pct'


def test_progression_family_publishes_active_module_unique_state_surfaces() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct',
            'state::module.orbital_augment.electron_count',
            'state::module.primordial_collapse.bh_damage_reduction_pct',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='test_module_unique_state_surface_publication',
    )

    black_hole = statbook.rows['state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct']
    orbital = statbook.rows['state::module.orbital_augment.electron_count']
    primordial = statbook.rows['state::module.primordial_collapse.bh_damage_reduction_pct']

    assert black_hole.status == 'resolved'
    assert black_hole.final_value == 0.30000000000000004
    assert black_hole.contributors[0]['source_class'] == 'module_unique'

    assert orbital.status == 'resolved'
    assert orbital.final_value == 2.0
    assert orbital.contributors[0]['source_class'] == 'module_unique'

    assert primordial.status == 'resolved'
    assert primordial.final_value == 80.0
    assert primordial.contributors[0]['source_class'] == 'module_unique'


def test_optimizer_module_effects_bundle_resolves_optional_module_surfaces_when_explicitly_requested() -> None:
    response = resolve_progression_consumer_bundle(
        account_state=_base_account_state(),
        consumer_id='optimizer_analysis',
        bundle_id='optimizer_module_effects',
        family_id='progression_start_of_run',
        preset_name='Farming',
        perks_enabled=False,
        include_optional_surface_ids=(
            'state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct',
            'state::module.orbital_augment.electron_count',
        ),
        state_mode='start_of_run',
        trace_mode='contributors',
    )

    rows = {row.surface_id: row for row in response.resolved_surface_rows}
    assert rows['state::module.primordial_collapse.bh_damage_reduction_pct'].final_value == pytest.approx(80.0)
    assert rows['state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'].final_value == pytest.approx(0.30000000000000004)
    assert rows['state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'].status == 'resolved'
    assert rows['state::module.orbital_augment.electron_count'].final_value == pytest.approx(2.0)
    assert rows['state::module.orbital_augment.electron_count'].status == 'resolved'



def test_intro_sprint_is_mapped() -> None:
    state = _base_account_state()
    assert 'Intro Sprint' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Intro Sprint']},
    )

    row = _single_row(_compiled_rows(mutated), 'Intro Sprint')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.intro_sprint.waves'
    assert row.notes == 'kb_card_effect_registry_routed:INTRO_SPRINT'


def test_enemy_balance_card_splits_to_spawn_and_cash_routes() -> None:
    state = _base_account_state()
    assert 'Enemy Balance' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Enemy Balance']},
    )

    rows = _rows_by_name(_compiled_rows(mutated), 'Enemy Balance')

    assert {(row.destination_object_type, row.destination_id) for row in rows} == {
        ('environment_param', 'bc.more_enemies_pct'),
        ('canonical_stat', 'cash_kill_multiplier'),
    }
    assert {row.notes for row in rows} == {'kb_card_effect_registry_split_routed:ENEMY_BALANCE'}


def test_range_card_routes_through_effect_registry_not_name_fallback() -> None:
    state = _base_account_state()
    assert 'Range' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Range']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Range', source_family='card')

    assert row.destination_object_type == 'canonical_stat'
    assert row.destination_id == 'tower_range_m'
    assert row.notes == 'kb_card_effect_registry_routed:RANGE'


def test_fortress_card_routes_through_effect_registry_not_alias_fallback() -> None:
    state = _base_account_state()
    assert 'Fortress' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Fortress']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Fortress', source_family='card')

    assert row.destination_object_type == 'canonical_stat'
    assert row.destination_id == 'tower_defense_absolute'
    assert row.notes == 'kb_card_effect_registry_routed:FORTRESS'


def test_recovery_package_chance_card_routes_through_effect_registry_not_name_fallback() -> None:
    state = _base_account_state()
    assert 'Recovery Package Chance' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Recovery Package Chance']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Recovery Package Chance', source_family='card')

    assert row.destination_object_type == 'canonical_stat'
    assert row.destination_id == 'package_chance_pct'
    assert row.notes == 'kb_card_effect_registry_routed:RECOVERY_PACKAGE_CHANCE'


def test_wave_accelerator_card_routes_through_effect_registry_not_name_fallback() -> None:
    state = _base_account_state()
    assert 'Wave Accelerator' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Wave Accelerator']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Wave Accelerator', source_family='card')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.wave_accelerator.spawn_rate_acceleration'
    assert row.notes == 'kb_card_effect_registry_routed:WAVE_ACCELERATOR'


def test_slow_aura_card_routes_to_base_card_enemy_speed_semantics() -> None:
    state = _base_account_state()
    assert 'Slow Aura' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Slow Aura']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Slow Aura', source_family='card')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.slow_aura.enemy_speed_pct'
    assert row.notes == 'kb_card_effect_registry_routed:SLOW_AURA'


def test_land_mine_stun_card_routes_to_duration_not_mastery_miss_attack_semantics() -> None:
    state = _base_account_state()
    assert 'Land Mine Stun' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Land Mine Stun']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Land Mine Stun', source_family='card')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.land_mine_stun.duration_seconds'
    assert row.notes == 'kb_card_effect_registry_routed:LAND_MINE_STUN'


def test_death_ray_card_splits_enable_and_duration_rows() -> None:
    state = _base_account_state()
    assert 'Death Ray' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Death Ray']},
    )

    rows = _rows_by_name(_compiled_rows(mutated), 'Death Ray')

    assert {(row.destination_object_type, row.destination_id) for row in rows} == {
        ('capability', 'capability.death_ray.enabled'),
        ('runtime_mechanic_param', 'cards.death_ray.duration_seconds'),
    }


def test_super_tower_card_splits_active_and_bonus_rows() -> None:
    state = _base_account_state()
    assert 'Super Tower' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Super Tower']},
    )

    rows = _rows_by_name(_compiled_rows(mutated), 'Super Tower')

    assert {(row.destination_object_type, row.destination_id) for row in rows} == {
        ('runtime_mechanic_param', 'cards.super_tower.active'),
        ('runtime_mechanic_param', 'cards.super_tower.bonus_multiplier'),
    }


def test_second_wind_and_energy_shield_split_enable_and_value_rows() -> None:
    state = _base_account_state()

    for card_name, expected in (
        ('Second Wind', {('capability', 'capability.second_wind.enabled'), ('runtime_mechanic_param', 'cards.second_wind.shield_duration_seconds')}),
        ('Energy Shield', {('capability', 'capability.energy_shield.enabled'), ('runtime_mechanic_param', 'cards.energy_shield.recharge_cooldown_seconds')}),
    ):
        assert card_name in state.cards_inventory
        mutated = replace(
            state,
            card_presets={**state.card_presets, state.default_preset: [card_name]},
        )
        rows = _rows_by_name(_compiled_rows(mutated), card_name)
        assert {(row.destination_object_type, row.destination_id) for row in rows} == expected


def test_berserker_card_routes_to_runtime_owned_base_semantics_when_projection_enabled() -> None:
    state = _base_account_state()
    assert 'Berserker' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Berserker']},
    )

    rows = _compiled_rows_with_projection(
        mutated,
        ScenarioProjectionState(berserker_damage_bonus=True),
    )
    row = _single_row_by_family(rows, name='Berserker', source_family='card')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.berserker.absorbed_damage_pct'
    assert row.notes == 'kb_card_effect_registry_routed:BERSERKER'


def test_berserker_card_routes_in_normal_audited_compile_path_without_falling_through() -> None:
    state = _base_account_state()
    assert 'Berserker' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Berserker']},
    )

    row = _single_row_by_family(_compiled_rows(mutated), name='Berserker', source_family='card')

    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'cards.berserker.absorbed_damage_pct'
    assert row.notes == 'kb_card_effect_registry_routed:BERSERKER'


def test_discount_labs_route_to_qe_owned_meta_surfaces_and_workshop_enhancements_routes_to_capability() -> None:
    rows = _compiled_rows(_base_account_state())
    expected_resolved = {
        'Workshop Attack Discount': ('meta_progression_param', 'workshop_attack_cost_reduction_pct', 13.5),
        'Workshop Defense Discount': ('meta_progression_param', 'workshop_defense_cost_reduction_pct', 14.0),
        'Workshop Utility Discount': ('meta_progression_param', 'workshop_utility_cost_reduction_pct', 20.5),
        'Labs Coin Discount': ('meta_progression_param', 'lab_coin_cost_reduction_pct', 20.4),
    }

    for lab_name, expected in expected_resolved.items():
        object_type, destination_id, value = expected
        row = _single_row(rows, lab_name)
        assert row.destination_object_type == object_type
        assert row.destination_id == destination_id
        assert row.value_type == 'resolved_value'
        assert row.value == value
        assert row.notes == f'governed_numeric_routed:{lab_name}'

    workshop_enhancements = _single_row(rows, 'Workshop Enhancements')
    assert workshop_enhancements.destination_object_type == 'capability'
    assert workshop_enhancements.destination_id == 'capability.workshop.enhancements_unlock'
    assert workshop_enhancements.value_type == 'bool'
    assert workshop_enhancements.value is True
    assert workshop_enhancements.notes == 'capability_policy_routed:Workshop Enhancements'


def test_materialized_lab_values_replace_level_pending_for_sanctioned_formula_labs() -> None:
    rows = _compiled_rows(_base_account_state())

    expected_resolved = {
        'Orbs Speed': ('mechanic_param', 'lab.orb_speed_bonus', 2.0),
        'Land Mine Decay': ('mechanic_param', 'lab.land_mine_decay_seconds', 6.5),
        'Shockwave Size': ('mechanic_param', 'lab.shockwave_size_bonus', 1.0),
        'Orb Boss Hit': ('runtime_mechanic_param', 'combat.orb_boss_hit_pct', 2.0),
        'Second Wind Blast': ('mechanic_param', 'lab.second_wind_blast_pct', 100.0),
        'Recharge Second Wind': ('mechanic_param', 'lab.recharge_second_wind_waves', 400.0),
        'Recharge Demon Mode': ('mechanic_param', 'lab.recharge_demon_mode_waves', 750.0),
        'Recharge Nuke': ('mechanic_param', 'lab.recharge_nuke_waves', 1250.0),
        'Energy Shield Extra Hit': ('mechanic_param', 'energy_shield_charge_count', 2.0),
    }

    for lab_name, expected in expected_resolved.items():
        object_type, destination_id, value = expected
        row = _single_row_by_family(rows, name=lab_name, source_family='lab')
        assert row.destination_object_type == object_type
        assert row.destination_id == destination_id
        assert row.value_type == 'resolved_value'
        assert row.value == value
        assert row.notes == f'kb_lab_value_table_resolved:{lab_name}'

    for lab_name, destination_id in (
        ('Enhancement Attack - Coin Discount', 'enhancement_attack_cost_reduction_pct'),
        ('Enhancement Defense - Coin Discount', 'enhancement_defense_cost_reduction_pct'),
        ('Enhancement Utility - Coin Discount', 'enhancement_utility_cost_reduction_pct'),
    ):
        row = _single_row_by_family(rows, name=lab_name, source_family='lab')
        assert row.destination_object_type == 'meta_progression_param'
        assert row.destination_id == destination_id
        assert row.value_type == 'resolved_value'
        assert row.value == 0.0
        assert row.notes == f'governed_numeric_routed:{lab_name}'


def test_shockwave_size_selected_level_uses_sanctioned_loadout_lab_adjuster_input() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config={
            **bundle.loadout_config,
            'lab_adjusters': {
                'Farming': {
                    'Shockwave Size': 11,
                }
            },
        },
        perk_config=bundle.perk_config,
    )

    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    row = _single_row(rows, 'Shockwave Size::Selected Level')
    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'shockwave.size_lab_level'
    assert row.value == 11.0
    assert row.notes == 'loadout_lab_adjuster_routed:Shockwave Size'


def test_range_selected_level_uses_sanctioned_loadout_lab_adjuster_input() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config={
            **bundle.loadout_config,
            'lab_adjusters': {
                'Farming': {
                    'Range': 7,
                }
            },
        },
        perk_config=bundle.perk_config,
    )

    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    row = _single_row(rows, 'Range::Selected Level')
    assert row.destination_object_type == 'runtime_mechanic_param'
    assert row.destination_id == 'tower.range_lab_level'
    assert row.value == 7.0
    assert row.notes == 'loadout_lab_adjuster_routed:Range'


def test_shockwave_size_selected_level_is_absent_without_explicit_loadout_lab_adjuster() -> None:
    rows = _compiled_rows(_base_account_state())

    assert all(row.stat_name != 'Shockwave Size::Selected Level' for row in rows)


def test_range_selected_level_is_absent_without_explicit_loadout_lab_adjuster() -> None:
    rows = _compiled_rows(_base_account_state())

    assert all(row.stat_name != 'Range::Selected Level' for row in rows)


def test_wave_skip_card_publishes_timing_family_state_surface() -> None:
    state = _base_account_state()
    assert 'Wave Skip' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Wave Skip']},
    )

    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        mutated,
        family_id='timing_scenario_probe',
        requested_surface_ids=('state::cards.wave_skip.chance_pct',),
        preset_name=mutated.default_preset,
        state_mode='start_of_run',
        notes='wave_skip_family_publication_test',
    )

    row = statbook.rows.get('state::cards.wave_skip.chance_pct')
    assert row is not None
    assert row.final_value is not None
    assert row.status == 'resolved'


def test_berserker_card_remains_present_when_projection_facet_is_enabled() -> None:
    state = _base_account_state()
    assert 'Berserker' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Berserker']},
    )

    start_rows = _compiled_rows_with_projection(mutated, ScenarioProjectionState())
    projected_rows = _compiled_rows_with_projection(
        mutated,
        ScenarioProjectionState(berserker_damage_bonus=True),
    )

    assert _single_row(start_rows, 'Berserker').source_family == 'card'
    assert _single_row(projected_rows, 'Berserker').source_family == 'card'


def test_berserker_projection_publishes_explicit_full_stack_runtime_assumption() -> None:
    state = _base_account_state()
    assert 'Berserker' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Berserker']},
    )

    rows = _compiled_rows_with_projection(
        mutated,
        ScenarioProjectionState(berserker_damage_bonus=True),
    )
    assumed_row = _single_row(rows, 'Berserker::Assumed Full Stack Bonus')

    assert assumed_row.source_family == 'card'
    assert assumed_row.destination_object_type == 'runtime_mechanic_param'
    assert assumed_row.destination_id == 'cards.berserker.assumed_bonus_multiplier'
    assert assumed_row.value == 8.0
    assert assumed_row.notes == 'projection_state=berserker_damage_bonus:assumed_full_stack_x8'


def test_progression_family_publishes_berserker_full_stack_assumption_surface() -> None:
    state = _base_account_state()
    assert 'Berserker' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Berserker']},
    )

    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        mutated,
        family_id='progression_start_of_run',
        requested_surface_ids=('state::cards.berserker.assumed_bonus_multiplier',),
        preset_name=mutated.default_preset,
        state_mode='max_progression',
        notes='hardening_f_berserker_projection_probe',
    )
    row = statbook.rows['state::cards.berserker.assumed_bonus_multiplier']

    assert row.final_value == 8.0
    assert row.status == 'resolved'


def test_progression_family_publishes_ultimate_crit_surface_and_uw_helper_factor() -> None:
    state = _base_account_state()
    assert 'Ultimate Crit' in state.cards_inventory
    mutated = replace(
        state,
        card_presets={**state.card_presets, state.default_preset: ['Ultimate Crit']},
    )

    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        mutated,
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'state::cards.ultimate_crit.chance_pct',
            'state::tower.crit_multiplier',
        ),
        preset_name=mutated.default_preset,
        state_mode='start_of_run',
        notes='hardening_f_ultimate_crit_probe',
    )

    card_row = statbook.rows['state::cards.ultimate_crit.chance_pct']
    factor_row = statbook.rows['derived::edamage.uw_crit_card_factor']

    assert card_row.final_value == pytest.approx(3.0)
    assert card_row.status == 'resolved'
    assert factor_row.final_value > 1.0
    assert factor_row.status == 'resolved'
    assert any(c['stat_name'] == 'state::cards.ultimate_crit.chance_pct' for c in factor_row.contributors)


def test_black_hole_uw_tracks_publish_progression_ehp_support_surfaces() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'support_surface::ehp.black_hole_duration_seconds',
            'support_surface::ehp.black_hole_cooldown_seconds',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_primordial_support_surface_probe',
    )

    duration_row = statbook.rows['support_surface::ehp.black_hole_duration_seconds']
    cooldown_row = statbook.rows['support_surface::ehp.black_hole_cooldown_seconds']

    assert duration_row.final_value == 32.0
    assert duration_row.status == 'resolved'
    assert cooldown_row.final_value == 50.0
    assert cooldown_row.status == 'resolved'


def test_progression_family_publishes_raw_uw_timing_rows_separately_from_timing_effective_rows() -> None:
    planner = QEResolutionPlanner()
    progression = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'state::uw.black_hole.base_duration_seconds',
            'state::uw.black_hole.base_cooldown_seconds',
            'state::uw.golden_tower.base_duration_seconds',
            'state::uw.golden_tower.base_cooldown_seconds',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_uw_raw_base_probe',
    )
    timing = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='timing_farm_with_perks',
        requested_surface_ids=(
            'state::uw.black_hole.duration_seconds',
            'state::uw.black_hole.cooldown_seconds',
            'state::uw.golden_tower.duration_seconds',
            'state::uw.golden_tower.cooldown_seconds',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_uw_effective_probe',
    )

    assert progression.rows['state::uw.black_hole.base_duration_seconds'].final_value == pytest.approx(36.0)
    assert progression.rows['state::uw.black_hole.base_cooldown_seconds'].final_value == pytest.approx(46.0)
    assert progression.rows['state::uw.golden_tower.base_duration_seconds'].final_value == pytest.approx(42.0)
    assert progression.rows['state::uw.golden_tower.base_cooldown_seconds'].final_value == pytest.approx(180.0)
    assert timing.rows['state::uw.black_hole.duration_seconds'].final_value == pytest.approx(36.0)
    assert timing.rows['state::uw.black_hole.cooldown_seconds'].final_value == pytest.approx(46.0)
    assert timing.rows['state::uw.golden_tower.duration_seconds'].final_value == pytest.approx(42.0)
    assert timing.rows['state::uw.golden_tower.cooldown_seconds'].final_value == pytest.approx(180.0)


def test_progression_family_publishes_active_thunder_bot_duration_and_linger_surfaces() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'state::bot.thunder.duration_seconds',
            'state::bot.thunder.linger_duration_seconds',
            'state::bot.thunder.linger_slow_pct',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_thunder_bot_publication_probe',
    )

    duration_row = statbook.rows['state::bot.thunder.duration_seconds']
    linger_duration_row = statbook.rows['state::bot.thunder.linger_duration_seconds']
    linger_slow_row = statbook.rows['state::bot.thunder.linger_slow_pct']

    assert duration_row.final_value == pytest.approx(5.0)
    assert duration_row.status == 'resolved'
    assert linger_duration_row.final_value == pytest.approx(0.0)
    assert linger_duration_row.status == 'resolved'
    assert linger_slow_row.final_value == pytest.approx(0.2)
    assert linger_slow_row.status == 'resolved'


def test_report_snapshot_resolves_active_thunder_bot_duration_and_linger_rows() -> None:
    snapshot = _resolved_snapshot(_base_account_state())
    rows = snapshot.statbook.rows

    assert rows['state::bot.thunder.duration_seconds'].final_value == pytest.approx(5.0)
    assert rows['state::bot.thunder.duration_seconds'].status == 'resolved'
    assert rows['state::bot.thunder.linger_duration_seconds'].final_value == pytest.approx(0.0)
    assert rows['state::bot.thunder.linger_duration_seconds'].status == 'resolved'
    assert rows['state::bot.thunder.linger_slow_pct'].final_value == pytest.approx(0.2)
    assert rows['state::bot.thunder.linger_slow_pct'].status == 'resolved'


def test_flame_bot_burn_stack_lab_resolves_from_sanctioned_lab_summary() -> None:
    rows = _compiled_rows(_base_account_state())
    burn_stack_row = _single_row_by_family(rows, name='Flame Bot - Burn Stack', source_family='lab')

    assert burn_stack_row.destination_object_type == 'runtime_mechanic_param'
    assert burn_stack_row.destination_id == 'bot.flame_bot.lab_burn_stack'
    assert burn_stack_row.value == pytest.approx(0.0)
    assert burn_stack_row.value_type == 'resolved_value'
    assert burn_stack_row.notes == 'kb_lab_value_table_resolved:Flame Bot - Burn Stack'


def test_progression_family_publishes_flame_bot_burn_stack_surface_without_gated_placeholder() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=('state::bot.flame_bot.lab_burn_stack',),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_flame_bot_burn_stack_probe',
    )

    row = statbook.rows['state::bot.flame_bot.lab_burn_stack']

    assert row.final_value == pytest.approx(0.0)
    assert row.status == 'resolved'
    assert row.contributors
    assert row.contributors[0]['surface_id'] == 'state::bot.flame_bot.lab_burn_stack'
    assert row.contributors[0]['value'] == pytest.approx(0.0)


def test_progression_family_publishes_effective_bot_range_surfaces_with_tower_range_amplification() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'state::bot.golden.range_m',
            'state::bot.amplify.range_m',
            'state::bot.flame.range_m',
            'state::bot.thunder.range_m',
            'state::bot.global.range_bonus_m',
            'state::tower.range_m',
            'state::bot.golden.effective_range_m',
            'state::bot.amplify.effective_range_m',
            'state::bot.flame.effective_range_m',
            'state::bot.thunder.effective_range_m',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_bot_effective_range_probe',
    )

    tower_range = statbook.rows['state::tower.range_m'].final_value
    global_bonus = statbook.rows['state::bot.global.range_bonus_m'].final_value
    amplification = 1.33 * (tower_range / 69.5)

    for bot_name in ('golden', 'amplify', 'flame', 'thunder'):
        raw_row = statbook.rows[f'state::bot.{bot_name}.range_m']
        effective_row = statbook.rows[f'state::bot.{bot_name}.effective_range_m']
        assert raw_row.status == 'resolved'
        assert effective_row.status == 'resolved'
        assert effective_row.final_value == pytest.approx((raw_row.final_value + global_bonus) * amplification)
        contributor_ids = {c['stat_name'] for c in effective_row.contributors}
        assert f'state::bot.{bot_name}.range_m' in contributor_ids
        assert 'state::bot.global.range_bonus_m' in contributor_ids
        assert 'state::tower.range_m' in contributor_ids


def test_progression_family_publishes_relic_support_surfaces_for_derived_consumers() -> None:
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        _base_account_state(),
        family_id='progression_start_of_run',
        requested_surface_ids=(
            'support_surface::ehp.health_relic_pct',
            'support_surface::ehp.dabs_relic_pct',
            'support_surface::ehp.def_pct_relic_pct',
            'support_surface::eecon.adstarter_theme_relic_factor',
            'support_surface::eecon.freeup_attack_relic_pct',
            'support_surface::eecon.freeup_defense_relic_pct',
            'support_surface::eecon.freeup_utility_relic_pct',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        notes='hardening_f_relic_support_probe',
    )

    assert statbook.rows['support_surface::ehp.health_relic_pct'].final_value == pytest.approx(0.51)
    assert statbook.rows['support_surface::ehp.health_relic_pct'].status == 'resolved'
    assert statbook.rows['support_surface::ehp.dabs_relic_pct'].final_value == pytest.approx(0.28)
    assert statbook.rows['support_surface::ehp.def_pct_relic_pct'].final_value == pytest.approx(0.04)
    assert statbook.rows['support_surface::eecon.adstarter_theme_relic_factor'].final_value == pytest.approx(1.48)
    assert statbook.rows['support_surface::eecon.freeup_attack_relic_pct'].final_value == pytest.approx(0.06)
    assert statbook.rows['support_surface::eecon.freeup_defense_relic_pct'].final_value == pytest.approx(0.03)
    assert statbook.rows['support_surface::eecon.freeup_utility_relic_pct'].final_value == pytest.approx(0.05)


def test_audited_enemy_and_bc_labs_have_explicit_owned_destinations_without_pending_limbs() -> None:
    rows = _compiled_rows(_base_account_state())

    expected = {
        'Battle Condition Reduction': ('environment_param', 'bc.reduction.generic_pct', 'kb_lab_application_registry_routed'),
        'Common Enemy Health': ('environment_param', 'enemy.common.health_multiplier', 'kb_uw_lab_direct_routed:Common Enemy Health'),
        'Common Enemy Attack': ('environment_param', 'enemy.common.attack_multiplier', 'kb_uw_lab_direct_routed:Common Enemy Attack'),
        'Fast Enemy Health': ('environment_param', 'enemy.fast.health_multiplier', 'kb_uw_lab_direct_routed:Fast Enemy Health'),
        'Fast Enemy Attack': ('environment_param', 'enemy.fast.attack_multiplier', 'kb_uw_lab_direct_routed:Fast Enemy Attack'),
        'Fast Enemy Speed': ('environment_param', 'enemy.fast.speed_multiplier', 'kb_uw_lab_direct_routed:Fast Enemy Speed'),
        'Tank Enemy Health': ('environment_param', 'enemy.tank.health_multiplier', 'kb_uw_lab_direct_routed:Tank Enemy Health'),
        'Tank Enemy Attack': ('environment_param', 'enemy.tank.attack_multiplier', 'kb_uw_lab_direct_routed:Tank Enemy Attack'),
        'Ranged Enemy Health': ('environment_param', 'enemy.ranged.health_multiplier', 'kb_uw_lab_direct_routed:Ranged Enemy Health'),
        'Ranged Enemy Attack': ('environment_param', 'enemy.ranged.attack_multiplier', 'kb_uw_lab_direct_routed:Ranged Enemy Attack'),
        'Boss Health': ('environment_param', 'enemy.boss.health_multiplier_lab', 'kb_uw_lab_direct_routed:Boss Health'),
        'Boss Attack': ('environment_param', 'enemy.boss.attack_multiplier', 'kb_uw_lab_direct_routed:Boss Attack'),
        'Protector Health': ('mechanic_param', 'enemy.protector.health_multiplier', 'kb_uw_lab_direct_routed:Protector Health'),
        'Protector Radius': ('mechanic_param', 'enemy.protector.radius_m', 'kb_uw_lab_direct_routed:Protector Radius'),
        'Protector Damage Reduction': ('mechanic_param', 'enemy.protector.damage_reduction_pct', 'kb_uw_lab_direct_routed:Protector Damage Reduction'),
        'Ray Enemy Attack': ('environment_param', 'enemy.ray.attack_multiplier', 'kb_uw_lab_direct_routed:Ray Enemy Attack'),
        'Ray Enemy Health': ('environment_param', 'enemy.ray.health_multiplier', 'kb_uw_lab_direct_routed:Ray Enemy Health'),
        'Vampire Enemy Attack': ('environment_param', 'enemy.vampire.attack_multiplier', 'kb_uw_lab_direct_routed:Vampire Enemy Attack'),
        'Vampire Enemy Health': ('environment_param', 'enemy.vampire.health_multiplier', 'kb_uw_lab_direct_routed:Vampire Enemy Health'),
        'Scatter Enemy Attack': ('environment_param', 'enemy.scatter.attack_multiplier', 'kb_uw_lab_direct_routed:Scatter Enemy Attack'),
        'Scatter Enemy Health': ('environment_param', 'enemy.scatter.health_multiplier', 'kb_uw_lab_direct_routed:Scatter Enemy Health'),
        'Ranged Enemy Range': ('environment_param', 'enemy.ranged.range_multiplier', 'kb_uw_lab_direct_routed:Ranged Enemy Range'),
        'Enemy Speed': ('environment_param', 'bc.enemy_speed_pct', 'kb_uw_lab_direct_routed:Enemy Speed'),
        'More Enemies': ('environment_param', 'bc.more_enemies_pct', 'kb_uw_lab_direct_routed:More Enemies'),
        'Enemy Attack Speed': ('environment_param', 'bc.enemy_attack_speed_pct', 'kb_uw_lab_direct_routed:Enemy Attack Speed'),
        'Knockback Resistance': ('environment_param', 'bc.knockback_resistance_pct', 'kb_uw_lab_direct_routed:Knockback Resistance'),
        'Thorns Resistance': ('environment_param', 'bc.thorns_resistance_pct', 'kb_uw_lab_direct_routed:Thorns Resistance'),
        'Orb Resistance': ('environment_param', 'bc.orb_resistance_pct', 'kb_uw_lab_direct_routed:Orb Resistance'),
        'Plasma Cannon Resistance': ('environment_param', 'bc.plasma_cannon_resistance_pct', 'kb_uw_lab_direct_routed:Plasma Cannon Resistance'),
        'Death Ray Resistance': ('environment_param', 'bc.death_ray_resistance_pct', 'kb_uw_lab_direct_routed:Death Ray Resistance'),
        'Death Defy Down': ('environment_param', 'bc.death_defy_down_pct', 'kb_uw_lab_direct_routed:Death Defy Down'),
        'Energy Shields Down': ('environment_param', 'bc.energy_shields_down_pct', 'kb_uw_lab_direct_routed:Energy Shields Down'),
        'Enemy Level Skip Reduction': ('environment_param', 'bc.enemy_level_skip_reduction_pp', 'kb_uw_lab_direct_routed:Enemy Level Skip Reduction'),
        'Armored Enemies': ('environment_param', 'bc.armored_enemies_blocked_hits', 'kb_uw_lab_direct_routed:Armored Enemies'),
        "Fast's Ultimate": ('environment_param', 'enemy.fast.ultimate_enabled', "governed_numeric_routed:Fast's Ultimate"),
        'Ranged Ultimate': ('environment_param', 'enemy.ranged.ultimate_enabled', 'governed_numeric_routed:Ranged Ultimate'),
        "Boss's Ultimate": ('environment_param', 'enemy.boss.ultimate_enabled', "governed_numeric_routed:Boss's Ultimate"),
        "Basic's Ultimate": ('environment_param', 'enemy.basic.ultimate_enabled', "governed_numeric_routed:Basic's Ultimate"),
        "Tank's Ultimate": ('environment_param', 'enemy.tank.ultimate_enabled', "governed_numeric_routed:Tank's Ultimate"),
        "Protector's Ultimate": ('environment_param', 'enemy.protector.ultimate_enabled', "governed_numeric_routed:Protector's Ultimate"),
    }

    for lab_name, expected_row in expected.items():
        object_type, destination_id, notes = expected_row
        row = _single_row_by_family(rows, name=lab_name, source_family='lab')
        assert row.destination_object_type == object_type
        assert row.destination_id == destination_id
        assert row.notes == notes
        assert row.destination_id is not None
        assert row.notes != 'kb_routing_pending_for_lab_label'


def test_transient_perk_presets_only_materialize_when_projection_facet_is_enabled() -> None:
    state = _base_account_state()
    mutated = replace(
        state,
        perk_presets={
            **state.perk_presets,
            'projected_auto': [
                PerkSelection(
                    perk_id='PERK_X1_50_TOWER_DAMAGE_BUT_BOSSES_HAVE_8X_HEALTH',
                    picks=1,
                )
            ],
        },
        perk_preset_namespace_class='transient',
        active_perk_preset='projected_auto',
    )

    start_rows = _compiled_rows_with_projection(mutated, ScenarioProjectionState())
    projected_rows = _compiled_rows_with_projection(
        mutated,
        ScenarioProjectionState(projected_perks=True),
    )

    assert all(row.source_family != 'perk' for row in start_rows)
    assert any(row.source_family == 'perk' for row in projected_rows)


def test_death_wave_health_lab_only_materializes_when_projection_facet_is_enabled() -> None:
    state = _base_account_state()
    mutated = replace(
        state,
        labs={**state.labs, 'Death Wave Health': 1},
        ultimate_weapons={
            **state.ultimate_weapons,
            'Death Wave': UltimateWeaponSnapshot(
                name='Death Wave',
                unlocked='true',
                track_levels=[],
                track_values=[],
            ),
        },
    )

    start_rows = _compiled_rows_with_projection(mutated, ScenarioProjectionState())
    projected_rows = _compiled_rows_with_projection(
        mutated,
        ScenarioProjectionState(death_wave_health=True),
    )

    assert all(row.stat_name != 'Death Wave Health' for row in start_rows)
    assert _single_row(projected_rows, 'Death Wave Health').source_family == 'lab'


def test_max_workshop_projection_uses_max_levels_without_mode_string_coupling() -> None:
    state = _base_account_state()
    candidate_name, candidate = next(
        (name, entry)
        for name, entry in state.workshop.items()
        if entry.max_level is not None and entry.preset_levels.get(state.default_preset) is not None and entry.max_level != entry.preset_levels.get(state.default_preset)
    )

    start_row = _single_row_by_family(
        _compiled_rows_with_projection(state, ScenarioProjectionState()),
        name=candidate_name,
        source_family='workshop',
    )
    projected_row = _single_row_by_family(
        _compiled_rows_with_projection(state, ScenarioProjectionState(max_workshop=True)),
        name=candidate_name,
        source_family='workshop',
    )

    assert start_row.raw_level in (None, candidate.preset_levels.get(state.default_preset))
    assert projected_row.raw_level in (None, candidate.max_level)
    assert start_row.value != projected_row.value
    assert projected_row.notes == 'projection_state=max_workshop:using_workshop_max_level'


def test_sharp_fortitude_rows_use_module_preset_and_keep_module_provenance_and_contributors(monkeypatch) -> None:
    state = _base_account_state()
    original_bind = stat_input_compiler.bind_preset_family

    def _bind_with_distinct_module_lane(**kwargs):
        bound = original_bind(**kwargs)
        return qe_models.BoundPresetFamily(
            preset_name=bound.preset_name,
            card_preset_name=bound.card_preset_name,
            module_preset_name='Milestone',
            perk_preset_name=bound.perk_preset_name,
            perk_namespace_class=bound.perk_namespace_class,
            state_mode=bound.state_mode,
            perks_enabled=bound.perks_enabled,
        )

    monkeypatch.setattr(stat_input_compiler, 'bind_preset_family', _bind_with_distinct_module_lane)
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    sharp_rows = [
        row for row in rows
        if row.source_family == 'module'
        and row.source_name == 'Sharp Fortitude'
        and row.stat_name in {'Sharp Fortitude::main', 'Sharp Fortitude::unique'}
    ]
    assert sharp_rows
    assert all(row.preset_name == 'Milestone' for row in sharp_rows)
    assert all(row.provenance == 'IDS::Modules' for row in sharp_rows)

    sf_manual_unique_rows = [
        row for row in sharp_rows
        if 'kb_manual_sharp_fortitude' in (row.notes or '')
    ]
    assert {row.contributor_id for row in sf_manual_unique_rows} == {
        'module__armor__wall_health__pct@@sharp fortitude@@primary@@unique',
        'module__armor__wall_regen__pct@@sharp fortitude@@primary@@unique',
    }


def test_routing_diagnostics_distinguish_classes_without_false_unmapped_inflation() -> None:
    state = _base_account_state()
    snapshot = _resolved_snapshot(state)
    statbook = snapshot.statbook
    class_counts = statbook.diagnostics.get('input_routing_class_counts') or {}
    mapped_count_by_family = statbook.diagnostics.get('mapped_count_by_family') or {}
    input_count_by_family = statbook.diagnostics.get('input_count_by_family') or {}

    assert class_counts.get('account_metadata', 0) >= 1
    assert class_counts.get('capability_policy', 0) >= 1
    assert class_counts.get('resolved', 0) >= 1
    assert statbook.diagnostics.get('unmapped_input_count', 0) == class_counts.get('truly_unrouted_unknown', 0)
    assert statbook.diagnostics.get('qe_resolution_interface') == 'report_snapshot_planner'
    assert mapped_count_by_family.get('module', 0) >= 1
    assert input_count_by_family.get('module', 0) >= mapped_count_by_family.get('module', 0)


def test_compare_kb_incomplete_areas_only_count_true_unrouted_inputs() -> None:
    state = _base_account_state()
    snapshot = _resolved_snapshot(state)
    stat_inputs = list(snapshot.stat_inputs)
    statbook = snapshot.statbook
    kb_incomplete = _build_kb_incomplete_areas(stat_inputs, statbook.to_dict(), {})
    active_unmapped = {item['stat_name'] for item in kb_incomplete.get('active_unmapped_inputs', [])}

    assert 'Intro Sprint' not in active_unmapped
    assert 'Starting Cash' not in active_unmapped
    assert 'Assist Module Bonus - Armor' not in active_unmapped
    assert 'Assist Module Substats - Armor' not in active_unmapped
    assert 'Keys spent' not in active_unmapped
    assert 'Auto Pick Perks' not in active_unmapped
    assert 'Ban Perks' not in active_unmapped
