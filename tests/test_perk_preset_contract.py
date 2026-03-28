from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.runtime_state import compile_account_state
from engine.query_perk_compiler import active_perk_selections
from input.ids_parser import parse_ids


def _ids_raw():
    return parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')


def test_canonical_perk_flow_uses_only_active_preset_without_merging_requested_preset():
    state = compile_account_state(
        _ids_raw(),
        default_preset='Farming',
        perk_config={
            'perk_presets': {
                'Farming': [{'perk_id': 'PERK_ORBS_1', 'picks': 1}],
                'Tourney': [{'perk_id': 'PERK_BOSS_HEALTH_70_BUT_BOSS_SPEED_50', 'picks': 1}],
            },
            'active_perk_preset': 'Tourney',
        },
    )

    assert state.perk_preset_namespace_class == 'canonical'
    assert active_perk_selections(state, 'Farming') == [('PERK_ORBS_1', 1)]
    assert active_perk_selections(state, None) == [('PERK_BOSS_HEALTH_70_BUT_BOSS_SPEED_50', 1)]


def test_empty_or_missing_perk_preset_resolves_deterministically_without_default_namespace():
    state = compile_account_state(
        _ids_raw(),
        default_preset='Farming',
        perk_config={
            'perk_presets': {'Farming': []},
            'active_perk_preset': 'Farming',
        },
    )

    assert state.perk_preset_namespace_class == 'canonical'
    assert active_perk_selections(state, 'Farming') == []
    assert active_perk_selections(state, 'Milestone') == []


def test_transient_perk_namespace_must_be_explicit_and_is_tracked_on_account_state():
    state = compile_account_state(
        _ids_raw(),
        default_preset='Farming',
        perk_config={
            'preset_namespace_class': 'transient',
            'perk_presets': {'ProjectedMax_AllAllowedExceptBanned': [{'perk_id': 'PERK_ORBS_1', 'picks': 2}]},
            'active_perk_preset': 'ProjectedMax_AllAllowedExceptBanned',
        },
    )

    assert state.perk_preset_namespace_class == 'transient'
    assert active_perk_selections(state, None) == [('PERK_ORBS_1', 2)]


@pytest.mark.parametrize('namespace_class', ['canonical', ''])
def test_noncanonical_perk_preset_names_remain_invalid_without_transient_typing(namespace_class: str):
    with pytest.raises(ValueError, match='non-canonical preset name'):
        compile_account_state(
            _ids_raw(),
            default_preset='Farming',
            perk_config={
                'preset_namespace_class': namespace_class,
                'perk_presets': {'ProjectedMax_AllAllowedExceptBanned': [{'perk_id': 'PERK_ORBS_1', 'picks': 1}]},
                'active_perk_preset': 'ProjectedMax_AllAllowedExceptBanned',
            },
        )
