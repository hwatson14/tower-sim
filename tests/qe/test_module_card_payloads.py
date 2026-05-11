from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.query_module_policy import build_module_card_payloads, module_substat_unlock_levels


def _account_state():
    bundle = load_inputs(ids_path=ROOT / 'input' / 'imports' / 'ids.csv')
    return build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )


def test_module_card_payloads_publish_v28_locked_assist_state():
    payload = build_module_card_payloads(_account_state())
    farming = payload['presets']['Farming']

    assert farming['armor']['assist'] is None
    assert farming['generator']['assist'] is None
    assert farming['core']['assist'] is None


def test_module_card_payloads_use_qe_unlock_schedule_for_eight_slots():
    assert module_substat_unlock_levels() == (1, 1, 41, 101, 141, 161, 201, 241)
    payload = build_module_card_payloads(_account_state())
    assert payload['presets']['Farming']['armor']['assist'] is None


def test_module_card_payloads_primary_card_uses_v28_any_other_module_level_and_cap():
    account_state = _account_state()
    payload = build_module_card_payloads(account_state)
    core_primary = payload['presets']['Farming']['core']['primary']
    expected_level = account_state.modules_inventory['Any Other'].level

    assert core_primary['module_name'] == 'Any Other'
    assert core_primary['displayed_level'] == expected_level
    assert core_primary['displayed_level_cap'] is None
    assert core_primary['level_text'] == f'Lv. {expected_level}'
    assert core_primary['main_value_text'].startswith('x')
    assert core_primary['unique_text'] is None
