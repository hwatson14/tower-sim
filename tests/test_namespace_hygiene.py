from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.state_identity import bind_state_identity
from tests.helpers import build_state, cached_run_stats_output


TRANSIENT_NAMES = (
    'ProjectedMax_AllAllowedExceptBanned',
    'ProgressionTimeline_CurrentWave',
    '__audit_all_perks__',
)


def test_state_identity_quarantines_transient_perk_namespace_names():
    state = build_state(perks_filename='perks_projected_max.json')
    renamed = replace(
        state,
        perk_presets={'DifferentTransientName': state.perk_presets[state.active_perk_preset]},
        active_perk_preset='DifferentTransientName',
    )

    original_identity = bind_state_identity(
        state,
        preset_name='Farming',
        state_mode='max_progression',
        runtime_branch_id='branch_base',
    ).identity
    renamed_identity = bind_state_identity(
        renamed,
        preset_name='Farming',
        state_mode='max_progression',
        runtime_branch_id='branch_base',
    ).identity

    assert original_identity.loadout_id == renamed_identity.loadout_id


def test_transient_perk_rows_are_sanitized_to_canonical_preset_name():
    from compilers.stat_input_compiler import compile_stat_inputs

    state = build_state(perks_filename='perks_projected_max.json')
    rows = compile_stat_inputs(state, preset_name='Farming', state_mode='max_progression', perks_enabled=True)
    perk_rows = [row for row in rows if row.source_family == 'perk']

    assert perk_rows
    assert {row.preset_name for row in perk_rows} == {'Farming'}


def test_run_stats_canonical_outputs_do_not_leak_transient_perk_names():
    out = cached_run_stats_output('--state-mode', 'max_progression')
    for artifact_name in (
        'diagnostics.json',
        'account_state.json',
        'stat_inputs.json',
        'statbook_publishable.json',
        'ep_oracle_compare.json',
    ):
        payload = (out / artifact_name).read_text()
        for transient_name in TRANSIENT_NAMES:
            assert transient_name not in payload, f'{transient_name} leaked into {artifact_name}'

    diagnostics = json.loads((out / 'diagnostics.json').read_text())
    assert diagnostics['active_perk_preset'] == 'Farming'
    assert set(diagnostics['configured_perk_presets']) <= {'Tourney', 'Farming', 'Milestone', 'Preset 4', 'Preset 5'}
