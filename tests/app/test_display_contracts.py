from __future__ import annotations

from app.display import (
    _format_display_number,
    annotate_compare_display_fields,
    annotate_display_fields,
    render_grouped_workshop_table_html,
    render_labs_bucket_grid_html,
    render_simple_metric_panel_html,
    render_workshop_stat_table_html,
    render_uw_track_table_html,
)


def test_format_display_number_preserves_significant_integer_zeros():
    assert _format_display_number(179723381637158.78) == '180T'
    assert _format_display_number(1010000000000) == '1.01T'


def test_display_helpers_preserve_output_contract():
    statbook = {
        'rows': {
            'damage': {
                'final_value': 1010000000000,
                'value_type': None,
                'contributors': [
                    {'value': 0.125, 'value_type': 'pct'},
                    {'value': 2.5, 'value_type': 'multiplier_display'},
                    {'value': False, 'value_type': None},
                ],
            },
        },
    }
    annotate_display_fields(statbook)
    row = statbook['rows']['damage']
    assert row['display_value'] == '1.01T'
    assert [c['display_value'] for c in row['contributors']] == ['0.125%', 'x2.5', 'false']

    compare = {
        'wall_hp': {
            'package_value': 114000000000000,
            'package_value_type': None,
            'ep_value_type': 'percent_display',
            'ep_value_parsed': 0.125,
            'compare_notes': ['ep_decimal_fraction_scaled_to_percent_points'],
            'delta': 2500000,
            'relative_delta_pct': 12.5,
        },
        'coin_bonus': {
            'package_value': 3.5,
            'package_value_type': 'multiplier',
            'ep_value_type': 'multiplier_display',
            'ep_value_parsed': 4.25,
            'compare_notes': [],
            'delta': 0.75,
            'relative_delta_pct': None,
        },
    }
    annotate_compare_display_fields(compare)
    assert compare['wall_hp']['package_value_display'] == '114T'
    assert compare['wall_hp']['ep_value_display'] == '12.5%'
    assert compare['wall_hp']['delta_display'] == '2.5M'
    assert compare['wall_hp']['relative_delta_display'] == '12.5%'
    assert compare['coin_bonus']['package_value_display'] == 'x3.5'
    assert compare['coin_bonus']['ep_value_display'] == 'x4.25'
    assert compare['coin_bonus']['delta_display'] == 'x0.75'
    assert compare['coin_bonus']['relative_delta_display'] is None


def test_contributor_display_uses_input_value_type_when_available():
    statbook = {
        'rows': {
            'state::tower.defense_pct': {
                'final_value': 98.0,
                'value_type': 'pct',
                'contributors': [
                    {'value': 69.3, 'value_type': 'scalar', 'input_value_type': 'pct'},
                    {'value': 1.2, 'value_type': 'scalar', 'input_value_type': 'multiplier'},
                    {'contributor_id': 'workshop__tower__defense_pct__pct', 'value': 30.0, 'value_type': 'scalar'},
                ],
            },
        },
    }
    annotate_display_fields(statbook)
    contributors = statbook['rows']['state::tower.defense_pct']['contributors']
    assert contributors[0]['display_value'] == '69.3%'
    assert contributors[1]['display_value'] == 'x1.2'
    assert contributors[2]['display_value'] == '30%'


def test_labs_renderer_contains_bucket_labels_and_rows():
    html = render_labs_bucket_grid_html(
        {
            'column_headers': ['Name', 'Level', 'Max'],
            'buckets': [{'bucket_label': 'Attack / Defense', 'rows': [{'name': 'Damage Lab', 'level': '50', 'max': ''}]}],
        }
    )
    assert 'Attack / Defense' in html
    assert 'Damage Lab' in html


def test_workshop_renderer_contains_group_labels():
    html = render_grouped_workshop_table_html(
        {
            'column_headers': ['Unlock', 'Name', 'Coin Level', 'Coin Value', 'Max Level', 'Max Value'],
            'groups': {'offense': [{'unlock': '', 'name': 'Damage', 'coin_level': '10', 'coin_value': '100', 'max_level': '20', 'max_value': ''}], 'defense': [], 'utility': []},
        }
    )
    assert 'Offense' in html
    assert 'Defense' in html
    assert 'Utility' in html
    assert 'inputs-triple' in html
    assert 'inputs-table-compact' in html


def test_uw_renderer_contains_expected_columns():
    html = render_uw_track_table_html(
        {
            'column_headers': ['Unlock', 'UW', 'Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Perk', 'Final', 'UW+'],
            'rows': [],
        }
    )
    assert 'Stone Level' in html
    assert 'UW+' in html


def test_simple_metric_panel_renders_theme_label():
    html = render_simple_metric_panel_html({'metric_label': 'Coin Multiplier', 'metric_value': '1.23'})
    assert 'Coin Multiplier' in html
    assert '1.23' in html


def test_workshop_stats_renderer_uses_grouped_phase_headers_and_totals():
    html = render_workshop_stat_table_html(
        {
            'sections': [
                {
                    'title': 'Offense',
                    'rows': [
                            {
                                'name': 'Damage',
                                'reconciliation_status': 'green',
                                'workshop_level': '100',
                                'workshop_value': '100',
                                'lab_effects': '+ 5',
                            'base_subtotal': '+ 11',
                            'module_effects': '+ 2',
                            'card_effects': '+ 3',
                            'relics': '+ 6',
                            'base_loadout_subtotal': '+ 16',
                            'enhancement_effects': '+ 4',
                            'start_of_run_modifier_total': '+ 20',
                            'start_of_run_value': '200',
                            'other': '+ 5',
                            'max_workshop_modifier_total': '+ 25',
                            'max_workshop_value': '250',
                            'max_workshop_resolved_value': '300',
                            'perk_effects': '+ 10',
                            'max_progression_value': '260',
                        }
                    ],
                }
            ]
        }
    )
    assert 'Workshop<br>Start Level' in html
    assert 'Start of Run' in html
    assert 'Max Workshop' in html
    assert 'Perks' in html
    assert html.count('>Total<') == 2
    assert 'recon-dot green' in html
    assert 'Lab Effects' not in html
    assert 'Module Effects' not in html
    assert 'Card Effects' not in html
    assert 'Enhancement Effects' not in html
    assert 'Perk Effects' not in html
    assert 'Base Modifiers' in html
    assert 'Base &amp; Loadout' in html
    assert "colspan='18'" in html
    assert '250' in html
    assert '300' in html
    assert html.index('>Relics<') < html.index('>Subtotal<') < html.index('>Module<')
    assert html.index('>Start of Run<') < html.index('>Max Workshop<') < html.index('>Perks<')


def test_workshop_stats_renderer_collapses_neutral_effect_tokens_to_dash():
    html = render_workshop_stat_table_html(
        {
            'sections': [
                {
                    'title': 'Offense',
                    'rows': [
                        {
                            'name': 'Damage',
                            'workshop_level': '100',
                            'workshop_value': '100',
                            'lab_effects': '—',
                            'module_effects': '—',
                            'card_effects': '—',
                            'enhancement_effects': '—',
                            'relics': '—',
                            'start_of_run_modifier_total': 'x 1',
                            'start_of_run_value': '100',
                            'max_workshop_value': '100',
                            'perk_effects': '—',
                            'other': '+ 0%',
                            'max_progression_modifier_total': '+ 0',
                            'max_progression_value': '100',
                        }
                    ],
                }
            ]
        }
    )
    assert 'x 1' not in html
    assert '+ 0%' not in html
    assert '+ 0<' not in html
