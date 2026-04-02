from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from input.state_types import PerkSelection, ScenarioProjectionState, UltimateWeaponSnapshot
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from evaluators.compare import _build_kb_incomplete_areas
from qe import models as qe_models
from qe.stat_input_compiler import compile_stat_inputs
import qe.stat_input_compiler as stat_input_compiler
from qe.routing import QEResolutionPlanner


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


def test_berserker_card_is_only_compiled_when_projection_facet_is_enabled() -> None:
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

    assert all(row.stat_name != 'Berserker' for row in start_rows)
    assert _single_row(projected_rows, 'Berserker').source_family == 'card'


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
