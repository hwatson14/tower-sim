"""
app/publication.py -- Pipeline output and trace persistence. AUTHORITY (T12).

T12: sharded from app/pipeline.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from app.models import PipelineRunRequest, PipelineTrace, PipelineRunResult, FastCheckpointRequest, FastCheckpointResult
from qe.contracts import contract_json_payload as js, normalize_surface_id_to_contract
from qe.publication import (
    build_input_dashboard_payload as qe_build_input_dashboard_payload,
    build_labs_panel as qe_build_labs_panel,
    build_stats_dashboard_payload as qe_build_stats_dashboard_payload,
    load_lab_category_registry_by_raw_name,
    preset_options as qe_preset_options,
)
from app.models import _normalize_perk_state
from app.display import annotate_display_fields

ROOT = Path(__file__).resolve().parents[1]

RUN_STATS_COMMITTED_BASELINE_ARTIFACTS: tuple[str, ...] = (
    'account_state.json',
    'run_stats.json',
    'run_stats_query_plan_start_of_run.json',
    'run_stats_query_plan_max_progression.json',
    'run_stats_query_rows_start_of_run.json',
    'run_stats_query_rows_max_progression.json',
)

RUN_STATS_LOCAL_SUPPORT_ARTIFACTS: tuple[str, ...] = (
    'diagnostics.json',
    'module_card_payloads.json',
)

RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS: tuple[str, ...] = (
    *RUN_STATS_LOCAL_SUPPORT_ARTIFACTS,
    *RUN_STATS_COMMITTED_BASELINE_ARTIFACTS,
)

FULL_PIPELINE_PUBLICATION_ARTIFACTS: tuple[str, ...] = (
    'diagnostics.json',
    'account_state.json',
    'input_dashboard.json',
    'stats_dashboard.json',
    'stat_inputs.json',
    'statbook.json',
    'statbook_publishable.json',
    'run_stats_query_rows_start_of_run.json',
    'run_stats_query_rows_max_progression.json',
    'ep_oracle_compare.json',
    'line_by_line_verification.json',
    'survivor_closure_report.json',
    'state_matrix.json',
    'audit_surface_manifest.json',
    'artifact_contract_manifest.json',
    'family_completeness_matrix.json',
    'optimizer_scores.json',
    'line_by_line_verification.csv',
)

# --- Helper Functions ---

def _relpath_str(path: Path | str | None, root_path: Path | None = None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    base = root_path or ROOT
    try:
        return Path(p.relative_to(base)).as_posix()
    except (ValueError, RuntimeError):
        return p.as_posix()

def _json_sanitize(obj, root_path: Path | None = None):
    if isinstance(obj, Path):
        return _relpath_str(obj, root_path)
    if isinstance(obj, dict):
        return {k: _json_sanitize(v, root_path) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v, root_path) for v in obj]
    if isinstance(obj, tuple):
        return [_json_sanitize(v, root_path) for v in obj]
    if isinstance(obj, str) and (obj.startswith('/') or obj.startswith('\\')):
        try:
            return _relpath_str(obj, root_path)
        except Exception:
            return obj
    return obj

def _load_json_artifact(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

def _generated_output_paths(out_dir: Path) -> list[Path]:
    return sorted(path for path in out_dir.glob('*.json')) + sorted(path for path in out_dir.glob('*.csv'))


def _preset_options(account_state_payload: dict) -> list[str]:
    return qe_preset_options(account_state_payload)


def _build_labs_panel(account_state_payload: dict, section_layout: dict[str, object] | None = None) -> tuple[dict[str, object], list[dict[str, str]]]:
    return qe_build_labs_panel(account_state_payload)


def _build_input_dashboard_payload(
    account_state_payload: dict,
    diagnostics: dict,
    *,
    qe_dashboard_publications: dict[str, object] | None = None,
    module_card_payloads: dict[str, object] | None = None,
) -> dict[str, object]:
    return qe_build_input_dashboard_payload(
        account_state_payload,
        diagnostics,
        qe_dashboard_publications=qe_dashboard_publications,
        module_card_payloads=module_card_payloads,
    )


def _build_stats_dashboard_payload(
    *,
    account_state_payload: dict[str, object],
    diagnostics: dict[str, object],
    input_dashboard_payload: dict[str, object],
    module_card_payloads: dict[str, object] | None,
    query_rows_start_of_run: dict[str, object] | None,
    query_rows_max_progression: dict[str, object] | None,
    ep_compare_publishable: dict[str, object] | None,
    line_verification: dict[str, object] | None,
    selected_preset: str,
    selected_state_mode: str,
) -> dict[str, object]:
    return qe_build_stats_dashboard_payload(
        account_state_payload=account_state_payload,
        diagnostics=diagnostics,
        input_dashboard_payload=input_dashboard_payload,
        module_card_payloads=module_card_payloads,
        query_rows_start_of_run=query_rows_start_of_run,
        query_rows_max_progression=query_rows_max_progression,
        ep_compare_publishable=ep_compare_publishable,
        line_verification=line_verification,
        selected_preset=selected_preset,
        selected_state_mode=selected_state_mode,
        annotate_display_fields=annotate_display_fields,
    )

# --- Core Output and Trace Writing ---

def write_pipeline_trace(out_dir: Path, trace: PipelineTrace, root_path: Path) -> Path:
    path = out_dir / 'pipeline_trace.json'
    payload = trace.to_dict()
    sanitized = _json_sanitize(payload, root_path)
    path.write_text(json.dumps(sanitized, indent=2, default=str), encoding='utf-8')
    return path

# Legacy filenames written by the pre-T12 analysis pipeline (run_stats.py monolith).
# Cleaned up at the start of write_core_outputs() so stale artifacts do not persist.
_ANALYSIS_PIPELINE_LEGACY_OUTPUTS: list[str] = [
    'start_of_run.json',
    'max_progression.json',
    'stat_inputs_start_of_run.json',
    'stat_inputs_max_progression.json',
]

# Legacy filenames written by the pre-T12 run-stats pipeline path.
# Cleaned up at the start of RunStatsSession.execute() so stale artifacts do not persist.
# Authority: publication.py (single source for all artifact cleanup contracts).
_RUN_STATS_LEGACY_OUTPUTS: list[str] = [
    'stat_inputs_start_of_run.json',
    'stat_inputs_max_progression.json',
    'statbook_start_of_run.json',
    'statbook_max_progression.json',
]


def _remove_legacy_outputs(out_dir: Path, legacy_list: list[str]) -> None:
    for name in legacy_list:
        path = out_dir / name
        if path.exists():
            path.unlink()

def write_core_outputs(
    *,
    out_dir: Path,
    diagnostics: dict,
    account_state_payload: dict,
    stat_inputs_payload: list[dict],
    statbook_dict: dict,
    statbook_publishable_dict: dict,
    ep_compare_publishable: dict,
    line_verification: dict,
    survivor_closure_report: dict,
    state_matrix: dict,
    optimizer_scores: dict,
    audit_surface_manifest: dict,
    artifact_contract_manifest: dict,
    family_completeness_matrix: dict,
    root_path: Path,
    module_card_payloads: dict[str, object] | None = None,
    qe_dashboard_publications: dict[str, object] | None = None,
    query_rows_start_of_run: dict[str, object] | None = None,
    query_rows_max_progression: dict[str, object] | None = None,
    selected_preset: str = 'Farming',
    selected_state_mode: str = 'max_progression',
) -> list[str]:

    _remove_legacy_outputs(out_dir, _ANALYSIS_PIPELINE_LEGACY_OUTPUTS)

    input_dashboard_payload = _build_input_dashboard_payload(
        account_state_payload,
        diagnostics,
        qe_dashboard_publications=qe_dashboard_publications,
        module_card_payloads=module_card_payloads,
    )
    stats_dashboard_payload = _build_stats_dashboard_payload(
        account_state_payload=account_state_payload,
        diagnostics=diagnostics,
        input_dashboard_payload=input_dashboard_payload,
        module_card_payloads=module_card_payloads,
        query_rows_start_of_run=query_rows_start_of_run,
        query_rows_max_progression=query_rows_max_progression,
        ep_compare_publishable=ep_compare_publishable,
        line_verification=line_verification,
        selected_preset=selected_preset,
        selected_state_mode=selected_state_mode,
    )
    artifacts = [
        ('diagnostics.json', diagnostics),
        ('account_state.json', account_state_payload),
        ('input_dashboard.json', input_dashboard_payload),
        ('stats_dashboard.json', stats_dashboard_payload),
        ('stat_inputs.json', stat_inputs_payload),
        ('statbook.json', statbook_dict),
        ('statbook_publishable.json', statbook_publishable_dict),
        ('run_stats_query_rows_start_of_run.json', query_rows_start_of_run or {}),
        ('run_stats_query_rows_max_progression.json', query_rows_max_progression or {}),
        ('ep_oracle_compare.json', ep_compare_publishable),
        ('line_by_line_verification.json', line_verification),
        ('survivor_closure_report.json', survivor_closure_report),
        ('state_matrix.json', state_matrix),
        ('audit_surface_manifest.json', audit_surface_manifest),
        ('artifact_contract_manifest.json', artifact_contract_manifest),
        ('family_completeness_matrix.json', family_completeness_matrix),
        ('optimizer_scores.json', optimizer_scores),
    ]

    written = []
    for name, payload in artifacts:
        path = out_dir / name
        path.write_text(json.dumps(js(_json_sanitize(payload, root_path)), indent=2, default=str), encoding='utf-8')
        written.append(name)

    # Residue reports (these are part of diagnostics, but writing them explicitly)
    residue_reports = [
        ('tower_regen_closure_report.json', diagnostics.get('tower_regen_closure_report')),
        ('tower_hp_semantic_gap_report.json', diagnostics.get('tower_hp_semantic_gap_report')),
        ('tower_regen_ep_semantic_gap_report.json', diagnostics.get('tower_regen_ep_semantic_gap_report')),
        ('tower_defense_absolute_semantic_gap_report.json', diagnostics.get('tower_defense_absolute_semantic_gap_report')),
        ('tower_damage_runtime_gap_report.json', diagnostics.get('tower_damage_runtime_gap_report')),
    ]
    for name, payload in residue_reports:
        if payload:
            path = out_dir / name
            path.write_text(json.dumps(js(_json_sanitize(payload, root_path)), indent=2, default=str), encoding='utf-8')
            written.append(name)

    # CSV export
    verification_rows = js([{'destination': k, **v} for k, v in line_verification.items()])
    csv_path = out_dir / 'line_by_line_verification.csv'
    pd.DataFrame(verification_rows).to_csv(csv_path, index=False)
    written.append('line_by_line_verification.csv')

    return written
