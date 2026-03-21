from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.incremental_cache_fingerprint import IncrementalCacheFingerprintBuilder
from parsers.ids_parser import parse_ids


def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def test_cache_fingerprint_ignores_workshop_only_mutation():
    state = _build_state()
    base_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run')
    base_fp = IncrementalCacheFingerprintBuilder().build(
        stat_inputs=base_inputs,
        state_mode='start_of_run',
        preset_name='Farming',
        card_preset_name=None,
        module_preset_name=None,
        perk_preset_name=None,
        perks_enabled=True,
        perk_counts_override=None,
    )
    state.workshop['Health'].preset_levels['Farming'] += 1
    mutated_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run')
    mutated_fp = IncrementalCacheFingerprintBuilder().build(
        stat_inputs=mutated_inputs,
        state_mode='start_of_run',
        preset_name='Farming',
        card_preset_name=None,
        module_preset_name=None,
        perk_preset_name=None,
        perks_enabled=True,
        perk_counts_override=None,
    )
    assert mutated_fp.to_dict() == base_fp.to_dict()


def test_cache_fingerprint_changes_when_non_workshop_inputs_change():
    state = _build_state()
    base_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run')
    base_fp = IncrementalCacheFingerprintBuilder().build(
        stat_inputs=base_inputs,
        state_mode='start_of_run',
        preset_name='Farming',
        card_preset_name=None,
        module_preset_name=None,
        perk_preset_name=None,
        perks_enabled=True,
        perk_counts_override=None,
    )
    changed_fp = IncrementalCacheFingerprintBuilder().build(
        stat_inputs=base_inputs,
        state_mode='start_of_run',
        preset_name='Farming',
        card_preset_name=None,
        module_preset_name=None,
        perk_preset_name=None,
        perks_enabled=False,
        perk_counts_override=None,
    )
    assert changed_fp.to_dict() != base_fp.to_dict()
