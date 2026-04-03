"""
app/publication.py -- Pipeline output and trace persistence. AUTHORITY (T12).

T12: sharded from app/pipeline.py.
"""
from __future__ import annotations

import json
import csv
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


def _load_lab_bucket_registry() -> tuple[dict[str, str], list[dict[str, str]]]:
    """Return (lab_name -> bucket_key, bucket metadata list) from KB-owned registry data."""
    registry_path = ROOT / 'kb' / 'labs' / 'tables' / 'lab-application-registry.csv'
    domain_to_bucket = {
        'tower_or_wall_stat': ('attack_defense', 'Attack/Defense'),
        'economy': ('utility_economy', 'Utility/Economy'),
        'ultimate_weapon_duration': ('ultimate_weapons', 'Ultimate Weapons'),
        'ultimate_weapon_damage': ('ultimate_weapons', 'Ultimate Weapons'),
        'ultimate_weapon_control': ('ultimate_weapons', 'Ultimate Weapons'),
        'ultimate_weapon_proc': ('ultimate_weapons', 'Ultimate Weapons'),
        'ultimate_weapon_bonus': ('ultimate_weapons', 'Ultimate Weapons'),
        'bot': ('bots', 'Bots'),
        'perk': ('perks', 'Perks'),
        'enemy_modifier': ('misc', 'Misc'),
        'module': ('modules', 'Modules'),
        'meta': ('main', 'Main'),
    }
    buckets_meta = [{'bucket_key': key, 'title': title} for key, title in dict.fromkeys(domain_to_bucket.values())]
    name_to_bucket: dict[str, str] = {}
    if not registry_path.exists():
        return name_to_bucket, buckets_meta
    with registry_path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            lab_name = str(row.get('lab_primary_name') or '').strip()
            target_domain = str(row.get('target_domain') or '').strip()
            if not lab_name:
                continue
            bucket = domain_to_bucket.get(target_domain, ('misc', 'Misc'))
            name_to_bucket[lab_name] = bucket[0]
    return name_to_bucket, buckets_meta


def _build_input_dashboard_payload(
    account_state_payload: dict,
    diagnostics: dict,
    *,
    qe_dashboard_publications: dict[str, object] | None = None,
) -> dict[str, object]:
    qe_published = qe_dashboard_publications or {}
    workshop_coin_values = dict(qe_published.get('workshop_coin_values') or {})
    workshop_max_values = dict(qe_published.get('workshop_max_values') or {})
    uw_track_effects = dict(qe_published.get('uw_track_effects') or {})
    raw_sections = (account_state_payload.get('raw_sections') or {}) if isinstance(account_state_payload, dict) else {}
    preset_names = list((account_state_payload.get('card_presets') or {}).keys()) if isinstance(account_state_payload, dict) else []
    active_preset = (account_state_payload.get('default_preset') or 'Farming') if isinstance(account_state_payload, dict) else 'Farming'
    if active_preset and active_preset not in preset_names:
        preset_names = [active_preset] + [name for name in preset_names if name != active_preset]
    if not preset_names:
        preset_names = [active_preset]

    labs_rows = []
    for row in raw_sections.get('Labs', []):
        name, level, _target, max_level = _dashboard_token_row(row, 4)
        if not name:
            continue
        labs_rows.append({'name': name, 'current': level, 'max': max_level})
    lab_bucket_registry, buckets_meta = _load_lab_bucket_registry()
    bucket_rows: dict[str, list[dict[str, str]]] = {}
    for row in labs_rows:
        bucket_key = lab_bucket_registry.get(row['name'], 'misc')
        bucket_rows.setdefault(bucket_key, []).append(row)
    labs_buckets = []
    for item in buckets_meta:
        rows = bucket_rows.get(item['bucket_key'], [])
        if rows:
            labs_buckets.append({'bucket_key': item['bucket_key'], 'title': item['title'], 'rows': rows})
    if bucket_rows.get('misc') and all(b.get('bucket_key') != 'misc' for b in labs_buckets):
        labs_buckets.append({'bucket_key': 'misc', 'title': 'Misc', 'rows': bucket_rows.get('misc', [])})

    ws_rows = []
    ws_raw = list(raw_sections.get('WS', []))
    if len(ws_raw) > 1:
        header = _dashboard_token_row(ws_raw[1], len(ws_raw[1]))
        for row in ws_raw[2:]:
            tokens = _dashboard_token_row(row, len(header))
            name = tokens[0]
            if not name:
                continue
            ws_rows.append(
                {
                    'name': name,
                    'coin_level': tokens[1],
                    'coin_value': workshop_coin_values.get(name, tokens[2]),
                    'max_level': tokens[-1],
                    'max_value': workshop_max_values.get(name, ''),
                    'max_value_source': 'qe_published' if name in workshop_max_values else 'qe_unavailable',
                }
            )

    ws_plus_rows = []
    for row in raw_sections.get('WS+', [])[2:]:
        tokens = _dashboard_token_row(row, 8)
        name = tokens[0]
        if not name:
            continue
        ws_plus_rows.append({'name': name, 'value': tokens[1], 'level': tokens[2], 'max': tokens[7]})

    uw_rows = []
    uw_plus_tracks = (account_state_payload.get('uw_plus_tracks') or {}) if isinstance(account_state_payload, dict) else {}
    labs_lookup = (account_state_payload.get('labs') or {}) if isinstance(account_state_payload, dict) else {}
    current_uw = ''
    current_unlock_state = ''
    for row in raw_sections.get('UWs', []):
        tokens = _dashboard_token_row(row, 5)
        if tokens[0] and tokens[1].strip().lower() not in {'uw unlocked', 'uw locked'}:
            current_uw = tokens[0]
        if tokens[1].strip().lower() in {'uw unlocked', 'uw locked'}:
            current_unlock_state = tokens[1].strip()
        uw_name = current_uw
        track_name = tokens[2]
        if not uw_name or not track_name:
            continue
        plus_key = f'{uw_name}::{track_name}'
        uw_rows.append(
            {
                'uw_name': uw_name,
                'track_name': track_name,
                'unlock_state': current_unlock_state,
                'stone_level': tokens[4].split('|', 1)[0].strip() if tokens[4] else '',
                'stone_value': tokens[3],
                'stone_detail': tokens[4],
                'lab_value': labs_lookup.get(f'{uw_name} {track_name}'),
                'module_effect': (uw_track_effects.get(plus_key) or {}).get('module_effect') or '',
                'module_effect_source': 'qe_published' if plus_key in uw_track_effects else 'qe_unavailable',
                'perk_effect': (uw_track_effects.get(plus_key) or {}).get('perk_effect') or '',
                'perk_effect_source': 'qe_published' if plus_key in uw_track_effects else 'qe_unavailable',
                'final_value': (uw_track_effects.get(plus_key) or {}).get('final_value') or tokens[3] or '',
                'plus_track': (uw_plus_tracks.get(plus_key) or {}).get('name'),
            }
        )

    cards_rows = []
    cards_raw = list(raw_sections.get('Cards', []))
    if cards_raw:
        preset_columns = cards_raw[0][3:]
        for row in cards_raw:
            tokens = _dashboard_token_row(row, 3 + len(preset_columns))
            card_name = tokens[0]
            if not card_name:
                continue
            row_payload = {'name': card_name, 'level': tokens[1], 'mastery': tokens[2]}
            for idx, preset_name in enumerate(preset_columns):
                row_payload[f'preset::{preset_name}'] = tokens[3 + idx]
            cards_rows.append(row_payload)

    section_map = {'Relics': 'relics', 'Vault': 'vault', 'Themes & Songs': 'themes_and_songs'}
    simple_bonus_payloads = {}
    for source_name, panel_id in section_map.items():
        rows = []
        for row in raw_sections.get(source_name, []):
            left, right, detail = _dashboard_token_row(row, 3)
            if not (left or right or detail):
                continue
            rows.append({'label': left, 'value': right, 'detail': detail})
        simple_bonus_payloads[panel_id] = rows

    panels = [
        {'panel_id': 'labs', 'panel_type': 'labs_bucket_panel', 'title': 'Labs', 'layout': {'span': 12}, 'payload': {'buckets': labs_buckets, 'columns': ['name', 'current', 'max']}},
        {'panel_id': 'workshop', 'panel_type': 'workshop_table_panel', 'title': 'WORKSHOP', 'layout': {'span': 6}, 'payload': {'rows': ws_rows, 'columns': ['unlock', 'name', 'coin_level', 'coin_value', 'max_level', 'max_value']}},
        {'panel_id': 'workshop_enhancements', 'panel_type': 'workshop_enhancement_table_panel', 'title': 'WORKSHOP ENHANCEMENTS', 'layout': {'span': 6}, 'payload': {'rows': ws_plus_rows, 'columns': ['name', 'level', 'max', 'value']}},
        {'panel_id': 'ultimate_weapons', 'panel_type': 'uw_track_panel', 'title': 'ULTIMATE WEAPONS', 'layout': {'span': 12}, 'payload': {'rows': uw_rows}},
        {'panel_id': 'cards', 'panel_type': 'cards_inventory_plus_preset_panel', 'title': 'CARDS', 'layout': {'span': 12}, 'payload': {'rows': cards_rows, 'preset_columns': [str(name) for name in (cards_raw[0][3:] if cards_raw else [])]}},
        {'panel_id': 'bots', 'panel_type': 'bot_track_panel', 'title': 'BOTS', 'layout': {'span': 6}, 'payload': {'rows': [dict(name=_dashboard_token_row(r, 5)[0], attribute=_dashboard_token_row(r, 5)[2], value=_dashboard_token_row(r, 5)[3], detail=_dashboard_token_row(r, 5)[4]) for r in raw_sections.get('Bots', [])]}},
        {'panel_id': 'relics', 'panel_type': 'simple_bonus_table_panel', 'title': 'RELICS', 'layout': {'span': 6}, 'payload': {'rows': simple_bonus_payloads['relics']}},
        {'panel_id': 'modules', 'panel_type': 'module_slot_stack_panel', 'title': 'MODULES', 'layout': {'span': 12}, 'payload': {'rows': [dict(tokens=_dashboard_token_row(row, 19)) for row in raw_sections.get('Modules', [])]}},
        {'panel_id': 'vault', 'panel_type': 'simple_bonus_table_panel', 'title': 'VAULT', 'layout': {'span': 6}, 'payload': {'rows': simple_bonus_payloads['vault']}},
        {'panel_id': 'guardians', 'panel_type': 'guardian_track_panel', 'title': 'GUARDIANS', 'layout': {'span': 6}, 'payload': {'rows': [dict(name=_dashboard_token_row(r, 5)[0], attribute=_dashboard_token_row(r, 5)[2], value=_dashboard_token_row(r, 5)[3], detail=_dashboard_token_row(r, 5)[4]) for r in raw_sections.get('Guardians', [])]}},
        {'panel_id': 'themes_and_songs', 'panel_type': 'simple_bonus_table_panel', 'title': 'Themes and Songs', 'layout': {'span': 6}, 'payload': {'rows': simple_bonus_payloads['themes_and_songs']}},
    ]

    gaps = []
    if not lab_bucket_registry:
        gaps.append('labs_bucket_registry_missing_upstream')

    return {
        'schema_version': 1,
        'preset_selector': {
            'available': preset_names,
            'default': preset_names[0] if preset_names else active_preset,
            'active_from_account_state': active_preset,
        },
        'panels': panels,
        'debug_sources': {'account_state': 'out/account_state.json', 'stat_inputs': 'out/stat_inputs.json'},
        'upstream_gaps': sorted(set(gaps)),
        'required_upstream_publications': {},
        'diagnostic_snapshot': {
            'section_names': list((diagnostics.get('section_names') or [])),
            'section_row_counts': dict(diagnostics.get('section_row_counts') or {}),
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
    qe_dashboard_publications: dict[str, object] | None = None,
) -> list[str]:

    _remove_legacy_outputs(out_dir, _ANALYSIS_PIPELINE_LEGACY_OUTPUTS)

    input_dashboard_payload = _build_input_dashboard_payload(
        account_state_payload,
        diagnostics,
        qe_dashboard_publications=qe_dashboard_publications,
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
