from __future__ import annotations

import json
from pathlib import Path

from app.publication import _build_input_dashboard_payload, _build_stats_dashboard_payload

ROOT = Path(__file__).resolve().parents[2]


def test_stats_dashboard_contract_and_panel_types():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    query_rows_start = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))

    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )

    assert payload['artifact'] == 'stats_dashboard.json'
    assert payload['schema_version'] == 1
    assert payload['selected_state_mode'] == 'max_progression'
    panel_pairs = [(panel.get('panel_id'), panel.get('panel_type')) for panel in (payload.get('panels') or [])]
    assert panel_pairs == [
        ('workshop', 'workshop_stat_table'),
        ('derived', 'resolved_stat_section'),
        ('uw_resolved', 'resolved_uw_section'),
        ('modules_context', 'context_modules'),
        ('cards_context', 'context_cards'),
        ('bots_context', 'context_track_table'),
    ]


def test_stats_dashboard_variants_include_state_modes():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={},
        query_rows_max_progression={},
        ep_compare_publishable={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    variants = payload.get('variants') or {}
    farming_variant = variants.get('Farming') or {}
    assert {'start_of_run', 'max_progression'}.issubset(set(farming_variant.keys()))


def test_stats_dashboard_variants_use_rows_for_each_preset():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': [], 'Tourney': []},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {},
        'uw_tracks': {},
        'ultimate_weapons': {},
    }
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    query_rows_start = {
        'Farming': {'rows': {'state::tower.damage': {'display_value': '1', 'final_value': 1}}},
        'Tourney': {'rows': {'state::tower.damage': {'display_value': '2', 'final_value': 2}}},
    }
    query_rows_max = {
        'Farming': {'rows': {'state::tower.damage': {'display_value': '10', 'final_value': 10}}},
        'Tourney': {'rows': {'state::tower.damage': {'display_value': '20', 'final_value': 20}}},
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )

    tourney_workshop = next(
        panel for panel in payload['variants']['Tourney']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = (
        (tourney_workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or []
    )
    damage_row = next(row for row in offense_rows if row.get('name') == 'Damage')
    assert damage_row['max_progression_value'] == '20'


def test_stats_dashboard_workshop_perk_effects_use_max_progression_rows():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {},
        'uw_tracks': {},
        'ultimate_weapons': {},
    }
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    query_rows_start = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'display_value': '1',
                    'final_value': 1,
                    'contributors': [],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'display_value': '10',
                    'final_value': 10,
                    'contributors': [
                        {'source_class': 'perk', 'contributor_id': 'perk.a', 'value': 2},
                        {'source_class': 'perk', 'contributor_id': 'perk.b', 'value': 3},
                    ],
                }
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )

    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = (
        (workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or []
    )
    damage_row = next(row for row in offense_rows if row.get('name') == 'Damage')
    assert damage_row['perk_effects'] == '+ 5'
