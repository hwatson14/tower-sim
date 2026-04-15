from __future__ import annotations

import json
from pathlib import Path

from app.publication import _build_input_dashboard_payload, _build_stats_dashboard_payload
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.query_module_policy import build_module_card_payloads
from qe.workshop_stat_rows import build_workshop_reconciliation_row, _strict_reconciliation_audit

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
        ('ultimate_weapons', 'workshop_stat_table'),
        ('bots', 'workshop_stat_table'),
        ('guardians', 'workshop_stat_table'),
        ('modules', 'context_modules'),
    ]
    secondary_pairs = [(panel.get('panel_id'), panel.get('panel_type')) for panel in (payload.get('secondary_panels') or [])]
    assert secondary_pairs == [
        ('offense_resolved', 'resolved_stat_section'),
        ('defense_resolved', 'resolved_stat_section'),
        ('utility_resolved', 'resolved_stat_section'),
        ('wall_economy_resolved', 'resolved_stat_section'),
        ('cards_resolved', 'resolved_stat_section'),
        ('bots_resolved', 'resolved_stat_section'),
        ('guardians_resolved', 'resolved_stat_section'),
        ('modules_resolved', 'resolved_stat_section'),
        ('uw_stats_resolved', 'resolved_stat_section'),
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


def test_stats_dashboard_publishes_contract_manifest_and_domain_acceptance_gate():
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

    contract = payload.get('contract') or {}
    assert contract.get('owner') == 'qe'
    assert contract.get('row_contract_model') == 'qe_workshop_reconciliation_rows'
    assert contract.get('no_backfill_sources') == ['line_verification', 'input_dashboard']
    assert 'mapped_not_resolved' in set(contract.get('row_status_semantics') or [])

    panel_acceptance = {entry.get('panel_id'): entry for entry in (contract.get('panel_acceptance') or [])}
    assert panel_acceptance['workshop']['acceptance_state'] == 'active'
    assert panel_acceptance['workshop']['authority'] == 'qe_query_rows'
    assert panel_acceptance['workshop']['product_tier'] == 'primary'
    assert panel_acceptance['ultimate_weapons']['acceptance_state'] == 'active'
    assert panel_acceptance['ultimate_weapons']['product_tier'] == 'primary'
    assert panel_acceptance['bots']['acceptance_state'] == 'active'
    assert panel_acceptance['bots']['product_tier'] == 'primary'
    assert panel_acceptance['guardians']['acceptance_state'] == 'active'
    assert panel_acceptance['guardians']['product_tier'] == 'primary'
    assert panel_acceptance['modules']['acceptance_state'] == 'active'
    assert panel_acceptance['modules']['product_tier'] == 'primary'
    assert panel_acceptance['offense_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['defense_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['utility_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['wall_economy_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['cards_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['bots_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['guardians_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['modules_resolved']['acceptance_state'] == 'secondary'
    assert panel_acceptance['uw_stats_resolved']['acceptance_state'] == 'secondary'


def test_stats_dashboard_primary_uw_operator_table_uses_workshop_shape():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {},
        'uw_tracks': {
            'Golden Tower': [
                {'track_name': 'Cooldown', 'level': 2, 'resolved_value': 180.0},
                {'track_name': 'Duration', 'level': 3, 'resolved_value': 42.0},
            ],
        },
        'ultimate_weapons': {'Golden Tower': {'unlocked': True}},
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
                    'state::uw.golden_tower.cooldown_seconds': {
                        'display_value': '180',
                        'final_value': 180.0,
                        'value_type': 'seconds',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'ultimate_weapons', 'value': 180.0}],
                    },
                    'state::uw.golden_tower.duration_seconds': {
                        'display_value': '42',
                        'final_value': 42.0,
                        'value_type': 'seconds',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'ultimate_weapons', 'value': 42.0}],
                    },
                }
            }
        },
        query_rows_max_progression={
            'Farming': {
                'rows': {
                    'state::uw.golden_tower.cooldown_seconds': {'display_value': '160', 'final_value': 160.0, 'value_type': 'seconds', 'status': 'resolved'},
                    'state::uw.golden_tower.duration_seconds': {'display_value': '48', 'final_value': 48.0, 'value_type': 'seconds', 'status': 'resolved'},
                }
            }
        },
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    uw_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'ultimate_weapons'
    )
    columns = [column.get('label') for column in (uw_panel.get('payload', {}).get('columns') or [])]
    assert columns == [
        'Track',
        'Stone Level',
        'Stone Value',
        'Lab',
        'Module',
        'Start of Run',
        'Perk',
        'Max Progression',
        'Other',
        'Recon',
    ]
    sections = {section.get('title'): section for section in (uw_panel.get('payload', {}).get('sections') or [])}
    rows_by_name = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    assert rows_by_name['Cooldown']['workshop_level'] == '2'
    assert rows_by_name['Cooldown']['stone_value'] == '180'
    assert rows_by_name['Cooldown']['start_of_run_value'] == '180'
    assert rows_by_name['Cooldown']['max_progression_value'] == '160'
    assert rows_by_name['Duration']['workshop_level'] == '3'
    assert rows_by_name['Duration']['start_of_run_value'] == '42'


def test_stats_dashboard_primary_uw_operator_table_lists_all_uw_and_appends_uw_plus():
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

    uw_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'ultimate_weapons')
    sections = list((uw_panel.get('payload', {}).get('sections') or []))
    assert [section.get('title') for section in sections] == [
        'Chain Lightning',
        'Smart Missiles',
        'Death Wave',
        'Chrono Field',
        'Inner Land Mines',
        'Golden Tower',
        'Poison Swamp',
        'Black Hole',
        'Spotlight',
    ]
    chain_rows = [row.get('name') for row in (sections[0].get('rows') or [])]
    assert chain_rows[:4] == ['Damage', 'Quantity', 'Chance', 'UW+ Smite']


def test_stats_dashboard_primary_uw_operator_table_wires_module_other_and_recon_fields():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    stat_inputs_payload = [
        {
            'destination_id': 'state::uw.chain_lightning.damage_multiplier',
            'source_family': 'module_unique',
            'source_name': 'Dimension Core',
            'value': 2.25,
        },
        {
            'destination_id': 'state::uw.chain_lightning.max_enemy_damage_reduction_pct',
            'source_family': 'module_unique',
            'source_name': 'Chain Thunder',
            'value': 22.0,
        },
        {
            'destination_id': 'state::uw.golden_tower.duration_seconds',
            'source_family': 'lab',
            'source_name': 'Golden Tower Duration Lab',
            'value': 20.0,
        },
        {
            'destination_id': 'state::uw.black_hole.duration_seconds',
            'source_family': 'module_unique',
            'source_name': 'Multiverse Nexus',
            'value': 4.0,
        },
    ]
    query_rows_start_of_run = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max_progression = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start_of_run,
        query_rows_max_progression=query_rows_max_progression,
        stat_inputs_payload=stat_inputs_payload,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    uw_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'ultimate_weapons')
    sections = {section.get('title'): section for section in (uw_panel.get('payload', {}).get('sections') or [])}
    chain_rows = {row.get('name'): row for row in (sections['Chain Lightning'].get('rows') or [])}
    golden_rows = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    black_hole_rows = {row.get('name'): row for row in (sections['Black Hole'].get('rows') or [])}

    assert chain_rows['Damage']['module_effects'] == 'x2.25'
    assert chain_rows['Damage']['other'].startswith('Chain Thunder ')
    assert golden_rows['Duration']['lab_effects'] == '20'
    assert golden_rows['Duration']['reconciliation_status'] == 'green'
    assert black_hole_rows['Duration']['module_effects'] == '4'
    assert black_hole_rows['Duration']['reconciliation_status'] == 'green'


def test_stats_dashboard_primary_bot_operator_table_uses_start_of_run_only_surface():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    query_rows_start_of_run = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max_progression = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start_of_run,
        query_rows_max_progression=query_rows_max_progression,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    bot_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'bots')
    sections = {section.get('title'): section for section in (bot_panel.get('payload', {}).get('sections') or [])}
    amplify_rows = {row.get('name'): row for row in (sections['Amplify'].get('rows') or [])}
    golden_rows = {row.get('name'): row for row in (sections['Golden'].get('rows') or [])}

    assert [section.get('title') for section in (bot_panel.get('payload', {}).get('sections') or [])] == ['Amplify', 'Flame', 'Golden', 'Thunder']
    assert [row.get('name') for row in (sections['Amplify'].get('rows') or [])] == ['Bonus', 'Cooldown', 'Duration', 'Range']
    assert amplify_rows['Range']['medal_level'] == '0'
    assert amplify_rows['Range']['medals_spent'] == '0'
    assert amplify_rows['Range']['medal_value'] == '25m'
    assert amplify_rows['Range']['start_of_run_value'] == '34m'
    assert amplify_rows['Range']['module_effects'] == '—'
    assert amplify_rows['Range']['reconciliation_status'] == 'amber'
    assert golden_rows['Range']['start_of_run_value'] == '59m'
    assert golden_rows['Range']['reconciliation_status'] == 'amber'


def test_stats_dashboard_primary_modules_panel_publishes_grouped_summary_rows():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    query_rows_start = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))
    bundle = load_inputs(ids_path=ROOT / 'input' / 'imports' / 'ids.csv')
    live_account_state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    module_card_payloads = build_module_card_payloads(live_account_state)
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads=module_card_payloads,
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression=query_rows_max,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    modules_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'modules')
    summary_rows = modules_panel.get('payload', {}).get('summary_rows') or []
    by_key = {(row.get('group'), row.get('label')): (row.get('values') or {}) for row in summary_rows}

    assert modules_panel.get('panel_type') == 'context_modules'
    assert by_key[('', 'Max Level')]['cannon'] == '220'
    assert by_key[('', 'Assist %')]['armor'] == '1%'
    assert by_key[('Primary', 'Module')]['generator'] == 'Singularity Harness'
    assert by_key[('Assist', 'Module')]['cannon'] == '—'
    assert by_key[('Current', 'Multiplier')]['core'] == 'x14.01'
    assert by_key[('Recon', 'Recon')]['generator'] == 'green'


def test_stats_dashboard_primary_bot_and_guardian_operator_tables_use_workshop_shape():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {
            'Bots': [
                ['Golden Bot', '', 'Duration', '26.5', '13 | 26.5s | Cost 580 ? | Next 620 ?'],
                ['', '', 'Cooldown', '111', '03 | 111s | Cost 180 ? | Next 220 ?'],
                ['', '', 'Bonus', '6.6', '23 | x6.6 | Cost 980 ? | Next 1020 ?'],
                ['true', 'Unlocked', 'Range', '50', '15 | 50m | Cost 660 ? | Maxed'],
            ],
        },
        'uw_tracks': {},
        'ultimate_weapons': {},
        'bot_upgrade_tracks': {},
        'raw_sections': {
            'Bots': [
                ['Golden Bot', '', 'Duration', '26.5', '13 | 26.5s | Cost 580 ? | Next 620 ?'],
                ['', '', 'Cooldown', '111', '03 | 111s | Cost 180 ? | Next 220 ?'],
                ['', '', 'Bonus', '6.6', '23 | x6.6 | Cost 980 ? | Next 1020 ?'],
                ['true', 'Unlocked', 'Range', '50', '15 | 50m | Cost 660 ? | Maxed'],
            ],
            'Guardians': [
                ['Attack', '', 'Percentage', '0.01', '00 | 1% | Cost 0 ? | Next 25 ?'],
                ['', '', 'Cooldown', '120', '00 | 120s | Cost 0 ? | Next 1 ?'],
                ['true', 'Unlocked', 'Targets', '1', '00 | 1 | Cost 0 ? | Next 100 ?'],
            ],
        },
        'guardian_tracks': {
            'Attack': [
                {'track_name': 'Percentage', 'level': 0, 'resolved_value': 0.01},
                {'track_name': 'Cooldown', 'level': 1, 'resolved_value': 120.0},
                {'track_name': 'Targets', 'level': 0, 'resolved_value': 1.0},
            ],
        },
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
                    'state::bot.golden.cooldown_seconds': {
                        'display_value': '80',
                        'final_value': 80.0,
                        'value_type': 'seconds',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'bots', 'value': 80.0}],
                    },
                    'state::bot.golden.duration_seconds': {
                        'display_value': '32.5',
                        'final_value': 32.5,
                        'value_type': 'seconds',
                        'status': 'resolved',
                        'contributors': [
                            {'source_class': 'bots', 'value': 26.5},
                            {'source_class': 'labs', 'value': 6.0, 'display_value': '6'},
                        ],
                    },
                    'state::bot.golden.bonus_multiplier': {
                        'display_value': 'x6.6',
                        'final_value': 6.6,
                        'value_type': 'multiplier',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'bots', 'value': 6.6}],
                    },
                    'state::bot.golden.range_m': {
                        'display_value': '59',
                        'final_value': 59.0,
                        'value_type': 'm',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'bots', 'value': 50.0}],
                    },
                    'state::bot.golden.effective_range_m': {
                        'display_value': '110.39',
                        'final_value': 110.39,
                        'value_type': 'distance',
                        'status': 'resolved',
                    },
                    'state::bot.global.range_bonus_m': {
                        'display_value': '15',
                        'final_value': 15.0,
                        'value_type': 'm',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'module_unique', 'value': 15.0, 'display_value': '15'}],
                    },
                    'state::guardian.attack.cooldown_seconds': {
                        'display_value': '120',
                        'final_value': 120.0,
                        'value_type': 'seconds',
                        'status': 'resolved',
                        'contributors': [{'source_class': 'guardians', 'value': 120.0}],
                    },
                }
            }
        },
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    bot_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'bots'
    )
    guardian_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'guardians'
    )
    bot_sections = {section.get('title'): section for section in (bot_panel.get('payload', {}).get('sections') or [])}
    guardian_sections = {section.get('title'): section for section in (guardian_panel.get('payload', {}).get('sections') or [])}
    bot_rows = {row.get('name'): row for row in (bot_sections['Golden'].get('rows') or [])}
    guardian_rows = {row.get('name'): row for row in (guardian_sections['Attack'].get('rows') or [])}
    bot_columns = [column.get('label') for column in (bot_panel.get('payload', {}).get('columns') or [])]
    guardian_columns = [column.get('label') for column in (guardian_panel.get('payload', {}).get('columns') or [])]
    assert bot_columns == ['Track', 'Level', 'Cumulative Medals Spent', 'Value', 'Lab', 'Module', 'Start of Run', 'Recon']
    assert guardian_columns == ['Track', 'Level', 'Cumulative Bits Spent', 'Value', 'Start of Run', 'Recon']
    assert [row.get('name') for row in (bot_sections['Golden'].get('rows') or [])] == ['Bonus', 'Cooldown', 'Duration', 'Range']
    assert [row.get('name') for row in (guardian_sections['Attack'].get('rows') or [])] == ['Percentage', 'Cooldown', 'Targets']
    assert bot_rows['Cooldown']['medal_level'] == '3'
    assert bot_rows['Cooldown']['medals_spent'] == '180'
    assert bot_rows['Cooldown']['medal_value'] == '111s'
    assert bot_rows['Cooldown']['start_of_run_value'] == '80s'
    assert bot_rows['Duration']['lab_effects'] == '+ 6'
    assert bot_rows['Range']['module_effects'] == '—'
    assert bot_rows['Range']['reconciliation_status'] == 'amber'
    assert guardian_rows['Cooldown']['bit_level'] == '0'
    assert guardian_rows['Cooldown']['bits_spent'] == '0'
    assert guardian_rows['Cooldown']['bit_value'] == '120s'
    assert guardian_rows['Cooldown']['start_of_run_value'] == '120s'
    assert guardian_rows['Cooldown']['reconciliation_status'] == 'green'


def test_stats_dashboard_resolved_sections_publish_offense_defense_and_utility_rows():
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
                'state::tower.damage': {'display_value': '111', 'final_value': 111.0, 'value_type': 'damage', 'status': 'resolved', 'contributors': [{'source_class': 'workshop', 'value': 111.0}]},
                'state::tower.hp': {'display_value': '222', 'final_value': 222.0, 'value_type': 'hp', 'status': 'resolved', 'contributors': [{'source_class': 'workshop', 'value': 222.0}]},
                'state::economy.cash_per_wave': {'display_value': '333', 'final_value': 333.0, 'value_type': 'scalar', 'status': 'resolved', 'contributors': [{'source_class': 'workshop', 'value': 333.0}]},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    panels = {panel.get('panel_id'): panel for panel in payload['secondary_variants']['Farming']['start_of_run']}
    offense_rows = {row.get('label'): row for row in (panels['offense_resolved'].get('payload', {}).get('rows') or [])}
    defense_rows = {row.get('label'): row for row in (panels['defense_resolved'].get('payload', {}).get('rows') or [])}
    utility_rows = {row.get('label'): row for row in (panels['utility_resolved'].get('payload', {}).get('rows') or [])}

    assert panels['offense_resolved'].get('payload', {}).get('owner') == 'qe'
    assert offense_rows['Damage']['display_value'] == '111'
    assert offense_rows['Attack Speed']['status'] == 'missing'
    assert defense_rows['Health']['display_value'] == '222'
    assert defense_rows['Wall Rebuild']['status'] == 'missing'
    assert utility_rows['Cash / Wave']['display_value'] == '333'
    assert utility_rows['Interest / Wave']['status'] == 'missing'


def test_stats_dashboard_resolved_sections_publish_wall_and_derived_rows():
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
                'state::wall.hp': {'display_value': '444', 'final_value': 444.0, 'value_type': 'hp', 'status': 'resolved', 'contributors': [{'source_class': 'workshop', 'value': 444.0}]},
                'state::wall.regen': {'display_value': '555', 'final_value': 555.0, 'value_type': 'hp_per_second', 'status': 'resolved', 'contributors': [{'source_class': 'workshop', 'value': 555.0}]},
                'derived::ehp': {'display_value': '666', 'final_value': 666.0, 'value_type': 'scalar', 'status': 'resolved', 'contributors': []},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    panels = {panel.get('panel_id'): panel for panel in payload['secondary_variants']['Farming']['start_of_run']}
    wall_rows = {row.get('label'): row for row in (panels['wall_economy_resolved'].get('payload', {}).get('rows') or [])}

    assert panels['wall_economy_resolved'].get('payload', {}).get('owner') == 'qe'
    assert wall_rows['Wall HP']['display_value'] == '444'
    assert wall_rows['Wall Regen']['display_value'] == '555'
    assert wall_rows['eHP']['display_value'] == '666'
    assert wall_rows['Wall Thorns']['status'] == 'missing'


def test_stats_dashboard_resolved_sections_publish_cards_and_uw_rows():
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
                'state::cards.plasma_cannon.effect_pct': {'display_value': '27%', 'final_value': 27.0, 'value_type': 'pct', 'status': 'resolved', 'contributors': [{'source_class': 'cards', 'value': 27.0}]},
                'state::cards.super_tower.bonus_multiplier': {'display_value': 'x1.5', 'final_value': 1.5, 'value_type': 'multiplier', 'status': 'resolved', 'contributors': [{'source_class': 'cards', 'value': 1.5}]},
                'state::uw.chain_lightning.damage_multiplier': {'display_value': 'x12', 'final_value': 12.0, 'value_type': 'multiplier', 'status': 'resolved', 'contributors': [{'source_class': 'uw', 'value': 12.0}]},
                'state::uw.chrono_field.slow_pct': {'display_value': '38%', 'final_value': 38.0, 'value_type': 'pct', 'status': 'resolved', 'contributors': [{'source_class': 'uw', 'value': 38.0}]},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    panels = {panel.get('panel_id'): panel for panel in payload['secondary_variants']['Farming']['start_of_run']}
    card_rows = {row.get('label'): row for row in (panels['cards_resolved'].get('payload', {}).get('rows') or [])}
    uw_rows = {row.get('label'): row for row in (panels['uw_stats_resolved'].get('payload', {}).get('rows') or [])}

    assert panels['cards_resolved'].get('payload', {}).get('owner') == 'qe'
    assert card_rows['Plasma Cannon']['display_value'] == '27%'
    assert card_rows['Super Tower']['display_value'] == 'x1.5'
    assert card_rows['Ultimate Crit']['status'] == 'missing'

    assert panels['uw_stats_resolved'].get('payload', {}).get('owner') == 'qe'
    assert uw_rows['Chain Lightning Damage']['display_value'] == 'x12'
    assert uw_rows['Chrono Field Speed Reduction']['display_value'] == '38%'
    assert uw_rows['Golden Tower Cooldown']['status'] == 'missing'


def test_stats_dashboard_resolved_sections_publish_bot_and_guardian_rows():
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
                'state::bot.golden.cooldown_seconds': {'display_value': '80s', 'final_value': 80.0, 'value_type': 'seconds', 'status': 'resolved', 'contributors': [{'source_class': 'bot', 'value': 80.0}]},
                'state::bot.golden.effective_range_m': {'display_value': '47.5m', 'final_value': 47.5, 'value_type': 'distance_m', 'status': 'resolved', 'contributors': [{'source_class': 'bot', 'value': 47.5}]},
                'state::guardian.attack.cooldown_seconds': {'display_value': '120s', 'final_value': 120.0, 'value_type': 'seconds', 'status': 'resolved', 'contributors': [{'source_class': 'guardian', 'value': 120.0}]},
                'state::guardian.fetch.find_chance_pct': {'display_value': '37%', 'final_value': 37.0, 'value_type': 'pct', 'status': 'resolved', 'contributors': [{'source_class': 'guardian', 'value': 37.0}]},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    panels = {panel.get('panel_id'): panel for panel in payload['secondary_variants']['Farming']['start_of_run']}
    bot_rows = {row.get('label'): row for row in (panels['bots_resolved'].get('payload', {}).get('rows') or [])}
    guardian_rows = {row.get('label'): row for row in (panels['guardians_resolved'].get('payload', {}).get('rows') or [])}

    assert panels['bots_resolved'].get('payload', {}).get('owner') == 'qe'
    assert bot_rows['Golden Cooldown']['display_value'] == '80'
    assert bot_rows['Golden Effective Range']['display_value'] == '47.5'
    assert bot_rows['Amplify Bonus']['status'] == 'missing'

    assert panels['guardians_resolved'].get('payload', {}).get('owner') == 'qe'
    assert guardian_rows['Attack Cooldown']['display_value'] == '120'
    assert guardian_rows['Fetch Find Chance']['display_value'] == '37%'
    assert guardian_rows['Summon Cash Bonus']['status'] == 'missing'


def test_stats_dashboard_resolved_sections_publish_module_rows():
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
                'state::module.orbital_augment.electron_count': {'display_value': '5', 'final_value': 5.0, 'value_type': 'count', 'status': 'resolved', 'contributors': [{'source_class': 'module', 'value': 5.0}]},
                'state::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct': {'display_value': '12%', 'final_value': 12.0, 'value_type': 'pct', 'status': 'resolved', 'contributors': [{'source_class': 'module', 'value': 12.0}]},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    panels = {panel.get('panel_id'): panel for panel in payload['secondary_variants']['Farming']['start_of_run']}
    module_rows = {row.get('label'): row for row in (panels['modules_resolved'].get('payload', {}).get('rows') or [])}

    assert panels['modules_resolved'].get('payload', {}).get('owner') == 'qe'
    assert module_rows['Orbital Augment Electrons']['display_value'] == '5'
    assert module_rows['BHD Extra Coin / Free Upgrade']['display_value'] == '12%'
    assert module_rows['Primordial Collapse BH Damage Reduction']['status'] == 'missing'


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
    assert damage_row['module_effects'] == 'x 10.04'


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
    assert row['max_progression_value'] == '111.84%'


def test_stats_dashboard_workshop_mixed_modifier_totals_are_built_from_visible_components():
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
                        {'source_class': 'cards', 'contributor_id': 'card.free_attack_upgrade', 'value': 10.0},
                        {'source_class': 'relics', 'contributor_id': 'relic.free_attack_upgrade', 'value': 6.0},
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
                        {'source_class': 'cards', 'contributor_id': 'card.free_attack_upgrade', 'value': 10.0},
                        {'source_class': 'relics', 'contributor_id': 'relic.free_attack_upgrade', 'value': 6.0},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.free_upgrades_+.account_state', 'value': 1.15},
                        {'source_class': 'perk_effect', 'contributor_id': 'perk.free_upgrade', 'value': 31.25, 'input_value_type': 'pct'},
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
    assert row['card_effects'] == '+ 10%'
    assert row['relics'] == '+ 6%'
    assert row['enhancement_effects'] == 'x 1.15'
    assert row['start_of_run_modifier_total'] == '+ 25.9%'
    assert row['perk_effects'] == '+ 31.25%'
    assert row['other'] == '—'
    assert row['max_progression_modifier_total'] == '+ 31.25%'


def test_stats_dashboard_workshop_lab_effects_use_start_of_run_values_for_multiplier_labs():
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
    assert health_row['lab_effects'] == 'x 3.04'
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


def test_stats_dashboard_workshop_panel_includes_derived_section_rows():
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
    workshop_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    derived_section = next(
        section for section in (workshop_panel.get('payload', {}).get('sections') or [])
        if section.get('title') == 'Derived'
    )
    labels = [row.get('name') for row in (derived_section.get('rows') or [])]
    canonical_row_ids = [row.get('canonical_row_id') for row in (derived_section.get('rows') or [])]
    assert 'Wall HP (Pre-Fort)' in labels
    assert 'Ultimate Weapon Damage' in labels
    assert 'eHP' in labels
    assert 'eEcon' in labels
    assert 'eDamage' in labels
    assert 'derived::wall.hp_pre_fort' in canonical_row_ids
    assert 'derived::wall.hp_final' in canonical_row_ids


def test_stats_dashboard_workshop_panel_includes_extended_attack_rows_from_layout_contract():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Range': {'preset_levels': {'Farming': 69}},
            'Damage / Meter': {'preset_levels': {'Farming': 14}},
            'Rapid Fire Chance': {'preset_levels': {'Farming': 85}},
            'Rapid Fire Duration': {'preset_levels': {'Farming': 84}},
            'Bounce Shot Range': {'preset_levels': {'Farming': 60}},
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
                'state::tower.range_m': {'display_value': '69.5', 'final_value': 69.5, 'value_type': 'distance', 'contributors': []},
                'state::tower.damage_per_meter_multiplier': {'display_value': 'x1.1355 / m', 'final_value': 1.1355, 'value_type': 'multiplier', 'contributors': []},
                'state::tower.rapid_fire_chance_pct': {'display_value': '34%', 'final_value': 34.0, 'value_type': 'pct', 'contributors': []},
                'state::tower.rapid_fire_duration_seconds': {'display_value': '5.55 sec', 'final_value': 5.55, 'value_type': 'seconds', 'contributors': []},
                'state::tower.bounce_shot_range_m': {'display_value': '8m', 'final_value': 8.0, 'value_type': 'distance', 'contributors': []},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': dict(query_rows_start['Farming']['rows'])}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = ((workshop_panel.get('payload', {}).get('sections') or [{}])[0].get('rows') or [])
    by_name = {row.get('name'): row for row in offense_rows}
    assert by_name['Range']['start_of_run_value'] == '69.5'
    assert by_name['Damage / Meter']['start_of_run_value'] == 'x1.14'
    assert by_name['Rapid Fire Chance']['start_of_run_value'] == '34%'
    assert by_name['Rapid Fire Duration']['start_of_run_value'] == '5.55'
    assert by_name['Bounce Shot Range']['start_of_run_value'] == '8'


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
    assert by_label['Shockwave Interval']['cap'] == '7'
    assert by_label['Wall Health']['canonical_row_id'] == 'workshop::wall.health'


def test_stats_dashboard_modules_slot_payload_normalizes_primary_display_values():
    account_state = {'default_preset': 'Farming', 'card_presets': {'Farming': []}, 'module_presets': {}, 'workshop': {}, 'workshop_enhancement_tracks': {}, 'cards_inventory': {}, 'raw_sections': {}, 'uw_tracks': {}, 'ultimate_weapons': {}}
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    module_card_payloads = {
        'presets': {
            'Farming': {
                'cannon': {'primary': {'main_value_text': 'x10.818', 'module_name': 'Amplifying Strike', 'rarity_text': 'Ancestral'}, 'assist': {}},
                'armor': {'primary': {'main_value_text': 'x10.24', 'module_name': 'Sharp Fortitude', 'rarity_text': 'Ancestral'}, 'assist': {'main_value_text': 'x1.0047', 'module_name': 'Assist Armor', 'rarity_text': 'Rare'}},
                'generator': {'primary': {'main_value_text': 'x1.81', 'module_name': 'Singularity Harness', 'rarity_text': 'Ancestral'}, 'assist': {'main_value_text': 'x1.029', 'module_name': 'Assist Generator', 'rarity_text': 'Rare'}},
                'core': {'primary': {'main_value_text': 'x14.014', 'module_name': 'Primordial Collapse', 'rarity_text': 'Ancestral'}, 'assist': {'main_value_text': 'x1.4695', 'module_name': 'Assist Core', 'rarity_text': 'Rare'}},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads=module_card_payloads,
        query_rows_start_of_run={},
        query_rows_max_progression={},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    modules_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'modules')
    slots = modules_panel.get('payload', {}).get('slots') or {}
    assert slots['cannon']['primary']['main_value_text'] == 'x10.82'
    assert slots['armor']['assist']['main_value_text'] == 'x1'
    assert slots['generator']['assist']['main_value_text'] == 'x1.03'
    assert slots['core']['primary']['main_value_text'] == 'x14.01'
    assert slots['core']['assist']['main_value_text'] == 'x1.47'


def test_stats_dashboard_derived_rows_normalize_display_values():
    account_state = {'default_preset': 'Farming', 'card_presets': {'Farming': []}, 'module_presets': {}, 'workshop': {}, 'workshop_enhancement_tracks': {}, 'cards_inventory': {}, 'raw_sections': {}, 'uw_tracks': {}, 'ultimate_weapons': {}}
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={'Farming': {'rows': {'state::tower.ultimate_damage_multiplier': {'display_value': 'x25.124', 'final_value': 25.124, 'value_type': 'multiplier', 'status': 'resolved'}}}},
        query_rows_max_progression={'Farming': {'rows': {'state::tower.ultimate_damage_multiplier': {'display_value': 'x25.124', 'final_value': 25.124, 'value_type': 'multiplier', 'status': 'resolved'}}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )
    workshop = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'workshop')
    derived_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}, {}, {}])[3].get('rows') or [])
    by_name = {row.get('name'): row for row in derived_rows}
    assert by_name['Ultimate Weapon Damage']['start_of_run_value'] == 'x25.12'
    assert by_name['Ultimate Weapon Damage']['max_progression_value'] == 'x25.12'


def test_stats_dashboard_wall_health_uses_workshop_percentage_track_not_wall_hp():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Wall Health': {
                'preset_levels': {'Farming': 1340},
                'preset_values': {'Farming': 1800.0},
                'max_level': 1800,
            },
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
                'state::wall.hp': {
                    'display_value': '132M',
                    'final_value': 131560783.2,
                    'value_type': 'hp',
                    'contributors': [],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::wall.hp': {
                    'display_value': '171M',
                    'final_value': 170858160.0,
                    'value_type': 'hp',
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
        selected_state_mode='start_of_run',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    defense_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}])[1].get('rows') or [])
    wall_health = next(item for item in defense_rows if item.get('name') == 'Wall Health')
    assert wall_health['workshop_value'] == '1.8k%'
    assert wall_health['start_of_run_value'] == '1.8k%'
    assert wall_health['max_progression_value'] == '1.8k%'


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

    workshop_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    derived_section = next(
        section for section in (workshop_panel.get('payload', {}).get('sections') or [])
        if section.get('title') == 'Derived'
    )
    derived_rows = {row.get('name'): row for row in (derived_section.get('rows') or [])}
    assert derived_rows['Wall Thorns']['start_of_run_value'] == '—'
    assert derived_rows['Wall Thorns']['row_status'] == 'missing'


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
    assert by_name['Wall Rebuild']['cap'] == '150'
    assert by_name['Interest / Wave']['start_of_run_value'] == '—'
    assert by_name['Interest / Wave']['max_progression_value'] == '—'


def test_stats_dashboard_workshop_publishes_wall_rebuild_and_interest_rows_green_when_qe_rows_exist():
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
    query_rows_start = {
        'Farming': {
            'rows': {
                'state::wall.rebuild_seconds': {
                    'display_value': '608',
                    'final_value': 608.0,
                    'value_type': 'seconds',
                    'status': 'resolved',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.wall_rebuild.account_state', 'value': -90.0},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__wall_rebuild_seconds_reduction', 'value': 2.0},
                        {'source_class': 'workshop', 'contributor_id': 'workshop__wall__rebuild__seconds', 'value': 700.0},
                    ],
                },
                'state::economy.interest_per_wave_pct': {
                    'display_value': '7.16%',
                    'final_value': 7.16,
                    'value_type': 'pct',
                    'status': 'partially_resolved',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.interest.account_state', 'value': 1.22},
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__interest_per_wave__pct', 'value': 5.94},
                    ],
                },
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::wall.rebuild_seconds': {
                    'display_value': '508',
                    'final_value': 508.0,
                    'value_type': 'seconds',
                    'status': 'resolved',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.wall_rebuild.account_state', 'value': -90.0},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__wall_rebuild_seconds_reduction', 'value': 2.0},
                        {'source_class': 'workshop', 'contributor_id': 'workshop__wall__rebuild__seconds', 'value': 600.0},
                    ],
                },
                'state::economy.interest_per_wave_pct': {
                    'display_value': '31.32%',
                    'final_value': 31.325,
                    'value_type': 'pct',
                    'status': 'partially_resolved',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.interest.account_state', 'value': 1.22},
                        {'source_class': 'perks', 'contributor_id': 'perk::PERK_INTEREST_X1_50::effect_1', 'value': 4.375, 'input_value_type': 'multiplier'},
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__interest_per_wave__pct', 'value': 5.94},
                    ],
                },
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
    assert by_name['Wall Rebuild']['row_status'] == 'resolved'
    assert by_name['Wall Rebuild']['start_of_run_value'] == '608'
    assert by_name['Wall Rebuild']['max_progression_value'] == '508'
    assert by_name['Wall Rebuild']['cap'] == '150'
    assert by_name['Wall Rebuild']['reconciliation_status'] == 'green'
    assert by_name['Wall Rebuild']['relics'] == '- 2'
    assert by_name['Interest / Wave']['row_status'] == 'partially_resolved'
    assert by_name['Interest / Wave']['start_of_run_value'] == '7.16%'
    assert by_name['Interest / Wave']['max_progression_value'] == '31.32%'
    assert by_name['Interest / Wave']['reconciliation_status'] == 'green'


def test_stats_dashboard_workshop_surfaces_start_and_max_progression_modifier_totals():
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
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 58_300_000.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.damage', 'value': 2.44},
                        {'source_class': 'module_main', 'contributor_id': 'module.damage', 'value': 10.0},
                        {'source_class': 'cards', 'contributor_id': 'card.damage', 'value': 2.15},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.damage', 'value': 1.56},
                        {'source_class': 'relics', 'contributor_id': 'relic.damage', 'value': 0.54},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.damage': {
                    'display_value': '4.19B',
                    'final_value': 4.19e9,
                    'value_type': 'damage',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 71_100_000.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.damage', 'value': 2.44},
                        {'source_class': 'module_main', 'contributor_id': 'module.damage', 'value': 10.0},
                        {'source_class': 'cards', 'contributor_id': 'card.damage', 'value': 2.15},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.damage', 'value': 1.56},
                        {'source_class': 'relics', 'contributor_id': 'relic.damage', 'value': 0.54},
                        {'source_class': 'perk_effect', 'contributor_id': 'perk.damage', 'value': 1.8},
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
    assert damage_row['start_of_run_modifier_total'] == 'x 126.03'
    assert damage_row['other'] == '—'
    assert damage_row['max_progression_modifier_total'] == 'x 1.8'


def test_workshop_reconciliation_row_populates_strict_green_audit():
    row = build_workshop_reconciliation_row(
        spec={'label': 'Damage', 'surface_id': 'state::tower.damage', 'canonical_row_id': 'state::tower.damage'},
        start_row={
            'status': 'resolved',
            'final_value': 300.0,
            'value_type': 'damage',
            'contributors': [
                {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 100.0},
                {'source_class': 'labs', 'contributor_id': 'lab.damage', 'value': 2.0},
                {'source_class': 'relics', 'contributor_id': 'relic.damage', 'value': 0.5},
            ],
        },
        max_row={
            'status': 'resolved',
            'final_value': 720.0,
            'value_type': 'damage',
            'contributors': [
                {'source_class': 'workshop', 'contributor_id': 'workshop__tower__damage__flat', 'value': 120.0},
                {'source_class': 'labs', 'contributor_id': 'lab.damage', 'value': 2.0},
                {'source_class': 'relics', 'contributor_id': 'relic.damage', 'value': 0.5},
                {'source_class': 'perks', 'contributor_id': 'perk.damage', 'value': 2.0, 'input_value_type': 'multiplier'},
            ],
        },
        account_state_payload={'workshop': {'Damage': {'preset_levels': {'Farming': 1}}}},
        selected_preset='Farming',
    )
    assert row['reconciliation_status'] == 'green'
    assert row['reconciliation_failures'] == []
    assert all(value is True for value in row['reconciliation_checks'].values())
    assert all(flag == 'pass' for flag in row['reconciliation_cell_flags'].values())


def test_workshop_reconciliation_audit_marks_bad_base_subtotal_red():
    checks, cell_flags, failures, status = _strict_reconciliation_audit(
        row_status='resolved',
        family='multiplicative',
        surface_id='state::tower.damage',
        value_type='damage',
        workshop_value=100.0,
        max_workshop_value=120.0,
        base_subtotal_effect=(0.0, 3.0, True),
        base_loadout_subtotal_effect=(0.0, 3.0, True),
        start_total_effect=(0.0, 3.0, True),
        other_effect=(0.0, 1.0, False),
        max_workshop_modifier_effect=(0.0, 3.0, True),
        perk_effect=(0.0, 2.0, True),
        base_subtotal_text='x 2.9',
        base_loadout_subtotal_text='x 3',
        start_modifier_total_text='x 3',
        start_of_run_value_text='300',
        other_text='—',
        max_workshop_total_text='x 3',
        max_workshop_resolved_value_text='360',
        perk_text='x 2',
        max_progression_value_text='720',
    )
    assert status == 'red'
    assert checks['base_subtotal_ok'] is False
    assert cell_flags['base_subtotal'] == 'fail'
    assert 'base_subtotal_ok' in failures


def test_workshop_reconciliation_audit_marks_bad_final_value_red():
    checks, cell_flags, failures, status = _strict_reconciliation_audit(
        row_status='resolved',
        family='multiplicative',
        surface_id='state::tower.damage',
        value_type='damage',
        workshop_value=100.0,
        max_workshop_value=120.0,
        base_subtotal_effect=(0.0, 3.0, True),
        base_loadout_subtotal_effect=(0.0, 3.0, True),
        start_total_effect=(0.0, 3.0, True),
        other_effect=(0.0, 1.0, False),
        max_workshop_modifier_effect=(0.0, 3.0, True),
        perk_effect=(0.0, 2.0, True),
        base_subtotal_text='x 3',
        base_loadout_subtotal_text='x 3',
        start_modifier_total_text='x 3',
        start_of_run_value_text='300',
        other_text='—',
        max_workshop_total_text='x 3',
        max_workshop_resolved_value_text='360',
        perk_text='x 2',
        max_progression_value_text='700',
    )
    assert status == 'red'
    assert checks['max_progression_value_ok'] is False
    assert cell_flags['max_progression_value'] == 'fail'
    assert 'max_progression_value_ok' in failures


def test_workshop_reconciliation_audit_marks_missing_row_amber():
    checks, cell_flags, failures, status = _strict_reconciliation_audit(
        row_status='missing',
        family='multiplicative',
        surface_id='state::tower.damage',
        value_type='damage',
        workshop_value=None,
        max_workshop_value=None,
        base_subtotal_effect=(0.0, 1.0, False),
        base_loadout_subtotal_effect=(0.0, 1.0, False),
        start_total_effect=(0.0, 1.0, False),
        other_effect=(0.0, 1.0, False),
        max_workshop_modifier_effect=(0.0, 1.0, False),
        perk_effect=(0.0, 1.0, False),
        base_subtotal_text='—',
        base_loadout_subtotal_text='—',
        start_modifier_total_text='—',
        start_of_run_value_text='—',
        other_text='—',
        max_workshop_total_text='—',
        max_workshop_resolved_value_text='—',
        perk_text='—',
        max_progression_value_text='—',
    )
    assert status == 'amber'
    assert failures == []
    assert all(value is None for value in checks.values())
    assert all(flag == 'na' for flag in cell_flags.values())


def test_stats_dashboard_workshop_modifier_totals_use_percent_display_for_pct_surfaces():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Defense %': {'preset_levels': {'Farming': 99}}},
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
                'state::tower.defense_pct': {
                    'display_value': '78.4%',
                    'final_value': 78.4,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__defense_pct__pct', 'value': 49.5},
                        {'source_class': 'labs', 'contributor_id': 'lab.defense_%.account_state', 'value': 5.6},
                        {'source_class': 'cards', 'contributor_id': 'card.extra_defense.loadout_resolved', 'value': 11.0},
                        {'source_class': 'module_substat', 'contributor_id': 'module.a', 'value': 8.3, 'input_value_type': 'pct'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__defense_pct__pct', 'value': 0.04},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.defense_pct': {
                    'display_value': '98%',
                    'final_value': 98.0,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__defense_pct__pct', 'value': 49.5},
                        {'source_class': 'labs', 'contributor_id': 'lab.defense_%.account_state', 'value': 5.6},
                        {'source_class': 'cards', 'contributor_id': 'card.extra_defense.loadout_resolved', 'value': 11.0},
                        {'source_class': 'module_substat', 'contributor_id': 'module.a', 'value': 8.3, 'input_value_type': 'pct'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__defense_pct__pct', 'value': 0.04},
                        {'source_class': 'perks', 'contributor_id': 'perk::PERK_DEFENSE_PERCENT_4_00::effect_1', 'value': 25.0, 'input_value_type': 'pct'},
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
        (workshop.get('payload', {}).get('sections') or [{}, {}])[1].get('rows') or []
    )
    defense_row = next(row for row in offense_rows if row.get('name') == 'Defense %')
    assert defense_row['start_of_run_modifier_total'] == '+ 28.9%'
    assert defense_row['other'] == '—'
    assert defense_row['cap'] == '98%'
    assert defense_row['max_progression_modifier_total'] == '+ 25%'
    assert defense_row['reconciliation_status'] == 'green'
    assert defense_row['reconciliation_checks']['max_progression_value_ok'] is True


def test_stats_dashboard_workshop_other_uses_start_to_max_non_perk_delta():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Attack Speed': {'preset_levels': {'Farming': 99}}},
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
                'state::tower.attack_speed': {
                    'display_value': '39.776',
                    'final_value': 39.776,
                    'value_type': 'attacks_per_second',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.attack_speed.account_state', 'value': 2.5},
                        {'source_class': 'module_substat', 'contributor_id': 'module.attack_speed', 'value': 3.0, 'input_value_type': 'pct'},
                        {'source_class': 'cards', 'contributor_id': 'card.attack_speed.loadout_resolved', 'value': 2.15},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.attack_speed', 'value': 1.15},
                        {'source_class': 'relics', 'contributor_id': 'relic.attack_speed', 'value': 0.05},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.attack_speed': {
                    'display_value': '41',
                    'final_value': 41.0,
                    'value_type': 'attacks_per_second',
                    'contributors': [
                        {'source_class': 'labs', 'contributor_id': 'lab.attack_speed.account_state', 'value': 2.5},
                        {'source_class': 'module_substat', 'contributor_id': 'module.attack_speed', 'value': 6.0, 'input_value_type': 'pct'},
                        {'source_class': 'cards', 'contributor_id': 'card.attack_speed.loadout_resolved', 'value': 2.15},
                        {'source_class': 'workshop', 'contributor_id': 'enhancement.attack_speed', 'value': 1.15},
                        {'source_class': 'relics', 'contributor_id': 'relic.attack_speed', 'value': 0.05},
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
    attack_speed_row = next(row for row in offense_rows if row.get('name') == 'Attack Speed')
    assert attack_speed_row['lab_effects'] == 'x 2.5'
    assert attack_speed_row['module_effects'] == 'x 1.03'
    assert attack_speed_row['other'] == 'x 1.03'
    assert attack_speed_row['max_progression_modifier_total'] == 'x 1.03'


def test_stats_dashboard_workshop_super_crit_relic_uses_multiplier_factor():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Super Critical Mult': {'preset_levels': {'Farming': 100}}},
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
                'state::tower.supercrit_multiplier': {
                    'display_value': 'x138.693',
                    'final_value': 138.693,
                    'value_type': 'multiplier',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__supercrit_multiplier__multiplier', 'value': 11.2},
                        {'source_class': 'labs', 'contributor_id': 'lab.super_crit_multi.account_state', 'value': 1.26},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.amplifying_strike.loadout_resolved', 'value': 5.0, 'input_value_type': 'multiplier_display'},
                        {'source_class': 'enhancement', 'contributor_id': 'enhancement.super_crit_multi_+.account_state', 'value': 1.56},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__supercrit_multiplier__pct', 'value': 0.05},
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
        query_rows_max_progression=query_rows_start,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = ((workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or [])
    row = next(item for item in offense_rows if item.get('name') == 'Super Crit Multiplier')
    assert row['relics'] == '+ 0.05'
    assert row['start_of_run_modifier_total'] == 'x 2.85'


def test_stats_dashboard_workshop_coins_kill_bonus_normalizes_module_and_lab_factors():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Coin / Kill Bonus': {'preset_levels': {'Farming': 149}}},
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
                'state::economy.coins_per_kill_bonus': {
                    'display_value': 'x14.757',
                    'final_value': 14.757,
                    'value_type': 'multiplier',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__coin_kill_bonus__multiplier', 'value': 2.49},
                        {'source_class': 'labs', 'contributor_id': 'lab__tower__coins_kill_bonus__pct', 'value': 2.8},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.black_hole_digestor.loadout_resolved', 'value': 0.03},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.singularity_harness.loadout_resolved', 'value': 0.5, 'input_value_type': 'multiplier_display'},
                        {'source_class': 'enhancement', 'contributor_id': 'enhancement.coin_bonus_+.account_state', 'value': 1.37},
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
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    utility_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}, {}])[2].get('rows') or [])
    row = next(item for item in utility_rows if item.get('name') == 'Coins / Kill Bonus')
    assert row['lab_effects'] == 'x 2.8'
    assert row['module_effects'] == 'x 1.54'
    assert row['start_of_run_modifier_total'] == 'x 5.93'


def test_stats_dashboard_workshop_enemy_attack_skip_keeps_enhancement_multiplicative():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Enemy Attack Level Skip': {'preset_levels': {'Farming': 330}}},
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
                'state::tower.enemy_attack_level_skip_pct': {
                    'display_value': '33.35%',
                    'final_value': 33.35,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__enemy_attack_level_skip__pct', 'value': 16.55},
                        {'source_class': 'labs', 'contributor_id': 'lab.enemy_attack_level_skip.account_state', 'value': 2.0},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.black_hole_digestor.loadout_resolved', 'value': 0.2, 'input_value_type': 'percent_display'},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.singularity_harness.loadout_resolved', 'value': 8.0, 'input_value_type': 'percent_display'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__enemy_attack_level_skip__pct', 'value': 2.0},
                        {'source_class': 'enhancement', 'contributor_id': 'enhancements__tower__enemy_attack_level_skip__multiplier', 'value': 1.16},
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
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    utility_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}, {}])[2].get('rows') or [])
    row = next(item for item in utility_rows if item.get('name') == 'Enemy Attack Level Skip')
    assert row['enhancement_effects'] == 'x 1.16'
    assert row['start_of_run_modifier_total'] == '+ 16.8%'


def test_stats_dashboard_workshop_pct_rows_scale_relic_fractions_to_percentage_points():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Critical Chance': {'preset_levels': {'Farming': 79}}},
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
                'state::tower.crit_chance_pct': {
                    'display_value': '86%',
                    'final_value': 86.0,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__crit_chance__pct', 'value': 80.0},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__crit_chance__pct', 'value': 0.06},
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
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = ((workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or [])
    row = next(item for item in offense_rows if item.get('name') == 'Crit Chance')
    assert row['relics'] == '+ 6%'
    assert row['start_of_run_modifier_total'] == '+ 6%'


def test_stats_dashboard_workshop_multiplier_rows_expand_module_substat_multiplier_display():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Super Critical Mult': {'preset_levels': {'Farming': 100}}},
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
                'state::tower.supercrit_multiplier': {
                    'display_value': 'x138.693',
                    'final_value': 138.693,
                    'value_type': 'multiplier',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__supercrit_multiplier__multiplier', 'value': 11.2},
                        {'source_class': 'labs', 'contributor_id': 'lab.super_crit_multi.account_state', 'value': 1.26},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.amplifying_strike.loadout_resolved', 'value': 5.0, 'input_value_type': 'multiplier_display'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__supercrit_multiplier__pct', 'value': 0.05},
                        {'source_class': 'enhancement', 'contributor_id': 'enhancement.super_crit_multi_+.account_state', 'value': 1.56},
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
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    offense_rows = ((workshop.get('payload', {}).get('sections') or [{}])[0].get('rows') or [])
    row = next(item for item in offense_rows if item.get('name') == 'Super Crit Multiplier')
    assert row['module_effects'] == '+ 5'
    assert row['relics'] == '+ 0.05'
    assert row['start_of_run_modifier_total'] == 'x 2.85'


def test_stats_dashboard_workshop_scalar_rows_can_use_multiplicative_reconciliation_family():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Knockback Force': {'preset_levels': {'Farming': 40}}, 'Orbs Speed': {'preset_levels': {'Farming': 38}}},
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
                'state::tower.knockback_force': {
                    'display_value': '14.556',
                    'final_value': 14.556,
                    'value_type': 'force',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__knockback_force__flat', 'value': 6.08},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.sharp_fortitude.loadout_resolved', 'value': 0.9},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__knockback_force__pct', 'value': 0.26},
                    ],
                },
                'state::tower.orb_speed_rpm': {
                    'display_value': '7.137',
                    'final_value': 7.137,
                    'value_type': 'rpm',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__orb_speed__rpm', 'value': 6.1},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.sharp_fortitude.loadout_resolved', 'value': 1.0},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__orb_speed__pct', 'value': 0.17},
                    ],
                },
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows_start,
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='max_progression',
    )
    workshop = next(
        panel for panel in payload['variants']['Farming']['max_progression']
        if panel.get('panel_id') == 'workshop'
    )
    defense_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}])[1].get('rows') or [])
    knockback_force = next(item for item in defense_rows if item.get('name') == 'Knockback Force')
    orb_speed = next(item for item in defense_rows if item.get('name') == 'Orb Speed')
    assert knockback_force['module_effects'] == 'x 1.9'
    assert knockback_force['relics'] == 'x 1.26'
    assert knockback_force['start_of_run_modifier_total'] == 'x 2.39'
    assert orb_speed['relics'] == 'x 1.17'
    assert orb_speed['start_of_run_modifier_total'] == 'x 1.17'


def test_stats_dashboard_thorns_scales_fractional_module_substat_to_percentage_points():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {'Thorn Damage': {'preset_levels': {'Farming': 99}}},
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
                'state::tower.thorns_damage_pct': {
                    'display_value': '140%',
                    'final_value': 140.0,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__thorns_damage__pct', 'value': 99.0},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.orbital_augment.loadout_resolved', 'value': 0.2},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.sharp_fortitude.loadout_resolved', 'value': 10.0, 'input_value_type': 'percent_display'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__thorns__pct', 'value': 11.0},
                    ],
                }
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::tower.thorns_damage_pct': {
                    'display_value': '140%',
                    'final_value': 140.0,
                    'value_type': 'pct',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__thorns_damage__pct', 'value': 99.0},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.orbital_augment.loadout_resolved', 'value': 0.2},
                        {'source_class': 'module_substat', 'contributor_id': 'module_substat.sharp_fortitude.loadout_resolved', 'value': 10.0, 'input_value_type': 'percent_display'},
                        {'source_class': 'relics', 'contributor_id': 'relic__tower__thorns__pct', 'value': 11.0},
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
    defense_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}])[1].get('rows') or [])
    row = next(item for item in defense_rows if item.get('name') == 'Thorns')
    assert row['module_effects'] == '+ 30%'
    assert row['start_of_run_modifier_total'] == '+ 41%'
    assert row['reconciliation_status'] == 'green'
    assert row['reconciliation_checks']['semantic_format_ok'] is True


def test_stats_dashboard_cash_and_coin_wave_rows_use_multiplicative_family():
    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Cash / Wave': {'preset_levels': {'Farming': 149}},
            'Coin / Wave': {'preset_levels': {'Farming': 149}},
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
                'state::economy.cash_per_wave': {
                    'display_value': '691.36',
                    'final_value': 691.36,
                    'value_type': 'cash',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__cash_per_wave__flat', 'value': 596.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.cash___wave.account_state', 'value': 1.16},
                    ],
                },
                'state::economy.coins_per_wave': {
                    'display_value': '168',
                    'final_value': 168.0,
                    'value_type': 'coins',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__coins_per_wave__flat', 'value': 150.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.coins___wave.account_state', 'value': 1.12},
                    ],
                },
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'state::economy.cash_per_wave': {
                    'display_value': '9.13k',
                    'final_value': 9130.0,
                    'value_type': 'cash',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__cash_per_wave__flat', 'value': 596.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.cash___wave.account_state', 'value': 1.16},
                        {'source_class': 'perks', 'contributor_id': 'perk::cash_wave', 'value': 13.2, 'input_value_type': 'multiplier'},
                    ],
                },
                'state::economy.coins_per_wave': {
                    'display_value': '168',
                    'final_value': 168.0,
                    'value_type': 'coins',
                    'contributors': [
                        {'source_class': 'workshop', 'contributor_id': 'workshop__tower__coins_per_wave__flat', 'value': 150.0},
                        {'source_class': 'labs', 'contributor_id': 'lab.coins___wave.account_state', 'value': 1.12},
                    ],
                },
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
    utility_rows = ((workshop.get('payload', {}).get('sections') or [{}, {}, {}])[2].get('rows') or [])
    cash_per_wave = next(item for item in utility_rows if item.get('name') == 'Cash / Wave')
    coins_per_wave = next(item for item in utility_rows if item.get('name') == 'Coins / Wave')
    assert cash_per_wave['lab_effects'] == 'x 1.16'
    assert cash_per_wave['start_of_run_modifier_total'] == 'x 1.16'
    assert cash_per_wave['perk_effects'] == 'x 13.2'
    assert cash_per_wave['max_progression_modifier_total'] == 'x 13.2'
    assert coins_per_wave['lab_effects'] == 'x 1.12'
    assert coins_per_wave['start_of_run_modifier_total'] == 'x 1.12'
