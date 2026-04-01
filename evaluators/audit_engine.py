"""
evaluators/audit_engine.py -- Publishing gates and KB audits. AUTHORITY (T12).

T12: sharded from evaluators/compare.py.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Callable

from qe.contracts import (
    CANONICAL_PRESET_NAMES,
)
from qe.routing import classify_input_routing

# --- Root path relative to evaluators/ sub-dir ---
_EV_ROOT = Path(__file__).resolve().parents[1]

def _load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))

def _build_publish_gate_audits(stat_inputs, statbook_publishable_dict, ep_compare_publishable, formula_ledger) -> dict:
    # Minimal implementation for now, mirroring the complex logic from compare.py
    # but focused on the audit output structure.
    return {
        'version': 1,
        'publish_status': statbook_publishable_dict.get('diagnostics', {}).get('oracle_policy'),
        'compare_layer_destination_unit_inconsistencies': [], # Logic to be migrated if needed
    }

def _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger):
    blocked_formula_contracts = []
    for destination_id, contract in (formula_ledger.get('surfaces') or {}).items():
        if contract.get('publish_policy') == 'block':
            blocked_formula_contracts.append({
                'destination_id': destination_id,
                'formula_class': contract.get('formula_class'),
                'rationale': contract.get('rationale'),
            })

    active_unmapped_inputs = []
    for row in stat_inputs:
        routing_class = classify_input_routing(row)
        if routing_class != 'truly_unrouted_unknown':
            continue
        if row.source_family == 'raw':
            continue
        active_unmapped_inputs.append({
            'source_family': row.source_family,
            'stat_name': row.stat_name,
            'value_type': row.value_type,
            'contributor_id': row.contributor_id,
            'routing_class': routing_class,
        })
    active_unmapped_inputs.sort(key=lambda item: (item['source_family'], item['stat_name']))
    active_unmapped_by_family = {}
    for item in active_unmapped_inputs:
        fam = item['source_family']
        active_unmapped_by_family[fam] = active_unmapped_by_family.get(fam, 0) + 1

    resolved_unknown_schema_units = []
    for destination_id, row in (statbook_publishable_dict.get('rows') or {}).items():
        if row.get('status') != 'resolved':
            continue
        schema = row.get('schema') or {}
        if schema.get('unit') != 'unknown':
            continue
        resolved_unknown_schema_units.append({
            'destination_id': destination_id,
            'resolver': schema.get('resolver'),
            'value_type': row.get('value_type'),
            'final_value': row.get('final_value'),
        })
    resolved_unknown_schema_units.sort(key=lambda item: item['destination_id'])

    relic_registry_rows = _load_csv_rows(_EV_ROOT / 'kb' / 'global-rules' / 'tables' / 'relic-input-registry.csv')
    ambiguous_relic_semantics = []
    for rec in relic_registry_rows:
        if (rec.get('semantic_unit_hint') or '').strip() == 'percent_points_or_pct_bonus':
            ambiguous_relic_semantics.append({
                'registry_key': rec.get('registry_key'),
                'destination_id': f"{rec.get('destination_object_type','').strip()}::{rec.get('destination_id','').strip()}" if rec.get('destination_id') else None,
            })
    ambiguous_relic_semantics.sort(key=lambda item: item['registry_key'] or '')

    return {
        'summary': {
            'blocked_formula_contract_count': len(blocked_formula_contracts),
            'active_unmapped_input_count': len(active_unmapped_inputs),
            'resolved_unknown_schema_unit_count': len(resolved_unknown_schema_units),
            'ambiguous_relic_semantic_hint_count': len(ambiguous_relic_semantics),
        },
        'priority_gaps': ([
            item for item in active_unmapped_inputs
            if item['stat_name'] == 'Dimension Core::main'
        ] + blocked_formula_contracts + active_unmapped_inputs[:12]),
        'blocked_formula_contracts': blocked_formula_contracts,
        'active_unmapped_by_family': active_unmapped_by_family,
        'active_unmapped_inputs': active_unmapped_inputs,
        'resolved_unknown_schema_units': resolved_unknown_schema_units,
        'ambiguous_relic_semantic_hints': ambiguous_relic_semantics,
    }

def _classify_unmapped_input_gap(item):
    source_family = (item.get('source_family') or '').strip().lower()
    stat_name = (item.get('stat_name') or '').strip()
    contributor_id = item.get('contributor_id')

    if contributor_id:
        return 'Calculator wiring / implementation gap'

    runtime_only_patterns = [
        r'Mastery$', r'Effect Bans', r'Assist Module', r'Enemy', r'Boss',
        r'Protector', r'Ranged', r'Fast', r'Tank', r'Vampire', r'Scatter',
        r'Ray', r'Resistance', r'Ultimate', r'Battle Condition', r'Card Presets',
        r'Buy Multiplier', r'More Round Stats', r'Auto Pick', r'Ban Perks',
        r'Perk Option Quantity', r'First Perk Choice', r'Standard Perks Bonus',
        r'Unlock Perks', r'END OF ARRAY', r'Keys spent', r'Total Bonuses',
        r'Misc\.', r'Unlocks$', r'Discount', r'Shards', r'Module Coin Cost',
        r'Rare Drop Chance', r'Unmerge Module', r'Shatter Shards',
    ]
    if any(re.search(pattern, stat_name) for pattern in runtime_only_patterns):
        return 'Intentional non-goal / runtime-only surface'

    if source_family == 'vault' and stat_name in {
        'Attack', 'Defense', 'Utility', 'Cash / Wave', 'Coins / Kill',
        'Coins / Wave', 'Interest / Wave', 'Keys spent', 'Misc.',
        'Total Bonuses', 'Unlocks'
    }:
        return 'Intentional non-goal / runtime-only surface'

    if source_family in {'lab', 'vault'}:
        return 'KB missing executable contract'
    return 'KB missing fact'

def _build_kb_gap_register(kb_incomplete_areas, audits):
    register = []
    for item in kb_incomplete_areas.get('blocked_formula_contracts', []):
        register.append({
            'gap_id': f"formula_contract::{item['destination_id']}",
            'bucket': 'KB missing executable contract',
            'surface': item['destination_id'],
        })
    for item in kb_incomplete_areas.get('active_unmapped_inputs', []):
        register.append({
            'gap_id': f"unmapped::{item['source_family']}::{item['stat_name']}",
            'bucket': _classify_unmapped_input_gap(item),
            'surface': item['stat_name'],
        })
    return register

def _build_perk_coverage_audit(ids_raw, account_state, destination_type_schema, perks_input_path):
    # Stub for the complex perk coverage logic
    return {
        'version': 1,
        'perk_coverage_pct': 0.0,
        'uncovered_perks': [],
    }

def _build_artifact_contract_manifest(account_state, canonical_output_preset: str, stat_inputs, statbook_dict: dict) -> dict:
    raw_names = set()
    for lane_map_name in ('card_presets', 'module_presets', 'perk_presets'):
        lane_map = getattr(account_state, lane_map_name, {}) or {}
        raw_names.update(lane_map.keys())
    synthetic_names = sorted(name for name in raw_names if name not in CANONICAL_PRESET_NAMES)

    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': synthetic_names,
        'artifacts': [
            {'surface': 'account_state.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'canonical': True},
            {'surface': 'stat_inputs.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'canonical': True},
            {'surface': 'statbook.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'canonical': True},
            {'surface': 'state_matrix.json', 'artifact_class': 'derived_matrix', 'contract': 'full', 'canonical': True},
            {'surface': 'statbook_publishable.json', 'artifact_class': 'publishable_view', 'contract': 'partial', 'canonical': False},
            {'surface': 'diagnostics.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'canonical': False},
            {'surface': 'ep_oracle_compare.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'canonical': False},
            {'surface': 'line_by_line_verification.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'canonical': False},
            {'surface': 'survivor_closure_report.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'canonical': False},
            {'surface': 'audit_surface_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'canonical': True},
            {'surface': 'artifact_contract_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'canonical': True},
            {'surface': 'family_completeness_matrix.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'canonical': True},
        ],
    }
