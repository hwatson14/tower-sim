from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from models.preset_contract import normalize_preset_name, require_canonical_preset_name
from parsers.ids_parser import parse_ids


def _ids_raw():
    return parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')


def test_invalid_default_preset_fails_closed():
    with pytest.raises(ValueError, match='default_preset'):
        compile_account_state(_ids_raw(), default_preset='Testing')


@pytest.mark.parametrize('field_name,payload', [
    ('active_card_preset', {'active_card_preset': 'Testing'}),
    ('active_module_preset', {'active_module_preset': 'Preset 3'}),
])
def test_invalid_runtime_loadout_preset_names_fail_closed(field_name, payload):
    with pytest.raises(ValueError, match=field_name):
        compile_account_state(_ids_raw(), default_preset='Farming', loadout_config=payload)


def test_missing_active_loadout_presets_use_explicit_default_preset_only():
    state = compile_account_state(_ids_raw(), default_preset='Tourney', loadout_config={})
    assert state.active_card_preset == 'Tourney'
    assert state.active_module_preset == 'Tourney'


def test_empty_card_preset_payload_is_valid_and_explicit():
    state = compile_account_state(
        _ids_raw(),
        default_preset='Farming',
        loadout_config={'card_presets': {'Farming': []}},
    )
    assert state.card_presets['Farming'] == []


def test_missing_empty_and_zero_remain_distinct_in_parser_system_behavior():
    from compilers.account_state_compiler import _parse_optional_int

    assert _parse_optional_int('') is None
    assert _parse_optional_int('?') is None
    assert _parse_optional_int('0') == 0
    assert _parse_optional_int(' 0 ') == 0


def test_noncanonical_perk_preset_name_fails_closed_in_canonical_flow():
    with pytest.raises(ValueError, match='perk_presets contains non-canonical preset name'):
        compile_account_state(
            _ids_raw(),
            default_preset='Farming',
            perk_config={
                'perk_presets': {'Testing': [{'perk_id': 'PERK_ORBS_1', 'picks': 1}]},
                'active_perk_preset': 'Testing',
            },
        )


def test_noncanonical_active_perk_preset_fails_closed_in_canonical_flow():
    with pytest.raises(ValueError, match='active_perk_preset'):
        compile_account_state(
            _ids_raw(),
            default_preset='Farming',
            perk_config={
                'perk_presets': {'Farming': [{'perk_id': 'PERK_ORBS_1', 'picks': 1}]},
                'active_perk_preset': 'Testing',
            },
        )


def test_transient_perk_preset_namespace_must_be_explicitly_typed():
    state = compile_account_state(
        _ids_raw(),
        default_preset='Farming',
        perk_config={
            'preset_namespace_class': 'transient',
            'perk_presets': {'ProjectedMax_AllAllowedExceptBanned': [{'perk_id': 'PERK_ORBS_1', 'picks': 1}]},
            'active_perk_preset': 'ProjectedMax_AllAllowedExceptBanned',
        },
    )
    assert state.active_perk_preset == 'ProjectedMax_AllAllowedExceptBanned'
    assert state.perk_presets['ProjectedMax_AllAllowedExceptBanned'][0].perk_id == 'PERK_ORBS_1'


def test_aliases_normalize_at_ingestion_only():
    assert normalize_preset_name('Testing', allow_aliases=True) == 'Milestone'
    assert normalize_preset_name('Testing', allow_aliases=False) is None
    with pytest.raises(ValueError, match='runtime_input'):
        require_canonical_preset_name('Testing', field_name='runtime_input')
