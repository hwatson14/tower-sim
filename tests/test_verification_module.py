from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.verification import (
    annotate_compare_display_fields,
    build_ep_compare,
    build_line_by_line_verification,
    build_survivability_residue_analysis,
    build_survivor_closure_report,
    ensure_line_verification_authoritative_verdict_fields,
)


def _formula_contract(_ledger, destination):
    if destination == 'canonical_stat::tower_hp':
        return {'publish_policy': 'allow', 'destination': destination, 'compare_policy': 'normal'}
    return {'publish_policy': 'block' if destination == 'canonical_stat::blocked' else 'allow', 'destination': destination, 'compare_policy': 'normal'}


def _format_display_value(value, value_type):
    return f'{value_type}:{value}' if value is not None else None


def _format_display_number(value):
    return None if value is None else f'{value:.3f}' if isinstance(value, float) else str(value)


def test_build_ep_compare_and_display_annotation_preserve_compare_payload_shape():
    ep_oracle = {
        'canonical_stat::tower_hp': {
            'ep_value_parsed': 90.0,
            'ep_value_type': 'flat',
            'ep_value_raw': '90',
        }
    }
    statbook_rows_by_preset = {
        'Farming': {
            'canonical_stat::tower_hp': {
                'final_value': 100.0,
                'value_type': 'flat',
                'contributors': [{'source_name': 'Workshop HP', 'value': 100.0, 'value_type': 'flat'}],
            }
        }
    }
    package_stage_context = {
        'state_mode': 'max_progression',
        'default_compare_preset': 'Farming',
        'active_cards_by_preset': {'Farming': ['Attack Speed']},
        'active_modules_by_preset': {'Farming': {'core': {'primary': 'Core', 'assist': None}}},
        'modules_inventory': {'Core': {'rarity': 'epic'}},
    }

    compare = build_ep_compare(
        ep_oracle,
        statbook_rows_by_preset,
        {},
        package_stage_context,
        ep_stage_context_for_destination=lambda destination, ctx: {'compare_preset': 'Farming', 'compare_perk_state': 'on', 'destination': destination},
        compare_state_key_for_destination=lambda destination, default_preset: default_preset,
        contributor_snapshot=lambda row: [] if row is None else list(row.get('contributors', [])),
        apply_projected_runtime_compare_assumptions=lambda destination, row, ctx: (row, ['kept_runtime_value']),
        formula_contract=_formula_contract,
        normalize_compare_values=lambda destination, compare_policy, package_value, ep_value: (package_value, ep_value, []),
    )

    annotate_compare_display_fields(compare, _format_display_value, _format_display_number)
    tower_hp = compare['canonical_stat::tower_hp']
    assert tower_hp['status'] == 'mismatch'
    assert tower_hp['kb_alignment_status'] == 'misaligned'
    assert tower_hp['verdict'] == 'fail'
    assert tower_hp['runtime_compare_assumptions'] == ['kept_runtime_value']
    assert tower_hp['package_value_source_state_mode'] == 'max_progression'
    assert tower_hp['package_contributors'][0]['source_name'] == 'Workshop HP'
    assert tower_hp['package_value_display'] == 'flat:100.0'
    assert tower_hp['ep_value_display'] == '90.000'
    assert tower_hp['delta_display'] == '10.000'
    assert tower_hp['relative_delta_display'] == '11.111%'


def test_build_line_by_line_verification_preserves_payload_shape_and_statuses():
    statbook = {
        'rows': {
            'canonical_stat::tower_hp': {
                'status': 'resolved',
                'final_value': 100.0,
                'notes': 'Consumed 1/2 contributors',
                'schema': {
                    'unit': 'hp',
                    'resolver': 'sum',
                    'allowed_input_value_types': ['flat'],
                },
                'contributors': [
                    {'source_name': 'Workshop HP', 'value': 100.0, 'value_type': 'flat', 'notes': ''},
                    {'source_name': 'Mystery', 'value': None, 'value_type': 'raw_text', 'notes': 'unresolved upstream'},
                ],
            },
            'raw::trace': {
                'status': 'resolved',
                'final_value': 'trace',
                'notes': '',
                'schema': {'unit': 'n/a', 'resolver': 'trace', 'allowed_input_value_types': []},
                'contributors': [],
            },
            'canonical_stat::blocked': {
                'status': 'resolved',
                'final_value': 5,
                'notes': '',
                'schema': {'unit': 'x', 'resolver': 'mul', 'allowed_input_value_types': ['multiplier']},
                'contributors': [],
            },
        }
    }
    ep_compare = {
        'canonical_stat::tower_hp': {
            'status': 'mismatch',
            'delta': 10.0,
            'package_value': 100.0,
            'package_value_type': 'flat',
            'ep_value': 90.0,
            'ep_value_type': 'flat',
            'compare_preset': 'Farming',
            'compare_perk_state': 'on',
            'package_value_source_preset': 'Farming',
            'package_value_source_state_mode': 'max_progression',
            'ep_stage_context': {'wave': 100},
        },
        'canonical_stat::blocked': {
            'status': 'formula_blocked',
            'delta': None,
            'package_value': 5,
            'package_value_type': 'multiplier',
            'ep_value': 5,
            'ep_value_type': 'multiplier',
        },
    }

    verification = build_line_by_line_verification(statbook, ep_compare, {}, _formula_contract)

    tower_hp = verification['canonical_stat::tower_hp']
    assert tower_hp['verification_status'] == 'blocked'
    assert tower_hp['verdict'] == 'fail'
    assert tower_hp['issues'] == [
        'unresolved_contributor_present',
        'semantically_incompatible_contributor_present',
        'unconsumed_contributor_present',
        'ep_reference_mismatch',
    ]
    assert tower_hp['contributor_consumption'] == {'consumed': 1, 'listed': 2}
    assert tower_hp['compare_context'] == {
        'compare_preset': 'Farming',
        'compare_perk_state': 'on',
        'package_value_source_preset': 'Farming',
        'package_value_source_state_mode': 'max_progression',
        'ep_stage_context': {'wave': 100},
    }

    assert verification['raw::trace']['verification_status'] == 'trace_only'
    assert verification['raw::trace']['verdict'] == 'trace_only'
    assert verification['canonical_stat::blocked']['verification_status'] == 'blocked_formula_pending'
    assert verification['canonical_stat::blocked']['verdict'] == 'fail'


def test_line_verification_authoritative_fields_and_reporting_helpers_remain_stable():
    verification = ensure_line_verification_authoritative_verdict_fields({
        'canonical_stat::tower_regen': {
            'verification_status': 'publishable',
            'ep_compare_status': 'stage_scope_mismatch',
        }
    })
    assert verification['canonical_stat::tower_regen']['kb_alignment_status'] == 'not_comparable'
    assert verification['canonical_stat::tower_regen']['verdict'] == 'pass_with_compare_limitations'

    ep_compare = {
        'canonical_stat::tower_regen': {
            'delta': 2,
            'relative_delta_pct': 10.0,
            'compare_preset': 'Farming',
            'compare_perk_state': 'off',
            'package_value_source_state_mode': 'current',
            'ep_stage_context': {'note': 'context'},
            'package_value': 22,
            'ep_value': 20,
            'status': 'close',
            'compare_state_key': 'farming__perks_off',
            'package_contributors': [
                {'source_family': 'lab', 'source_name': 'Regen Lab', 'preset_name': 'Farming', 'value': 1.2, 'value_type': 'multiplier'}
            ],
        },
        'canonical_stat::wall_regen': {
            'package_value': 44,
            'ep_value': 40,
            'status': 'close',
            'compare_state_key': 'farming__perks_off',
            'compare_preset': 'Farming',
            'compare_perk_state': 'off',
            'package_contributors': [],
        },
        'canonical_stat::tower_hp': {'package_value': 100, 'ep_value': 80, 'status': 'mismatch'},
        'canonical_stat::wall_hp': {'package_value': 150, 'ep_value': 120, 'status': 'mismatch'},
        'canonical_stat::tower_defense_absolute': {'package_value': 10, 'ep_value': 8, 'status': 'close'},
    }
    closure = build_survivor_closure_report(ep_compare, verification)
    assert closure['survivor_order'][0] == 'canonical_stat::tower_regen'
    assert closure['rows'][0]['issues'] == []
    assert closure['rows'][-1]['note'] == 'downstream_reflection_of_tower_residue'

    residue = build_survivability_residue_analysis(
        ep_compare,
        {'best_fit_by_destination': {'canonical_stat::tower_regen': {'state_key': 'farming__perks_off', 'preset': 'Farming', 'perk_state': 'off'}}},
        {},
    )
    assert residue['canonical_stat::tower_regen']['package_to_ep_ratio'] == 1.1
    assert residue['canonical_stat::tower_regen']['best_fit_state_key'] == 'farming__perks_off'
    assert residue['_shared_residue_summary']['tower_regen_vs_wall_regen_ratio_gap'] == 0.0
