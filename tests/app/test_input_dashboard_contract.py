from __future__ import annotations

import json
from pathlib import Path

from app.publication import _build_input_dashboard_payload, _build_labs_panel, _preset_options

ROOT = Path(__file__).resolve().parents[2]


def test_input_dashboard_panel_contract_and_no_placeholder_headers():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    payload = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    assert payload.get('schema_version') == 2
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
    assert 'groups' in (workshop_panel.get('payload') or {})
    assert 'rows' not in (workshop_panel.get('payload') or {})
    grouped_rows = []
    for group_name in ['offense', 'defense', 'utility']:
        grouped_rows.extend(((workshop_panel.get('payload') or {}).get('groups') or {}).get(group_name) or [])
    if grouped_rows:
        assert sorted(grouped_rows[0].keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']

    uw_panel = next(panel for panel in payload['panels'] if panel['panel_id'] == 'ultimate_weapons')
    uw_rows = (uw_panel.get('payload') or {}).get('rows') or []
    if uw_rows:
        assert sorted(uw_rows[0].keys()) == [
            'final',
            'lab',
            'module',
            'perk',
            'stone_level',
            'stone_value',
            'track',
            'unlock',
            'uw',
            'uw_plus',
        ]


def test_input_dashboard_uw_upstream_gaps_are_field_conditional():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    payload = _build_input_dashboard_payload(
        account_state,
        {},
        module_card_payloads={},
        qe_dashboard_publications={
            'uw_track_effects': {
                'Chain Lightning::Damage': {
                    'module_effect': 'x2.25',
                    'perk_effect': '5',
                    'final_value': 'x903',
                }
            }
        },
    )
    uw_damage_gaps = [
        gap for gap in (payload.get('upstream_gaps') or [])
        if gap.get('panel_id') == 'ultimate_weapons' and 'Chain Lightning::Damage' in str(gap.get('detail') or '')
    ]
    uw_damage_gap_ids = [gap.get('gap_id') for gap in uw_damage_gaps]
    assert 'module_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'perk_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'final_column_not_published_upstream' not in uw_damage_gap_ids


def test_modules_panel_uses_module_card_payload_shape_when_available():
    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    module_payloads = {'presets': {'Farming': {'cannon': {'primary': {'module_name': 'ACP'}}}}}
    payload = _build_input_dashboard_payload(account_state, {}, module_card_payloads=module_payloads)
    modules_panel = next(panel for panel in payload['panels'] if panel['panel_id'] == 'modules')
    assert 'cannon' in (modules_panel.get('payload') or {}).get('slots', {})


def test_preset_options_canonical_order_with_stable_extras():
    account_state_payload = {
        'default_preset': 'Tourney',
        'card_presets': {'Preset X': [], 'Farming': []},
        'module_presets': {'Milestone': {}, 'Preset Y': {}},
        'workshop': {
            'Damage': {
                'preset_levels': {'Preset Z': 1, 'Tourney': 2},
                'preset_values': {'Preset Q': 3},
            }
        },
        'workshop_enhancement_tracks': {
            'Enhancement': {
                'preset_levels': {'Preset R': 4},
            }
        },
    }

    assert _preset_options(account_state_payload) == [
        'Farming',
        'Tourney',
        'Milestone',
        'Preset X',
        'Preset Y',
        'Preset Z',
        'Preset Q',
        'Preset R',
    ]


def test_preset_options_includes_default_when_upstream_missing():
    account_state_payload = {
        'default_preset': 'Preset 4',
        'card_presets': {'Milestone': []},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
    }

    assert _preset_options(account_state_payload) == ['Milestone', 'Preset 4']


def test_preset_options_defaults_to_default_preset_when_no_sources():
    account_state_payload = {
        'default_preset': 'Tourney',
        'card_presets': {},
        'module_presets': {},
        'workshop': {},
        'workshop_enhancement_tracks': {},
    }
    assert _preset_options(account_state_payload) == ['Tourney']


def test_publication_contains_single_dashboard_builder_definition():
    text = (ROOT / 'app' / 'publication.py').read_text(encoding='utf-8')
    assert text.count('def _build_input_dashboard_payload(') == 1


def test_labs_panel_unmapped_rows_emit_gap_when_misc_bucket_missing():
    panel, gaps = _build_labs_panel(
        {
            'raw_sections': {
                'Labs': [
                    ['Unmapped Lab', '25', '', '50'],
                ]
            }
        },
        {
            'labs': {
                'bucket_order': ['attack_defense'],
                'bucket_labels': {'attack_defense': 'Attack / Defense'},
                'bucket_registry': {},
            }
        },
    )
    assert panel['panel_id'] == 'labs'
    assert panel['payload']['buckets'] == []
    assert gaps == [
        {
            'panel_id': 'labs',
            'gap_id': 'lab_bucket_not_published_upstream',
            'detail': 'Bucket mapping missing for Unmapped Lab',
        }
    ]
