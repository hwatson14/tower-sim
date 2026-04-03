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
from qe.contracts import contract_json_payload as js
from app.models import _normalize_perk_state

ROOT = Path(__file__).resolve().parents[1]

# --- Helper Functions ---

def _relpath_str(path: Path | str | None, root_path: Path | None = None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    base = root_path or ROOT
    try:
        return str(p.relative_to(base))
    except (ValueError, RuntimeError):
        return str(p)

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


def _dashboard_token_row(row: list[object], width: int) -> list[str]:
    tokens = [str(value).strip() for value in list(row or [])[:width]]
    if len(tokens) < width:
        tokens.extend([''] * (width - len(tokens)))
    return tokens


def _dashboard_gap(panel_id: str, gap_id: str, detail: str) -> dict[str, str]:
    return {'panel_id': panel_id, 'gap_id': gap_id, 'detail': detail}


def _preset_options(account_state_payload: dict) -> list[str]:
    presets = list((account_state_payload.get('card_presets') or {}).keys())
    canonical = ['Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5']
    merged = canonical + [preset for preset in presets if preset not in canonical]
    return merged or ['Farming']


def _build_labs_panel(account_state_payload: dict, section_layout: dict[str, object]) -> tuple[dict[str, object], list[dict[str, str]]]:
    layout = section_layout.get('labs') or {}
    bucket_order = list(layout.get('bucket_order') or [])
    bucket_labels = {str(k): str(v) for k, v in (layout.get('bucket_labels') or {}).items()}
    bucket_registry = {str(k): str(v) for k, v in (layout.get('bucket_registry') or {}).items()}
    rows_by_bucket: dict[str, list[dict[str, object]]] = {bucket_id: [] for bucket_id in bucket_order}
    for lab_name, level in (account_state_payload.get('labs') or {}).items():
        bucket_id = bucket_registry.get(str(lab_name), 'misc')
        rows_by_bucket.setdefault(bucket_id, [])
        rows_by_bucket[bucket_id].append(
            {
                'name': str(lab_name),
                'level': '' if level is None else str(level),
                'max': '',
            }
        )
    buckets = []
    for bucket_id in bucket_order:
        rows = rows_by_bucket.get(bucket_id) or []
        if rows:
            buckets.append(
                {
                    'bucket_id': bucket_id,
                    'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()),
                    'rows': rows,
                }
            )
    for bucket_id, rows in rows_by_bucket.items():
        if rows and bucket_id not in bucket_order:
            buckets.append(
                {
                    'bucket_id': bucket_id,
                    'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()),
                    'rows': rows,
                }
            )
    return (
        {
            'panel_id': 'labs',
            'panel_type': 'labs_bucket_grid',
            'title': 'Labs',
            'payload': {
                'column_headers': ['Name', 'Level', 'Max'],
                'bucket_order': bucket_order,
                'buckets': buckets,
            },
        },
        [],
    )


def _build_workshop_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, object]]] = {'offense': [], 'defense': [], 'utility': []}
    gaps: list[dict[str, str]] = []
    for name, row in (account_state_payload.get('workshop') or {}).items():
        category = str((row or {}).get('category') or '').strip().lower()
        category = category if category in groups else 'utility'
        preset_levels = dict((row or {}).get('preset_levels') or {})
        preset_values = dict((row or {}).get('preset_values') or {})
        max_value = ''
        if not max_value:
            gaps.append(_dashboard_gap('workshop', 'max_value_not_published_upstream', f'Max Value missing for {name}'))
        groups[category].append(
            {
                'unlock': (row or {}).get('unlocked') or '',
                'name': name,
                'coin_level': '' if preset_levels.get(selected_preset) is None else str(preset_levels.get(selected_preset)),
                'coin_value': '' if preset_values.get(selected_preset) is None else str(preset_values.get(selected_preset)),
                'max_level': '' if (row or {}).get('max_level') is None else str((row or {}).get('max_level')),
                'max_value': max_value,
            }
        )
    payload = {
        'column_headers': ['Unlock', 'Name', 'Coin Level', 'Coin Value', 'Max Level', 'Max Value'],
        'groups': groups,
    }
    return ({'panel_id': 'workshop', 'panel_type': 'grouped_workshop_table', 'title': 'Workshop', 'payload': payload}, gaps)


def _build_workshop_enhancements_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, object]]] = {'offense': [], 'defense': [], 'utility': []}
    for name, row in (account_state_payload.get('workshop_enhancement_tracks') or {}).items():
        category = str((row or {}).get('category') or '').strip().lower()
        category = category if category in groups else 'utility'
        preset_levels = dict((row or {}).get('preset_levels') or {})
        groups[category].append(
            {
                'name': name,
                'level': '' if preset_levels.get(selected_preset) is None else str(preset_levels.get(selected_preset)),
                'max': '' if (row or {}).get('max_level') is None else str((row or {}).get('max_level')),
                'value': '' if (row or {}).get('current_multiplier') is None else str((row or {}).get('current_multiplier')),
            }
        )
    return ({'panel_id': 'workshop_enhancements', 'panel_type': 'grouped_enhancement_table', 'title': 'Workshop Enhancements', 'payload': {'column_headers': ['Name', 'Level', 'Max', 'Value'], 'groups': groups}}, [])


def _build_uw_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    uw_plus_tracks = account_state_payload.get('uw_plus_tracks') or {}
    rows: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []
    for uw_name, tracks in (account_state_payload.get('uw_tracks') or {}).items():
        unlock = (account_state_payload.get('ultimate_weapons') or {}).get(uw_name, {}).get('unlocked') or ''
        for track in tracks or []:
            plus_key = f"{uw_name}::{track.get('track_name') or ''}"
            rows.append(
                {
                    'unlock': unlock,
                    'uw': uw_name,
                    'track': track.get('track_name') or '',
                    'stone_level': '' if track.get('level') is None else str(track.get('level')),
                    'stone_value': '' if track.get('resolved_value') is None else str(track.get('resolved_value')),
                    'lab': '',
                    'module': '',
                    'perk': '',
                    'final': '' if track.get('resolved_value') is None else str(track.get('resolved_value')),
                    'uw_plus': ((uw_plus_tracks.get(plus_key) or {}).get('display_token') or ''),
                }
            )
            gaps.extend(
                [
                    _dashboard_gap('ultimate_weapons', 'lab_column_not_published_upstream', f'Lab column missing for {plus_key}'),
                    _dashboard_gap('ultimate_weapons', 'module_column_not_published_upstream', f'Module column missing for {plus_key}'),
                    _dashboard_gap('ultimate_weapons', 'perk_column_not_published_upstream', f'Perk column missing for {plus_key}'),
                    _dashboard_gap('ultimate_weapons', 'final_column_not_published_upstream', f'Final column defaults to stone value for {plus_key}'),
                ]
            )
    return ({'panel_id': 'ultimate_weapons', 'panel_type': 'uw_track_table', 'title': 'Ultimate Weapons', 'payload': {'column_headers': ['Unlock', 'UW', 'Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Perk', 'Final', 'UW+'], 'rows': rows}}, gaps)


def _build_cards_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    inventory_rows = []
    for card_name, card_payload in (account_state_payload.get('cards_inventory') or {}).items():
        inventory_rows.append({'name': card_name, 'level': card_payload.get('level') or '', 'mastery': card_payload.get('mastery_lab_level') or ''})
    selected_cards = set((account_state_payload.get('card_presets') or {}).get(selected_preset) or [])
    preset_rows = [{'name': card_name, 'selected': 'Yes' if card_name in selected_cards else ''} for card_name in sorted((account_state_payload.get('cards_inventory') or {}).keys())]
    return ({'panel_id': 'cards', 'panel_type': 'cards_inventory_and_preset', 'title': 'Cards', 'payload': {'inventory_rows': inventory_rows, 'preset_rows': preset_rows, 'slot_count': account_state_payload.get('card_slots_unlocked') or ''}}, [])


def _build_track_rows(rows: list[dict[str, object]], owner_label: str) -> list[dict[str, object]]:
    out = []
    current_name = ''
    for row in rows:
        current_name = str(row.get(owner_label) or current_name)
        out.append({'unlock': row.get('unlock') or '', owner_label: current_name, 'track': row.get('track') or '', 'level': row.get('level') or '', 'value': row.get('value') or ''})
    return out


def _build_bots_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    for bot_name, tracks in (account_state_payload.get('bot_upgrade_tracks') or {}).items():
        for track in tracks or []:
            rows.append({'unlock': '', 'bot': bot_name, 'track': track.get('track_name') or '', 'level': '' if track.get('level') is None else str(track.get('level')), 'value': '' if track.get('resolved_value') is None else str(track.get('resolved_value'))})
    return ({'panel_id': 'bots', 'panel_type': 'track_table', 'title': 'Bots', 'payload': {'entity_key': 'bot', 'column_headers': ['Unlock', 'Bot', 'Track', 'Level', 'Value'], 'rows': rows}}, [])


def _build_simple_bonus_panel(panel_id: str, title: str, section_rows: list[list[object]]) -> dict[str, object]:
    rows = []
    for row in section_rows:
        name, bonus, _ = _dashboard_token_row(row, 3)
        if name or bonus:
            rows.append({'name': name, 'bonus': bonus})
    return {'panel_id': panel_id, 'panel_type': 'simple_bonus_table', 'title': title, 'payload': {'column_headers': ['Name', 'Bonus'], 'rows': rows}}


def _build_modules_panel(module_card_payloads: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    gaps: list[dict[str, str]] = []
    presets = module_card_payloads.get('presets') or {}
    preset_payload = presets.get(selected_preset)
    if not preset_payload:
        gaps.append(_dashboard_gap('modules', 'module_card_payloads_missing', 'module_card_payloads.json missing selected preset payload'))
        return ({'panel_id': 'modules', 'panel_type': 'module_slot_stack', 'title': 'Modules', 'payload': {'selected_preset': selected_preset, 'slots': {}, 'message': 'Module card payload unavailable.'}}, gaps)
    return ({'panel_id': 'modules', 'panel_type': 'module_slot_stack', 'title': 'Modules', 'payload': {'selected_preset': selected_preset, 'slots': preset_payload}}, gaps)


def _build_guardians_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    for guardian_name, tracks in (account_state_payload.get('guardian_tracks') or {}).items():
        for track in tracks or []:
            rows.append({'unlock': '', 'guardian': guardian_name, 'track': track.get('track_name') or '', 'level': '' if track.get('level') is None else str(track.get('level')), 'value': '' if track.get('resolved_value') is None else str(track.get('resolved_value'))})
    return ({'panel_id': 'guardians', 'panel_type': 'track_table', 'title': 'Guardians', 'payload': {'entity_key': 'guardian', 'column_headers': ['Unlock', 'Guardian', 'Track', 'Level', 'Value'], 'rows': rows}}, [])


def _build_themes_panel(account_state_payload: dict) -> tuple[dict[str, object], list[dict[str, str]]]:
    value = account_state_payload.get('theme_song_coin_multiplier')
    return ({'panel_id': 'themes_and_songs', 'panel_type': 'simple_metric_panel', 'title': 'Themes and Songs', 'payload': {'metric_label': 'Coin Multiplier', 'metric_value': '' if value is None else str(value)}}, [])


def _build_input_dashboard_payload(
    account_state_payload: dict,
    diagnostics: dict,
    *,
    module_card_payloads: dict[str, object] | None = None,
) -> dict[str, object]:
    from input.state_builder import load_section_layout_contract

    selected_preset = str(account_state_payload.get('default_preset') or 'Farming')
    preset_options = _preset_options(account_state_payload)
    if selected_preset not in preset_options:
        selected_preset = preset_options[0]

    section_layout = load_section_layout_contract()
    panels = []
    gaps: list[dict[str, str]] = []

    for builder in [
        lambda: _build_labs_panel(account_state_payload, section_layout),
        lambda: _build_workshop_panel(account_state_payload, selected_preset),
        lambda: _build_workshop_enhancements_panel(account_state_payload, selected_preset),
        lambda: _build_uw_panel(account_state_payload),
        lambda: _build_cards_panel(account_state_payload, selected_preset),
        lambda: _build_bots_panel(account_state_payload),
        lambda: (_build_simple_bonus_panel('relics', 'Relics', (account_state_payload.get('raw_sections') or {}).get('Relics', [])), []),
        lambda: _build_modules_panel(module_card_payloads or {}, selected_preset),
        lambda: (_build_simple_bonus_panel('vault', 'Vault', (account_state_payload.get('raw_sections') or {}).get('Vault', [])), []),
        lambda: _build_guardians_panel(account_state_payload),
        lambda: _build_themes_panel(account_state_payload),
    ]:
        panel, panel_gaps = builder()
        panels.append(panel)
        gaps.extend(panel_gaps)

    return {
        'schema_version': 1,
        'selected_preset': selected_preset,
        'preset_options': preset_options,
        'upstream_gaps': gaps,
        'panels': panels,
        'debug_manifest': {
            'source_artifacts': ['account_state.json', 'module_card_payloads.json', 'diagnostics.json'],
            'generated_from': list((diagnostics.get('section_names') or [])),
        },
    }

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
) -> list[str]:

    _remove_legacy_outputs(out_dir, _ANALYSIS_PIPELINE_LEGACY_OUTPUTS)

    input_dashboard_payload = _build_input_dashboard_payload(
        account_state_payload,
        diagnostics,
        module_card_payloads=module_card_payloads,
    )
    artifacts = [
        ('diagnostics.json', diagnostics),
        ('account_state.json', account_state_payload),
        ('input_dashboard.json', input_dashboard_payload),
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
