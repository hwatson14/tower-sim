"""
app/publication.py -- Pipeline output and trace persistence. AUTHORITY (T12).

T12: sharded from app/pipeline.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models import PipelineTrace

def _json_sanitize(obj, root_path: Path):
    if isinstance(obj, Path):
        try:
            return str(obj.resolve().relative_to(root_path))
        except Exception:
            try:
                return str(obj.relative_to(root_path))
            except Exception:
                return str(obj)
    if isinstance(obj, dict):
        return {k: _json_sanitize(v, root_path) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v, root_path) for v in obj]
    if isinstance(obj, tuple):
        return [_json_sanitize(v, root_path) for v in obj]
    return obj

def write_pipeline_trace(out_dir: Path, trace: PipelineTrace, root_path: Path) -> Path:
    path = out_dir / 'pipeline_trace.json'
    payload = trace.to_dict()
    sanitized = _json_sanitize(payload, root_path)
    path.write_text(json.dumps(sanitized, indent=2, default=str), encoding='utf-8')
    return path

def _remove_run_stats_legacy_outputs(out_dir: Path) -> None:
    legacy = (
        'statbook_start_of_run.json',
        'statbook_max_progression.json',
        'stat_inputs_start_of_run.json',
        'stat_inputs_max_progression.json',
    )
    for name in legacy:
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
) -> list[str]:
    import pandas as pd
    from qe.contracts import normalize_contract_payload

    def js(obj):
        return normalize_contract_payload(_json_sanitize(obj, root_path))

    _remove_run_stats_legacy_outputs(out_dir)

    artifacts = [
        ('diagnostics.json', diagnostics),
        ('account_state.json', account_state_payload),
        ('stat_inputs.json', stat_inputs_payload),
        ('statbook.json', statbook_dict),
        ('statbook_publishable.json', statbook_publishable_dict),
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
        path.write_text(json.dumps(js(payload), indent=2, default=str), encoding='utf-8')
        written.append(name)

    # Residue reports
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
            path.write_text(json.dumps(js(payload), indent=2, default=str), encoding='utf-8')
            written.append(name)

    # CSV export
    verification_rows = js([{'destination': k, **v} for k, v in line_verification.items()])
    csv_path = out_dir / 'line_by_line_verification.csv'
    pd.DataFrame(verification_rows).to_csv(csv_path, index=False)
    written.append('line_by_line_verification.csv')

    return written
