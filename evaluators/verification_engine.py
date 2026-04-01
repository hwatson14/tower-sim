"""
evaluators/verification_engine.py -- Verification verdict and EP oracle loading.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Callable

import pandas as pd


def _load_ep_oracle(ep_path: Path):
    from evaluators.compare import EP_LABEL_TO_DESTINATION, _parse_ep_value
    if not ep_path.exists():
        return {}
    df = pd.read_csv(ep_path, header=None)
    out = {}
    for _, row in df.iterrows():
        if len(row) < 4:
            continue
        label = str(row.iloc[2]).strip()
        value_raw = row.iloc[3] if len(row) > 3 else None
        if label in EP_LABEL_TO_DESTINATION:
            parsed, kind = _parse_ep_value(value_raw)
            if parsed is not None:
                out[EP_LABEL_TO_DESTINATION[label]] = {
                    'label': label,
                    'ep_value_raw': value_raw,
                    'ep_value_parsed': parsed,
                    'ep_value_type': kind,
                }
    return out


def _load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def build_line_by_line_verification(statbook_dict, ep_compare, formula_ledger, formula_contract: Callable[[dict, str], dict]):
    from evaluators.compare import kb_alignment_status_from_compare_status, verdict_from_verification
    verification = {}
    rows = statbook_dict['rows']
    for key, row in rows.items():
        contributors = row.get('contributors', [])
        schema = row.get('schema') or {}
        allowed = set(schema.get('allowed_input_value_types') or [])
        issues = []
        unresolved = []
        level_rows = []
        semantic_mismatch = []
        for c in contributors:
            vt = c.get('value_type')
            notes = str(c.get('notes') or '').lower()
            if vt == 'level':
                level_rows.append(c.get('source_name') or c.get('stat_name'))
            if c.get('value') is None or 'unresolved' in notes or vt in {'missing_inventory', 'raw_text', 'display_token'}:
                unresolved.append(c.get('source_name') or c.get('stat_name'))
            if allowed and vt is not None and vt not in allowed:
                semantic_mismatch.append({
                    'source': c.get('source_name') or c.get('stat_name'),
                    'value_type': vt,
                })
        if level_rows:
            issues.append('level_contributor_present')
        if unresolved:
            issues.append('unresolved_contributor_present')
        if semantic_mismatch:
            issues.append('semantically_incompatible_contributor_present')
        contract = formula_contract(formula_ledger, key)
        consumed_contributors = None
        notes_text = str(row.get('notes') or '')
        match = re.search(r'Consumed\s+(\d+)\/(\d+)\s+contributors', notes_text)
        if match:
            consumed_contributors = {'consumed': int(match.group(1)), 'listed': int(match.group(2))}
            if int(match.group(1)) < int(match.group(2)):
                issues.append('unconsumed_contributor_present')
        compare = ep_compare.get(key)
        compare_status = None if compare is None else compare.get('status')
        if compare_status == 'mismatch':
            issues.append('ep_reference_mismatch')
        if compare_status == 'stage_scope_mismatch':
            issues.append('ep_reference_stage_scope_mismatch')
        if compare_status == 'formula_blocked':
            issues.append('formula_blocked_pending_exact_destination_logic')
        verification_status = 'publishable'
        if key.startswith('raw::'):
            verification_status = 'trace_only'
        elif row.get('status') != 'resolved':
            verification_status = 'not_resolved'
        if contract.get('publish_policy') == 'block' and not key.startswith('raw::'):
            verification_status = 'blocked_formula_pending'
        elif issues:
            if key.startswith('raw::'):
                verification_status = 'trace_only'
            else:
                verification_status = 'blocked' if row.get('status') == 'resolved' else 'needs_work'
        kb_alignment_status = kb_alignment_status_from_compare_status(compare_status)
        verdict = verdict_from_verification(verification_status, compare_status)
        verification[key] = {
            'destination': key,
            'status': row.get('status'),
            'verification_status': verification_status,
            'kb_alignment_status': kb_alignment_status,
            'verdict': verdict,
            'final_value': row.get('final_value'),
            'unit': schema.get('unit'),
            'resolver': schema.get('resolver'),
            'contributor_count': len(contributors),
            'issues': issues,
            'level_contributors': level_rows,
            'unresolved_contributors': unresolved,
            'semantic_mismatches': semantic_mismatch,
            'ep_compare_status': compare_status,
            'ep_compare_delta': None if compare is None else compare.get('delta'),
            'ep_compare_value': None if compare is None else compare.get('package_value'),
            'ep_compare_value_type': None if compare is None else compare.get('package_value_type'),
            'ep_reference_value': None if compare is None else compare.get('ep_value'),
            'ep_reference_value_type': None if compare is None else compare.get('ep_value_type'),
            'compare_context': None if compare is None else {
                'compare_preset': compare.get('compare_preset'),
                'compare_perk_state': compare.get('compare_perk_state'),
                'package_value_source_preset': compare.get('package_value_source_preset'),
                'package_value_source_state_mode': compare.get('package_value_source_state_mode'),
                'ep_stage_context': compare.get('ep_stage_context'),
            },
            'formula_contract': contract,
            'contributor_consumption': consumed_contributors,
        }
    return verification
