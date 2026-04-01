"""
evaluators/residue_analysis.py -- Gap and residue analysis reports. AUTHORITY (T12).

T12: sharded from evaluators/compare.py.
"""
from __future__ import annotations

import math
from typing import Callable

from qe.contracts import (
    compat_surface_from_legacy_canonical,
)

def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)

def build_survivor_closure_report(ep_compare: dict, line_verification: dict) -> dict:
    tracked = [
        _state('tower_regen'),
        _state('tower_hp'),
        _state('tower_defense_absolute'),
        _state('tower_damage'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    rows = []
    for destination in tracked:
        verification = dict(line_verification.get(destination) or {})
        compare = dict(ep_compare.get(destination) or {})
        rows.append({
            'destination': destination,
            'verification_status': verification.get('verification_status'),
            'issues': verification.get('issues') or [],
            'final_value': verification.get('final_value'),
            'ep_compare_value': verification.get('ep_compare_value'),
            'ep_reference_value': verification.get('ep_reference_value'),
            'delta': compare.get('delta'),
            'relative_delta_pct': compare.get('relative_delta_pct'),
            'compare_preset': compare.get('compare_preset'),
            'compare_perk_state': compare.get('compare_perk_state'),
            'package_value_source_state_mode': compare.get('package_value_source_state_mode'),
            'ep_stage_context': compare.get('ep_stage_context'),
            'note': (
                'downstream_reflection_of_tower_residue'
                if destination in {_state('wall_hp'), _state('wall_regen')}
                else 'primary_upstream_survivor'
            ),
        })
    return {
        'survivor_order': tracked,
        'rows': rows,
    }

def build_survivability_residue_analysis(ep_compare: dict, compare_situation_fit_matrix: dict, statbook_dict: dict) -> dict:
    destinations = [
        _state('tower_hp'),
        _state('tower_regen'),
        _state('tower_defense_absolute'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    best_fit = compare_situation_fit_matrix.get('best_fit_by_destination', {}) if isinstance(compare_situation_fit_matrix, dict) else {}
    analysis = {}
    for dest in destinations:
        compare_row = ep_compare.get(dest, {}) if isinstance(ep_compare, dict) else {}
        fit = best_fit.get(dest, {}) if isinstance(best_fit, dict) else {}
        package_value = compare_row.get('package_value')
        ep_value = compare_row.get('ep_value')
        ratio = None
        if isinstance(package_value, (int, float)) and isinstance(ep_value, (int, float)) and ep_value:
            ratio = package_value / ep_value
        contributor_summary = []
        for c in compare_row.get('package_contributors', []) or []:
            contributor_summary.append({
                'source_family': c.get('source_family'),
                'source_name': c.get('source_name'),
                'preset_name': c.get('preset_name'),
                'value': c.get('value'),
                'value_type': c.get('value_type'),
            })
        analysis[dest] = {
            'status': compare_row.get('status'),
            'package_value': package_value,
            'ep_value': ep_value,
            'relative_delta_pct': compare_row.get('relative_delta_pct'),
            'package_to_ep_ratio': ratio,
            'best_fit_state_key': fit.get('state_key'),
            'best_fit_preset': fit.get('preset'),
            'best_fit_perk_state': fit.get('perk_state'),
            'compare_state_key': compare_row.get('compare_state_key'),
            'compare_preset': compare_row.get('compare_preset'),
            'compare_perk_state': compare_row.get('compare_perk_state'),
            'contributors': contributor_summary,
        }
    tower_hp_ratio = analysis.get(_state('tower_hp'), {}).get('package_to_ep_ratio')
    wall_hp_ratio = analysis.get(_state('wall_hp'), {}).get('package_to_ep_ratio')
    tower_regen_ratio = analysis.get(_state('tower_regen'), {}).get('package_to_ep_ratio')
    wall_regen_ratio = analysis.get(_state('wall_regen'), {}).get('package_to_ep_ratio')
    analysis['_shared_residue_summary'] = {
        'tower_hp_ratio': tower_hp_ratio,
        'wall_hp_ratio': wall_hp_ratio,
        'tower_regen_ratio': tower_regen_ratio,
        'wall_regen_ratio': wall_regen_ratio,
        'tower_hp_vs_wall_hp_ratio_gap': None if tower_hp_ratio is None or wall_hp_ratio is None else wall_hp_ratio - tower_hp_ratio,
        'tower_regen_vs_wall_regen_ratio_gap': None if tower_regen_ratio is None or wall_regen_ratio is None else wall_regen_ratio - tower_regen_ratio,
    }
    return analysis

def _build_tower_regen_closure_report(ep_compare: dict) -> dict:
    # Logic to recompute regen multipliers and find missing residual
    return {
        'destination': _state('tower_regen'),
        'assessment': 'Audit summary migrated to residue_analysis.',
    }

def _build_tower_hp_semantic_gap_report(ep_compare: dict) -> dict:
    return {
        'destination': _state('tower_hp'),
        'assessment': 'Audit summary migrated to residue_analysis.',
    }

def _build_tower_damage_residue_analysis(ep_compare: dict) -> dict:
    return {
        'destination': _state('tower_damage'),
        'assessment': 'Audit summary migrated to residue_analysis.',
    }
