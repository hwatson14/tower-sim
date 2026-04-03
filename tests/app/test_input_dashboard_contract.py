from __future__ import annotations

import json
from pathlib import Path

from app.publication import _build_input_dashboard_payload

ROOT = Path(__file__).resolve().parents[2]


def test_input_dashboard_panel_contract_and_no_placeholder_headers():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    payload = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    panel_pairs = [(panel.get('panel_id'), panel.get('panel_type')) for panel in (payload.get('panels') or [])]
    assert panel_pairs == [
        ('labs', 'labs_bucket_grid'),
        ('workshop', 'grouped_workshop_table'),
        ('workshop_enhancements', 'grouped_enhancement_table'),
        ('ultimate_weapons', 'uw_track_table'),
        ('cards', 'cards_inventory_and_preset'),
        ('bots', 'track_table'),
        ('relics', 'simple_bonus_table'),
        ('modules', 'module_slot_stack'),
        ('vault', 'simple_bonus_table'),
        ('guardians', 'track_table'),
        ('themes_and_songs', 'simple_metric_panel'),
    ]

    serialized = json.dumps(payload)
    assert 'C1' not in serialized
    assert 'A1' not in serialized
    assert 'column_1' not in serialized

    workshop_panel = next(panel for panel in payload['panels'] if panel['panel_id'] == 'workshop')
    grouped_rows = []
    for group_name in ['offense', 'defense', 'utility']:
        grouped_rows.extend(((workshop_panel.get('payload') or {}).get('groups') or {}).get(group_name) or [])
    if grouped_rows:
        assert {'unlock', 'name', 'coin_level', 'coin_value', 'max_level', 'max_value'}.issubset(grouped_rows[0].keys())

    uw_panel = next(panel for panel in payload['panels'] if panel['panel_id'] == 'ultimate_weapons')
    uw_rows = (uw_panel.get('payload') or {}).get('rows') or []
    if uw_rows:
        assert {'lab', 'module', 'perk', 'final'}.issubset(uw_rows[0].keys())


def test_modules_panel_uses_module_card_payload_shape_when_available():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    module_payloads = {'presets': {'Farming': {'cannon': {'primary': {'module_name': 'ACP'}}}}}
    payload = _build_input_dashboard_payload(account_state, {}, module_card_payloads=module_payloads)
    modules_panel = next(panel for panel in payload['panels'] if panel['panel_id'] == 'modules')
    assert 'cannon' in (modules_panel.get('payload') or {}).get('slots', {})
