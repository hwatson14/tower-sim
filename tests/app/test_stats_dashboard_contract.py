from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.publication import _build_input_dashboard_payload, _build_stats_dashboard_payload
from qe.query_module_policy import build_module_card_payloads
from qe.workshop_stat_rows import build_workshop_reconciliation_row, _strict_reconciliation_audit

ROOT = Path(__file__).resolve().parents[2]


def _namespace_tree(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{str(key): _namespace_tree(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace_tree(item) for item in value]
    return value


def _module_card_payloads_from_account_state_payload(account_state: dict) -> dict:
    account_state_view = SimpleNamespace(
        module_presets={
            preset: {
                slot: _namespace_tree(selection)
                for slot, selection in (slot_map or {}).items()
            }
            for preset, slot_map in (account_state.get('module_presets') or {}).items()
        },
        module_system_state={
            slot: _namespace_tree(slot_state)
            for slot, slot_state in (account_state.get('module_system_state') or {}).items()
        },
        modules_inventory={
            name: _namespace_tree(module)
            for name, module in (account_state.get('modules_inventory') or {}).items()
        },
    )
    return build_module_card_payloads(account_state_view)


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
        ('derived_wall_economy', 'workshop_stat_table'),
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


def test_stats_dashboard_reuses_workshop_reconciliation_payload_per_preset(monkeypatch):
    import qe.publication as qe_publication

    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    query_rows_start = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    original = qe_publication.publish_workshop_reconciliation_payload
    calls: list[str] = []

    def counted_publish_workshop_reconciliation_payload(**kwargs):
        calls.append(str(kwargs.get('selected_preset') or ''))
        return original(**kwargs)

    monkeypatch.setattr(
        qe_publication,
        'publish_workshop_reconciliation_payload',
        counted_publish_workshop_reconciliation_payload,
    )

    payload = qe_publication.build_stats_dashboard_payload(
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

    expected_presets = list((payload.get('variants') or {}).keys())
    assert calls == expected_presets
    assert {'start_of_run', 'max_progression'}.issubset(set((payload['variants']['Farming'] or {}).keys()))


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
    assert panel_acceptance['derived_wall_economy']['acceptance_state'] == 'active'
    assert panel_acceptance['derived_wall_economy']['authority'] == 'qe_query_rows'
    assert panel_acceptance['derived_wall_economy']['product_tier'] == 'primary'
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
    assert rows_by_name['Cooldown']['stone_value'] == '180s'
    assert rows_by_name['Cooldown']['start_of_run_value'] == '180s'
    assert rows_by_name['Cooldown']['max_progression_value'] == '160s'
    assert rows_by_name['Duration']['workshop_level'] == '3'
    assert rows_by_name['Duration']['start_of_run_value'] == '42s'


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
    assert [section.get('title') for section in sections] == ['Chrono Field', 'Golden Tower', 'Black Hole']
    chrono_rows = [row.get('name') for row in (sections[0].get('rows') or [])]
    assert chrono_rows[:3] == ['Duration', 'Speed Reduction', 'Cooldown']
    chrono_payload_rows = {row.get('name'): row for row in (sections[0].get('rows') or [])}
    assert chrono_payload_rows['Duration']['reconciliation_status'] == 'amber'


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
    start_rows = query_rows_start_of_run['Farming']['rows']
    max_rows = query_rows_max_progression['Farming']['rows']
    assert start_rows['state::uw.black_hole.duration_seconds']['final_value'] == pytest.approx(36.0)
    assert start_rows['state::uw.black_hole.cooldown_seconds']['final_value'] == pytest.approx(46.0)
    assert start_rows['state::uw.chrono_field.duration_seconds']['final_value'] == pytest.approx(50.0)
    assert start_rows['state::uw.chrono_field.cooldown_seconds']['final_value'] == pytest.approx(60.0)
    assert start_rows['state::uw.chrono_field.damage_reduction_pct']['final_value'] == pytest.approx(20.0)
    assert start_rows['state::uw.chrono_field.slow_pct']['final_value'] == pytest.approx(62.25)
    assert max_rows['state::uw.black_hole.duration_seconds']['final_value'] == pytest.approx(48.0)
    assert max_rows['state::uw.chrono_field.duration_seconds']['final_value'] == pytest.approx(55.0)
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
    golden_rows = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    black_hole_rows = {row.get('name'): row for row in (sections['Black Hole'].get('rows') or [])}
    assert golden_rows['Duration']['lab_effects'] == '20s'
    assert golden_rows['Duration']['reconciliation_status'] == 'green'
    assert black_hole_rows['Duration']['module_effects'] == '4s'
    assert black_hole_rows['Duration']['reconciliation_status'] == 'green'


def test_stats_dashboard_live_guardian_scout_rows_publish_cumulative_bits_and_green_recon():
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
        selected_state_mode='start_of_run',
    )
    guardian_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'guardians')
    sections = {section.get('title'): section for section in (guardian_panel.get('payload', {}).get('sections') or [])}
    scout_rows = {row.get('name'): row for row in (sections['Scout'].get('rows') or [])}
    assert scout_rows['Cooldown']['bits_spent'] == '0'
    assert scout_rows['Cooldown']['bit_value'] == '105s'
    assert scout_rows['Cooldown']['start_of_run_value'] == '105s'
    assert scout_rows['Cooldown']['reconciliation_status'] == 'green'
    assert scout_rows['Range Bonus']['bits_spent'] == '0'
    assert scout_rows['Range Bonus']['bit_value'] == '2x'
    assert scout_rows['Range Bonus']['start_of_run_value'] == 'x2'
    assert scout_rows['Range Bonus']['reconciliation_status'] == 'green'
    totals_rows = {row.get('name'): row for row in (sections['Totals'].get('rows') or [])}
    assert totals_rows['Total']['bits_spent'] == '921'


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
    module_card_payloads = _module_card_payloads_from_account_state_payload(account_state)
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
    assert by_key[('', 'Max Level')]['cannon'] == '240'
    assert by_key[('', 'Assist %')]['armor'] == '1%'
    assert by_key[('Primary', 'Module')]['generator'] == 'Singularity Harness'
    assert by_key[('Assist', 'Module')]['cannon'] == '—'
    assert by_key[('Current', 'Multiplier')]['core'] == 'x12.54'
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
                'derived::wall.hp_final': {'display_value': '4.44T', 'final_value': 4_440_000_000_000.0, 'value_type': 'hp', 'status': 'resolved', 'contributors': []},
                'derived::wall.regen_hp_per_second': {'display_value': '5.55T', 'final_value': 5_550_000_000_000.0, 'value_type': 'hp_per_second', 'status': 'resolved', 'contributors': []},
                'state::wall.thorns_damage_pct': {'display_value': '15.8%', 'final_value': 15.84, 'value_type': 'pct', 'status': 'resolved', 'contributors': []},
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
    assert wall_rows['Wall HP']['display_value'] == '4.44T'
    assert wall_rows['Wall Regen']['display_value'] == '5.55T'
    assert wall_rows['eHP']['display_value'] == '666'
    assert wall_rows['Wall Thorns']['display_value'] == '15.84%'
    assert wall_rows['Wall Thorns']['status'] == 'resolved'


def test_stats_dashboard_primary_derived_rows_use_compact_qe_owned_table():
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
                'derived::wall.hp_final': {
                    'display_value': '4.44T',
                    'final_value': 4_440_000_000_000.0,
                    'value_type': 'hp',
                    'status': 'resolved',
                    'notes': 'QE-published final displayed Wall HP.',
                    'contributors': [],
                },
                'derived::wall.regen_hp_per_second': {
                    'display_value': '5.55T',
                    'final_value': 5_550_000_000_000.0,
                    'value_type': 'hp_per_second',
                    'status': 'resolved',
                    'notes': 'QE-published final displayed Wall Regen.',
                    'contributors': [],
                },
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'derived::wall.hp_final': {
                    'display_value': '8.88T',
                    'final_value': 8_880_000_000_000.0,
                    'value_type': 'hp',
                    'status': 'resolved',
                    'notes': 'QE-published final displayed Wall HP.',
                    'contributors': [],
                },
                'derived::wall.regen_hp_per_second': {
                    'display_value': '9.99T',
                    'final_value': 9_990_000_000_000.0,
                    'value_type': 'hp_per_second',
                    'status': 'resolved',
                    'notes': 'QE-published final displayed Wall Regen.',
                    'contributors': [],
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

    primary = {panel.get('panel_id'): panel for panel in payload['variants']['Farming']['start_of_run']}
    workshop_sections = {section.get('title'): section for section in (primary['workshop'].get('payload', {}).get('sections') or [])}
    assert 'Derived' not in workshop_sections

    derived_payload = primary['derived_wall_economy']['payload']
    assert derived_payload['owner'] == 'qe'
    assert derived_payload['display_variant'] == 'objective_breakdown_grid'
    assert [column['key'] for column in derived_payload['columns']] == [
        'name',
        'surface_id',
        'value_type',
        'start_of_run_value',
        'max_progression_value',
        'status',
        'notes',
        'reconciliation_status',
    ]
    sections = {section.get('title'): section for section in (derived_payload.get('sections') or [])}
    assert 'Derived' in sections
    derived_rows = {row.get('name'): row for row in (sections['Derived'].get('rows') or [])}
    assert derived_rows['Wall HP']['surface_id'] == 'derived::wall.hp_final'
    assert derived_rows['Wall HP']['start_of_run_value'] == '4.44T'
    assert derived_rows['Wall HP']['max_progression_value'] == '8.88T'
    assert derived_rows['Wall HP']['reconciliation_status'] == 'green'
    assert derived_rows['Wall Regen']['surface_id'] == 'derived::wall.regen_hp_per_second'
    assert derived_rows['Wall Regen']['start_of_run_value'] == '5.55T'
    assert derived_rows['Wall Regen']['max_progression_value'] == '9.99T'
    assert derived_rows['Wall Regen']['reconciliation_status'] == 'green'


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
                'state::economy.coins_multiplier': {'display_value': 'x2.305', 'final_value': 2.3055, 'value_type': 'multiplier', 'status': 'resolved', 'contributors': [{'source_class': 'cards', 'contributor_id': 'card.coins.loadout_resolved', 'value': 1.45, 'display_value': '1.45'}, {'source_class': 'relics', 'contributor_id': 'relic__tower__coins__pct', 'value': 0.59, 'display_value': '0.59%'}]},
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
    assert card_rows['Coins Card']['display_value'] == 'x1.45'
    assert card_rows['Coins Card']['source_surface_id'] == 'state::economy.coins_multiplier'
    assert card_rows['Coins Card']['contributors_available'] is True
    assert card_rows['Plasma Cannon']['display_value'] == '27%'
    assert card_rows['Super Tower']['display_value'] == 'x1.5'
    assert card_rows['Ultimate Crit']['status'] == 'missing'

    assert panels['uw_stats_resolved'].get('payload', {}).get('owner') == 'qe'
    assert uw_rows['Chain Lightning Damage']['display_value'] == 'x12'
    assert uw_rows['Chrono Field Speed Reduction']['display_value'] == '38%'
    assert uw_rows['Golden Tower Cooldown']['status'] == 'missing'


def test_stats_dashboard_artifacts_prove_current_scope_effect_family_qe_coverage():
    requested_families = {
        'cards',
        'card_mastery',
        'bots',
        'workshop',
        'enhancements',
        'relics',
        'modules',
    }
    requested_kb_source_families = {
        'bot_upgrade',
        'card',
        'enhancements',
        'module',
        'relic',
        'workshop',
    }
    family_summary = {
        row['source_family']: row
        for row in csv.DictReader(
            (ROOT / 'kb' / 'ledgers' / 'tables' / 'contributor-routing-family-summary.csv').open(
                encoding='utf-8'
            )
        )
    }
    source_registry = {
        row['source_family']: row
        for row in csv.DictReader(
            (ROOT / 'kb' / 'ledgers' / 'tables' / 'source-family-surface-registry.csv').open(
                encoding='utf-8'
            )
        )
    }
    completeness_matrix = json.loads((ROOT / 'out' / 'family_completeness_matrix.json').read_text(encoding='utf-8'))
    boss_matrix = json.loads((ROOT / 'out' / 'boss_wave_milestone_matrix.json').read_text(encoding='utf-8'))
    diagnostics = json.loads((ROOT / 'out' / 'diagnostics.json').read_text(encoding='utf-8'))
    statbook_rows = json.loads(
        (ROOT / 'out' / 'statbook_publishable.json').read_text(encoding='utf-8')
    )['rows']
    assert statbook_rows['state::bot.bot_bot.maximum_power_multiplier']['final_value'] == 1.25
    assert statbook_rows['state::capability.plasma_cannon.enabled']['final_value'] is True
    assert 'state::module.om_chip.boss_reflection_multiplier' in statbook_rows
    assert 'state::module.sharp_fortitude.wall_bonus_multiplier' in statbook_rows

    kb_incomplete = diagnostics['kb_incomplete_areas']
    assert kb_incomplete['summary'] == {
        'active_unmapped_input_count': 0,
        'ambiguous_relic_semantic_hint_count': 0,
        'resolved_unknown_schema_unit_count': 0,
    }
    assert diagnostics['active_unmapped_input_count'] == 0
    assert diagnostics['resolved_unknown_schema_unit_count'] == 0
    assert diagnostics['ambiguous_relic_semantic_hint_count'] == 0
    assert kb_incomplete['priority_gaps'] == []
    assert kb_incomplete['active_unmapped_by_family'] == {}
    assert kb_incomplete['active_unmapped_inputs'] == []
    assert kb_incomplete['resolved_unknown_schema_units'] == []
    assert kb_incomplete['ambiguous_relic_semantic_hints'] == []

    artifact_route_closure = completeness_matrix['requested_effect_route_closure']
    assert artifact_route_closure['status'] == 'closed'
    assert artifact_route_closure['source_family_count'] == len(requested_kb_source_families)
    assert artifact_route_closure['closed_source_family_count'] == len(requested_kb_source_families)
    assert artifact_route_closure['open_source_families'] == []
    assert set(artifact_route_closure['source_families']) == requested_kb_source_families
    assert (
        'card base and mastery effects'
        in artifact_route_closure['source_families']['card']['effect_scopes']
    )
    assert (
        'module substat effects'
        in artifact_route_closure['source_families']['module']['effect_scopes']
    )

    for family in requested_kb_source_families:
        summary = family_summary[family]
        assert summary['status'] == 'closed'
        assert summary['dangling_routes'] == '0'
        assert summary['registered_routes'] == summary['route_count']

        registry = source_registry[family]
        assert registry['routing_status'] == 'closed'
        assert registry['dedicated_active_surface_present'] == 'yes'
        assert registry['content_gap_flag'] == 'no'
        if family == 'relic':
            assert 'per-account relic numeric values remain external instance inputs by design' in registry['note']

    matrix_families = {
        'bot',
        'card',
        'enhancement',
        'module',
        'module_substat',
        'relic',
        'workshop',
    }
    matrix_by_family = completeness_matrix.get('families') or {}
    for family in matrix_families:
        row = matrix_by_family[family]
        assert row['total_rows'] > 0
        assert row['mapped_rows'] == row['total_rows']
        assert row['unmapped_rows'] == 0
        route_closure = row['requested_effect_route_closure']
        assert route_closure['closed'] is True
        assert route_closure['source_family'] in requested_kb_source_families
        assert route_closure['effect_scope']

    diagnostics_evidence = diagnostics['current_scope_effect_family_evidence']
    goal_readiness = diagnostics['tower_goal_readiness']
    perk_coverage = diagnostics['perk_coverage_audit']
    assert perk_coverage['entity_count'] == 34
    assert perk_coverage['effect_count'] == 45
    assert perk_coverage['all_perks_compile_audit_row_count'] == 48
    assert perk_coverage['summary_by_coverage'] == {
        'canonical_stat_routed': 22,
        'capability_routed': 1,
        'runtime_param_routed': 22,
    }
    assert perk_coverage['summary_by_destination_object_type'] == {
        'canonical_stat': 22,
        'capability': 1,
        'environment_param': 9,
        'mechanic_param': 6,
        'runtime_mechanic_param': 7,
    }
    perk_compile_gaps = [
        (perk['perk_id'], effect['effect_index'], effect['coverage'])
        for perk in perk_coverage['perks']
        for effect in perk['effects']
        if effect['compile_status'] != 'compiled'
        or effect['coverage'] in {'compile_gap', 'unsupported_operation', 'unbound_target'}
    ]
    assert perk_compile_gaps == []
    assert goal_readiness['status'] == 'not_complete'
    assert goal_readiness['achieved'] is False
    assert goal_readiness['remaining_blockers'] == [
        'boss_waves_full_accuracy',
        'farming_cph_objective',
    ]
    readiness_by_requirement = {
        row['id']: row for row in goal_readiness['requirements']
    }
    assert readiness_by_requirement['effect_family_carrythrough_to_boss_waves']['status'] == 'proven'
    effect_goal = readiness_by_requirement['effect_family_carrythrough_to_boss_waves']
    assert effect_goal['family_proof_counts'] == {
        'requested_family_count': 7,
        'covered_family_count': 7,
        'route_contributor_count': 163,
        'registered_route_contributor_count': 163,
        'unregistered_route_contributor_count': 0,
        'boss_wave_selected_row_count': 105,
        'boss_wave_rows_with_coverage': 105,
        'line_verification_status': 'covered',
        'statbook_route_visibility_exception_status': 'classified_partial_visibility_accepted',
    }
    family_proof_by_id = {
        row['family']: row for row in effect_goal['family_proof_summary']
    }
    assert set(family_proof_by_id) == {
        'bot',
        'card_base',
        'card_mastery',
        'workshop',
        'enhancement',
        'module',
        'relic',
    }
    expected_goal_route_counts = {
        'bot': 22,
        'card_base': 7,
        'card_mastery': 7,
        'workshop': 48,
        'enhancement': 17,
        'module': 42,
        'relic': 27,
    }
    for family, expected_route_count in expected_goal_route_counts.items():
        row = family_proof_by_id[family]
        assert row['status'] == 'covered'
        assert row['route_contributor_count'] == expected_route_count
        assert row['registered_route_contributor_count'] == expected_route_count
        assert row['unregistered_route_contributor_count'] == 0
        assert row['generated_unmapped_effect_row_count'] == 0
        assert row['boss_wave_selected_row_count'] == 105
        assert row['boss_wave_rows_with_coverage'] == 105
        assert row['line_verification_status'] == 'covered'
        assert row['ep_unaccounted_count'] == 0
    assert readiness_by_requirement['ep_export_alignment']['status'] == (
        'proven_with_accounted_stage_scope_limits'
    )
    assert readiness_by_requirement['dissonance_reference_policy']['status'] == 'proven'
    assert readiness_by_requirement['boss_waves_full_accuracy']['status'] == 'blocked'
    assert readiness_by_requirement['boss_waves_full_accuracy']['model_completion_blockers'] == [
        'source_owned_non_boss_terminal_pressure_formulas'
    ]
    assert readiness_by_requirement['boss_waves_full_accuracy'][
        'empirical_transform_promotion_status'
    ] == 'not_promoted'
    assert readiness_by_requirement['boss_waves_full_accuracy'][
        'empirical_transform_promotion_readiness'
    ]['status'] == 'not_ready'
    assert readiness_by_requirement['farming_cph_objective']['status'] == 'blocked'
    assert readiness_by_requirement['farming_cph_objective'][
        'coins_per_hour_certification_status'
    ] == 'not_certified_missing_formula_links'
    assert diagnostics_evidence['status'] == 'covered'
    assert diagnostics_evidence['route_closure_status'] == 'closed'
    assert diagnostics_evidence['route_closure_open_source_families'] == []
    assert diagnostics_evidence['individual_route_evidence_status'] == 'closed'
    assert diagnostics_evidence['individual_route_ledger'] == (
        'kb/ledgers/tables/contributor-routing-closure.csv'
    )
    assert diagnostics_evidence['unique_source_family_route_count'] == 163
    assert diagnostics_evidence['unique_source_family_registered_route_count'] == 163
    assert diagnostics_evidence['unique_source_family_unregistered_route_count'] == 0
    assert diagnostics_evidence['unique_source_family_route_status_counts'] == {'registered': 163}
    assert diagnostics_evidence['statbook_route_visibility_status'] == 'partial'
    assert diagnostics_evidence['statbook_route_visibility_exception_status'] == (
        'classified_partial_visibility_accepted'
    )
    assert diagnostics_evidence['statbook_route_visibility_exception_policy'] == {
        'accepted_partial_visibility_classifications': [
            'inactive_card_capability_route_gated_off_current_statbook',
            'inactive_module_unique_registered_not_current_account_route',
            'other_preset_module_card_payload_visible_in_query_books',
        ],
        'active_selected_route_gap_count': 0,
        'other_preset_missing_query_evidence_count': 0,
        'unclassified_route_gap_count': 0,
        'policy': (
            'Selected-statbook visibility may be partial only when every hidden route is '
            'classified as inactive for the selected preset or visible through another-preset query-book evidence.'
        ),
    }
    assert diagnostics_evidence['statbook_route_visibility_status_counts'] == {
        'covered': 4,
        'partial': 3,
    }
    assert diagnostics_evidence['statbook_route_visibility_mode_counts'] == {
        'destination_surface_visible': 52,
        'exact_statbook_contributor': 94,
        'not_visible_in_current_statbook': 24,
    }
    assert diagnostics_evidence['statbook_route_visibility_incomplete_families'] == [
        'card_base',
        'card_mastery',
        'module',
    ]
    assert diagnostics_evidence['module_card_payload_context_status'] == 'evaluated'
    assert diagnostics_evidence['module_card_payload_selected_preset'] == 'Farming'
    assert diagnostics_evidence['query_book_visibility_status'] == 'evaluated'
    assert diagnostics_evidence['query_book_visibility_book_count'] == 4
    assert diagnostics_evidence['module_unique_runtime_catalog_count'] == 24
    assert diagnostics_evidence['not_visible_route_classification_counts'] == {
        'inactive_card_capability_route_gated_off_current_statbook': 2,
        'inactive_module_unique_registered_not_current_account_route': 15,
        'other_preset_module_card_payload_visible_in_query_books': 7,
    }
    assert diagnostics_evidence['generated_mapping_status'] == 'closed'
    assert diagnostics_evidence['effect_row_carrythrough_status'] == 'covered'
    assert diagnostics_evidence['effect_row_carrythrough_status_counts'] == {'covered': 7}
    assert diagnostics_evidence['effect_row_carrythrough_incomplete_families'] == []
    assert diagnostics_evidence['boss_wave_coverage_status'] == 'covered'
    assert diagnostics_evidence['boss_wave_selected_row_count'] == 105
    assert diagnostics_evidence['boss_wave_rows_with_coverage'] == 105
    assert diagnostics_evidence['line_verification_status'] == 'covered'
    line_evidence = diagnostics_evidence['line_verification']
    assert line_evidence['status'] == 'covered'
    assert line_evidence['accepted_verdicts'] == ['pass', 'pass_with_compare_limitations']
    assert line_evidence['missing_statbook_families'] == []
    assert line_evidence['missing_line_verification_families'] == []
    assert line_evidence['unmapped_statbook_contributor_families'] == []
    assert line_evidence['unknown_value_type_families'] == []
    assert line_evidence['non_pass_verdict_families'] == []
    assert line_evidence['issue_families'] == []
    assert diagnostics_evidence['missing_route_closure_families'] == []
    assert diagnostics_evidence['missing_kb_route_ledger_closure_families'] == []
    assert diagnostics_evidence['missing_individual_route_evidence_families'] == []
    assert diagnostics_evidence['missing_generated_mapping_families'] == []
    assert diagnostics_evidence['missing_boss_wave_coverage_families'] == []
    requested_boss_families = {
        'bot',
        'card_base',
        'card_mastery',
        'workshop',
        'enhancement',
        'module',
        'relic',
    }
    assert set(diagnostics_evidence['requested_effect_families']) == requested_boss_families
    boss_coverage = boss_matrix['replacement_primitive_family_coverage_summary']
    assert boss_coverage['status'] == 'covered'
    assert boss_coverage['selected_row_count'] == diagnostics_evidence['boss_wave_selected_row_count']
    assert boss_coverage['rows_with_coverage'] == diagnostics_evidence['boss_wave_rows_with_coverage']
    assert set(boss_coverage['requested_effect_families']) == requested_boss_families
    assert boss_coverage['missing_requested_families'] == []
    assert boss_coverage['missing_requested_family_counts'] == {}
    assert boss_coverage['row_status_counts'] == {'covered': 105}
    covered_family_statuses = {
        'covered_by_qe_contributor',
        'covered_by_qe_surface',
        'covered_by_qe_surface_and_contributor',
    }
    for family in requested_boss_families:
        status_counts = boss_coverage['family_status_counts'][family]
        assert set(status_counts) <= covered_family_statuses
        assert sum(status_counts.values()) == 105
    boss_rows = boss_matrix['rows']
    assert len(boss_rows) == diagnostics_evidence['boss_wave_selected_row_count']
    for index, row in enumerate(boss_rows):
        coverage = row['replacement_primitive_family_coverage']
        assert coverage['status'] == 'covered', f'Boss Waves row {index} lacks full family coverage'
        assert coverage['scope'] == 'boss_waves_replacement_primitive_boundary'
        assert set(coverage['requested_effect_families']) == requested_boss_families
        assert coverage['missing_requested_families'] == []
        assert set(coverage['family_statuses']) == requested_boss_families
        assert set(coverage['family_statuses'].values()) <= covered_family_statuses
        assert coverage['observed_resolved_surface_count'] > 0
        assert coverage['observed_active_contributor_evidence_count'] > 0

    expected_route_counts = {
        'bot': 22,
        'card_base': 7,
        'card_mastery': 7,
        'workshop': 48,
        'enhancement': 17,
        'module': 42,
        'relic': 27,
    }
    expected_primary_surfaces = {
        'bot': ['kb/bots/tables/bot-entity-registry.csv'],
        'card_base': ['kb/cards/tables/card-base-ladders.csv'],
        'card_mastery': ['kb/cards/tables/card-base-ladders.csv'],
        'workshop': ['kb/workshop/tables/workshop-values.csv'],
        'enhancement': ['kb/workshop/tables/enhancements-values.csv'],
        'module': ['kb/modules/tables/module-main-effect-bases.csv'],
        'relic': ['kb/global-rules/tables/relic-input-registry.csv'],
    }
    expected_visibility_counts = {
        'bot': {
            'exact_statbook_contributor': 21,
            'destination_surface_visible': 1,
        },
        'card_base': {
            'destination_surface_visible': 6,
            'not_visible_in_current_statbook': 1,
        },
        'card_mastery': {
            'destination_surface_visible': 6,
            'not_visible_in_current_statbook': 1,
        },
        'workshop': {'exact_statbook_contributor': 48},
        'enhancement': {
            'exact_statbook_contributor': 3,
            'destination_surface_visible': 14,
        },
        'module': {
            'destination_surface_visible': 20,
            'not_visible_in_current_statbook': 22,
        },
        'relic': {
            'exact_statbook_contributor': 22,
            'destination_surface_visible': 5,
        },
    }
    expected_route_gap_classification_counts = {
        'bot': {},
        'card_base': {
            'inactive_card_capability_route_gated_off_current_statbook': 1,
        },
        'card_mastery': {
            'inactive_card_capability_route_gated_off_current_statbook': 1,
        },
        'workshop': {},
        'enhancement': {},
        'module': {
            'inactive_module_unique_registered_not_current_account_route': 15,
            'other_preset_module_card_payload_visible_in_query_books': 7,
        },
        'relic': {},
    }
    for family in diagnostics_evidence['requested_effect_families']:
        evidence_row = diagnostics_evidence['families'][family]
        assert evidence_row['status'] == 'covered'
        assert evidence_row['route_closed'] is True
        assert evidence_row['kb_route_ledger_closed'] is True
        assert evidence_row['kb_route_count'] == expected_route_counts[family]
        assert evidence_row['kb_registered_route_count'] == evidence_row['kb_route_count']
        assert evidence_row['kb_dangling_route_count'] == 0
        assert evidence_row['kb_route_ledger_statuses'] == ['closed']
        assert evidence_row['kb_surface_registry_statuses'] == ['closed']
        assert evidence_row['kb_content_gap_flags'] == ['no']
        assert evidence_row['kb_primary_surfaces'] == expected_primary_surfaces[family]
        individual_route_evidence = evidence_row['individual_route_evidence']
        assert individual_route_evidence['status'] == 'closed'
        assert individual_route_evidence['ledger'] == (
            'kb/ledgers/tables/contributor-routing-closure.csv'
        )
        assert individual_route_evidence['route_contributor_count'] == expected_route_counts[family]
        assert individual_route_evidence['registered_route_contributor_count'] == expected_route_counts[family]
        assert individual_route_evidence['unregistered_route_contributor_count'] == 0
        assert individual_route_evidence['registration_status_counts'] == {
            'registered': expected_route_counts[family]
        }
        assert individual_route_evidence['destination_count'] > 0
        assert individual_route_evidence['destination_object_type_counts']
        assert individual_route_evidence['contributor_id_examples']
        assert individual_route_evidence['unregistered_contributor_ids'] == []
        assert individual_route_evidence['statbook_route_visibility_status'] in {
            'covered',
            'partial',
        }
        assert individual_route_evidence['statbook_route_visibility_mode_counts'] == (
            expected_visibility_counts[family]
        )
        assert individual_route_evidence['not_visible_route_classification_counts'] == (
            expected_route_gap_classification_counts[family]
        )
        if family == 'module':
            classified_examples = individual_route_evidence['statbook_not_visible_classified_examples']
            query_visible_examples = [
                example
                for example in classified_examples
                if (
                    example.get('classification') or {}
                ).get('status') == 'other_preset_module_card_payload_visible_in_query_books'
            ]
            assert len(query_visible_examples) == 7
            visible_by_contributor = {
                example['contributor_id']: (example.get('classification') or {}).get('query_book_visibility') or {}
                for example in query_visible_examples
            }
            assert visible_by_contributor[
                'module__armor__anti_cube_portal__damage_multiplier'
            ]['query_evidence_surface_id'] == 'state::module.anti_cube_portal.shockwave_damage_taken_mult_x'
            assert visible_by_contributor[
                'module__armor__anti_cube_portal__damage_multiplier'
            ]['equivalent_entry_count'] == 4
            assert visible_by_contributor[
                'module__armor__anti_cube_portal__shockwave_damage_taken_mult_x'
            ]['resolved_query_presets'] == ['Tourney']
            assert visible_by_contributor[
                'module__cannon__being_annihilator__guaranteed_supercrits_after_supercrit_attacks'
            ]['direct_entry_count'] == 4
            assert visible_by_contributor[
                'module__cannon__being_annihilator__guaranteed_supercrits_after_supercrit_attacks'
            ]['gated_query_presets'] == ['Farming', 'Tourney']
            assert visible_by_contributor[
                'module__generator__galaxy_compressor__uw_cooldown_reduction_seconds'
            ]['materialized_surface_id'] == 'support_surface::timing.gcomp_cooldown_reduction_seconds'
            assert visible_by_contributor[
                'module__generator__galaxy_compressor__uw_cooldown_reduction_seconds'
            ]['materialized_entry_count'] == 4
            assert visible_by_contributor[
                'module__generator__galaxy_compressor__uw_cooldown_reduction_on_package_s'
            ]['query_evidence_surface_id'] == 'support_surface::timing.gcomp_cooldown_reduction_seconds'
            assert visible_by_contributor[
                'module__generator__galaxy_compressor__uw_cooldown_reduction_on_package_s'
            ]['equivalent_entry_count'] == 4
        if family in {'card_base', 'card_mastery', 'module'}:
            assert individual_route_evidence['statbook_not_visible_examples']
            assert individual_route_evidence['statbook_not_visible_classified_examples']
        else:
            assert individual_route_evidence['statbook_not_visible_examples'] == []
            assert individual_route_evidence['statbook_not_visible_classified_examples'] == []
        assert evidence_row['generated_total_rows'] > 0
        assert evidence_row['generated_mapped_rows'] == evidence_row['generated_total_rows']
        assert evidence_row['generated_unmapped_rows'] == 0
        carrythrough = evidence_row['effect_row_carrythrough']
        assert carrythrough['status'] == 'covered'
        assert carrythrough['route_closed'] is True
        assert carrythrough['kb_route_ledger_closed'] is True
        assert carrythrough['individual_routes_closed'] is True
        assert carrythrough['individual_route_contributor_count'] == expected_route_counts[family]
        assert carrythrough['individual_registered_route_contributor_count'] == expected_route_counts[family]
        assert carrythrough['individual_unregistered_route_contributor_count'] == 0
        assert carrythrough['generated_mapping_closed'] is True
        assert carrythrough['generated_family_keys'] == evidence_row['generated_family_keys']
        assert carrythrough['generated_effect_row_count'] == evidence_row['generated_total_rows']
        assert carrythrough['generated_mapped_effect_row_count'] == evidence_row['generated_mapped_rows']
        assert carrythrough['generated_unmapped_effect_row_count'] == 0
        assert carrythrough['boss_wave_covered'] is True
        assert carrythrough['boss_wave_selected_row_count'] == 105
        assert carrythrough['boss_wave_rows_with_coverage'] == 105
        assert carrythrough['line_verification_status'] == 'covered'
        assert evidence_row['boss_wave_covered'] is True
        assert evidence_row['boss_wave_family_status_counts']
        assert evidence_row['line_verification_status'] == 'covered'
        assert evidence_row['statbook_surface_count'] > 0
        assert evidence_row['statbook_surface_ids']
        assert evidence_row['line_verification_surface_count'] == evidence_row['statbook_surface_count']
        assert evidence_row['line_verification_missing_surfaces'] == []
        assert evidence_row['statbook_kb_mapped_contributor_count'] == evidence_row['statbook_contributor_count']
        assert evidence_row['statbook_unmapped_contributor_count'] == 0
        assert evidence_row['statbook_unknown_value_type_count'] == 0
        assert evidence_row['statbook_unknown_value_type_surfaces'] == []
        assert 'unknown' not in evidence_row['statbook_value_type_counts']
        assert 'missing' not in evidence_row['statbook_value_type_counts']
        assert evidence_row['issue_surfaces'] == []
        assert evidence_row['non_pass_verdict_surfaces'] == []
        assert set(evidence_row['verdict_counts']) <= {'pass', 'pass_with_compare_limitations'}
    assert diagnostics_evidence['families']['card_base']['route_family_keys'] == ['card']
    assert diagnostics_evidence['families']['card_mastery']['route_family_keys'] == ['card']
    assert diagnostics_evidence['families']['card_base']['statbook_selection_mode'] == (
        'active_card_base_runtime_contributors'
    )
    assert diagnostics_evidence['families']['card_base']['statbook_surface_count'] == 22
    assert diagnostics_evidence['families']['card_base']['statbook_contributor_count'] == 23
    assert diagnostics_evidence['families']['card_base']['statbook_source_family_counts'] == {'card': 23}
    assert diagnostics_evidence['families']['card_mastery']['statbook_selection_mode'] == (
        'card_mastery_registry_and_applied_runtime_surfaces'
    )
    assert diagnostics_evidence['families']['card_mastery']['statbook_surface_count'] == 34
    assert diagnostics_evidence['families']['card_mastery']['statbook_contributor_count'] == 34
    assert diagnostics_evidence['families']['card_mastery']['statbook_source_family_counts'] == {
        'card': 3,
        'lab': 31,
    }
    assert diagnostics_evidence['families']['card_mastery']['verdict_counts'] == {'pass': 34}
    assert (
        'card base and mastery effects'
        in diagnostics_evidence['families']['card_mastery']['route_effect_scopes']
    )
    assert diagnostics_evidence['families']['module']['generated_family_keys'] == ['module', 'module_substat']
    assert diagnostics_evidence['families']['module']['route_family_keys'] == ['module', 'module_substat']
    assert diagnostics_evidence['families']['module']['route_source_families'] == ['module']
    assert diagnostics_evidence['families']['module']['route_effect_scopes'] == [
        'module main and unique effects',
        'module substat effects',
    ]

    bot_plus_surfaces = (
        'state::bot.plus.wildfire.unlocked',
        'state::bot.plus.titan_shock.unlocked',
        'state::bot.plus.bonus_cell.unlocked',
        'state::bot.plus.echoing_shot.unlocked',
        'state::bot.plus.maximum_power.unlocked',
    )
    observed_bot_plus_unlocked_count = 0
    for surface_id in bot_plus_surfaces:
        row = statbook_rows[surface_id]
        bot_plus_contributors = [
            contributor
            for contributor in row.get('contributors') or []
            if contributor.get('source_family') == 'bot_plus'
        ]
        assert len(bot_plus_contributors) == 1
        expected_value = bot_plus_contributors[0]['value']
        assert isinstance(expected_value, bool)
        assert row['status'] == 'resolved'
        assert row['value_type'] == 'bool'
        assert row['final_value'] is expected_value
        assert (row.get('schema') or {}).get('unit') == 'bool'
        assert (row.get('schema') or {}).get('resolver') == 'standard_bool'
        observed_bot_plus_unlocked_count += int(expected_value)
    assert statbook_rows['derived::bot.plus.unlocked_count']['final_value'] == float(
        observed_bot_plus_unlocked_count
    )
    assert statbook_rows['derived::bot.plus.all_unlocked']['final_value'] == (
        1.0 if observed_bot_plus_unlocked_count == len(bot_plus_surfaces) else 0.0
    )
    assert statbook_rows['derived::bot.synchronicity.base_slots_unlocked']['final_value'] == (
        2.0 if observed_bot_plus_unlocked_count == len(bot_plus_surfaces) else 0.0
    )
    expected_bot_plus_values = {
        surface_id: statbook_rows[surface_id]['final_value']
        for surface_id in bot_plus_surfaces
    }
    expected_bot_plus_all_unlocked = (
        1.0 if observed_bot_plus_unlocked_count == len(bot_plus_surfaces) else 0.0
    )
    expected_synchronicity_slots = (
        2.0 if observed_bot_plus_unlocked_count == len(bot_plus_surfaces) else 0.0
    )

    artifacts = {
        'start_of_run': json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8')),
        'max_progression': json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8')),
    }
    for state_mode, payload in artifacts.items():
        for preset, preset_payload in payload.items():
            rows = preset_payload.get('rows') or {}
            bad_status_rows = {
                surface_id: row.get('status')
                for surface_id, row in rows.items()
                if row.get('status') not in {'resolved', 'gated_off'}
            }
            assert bad_status_rows == {}, f'{state_mode}/{preset} has unresolved current-scope rows: {bad_status_rows}'

            for surface_id, expected_value in expected_bot_plus_values.items():
                row = rows[surface_id]
                assert row['status'] == 'resolved'
                assert row['value_type'] == 'bool'
                assert row['final_value'] is expected_value
            assert rows['derived::bot.plus.unlocked_count']['final_value'] == float(
                observed_bot_plus_unlocked_count
            )
            assert rows['derived::bot.plus.all_unlocked']['final_value'] == expected_bot_plus_all_unlocked
            assert (
                rows['derived::bot.synchronicity.base_slots_unlocked']['final_value']
                == expected_synchronicity_slots
            )

            seen: dict[str, set[str]] = {family: set() for family in requested_families}
            for surface_id, row in rows.items():
                row_blob = json.dumps(row, sort_keys=True).lower()
                if 'mastery' in surface_id.lower() or 'mastery' in row_blob:
                    seen['card_mastery'].add(surface_id)
                for contributor in row.get('contributors') or []:
                    source_class = str(contributor.get('source_class') or contributor.get('source_family') or '')
                    if source_class == 'cards':
                        seen['cards'].add(surface_id)
                    elif source_class == 'bots':
                        seen['bots'].add(surface_id)
                    elif source_class == 'workshop':
                        seen['workshop'].add(surface_id)
                    elif source_class == 'enhancement':
                        seen['enhancements'].add(surface_id)
                    elif source_class == 'relics':
                        seen['relics'].add(surface_id)
                    elif source_class.startswith('module_'):
                        seen['modules'].add(surface_id)

            missing_families = {family for family, surfaces in seen.items() if not surfaces}
            assert missing_families == set(), f'{state_mode}/{preset} missing QE family evidence for {sorted(missing_families)}'


def test_boss_wave_matrix_artifact_keeps_default_model_posture_explicit():
    matrix = json.loads((ROOT / 'out' / 'boss_wave_milestone_matrix.json').read_text(encoding='utf-8'))
    run_stats = json.loads((ROOT / 'out' / 'run_stats.json').read_text(encoding='utf-8'))
    diagnostics = json.loads((ROOT / 'out' / 'diagnostics.json').read_text(encoding='utf-8'))
    run_stats_matrix = (run_stats.get('diagnostics') or {}).get('boss_wave_milestone_matrix') or {}
    diagnostics_matrix = diagnostics.get('boss_wave_milestone_matrix') or {}

    expected_blockers = ['source_owned_non_boss_terminal_pressure_formulas']
    expected_review_input = {'boss_wave_pressure_factor': 2.606384292771721}

    assert matrix['model_closure_status'] == 'partial_missing_required_model_inputs'
    assert matrix['model_completion_blockers'] == expected_blockers
    assert matrix['certified_full_max_wave_model'] is False
    assert matrix['accepted_approximation_closure'] == {
        'closed': False,
        'mode': 'none',
        'scope': 'non_boss_terminal_pressure_scalar_on_boss_health_and_damage',
        'boss_wave_pressure_factor': None,
        'replaced_blockers': [],
        'certification_effect': 'none',
        'certified_full_max_wave_model': False,
    }
    accuracy = matrix['model_accuracy_summary']
    assert accuracy['status'] == 'default_partial_comparison_calibration_available'
    assert accuracy['operator_next_step'] == 'apply_comparison_only_pressure_factor_input_to_review_approximation'
    assert accuracy['comparison_only_pressure_factor_inputs'] == expected_review_input
    assert accuracy['pressure_factor_application'] == 'manual_or_comparison_only'
    pressure_driver_model = accuracy['non_boss_pressure_driver_model']
    assert pressure_driver_model['status'] == (
        'source_driver_curves_partially_available_terminal_transform_missing'
    )
    assert pressure_driver_model['default_pressure_factor_derived'] is False
    assert pressure_driver_model['pressure_factor_policy'] == (
        'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved'
    )
    assert pressure_driver_model['required_formula_owner'] == 'simulators_with_kb_formula_inputs'
    assert pressure_driver_model['driver_emphasis'] == 'spawn_rate_elite_fleet_tier_wave'
    assert pressure_driver_model['source_backed_curve_coverage'] == {
        'normal_spawn_rate_curve_by_wave_and_wave_accelerator': True,
        'elite_spawn_curve_by_tier_and_wave': True,
        'fleet_spawn_curve_by_tier_and_wave': True,
        'fleet_related_enemy_group_count_range': True,
        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase': False,
    }
    terminal_readiness = pressure_driver_model['terminal_pressure_transform_readiness']
    assert terminal_readiness['status'] == (
        'source_driver_curves_available_terminal_transform_missing'
    )
    assert terminal_readiness['owner'] == (
        'app.pipeline.summary_from_simulators.scenario_source_evidence'
    )
    assert terminal_readiness['application'] == 'diagnostic_only_not_default_formula'
    assert terminal_readiness['certification_effect'] == 'none'
    assert terminal_readiness['default_boss_wave_truth_changed'] is False
    assert terminal_readiness['source_curve_coverage'] == pressure_driver_model[
        'source_backed_curve_coverage'
    ]
    assert terminal_readiness['source_owned_driver_input_count'] == 5
    assert [row['driver'] for row in terminal_readiness['source_owned_driver_inputs']] == [
        'enemy_spawn_rate',
        'wave_accelerator_mastery_spawn_rate_acceleration',
        'elite_spawn_pressure',
        'fleet_spawn_pressure',
        'tier_and_wave_pressure',
    ]
    assert terminal_readiness['missing_source_owned_formula_links'] == [
        'enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight',
        'wave_accelerator_mastery_spawn_acceleration_to_spawn_pressure_weight',
        'normal_spawn_rate_value_to_terminal_pressure',
        'elite_spawn_pressure_weight_to_terminal_pressure',
        'fleet_spawn_pressure_weight_to_terminal_pressure',
        'normal_elite_fleet_pressure_composition_rule',
        'pressure_to_terminal_max_wave_or_boss_pressure_factor_transform',
    ]
    assert terminal_readiness['remaining_to_certify'] == [
        'normal_spawn_rate_value_to_terminal_pressure',
        'elite_spawn_pressure_weight_to_terminal_pressure',
        'fleet_spawn_pressure_weight_to_terminal_pressure',
        'normal_elite_fleet_pressure_composition_rule',
        'pressure_to_terminal_max_wave_or_boss_pressure_factor_transform',
        'validation_across_regular_and_non_capped_dissonance_references',
    ]
    assert pressure_driver_model['simulator_source_summary']['source_table_counts'] == {
        'normal_spawn_rate_wave_threshold_rows': 28,
        'elite_spawn_threshold_rows': 21,
        'fleet_spawn_tier_rows': 21,
    }
    assert pressure_driver_model['monotonic_pressure_drivers'] == [
        'enemy_spawn_rate',
        'wave_accelerator_mastery_spawn_rate_acceleration',
        'elite_spawn_rate',
        'fleet_spawn_rate',
        'fleet_related_enemy_group_load',
        'tier',
        'wave',
    ]
    driver_inputs = {
        item['driver']: item for item in pressure_driver_model['source_owned_driver_inputs']
    }
    assert set(driver_inputs) == {
        'enemy_spawn_rate',
        'wave_accelerator_mastery_spawn_rate_acceleration',
        'elite_spawn_pressure',
        'fleet_spawn_pressure',
        'tier_and_wave_pressure',
    }
    assert driver_inputs['enemy_spawn_rate']['surface_ids'] == [
        'kb::normal_spawn_rate_wave_thresholds',
        'context::bc.more_enemies_pct',
    ]
    assert 'state::cards.wave_accelerator.spawn_rate_acceleration' in driver_inputs[
        'wave_accelerator_mastery_spawn_rate_acceleration'
    ]['surface_ids']
    assert 'state::cards.enemy_balance.mastery_effect' in driver_inputs[
        'elite_spawn_pressure'
    ]['surface_ids']
    assert driver_inputs['enemy_spawn_rate']['boss_wave_consumption_status'] == (
        'source_curve_available_terminal_weight_missing'
    )
    assert driver_inputs['wave_accelerator_mastery_spawn_rate_acceleration'][
        'boss_wave_consumption_status'
    ] == 'source_curve_modifier_available_terminal_weight_missing'
    assert driver_inputs['elite_spawn_pressure']['boss_wave_consumption_status'] == (
        'source_curve_available_terminal_weight_missing'
    )
    assert driver_inputs['fleet_spawn_pressure']['boss_wave_consumption_status'] == (
        'source_curve_available_terminal_weight_missing'
    )
    assert pressure_driver_model['missing_source_owned_formula_links'] == [
        'enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight',
        'wave_accelerator_mastery_spawn_acceleration_to_spawn_pressure_weight',
        'normal_spawn_rate_value_to_terminal_pressure',
        'elite_spawn_pressure_weight_to_terminal_pressure',
        'fleet_spawn_pressure_weight_to_terminal_pressure',
        'normal_elite_fleet_pressure_composition_rule',
        'pressure_to_terminal_max_wave_or_boss_pressure_factor_transform',
    ]
    assert pressure_driver_model['empirical_calibration_policy'][
        'dissonance_pb_5000_cap_policy'
    ] == 'excluded_from_calibration_lower_bound_only'
    assert pressure_driver_model['empirical_calibration_policy'][
        'below_3000_wave_policy'
    ] == 'reported_as_caveated_sensitivity_not_clean_calibration'
    assert pressure_driver_model['empirical_calibration_policy']['below_3000_wave_reference_count'] == 11
    assert pressure_driver_model['empirical_calibration_policy']['dissonance_pb_5000_cap_count'] == 42
    assert pressure_driver_model['rows_with_unsupported_terminal_pressures'] == 35
    pressure_samples = pressure_driver_model['pressure_driver_samples']
    assert pressure_samples['status'] == 'available_terminal_transform_missing'
    assert pressure_samples['application'] == 'diagnostic_only_not_terminal_formula'
    assert pressure_samples['default_pressure_factor_derived'] is False
    assert pressure_samples['sample_count'] == 86
    regular_sample = next(
        sample
        for sample in pressure_samples['samples']
        if sample['tier'] == 14 and sample['dissonance_run_category'] == 'none'
    )
    assert regular_sample['wave'] == 9639
    assert regular_sample['displayed_spawn_rate'] == pytest.approx(56.0)
    assert regular_sample['loadout_policy_preset'] is None
    assert regular_sample['wave_accelerator_spawn_rate_acceleration'] == pytest.approx(1.0)
    assert regular_sample['enemy_balance_mastery_double_elite_chance_pct'] == pytest.approx(0.0)
    assert regular_sample['normal_spawn_rate_pressure_index'] == pytest.approx(56.0)
    assert regular_sample['elite_pressure_index_pct'] >= 0.0
    assert regular_sample['fleet_events_per_wave_pressure'] >= 0.0
    assert regular_sample['fleet_related_enemy_group_expected_enemies_per_wave_pressure'] >= 0.0
    candidate_pressure_samples = pressure_driver_model['pressure_driver_candidate_samples']
    assert candidate_pressure_samples['status'] == 'available_terminal_transform_missing'
    assert candidate_pressure_samples['application'] == 'diagnostic_only_not_terminal_formula'
    assert candidate_pressure_samples['default_pressure_factor_derived'] is False
    farming_candidate = next(
        sample
        for sample in candidate_pressure_samples['samples']
        if sample['tier'] == 14
        and sample['dissonance_run_category'] == 'none'
        and sample['loadout_policy_preset'] == 'eHP Max Waves'
    )
    assert farming_candidate['loadout_profile_preset'] == 'Farming'
    assert farming_candidate['wave'] == 7839
    assert farming_candidate['wave_accelerator_spawn_rate_acceleration'] == pytest.approx(1.8)
    assert farming_candidate['displayed_spawn_rate'] == pytest.approx(56.0)
    assert farming_candidate['pressure_factor_hint']['calculated_selected_max_wave'] == 7839
    assert farming_candidate['pressure_factor_hint']['boss_wave_pressure_factor'] == pytest.approx(
        7839 / 5761
    )
    empirical_calibration = pressure_driver_model['pressure_driver_empirical_calibration']
    assert empirical_calibration['status'] == 'available_descriptive_only'
    assert empirical_calibration['application'] == 'diagnostic_only_not_account_truth'
    assert empirical_calibration['default_pressure_factor_derived'] is False
    assert empirical_calibration['model_fit_status'] == 'not_fitted_terminal_transform_missing'
    assert empirical_calibration['calibration_row_count'] == 16
    assert empirical_calibration['pressure_factor_distribution']['median_factor'] == pytest.approx(
        2.606384292771721
    )
    assert {
        'normal_spawn_rate_pressure_index',
        'wave_accelerator_spawn_rate_acceleration',
        'elite_pressure_index_pct',
        'fleet_events_per_wave_pressure',
        'fleet_related_enemy_group_expected_enemies_per_wave_pressure',
        'tier',
        'wave',
    } <= set(empirical_calibration['candidate_driver_features'])
    t14_calibration = next(
        row for row in empirical_calibration['rows'] if row['tier'] == 14
    )
    assert t14_calibration['pressure_factor_hint'] == pytest.approx(9639 / 5761)
    assert t14_calibration['normal_spawn_rate_pressure_index'] == pytest.approx(56.0)
    assert t14_calibration['fleet_related_enemy_group_expected_enemies_per_wave_pressure'] >= 0.0
    transform = empirical_calibration['empirical_transform_candidate']
    assert transform['status'] == 'fitted_in_sample_descriptive_only'
    assert transform['application'] == 'diagnostic_only_not_account_truth'
    assert transform['default_pressure_factor_derived'] is False
    assert transform['validation_status'] == 'leave_one_out_descriptive_only_not_promoted'
    assert transform['promotion_status'] == 'not_promoted'
    assert transform['promotion_readiness'] == {
        'status': 'not_ready',
        'application': 'diagnostic_only_not_account_truth',
        'default_pressure_factor_derived': False,
        'operator_approval_required': True,
        'operator_approved_empirical_transform_default': False,
        'operator_approval_status': 'not_approved',
        'approval_runtime_input': 'approve_boss_wave_empirical_pressure_transform',
        'approval_policy': (
            'Explicit approval removes only the operator-approval blocker; '
            'source-owned formula and validation blockers still apply.'
        ),
        'validation_basis': 'clean_regular_rows_leave_one_out_only',
        'validated_row_count': 16,
        'mean_absolute_error': pytest.approx(0.6455062281014187),
        'max_absolute_error': pytest.approx(2.761589637980494),
        'blocking_reasons': [
            'not_source_owned_terminal_pressure_formula',
            'operator_has_not_approved_empirical_transform_as_default',
            'non_capped_dissonance_reference_validation_missing',
            'out_of_sample_validation_beyond_clean_regular_rows_missing',
        ],
    }
    assert transform['row_count'] == 16
    assert 'tier' in transform['active_features']
    assert 'wave' in transform['active_features']
    assert 'elite_pressure_index_pct' in transform['omitted_constant_features']
    assert transform['error_metrics']['mean_absolute_error'] >= 0.0
    assert transform['predictions'][0]['predicted_pressure_factor'] is not None
    loo_validation = transform['leave_one_out_validation']
    assert loo_validation['method'] == 'leave_one_out_by_clean_regular_row'
    assert loo_validation['status'] == 'available_descriptive_only'
    assert loo_validation['validated_row_count'] == 16
    assert loo_validation['unvalidated_row_count'] == 0
    assert loo_validation['mean_absolute_error'] >= transform['error_metrics']['mean_absolute_error']
    assert loo_validation['worst_row']['predicted_pressure_factor'] is not None
    assert accuracy['accepted_approximation_closure'] == matrix['accepted_approximation_closure']
    assert accuracy['certified_full_max_wave_model'] is False
    assert matrix['tracker_reference_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert accuracy['reference_caveat_counts']['dissonance_pb_5000_bonus_cap_floor'] == 42
    dissonance_pressure_evidence = accuracy['dissonance_pressure_factor_evidence']
    assert dissonance_pressure_evidence['status'] == 'caveated_dissonance_hints_only'
    assert dissonance_pressure_evidence['run_type_count'] == 4
    assert dissonance_pressure_evidence['calibration_quality_hint_count'] == 0
    assert dissonance_pressure_evidence['categories_with_clean_calibration'] == []
    assert set(dissonance_pressure_evidence['categories_without_clean_calibration']) == {
        'Attack Dissonant Run',
        'Defense Dissonant Run',
        'Utility Dissonant Run',
        'Ultimate Weapon Dissonant Run',
    }
    assert dissonance_pressure_evidence['disabled_hint_mode_counts'][
        'dissonance_pb_bonus_cap_not_exact_reference'
    ] == 42

    cap_caveat_rows = [
        row
        for row in matrix['rows']
        if 'dissonance_pb_5000_bonus_cap_floor'
        in ((row.get('reference_quality') or {}).get('caveats') or [])
    ]
    assert len(cap_caveat_rows) == 42
    for row in cap_caveat_rows:
        reference_quality = row['reference_quality']
        pressure_hint = row['pressure_factor_reference_hint']
        assert reference_quality['reference_kind'] == 'ids_dissonant_pb_wave'
        assert reference_quality['dissonance_pb_bonus_cap_reached'] is True
        assert reference_quality['reference_interpretation'] == 'lower_bound_at_dissonance_bonus_cap'
        assert reference_quality['exact_reference'] is False
        assert reference_quality['calibration_candidate'] is False
        assert pressure_hint['enabled'] is False
        assert pressure_hint['mode'] == 'dissonance_pb_bonus_cap_not_exact_reference'
        assert pressure_hint['boss_wave_pressure_factor'] is None
        assert pressure_hint['exact_reference'] is False

    assert run_stats_matrix['model_closure_status'] == matrix['model_closure_status']
    assert run_stats_matrix['model_completion_blockers'] == expected_blockers
    assert run_stats_matrix['model_accuracy_summary'] == accuracy
    assert diagnostics_matrix['model_closure_status'] == matrix['model_closure_status']
    assert diagnostics_matrix['model_completion_blockers'] == expected_blockers
    assert diagnostics_matrix['model_accuracy_summary'] == accuracy
    assert diagnostics_matrix['tracker_reference_evidence'] == matrix['tracker_reference_evidence']


def test_farming_econ_readiness_records_cph_anchor_without_certifying_formula():
    run_stats = json.loads((ROOT / 'out' / 'run_stats.json').read_text(encoding='utf-8'))
    query_rows = json.loads(
        (ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8')
    )
    rows = query_rows['Farming']['rows']

    assert rows['state::cards.intro_sprint.waves']['final_value'] == 1440.0
    assert rows['state::cards.wave_skip.chance_pct']['final_value'] == 19.0
    assert rows['state::cards.wave_accelerator.wave_cooldown_reduction_pct']['final_value'] == 54.0
    assert rows['state::cards.wave_accelerator.spawn_rate_acceleration']['final_value'] == 1.8
    assert rows['support_surface::scenario.target_farming_wave']['final_value'] > 0.0
    assert rows['support_surface::scenario.waves_per_run_effective']['final_value'] > rows[
        'support_surface::scenario.target_farming_wave'
    ]['final_value']

    readiness = (run_stats.get('diagnostics') or {})['farming_econ_model_readiness']
    diagnostics_readiness = json.loads(
        (ROOT / 'out' / 'diagnostics.json').read_text(encoding='utf-8')
    )['farming_econ_model_readiness']
    assert readiness['coins_per_hour_objective_identity'] == diagnostics_readiness[
        'coins_per_hour_objective_identity'
    ]
    assert readiness['missing_formula_links'] == diagnostics_readiness['missing_formula_links']
    assert readiness['objective'] == 'coins_per_hour'
    assert readiness['optimizer_policy'] == 'farming_should_optimize_coins_per_hour_not_longest_wave'
    assert readiness['certified_farming_cph_model'] is False
    assert readiness['coins_per_hour_certification_status'] == 'not_certified_missing_formula_links'
    assert readiness['coins_per_hour_objective_identity'] == {
        'status': 'source_owned_identity_available',
        'formula': 'coins_per_hour = coins_per_run / run_duration_hours',
        'owner': 'simulators.timing',
        'application': 'objective_conversion_only_not_coin_or_duration_integral',
        'certification_effect': 'closes_objective_conversion_link_only',
        'required_inputs': ['coins_per_run', 'run_duration_hours'],
        'remaining_to_certify': [
            'coins_per_run_integral',
            'run_duration_integral_after_intro_sprint_wave_skip_and_game_speed',
        ],
    }
    duration_readiness = readiness['run_duration_projection_readiness']
    assert duration_readiness['status'] == (
        'source_timing_projection_available_anchor_delta_reported'
    )
    assert duration_readiness['formula'] == (
        'played_non_intro_waves_after_expected_wave_skip * '
        'effective_wave_duration_seconds / effective_game_speed_multiplier'
    )
    assert duration_readiness['owner'] == 'simulators.timing'
    assert duration_readiness['application'] == 'duration_projection_only_not_certified_cph'
    assert duration_readiness['certification_effect'] == 'none'
    assert duration_readiness['operator_approval_required'] is True
    assert (
        duration_readiness[
            'operator_approved_tracker_empirical_run_duration_projection'
        ]
        is False
    )
    assert duration_readiness['operator_approval_status'] == 'not_approved'
    assert duration_readiness['approval_runtime_input'] == (
        'approve_tracker_empirical_run_duration_projection'
    )
    assert duration_readiness['tracker_duration_candidate_available'] is False
    assert duration_readiness['approved_projection_closes_formula_link'] is False
    assert duration_readiness['source_driver_status'] == 'available'
    assert duration_readiness['missing_required_timing_surfaces'] == []
    assert duration_readiness['projected_run_hours'] == pytest.approx(4.864050046685341)
    assert duration_readiness['anchor_run_hours'] == pytest.approx(5.5)
    assert duration_readiness['projected_to_anchor_run_hours_ratio'] == pytest.approx(
        0.884372735760971
    )
    assert duration_readiness['projected_delta_hours_vs_anchor'] == pytest.approx(
        -0.635949953314659
    )
    assert duration_readiness[
        'tracker_skip_adjusted_projected_over_observed_duration_ratio'
    ] is None
    assert duration_readiness['remaining_to_certify'] == [
        'source_confirmed_wave_duration_semantics',
        'source_confirmed_intro_sprint_timing_and_coin_window_semantics',
        'source_confirmed_wave_skip_timing_reward_expected_value',
        'validation_across_tracker_exports_and_account_states',
    ]
    assert readiness['coins_per_hour_optimization_target'] is True
    assert readiness['coins_per_hour_certification_blockers'] == [
        'calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed',
        'spawn_rate_to_enemy_kill_density_by_wave',
        'intro_sprint_no_coin_window_to_run_coin_integral',
        'wave_skip_reward_and_mastery_expected_value',
        'gt_bh_dw_spotlight_golden_bot_overlap_coin_integral',
    ]
    cph_promotion = readiness['coins_per_hour_promotion_readiness']
    assert cph_promotion['status'] == 'not_ready'
    assert cph_promotion['application'] == 'diagnostic_only_not_account_truth'
    assert cph_promotion['default_cph_derived'] is False
    assert cph_promotion['operator_approval_required'] is True
    assert cph_promotion['validation_basis'] == 'no_tracker_export_supplied'
    assert cph_promotion['tracker_cph_status'] == 'not_supplied'
    assert cph_promotion['tracker_cph_identity_status'] == 'not_supplied'
    assert cph_promotion['tracker_kill_density_status'] == 'not_supplied'
    assert cph_promotion['tracker_coin_integral_status'] == 'not_supplied'
    assert cph_promotion['tracker_calibration_anchor_hint'] == {}
    assert cph_promotion['tracker_latest_coins_per_hour'] is None
    assert cph_promotion['tracker_recent_median_coins_per_hour'] is None
    assert cph_promotion['tracker_prior_median_coins_per_hour'] is None
    assert cph_promotion['tracker_recent_to_prior_coins_per_hour_ratio'] is None
    assert cph_promotion['tracker_skip_semantics_inference_status'] is None
    assert cph_promotion['tracker_skip_semantics_best_candidate'] is None
    assert cph_promotion['tracker_skip_semantics_best_candidate_distance_from_expected'] is None
    assert cph_promotion['blocking_reasons'] == [
        'not_source_owned_run_coin_and_duration_integrals',
        'operator_has_not_approved_tracker_empirical_cph_as_default',
        'tracker_t14_farming_cph_band_missing',
        'tracker_density_component_identity_missing',
        'tracker_spawn_rate_to_kill_density_candidate_missing',
        'tracker_kill_density_to_coin_integral_candidate_missing',
        'recent_prior_kill_density_stability_missing',
        'recent_prior_coin_yield_stability_missing',
        'tracker_wave_skip_reward_fields_missing',
        'tracker_econ_coin_source_fields_missing',
        'wave_skip_reward_expected_value_missing',
        'econ_window_overlap_coin_integral_missing',
        'validation_across_multiple_exports_and_account_states_missing',
    ]
    anchor = readiness['calibration_anchor']
    assert anchor == {
        'source': 'user_reported_2026-06-13',
        'tier': 14,
        'preset': 'Farming',
        'observed_final_wave': 5500,
        'observed_run_hours': 5.5,
        'observed_coins_per_hour': 210_000_000_000_000.0,
        'implied_coins_per_run': 1_155_000_000_000_000.0,
        'application': 'calibration_target_only_not_account_truth',
    }
    assert (
        'calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed'
        in readiness['missing_formula_links']
    )
    assert 'gt_bh_dw_spotlight_golden_bot_overlap_coin_integral' in readiness[
        'missing_formula_links'
    ]
    assert 'coins_per_run_integral_to_coins_per_hour_objective' not in readiness[
        'missing_formula_links'
    ]
    assert readiness['tracker_cph_calibration_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert readiness['tracker_cph_identity_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert readiness['tracker_wave_reward_candidate'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    wave_skip_reward = readiness['wave_skip_reward_readiness']
    assert wave_skip_reward['status'] == (
        'source_reward_semantics_available_expected_value_integral_missing'
    )
    assert wave_skip_reward['owner'] == 'simulators.timing'
    assert wave_skip_reward['application'] == 'diagnostic_only_not_coin_formula'
    assert wave_skip_reward['certification_effect'] == 'none'
    assert wave_skip_reward['tracker_reward_status'] == 'not_supplied'
    assert wave_skip_reward['tracker_reward_field_status'] is None
    assert wave_skip_reward['operator_approval_required'] is True
    assert (
        wave_skip_reward['operator_approved_tracker_empirical_wave_skip_reward']
        is False
    )
    assert wave_skip_reward['operator_approval_status'] == 'not_approved'
    assert wave_skip_reward['approval_runtime_input'] == (
        'approve_tracker_empirical_wave_skip_reward'
    )
    assert wave_skip_reward['tracker_reward_candidate_available'] is False
    assert wave_skip_reward['approved_reward_closes_formula_link'] is False
    assert wave_skip_reward['remaining_to_certify'] == [
        'wave_skip_coin_reward_expected_value_over_per_wave_coin_curve',
        'wave_skip_mastery_double_skip_reward_semantics',
        'tracker_waves_skipped_intro_sprint_semantics',
        'econ_window_overlap_for_skipped_and_played_waves',
    ]
    intro_sprint_coin_window = readiness['intro_sprint_coin_window_readiness']
    assert intro_sprint_coin_window['status'] == (
        'source_intro_sprint_coin_suppression_available_coin_integral_missing'
    )
    assert intro_sprint_coin_window['owner'] == 'simulators.timing'
    assert intro_sprint_coin_window['application'] == 'diagnostic_only_not_coin_formula'
    assert intro_sprint_coin_window['certification_effect'] == 'none'
    assert intro_sprint_coin_window['operator_approval_required'] is True
    assert (
        intro_sprint_coin_window['operator_approved_source_intro_sprint_coin_window']
        is False
    )
    assert intro_sprint_coin_window['operator_approval_status'] == 'not_approved'
    assert intro_sprint_coin_window['approval_runtime_input'] == (
        'approve_source_intro_sprint_coin_window'
    )
    assert intro_sprint_coin_window['source_coin_window_candidate_available'] is True
    assert intro_sprint_coin_window['approved_window_closes_formula_link'] is False
    assert intro_sprint_coin_window['source_surface_id'] == 'state::cards.intro_sprint.waves'
    assert intro_sprint_coin_window['driver_status'] == 'resolved'
    assert intro_sprint_coin_window['active_wave_count'] == pytest.approx(1440.0)
    assert intro_sprint_coin_window['target_wave'] == pytest.approx(5761.0)
    assert intro_sprint_coin_window[
        'coin_eligible_displayed_waves_after_intro_at_target'
    ] == pytest.approx(4321.0)
    assert intro_sprint_coin_window['remaining_to_certify'] == [
        'source_owned_per_wave_coin_curve_after_intro_sprint',
        'intro_sprint_boundary_interaction_with_wave_skip_and_wave_rewards',
        'econ_window_overlap_for_post_intro_played_and_skipped_waves',
        'run_coin_integral_excluding_intro_sprint_waves',
    ]
    wave_reward_audit = wave_skip_reward['source_audit']
    assert wave_reward_audit['status'] == (
        'base_reward_sources_available_integral_semantics_unresolved'
    )
    assert wave_reward_audit['certification_effect'] == 'none'
    assert wave_reward_audit['intro_sprint_coin_suppression']['status'] == (
        'source_backed_available'
    )
    assert wave_reward_audit['intro_sprint_coin_suppression']['active_wave_count'] == (
        pytest.approx(1440.0)
    )
    assert wave_reward_audit['wave_skip_base_reward']['status'] == (
        'source_backed_available_expected_value_missing'
    )
    assert wave_reward_audit['wave_skip_base_reward']['chance_pct'] == pytest.approx(19.0)
    assert wave_reward_audit['wave_skip_mastery_double_skip']['driver_status'] == (
        'gated_off'
    )
    assert wave_reward_audit['tracker_skip_count_semantics']['status'] is None
    assert wave_reward_audit['missing_to_promote'] == [
        'wave_skip_coin_reward_expected_value_over_per_wave_coin_curve',
        'wave_skip_mastery_double_skip_reward_semantics',
        'tracker_waves_skipped_intro_sprint_semantics',
        'econ_window_overlap_for_skipped_and_played_waves',
    ]
    econ_sync = readiness['econ_sync_window_readiness']
    assert econ_sync['status'] == 'window_inputs_available_overlap_integral_not_certified'
    assert econ_sync['application'] == 'diagnostic_only_not_coin_formula'
    assert econ_sync['certification_effect'] == 'none'
    assert econ_sync['operator_approval_status'] == 'not_approved'
    assert econ_sync['approved_overlap_closes_formula_link'] is False
    assert econ_sync['phase_model'] == 'phase_zero_current_helper_only'
    assert econ_sync['phase_model_certified'] is False
    assert econ_sync['available_window_count'] == 3
    assert econ_sync['required_window_count'] == 3
    assert econ_sync['missing_window_inputs'] == []
    overlap_integral = econ_sync['overlap_integral_readiness']
    assert overlap_integral['status'] == (
        'source_window_inputs_available_overlap_integral_missing'
    )
    assert overlap_integral['owner'] == 'simulators.timing'
    assert overlap_integral['application'] == 'diagnostic_only_not_coin_formula'
    assert overlap_integral['certification_effect'] == 'none'
    assert overlap_integral['operator_approval_required'] is True
    assert (
        overlap_integral['operator_approved_tracker_empirical_econ_window_overlap']
        is False
    )
    assert overlap_integral['operator_approval_status'] == 'not_approved'
    assert overlap_integral['approval_runtime_input'] == (
        'approve_tracker_empirical_econ_window_overlap'
    )
    assert overlap_integral['tracker_econ_source_candidate_available'] is False
    assert overlap_integral['approved_overlap_closes_formula_link'] is False
    assert overlap_integral['phase_model'] == 'phase_zero_current_helper_only'
    assert overlap_integral['phase_model_certified'] is False
    assert overlap_integral['window_mechanic_ids'] == [
        'golden_tower',
        'black_hole_coin',
        'golden_bot',
    ]
    assert overlap_integral['window_inputs_available'] is True
    assert overlap_integral['pair_overlap_fraction_source'] == (
        'simulators.timing.overlap_fraction'
    )
    assert overlap_integral['pair_overlap_fraction_formula_status'] == (
        'phase_zero_current_helper_pairwise_fraction_only'
    )
    assert overlap_integral['multiplier_only_without_window_model'] == [
        'state::uw.death_wave.coin_bonus_multiplier',
        'state::uw.spotlight.coin_bonus_multiplier',
    ]
    assert overlap_integral['remaining_to_certify'] == [
        'phase_offsets_or_sync_schedule',
        'kill_density_inside_each_econ_window',
        'death_wave_coin_bonus_active_window_or_kill_state',
        'spotlight_coin_exposure_fraction_by_kill',
        'wave_skip_reward_interaction_with_econ_windows',
    ]
    assert set(econ_sync['pair_overlap_fractions']) == {
        'golden_tower__black_hole_coin',
        'golden_tower__golden_bot',
        'black_hole_coin__golden_bot',
    }
    assert overlap_integral['pair_overlap_fractions'] == econ_sync['pair_overlap_fractions']
    assert econ_sync['pair_overlap_fractions']['golden_tower__black_hole_coin'] >= 0.0
    assert econ_sync['diagnostic_average_combined_multiplier_for_available_windows'] > 0.0
    assert 'state::uw.death_wave.coin_bonus_multiplier' in econ_sync[
        'multiplier_only_without_window_model'
    ]
    assert 'wave_skip_reward_interaction_with_econ_windows' in econ_sync['missing_to_certify']
    spawn_density = readiness['spawn_density_readiness']
    assert spawn_density['status'] == 'spawn_rate_curve_available_kill_density_transform_missing'
    assert spawn_density['application'] == 'diagnostic_only_not_coin_formula'
    assert spawn_density['target_wave'] == 5761
    assert spawn_density['wave_accelerator_spawn_rate_acceleration'] == pytest.approx(1.8)
    assert spawn_density['displayed_spawn_rate'] == pytest.approx(56.0)
    assert spawn_density['normal_enemy_spawn_count_curve_available'] is False
    kill_density_transform = spawn_density['kill_density_transform_readiness']
    assert kill_density_transform['status'] == (
        'source_spawn_rate_available_kill_density_transform_missing'
    )
    assert kill_density_transform['owner'] == 'simulators.timing'
    assert kill_density_transform['application'] == 'diagnostic_only_not_coin_formula'
    assert kill_density_transform['certification_effect'] == 'none'
    assert kill_density_transform['tier'] == 14
    assert kill_density_transform['target_wave'] == 5761
    assert kill_density_transform['displayed_spawn_rate'] == pytest.approx(56.0)
    assert kill_density_transform['wave_accelerator_spawn_rate_acceleration'] == pytest.approx(1.8)
    assert kill_density_transform['normal_spawn_rate_pressure_index'] == pytest.approx(56.0)
    assert kill_density_transform['normal_enemy_spawn_count_curve_available'] is False
    assert kill_density_transform['tracker_candidate_status'] == 'not_supplied'
    assert kill_density_transform['tracker_candidate_can_promote'] is False
    assert kill_density_transform[
        'operator_approved_tracker_empirical_kill_density_transform'
    ] is False
    assert kill_density_transform['operator_approval_status'] == 'not_approved'
    assert kill_density_transform['approval_runtime_input'] == (
        'approve_tracker_empirical_kill_density_transform'
    )
    assert kill_density_transform['approved_transform_closes_formula_link'] is False
    assert kill_density_transform['source_input_status'] == {
        'normal_spawn_rate_curve_by_wave_and_wave_accelerator': True,
        'displayed_spawn_rate_available': True,
        'wave_accelerator_spawn_rate_acceleration_available': True,
        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase': False,
    }
    assert kill_density_transform['remaining_to_certify'] == [
        'source_owned_normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase',
        'approved_spawn_rate_to_kill_density_transform',
        'tier_wave_spawn_phase_validation_set',
        'integration_with_intro_sprint_wave_skip_and_econ_windows',
    ]
    spawn_count_audit = spawn_density['normal_enemy_spawn_count_source_audit']
    assert spawn_count_audit['status'] == 'source_not_found_spawn_rate_curve_only'
    assert spawn_count_audit['application'] == 'diagnostic_only_not_coin_formula'
    assert spawn_count_audit['certification_effect'] == 'none'
    assert 'kb/enemies/tables/wiki-advanced-analysis-spawn-rate-wave-thresholds.csv' in (
        spawn_count_audit['local_kb_tables_checked']
    )
    assert 'kb/enemies/tables/note-derived-enemy-spawn-caps.csv' in (
        spawn_count_audit['local_kb_tables_checked']
    )
    assert 'https://the-tower-idle-tower-defense.fandom.com/wiki/AdvancedAnalysis' in (
        spawn_count_audit['external_sources_checked']
    )
    assert spawn_count_audit['source_backed_available_surfaces'] == [
        'normal_spawn_rate_wave_thresholds',
        'normal_enemy_on_screen_spawn_cap',
        'elite_spawn_thresholds',
        'fleet_spawn_schedule',
    ]
    assert spawn_count_audit['missing_source_owned_surface'] == (
        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase'
    )
    pressure_driver_evidence = spawn_density['non_boss_pressure_driver_evidence']
    assert pressure_driver_evidence['status'] == (
        'driver_inputs_available_terminal_transform_missing'
    )
    assert pressure_driver_evidence['application'] == 'diagnostic_only_not_coin_formula'
    assert pressure_driver_evidence['certification_effect'] == 'none'
    assert pressure_driver_evidence['tier'] == 14
    assert pressure_driver_evidence['wave'] == 5761
    assert pressure_driver_evidence['wave_accelerator_spawn_rate_acceleration'] == pytest.approx(1.8)
    assert pressure_driver_evidence['enemy_balance_mastery_double_elite_chance_pct'] == pytest.approx(0.0)
    assert pressure_driver_evidence['normal_spawn_rate_pressure']['displayed_spawn_rate'] == pytest.approx(56.0)
    assert pressure_driver_evidence['elite_spawn_pressure']['elite_pressure_index_pct'] == pytest.approx(66.0)
    assert pressure_driver_evidence['fleet_spawn_pressure']['fleet_events_per_wave_pressure'] == pytest.approx(0.001)
    assert pressure_driver_evidence['fleet_spawn_pressure'][
        'fleet_related_enemy_group_expected_enemies_per_wave_pressure'
    ] == pytest.approx(0.012)
    assert pressure_driver_evidence['source_backed_curve_coverage'] == {
        'normal_spawn_rate_curve_by_wave_and_wave_accelerator': True,
        'elite_spawn_curve_by_tier_and_wave': True,
        'fleet_spawn_curve_by_tier_and_wave': True,
        'fleet_related_enemy_group_count_range': True,
        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase': False,
    }
    assert 'normal_elite_fleet_pressure_composition_rule' in pressure_driver_evidence[
        'missing_terminal_formula_links'
    ]
    assert spawn_density['tracker_enemy_density_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
    }
    assert spawn_density['tracker_kill_density_transform_candidate'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert spawn_density['tracker_kill_density_stability_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert spawn_density['tracker_coin_density_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
    }
    assert spawn_density['tracker_coin_yield_stability_evidence'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert spawn_density['tracker_coin_integral_candidate'] == {
        'status': 'not_supplied',
        'application': 'external_observation_not_account_truth',
        'certification_effect': 'none',
    }
    assert 'kb/enemies/tables/wiki-advanced-analysis-spawn-rate-wave-thresholds.csv' in spawn_density[
        'source_tables'
    ]
    assert 'spawn_rate_to_enemy_kill_density_by_wave' in spawn_density['missing_to_certify']
    assert readiness['driver_coverage']['total'] >= 20
    assert readiness['current_timing_projection']['observed_run_hours'] == 5.5
    assert readiness['current_timing_projection'][
        'effective_game_speed_multiplier_for_diagnostic'
    ] == 6.25
    assert readiness['current_timing_projection']['estimated_run_hours_after_game_speed'] > 0.0
    assert (
        readiness['current_timing_projection'][
            'estimated_run_hours_after_wave_skip_intro_and_game_speed'
        ]
        > 0.0
    )
    assert (
        readiness['current_timing_projection'][
            'estimated_run_hours_after_wave_skip_intro_and_game_speed'
        ]
        < readiness['current_timing_projection']['estimated_run_hours_after_game_speed']
    )


def test_ep_compare_artifacts_preserve_current_alignment_and_stage_scope_limits():
    diagnostics = json.loads((ROOT / 'out' / 'diagnostics.json').read_text(encoding='utf-8'))
    compare = json.loads((ROOT / 'out' / 'ep_oracle_compare.json').read_text(encoding='utf-8'))
    line_verification = json.loads(
        (ROOT / 'out' / 'line_by_line_verification.json').read_text(encoding='utf-8')
    )

    summary = diagnostics['ep_compare_summary']
    status_counts = Counter(row.get('status') for row in compare.values())
    line_ep_rows = {
        surface_id: row
        for surface_id, row in line_verification.items()
        if row.get('ep_compare_status')
    }
    line_status_counts = Counter(row.get('ep_compare_status') for row in line_ep_rows.values())

    assert len(compare) == summary['ep_compare_count'] == 49
    assert dict(sorted(status_counts.items())) == {
        'matched_close': 9,
        'matched_exact': 17,
        'stage_scope_mismatch': 23,
    }
    assert summary['ep_compare_status_counts'] == dict(sorted(status_counts.items()))
    assert summary['ep_alignment_status'] == 'aligned_except_accounted_stage_scope_limits'
    assert summary['ep_clean_aligned_count'] == 26
    assert summary['ep_accounted_stage_scope_limit_count'] == 23
    assert summary['ep_unaccounted_alignment_gap_count'] == 0
    assert summary['ep_raw_formula_mismatch_count'] == 0
    assert summary['ep_true_formula_mismatch_count'] == 0
    assert summary['ep_known_export_defect_count'] == 0
    assert summary['ep_unknown_formula_mismatch_count'] == 0
    assert summary['ep_stage_scope_mismatch_count'] == 23
    assert summary['ep_stage_scope_rows_with_accounted_facets'] == 23
    assert summary['ep_stage_scope_rows_without_accounted_facets'] == 0
    assert summary['ep_stage_scope_unaccounted_destinations'] == []
    assert summary['ep_non_comparable_count'] == 0
    assert summary['ep_missing_from_package_count'] == 0

    assert set(line_ep_rows) == set(compare)
    assert dict(sorted(line_status_counts.items())) == dict(sorted(status_counts.items()))
    for surface_id, row in compare.items():
        line_row = line_ep_rows[surface_id]
        assert line_row['ep_compare_status'] == row['status']
        if row['status'] in {'matched_exact', 'matched_close'}:
            assert row['kb_alignment_status'] == 'aligned'
            assert row['verdict'] == 'pass'
            assert line_row['kb_alignment_status'] == 'aligned'
            assert line_row['verdict'] == 'pass'
        else:
            assert row['status'] == 'stage_scope_mismatch'
            assert row['kb_alignment_status'] == 'not_comparable'
            assert row['verdict'] == 'pass_with_compare_limitations'
            assert 'ep_compare_uses_unsupported_stage_facets' in (row.get('compare_notes') or [])
            assert line_row['kb_alignment_status'] == 'not_comparable'
            assert line_row['verdict'] == 'pass_with_compare_limitations'


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
    derived_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'derived_wall_economy'
    )
    derived_section = next(
        table for table in (derived_panel.get('payload', {}).get('objective_tables') or [])
        if table.get('title') == 'eHP'
    )
    other_derived_section = next(
        section for section in (derived_panel.get('payload', {}).get('sections') or [])
        if section.get('title') == 'Derived'
    )
    labels = [row.get('modifier') for row in (derived_section.get('rows') or [])]
    other_labels = [row.get('name') for row in (other_derived_section.get('rows') or [])]
    canonical_row_ids = [row.get('canonical_row_id') for row in (other_derived_section.get('rows') or [])]
    objective_titles = [table.get('title') for table in (derived_panel.get('payload', {}).get('objective_tables') or [])]
    assert objective_titles == ['eHP', 'eDamage', 'eEcon']
    assert 'Base Pool' not in other_labels
    assert 'Wall HP (Pre-Fort)' in other_labels
    assert 'Ultimate Weapon Damage' in other_labels
    assert 'derived::wall.hp_pre_fort' in canonical_row_ids
    assert 'derived::wall.hp_final' in canonical_row_ids


def test_stats_dashboard_primary_derived_panel_publishes_objective_breakdowns():
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
    query_rows = {
        'Farming': {
            'rows': {
                'derived::ehp': {'display_value': '10', 'final_value': 10, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::edamage': {'display_value': '20', 'final_value': 20, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::eecon': {'display_value': '30', 'final_value': 30, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::ehp.pre_defense_pool': {'display_value': '40', 'final_value': 40, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::ehp.defense_taken_factor': {'display_value': 'x5', 'final_value': 5, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::ehp.tradeoff_defense_factor': {'display_value': 'x1.2', 'final_value': 1.2, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::ehp.chrono_field_damage_reduction_factor': {'display_value': 'x1.3', 'final_value': 1.3, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::ehp.chain_thunder_factor': {'display_value': 'x1.4', 'final_value': 1.4, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::ehp.primordial_black_hole_damage_reduction_factor': {'display_value': 'x1.5', 'final_value': 1.5, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::edamage.base_damage_stack': {'display_value': '100', 'final_value': 100, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::edamage.bullet_crit_factor': {'display_value': 'x2', 'final_value': 2, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::edamage.bullet_pipeline_factor': {'display_value': 'x3', 'final_value': 3, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::edamage.spotlight_factor': {'display_value': 'x4', 'final_value': 4, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::edamage.uw_total_damage': {'display_value': '200', 'final_value': 200, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::edamage.uw_crit_factor': {'display_value': 'x5', 'final_value': 5, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::edamage.slow_factor': {'display_value': 'x6', 'final_value': 6, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::eecon.cl_factor': {'display_value': 'x1.1', 'final_value': 1.1, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::eecon.eom_factor': {'display_value': 'x1.2', 'final_value': 1.2, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::eecon.sync_factor': {'display_value': 'x1.3', 'final_value': 1.3, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::eecon.spotlight_coin_factor': {'display_value': 'x1.4', 'final_value': 1.4, 'value_type': 'multiplier', 'status': 'resolved'},
                'derived::eecon.wave_factor': {'display_value': 'x1.5', 'final_value': 1.5, 'value_type': 'multiplier', 'status': 'resolved'},
            }
        }
    }
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run=query_rows,
        query_rows_max_progression=query_rows,
        ep_compare_publishable={},
        line_verification={},
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    derived_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'derived_wall_economy')
    objective_tables = derived_panel.get('payload', {}).get('objective_tables') or []
    assert [table.get('title') for table in objective_tables] == ['eHP', 'eDamage', 'eEcon']
    ehp_table = objective_tables[0]
    assert ehp_table['summary_value'] == '10'
    ehp_rows = {row.get('modifier'): row for row in (ehp_table.get('rows') or [])}
    assert ehp_rows['Base Pool']['surface_id'] == 'derived::ehp.pre_defense_pool'
    assert ehp_rows['Primordial BH DR Factor']['value'] == 'x1.5'
    edamage_table = objective_tables[1]
    edamage_rows = {row.get('modifier'): row for row in (edamage_table.get('rows') or [])}
    assert edamage_table['summary_value'] == '20'
    assert edamage_rows['UW Total Damage']['surface_id'] == 'derived::edamage.uw_total_damage'
    assert edamage_rows['Slow Factor']['value'] == 'x6'
    eecon_table = objective_tables[2]
    eecon_rows = {row.get('modifier'): row for row in (eecon_table.get('rows') or [])}
    assert eecon_table['summary_value'] == '30'
    assert eecon_rows['Meta Stack']['surface_id'] == 'derived::eecon.cl_factor'
    assert eecon_rows['Wave Factor']['value'] == 'x1.5'


def test_stats_dashboard_primary_derived_panel_uses_selected_state_mode_for_objective_tables():
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
                'derived::ehp': {'display_value': '10', 'final_value': 10, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::ehp.pre_defense_pool': {'display_value': '40', 'final_value': 40, 'value_type': 'scalar', 'status': 'resolved'},
            }
        }
    }
    query_rows_max = {
        'Farming': {
            'rows': {
                'derived::ehp': {'display_value': '99', 'final_value': 99, 'value_type': 'scalar', 'status': 'resolved'},
                'derived::ehp.pre_defense_pool': {'display_value': '88', 'final_value': 88, 'value_type': 'scalar', 'status': 'resolved'},
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

    derived_panel = next(panel for panel in payload['variants']['Farming']['max_progression'] if panel.get('panel_id') == 'derived_wall_economy')
    ehp_table = next(table for table in (derived_panel.get('payload', {}).get('objective_tables') or []) if table.get('title') == 'eHP')
    assert ehp_table['summary_value'] == '99'
    ehp_rows = {row.get('modifier'): row for row in (ehp_table.get('rows') or [])}
    assert ehp_rows['Base Pool']['value'] == '88'


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
    derived_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'derived_wall_economy')
    derived_section = next(
        section for section in (derived_panel.get('payload', {}).get('sections') or [])
        if section.get('title') == 'Derived'
    )
    derived_rows = derived_section.get('rows') or []
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

    derived_panel = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'derived_wall_economy'
    )
    derived_section = next(
        section for section in (derived_panel.get('payload', {}).get('sections') or [])
        if section.get('title') == 'Derived'
    )
    derived_rows = {row.get('name'): row for row in (derived_section.get('rows') or [])}
    assert derived_rows['Wall Thorns']['start_of_run_value'] == '—'
    assert derived_rows['Wall Thorns']['status'] == 'missing'


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
    uw_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'ultimate_weapons')
    columns = [column.get('label') for column in (uw_panel.get('payload', {}).get('columns') or [])]
    assert columns == ['Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Start of Run', 'Perk', 'Max Progression', 'Other', 'Recon']
    sections = {section.get('title'): section for section in (uw_panel.get('payload', {}).get('sections') or [])}
    rows_by_name = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    assert rows_by_name['Cooldown']['workshop_level'] == '2'
    assert rows_by_name['Cooldown']['stone_value'] == '180s'
    assert rows_by_name['Cooldown']['start_of_run_value'] == '180s'
    assert rows_by_name['Cooldown']['max_progression_value'] == '160s'
    assert rows_by_name['Duration']['workshop_level'] == '3'
    assert rows_by_name['Duration']['start_of_run_value'] == '42s'


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
    assert [section.get('title') for section in sections] == ['Chrono Field', 'Golden Tower', 'Black Hole']
    chrono_rows = [row.get('name') for row in (sections[0].get('rows') or [])]
    assert chrono_rows[:3] == ['Duration', 'Speed Reduction', 'Cooldown']


def test_stats_dashboard_primary_uw_operator_table_wires_module_other_and_recon_fields():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    stat_inputs_payload = [
        {'destination_id': 'state::uw.chain_lightning.damage_multiplier', 'source_family': 'module_unique', 'source_name': 'Dimension Core', 'value': 2.25},
        {'destination_id': 'state::uw.chain_lightning.max_enemy_damage_reduction_pct', 'source_family': 'module_unique', 'source_name': 'Chain Thunder', 'value': 22.0},
        {'destination_id': 'state::uw.golden_tower.duration_seconds', 'source_family': 'lab', 'source_name': 'Golden Tower Duration Lab', 'value': 15.0},
        {'destination_id': 'state::uw.black_hole.duration_seconds', 'source_family': 'module_unique', 'source_name': 'Multiverse Nexus', 'value': 4.0},
        {'destination_id': 'state::uw.black_hole.cooldown_seconds', 'source_family': 'module_unique', 'source_name': 'Multiverse Nexus', 'value': -4.0},
        {'destination_id': 'state::uw.chrono_field.duration_seconds', 'source_family': 'lab', 'source_name': 'Chrono Field Duration Lab', 'value': 30.0},
        {'destination_id': 'state::uw.chrono_field.slow_pct', 'source_family': 'module_unique', 'source_name': 'Dimension Core', 'value': 2.25},
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
    golden_rows = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    black_hole_rows = {row.get('name'): row for row in (sections['Black Hole'].get('rows') or [])}
    assert golden_rows['Duration']['lab_effects'] == '20s'
    assert golden_rows['Duration']['reconciliation_status'] == 'green'
    assert black_hole_rows['Duration']['module_effects'] == '4s'
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
    totals_rows = {row.get('name'): row for row in (sections['Totals'].get('rows') or [])}
    assert [section.get('title') for section in (bot_panel.get('payload', {}).get('sections') or [])] == ['Amplify', 'Flame', 'Golden', 'Thunder', 'Totals']
    assert [row.get('name') for row in (sections['Amplify'].get('rows') or [])] == ['Bonus', 'Cooldown', 'Duration', 'Range']
    assert amplify_rows['Range']['medal_level'] == '0'
    assert amplify_rows['Range']['medals_spent'] == '0'
    assert amplify_rows['Range']['medal_value'] == '25m'
    assert amplify_rows['Range']['start_of_run_value'] == '0m'
    assert amplify_rows['Range']['module_effects'] == '+ 15'
    assert amplify_rows['Range']['reconciliation_status'] == 'green'
    assert golden_rows['Range']['start_of_run_value'] == '70m'
    assert golden_rows['Range']['module_effects'] == '+ 15'
    assert golden_rows['Range']['reconciliation_status'] == 'green'
    assert totals_rows['Total']['medals_spent'] == '1980'


def test_stats_dashboard_primary_modules_panel_publishes_grouped_summary_rows():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    query_rows_start = json.loads((ROOT / 'out' / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    query_rows_max = json.loads((ROOT / 'out' / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))
    module_card_payloads = _module_card_payloads_from_account_state_payload(account_state)
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
    assert by_key[('', 'Max Level')]['cannon'] == '240'
    assert by_key[('', 'Assist %')]['armor'] == '1%'
    assert by_key[('Primary', 'Module')]['generator'] == 'Singularity Harness'
    assert by_key[('Assist', 'Module')]['cannon'] == '—'
    assert by_key[('Current', 'Multiplier')]['core'] == 'x13.53'
    assert ('Recon', 'Recon') not in by_key


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
            'Guardians': [
                ['Attack', '', 'Percentage', '0.01', '00 | 1% | Cost 0 ? | Next 25 ?'],
                ['', '', 'Cooldown', '120', '00 | 120s | Cost 0 ? | Next 1 ?'],
                ['true', 'Unlocked', 'Targets', '1', '00 | 1 | Cost 0 ? | Next 100 ?'],
            ],
        },
        'uw_tracks': {},
        'ultimate_weapons': {},
        'bot_upgrade_tracks': {},
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
    bot_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'bots')
    guardian_panel = next(panel for panel in payload['variants']['Farming']['start_of_run'] if panel.get('panel_id') == 'guardians')
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
    assert bot_rows['Range']['module_effects'] == '+ 15'
    assert bot_rows['Range']['reconciliation_status'] == 'green'
    assert guardian_rows['Cooldown']['bit_level'] == '0'
    assert guardian_rows['Cooldown']['bits_spent'] == '0'
    assert guardian_rows['Cooldown']['bit_value'] == '120s'
    assert guardian_rows['Cooldown']['start_of_run_value'] == '120s'
    assert guardian_rows['Cooldown']['reconciliation_status'] == 'green'
    guardian_totals = {row.get('name'): row for row in (guardian_sections['Totals'].get('rows') or [])}
    assert guardian_totals['Total']['bits_spent'] == '0'


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
    assert [section.get('title') for section in sections] == ['Chrono Field', 'Golden Tower', 'Black Hole']
    chrono_rows = [row.get('name') for row in (sections[0].get('rows') or [])]
    assert chrono_rows[:3] == ['Duration', 'Speed Reduction', 'Cooldown']


def test_stats_dashboard_primary_uw_operator_table_wires_module_other_and_recon_fields():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    stat_inputs_payload = [
        {'destination_id': 'state::uw.chain_lightning.damage_multiplier', 'source_family': 'module_unique', 'source_name': 'Dimension Core', 'value': 2.25},
        {'destination_id': 'state::uw.chain_lightning.max_enemy_damage_reduction_pct', 'source_family': 'module_unique', 'source_name': 'Chain Thunder', 'value': 22.0},
        {'destination_id': 'state::uw.golden_tower.duration_seconds', 'source_family': 'lab', 'source_name': 'Golden Tower Duration Lab', 'value': 20.0},
        {'destination_id': 'state::uw.black_hole.duration_seconds', 'source_family': 'module_unique', 'source_name': 'Multiverse Nexus', 'value': 4.0},
        {'destination_id': 'state::uw.black_hole.cooldown_seconds', 'source_family': 'module_unique', 'source_name': 'Multiverse Nexus', 'value': -4.0},
        {'destination_id': 'state::uw.chrono_field.duration_seconds', 'source_family': 'lab', 'source_name': 'Chrono Field Duration Lab', 'value': 30.0},
        {'destination_id': 'state::uw.chrono_field.slow_pct', 'source_family': 'module_unique', 'source_name': 'Dimension Core', 'value': 2.25},
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
    golden_rows = {row.get('name'): row for row in (sections['Golden Tower'].get('rows') or [])}
    black_hole_rows = {row.get('name'): row for row in (sections['Black Hole'].get('rows') or [])}
    chrono_rows = {row.get('name'): row for row in (sections['Chrono Field'].get('rows') or [])}
    assert golden_rows['Duration']['lab_effects'] == '20s'
    assert golden_rows['Duration']['reconciliation_status'] == 'green'
    assert black_hole_rows['Duration']['module_effects'] == '4s'
    assert black_hole_rows['Duration']['start_of_run_value'] == '36s'
    assert black_hole_rows['Duration']['perk_effects'] == '+ 12s'
    assert black_hole_rows['Duration']['max_progression_value'] == '48s'
    assert black_hole_rows['Duration']['reconciliation_status'] == 'green'
    assert black_hole_rows['Cooldown']['start_of_run_value'] == '46s'
    assert black_hole_rows['Cooldown']['reconciliation_status'] == 'green'
    assert chrono_rows['Duration']['stone_value'] == '20s'
    assert chrono_rows['Duration']['lab_effects'] == '30s'
    assert chrono_rows['Duration']['perk_effects'] == '+ 5'
    assert chrono_rows['Duration']['max_progression_value'] == '55s'
    assert chrono_rows['Duration']['reconciliation_status'] == 'green'
    assert chrono_rows['Cooldown']['start_of_run_value'] == '60s'
    assert chrono_rows['Cooldown']['reconciliation_status'] == 'green'
    assert chrono_rows['Speed Reduction']['stone_value'] == '70%'
    assert chrono_rows['Speed Reduction']['module_effects'] == '2.25%'
    assert chrono_rows['Speed Reduction']['start_of_run_value'] == '72.85%'
    assert chrono_rows['Speed Reduction']['reconciliation_status'] == 'green'
