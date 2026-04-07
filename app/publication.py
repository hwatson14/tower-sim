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
from qe.models import StatRow
from qe.publication import publish_query_surfaces as qe_publish_query_surfaces, publish_workshop_reconciliation_payload
from app.models import _normalize_perk_state
from app.display import annotate_display_fields
from input.lab_category_registry import load_lab_category_registry_by_raw_name

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


def _dashboard_token_row(row: list[object], width: int) -> list[str]:
    tokens = [str(value).strip() for value in list(row or [])[:width]]
    if len(tokens) < width:
        tokens.extend([''] * (width - len(tokens)))
    return tokens


def _dashboard_gap(panel_id: str, gap_id: str, detail: str) -> dict[str, str]:
    return {'panel_id': panel_id, 'gap_id': gap_id, 'detail': detail}


def _dashboard_display_token(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _preset_options(account_state_payload: dict) -> list[str]:
    default_preset = str(account_state_payload.get('default_preset') or 'Farming')
    canonical_order = ['Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5']

    source_options: list[str] = []
    seen: set[str] = set()

    def _add_option(name: object) -> None:
        value = str(name).strip()
        if value and value not in seen:
            seen.add(value)
            source_options.append(value)

    for preset_name in (account_state_payload.get('card_presets') or {}).keys():
        _add_option(preset_name)
    for preset_name in (account_state_payload.get('module_presets') or {}).keys():
        _add_option(preset_name)
    for row in (account_state_payload.get('workshop') or {}).values():
        for preset_name in dict((row or {}).get('preset_levels') or {}).keys():
            _add_option(preset_name)
        for preset_name in dict((row or {}).get('preset_values') or {}).keys():
            _add_option(preset_name)
    for row in (account_state_payload.get('workshop_enhancement_tracks') or {}).values():
        for preset_name in dict((row or {}).get('preset_levels') or {}).keys():
            _add_option(preset_name)

    _add_option(default_preset)
    if not source_options and len(seen) == 1:
        return [default_preset] if default_preset else ['Farming']

    options = [name for name in canonical_order if name in seen]
    options.extend(name for name in source_options if name not in canonical_order)
    if not options:
        return ['Farming']
    return options


def _build_labs_panel(account_state_payload: dict, section_layout: dict[str, object]) -> tuple[dict[str, object], list[dict[str, str]]]:
    raw_rows = list(((account_state_payload.get('raw_sections') or {}).get('Labs') or []))
    labs_rows = []
    for row in raw_rows:
        name, level, _target, max_level = _dashboard_token_row(row, 4)
        if name and name != 'END OF ARRAY':
            labs_rows.append({'name': name, 'level': level, 'max': max_level})

    labs_layout = dict(section_layout.get('labs') or {})
    bucket_order = [str(name) for name in (labs_layout.get('bucket_order') or [])]
    bucket_labels = {str(k): str(v) for k, v in (labs_layout.get('bucket_labels') or {}).items()}
    lab_category_registry = load_lab_category_registry_by_raw_name()

    layout_bucket_ids = set(bucket_order) | set(bucket_labels.keys())
    misc_bucket_id = 'misc' if 'misc' in layout_bucket_ids else None
    rows_by_bucket: dict[str, list[dict[str, str]]] = {}
    gaps: list[dict[str, str]] = []
    for row in labs_rows:
        taxonomy = lab_category_registry.get(row['name']) or {}
        bucket_id = str(taxonomy.get('category_ui') or 'misc')
        if bucket_id == 'misc':
            gaps.append(_dashboard_gap('labs', 'lab_category_registry_missing', f'Lab category mapping missing for {row["name"]}'))
        rows_by_bucket.setdefault(bucket_id, []).append(row)

    buckets = []
    for bucket_id in bucket_order:
        rows = rows_by_bucket.get(bucket_id) or []
        if rows:
            buckets.append({'bucket_id': bucket_id, 'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()), 'rows': rows})
    for bucket_id, rows in rows_by_bucket.items():
        if rows and bucket_id not in bucket_order:
            buckets.append({'bucket_id': bucket_id, 'bucket_label': bucket_labels.get(bucket_id, bucket_id.replace('_', ' ').title()), 'rows': rows})

    return (
        {
            'panel_id': 'labs',
            'panel_type': 'labs_bucket_grid',
            'title': 'Labs',
            'payload': {'column_headers': ['Name', 'Level', 'Max'], 'bucket_order': bucket_order, 'buckets': buckets},
        },
        gaps,
    )


def _build_workshop_panel(
    account_state_payload: dict,
    selected_preset: str,
    qe_dashboard_publications: dict[str, object] | None = None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, object]]] = {'offense': [], 'defense': [], 'utility': []}
    gaps: list[dict[str, str]] = []
    qe_published = qe_dashboard_publications or {}
    workshop_coin_values = dict(qe_published.get('workshop_coin_values') or {})
    workshop_max_values = dict(qe_published.get('workshop_max_values') or {})
    for name, row in (account_state_payload.get('workshop') or {}).items():
        category = str((row or {}).get('category') or '').strip().lower()
        category = category if category in groups else 'utility'
        preset_levels = dict((row or {}).get('preset_levels') or {})
        preset_values = dict((row or {}).get('preset_values') or {})
        unlock_value = (row or {}).get('unlocked')
        if unlock_value is None:
            level_value = preset_levels.get(selected_preset)
            unlock_value = bool(level_value) if level_value is not None else None
        coin_level_value = preset_levels.get(selected_preset)
        max_level_value = (row or {}).get('max_level')
        coin_value = workshop_coin_values.get(name, preset_values.get(selected_preset))
        max_value = workshop_max_values.get(name, '')
        if max_value in (None, '') and coin_value not in (None, '') and coin_level_value is not None and max_level_value is not None:
            if str(coin_level_value) == str(max_level_value):
                max_value = coin_value
        if max_value in (None, ''):
            gaps.append(_dashboard_gap('workshop', 'max_value_not_published_upstream', f'Max Value missing for {name}'))
        output_row = {
            'unlock': _dashboard_display_token(unlock_value),
            'name': name,
            'coin_level': '' if preset_levels.get(selected_preset) is None else str(preset_levels.get(selected_preset)),
            'coin_value': '' if coin_value is None else str(coin_value),
            'max_level': '' if (row or {}).get('max_level') is None else str((row or {}).get('max_level')),
            'max_value': '' if max_value is None else str(max_value),
        }
        groups[category].append(output_row)
    payload: dict[str, object] = {
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


def _build_uw_panel(
    account_state_payload: dict,
    qe_dashboard_publications: dict[str, object] | None = None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    uw_plus_tracks = account_state_payload.get('uw_plus_tracks') or {}
    qe_published = qe_dashboard_publications or {}
    uw_track_effects = dict(qe_published.get('uw_track_effects') or {})
    rows: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []
    for uw_name, tracks in (account_state_payload.get('uw_tracks') or {}).items():
        unlock = _dashboard_display_token((account_state_payload.get('ultimate_weapons') or {}).get(uw_name, {}).get('unlocked'))
        for track in tracks or []:
            plus_key = f"{uw_name}::{track.get('track_name') or ''}"
            published_effects = dict(uw_track_effects.get(plus_key) or {})
            lab_effect = published_effects.get('lab_effect')
            module_effect = published_effects.get('module_effect')
            perk_effect = published_effects.get('perk_effect')
            final_value = published_effects.get('final_value')
            rows.append(
                {
                    'unlock': unlock,
                    'uw': uw_name,
                    'track': track.get('track_name') or '',
                    'stone_level': '' if track.get('level') is None else str(track.get('level')),
                    'stone_value': '' if track.get('resolved_value') is None else str(track.get('resolved_value')),
                    'lab': '' if lab_effect is None else str(lab_effect),
                    'module': '' if module_effect is None else str(module_effect),
                    'perk': '' if perk_effect is None else str(perk_effect),
                    'final': '' if final_value is None else str(final_value),
                    'uw_plus': ((uw_plus_tracks.get(plus_key) or {}).get('display_token') or ''),
                }
            )
            if lab_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'lab_column_not_published_upstream', f'Lab column missing for {plus_key}'))
            if module_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'module_column_not_published_upstream', f'Module column missing for {plus_key}'))
            if perk_effect is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'perk_column_not_published_upstream', f'Perk column missing for {plus_key}'))
            if final_value is None:
                gaps.append(_dashboard_gap('ultimate_weapons', 'final_column_not_published_upstream', f'Final column missing for {plus_key}'))
    return ({'panel_id': 'ultimate_weapons', 'panel_type': 'uw_track_table', 'title': 'Ultimate Weapons', 'payload': {'column_headers': ['Unlock', 'UW', 'Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Perk', 'Final', 'UW+'], 'rows': rows}}, gaps)


def _build_cards_panel(account_state_payload: dict, selected_preset: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    inventory_rows = []
    for card_name, card_payload in (account_state_payload.get('cards_inventory') or {}).items():
        inventory_rows.append({'name': card_name, 'level': card_payload.get('level') or '', 'mastery': card_payload.get('mastery_lab_level') or ''})
    card_names = sorted((account_state_payload.get('cards_inventory') or {}).keys())
    preset_rows_by_preset: dict[str, list[dict[str, str]]] = {}
    card_presets = dict(account_state_payload.get('card_presets') or {})
    for preset_name in _preset_options(account_state_payload):
        preset_cards = card_presets.get(preset_name) or []
        selected_cards = set(preset_cards or [])
        preset_rows_by_preset[str(preset_name)] = [
            {'name': card_name, 'selected': 'Yes' if card_name in selected_cards else ''} for card_name in card_names
        ]

    selected_rows = preset_rows_by_preset.get(selected_preset, [{'name': card_name, 'selected': ''} for card_name in card_names])
    return (
        {
            'panel_id': 'cards',
            'panel_type': 'cards_inventory_and_preset',
            'title': 'Cards',
            'payload': {
                'inventory_rows': inventory_rows,
                'preset_rows': selected_rows,
                'preset_rows_by_preset': preset_rows_by_preset,
                'slot_count': account_state_payload.get('card_slots_unlocked') or '',
            },
        },
        [],
    )


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
    qe_dashboard_publications: dict[str, object] | None = None,
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
        lambda: _build_workshop_panel(
            account_state_payload,
            selected_preset,
            qe_dashboard_publications=qe_dashboard_publications,
        ),
        lambda: _build_workshop_enhancements_panel(account_state_payload, selected_preset),
        lambda: _build_uw_panel(account_state_payload, qe_dashboard_publications=qe_dashboard_publications),
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
        'schema_version': 2,
        'selected_preset': selected_preset,
        'preset_options': preset_options,
        'upstream_gaps': gaps,
        'panels': panels,
        'debug_manifest': {
            'source_artifacts': ['account_state.json', 'module_card_payloads.json', 'diagnostics.json'],
            'generated_from': list((diagnostics.get('section_names') or [])),
        },
    }


def _stats_rows_by_surface(rows_payload: dict[str, object] | None, preset: str) -> dict[str, dict[str, object]]:
    preset_payload = dict((rows_payload or {}).get(preset) or {})
    raw_rows = preset_payload.get('rows')
    if isinstance(raw_rows, dict):
        rows = dict(raw_rows)
    else:
        rows = dict(preset_payload)
    normalized: dict[str, dict[str, object]] = {}
    for raw_surface_id, payload in rows.items():
        normalized[normalize_surface_id_to_contract(str(raw_surface_id))] = dict(payload or {})
    return normalized


def _stats_surface_specs(layout: dict[str, object], key: str) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for entry in (layout.get(key) or []):
        if not isinstance(entry, dict):
            continue
        surface_id = normalize_surface_id_to_contract(str(entry.get('surface_id') or '').strip())
        label = str(entry.get('label') or '').strip()
        canonical_row_id = str(entry.get('canonical_row_id') or surface_id).strip()
        if surface_id and label:
            specs.append({'surface_id': surface_id, 'label': label, 'canonical_row_id': canonical_row_id})
    return specs


def _stats_row_payload(
    *,
    row_map: dict[str, dict[str, object]],
    ep_compare: dict[str, object],
    surface_id: str,
    label: str,
    canonical_row_id: str,
) -> dict[str, object]:
    row = dict(row_map.get(surface_id) or {})
    ep = dict(ep_compare.get(surface_id) or {})
    return {
        'canonical_row_id': canonical_row_id,
        'display_label': label,
        'label': label,
        'surface_id': surface_id,
        'display_value': row.get('display_value'),
        'value': row.get('final_value'),
        'status': row.get('status'),
        'ep_display': ep.get('ep_value_display') or ep.get('ep_value_raw'),
        'ep_delta': ep.get('delta_display'),
        'contributors_available': bool(row.get('contributors')),
    }


def _rows_with_qe_derived_values(rows: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    preserved_derived_rows: dict[str, dict[str, object]] = {}
    for surface_id, row in (rows or {}).items():
        if str(surface_id).startswith('derived::'):
            preserved_derived_rows[str(surface_id)] = dict(row or {})

    stat_rows: dict[str, StatRow] = {}
    for surface_id, row in (rows or {}).items():
        if str(surface_id).startswith('derived::'):
            continue
        payload = dict(row or {})
        stat_rows[str(surface_id)] = StatRow(
            stat_name=str(surface_id),
            final_value=payload.get('final_value'),
            value_type=str(payload.get('value_type') or 'scalar'),
            source_count=len(payload.get('contributors') or []),
            status=str(payload.get('status') or 'resolved'),
            notes=str(payload.get('notes') or ''),
            contributors=[dict(contributor or {}) for contributor in (payload.get('contributors') or [])],
            schema={},
        )
    qe_publish_query_surfaces(stat_rows)
    hydrated = {
        surface_id: {
            'stat_name': row.stat_name,
            'final_value': row.final_value,
            'value_type': row.value_type,
            'status': row.status,
            'contributors': [dict(contributor or {}) for contributor in (row.contributors or [])],
        }
        for surface_id, row in stat_rows.items()
    }
    hydrated.update(preserved_derived_rows)
    annotate_display_fields({'rows': hydrated})
    return hydrated


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
    from input.state_builder import load_section_layout_contract

    section_layout = load_section_layout_contract()
    stats_layout = dict(section_layout.get('stats_dashboard') or {})
    panel_order = [str(name) for name in (stats_layout.get('panel_order') or [])]
    state_mode_options = [str(name) for name in (stats_layout.get('state_mode_options') or ['start_of_run', 'max_progression'])]
    if selected_state_mode not in state_mode_options:
        selected_state_mode = state_mode_options[0]

    configured_preset_options = _preset_options(account_state_payload)
    available_query_presets = sorted(
        set((query_rows_start_of_run or {}).keys()) | set((query_rows_max_progression or {}).keys())
    )
    preset_options = [name for name in configured_preset_options if name in available_query_presets]
    preset_options.extend(name for name in available_query_presets if name not in preset_options)
    if not preset_options:
        preset_options = configured_preset_options
    if selected_preset not in preset_options:
        selected_preset = preset_options[0]

    input_panels_by_id = {
        str(panel.get('panel_id')): dict(panel or {})
        for panel in (input_dashboard_payload.get('panels') or [])
        if isinstance(panel, dict)
    }
    ep_compare = dict(ep_compare_publishable or {})
    row_map_by_mode = {
        'start_of_run': {preset_name: _stats_rows_by_surface(query_rows_start_of_run, preset_name) for preset_name in preset_options},
        'max_progression': {preset_name: _stats_rows_by_surface(query_rows_max_progression, preset_name) for preset_name in preset_options},
    }
    upstream_gaps: list[dict[str, str]] = []
    variants: dict[str, dict[str, list[dict[str, object]]]] = {}
    for preset_name in preset_options:
        start_rows_raw = _stats_rows_by_surface(query_rows_start_of_run, preset_name)
        max_rows_raw = _stats_rows_by_surface(query_rows_max_progression, preset_name)
        start_rows_hydrated = _rows_with_qe_derived_values(start_rows_raw)
        max_rows_hydrated = _rows_with_qe_derived_values(max_rows_raw)
        per_preset_row_map_by_mode = {
            'start_of_run': start_rows_hydrated,
            'max_progression': max_rows_hydrated,
        }
        variants[preset_name] = {}
        for state_mode in state_mode_options:
            rows_start = per_preset_row_map_by_mode.get('start_of_run') or {}
            rows_max = per_preset_row_map_by_mode.get('max_progression') or {}
            rows = rows_start if state_mode == 'start_of_run' else rows_max
            panels: list[dict[str, object]] = []
            workshop_payload = publish_workshop_reconciliation_payload(
                stats_layout=stats_layout,
                rows_start=rows_start,
                rows_max=rows_max,
                account_state_payload=account_state_payload,
                selected_preset=preset_name,
                surface_specs=_stats_surface_specs,
            )
            panels.append({'panel_id': 'workshop', 'panel_type': 'workshop_stat_table', 'title': 'Workshop', 'payload': workshop_payload})

            derived_rows = [
                _stats_row_payload(
                    row_map=rows,
                    ep_compare=ep_compare,
                    surface_id=spec['surface_id'],
                    label=spec['label'],
                    canonical_row_id=spec['canonical_row_id'],
                )
                for spec in _stats_surface_specs(stats_layout, 'derived_wall_economy_surfaces')
            ]
            panels.append({'panel_id': 'derived', 'panel_type': 'resolved_stat_section', 'title': 'Derived (Wall, economy)', 'payload': {'rows': derived_rows}})

            uw_payload = dict((input_panels_by_id.get('ultimate_weapons') or {}).get('payload') or {})
            if uw_payload:
                uw_rows = list((uw_payload.get('rows') or []))
                panels.append(
                    {
                        'panel_id': 'uw_resolved',
                        'panel_type': 'resolved_uw_section',
                        'title': 'UW',
                        'payload': {'column_headers': uw_payload.get('column_headers') or ['Unlock', 'UW', 'Track', 'Stone Level', 'Stone Value', 'Lab', 'Module', 'Perk', 'Final', 'UW+'], 'rows': uw_rows},
                    }
                )
            else:
                panels.append({'panel_id': 'uw_resolved', 'panel_type': 'gap_notice', 'title': 'UW', 'payload': {'message': 'UW context unavailable.'}})
                upstream_gaps.append(_dashboard_gap('uw_resolved', 'input_dashboard_uw_missing', 'Ultimate weapons panel missing from input_dashboard.json'))

            modules_panel, module_gaps = _build_modules_panel(module_card_payloads or {}, preset_name)
            panels.append({'panel_id': 'modules_context', 'panel_type': 'context_modules', 'title': 'Modules', 'payload': modules_panel.get('payload') or {}})
            upstream_gaps.extend(module_gaps)

            cards_payload = dict((input_panels_by_id.get('cards') or {}).get('payload') or {})
            if cards_payload:
                selected_rows = (cards_payload.get('preset_rows_by_preset') or {}).get(preset_name)
                if selected_rows is None:
                    upstream_gaps.append(_dashboard_gap('cards_context', 'cards_preset_rows_missing', f'Cards rows missing for preset {preset_name}'))
                else:
                    cards_payload['preset_rows'] = selected_rows
                panels.append({'panel_id': 'cards_context', 'panel_type': 'context_cards', 'title': 'Cards', 'payload': cards_payload})
            else:
                panels.append({'panel_id': 'cards_context', 'panel_type': 'gap_notice', 'title': 'Cards', 'payload': {'message': 'Cards context unavailable.'}})
                upstream_gaps.append(_dashboard_gap('cards_context', 'input_dashboard_cards_missing', 'Cards panel missing from input_dashboard.json'))

            bots_payload = dict((input_panels_by_id.get('bots') or {}).get('payload') or {})
            if bots_payload:
                panels.append({'panel_id': 'bots_context', 'panel_type': 'context_track_table', 'title': 'Bots', 'payload': bots_payload})
            else:
                panels.append({'panel_id': 'bots_context', 'panel_type': 'gap_notice', 'title': 'Bots', 'payload': {'message': 'Bots context unavailable.'}})
                upstream_gaps.append(_dashboard_gap('bots_context', 'input_dashboard_bots_missing', 'Bots panel missing from input_dashboard.json'))
            variants[preset_name][state_mode] = panels

    active_panels = (variants.get(selected_preset) or {}).get(selected_state_mode) or []
    panel_map = {str(panel.get('panel_id')): panel for panel in active_panels}
    ordered_panels = [panel_map[panel_id] for panel_id in panel_order if panel_id in panel_map]
    ordered_panels.extend(panel for panel in active_panels if str(panel.get('panel_id')) not in set(panel_order))

    return {
        'artifact': 'stats_dashboard.json',
        'schema_version': 1,
        'dashboard_version': 1,
        'selected_preset': selected_preset,
        'preset_options': preset_options,
        'selected_state_mode': selected_state_mode,
        'state_mode_options': state_mode_options,
        'upstream_gaps': upstream_gaps,
        'panels': ordered_panels,
        'variants': variants,
        'debug_manifest': {
            'source_artifacts': [
                'input_dashboard.json',
                'module_card_payloads.json',
                'run_stats_query_rows_start_of_run.json',
                'run_stats_query_rows_max_progression.json',
                'ep_oracle_compare.json',
            ],
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
