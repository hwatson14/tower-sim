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
        line_verification={},
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
        line_verification={},
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
    input_dashboard = {
        'artifact': 'input_dashboard',
        'panels': [
            {
                'panel_id': 'workshop',
                'payload': {
                    'groups': {
                        'utility': [
                            {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': ''},
                            {'name': 'Interest / Wave', 'coin_level': '99', 'coin_value': '99.0', 'max_level': '99', 'max_value': '99.0'},
                        ]
                    }
                },
            }
        ],
    }
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
        line_verification={},
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
    input_dashboard = {
        'artifact': 'input_dashboard',
        'panels': [
            {
                'panel_id': 'workshop',
                'payload': {
                    'groups': {
                        'utility': [
                            {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': ''},
                            {'name': 'Interest / Wave', 'coin_level': '99', 'coin_value': '99.0', 'max_level': '99', 'max_value': '99.0'},
                        ]
                    }
                },
            }
        ],
    }
    query_rows_start = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'display_value': '1',
                    'final_value': 1,
                    'contributors': [
                        {'source_class': 'perks', 'contributor_id': 'perk.start', 'value': 99},
                    ],
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
                        {'source_class': 'perks', 'contributor_id': 'perk.a', 'value': 2},
                        {'source_class': 'perks', 'contributor_id': 'perk.b', 'value': 3},
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
        line_verification={},
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


def test_stats_dashboard_workshop_max_workshop_value_uses_max_progression_workshop_contributors():
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
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop.start', 'value': 1},
                    ],
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
                        {'source_class': 'workshop', 'contributor_id': 'workshop.max', 'value': 7},
                        {'source_class': 'perks', 'contributor_id': 'perk.a', 'value': 3},
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
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )

    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    assert workshop.get('payload', {}).get('artifact') == 'qe_workshop_reconciliation_rows'
    assert workshop.get('payload', {}).get('owner') == 'qe'
    offense_rows = (
        (workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or []
    )
    damage_row = next(row for row in offense_rows if row.get('name') == 'Damage')
    assert damage_row['canonical_row_id'] == 'state::tower.damage'
    assert damage_row['display_label'] == 'Damage'
    assert damage_row['value_format'] == {'value_type': 'scalar', 'display_kind': 'scalar'}
    assert damage_row['start_of_run'] == '1'
    assert damage_row['max_workshop'] == '10'
    assert damage_row['decomposition']['workshop'] == '1'
    assert damage_row['row_status'] == 'resolved'
    assert damage_row['row_notes'] == ''
    assert damage_row['max_workshop_value'] == '7'


def test_stats_dashboard_workshop_module_effects_follow_qe_multiplier_display_for_damage():
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
                    'display_value': '8',
                    'final_value': 8,
                    'value_type': 'damage',
                    'contributors': [
                        {'source_class': 'module_main', 'contributor_id': 'module__cannon__damage__pct@@amp@@primary', 'value': 10.04},
                    ],
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
                    'value_type': 'damage',
                    'contributors': [],
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
        line_verification={},
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
    assert damage_row['module_effects'] == 'x 10'


def test_stats_dashboard_workshop_relics_use_start_of_run_rows():
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
                    'display_value': '8',
                    'final_value': 8,
                    'contributors': [
                        {'source_class': 'relics', 'contributor_id': 'relic.damage_bonus', 'value': 4},
                    ],
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
                    'contributors': [],
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
        line_verification={},
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
    assert damage_row['relics'] == '+ 4'


def test_stats_dashboard_workshop_damage_debug_order_regression():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Damage': {'preset_levels': {'Farming': 5750}}},
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
                    'display_value': '3.43B',
                    'final_value': 3.43e9,
                    'value_type': 'damage',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 58_110_000.0},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__damage__pct', 'value': 0.54},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'display_value': '13.4B',
                    'final_value': 13.4e9,
                    'value_type': 'damage',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 71_100_000.0},
                        {'source_class': 'perks', 'contributor_id': 'perk.damage_tradeoff', 'value': 1.8},
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
        line_verification={},
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

    assert damage_row['workshop_level'] == 5750
    assert damage_row['relics'] == 'x 1.54'
    assert damage_row['perk_effects'] == 'x 1.8'
    assert damage_row['max_progression_value'] == '13.4B'


def test_stats_dashboard_workshop_free_upgrade_enhancement_is_multiplier_and_pct_max_uses_max_row():
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
                'state::tower.free_attack_upgrade_chance_pct': {
                    'display_value': '75.9%',
                    'final_value': 75.9,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__free_attack_upgrade__pct', 'value': 50.0},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.free_upgrades_+.account_state', 'value': 1.15},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.free_attack_upgrade_chance_pct': {
                    'display_value': '111.837%',
                    'final_value': 111.8375,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__free_attack_upgrade__pct', 'value': 50.0},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.free_upgrades_+.account_state', 'value': 1.15},
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
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    utility_rows = (
        (workshop.get('payload', {}).get('sections') or [{}, {}, {}])[2].get('rows') or []
    )
    row = next(item for item in utility_rows if item.get('name') == 'Free Attack Upgrade')
    assert row['enhancement_effects'] == 'x 1.15'
    assert row['max_progression_value'] == '111.838%'


def test_stats_dashboard_workshop_lab_effects_use_start_to_max_delta_for_multiplier_labs():
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
                'state::tower.hp': {
                    'display_value': '10',
                    'final_value': 10.0,
                    'value_type': 'hp',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__health__flat', 'value': 1.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.health.account_state', 'value': 3.04},
                        {'source_class': 'labs', 'contributor_id': 'lab.death_wave_health.account_state', 'value': 0.0},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.hp': {
                    'display_value': '100',
                    'final_value': 100.0,
                    'value_type': 'hp',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__health__flat', 'value': 1.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.health.account_state', 'value': 3.04},
                        {'source_class': 'labs', 'contributor_id': 'lab.death_wave_health.account_state', 'value': 12.5},
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
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    defense_rows = (
        (workshop.get('payload', {}).get('sections') or [{}, {}])[1].get('rows') or []
    )
    health_row = next(item for item in defense_rows if item.get('name') == 'Health')
    assert health_row['lab_effects'] == 'x 12.5'
    assert 'Death Wave Health' in health_row['row_notes']


def test_stats_dashboard_workshop_level_aliases_cover_regen_coin_and_max_recovery():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Health Regen': {'preset_levels': {'Farming': 101}},
            'Coin / Kill Bonus': {'preset_levels': {'Farming': 202}},
            'Coin / Wave': {'preset_levels': {'Farming': 303}},
            'Max Amount': {'preset_levels': {'Farming': 404}},
        },
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
                'state::tower.regen': {'display_value': '1', 'final_value': 1},
                'state::economy.coins_per_kill_bonus': {'display_value': '1', 'final_value': 1},
                'state::economy.coins_per_wave': {'display_value': '1', 'final_value': 1},
                'state::tower.max_recovery_multiplier': {'display_value': '1', 'final_value': 1},
            }
        }
    }
    query_rows_max = {'Farming': {'rows': dict(query_rows_start['Farming']['rows'])}}
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Regen']['workshop_level'] == 101
    assert by_name['Coins / Kill Bonus']['workshop_level'] == 202
    assert by_name['Coins / Wave']['workshop_level'] == 303
    assert by_name['Max Recovery']['workshop_level'] == 404


def test_stats_dashboard_derived_panel_includes_uw_damage_and_e_metrics():
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
                'state::tower.ultimate_damage_multiplier': {'display_value': 'x2', 'final_value': 2, 'value_type': 'multiplier'},
                'derived::ehp': {'display_value': '10', 'final_value': 10},
                'derived::eecon': {'display_value': '20', 'final_value': 20},
                'derived::edamage': {'display_value': '30', 'final_value': 30},
            }
        }
    }
    query_rows_max = {'Farming': {'rows': dict(query_rows_start['Farming']['rows'])}}
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    derived_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'derived'
    )
    labels = [row.get('label') for row in (derived_panel.get('payload', {}).get('rows') or [])]
    canonical_row_ids = [row.get('canonical_row_id') for row in (derived_panel.get('payload', {}).get('rows') or [])]
    assert 'Wall HP (Pre-Fort)' in labels
    assert 'Ultimate Weapon Damage' in labels
    assert 'eHP' in labels
    assert 'eEcon' in labels
    assert 'eDamage' in labels
    assert 'derived::wall.hp_pre_fort' in canonical_row_ids
    assert 'derived::wall.hp_final' in canonical_row_ids


def test_stats_dashboard_canonical_row_ids_disambiguate_workshop_rows():
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
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={
            'Farming': {
                'rows': {
                    'state::tower.crit_multiplier': {'display_value': 'x174', 'final_value': 174, 'value_type': 'multiplier'},
                    'state::tower.regen': {'display_value': '44T', 'final_value': 44, 'value_type': 'scalar'},
                    'state::tower.package_chance_pct': {'display_value': '79%', 'final_value': 79, 'value_type': 'pct'},
                    'state::tower.shockwave_interval_seconds': {'display_value': '14', 'final_value': 14, 'value_type': 'seconds'},
                    'state::wall.hp': {'display_value': '132T', 'final_value': 132, 'value_type': 'hp'},
                }
            }
        },
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_label = {row.get('display_label'): row for row in rows}
    assert by_label['Crit Multiplier']['canonical_row_id'] == 'workshop::tower.crit_multiplier'
    assert by_label['Regen']['canonical_row_id'] == 'workshop::tower.regen'
    assert by_label['Package Chance']['canonical_row_id'] == 'workshop::tower.package_chance_pct'
    assert by_label['Shockwave Interval']['canonical_row_id'] == 'workshop::tower.shockwave_interval_seconds'
    assert by_label['Wall Health']['canonical_row_id'] == 'workshop::wall.health'


def test_stats_dashboard_does_not_backfill_missing_rows_from_line_verification():
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
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={'Farming': {'rows': {}}},
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={
            'state::wall.rebuild_seconds': {'final_value': 150.0, 'unit': 'seconds', 'status': 'resolved'},
            'state::economy.interest_per_wave_pct': {'final_value': 132.0, 'unit': 'pct', 'status': 'resolved'},
            'state::wall.thorns_damage_pct': {'final_value': 15.0, 'unit': 'pct', 'status': 'resolved'},
        },
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Wall Rebuild']['start_of_run_value'] == '—'
    assert by_name['Interest / Wave']['start_of_run_value'] == '—'

    derived_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'derived'
    )
    derived_rows = {row.get('label'): row for row in (derived_panel.get('payload', {}).get('rows') or [])}
    assert derived_rows['Wall Thorns']['display_value'] is None
    assert derived_rows['Wall Thorns']['status'] is None


def test_stats_dashboard_preserves_unresolved_query_rows_without_line_verification_backfill():
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
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={
            'Farming': {
                'rows': {
                    'state::wall.rebuild_seconds': {
                        'display_value': None,
                        'final_value': None,
                        'value_type': 'seconds',
                        'status': 'mapped_not_resolved',
                        'contributors': [],
                    },
                    'state::economy.interest_per_wave_pct': {
                        'display_value': None,
                        'final_value': None,
                        'value_type': 'pct',
                        'status': 'mapped_not_resolved',
                        'contributors': [],
                    },
                }
            }
        },
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={
            'state::wall.rebuild_seconds': {'final_value': 150.0, 'unit': 'seconds', 'status': 'resolved'},
            'state::economy.interest_per_wave_pct': {'final_value': 132.0, 'unit': 'pct', 'status': 'resolved'},
        },
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Wall Rebuild']['row_status'] == 'mapped_not_resolved'
    assert by_name['Interest / Wave']['row_status'] == 'mapped_not_resolved'
    assert by_name['Wall Rebuild']['start_of_run_value'] == '—'
    assert by_name['Interest / Wave']['start_of_run_value'] == '—'


def test_stats_dashboard_workshop_does_not_backfill_from_input_dashboard_when_qe_rows_are_missing():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Wall Rebuild': {'preset_levels': {'Farming': 250}},
            'Interest / Wave': {'preset_levels': {'Farming': 99}},
        },
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {
            'workshop': {
                'groups': {
                    'utility': [
                        {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': ''},
                        {'name': 'Interest / Wave', 'coin_level': '99', 'coin_value': '99.0', 'max_level': '99', 'max_value': '99.0'},
                    ]
                }
            }
        },
        'uw_tracks': {},
        'ultimate_weapons': {},
    }
    input_dashboard = {
        'artifact': 'input_dashboard',
        'panels': [
            {
                'panel_id': 'workshop',
                'payload': {
                    'groups': {
                        'utility': [
                            {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': ''},
                            {'name': 'Interest / Wave', 'coin_level': '99', 'coin_value': '99.0', 'max_level': '99', 'max_value': '99.0'},
                        ]
                    }
                },
            }
        ],
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={'Farming': {'rows': {}}},
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Wall Rebuild']['row_status'] == 'missing'
    assert by_name['Wall Rebuild']['row_notes'] == 'Missing QE query row.'
    assert by_name['Wall Rebuild']['start_of_run_value'] == '—'
    assert by_name['Wall Rebuild']['max_progression_value'] == '—'
    assert by_name['Interest / Wave']['start_of_run_value'] == '—'
    assert by_name['Interest / Wave']['max_progression_value'] == '—'
