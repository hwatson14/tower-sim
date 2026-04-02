from __future__ import annotations

from app.display import (
    _format_display_number,
    annotate_compare_display_fields,
    annotate_display_fields,
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
