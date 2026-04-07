from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import pytest

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.routing import QEResolutionPlanner
from qe.stat_input_compiler import compile_stat_inputs


@lru_cache(maxsize=1)
def _base_account_state():
    bundle = load_inputs()
    return build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )


def _select_module_with_substats(state):
    preset = state.default_preset
    selections = state.module_presets.get(preset, {})
    for slot_type, selection in selections.items():
        for role in ('primary', 'assist'):
            module_name = getattr(selection, role)
            if not module_name:
                continue
            module = state.modules_inventory.get(module_name)
            if module and module.substats:
                return slot_type, role, module_name, module
    raise AssertionError('expected at least one selected module with substats in fixture state')


def test_module_substat_parse_failures_are_emitted_and_diagnosed() -> None:
    state = _base_account_state()
    _, _, module_name, module = _select_module_with_substats(state)

    bad_substat = replace(module.substats[0], value='not_numeric_token', raw_token='lvl??')
    mutated_module = replace(module, substats=[bad_substat, *module.substats[1:]])
    mutated_state = replace(
        state,
        modules_inventory={**state.modules_inventory, module_name: mutated_module},
    )

    compiled_rows = compile_stat_inputs(
        mutated_state,
        preset_name=mutated_state.default_preset,
        state_mode='start_of_run',
    )
    emitted_rows = [
        row for row in compiled_rows
        if row.source_family == 'module_substat' and row.source_name == module_name and row.stat_name == bad_substat.name
    ]
    assert emitted_rows, 'module substat row should still be emitted when parse fails'
    emitted = emitted_rows[0]
    assert emitted.value_type == 'raw_text'
    assert 'module_substat_parse_failed:' in (emitted.notes or '')
    assert 'token=lvl??' in (emitted.notes or '')

    snapshot = QEResolutionPlanner().resolve_report_snapshot(
        mutated_state,
        preset_name=mutated_state.default_preset,
        state_mode='start_of_run',
        perks_enabled=bool(mutated_state.active_perk_preset),
    )
    diagnostics = snapshot.statbook.diagnostics
    class_counts = diagnostics.get('input_routing_class_counts') or {}
    unresolved_diagnostics = diagnostics.get('unresolved_contributor_diagnostics') or {}

    assert class_counts.get('unresolved_module_substat_parse', 0) >= 1
    assert unresolved_diagnostics.get('module_substat_parse_failed_count', 0) >= 1
    assert (unresolved_diagnostics.get('module_substat_parse_failed_by_substat') or {}).get(bad_substat.name, 0) >= 1


def test_assist_substat_uses_rarity_cap_table_value() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )
    defense_rows = [
        row for row in rows
        if row.source_family == 'module_substat'
        and row.source_name == 'Orbital Augment'
        and row.stat_name == 'Defense %'
    ]
    assert defense_rows
    # Armor assist cap is Epic at 10%; Defense substat is 3% at Epic in KB module-substats table.
    assert defense_rows[0].value_type == 'percent_display'
    assert defense_rows[0].value == pytest.approx(0.3)


def test_generator_assist_enemy_skip_substats_use_equipped_roll_scaled_by_assist_efficiency() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )
    attack_skip_rows = [
        row for row in rows
        if row.source_family == 'module_substat'
        and row.source_name == 'Black Hole Digestor'
        and row.stat_name == 'Enemy Attack Level Skip'
    ]
    health_skip_rows = [
        row for row in rows
        if row.source_family == 'module_substat'
        and row.source_name == 'Black Hole Digestor'
        and row.stat_name == 'Enemy Health Level Skip'
    ]
    assert attack_skip_rows
    assert health_skip_rows
    assert attack_skip_rows[0].value_type == 'percent_display'
    assert health_skip_rows[0].value_type == 'percent_display'
    assert attack_skip_rows[0].value == pytest.approx(0.6)
    assert health_skip_rows[0].value == pytest.approx(0.6)
