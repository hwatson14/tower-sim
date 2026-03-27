from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.runtime_state import ScenarioRuntimeInputs
from engine.state_identity import bind_state_identity, compile_stat_inputs_with_identity
from tests.helpers import build_state



def test_state_identity_is_stable_for_identical_inputs():
    state_a = build_state()
    state_b = build_state()
    scenario_inputs = ScenarioRuntimeInputs.from_mapping({'boss_wave_interval': 11.5})

    binding_a = bind_state_identity(
        state_a,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        scenario_runtime_inputs=scenario_inputs,
    )
    binding_b = bind_state_identity(
        state_b,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
        scenario_runtime_inputs=scenario_inputs,
    )

    assert binding_a.identity.as_tuple() == binding_b.identity.as_tuple()


def test_state_identity_changes_when_any_identity_surface_changes():
    base_state = build_state()
    account_changed_state = build_state()
    account_changed_state.labs['Damage'] = (account_changed_state.labs['Damage'] or 0) + 1

    base_identity = bind_state_identity(base_state, preset_name='Farming', state_mode='start_of_run', runtime_branch_id='branch_base').identity
    account_identity = bind_state_identity(account_changed_state, preset_name='Farming', state_mode='start_of_run', runtime_branch_id='branch_base').identity
    loadout_identity = bind_state_identity(base_state, preset_name='Tourney', state_mode='start_of_run', runtime_branch_id='branch_base').identity
    scenario_identity = bind_state_identity(base_state, preset_name='Farming', state_mode='max_progression', runtime_branch_id='branch_base').identity
    branch_identity = bind_state_identity(base_state, preset_name='Farming', state_mode='start_of_run', runtime_branch_id='branch_overlay').identity

    assert account_identity.account_snapshot_id != base_identity.account_snapshot_id
    assert loadout_identity.loadout_id != base_identity.loadout_id
    assert scenario_identity.scenario_id != base_identity.scenario_id
    assert branch_identity.runtime_branch_id != base_identity.runtime_branch_id


def test_account_snapshot_id_does_not_depend_on_ids_file_path():
    state = build_state()
    moved_state = replace(state, ids_path=Path('/tmp/other/_IDS.csv'))

    base_identity = bind_state_identity(state, preset_name='Farming', state_mode='start_of_run', runtime_branch_id='branch_base').identity
    moved_identity = bind_state_identity(moved_state, preset_name='Farming', state_mode='start_of_run', runtime_branch_id='branch_base').identity

    assert moved_identity.account_snapshot_id == base_identity.account_snapshot_id


def test_compile_stat_inputs_with_identity_preserves_existing_compiler_behavior():
    state = build_state()

    bound = compile_stat_inputs_with_identity(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    )

    assert bound.binding.identity.runtime_branch_id == 'branch_base'
    assert bound.stat_inputs


def test_state_identity_distinguishes_missing_and_explicit_empty_perk_state():
    missing_state = build_state()
    base_empty_state = build_state()
    empty_perk_presets = dict(base_empty_state.perk_presets)
    empty_perk_presets['Farming'] = []
    empty_state = replace(
        base_empty_state,
        perk_presets=empty_perk_presets,
        active_perk_preset='Farming',
    )

    missing_identity = bind_state_identity(
        missing_state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    ).identity
    empty_identity = bind_state_identity(
        empty_state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    ).identity

    assert missing_identity.loadout_id != empty_identity.loadout_id


def test_state_identity_distinguishes_missing_and_zero_runtime_values():
    zero_state = build_state()
    missing_state = build_state()
    zero_state.labs['Damage'] = 0
    missing_state.labs.pop('Damage', None)

    zero_identity = bind_state_identity(
        zero_state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    ).identity
    missing_identity = bind_state_identity(
        missing_state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    ).identity

    assert zero_identity.account_snapshot_id != missing_identity.account_snapshot_id
