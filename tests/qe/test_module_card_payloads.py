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


def test_module_card_payloads_publish_selected_assist_state():
    account_state = _account_state()
    payload = build_module_card_payloads(account_state)
    farming = payload['presets']['Farming']

    for slot_type in ('armor', 'generator', 'core'):
        assert farming[slot_type]['assist']['module_name'] == (
            account_state.module_presets['Farming'][slot_type].assist
        )


def test_module_card_payloads_use_qe_unlock_schedule_for_eight_slots():
    assert module_substat_unlock_levels() == (1, 1, 41, 101, 141, 161, 201, 241)
    account_state = _account_state()
    payload = build_module_card_payloads(account_state)
    armor_assist_slots = payload['presets']['Farming']['armor']['assist']['effect_slots']
    armor_assist_level = account_state.module_system_state['armor'].assist_level
    assert len(armor_assist_slots) == 8
    assert armor_assist_slots[0]['state'] == 'populated'
    assert armor_assist_slots[3]['state'] == 'populated'
    assert armor_assist_slots[5]['unlock_level'] == 161
    assert (armor_assist_slots[5]['state'] == 'locked') is (armor_assist_level < 161)


def test_module_card_payloads_primary_card_uses_selected_core_module_level_and_cap():
    account_state = _account_state()
    payload = build_module_card_payloads(account_state)
    core_primary = payload['presets']['Farming']['core']['primary']
    expected_module_name = account_state.module_presets['Farming']['core'].primary
    expected_level = account_state.modules_inventory[expected_module_name].level

    assert core_primary['module_name'] == expected_module_name
    assert core_primary['displayed_level'] == expected_level
    assert core_primary['displayed_level_cap'] >= expected_level
    assert core_primary['level_text'] == (
        f"Lv. {expected_level} / {core_primary['displayed_level_cap']}"
    )
    assert core_primary['main_value_text'].startswith('x')
    assert core_primary['unique_text']['value_text']
