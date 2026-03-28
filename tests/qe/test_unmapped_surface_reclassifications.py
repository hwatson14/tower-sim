from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from evaluators.compare import _build_kb_incomplete_areas
from qe.stat_input_compiler import compile_stat_inputs
from qe.stat_resolution import resolve_stats


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


def _single_row(rows, name: str):
    matched = [row for row in rows if row.stat_name == name]
    assert matched, f'missing compiled row for {name!r}'
    assert len(matched) == 1, f'expected one compiled row for {name!r}, got {len(matched)}'
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


def test_routing_diagnostics_distinguish_classes_without_false_unmapped_inflation() -> None:
    stat_inputs = _compiled_rows(_base_account_state())
    statbook = resolve_stats(stat_inputs)
    class_counts = statbook.diagnostics.get('input_routing_class_counts') or {}

    assert class_counts.get('account_metadata', 0) >= 1
    assert class_counts.get('capability_policy', 0) >= 1
    assert class_counts.get('resolved', 0) >= 1
    assert statbook.diagnostics.get('unmapped_input_count', 0) == class_counts.get('truly_unrouted_unknown', 0)


def test_compare_kb_incomplete_areas_only_count_true_unrouted_inputs() -> None:
    stat_inputs = _compiled_rows(_base_account_state())
    statbook = resolve_stats(stat_inputs)
    kb_incomplete = _build_kb_incomplete_areas(stat_inputs, statbook.to_dict(), {})
    active_unmapped = {item['stat_name'] for item in kb_incomplete.get('active_unmapped_inputs', [])}

    assert 'Intro Sprint' not in active_unmapped
    assert 'Starting Cash' not in active_unmapped
    assert 'Assist Module Bonus - Armor' not in active_unmapped
    assert 'Assist Module Substats - Armor' not in active_unmapped
    assert 'Keys spent' not in active_unmapped
    assert 'Auto Pick Perks' not in active_unmapped
    assert 'Ban Perks' not in active_unmapped
