from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from engine.scenario_runtime_inputs import ScenarioRuntimeInputs
from engine.state_identity import bind_state_identity, compile_stat_inputs_with_identity
from parsers.ids_parser import parse_ids


def _build_state():
    ids = parse_ids(ROOT / 'input' / '_IDS.csv')
    loadout = json.loads((ROOT / 'input' / 'loadout.json').read_text())
    perks = json.loads((ROOT / 'input' / 'perks.json').read_text())
    return compile_account_state(ids, default_preset='Farming', loadout_config=loadout, perk_config=perks)


def test_state_identity_is_stable_for_identical_inputs():
    state_a = _build_state()
    state_b = _build_state()
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
    base_state = _build_state()
    account_changed_state = _build_state()
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


def test_compile_stat_inputs_with_identity_preserves_existing_compiler_behavior():
    state = _build_state()

    bound = compile_stat_inputs_with_identity(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        runtime_branch_id='branch_base',
    )

    assert bound.binding.identity.runtime_branch_id == 'branch_base'
    assert bound.stat_inputs
