"""
app/publication.py -- Output publication and cleanup helpers.
"""
from __future__ import annotations

import json
from pathlib import Path


def _write_core_outputs(
    *,
    out_dir: Path,
    diagnostics: dict,
    account_state,
    canonical_output_preset: str,
    stat_inputs,
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
) -> None:
    import pandas as pd
    from qe.contracts import contract_json_payload as js
    from app.pipeline import _sanitized_account_state_for_output

    (out_dir / 'diagnostics.json').write_text(json.dumps(js(diagnostics), indent=2, default=str))
    (out_dir / 'account_state.json').write_text(
        json.dumps(js(_sanitized_account_state_for_output(account_state, canonical_output_preset)), indent=2, default=str)
    )
    (out_dir / 'stat_inputs.json').write_text(
        json.dumps(js([row.to_dict() for row in stat_inputs]), indent=2, default=str)
    )
    (out_dir / 'statbook.json').write_text(json.dumps(js(statbook_dict), indent=2, default=str))
    (out_dir / 'statbook_publishable.json').write_text(
        json.dumps(js(statbook_publishable_dict), indent=2, default=str)
    )
    (out_dir / 'ep_oracle_compare.json').write_text(
        json.dumps(js(ep_compare_publishable), indent=2, default=str)
    )
    (out_dir / 'line_by_line_verification.json').write_text(
        json.dumps(js(line_verification), indent=2, default=str)
    )
    (out_dir / 'survivor_closure_report.json').write_text(
        json.dumps(js(survivor_closure_report), indent=2, default=str)
    )
    (out_dir / 'state_matrix.json').write_text(json.dumps(js(state_matrix), indent=2, default=str))
    (out_dir / 'audit_surface_manifest.json').write_text(
        json.dumps(js(audit_surface_manifest), indent=2, default=str)
    )
    (out_dir / 'artifact_contract_manifest.json').write_text(
        json.dumps(js(artifact_contract_manifest), indent=2, default=str)
    )
    (out_dir / 'family_completeness_matrix.json').write_text(
        json.dumps(js(family_completeness_matrix), indent=2, default=str)
    )
    (out_dir / 'optimizer_scores.json').write_text(json.dumps(js(optimizer_scores), indent=2, default=str))
    verification_rows = js([{'destination': k, **v} for k, v in line_verification.items()])
    pd.DataFrame(verification_rows).to_csv(out_dir / 'line_by_line_verification.csv', index=False)


def _remove_run_stats_legacy_outputs(out_dir: Path) -> None:
    from app.pipeline import _RUN_STATS_LEGACY_OUTPUTS
    for name in _RUN_STATS_LEGACY_OUTPUTS:
        path = out_dir / name
        if path.exists():
            path.unlink()


def _cleanup_stale_outputs(out_dir: Path) -> None:
    stale_outputs = [
        'ep_oracle_compare_backfilled.json',
        'statbook_oracle_backfilled.json',
        'destination_formula_ledger.json',
        'forensic_debug_focus.json',
    ]
    for stale_name in stale_outputs:
        stale_path = out_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
