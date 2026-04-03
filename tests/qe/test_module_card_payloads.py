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


def test_module_card_payloads_build_expected_farming_assist_details():
    payload = build_module_card_payloads(_account_state())
    farming = payload['presets']['Farming']
    armor_assist = farming['armor']['assist']
    assert armor_assist['module_name'] == 'Orbital Augment'
    assert armor_assist['displayed_level'] == 41
    assert armor_assist['level_text'] == 'Lv. 41'
    assert armor_assist['role_bar_label_text'] == 'Assist'
    assert armor_assist['role_bar_detail_text'] == 'Epic | Main 0.01x | Substats 0.10x'
    assert len(armor_assist['effect_slots']) == 8


def test_module_card_payloads_use_qe_unlock_schedule_for_eight_slots():
    assert module_substat_unlock_levels() == (1, 1, 41, 101, 141, 161, 201, 241)
    payload = build_module_card_payloads(_account_state())
    armor_assist = payload['presets']['Farming']['armor']['assist']
    states = [slot['state'] for slot in armor_assist['effect_slots']]
    assert states[:3] == ['populated', 'populated', 'populated']
    assert states[3:] == ['locked', 'locked', 'locked', 'locked', 'locked']
    assert armor_assist['effect_slots'][3]['label_text'] == 'Unlocks at Lv. 101'




def test_module_card_payloads_assist_angle_substat_uses_degree_symbol():
    payload = build_module_card_payloads(_account_state())
    core_assist = payload['presets']['Farming']['core']['assist']
    angle_slot = core_assist['effect_slots'][0]
    assert angle_slot['label_text'] == 'Spotlight - Angle'
    assert angle_slot['value_text'] == '+2.25°'

def test_module_card_payloads_primary_card_uses_module_level_and_cap():
    account_state = _account_state()
    payload = build_module_card_payloads(account_state)
    core_primary = payload['presets']['Farming']['core']['primary']
    expected_level = account_state.modules_inventory['Primordial Collapse'].level
    assert core_primary['module_name'] == 'Primordial Collapse'
    assert core_primary['displayed_level'] == expected_level
    assert core_primary['displayed_level_cap'] == 240
    assert core_primary['level_text'] == f'Lv. {expected_level} / 240'
    assert core_primary['main_value_text'].startswith('x')
    assert core_primary['unique_text']['value_text'] is not None
