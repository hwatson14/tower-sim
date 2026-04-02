from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from qe.contracts import normalize_surface_id_to_contract


CORE_ARTIFACTS = (
    'pipeline_trace.json',
    'diagnostics.json',
    'module_card_payloads.json',
    'account_state.json',
    'stat_inputs.json',
    'run_stats.json',
    'statbook.json',
    'statbook_publishable.json',
    'statbook_start_of_run.json',
    'statbook_max_progression.json',
    'run_stats_query_rows_start_of_run.json',
    'run_stats_query_rows_max_progression.json',
    'run_stats_query_plan_start_of_run.json',
    'run_stats_query_plan_max_progression.json',
    'state_matrix.json',
    'ep_oracle_compare.json',
    'line_by_line_verification.json',
    'audit_surface_manifest.json',
    'family_completeness_matrix.json',
)


@dataclass(frozen=True)
class InspectorArtifacts:
    out_dir: Path
    data: dict[str, Any]

    def get(self, name: str, default: Any = None) -> Any:
        return self.data.get(name, default)


def load_artifacts(out_dir: Path) -> InspectorArtifacts:
    payload: dict[str, Any] = {}
    for name in CORE_ARTIFACTS:
        path = out_dir / name
        if path.exists():
            try:
                payload[name] = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                payload[name] = {}
        else:
            payload[name] = {}
    optional_paths = [
        'artifact_contract_manifest.json',
        'tower_regen_closure_report.json',
        'tower_hp_semantic_gap_report.json',
        'tower_regen_ep_semantic_gap_report.json',
        'tower_defense_absolute_semantic_gap_report.json',
        'tower_damage_runtime_gap_report.json',
    ]
    for name in optional_paths:
        path = out_dir / name
        if path.exists():
            try:
                payload[name] = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                payload[name] = {}
    return InspectorArtifacts(out_dir=out_dir, data=payload)


def _semantic_group(surface_id: str) -> str:
    if surface_id.startswith('state::tower.') or surface_id.startswith('canonical_stat::tower_'):
        return 'Tower'
    if surface_id.startswith('state::wall.') or surface_id.startswith('canonical_stat::wall_'):
        return 'Wall'
    if surface_id.startswith('state::economy.') or 'coin' in surface_id or 'cash' in surface_id:
        return 'Economy'
    if surface_id.startswith('state::cards.') or surface_id.startswith('runtime_mechanic_param::cards.'):
        return 'Cards'
    if surface_id.startswith('state::perk.') or surface_id.startswith('runtime_mechanic_param::perk.'):
        return 'Perks'
    if surface_id.startswith('state::uw.') or surface_id.startswith('mechanic_param::uw.'):
        return 'Ultimate Weapons'
    if surface_id.startswith('state::module.') or surface_id.startswith('mechanic_param::module.'):
        return 'Modules'
    if surface_id.startswith('state::bot.') or surface_id.startswith('runtime_mechanic_param::bot.'):
        return 'Bots'
    if surface_id.startswith('state::guardian.') or surface_id.startswith('runtime_mechanic_param::guardian.'):
        return 'Guardians'
    if surface_id.startswith('context::') or surface_id.startswith('environment_param::'):
        return 'Context'
    if surface_id.startswith('derived::') or surface_id.startswith('support_surface::'):
        return 'Derived'
    return 'Other'


def _display_label(surface_id: str) -> str:
    return surface_id.split('::', 1)[-1]


def statbook_rows_frame(statbook_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for raw_surface_id, payload in (statbook_payload.get('rows') or {}).items():
        surface_id = normalize_surface_id_to_contract(raw_surface_id)
        row = dict(payload)
        row['raw_surface_id'] = raw_surface_id
        row['surface_id'] = surface_id
        row['group'] = _semantic_group(surface_id)
        row['display_label'] = _display_label(surface_id)
        row['contributor_count'] = len(row.get('contributors') or [])
        rows.append(row)
    if not rows:
        return pd.DataFrame(
            columns=[
                'surface_id',
                'raw_surface_id',
                'group',
                'display_label',
                'final_value',
                'display_value',
                'value_type',
                'status',
                'contributor_count',
            ]
        )
    return pd.DataFrame(rows)


def compare_rows_frame(compare_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for raw_surface_id, payload in compare_payload.items():
        surface_id = normalize_surface_id_to_contract(raw_surface_id)
        row = dict(payload)
        row['raw_surface_id'] = raw_surface_id
        row['surface_id'] = surface_id
        row['group'] = _semantic_group(surface_id)
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['surface_id', 'group'])


def verification_rows_frame(verification_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for raw_surface_id, payload in verification_payload.items():
        surface_id = normalize_surface_id_to_contract(raw_surface_id)
        row = dict(payload)
        row['raw_surface_id'] = raw_surface_id
        row['surface_id'] = surface_id
        row['group'] = _semantic_group(surface_id)
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['surface_id', 'group'])


def pipeline_stages_frame(trace_payload: dict[str, Any]) -> pd.DataFrame:
    stages = trace_payload.get('stages') or []
    if not isinstance(stages, list):
        return pd.DataFrame(columns=['stage_id', 'title', 'owner_module', 'entry_function', 'status', 'elapsed_ms'])
    return pd.DataFrame(stages)


def run_stats_rows_frame(run_stats_payload: dict[str, Any], *, preset: str) -> pd.DataFrame:
    preset_payload = ((run_stats_payload.get('presets') or {}).get(preset) or {})
    rows_payload = (((preset_payload.get('stats') or {}).get('rows')) or {})
    rows = []
    for raw_surface_id, payload in rows_payload.items():
        surface_id = normalize_surface_id_to_contract(raw_surface_id)
        start = dict(payload.get('start_of_run') or {})
        max_progression = dict(payload.get('max_progression') or {})
        row = {
            'preset': preset,
            'raw_surface_id': raw_surface_id,
            'surface_id': surface_id,
            'group': _semantic_group(surface_id),
            'display_label': _display_label(surface_id),
            'changed_in_max_progression': bool(payload.get('changed_in_max_progression')),
            'start_of_run_value': start.get('final_value'),
            'start_of_run_display': start.get('display_value'),
            'start_of_run_type': start.get('value_type'),
            'start_of_run_status': start.get('status'),
            'max_progression_value': max_progression.get('final_value'),
            'max_progression_display': max_progression.get('display_value'),
            'max_progression_type': max_progression.get('value_type'),
            'max_progression_status': max_progression.get('status'),
        }
        rows.append(row)
    if not rows:
        return pd.DataFrame(
            columns=[
                'preset',
                'surface_id',
                'raw_surface_id',
                'group',
                'display_label',
                'changed_in_max_progression',
                'start_of_run_value',
                'start_of_run_display',
                'start_of_run_type',
                'start_of_run_status',
                'max_progression_value',
                'max_progression_display',
                'max_progression_type',
                'max_progression_status',
            ]
        )
    return pd.DataFrame(rows)


def dual_state_statbook_rows_frame(
    statbook_start_payload: dict[str, Any],
    statbook_max_payload: dict[str, Any],
    *,
    preset: str,
) -> pd.DataFrame:
    start_rows = (((statbook_start_payload.get(preset) or {}).get('rows')) or {})
    max_rows = (((statbook_max_payload.get(preset) or {}).get('rows')) or {})
    surface_ids = {
        normalize_surface_id_to_contract(raw_surface_id)
        for raw_surface_id in start_rows.keys()
    } | {
        normalize_surface_id_to_contract(raw_surface_id)
        for raw_surface_id in max_rows.keys()
    }
    rows = []
    for surface_id in sorted(surface_ids):
        start_payload = next(
            (payload for raw_surface_id, payload in start_rows.items() if normalize_surface_id_to_contract(raw_surface_id) == surface_id),
            {},
        )
        max_payload = next(
            (payload for raw_surface_id, payload in max_rows.items() if normalize_surface_id_to_contract(raw_surface_id) == surface_id),
            {},
        )
        row = {
            'preset': preset,
            'surface_id': surface_id,
            'raw_surface_id': surface_id,
            'group': _semantic_group(surface_id),
            'display_label': _display_label(surface_id),
            'changed_in_max_progression': (
                start_payload.get('display_value') != max_payload.get('display_value')
                or start_payload.get('final_value') != max_payload.get('final_value')
            ),
            'start_of_run_value': start_payload.get('final_value'),
            'start_of_run_display': start_payload.get('display_value'),
            'start_of_run_type': start_payload.get('value_type'),
            'start_of_run_status': start_payload.get('status'),
            'max_progression_value': max_payload.get('final_value'),
            'max_progression_display': max_payload.get('display_value'),
            'max_progression_type': max_payload.get('value_type'),
            'max_progression_status': max_payload.get('status'),
        }
        rows.append(row)
    if not rows:
        return pd.DataFrame(
            columns=[
                'preset',
                'surface_id',
                'raw_surface_id',
                'group',
                'display_label',
                'changed_in_max_progression',
                'start_of_run_value',
                'start_of_run_display',
                'start_of_run_type',
                'start_of_run_status',
                'max_progression_value',
                'max_progression_display',
                'max_progression_type',
                'max_progression_status',
            ]
        )
    return pd.DataFrame(rows)


def snapshot_label(*, preset: str, state_mode: str, perk_state: str, out_dir: Path) -> str:
    return f'{preset} | {state_mode} | perks {perk_state} | {out_dir.name}'


def qe_query_rows_frame(query_rows_payload: dict[str, Any], *, preset: str) -> pd.DataFrame:
    preset_payload = (query_rows_payload.get(preset) or {}) if isinstance(query_rows_payload, dict) else {}
    rows_payload = preset_payload.get('rows') or {}
    rows = []
    for raw_surface_id, payload in rows_payload.items():
        surface_id = normalize_surface_id_to_contract(raw_surface_id)
        dependency_trace = payload.get('dependency_trace') or {}
        rows.append({
            'raw_surface_id': raw_surface_id,
            'surface_id': surface_id,
            'group': _semantic_group(surface_id),
            'display_label': _display_label(surface_id),
            'final_value': payload.get('final_value'),
            'display_value': payload.get('display_value'),
            'value_type': payload.get('value_type'),
            'status': payload.get('status'),
            'bundle_id': payload.get('bundle_id'),
            'family_id': payload.get('family_id'),
            'trace_mode': payload.get('trace_mode'),
            'contributor_count': len(payload.get('contributors') or []),
            'has_trace_steps': bool(dependency_trace.get('trace_steps')),
            'resolution_order_index': dependency_trace.get('resolution_order_index'),
        })
    if not rows:
        return pd.DataFrame(columns=['surface_id', 'group', 'status', 'bundle_id', 'family_id'])
    return pd.DataFrame(rows).sort_values(['group', 'surface_id']).reset_index(drop=True)


def qe_surface_payload(query_rows_payload: dict[str, Any], *, preset: str, surface_id: str) -> dict[str, Any]:
    preset_payload = (query_rows_payload.get(preset) or {}) if isinstance(query_rows_payload, dict) else {}
    rows_payload = preset_payload.get('rows') or {}
    for raw_surface_id, payload in rows_payload.items():
        if normalize_surface_id_to_contract(raw_surface_id) == surface_id:
            row = dict(payload)
            row['surface_id'] = normalize_surface_id_to_contract(raw_surface_id)
            row['raw_surface_id'] = raw_surface_id
            return row
    return {}


def qe_trace_summary_frame(trace_payload: dict[str, Any]) -> pd.DataFrame:
    if not trace_payload:
        return pd.DataFrame(columns=['field', 'value'])
    rows = [
        ('trace_contract_id', trace_payload.get('trace_contract_id')),
        ('trace_mode', trace_payload.get('trace_mode')),
        ('resolution_order_index', trace_payload.get('resolution_order_index')),
        ('direct_upstream_count', len(trace_payload.get('direct_upstream_node_ids') or [])),
        ('direct_downstream_count', len(trace_payload.get('direct_downstream_node_ids') or [])),
        ('upstream_closure_count', len(trace_payload.get('upstream_closure_node_ids') or [])),
        ('downstream_closure_count', len(trace_payload.get('downstream_closure_node_ids') or [])),
        ('resolved_upstream_count', len(trace_payload.get('resolved_upstream_node_ids') or [])),
        ('unresolved_upstream_count', len(trace_payload.get('unresolved_upstream_node_ids') or [])),
        ('has_runtime_trace_steps', bool(trace_payload.get('has_runtime_trace_steps'))),
    ]
    return pd.DataFrame(rows, columns=['field', 'value'])


def qe_contributor_rows_frame(row_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for contributor in (row_payload.get('contributors') or []):
        rows.append({
            'contributor_id': contributor.get('contributor_id'),
            'source_class': contributor.get('source_class'),
            'composition_stage': contributor.get('composition_stage'),
            'active': contributor.get('active'),
            'gate_reason': contributor.get('gate_reason'),
            'value': contributor.get('value'),
            'value_type': contributor.get('value_type'),
            'provenance_ref': contributor.get('provenance_ref'),
            'display_value': contributor.get('display_value'),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['contributor_id', 'source_class'])


def qe_trace_steps_frame(trace_payload: dict[str, Any]) -> pd.DataFrame:
    steps = trace_payload.get('trace_steps') or []
    return pd.DataFrame(steps) if steps else pd.DataFrame(columns=['step_index', 'step_kind', 'node_id', 'status', 'note'])


def qe_dependency_nodes_frame(trace_payload: dict[str, Any], *, field_name: str) -> pd.DataFrame:
    node_ids = trace_payload.get(field_name) or []
    return pd.DataFrame([{'node_id': node_id} for node_id in node_ids]) if node_ids else pd.DataFrame(columns=['node_id'])


def qe_plan_coverage_frame(query_plan_payload: dict[str, Any], *, preset: str, surface_id: str) -> pd.DataFrame:
    presets_payload = (query_plan_payload.get('presets') or {}) if isinstance(query_plan_payload, dict) else {}
    preset_payload = presets_payload.get(preset) or {}
    rows = []
    progression = preset_payload.get('progression') or {}
    if surface_id in (progression.get('resolved_surface_ids') or []):
        rows.append({
            'bundle_kind': 'progression',
            'bundle_id': progression.get('bundle_id'),
            'family_id': progression.get('family_id'),
            'surface_id': surface_id,
        })
    for timing_payload in (preset_payload.get('timing') or []):
        if surface_id in (timing_payload.get('resolved_surface_ids') or []):
            rows.append({
                'bundle_kind': 'timing',
                'bundle_id': timing_payload.get('bundle_id'),
                'family_id': timing_payload.get('family_id'),
                'surface_id': surface_id,
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['bundle_kind', 'bundle_id', 'family_id', 'surface_id'])


def _lineage_source_group(row: dict[str, Any]) -> str:
    stage = str(row.get('stage') or '').strip()
    source_family = str(row.get('source_family') or '').strip()
    if stage and source_family:
        return f'{stage}:{source_family}'
    if source_family:
        return source_family
    if stage:
        return stage
    return 'unknown'


def _lineage_resolved_surface_id(row: dict[str, Any]) -> str | None:
    surface_id = str(row.get('surface_id') or '').strip()
    if surface_id:
        return normalize_surface_id_to_contract(surface_id)
    destination_object_type = str(row.get('destination_object_type') or '').strip()
    destination_id = str(row.get('destination_id') or '').strip()
    if destination_object_type and destination_id:
        return normalize_surface_id_to_contract(f'{destination_object_type}::{destination_id}')
    return None


def input_lineage_rows_frame(stat_inputs_payload: Any) -> pd.DataFrame:
    columns = ['source_group', 'source_key', 'source_value', 'resolved_surface_id', 'resolved_value', 'mapping_status']
    if not isinstance(stat_inputs_payload, list):
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for raw_row in stat_inputs_payload:
        if not isinstance(raw_row, dict):
            continue
        source_key = (
            str(raw_row.get('source_name') or '').strip()
            or str(raw_row.get('stat_name') or '').strip()
            or str(raw_row.get('destination_id') or '').strip()
        )
        resolved_surface_id = _lineage_resolved_surface_id(raw_row)
        source_value = raw_row.get('value')
        resolved_value = raw_row.get('resolved_value')
        if resolved_value is None:
            resolved_value = source_value
        kb_mapped = bool(raw_row.get('kb_mapped'))
        if resolved_surface_id:
            mapping_status = 'mapped'
        elif kb_mapped:
            mapping_status = 'mapped_missing_surface'
        else:
            mapping_status = 'unmapped'
        rows.append(
            {
                'source_group': _lineage_source_group(raw_row),
                'source_key': source_key,
                'source_value': source_value,
                'resolved_surface_id': resolved_surface_id,
                'resolved_value': resolved_value,
                'mapping_status': mapping_status,
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)
