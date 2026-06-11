"""
Streamlit operational console contract freeze (T0).

Dependency policy:
- `streamlit` is optional for non-UI runtime paths.
- This module must remain import-safe when streamlit is not installed.

Import policy:
- Allowed owner surfaces: app.*, input.*, qe.*, simulators.*
- Forbidden direct imports: engine.*, root run_stats, and archived transitional roots.

Artifact policy:
- The console consumes pipeline/QE/input runtime artifacts as a read-only UI.

UI policy:
- Boss Waves is interactive in the console tab UI.

Legacy policy:
- Legacy standalone start/max statbook artifacts are permanently removed.
"""
from __future__ import annotations

import json
import html
import importlib
import importlib.util
import time
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import sys

import pandas as pd
if importlib.util.find_spec('streamlit') is not None:
    st = importlib.import_module('streamlit')
else:  # pragma: no cover - import-safe helper tests
    class _MissingStreamlit:
        def __getattr__(self, name):
            raise ModuleNotFoundError('streamlit is required to run the inspector UI.')

    st = _MissingStreamlit()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.display import (
    INPUT_DASHBOARD_CSS,
    MODULE_CARD_CSS,
    _format_display_number,
    render_cards_inventory_and_preset_html,
    render_gap_notice_html,
    render_grouped_enhancement_table_html,
    render_grouped_modules_html,
    render_grouped_workshop_table_html,
    render_labs_bucket_grid_html,
    render_module_card_html,
    render_overview_metric_strip_html,
    render_resolved_stat_section_html,
    render_simple_bonus_table_html,
    render_simple_metric_panel_html,
    render_stats_uw_section_html,
    render_workshop_stat_table_html,
    render_track_table_html,
    render_uw_track_table_html,
)
from app.inspector_data import (
    compare_rows_frame,
    input_lineage_rows_frame,
    load_artifacts,
    pipeline_stages_frame,
    qe_contributor_rows_frame,
    qe_dependency_nodes_frame,
    qe_plan_coverage_frame,
    qe_query_rows_frame,
    qe_surface_payload,
    qe_trace_steps_frame,
    qe_trace_summary_frame,
    query_rows_dual_state_frame,
    query_rows_surface_detail,
    run_stats_rows_frame,
    RUN_STATS_SECTION_ORDER,
    run_stats_section_name,
    snapshot_label,
    statbook_rows_frame,
    verification_rows_frame,
)
from app.pipeline import (
    BOSS_WAVE_DISSONANCE_RUN_CATEGORIES,
    BOSS_WAVE_DISSONANCE_RUN_LABELS,
    BOSS_WAVE_PERK_POLICY_PRESETS,
    FastCheckpointRequest,
    PipelineRunRequest,
    build_boss_wave_payload,
    build_boss_wave_milestone_matrix,
    build_perk_timeline_preview,
    build_verification_snapshot_set,
    compute_perk_max_effect_displays,
    execute_pipeline,
    load_streamlit_reference_data,
    resolve_fast_checkpoint,
)
from qe.contracts import normalize_surface_id_to_contract

DEFAULT_OUT = ROOT / 'out'
DEFAULT_IDS = ROOT / 'input' / 'imports' / 'ids.csv'


def _friendly_recompute_mode(value: object) -> str:
    text = str(value or '')
    if text == 'not_exposed_by_current_pipeline':
        return 'classic app pipeline'
    return text or 'n/a'


def _friendly_cache_status(value: object) -> str:
    text = str(value or '')
    if text == 'not_attempted':
        return 'not used on this path'
    return text or 'n/a'


def _boss_wave_percent_text(value: object) -> str:
    if value is None or pd.isna(value):
        return '—'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:.2f}".rstrip('0').rstrip('.')
    return f"{text}%"


def _boss_wave_seconds_text(value: object) -> str:
    if value is None or pd.isna(value):
        return '—'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:.2f}".rstrip('0').rstrip('.')
    return text


def _boss_wave_compact_text(value: object) -> str:
    if value is None or pd.isna(value):
        return '—'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = _format_display_number(number)
    return formatted if formatted is not None else str(value)


def _boss_wave_signed_compact_text(value: object) -> str:
    if value is None or pd.isna(value):
        return '—'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == 0:
        return '0'
    sign = '+' if number > 0 else '-'
    formatted = _format_display_number(abs(number))
    return f"{sign}{formatted if formatted is not None else abs(number)}"


def _build_boss_wave_operator_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    def _series(key: str) -> pd.Series:
        return frame.get(key, pd.Series([None] * len(frame), index=frame.index))

    wall_hp = _series('wall_hp')
    return pd.DataFrame(
        {
            'Wave': _series('display_wave'),
            'Atk Wave': _series('attack_wave'),
            'HP Wave': _series('health_wave'),
            'Boss HP': _series('boss_health').map(_boss_wave_compact_text),
            'Boss Atk': _series('boss_attack').map(_boss_wave_compact_text),
            'Tower DPS': _series('tower_damage_per_second').map(_boss_wave_compact_text),
            'Wall HP': wall_hp.map(_boss_wave_compact_text),
            'Wall Regen': _series('wall_regen').map(_boss_wave_compact_text),
            'Regen Gain': _series('wall_regen_gained_hp').map(_boss_wave_compact_text),
            'Damage Reduction': _series('effective_damage_reduction_pct').map(_boss_wave_percent_text),
            'Boss Kill Time': _series('boss_ttk_seconds').map(_boss_wave_seconds_text),
            'Killed Before Contact': _series('boss_killed_before_contact').map(lambda value: 'Yes' if bool(value) else 'No'),
            'PC Dmg %': _series('boss_plasma_cannon_damage_to_boss_pct').map(_boss_wave_percent_text),
            'Orb Dmg %': _series('boss_orb_damage_to_boss_pct').map(_boss_wave_percent_text),
            'Electron Dmg %': _series('boss_electron_damage_to_boss_pct').map(_boss_wave_percent_text),
            'Cont Dmg %': _series('boss_continuous_damage_to_boss_pct').map(_boss_wave_percent_text),
            'Wall Thorns Dmg %': _series('boss_wall_thorns_damage_to_boss_pct').map(_boss_wave_percent_text),
            'Expected Wall Thorns Dmg %': _series('boss_expected_wall_thorns_damage_from_hits_pct').map(_boss_wave_percent_text),
            'Wall Thorns Kill (s)': _series('boss_wall_thorns_contact_kill_seconds').map(_boss_wave_seconds_text),
            'Contact Time': _series('boss_time_to_contact_seconds').map(_boss_wave_seconds_text),
            'Hit Interval (s)': _series('boss_hit_interval_seconds').map(_boss_wave_seconds_text),
            'Boss Hits': _series('boss_hits_taken'),
            'Hits to Player': _series('boss_hits_to_player'),
            'Wall Thorns Hits': _series('boss_wall_thorns_hits'),
            'Damage Taken': _series('boss_total_damage_taken').map(_boss_wave_compact_text),
            'Survival Margin': _series('boss_survival_margin_hp').map(_boss_wave_signed_compact_text),
            'Envelope Regen': _series('contact_envelope_wall_regen_gained_hp').map(_boss_wave_compact_text),
            'Envelope Margin': _series('contact_envelope_survival_margin_hp').map(_boss_wave_signed_compact_text),
            'Envelope Survives': _series('contact_envelope_survives_boss').map(lambda value: 'Yes' if bool(value) else 'No'),
            'Survives': _series('survives_boss').map(lambda value: 'Yes' if bool(value) else 'No'),
        }
    )


def _focus_boss_wave_display_frame(frame: pd.DataFrame, *, max_boss_wave: int, max_rows: int = 12) -> pd.DataFrame:
    if frame.empty or 'Wave' not in frame.columns or len(frame) <= max_rows:
        return frame.copy()
    focused = frame.copy()
    wave_values = pd.to_numeric(focused['Wave'], errors='coerce')
    if max_boss_wave <= 0 or wave_values.isna().all():
        return focused.tail(max_rows).copy()
    distance = (wave_values - float(max_boss_wave)).abs()
    indexes = distance.nsmallest(max_rows).index
    return focused.loc[sorted(indexes)].copy()


def _boss_wave_assumption_text(value: object) -> str:
    if value is None:
        return 'n/a'
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, float):
        return f'{value:g}'
    if isinstance(value, (list, tuple, set)):
        return ', '.join(str(item) for item in value) or 'n/a'
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    text = str(value).strip()
    return text or 'n/a'


def _boss_wave_assumption_frame(
    *,
    diagnostics: dict[str, object],
    contract: dict[str, object],
    payload_diagnostics: dict[str, object],
    primitive_values: dict[str, object],
    boss_damage_source: str,
) -> pd.DataFrame:
    certification = dict(payload_diagnostics.get('model_certification') or {})
    contact_contract = dict((payload_diagnostics.get('contact_time_contract') or {}).get('boss_time_to_contact_seconds') or {})
    replacement_model = dict(payload_diagnostics.get('replacement_model') or {})
    timed_sources = dict(
        ((payload_diagnostics.get('replacement_primitive_semantics_ledger') or {}).get('timed_dr_semantic_contract') or {}).get('sources') or {}
    )
    flame_bot_source = dict(timed_sources.get('flame_bot') or {})
    flame_bot_static_model = dict(flame_bot_source.get('static_hit_chance_model') or {})
    rows = [
        {'group': 'Result', 'assumption': 'Selected model', 'value': diagnostics.get('selected_model'), 'source': 'payload summary'},
        {'group': 'Result', 'assumption': 'Certification status', 'value': certification.get('model_certification_status'), 'source': 'model certification'},
        {'group': 'Result', 'assumption': 'Certified full max-wave model', 'value': certification.get('certified_full_max_wave_model'), 'source': 'model certification'},
        {'group': 'Run', 'assumption': 'Start state', 'value': contract.get('start_state_basis') or diagnostics.get('state_mode'), 'source': 'payload contract'},
        {'group': 'Run', 'assumption': 'Perk timeline', 'value': contract.get('perk_timeline_mode'), 'source': 'payload contract'},
        {'group': 'Run', 'assumption': 'Free upgrades', 'value': contract.get('free_upgrade_mode'), 'source': 'payload contract'},
        {'group': 'Run', 'assumption': 'Enemy skips', 'value': contract.get('enemy_skip_mode'), 'source': 'payload contract'},
        {'group': 'Run', 'assumption': 'Checkpoint cadence', 'value': diagnostics.get('checkpoint_every_bosses'), 'source': 'payload diagnostics'},
        {'group': 'Run', 'assumption': 'Tournament wave source', 'value': diagnostics.get('tournament_wave_source'), 'source': 'payload diagnostics'},
        {'group': 'Contact', 'assumption': 'Boss time to contact', 'value': contact_contract.get('value'), 'source': contact_contract.get('source')},
        {'group': 'Contact', 'assumption': 'Base travel time', 'value': contact_contract.get('base_seconds'), 'source': 'contact-time contract'},
        {'group': 'Contact', 'assumption': 'Chrono Field slow', 'value': contact_contract.get('chrono_field_average_slow_fraction'), 'source': 'contact-time contract'},
        {'group': 'Contact', 'assumption': 'Slow Aura slow', 'value': contact_contract.get('slow_aura_fraction'), 'source': 'contact-time contract'},
        {'group': 'Contact', 'assumption': 'Energy Net hold', 'value': contact_contract.get('energy_net_hold_seconds'), 'source': 'contact-time contract'},
        {'group': 'Damage', 'assumption': 'Boss damage source', 'value': boss_damage_source, 'source': 'replacement primitives'},
        {'group': 'Damage', 'assumption': 'Final boss DPS', 'value': primitive_values.get('boss_damage_per_second') or primitive_values.get('gc_boss_damage_per_second'), 'source': 'replacement primitives'},
        {'group': 'Damage', 'assumption': 'EP eDamage base', 'value': primitive_values.get('edamage_ep'), 'source': 'QE derived::edamage_ep'},
        {'group': 'Damage', 'assumption': 'Chain Lightning DPS', 'value': primitive_values.get('chain_lightning_boss_damage_per_second'), 'source': 'QE CL DPS diagnostic'},
        {'group': 'Damage', 'assumption': 'Boss runtime factor', 'value': primitive_values.get('edamage_boss_runtime_factor'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'Spotlight exposure', 'value': primitive_values.get('edamage_boss_spotlight_exposure_fraction'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'Spotlight factor', 'value': primitive_values.get('edamage_boss_spotlight_factor'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'Om Chip forces Spotlight', 'value': primitive_values.get('edamage_boss_om_chip_forces_spotlight'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'Shockwave hit probability', 'value': primitive_values.get('edamage_boss_shockwave_hit_probability'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'ACP active fraction', 'value': primitive_values.get('edamage_boss_acp_active_fraction'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'ACP factor', 'value': primitive_values.get('edamage_boss_acp_factor'), 'source': 'Boss Waves exposure replacement'},
        {'group': 'Damage', 'assumption': 'EN mastery multiplier', 'value': primitive_values.get('energy_net_mastery_multiplier'), 'source': 'combat primitives'},
        {'group': 'Damage', 'assumption': 'EN boosted seconds', 'value': primitive_values.get('edamage_boss_pre_contact_energy_net_boosted_seconds'), 'source': 'combat primitives'},
        {'group': 'Defense', 'assumption': 'Flame Bot hit chance', 'value': flame_bot_source.get('uptime_fraction'), 'source': flame_bot_source.get('uptime_source')},
        {'group': 'Defense', 'assumption': 'Flame Bot all-or-nothing', 'value': flame_bot_source.get('binary_outcome'), 'source': flame_bot_source.get('primitive_status')},
        {'group': 'Defense', 'assumption': 'Flame Bot hit model', 'value': flame_bot_static_model.get('model') or flame_bot_source.get('primitive_status'), 'source': flame_bot_source.get('primitive_status')},
        {'group': 'Defense', 'assumption': 'Flame Bot spatial coverage', 'value': flame_bot_static_model.get('average_spatial_fraction'), 'source': 'static hit model'},
        {'group': 'Defense', 'assumption': 'Death Defy effective chance', 'value': primitive_values.get('death_defy_effective_chance_pct'), 'source': primitive_values.get('death_defy_model_policy')},
        {'group': 'Model', 'assumption': 'Boss kill sources', 'value': replacement_model.get('boss_kill_sources'), 'source': 'replacement model'},
        {'group': 'Model', 'assumption': 'Contact resolution sources', 'value': replacement_model.get('contact_resolution_sources'), 'source': 'replacement model'},
        {'group': 'Model', 'assumption': 'Survival model', 'value': replacement_model.get('boss_survival_model'), 'source': 'replacement model'},
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in ('value', 'source'):
        frame[column] = frame[column].map(_boss_wave_assumption_text)
    return frame


def _boss_wave_runtime_inputs_frame(diagnostics: dict[str, object]) -> pd.DataFrame:
    runtime_inputs = dict(diagnostics.get('scenario_runtime_inputs') or {})
    if not runtime_inputs:
        return pd.DataFrame(columns=['input', 'value'])
    rows = [
        {'input': key, 'value': _boss_wave_assumption_text(value)}
        for key, value in sorted(runtime_inputs.items())
    ]
    return pd.DataFrame(rows)


def _boss_wave_preset_matrix_frame(matrix_payload: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for matrix_row in matrix_payload.get('rows') or []:
        row = {
            'Tier': matrix_row.get('tier_column') or f"Tier {matrix_row.get('tier')}",
            'Reference': matrix_row.get('reference_wave') or '',
            'Best': matrix_row.get('best_display') or '',
            'Delta': matrix_row.get('delta_vs_reference_wave') if matrix_row.get('delta_vs_reference_wave') is not None else '',
            'Status': matrix_row.get('best_model_certification_status') or '',
            'Limiter': matrix_row.get('terminal_pressure_limiter') or '',
            'Unsupported': ', '.join(str(item) for item in (matrix_row.get('unsupported_terminal_pressures') or ())),
        }
        for candidate in matrix_row.get('candidate_results') or []:
            preset = str(candidate.get('loadout_policy_preset') or '').strip()
            if preset:
                row[preset] = candidate.get('selected_max_wave') or 0
        rows.append(row)
    columns = ['Tier', *BOSS_WAVE_PERK_POLICY_PRESETS, 'Best', 'Reference', 'Delta', 'Status', 'Limiter', 'Unsupported']
    return _arrow_safe_frame(pd.DataFrame(rows), columns=columns)


def _slug_text(value: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in value).strip('_')


def _normalize_module_rarity_family(rarity: object) -> str | None:
    text = str(rarity or '').strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith('ancestral'):
        return 'ancestral'
    if lowered.startswith('mythic'):
        return 'mythic'
    if lowered.startswith('legendary'):
        return 'legendary'
    if lowered.startswith('epic'):
        return 'epic'
    return None


def _rarity_rank(rarity: object) -> int | None:
    family = _normalize_module_rarity_family(rarity)
    order = {
        'common': 0,
        'rare': 1,
        'epic': 2,
        'legendary': 3,
        'mythic': 4,
        'ancestral': 5,
    }
    return order.get(family) if family is not None else None


def _cap_rarity(rarity: object, cap: object) -> str | None:
    rank = _rarity_rank(rarity)
    cap_rank = _rarity_rank(cap)
    labels = {
        0: 'Common',
        1: 'Rare',
        2: 'Epic',
        3: 'Legendary',
        4: 'Mythic',
        5: 'Ancestral',
    }
    if rank is None and cap_rank is None:
        return None
    if rank is None:
        return labels.get(cap_rank)
    if cap_rank is None:
        return labels.get(rank)
    return labels.get(min(rank, cap_rank))


def _module_substat_unlock_count(level: object) -> int:
    try:
        numeric = int(level)
    except (TypeError, ValueError):
        return 0
    thresholds = [1, 41, 81, 101, 141, 161, 201, 241]
    return sum(1 for threshold in thresholds if numeric >= threshold)


def _normalize_module_substat_name(value: object) -> str:
    text = str(value or '').strip()
    aliases = {
        'Defense %': 'Defense',
        'Critical Factor': 'Crit Factor',
        'MultiShot Chance': 'Multishot Chance',
    }
    return aliases.get(text, text)


@lru_cache(maxsize=1)
def _module_substat_lookup() -> dict[tuple[str, str], list[dict[str, object]]]:
    return dict(_streamlit_reference_data(str(DEFAULT_IDS), None).get('module_substat_lookup') or {})


def _infer_module_substat_rarity(slot_type: str, sub: dict, *, role: str, slot_state: dict | None) -> str | None:
    name = _normalize_module_substat_name(sub.get('name'))
    if not name:
        return None
    entries = _module_substat_lookup().get((slot_type.strip().lower(), name))
    if not entries:
        return _cap_rarity(None, slot_state.get('rarity_cap') if slot_state else None) if role == 'assist' else None
    raw_token = str(sub.get('raw_token') or '').strip()
    try:
        raw_value = float(raw_token)
    except ValueError:
        raw_value = None
    matched_rarity = None
    if raw_value is not None:
        for entry in entries:
            candidate = float(entry['value'])
            unit = str(entry['unit'])
            comparisons = [candidate]
            if unit == 'percent':
                comparisons.append(candidate / 100.0)
            if any(abs(raw_value - probe) <= 1e-9 for probe in comparisons):
                matched_rarity = str(entry['rarity'])
                break
    if matched_rarity is None:
        matched_rarity = str(entries[-1]['rarity'])
    if role == 'assist':
        return _cap_rarity(matched_rarity, slot_state.get('rarity_cap') if slot_state else None) or matched_rarity
    return matched_rarity


def _card_key(value: str) -> str:
    return _slug_text(value).upper()


def _uw_slug(value: str) -> str:
    return _slug_text(value)


@lru_cache(maxsize=8)
def _streamlit_reference_data(ids_path: str | None = None, manual_inputs_path: str | None = None) -> dict[str, object]:
    ids = Path(ids_path) if ids_path else DEFAULT_IDS
    manual = None if not manual_inputs_path else Path(manual_inputs_path)
    return load_streamlit_reference_data(ids_path=ids, manual_inputs_path=manual)


def _perk_entity_map() -> dict[str, dict]:
    return dict(_streamlit_reference_data(str(DEFAULT_IDS), None).get('perk_entity_map') or {})


def _card_effect_map() -> dict[str, str]:
    return dict(_streamlit_reference_data(str(DEFAULT_IDS), None).get('card_effects') or {})


def _card_value_map() -> dict[tuple[str, int], str]:
    return dict(_streamlit_reference_data(str(DEFAULT_IDS), None).get('card_values') or {})


def _manual_banned_perks(ids_path: Path, manual_inputs_path: Path | None) -> set[str]:
    return set(
        _streamlit_reference_data(str(ids_path), str(manual_inputs_path) if manual_inputs_path else None).get('manual_banned_perk_ids')
        or set()
    )


def _rarity_color(rarity: object) -> str:
    text = str(rarity or '').strip().lower()
    if text.startswith('ancestral'):
        return 'rgba(116, 196, 118, 0.24)'
    if text.startswith('mythic'):
        return 'rgba(220, 38, 38, 0.22)'
    if text.startswith('legendary'):
        return 'rgba(255, 188, 88, 0.22)'
    if text.startswith('epic'):
        return 'rgba(139, 92, 246, 0.2)'
    if text.startswith('rare'):
        return 'rgba(90, 170, 255, 0.18)'
    if text.startswith('common'):
        return 'rgba(180, 180, 180, 0.14)'
    return 'rgba(255, 255, 255, 0.04)'


def _format_scaled_value(value: float | None, suffix: str) -> str:
    if value is None:
        return ''
    if suffix == '%':
        return f"+{value:g}%"
    if suffix == 'x':
        return f"+{value:g}x"
    if suffix == 's':
        return f"{value:g}s"
    if suffix == 'm':
        return f"{value:g}m"
    return f"{value:g}"


def _parse_display_with_suffix(display: object) -> tuple[float | None, str]:
    text = str(display or '').strip()
    if not text:
        return None, ''
    cleaned = text.replace('+', '').replace('?', '').strip()
    if cleaned.lower().endswith('x'):
        try:
            return float(cleaned[:-1]), 'x'
        except ValueError:
            return None, 'x'
    if cleaned.endswith('%'):
        try:
            return float(cleaned[:-1]), '%'
        except ValueError:
            return None, '%'
    if cleaned.lower().endswith('s'):
        try:
            return float(cleaned[:-1]), 's'
        except ValueError:
            return None, 's'
    if cleaned.lower().endswith('m'):
        try:
            return float(cleaned[:-1]), 'm'
        except ValueError:
            return None, 'm'
    try:
        return float(cleaned), ''
    except ValueError:
        return None, ''


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_qe_perk_value(value: object, value_type: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    numeric = _coerce_float(value)
    if numeric is None:
        return str(value)
    kind = str(value_type or '').strip().lower()
    if kind == 'multiplier':
        return f"x{numeric:g}"
    if kind in {'pct', 'additive_percent', 'percent', 'percentage_points_add'}:
        return f"+{numeric:g}%"
    if kind == 'seconds_add':
        return f"+{numeric:g}s"
    if kind in {'count_add', 'flat'} and numeric >= 0:
        return f"+{numeric:g}"
    return f"{numeric:g}"


def _perk_rows_from_qe(stat_inputs_payload: object, *, selected_preset: str) -> dict[str, list[dict]]:
    if not isinstance(stat_inputs_payload, list):
        return {}
    perk_entities = _perk_entity_map()
    perk_rows: dict[str, list[dict]] = {}
    for row in stat_inputs_payload:
        if not isinstance(row, dict):
            continue
        if str(row.get('source_family') or '').strip() != 'perk':
            continue
        if row.get('active') is False:
            continue
        preset_name = str(row.get('preset_name') or '').strip()
        if preset_name and preset_name != selected_preset:
            continue
        perk_name = str(row.get('source_name') or '').strip()
        if not perk_name:
            contributor_id = str(row.get('contributor_id') or '').strip()
            perk_id = contributor_id.split('::')[1] if contributor_id.startswith('perk::') and '::' in contributor_id else ''
            perk_name = str((perk_entities.get(perk_id) or {}).get('perk_name') or perk_id).strip()
        if not perk_name:
            continue
        perk_rows.setdefault(str(perk_name), []).append(
            {
                'value': row.get('value'),
                'value_type': row.get('value_type'),
            }
        )
    return perk_rows


def _perk_display_preset(account_state: dict, *, selected_preset: str) -> str | None:
    if selected_preset == 'Tourney':
        return None
    perk_presets = account_state.get('perk_presets') or {}
    if selected_preset in perk_presets:
        return selected_preset
    return str(account_state.get('active_perk_preset') or selected_preset)


def _perk_lab_bonus_summary(stat_inputs_payload: object) -> tuple[float | None, float | None]:
    if not isinstance(stat_inputs_payload, list):
        return None, None
    standard_bonus = None
    tradeoff_bonus = None
    for row in stat_inputs_payload:
        if not isinstance(row, dict):
            continue
        if str(row.get('source_family') or '').strip() != 'lab':
            continue
        if row.get('active') is False:
            continue
        destination_id = str(row.get('destination_id') or '').strip()
        if destination_id == 'perk.standard_perks_bonus_pct':
            standard_bonus = _coerce_float(row.get('value'))
        elif destination_id == 'perk.tradeoff_bonus_pct':
            tradeoff_bonus = _coerce_float(row.get('value'))
    return standard_bonus, tradeoff_bonus


def _resolved_statbook_row_map(resolved_statbook_payload: object) -> dict[str, dict]:
    if not isinstance(resolved_statbook_payload, dict):
        return {}
    row_map: dict[str, dict] = {}
    if isinstance(resolved_statbook_payload.get('rows'), dict):
        for raw_surface_id, payload in (resolved_statbook_payload.get('rows') or {}).items():
            row_map[normalize_surface_id_to_contract(raw_surface_id)] = dict(payload or {})
        return row_map
    for preset_payload in resolved_statbook_payload.values():
        if not isinstance(preset_payload, dict):
            continue
        for raw_surface_id, payload in (preset_payload.get('rows') or {}).items():
            row_map[normalize_surface_id_to_contract(raw_surface_id)] = dict(payload or {})
    return row_map


def _stringify_for_display(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        return f'{value:g}'
    return str(value)


def _arrow_safe_frame(frame: pd.DataFrame, *, columns: tuple[str, ...] = ('value',)) -> pd.DataFrame:
    safe = frame.copy()
    for column in columns:
        if column not in safe.columns:
            continue
        sample_types = {type(item) for item in safe[column] if item is not None}
        if len(sample_types) > 1:
            safe[column] = safe[column].map(_stringify_for_display)
    return safe


def _init_state() -> None:
    st.session_state.setdefault('snapshot_dirs', {DEFAULT_OUT.name: str(DEFAULT_OUT)})
    st.session_state.setdefault('active_out_dir', str(DEFAULT_OUT))
    st.session_state.setdefault('fast_checkpoint_result', None)


def _register_snapshot(out_dir: Path, *, preset: str, state_mode: str, perk_state: str) -> None:
    label = snapshot_label(preset=preset, state_mode=state_mode, perk_state=perk_state, out_dir=out_dir)
    snapshot_dirs = st.session_state['snapshot_dirs']
    for existing_label, existing_path in list(snapshot_dirs.items()):
        if Path(existing_path) == out_dir and existing_label != label:
            del snapshot_dirs[existing_label]
    st.session_state['snapshot_dirs'][label] = str(out_dir)
    st.session_state['active_out_dir'] = str(out_dir)


def _render_action_failure(action_name: str, exc: Exception) -> None:
    st.error(f'{action_name} failed: {exc}')


def _run_request(request: PipelineRunRequest, *, action_name: str = 'Run snapshot') -> bool:
    try:
        result = execute_pipeline(request)
    except Exception as exc:
        _render_action_failure(action_name, exc)
        return False
    _register_snapshot(result.out_dir, preset=request.preset, state_mode=request.state_mode, perk_state=request.perk_state)
    return True


def _run_default_verification_set(base_request: PipelineRunRequest) -> bool:
    try:
        results = build_verification_snapshot_set(base_request)
    except Exception as exc:
        _render_action_failure('Build default verification set', exc)
        return False
    for result in results:
        _register_snapshot(
            result.out_dir,
            preset=result.request.preset,
            state_mode=result.request.state_mode,
            perk_state=result.request.perk_state,
        )
    return True


def _artifact_path(value: object, *, default: Path) -> Path:
    if value is None:
        return default
    raw = str(value).strip()
    if not raw or raw.lower() in {'none', 'null'}:
        return default
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _request_from_active_snapshot(active_out_dir: Path, active_artifacts: dict[str, object]) -> PipelineRunRequest:
    diagnostics = dict(active_artifacts.get('diagnostics.json') or {})
    trace_request = dict((active_artifacts.get('pipeline_trace.json') or {}).get('request') or {})
    perk_support = dict(diagnostics.get('perk_support') or {})
    return PipelineRunRequest(
        ids=_artifact_path(trace_request.get('ids'), default=DEFAULT_IDS),
        out=active_out_dir,
        preset=str(diagnostics.get('default_preset') or trace_request.get('preset') or 'Farming'),
        state_mode=str(diagnostics.get('state_mode') or trace_request.get('state_mode') or 'start_of_run'),
        manual_inputs=(
            None
            if trace_request.get('manual_inputs') in {None, '', 'None', 'none'}
            else _artifact_path(trace_request.get('manual_inputs'), default=ROOT / 'input' / ('manual_inputs' + '.yaml'))
        ),
        runtime_state_overlay=(
            str(trace_request.get('runtime_state_overlay'))
            if trace_request.get('runtime_state_overlay') not in {None, '', 'None', 'none'}
            else None
        ),
        perk_mode=str(trace_request.get('perk_mode') or 'max_progression_policy'),
        include_slow_audits=bool(trace_request.get('include_slow_audits') or False),
        perk_state=str(perk_support.get('perk_state') or trace_request.get('perk_state') or 'auto'),
        perk_policy_preset=(
            str(perk_support.get('perk_policy_preset') or trace_request.get('perk_policy_preset'))
            if (perk_support.get('perk_policy_preset') or trace_request.get('perk_policy_preset'))
            else None
        ),
    )


def _snapshot_sidebar() -> None:
    st.sidebar.header('Snapshots')
    snapshot_labels = list(st.session_state['snapshot_dirs'].keys())
    active_label = next(
        (label for label, path in st.session_state['snapshot_dirs'].items() if path == st.session_state['active_out_dir']),
        snapshot_labels[0],
    )
    selected_label = st.sidebar.selectbox(
        'Active snapshot',
        options=snapshot_labels,
        index=max(0, snapshot_labels.index(active_label)),
    )
    st.session_state['active_out_dir'] = st.session_state['snapshot_dirs'][selected_label]
    st.sidebar.caption('Tabs use this snapshot as their artifact source. New runs and verification snapshots are launched from Pipeline and Checks.')


def _render_pipeline_run_controls(default_request: PipelineRunRequest) -> None:
    with st.expander('Run a new snapshot', expanded=False):
        path_cols = st.columns(4)
        ids_path = Path(path_cols[0].text_input('Run IDS path', value=str(default_request.ids), key='pipeline_ids_path'))
        out_dir = Path(path_cols[1].text_input('Run output dir', value=str(default_request.out), key='pipeline_out_dir'))
        manual_inputs_raw = path_cols[2].text_input(
            'Run manual inputs override',
            value='' if default_request.manual_inputs is None else str(default_request.manual_inputs),
            key='pipeline_manual_inputs',
        )
        manual_inputs = Path(manual_inputs_raw) if manual_inputs_raw.strip() else None
        runtime_state_overlay_raw = path_cols[3].text_input(
            'Run runtime overlay',
            value='' if default_request.runtime_state_overlay is None else str(default_request.runtime_state_overlay),
            key='pipeline_runtime_state_overlay',
        )
        runtime_state_overlay = runtime_state_overlay_raw.strip() or None
        config_cols = st.columns(4)
        preset_options = ['Farming', 'Tourney', 'Milestone']
        preset = config_cols[0].selectbox(
            'Run loadout',
            options=preset_options,
            index=preset_options.index(default_request.preset) if default_request.preset in preset_options else 0,
            key='pipeline_loadout',
        )
        state_options = ['start_of_run', 'max_progression']
        state_mode = config_cols[1].selectbox(
            'State mode',
            options=state_options,
            index=0,
            key='pipeline_state_mode',
        )
        perk_policy_preset = config_cols[2].selectbox(
            'Run perk plan',
            options=list(BOSS_WAVE_PERK_POLICY_PRESETS),
            index=(
                list(BOSS_WAVE_PERK_POLICY_PRESETS).index(default_request.perk_policy_preset)
                if default_request.perk_policy_preset in BOSS_WAVE_PERK_POLICY_PRESETS
                else 1
            ),
            key='pipeline_perk_plan',
        )
        include_slow_audits = config_cols[3].checkbox(
            'Run slow audits',
            value=bool(default_request.include_slow_audits),
            key='pipeline_include_slow_audits',
        )
        if st.button('Run snapshot', width='stretch'):
            did_run = _run_request(
                PipelineRunRequest(
                    ids=ids_path,
                    out=out_dir,
                    preset=preset,
                    state_mode=state_mode,
                    manual_inputs=manual_inputs,
                    runtime_state_overlay=runtime_state_overlay,
                    perk_mode='max_progression_policy',
                    include_slow_audits=include_slow_audits,
                    perk_state='auto',
                    perk_policy_preset=perk_policy_preset,
                ),
                action_name='Run snapshot',
            )
            if did_run:
                st.rerun()


def _render_verification_snapshot_controls(default_request: PipelineRunRequest) -> None:
    with st.expander('Build verification snapshots', expanded=False):
        path_cols = st.columns(4)
        ids_path = Path(path_cols[0].text_input('Verification IDS path', value=str(default_request.ids), key='verification_ids_path'))
        out_dir = Path(path_cols[1].text_input('Verification output dir', value=str(default_request.out), key='verification_out_dir'))
        manual_inputs_raw = path_cols[2].text_input(
            'Verification manual inputs override',
            value='' if default_request.manual_inputs is None else str(default_request.manual_inputs),
            key='verification_manual_inputs',
        )
        manual_inputs = Path(manual_inputs_raw) if manual_inputs_raw.strip() else None
        runtime_state_overlay_raw = path_cols[3].text_input(
            'Verification runtime overlay',
            value='' if default_request.runtime_state_overlay is None else str(default_request.runtime_state_overlay),
            key='verification_runtime_state_overlay',
        )
        runtime_state_overlay = runtime_state_overlay_raw.strip() or None
        config_cols = st.columns(2)
        perk_policy_preset = config_cols[0].selectbox(
            'Verification perk plan',
            options=list(BOSS_WAVE_PERK_POLICY_PRESETS),
            index=(
                list(BOSS_WAVE_PERK_POLICY_PRESETS).index(default_request.perk_policy_preset)
                if default_request.perk_policy_preset in BOSS_WAVE_PERK_POLICY_PRESETS
                else 1
            ),
            key='verification_perk_plan',
        )
        include_slow_audits = config_cols[1].checkbox(
            'Verification slow audits',
            value=bool(default_request.include_slow_audits),
            key='verification_include_slow_audits',
        )
        if st.button('Build default verification set', width='stretch'):
            did_build = _run_default_verification_set(
                PipelineRunRequest(
                    ids=ids_path,
                    out=out_dir,
                    preset=default_request.preset,
                    state_mode=default_request.state_mode,
                    manual_inputs=manual_inputs,
                    runtime_state_overlay=runtime_state_overlay,
                    perk_mode='max_progression_policy',
                    include_slow_audits=include_slow_audits,
                    perk_state='auto',
                    perk_policy_preset=perk_policy_preset,
                )
            )
            if did_build:
                st.rerun()


def _render_pipeline(trace_payload: dict, diagnostics: dict, request: PipelineRunRequest) -> None:
    _render_pipeline_run_controls(request)
    execution = trace_payload.get('execution_path') or {}
    cols = st.columns(6)
    cols[0].metric('Recompute mode', _friendly_recompute_mode(execution.get('recompute_mode')))
    cols[1].metric('Cache status', _friendly_cache_status(execution.get('cache_status')))
    cols[2].metric('Fallback', 'Yes' if execution.get('fallback_required') else 'No')
    cols[3].metric('Bundle', str(execution.get('bundle_used') or 'n/a'))
    cols[4].metric('Family', str(execution.get('family_id') or 'n/a'))
    cols[5].metric('Elapsed ms', execution.get('total_elapsed_ms') or 'n/a')

    if execution.get('recompute_mode') == 'not_exposed_by_current_pipeline':
        st.info(
            'This run came through the current top-level app pipeline, which does not yet emit full incremental/cache branch diagnostics. '
            'You are still seeing the real artifacts and outputs, but the cache/bundle branch fields are structural placeholders on this path.'
        )

    with st.expander('Pipeline evidence', expanded=False):
        execution_tab, stages_tab, cache_tab, runtime_tab, advanced_tab = st.tabs(
            ['Execution', 'Stages', 'Cache', 'Runtime', 'Advanced']
        )
        with execution_tab:
            st.json(execution)
        with stages_tab:
            stage_df = pipeline_stages_frame(trace_payload)
            if stage_df.empty:
                st.info('No pipeline stages were published for this snapshot.')
            else:
                st.dataframe(stage_df, width='stretch', hide_index=True)
                for stage in trace_payload.get('stages') or []:
                    title = f"{stage.get('title', stage.get('stage_id'))} - {stage.get('owner_module', '')}"
                    with st.expander(title):
                        st.write(f"`{stage.get('entry_function', '')}`")
                        st.json(stage)
        with cache_tab:
            st.json(
                {
                    'cache_fingerprint': execution.get('cache_fingerprint'),
                    'cache_validation': execution.get('cache_validation'),
                    'mutated_workshop_keys': ((execution.get('incremental_plan') or {}).get('mutated_source_nodes')),
                    'reused_cached_reference_statbook': execution.get('cache_status') == 'hit',
                    'incremental_plan': execution.get('incremental_plan') or {},
                }
            )
        with runtime_tab:
            st.json(
                {
                    'runtime_consumers': execution.get('runtime_consumers') or [],
                    'runtime_publication': execution.get('runtime_publication'),
                }
            )
        with advanced_tab:
            st.caption('Active snapshot request defaults')
            st.code(json.dumps(request.__dict__, indent=2, default=str))
            st.code(
                '\n'.join(
                    [
                        'simulators.progression.ProgressionRecalcBridge.recompute',
                        'simulators.incremental_recalc_runtime.IncrementalRecalcRuntime.plan_consumer_bundle',
                        'simulators.incremental_cache_validator.IncrementalCacheValidator.validate',
                        'simulators.incremental_overlay_publisher.IncrementalOverlayPublisher.publish',
                        'simulators.incremental_parity_harness.IncrementalParityHarness.compare',
                    ]
                )
            )
            st.json(diagnostics.get('pipeline_incremental_summary') or {})


def _render_cards_matrix(account_state: dict, *, selected_preset: str) -> None:
    card_presets = account_state.get('card_presets') or {}
    if not isinstance(card_presets, dict) or not card_presets:
        return
    st.subheader('Cards')
    st.caption(f"Unlocked slots: {account_state.get('card_slots_unlocked') or 'unknown'}")
    card_effects = _card_effect_map()
    card_values = _card_value_map()
    inventory = account_state.get('cards_inventory') or {}
    preset_names = list(card_presets.keys())
    all_cards = sorted(set(inventory.keys()) | {card for cards in card_presets.values() for card in (cards or [])})
    rows = []
    for card in all_cards:
        card_info = inventory.get(card) or {}
        effect_name = card_effects.get(_card_key(card), '')
        row = {
            'card': card,
            'effect': effect_name,
            'value': card_values.get((_card_key(card), int(card_info.get('level') or 0)), ''),
            'level': card_info.get('level'),
            'mastery': (
                str(card_info.get('mastery_lab_level'))
                if card_info.get('mastery_unlocked')
                else ''
            ),
        }
        for preset_name in preset_names:
            header = f'{preset_name} (selected)' if preset_name == selected_preset else preset_name
            row[header] = 'used' if card in (card_presets.get(preset_name) or []) else ''
        rows.append(row)
    frame = pd.DataFrame(rows)
    selected_header = f'{selected_preset} (selected)'

    def _style_selected(row: pd.Series):
        active = row.get(selected_header) == 'used'
        return ['background-color: rgba(255, 214, 102, 0.2)' if active else '' for _ in row]

    st.dataframe(frame.style.apply(_style_selected, axis=1), width='stretch', hide_index=True)


def _render_modules_table(active_artifacts, *, selected_preset: str) -> None:
    payload_root = active_artifacts.get('module_card_payloads.json', {}) or {}
    preset_payload = ((payload_root.get('presets') or {}).get(selected_preset) or {})
    if not preset_payload:
        st.info('module_card_payloads.json not present for this snapshot')
        return
    st.subheader('Modules Equipped')
    st.markdown(MODULE_CARD_CSS, unsafe_allow_html=True)
    slot_columns = st.columns(4)
    for idx, slot in enumerate(['cannon', 'armor', 'generator', 'core']):
        with slot_columns[idx]:
            st.markdown(f'**{slot.title()}**')
            slot_payload = preset_payload.get(slot) or {}
            for role in ['primary', 'assist']:
                st.caption(role.title())
                card_payload = slot_payload.get(role)
                if not card_payload:
                    st.write('No module equipped')
                    continue
                st.markdown(render_module_card_html(card_payload), unsafe_allow_html=True)


def _render_perks_table(
    account_state: dict,
    *,
    selected_preset: str,
    stat_inputs_payload: object,
    ids_path: Path,
    manual_inputs_path: Path | None,
) -> None:
    st.subheader('Perks')
    perk_rows = _perk_entity_map()
    display_preset = _perk_display_preset(account_state, selected_preset=selected_preset)
    qe_perk_rows = (
        _perk_rows_from_qe(stat_inputs_payload, selected_preset=display_preset)
        if display_preset is not None
        else {}
    )
    standard_bonus, tradeoff_bonus = _perk_lab_bonus_summary(stat_inputs_payload)
    cols = st.columns(2)
    cols[0].metric('Standard Perk Bonus lab', f'{standard_bonus:g}%' if standard_bonus is not None else 'n/a')
    cols[1].metric('Trade-off Perk Bonus lab', f'{tradeoff_bonus:g}%' if tradeoff_bonus is not None else 'n/a')
    selections = {
        row.get('perk_id'): int(row.get('picks') or 0)
        for row in ((account_state.get('perk_presets') or {}).get(display_preset or '') or [])
    }
    banned_ids = _manual_banned_perks(ids_path, manual_inputs_path)
    rows = []
    for perk_id, meta in perk_rows.items():
        picks = selections.get(perk_id, 0)
        banned = perk_id in banned_ids
        if picks <= 0 and not banned:
            continue
        active_values = [
            _format_qe_perk_value(row.get('value'), row.get('value_type'))
            for row in qe_perk_rows.get(meta.get('perk_name') or perk_id, [])
            if _format_qe_perk_value(row.get('value'), row.get('value_type'))
        ]
        max_values = []
        for scaled, value_type in compute_perk_max_effect_displays(
            perk_id=perk_id,
            standard_bonus_pct=standard_bonus,
            tradeoff_bonus_pct=tradeoff_bonus,
        ):
            formatted = _format_qe_perk_value(scaled, value_type)
            if formatted:
                max_values.append(formatted)
        rows.append(
            {
                'perk': meta.get('perk_name') or perk_id,
                'category': meta.get('category'),
                'value': ' | '.join(active_values),
                'picks': picks if picks > 0 else '',
                'banned': 'banned' if banned else '',
                'max value': ' | '.join(max_values),
            }
        )
    st.dataframe(
        _arrow_safe_frame(pd.DataFrame(rows), columns=('value', 'picks', 'max value')),
        width='stretch',
        hide_index=True,
    )


def _render_perk_policy_tab(request: PipelineRunRequest) -> None:
    st.subheader('Perk Timeline Policy')
    columns = st.columns(len(BOSS_WAVE_PERK_POLICY_PRESETS))
    previews: dict[str, dict[str, object]] = {}
    for column, policy_preset in zip(columns, BOSS_WAVE_PERK_POLICY_PRESETS):
        policy_request = replace(request, perk_policy_preset=policy_preset)
        with column:
            st.markdown(f"**{policy_preset}**")
            try:
                preview = build_perk_timeline_preview(policy_request)
            except Exception as exc:
                st.error(f'Perk plan preview failed: {exc}')
                continue
            previews[policy_preset] = preview
            resolved = dict(preview.get('resolved_policy') or {})
            validation = dict(preview.get('validation') or {})
            diagnostics = dict(preview.get('diagnostics') or {})
            if validation.get('errors'):
                st.error('Perk plan is invalid: ' + '; '.join(str(item) for item in validation.get('errors') or []))
            for warning in validation.get('warnings') or []:
                st.warning(str(warning))
            metric_cols = st.columns(2)
            metric_cols[0].metric('Generated', int(diagnostics.get('generated_rows') or 0))
            metric_cols[1].metric('Final wave', int(diagnostics.get('final_wave') or 0))

            priority_rows = [
                {'rank': index, 'perk': perk_name}
                for index, perk_name in enumerate(resolved.get('priority_order') or (), start=1)
            ]
            st.caption('Priority order')
            st.dataframe(pd.DataFrame(priority_rows), width='stretch', hide_index=True)

            banned_rows = [
                {'slot': index, 'perk': perk_name}
                for index, perk_name in enumerate(resolved.get('banned_perks') or (), start=1)
            ]
            st.caption('Bans')
            st.dataframe(pd.DataFrame(banned_rows), width='stretch', hide_index=True)

            timeline_rows = [
                {
                    'wave': row.get('wave'),
                    'perk': row.get('perk_taken'),
                    'qty': row.get('quantity'),
                }
                for row in (preview.get('timeline') or ())
            ]
            st.caption('Taken by wave')
            st.dataframe(pd.DataFrame(timeline_rows), width='stretch', hide_index=True)

    with st.expander('Resolved perk policy diagnostics', expanded=False):
        st.json(
            {
                policy_preset: {
                    'resolved_policy': preview.get('resolved_policy'),
                    'validation': preview.get('validation'),
                    'diagnostics': preview.get('diagnostics'),
                    'generator_owner': preview.get('generator_owner'),
                }
                for policy_preset, preview in previews.items()
            }
        )
    return None


def _uw_track_stat_suffix(track_name: object) -> tuple[str, ...]:
    text = str(track_name or '').strip().lower()
    mapping = {
        'damage': ('damage',),
        'quantity': ('quantity', 'count'),
        'chance': ('chance',),
        'cooldown': ('cooldown',),
        'duration': ('duration',),
        'multiplier': ('multiplier', 'bonus'),
        'bonus': ('bonus', 'multiplier'),
        'angle': ('angle',),
        'size': ('size',),
        'speed reduction': ('speed_reduction',),
    }
    return mapping.get(text, (text.replace(' ', '_'),))


def _uw_track_surface_tokens(track_name: object) -> tuple[str, ...]:
    text = str(track_name or '').strip().lower()
    mapping = {
        'damage': ('damage',),
        'quantity': ('quantity', 'count'),
        'chance': ('chance',),
        'cooldown': ('cooldown',),
        'duration': ('duration',),
        'multiplier': ('multiplier', 'bonus'),
        'bonus': ('bonus', 'multiplier'),
        'angle': ('angle',),
        'size': ('size',),
        'speed reduction': ('speed_reduction',),
    }
    return mapping.get(text, (text.replace(' ', '_'),))


def _module_effects_for_uw_track(
    selected_modules: dict,
    modules_inventory: dict,
    *,
    uw_name: str,
    track_name: object,
) -> str:
    suffixes = _uw_track_stat_suffix(track_name)
    matches: list[str] = []
    for selection in selected_modules.values():
        for role in ['primary', 'assist']:
            module_name = (selection or {}).get(role)
            if not module_name:
                continue
            module = modules_inventory.get(module_name) or {}
            for sub in (module.get('substats') or []):
                sub_name = str(sub.get('name') or '')
                sub_slug = _slug_text(sub_name)
                if _slug_text(uw_name) not in sub_slug:
                    continue
                if any(token in sub_slug for token in suffixes):
                    value = sub.get('value')
                    if value:
                        matches.append(str(value).strip())
    return '; '.join(matches)


def _max_progression_value_for_uw_track(max_progression_rows: dict[str, dict], *, uw_name: str, track_name: object) -> object:
    uw_slug = _uw_slug(uw_name)
    suffixes = _uw_track_surface_tokens(track_name)
    for surface_id, payload in max_progression_rows.items():
        if f'state::uw.{uw_slug}.' not in surface_id:
            continue
        if any(token in surface_id for token in suffixes):
            return payload.get('display_value') or payload.get('final_value')
    return None


def _lookup_statbook_row(statbook_payload: dict, *, preset: str, surface_id: str) -> dict:
    preset_payload = statbook_payload.get(preset) or {}
    for raw_surface_id, payload in ((preset_payload.get('rows') or {}).items()):
        if normalize_surface_id_to_contract(raw_surface_id) == surface_id:
            return dict(payload)
    return {}


def _perk_effects_for_surface(statbook_payload: dict, *, preset: str, surface_id: str) -> str:
    row_payload = _lookup_statbook_row(statbook_payload, preset=preset, surface_id=surface_id)
    values = []
    for contributor in (row_payload.get('contributors') or []):
        if str(contributor.get('source_class') or '').strip() != 'perk_effect':
            continue
        text = str(contributor.get('display_value') or contributor.get('value') or '').strip()
        if text:
            values.append(text)
    return '; '.join(values)


def _render_uw_groups(
    account_state: dict,
    *,
    selected_preset: str,
    max_progression_rows: dict[str, dict],
    statbook_max_progression: dict,
    resolved_statbook_rows: dict[str, dict],
) -> None:
    st.subheader('Ultimate Weapons')
    ultimate_weapons = account_state.get('ultimate_weapons') or {}
    uw_tracks = account_state.get('uw_tracks') or {}
    uw_plus_tracks = account_state.get('uw_plus_tracks') or {}
    labs = account_state.get('labs') or {}
    module_presets = account_state.get('module_presets') or {}
    modules_inventory = account_state.get('modules_inventory') or {}
    unlocked = [
        name
        for name, payload in ultimate_weapons.items()
        if str((payload or {}).get('unlocked') or '').strip().lower() == 'true'
    ]
    for uw_name in unlocked:
        with st.expander(uw_name, expanded=False):
            selected_modules = module_presets.get(selected_preset) or {}
            track_rows = []
            for row in (uw_tracks.get(uw_name) or []):
                track_name = row.get('track_name')
                lab_key = f'{uw_name} {track_name}'
                surface_id = None
                uw_slug = _uw_slug(uw_name)
                suffixes = _uw_track_surface_tokens(track_name)
                for candidate_surface_id in max_progression_rows:
                    if f'state::uw.{uw_slug}.' not in candidate_surface_id:
                        continue
                    if any(token in candidate_surface_id for token in suffixes):
                        surface_id = candidate_surface_id
                        break
                track_rows.append(
                    {
                        'track': row.get('track_name'),
                        'stone level': row.get('level'),
                        'stone value': row.get('resolved_value'),
                        'lab value': labs.get(lab_key),
                        'module effect': _module_effects_for_uw_track(
                            selected_modules,
                            modules_inventory,
                            uw_name=uw_name,
                            track_name=track_name,
                        ),
                        'perk': _perk_effects_for_surface(
                            statbook_max_progression,
                            preset=selected_preset,
                            surface_id=surface_id or '',
                        ) if surface_id else '',
                        'final val': (
                            (resolved_statbook_rows.get(surface_id or '', {}) or {}).get('display_value')
                            or _max_progression_value_for_uw_track(
                                max_progression_rows,
                                uw_name=uw_name,
                                track_name=track_name,
                            )
                        ),
                    }
                )
            st.dataframe(pd.DataFrame(track_rows), width='stretch', hide_index=True)
            plus_rows = [
                row for key, row in uw_plus_tracks.items() if key.startswith(f'{uw_name}::')
            ]
            if plus_rows:
                st.dataframe(pd.DataFrame(plus_rows), width='stretch', hide_index=True)


def _render_loadout_panel(
    active_artifacts,
    *,
    preset: str,
    max_progression_rows: dict[str, dict],
    ids_path: Path,
    manual_inputs_path: Path | None,
) -> None:
    account_state = active_artifacts.get('account_state.json', {}) or {}
    if not account_state:
        return
    resolved_statbook = active_artifacts.get('statbook_publishable.json') or active_artifacts.get('statbook.json') or {}
    _render_cards_matrix(account_state, selected_preset=preset)
    _render_modules_table(active_artifacts, selected_preset=preset)
    _render_perks_table(
        account_state,
        selected_preset=preset,
        stat_inputs_payload=active_artifacts.get('stat_inputs.json', []),
        ids_path=ids_path,
        manual_inputs_path=manual_inputs_path,
    )
    _render_uw_groups(
        account_state,
        selected_preset=preset,
        max_progression_rows=max_progression_rows,
        statbook_max_progression=active_artifacts.get('run_stats_query_rows_max_progression.json', {}),
        resolved_statbook_rows=_resolved_statbook_row_map(resolved_statbook),
    )


def _render_sectioned_run_stats_table(frame: pd.DataFrame, *, show_raw_ids: bool) -> None:
    frame = frame.copy()
    frame['section'] = frame['surface_id'].map(run_stats_section_name)
    for section_name in RUN_STATS_SECTION_ORDER:
        section_df = frame[frame['section'] == section_name].copy()
        if section_df.empty:
            continue
        st.subheader(section_name)
        table_columns = [
            'display_label',
            'surface_id',
            'start_of_run_display',
            'start_of_run_value',
            'start_of_run_status',
            'max_progression_display',
            'max_progression_value',
            'max_progression_status',
            'changed_in_max_progression',
            'ep display',
            'ep value',
            'ep delta vs max',
            'ep preset',
            'ep perks',
            'ep status',
        ]
        if show_raw_ids:
            table_columns.insert(2, 'raw_surface_id')
        st.dataframe(
            _arrow_safe_frame(
                section_df[table_columns],
                columns=('start_of_run_value', 'max_progression_value', 'ep value', 'ep delta vs max'),
            ),
            width='stretch',
            hide_index=True,
        )


def _max_progression_lookup(frame: pd.DataFrame) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for row in frame.itertuples(index=False):
        rows[str(row.surface_id)] = {
            'display_value': getattr(row, 'max_progression_display', None),
            'final_value': getattr(row, 'max_progression_value', None),
        }
    return rows


def _render_qe(active_artifacts, request: PipelineRunRequest) -> None:
    st.subheader('QE Surface Lineage Explorer')
    state_mode = st.selectbox('QE state mode', options=['start_of_run', 'max_progression'], index=0 if request.state_mode == 'start_of_run' else 1)
    query_rows_name = f'run_stats_query_rows_{state_mode}.json'
    query_plan_name = f'run_stats_query_plan_{state_mode}.json'
    query_rows_payload = active_artifacts.get(query_rows_name, {})
    query_plan_payload = active_artifacts.get(query_plan_name, {})
    preset_options = sorted((query_rows_payload or {}).keys())
    if not preset_options:
        st.info('No QE query-row artifacts found for this state mode yet. Run the pipeline to populate run_stats_query_rows outputs.')
        return
    preset_name = request.preset if request.preset in preset_options else preset_options[0]
    preset_name = st.selectbox('QE preset', options=preset_options, index=preset_options.index(preset_name))
    frame = qe_query_rows_frame(query_rows_payload, preset=preset_name)
    if frame.empty:
        st.info('No QE rows available for the selected preset.')
        return

    control_cols = st.columns((2, 1, 1))
    surface_search = control_cols[0].text_input('Surface search', value='')
    active_only = control_cols[1].toggle('Active only', value=True)
    unresolved_only = control_cols[2].toggle('Unresolved only', value=False)

    filtered = frame.copy()
    if surface_search:
        needle = surface_search.lower()
        filtered = filtered[filtered['surface_id'].str.lower().str.contains(needle)]
    if active_only:
        filtered = filtered[filtered['status'] != 'gated_off']
    if unresolved_only:
        filtered = filtered[filtered['status'] != 'resolved']
    if filtered.empty:
        st.warning('No QE surfaces match the current filters.')
        return

    st.dataframe(
        filtered[['group', 'display_label', 'surface_id', 'status', 'bundle_id', 'family_id', 'contributor_count', 'resolution_order_index', 'has_trace_steps']],
        width='stretch',
        hide_index=True,
    )

    selected_surface = st.selectbox('Selected surface', options=filtered['surface_id'].tolist())
    row_payload = qe_surface_payload(query_rows_payload, preset=preset_name, surface_id=selected_surface)
    trace_payload = row_payload.get('dependency_trace') or {}

    summary_rows = [
        ('surface_id', row_payload.get('surface_id')),
        ('raw_surface_id', row_payload.get('raw_surface_id')),
        ('status', row_payload.get('status')),
        ('final_value', row_payload.get('final_value')),
        ('display_value', row_payload.get('display_value')),
        ('value_type', row_payload.get('value_type')),
        ('bundle_id', row_payload.get('bundle_id')),
        ('family_id', row_payload.get('family_id')),
        ('trace_mode', row_payload.get('trace_mode')),
    ]
    st.subheader('Selected Surface Summary')
    st.dataframe(
        _arrow_safe_frame(pd.DataFrame(summary_rows, columns=['field', 'value'])),
        width='stretch',
        hide_index=True,
    )

    st.subheader('Contributor Lineage')
    st.dataframe(
        _arrow_safe_frame(qe_contributor_rows_frame(row_payload), columns=('value', 'display_value')),
        width='stretch',
        hide_index=True,
    )

    st.subheader('Dependency Trace Summary')
    st.dataframe(_arrow_safe_frame(qe_trace_summary_frame(trace_payload)), width='stretch', hide_index=True)

    trace_cols = st.columns(2)
    with trace_cols[0]:
        st.caption('Direct upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='direct_upstream_node_ids'), width='stretch', hide_index=True)
        st.caption('Resolved upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='resolved_upstream_node_ids'), width='stretch', hide_index=True)
        st.caption('Unresolved upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='unresolved_upstream_node_ids'), width='stretch', hide_index=True)
    with trace_cols[1]:
        st.caption('Direct downstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='direct_downstream_node_ids'), width='stretch', hide_index=True)
        st.caption('Upstream closure')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='upstream_closure_node_ids'), width='stretch', hide_index=True)
        st.caption('Downstream closure')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='downstream_closure_node_ids'), width='stretch', hide_index=True)

    st.subheader('Runtime Trace Steps')
    st.dataframe(qe_trace_steps_frame(trace_payload), width='stretch', hide_index=True)

    st.subheader('Active Query-Plan Coverage')
    st.dataframe(qe_plan_coverage_frame(query_plan_payload, preset=preset_name, surface_id=selected_surface), width='stretch', hide_index=True)

def _render_stats_debug_tools(active_artifacts, comparison_artifacts: list[tuple[str, object]], request: PipelineRunRequest) -> None:
    def _available_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
        return [column for column in columns if column in frame.columns]

    st.subheader('Stats')
    run_stats_payload = active_artifacts.get('run_stats.json', {})
    available_presets = sorted(
        set(((run_stats_payload.get('presets') or {}).keys()))
        | set((active_artifacts.get('run_stats_query_rows_start_of_run.json', {}) or {}).keys())
        | set((active_artifacts.get('run_stats_query_rows_max_progression.json', {}) or {}).keys())
    )
    active_preset = request.preset if request.preset in available_presets else (available_presets[0] if available_presets else request.preset)
    preset = st.selectbox('Loadout', options=available_presets or [active_preset], index=(available_presets.index(active_preset) if active_preset in available_presets else 0))
    view_mode = st.radio(
        'Artifact view',
        options=[
            'Resolved ledger (query rows)',
            'Run-stats payload (fast subset)',
            'Published statbook artifact (advanced)',
        ],
        horizontal=True,
    )
    st.caption('One stat authority (QE-resolved ledger); this selector switches derived artifact views.')
    show_changed_only = st.toggle('Changed in max progression only', value=False)
    show_raw_ids = st.toggle('Show raw artifact IDs', value=False)
    search_text = st.text_input('Search stats', value='').strip().lower()

    if view_mode == 'Resolved ledger (query rows)':
        active_df = query_rows_dual_state_frame(
            active_artifacts.get('run_stats_query_rows_start_of_run.json', {}),
            active_artifacts.get('run_stats_query_rows_max_progression.json', {}),
            preset=preset,
        )
    elif view_mode == 'Run-stats payload (fast subset)':
        active_df = run_stats_rows_frame(run_stats_payload, preset=preset)
    else:
        use_publishable = st.toggle('Use publishable statbook', value=True)
        payload_name = 'statbook_publishable.json' if use_publishable else 'statbook.json'
        active_df = statbook_rows_frame(active_artifacts.get(payload_name, {}))
    if active_df.empty:
        st.info('No stat rows available for this snapshot.')
        return

    groups = sorted(active_df['group'].dropna().unique().tolist())
    selected_groups = st.multiselect('Groups', options=groups, default=groups)
    filtered_active = active_df[active_df['group'].isin(selected_groups)].copy()
    if search_text:
        filtered_active = filtered_active[
            filtered_active['display_label'].str.lower().str.contains(search_text, na=False)
            | filtered_active['surface_id'].str.lower().str.contains(search_text, na=False)
        ].copy()
    if 'changed_in_max_progression' in filtered_active.columns and show_changed_only:
        filtered_active = filtered_active[filtered_active['changed_in_max_progression']]

    compare_df = compare_rows_frame(active_artifacts.get('ep_oracle_compare.json', {}))
    compare_columns = _available_columns(compare_df, ['surface_id', 'ep_value', 'ep_value_raw', 'compare_preset', 'compare_perk_state', 'status', 'label'])
    if not compare_df.empty and 'surface_id' in compare_columns:
        compare_subset = compare_df[compare_columns].copy()
        compare_subset = compare_subset.rename(
            columns={
                'ep_value': 'ep value',
                'ep_value_raw': 'ep display',
                'compare_preset': 'ep preset',
                'compare_perk_state': 'ep perks',
                'status': 'ep status',
                'label': 'ep label',
            }
        )
        filtered_active = filtered_active.merge(compare_subset, on='surface_id', how='left')

    if filtered_active.empty:
        st.info('No stats match the current filters.')
        return

    if view_mode in {'Resolved ledger (query rows)', 'Run-stats payload (fast subset)'}:
        _render_loadout_panel(
            active_artifacts,
            preset=preset,
            max_progression_rows=_max_progression_lookup(active_df),
            ids_path=request.ids,
            manual_inputs_path=request.manual_inputs,
        )
        filtered_active['ep delta vs max'] = pd.to_numeric(filtered_active.get('max_progression_value'), errors='coerce') - pd.to_numeric(
            filtered_active.get('ep value'),
            errors='coerce',
        )
        _render_sectioned_run_stats_table(filtered_active, show_raw_ids=show_raw_ids)
        with st.expander('Flat all-stats table'):
            table_columns = _available_columns(filtered_active, [
                'group',
                'display_label',
                'surface_id',
                'start_of_run_display',
                'start_of_run_value',
                'start_of_run_status',
                'max_progression_display',
                'max_progression_value',
                'max_progression_status',
                'changed_in_max_progression',
                'ep display',
                'ep value',
                'ep delta vs max',
                'ep preset',
                'ep perks',
                'ep status',
            ])
            if show_raw_ids and 'raw_surface_id' in filtered_active.columns:
                table_columns.insert(3, 'raw_surface_id')
            st.dataframe(filtered_active[table_columns], width='stretch', hide_index=True)
    else:
        table_columns = _available_columns(filtered_active, ['group', 'display_label', 'surface_id', 'final_value', 'display_value', 'value_type', 'status', 'contributor_count', 'ep display', 'ep value', 'ep preset', 'ep perks', 'ep status'])
        if show_raw_ids and 'raw_surface_id' in filtered_active.columns:
            table_columns.insert(3, 'raw_surface_id')
        st.dataframe(filtered_active[table_columns], width='stretch', hide_index=True)

    st.subheader('Fast Checkpoint Verification')
    st.caption('Uses the lightweight QE checkpoint resolver from PR 318 for exact targeted surfaces. Mixed visible tables can span unsupported families, so verification should be focused.')
    verification_state_mode = st.radio(
        'Verification state',
        options=['start_of_run', 'max_progression'],
        index=0 if request.state_mode == 'start_of_run' else 1,
        horizontal=True,
    )
    verification_options = {
        f"{row.display_label} [{row.surface_id}]": row.surface_id
        for row in filtered_active[['display_label', 'surface_id']].drop_duplicates().itertuples(index=False)
    }
    default_focus_labels = [
        label
        for label, surface_id in verification_options.items()
        if surface_id in {
            'state::tower.defense_pct',
            'state::tower.enemy_attack_level_skip_pct',
            'state::tower.enemy_health_level_skip_pct',
            'state::tower.free_attack_upgrade_chance_pct',
            'state::tower.free_defense_upgrade_chance_pct',
            'state::tower.free_utility_upgrade_chance_pct',
        }
    ]
    selected_verification_labels = st.multiselect(
        'Surfaces to verify',
        options=list(verification_options.keys()),
        default=default_focus_labels,
    )
    requested_surface_ids = tuple(verification_options[label] for label in selected_verification_labels)
    st.write(f'Surfaces selected for fast verification: `{len(requested_surface_ids)}`')
    if st.button('Resolve selected stats via fast checkpoint', width='stretch', disabled=not requested_surface_ids):
        fast_result = resolve_fast_checkpoint(
            FastCheckpointRequest(
                ids=request.ids,
                manual_inputs=request.manual_inputs,
                runtime_state_overlay=request.runtime_state_overlay,
                preset=preset,
                state_mode=verification_state_mode,
                perk_mode=request.perk_mode,
                perk_state=request.perk_state,
                requested_surface_ids=requested_surface_ids,
            )
        )
        st.session_state['fast_checkpoint_result'] = {
            'request': {
                'preset': request.preset,
                'state_mode': verification_state_mode,
                'perk_state': request.perk_state,
                'surface_count': len(requested_surface_ids),
            },
            'statbook': fast_result.statbook,
            'diagnostics': fast_result.diagnostics,
        }

    fast_payload = st.session_state.get('fast_checkpoint_result')
    if isinstance(fast_payload, dict) and fast_payload.get('statbook'):
        fast_df = statbook_rows_frame(fast_payload.get('statbook') or {})
        st.json(fast_payload.get('diagnostics') or {})
        if not fast_df.empty:
            if view_mode in {'Resolved ledger (query rows)', 'Run-stats payload (fast subset)'}:
                source_prefix = 'start_of_run' if fast_payload.get('request', {}).get('state_mode') == 'start_of_run' else 'max_progression'
                fast_compare = filtered_active[_available_columns(filtered_active, ['surface_id', 'display_label', f'{source_prefix}_display', f'{source_prefix}_value', f'{source_prefix}_status'])].copy()
                fast_compare = fast_compare.rename(
                    columns={
                        f'{source_prefix}_display': 'artifact display',
                        f'{source_prefix}_value': 'artifact value',
                        f'{source_prefix}_status': 'artifact status',
                    }
                )
            else:
                fast_compare = filtered_active[_available_columns(filtered_active, ['surface_id', 'display_label', 'display_value', 'final_value', 'status'])].copy()
                fast_compare = fast_compare.rename(
                    columns={
                        'display_value': 'artifact display',
                        'final_value': 'artifact value',
                        'status': 'artifact status',
                    }
                )
            fast_compare = fast_compare.merge(
                fast_df[['surface_id', 'display_value', 'final_value', 'status']].rename(
                    columns={
                        'display_value': 'fast display',
                        'final_value': 'fast value',
                        'status': 'fast status',
                    }
                ),
                on='surface_id',
                how='left',
            )
            fast_compare['delta'] = pd.to_numeric(fast_compare['fast value'], errors='coerce') - pd.to_numeric(
                fast_compare['artifact value'], errors='coerce'
            )
            st.dataframe(fast_compare, width='stretch', hide_index=True)

    if comparison_artifacts:
        st.subheader('Comparison Workbench')
        labels = [label for label, _ in comparison_artifacts]
        selected = st.multiselect('Snapshots to compare', options=labels, default=labels[: min(4, len(labels))])
        comparison_frames = []
        for label, artifacts in comparison_artifacts:
            if label not in selected:
                continue
            frame = query_rows_dual_state_frame(
                artifacts.get('run_stats_query_rows_start_of_run.json', {}),
                artifacts.get('run_stats_query_rows_max_progression.json', {}),
                preset=preset,
            )
            if frame.empty:
                continue
            frame = frame[['surface_id', 'start_of_run_display', 'max_progression_display']].rename(
                columns={
                    'start_of_run_display': f'{label} start',
                    'max_progression_display': f'{label} max',
                }
            )
            comparison_frames.append(frame)
        if comparison_frames:
            merged = filtered_active[['group', 'display_label', 'surface_id', 'start_of_run_display', 'max_progression_display', 'changed_in_max_progression']].copy()
            merged = merged.rename(columns={'start_of_run_display': 'active start', 'max_progression_display': 'active max'})
            for frame in comparison_frames:
                merged = merged.merge(frame, on='surface_id', how='left')
            st.dataframe(merged, width='stretch', hide_index=True)

    selected_surface = st.selectbox('Contributor drilldown surface', options=filtered_active['surface_id'].tolist())
    detail_payload_name = 'run_stats_query_rows_start_of_run.json' if request.state_mode == 'start_of_run' else 'run_stats_query_rows_max_progression.json'
    selected_row = query_rows_surface_detail(active_artifacts.get(detail_payload_name, {}), preset=preset, surface_id=selected_surface)
    if selected_row:
        st.subheader('Contributor Drilldown')
        st.json(selected_row)


def _render_stats(active_artifacts, comparison_artifacts: list[tuple[str, object]], request: PipelineRunRequest) -> None:
    st.subheader('Stats')
    dashboard = active_artifacts.get('stats_dashboard.json') or {}
    if isinstance(dashboard, dict) and dashboard.get('panels'):
        st.markdown(INPUT_DASHBOARD_CSS, unsafe_allow_html=True)
        preset_options = [str(name) for name in (dashboard.get('preset_options') or ['Farming'])]
        default_preset = str(dashboard.get('selected_preset') or preset_options[0])
        requested_preset = str(request.preset or '').strip()
        if requested_preset in preset_options:
            selected_preset = requested_preset
        else:
            selected_preset = default_preset if default_preset in preset_options else preset_options[0]
        selected_state_mode = str(dashboard.get('selected_state_mode') or 'max_progression')

        variants = dashboard.get('variants') or {}
        secondary_variants = dashboard.get('secondary_variants') or {}
        panels = (
            (((variants.get(selected_preset) or {}).get(selected_state_mode) or []))
            if isinstance(variants, dict)
            else (dashboard.get('panels') or [])
        )
        secondary_panels = (
            (((secondary_variants.get(selected_preset) or {}).get(selected_state_mode) or []))
            if isinstance(secondary_variants, dict)
            else (dashboard.get('secondary_panels') or [])
        )
        if not panels:
            panels = dashboard.get('panels') or []
        if not secondary_panels:
            secondary_panels = dashboard.get('secondary_panels') or []

        for panel in panels:
            panel_type = str((panel or {}).get('panel_type') or '')
            payload = dict((panel or {}).get('payload') or {})
            title = str((panel or {}).get('title') or (panel or {}).get('panel_id') or 'Panel')
            st.subheader(title)
            if panel_type == 'overview_metrics':
                st.markdown(render_overview_metric_strip_html(payload), unsafe_allow_html=True)
            elif panel_type == 'context_modules':
                slots = payload.get('slots') or {}
                if not slots:
                    st.markdown(render_gap_notice_html({'message': payload.get('message') or 'Module card payload unavailable.'}), unsafe_allow_html=True)
                    continue
                grouped_modules_html = render_grouped_modules_html(payload)
                if grouped_modules_html:
                    st.markdown(grouped_modules_html, unsafe_allow_html=True)
                st.markdown(MODULE_CARD_CSS, unsafe_allow_html=True)
                slot_columns = st.columns(4)
                for idx, slot in enumerate(['cannon', 'armor', 'generator', 'core']):
                    with slot_columns[idx]:
                        st.markdown(f'**{slot.title()}**')
                        slot_payload = (slots.get(slot) or {})
                        for role in ['primary', 'assist']:
                            card_payload = slot_payload.get(role)
                            if not card_payload:
                                st.caption(f'{role.title()}: No module equipped')
                                continue
                            st.markdown(render_module_card_html(card_payload), unsafe_allow_html=True)
            elif panel_type == 'context_cards':
                st.markdown(render_cards_inventory_and_preset_html(payload), unsafe_allow_html=True)
            elif panel_type in {'context_uw', 'resolved_uw_section'}:
                st.markdown(render_stats_uw_section_html(payload), unsafe_allow_html=True)
            elif panel_type == 'context_bonus_table':
                st.markdown(render_simple_bonus_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'resolved_stat_section':
                st.markdown(render_resolved_stat_section_html(payload), unsafe_allow_html=True)
            elif panel_type == 'workshop_stat_table':
                st.markdown(render_workshop_stat_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'context_track_table':
                st.markdown(render_track_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'gap_notice':
                st.markdown(render_gap_notice_html(payload), unsafe_allow_html=True)
            else:
                st.markdown(render_gap_notice_html({'message': f'Unsupported panel type: {panel_type}'}), unsafe_allow_html=True)

        if secondary_panels:
            with st.expander('Detailed QE rows and secondary context', expanded=False):
                for panel in secondary_panels:
                    panel_type = str((panel or {}).get('panel_type') or '')
                    payload = dict((panel or {}).get('payload') or {})
                    title = str((panel or {}).get('title') or (panel or {}).get('panel_id') or 'Panel')
                    st.subheader(title)
                    if panel_type == 'resolved_stat_section':
                        st.markdown(render_resolved_stat_section_html(payload), unsafe_allow_html=True)
                    elif panel_type in {'context_uw', 'resolved_uw_section'}:
                        st.markdown(render_stats_uw_section_html(payload), unsafe_allow_html=True)
                    elif panel_type == 'context_modules':
                        slots = payload.get('slots') or {}
                        if not slots:
                            st.markdown(render_gap_notice_html({'message': payload.get('message') or 'Module card payload unavailable.'}), unsafe_allow_html=True)
                            continue
                        grouped_modules_html = render_grouped_modules_html(payload)
                        if grouped_modules_html:
                            st.markdown(grouped_modules_html, unsafe_allow_html=True)
                        st.markdown(MODULE_CARD_CSS, unsafe_allow_html=True)
                        slot_columns = st.columns(4)
                        for idx, slot in enumerate(['cannon', 'armor', 'generator', 'core']):
                            with slot_columns[idx]:
                                st.markdown(f'**{slot.title()}**')
                                slot_payload = (slots.get(slot) or {})
                                for role in ['primary', 'assist']:
                                    card_payload = slot_payload.get(role)
                                    if not card_payload:
                                        st.caption(f'{role.title()}: No module equipped')
                                        continue
                                    st.markdown(render_module_card_html(card_payload), unsafe_allow_html=True)
                    elif panel_type == 'context_cards':
                        st.markdown(render_cards_inventory_and_preset_html(payload), unsafe_allow_html=True)
                    elif panel_type == 'context_bonus_table':
                        st.markdown(render_simple_bonus_table_html(payload), unsafe_allow_html=True)
                    elif panel_type == 'context_track_table':
                        st.markdown(render_track_table_html(payload), unsafe_allow_html=True)
                    elif panel_type == 'simple_metric_panel':
                        st.markdown(render_simple_metric_panel_html(payload), unsafe_allow_html=True)
                    elif panel_type == 'gap_notice':
                        st.markdown(render_gap_notice_html(payload), unsafe_allow_html=True)
                    else:
                        st.markdown(render_gap_notice_html({'message': f'Unsupported secondary panel type: {panel_type}'}), unsafe_allow_html=True)

        if dashboard.get('upstream_gaps'):
            st.warning('Upstream publication gaps detected')
            st.json(dashboard.get('upstream_gaps'))
        with st.expander('Advanced stats artifact (stats_dashboard.json)', expanded=False):
            st.json(dashboard)
    else:
        st.info('stats_dashboard.json missing; showing fallback stats views only.')

    with st.expander('Stats evidence and verification', expanded=False):
        try:
            _render_stats_debug_tools(active_artifacts, comparison_artifacts, request)
        except Exception as exc:
            st.warning(f'Stats evidence tools unavailable for this snapshot: {exc}')


def _render_checks(active_artifacts, request: PipelineRunRequest) -> None:
    _render_verification_snapshot_controls(request)
    diagnostics = active_artifacts.get('diagnostics.json', {})
    st.subheader('Needs Attention')
    compare_df = compare_rows_frame(active_artifacts.get('ep_oracle_compare.json', {}))
    verification_df = verification_rows_frame(active_artifacts.get('line_by_line_verification.json', {}))
    attention = {
        'compare_mismatches': int((compare_df.get('status') == 'mismatch').sum()) if 'status' in compare_df else 0,
        'verification_non_pass': int((verification_df.get('authoritative_verdict') != 'pass').sum()) if 'authoritative_verdict' in verification_df else 0,
        'cache_invalidations': 1 if ((active_artifacts.get('pipeline_trace.json', {}).get('execution_path') or {}).get('cache_status') == 'invalid') else 0,
        'fallback_required': 1 if ((active_artifacts.get('pipeline_trace.json', {}).get('execution_path') or {}).get('fallback_required')) else 0,
        'parity_mismatches': len((((active_artifacts.get('pipeline_trace.json', {}).get('execution_path') or {}).get('parity') or {}).get('mismatches') or [])),
    }
    st.json(attention)
    st.subheader('QE Mapping')
    qe_summary = {
        'qe_resolution_interface': diagnostics.get('qe_resolution_interface'),
        'qe_resolution_backend': diagnostics.get('qe_resolution_backend'),
        'qe_native_family_available': diagnostics.get('qe_native_family_available'),
        'qe_native_family_id': diagnostics.get('qe_native_family_id'),
        'mapped_stat_input_count': diagnostics.get('mapped_stat_input_count'),
        'unmapped_stat_input_count': diagnostics.get('unmapped_stat_input_count'),
        'calculator_scope_mapped_inputs': ((diagnostics.get('coverage_summary') or {}).get('calculator_scope_mapped_inputs')),
        'calculator_scope_mapping_pct': ((diagnostics.get('coverage_summary') or {}).get('calculator_scope_mapping_pct')),
        'calculator_scope_unmapped_examples': ((diagnostics.get('coverage_summary') or {}).get('calculator_scope_unmapped_examples')),
    }
    st.json(qe_summary)
    family_mapping_pct = ((diagnostics.get('coverage_summary') or {}).get('family_mapping_pct')) or {}
    if family_mapping_pct:
        family_rows = []
        for family_name, payload in family_mapping_pct.items():
            family_rows.append(
                {
                    'family': family_name,
                    'mapped': payload.get('mapped'),
                    'total': payload.get('total'),
                    'pct': payload.get('pct'),
                }
            )
        st.dataframe(pd.DataFrame(family_rows), width='stretch', hide_index=True)
    active_unmapped_inputs = diagnostics.get('active_unmapped_inputs') or []
    if active_unmapped_inputs:
        with st.expander('Active unmapped inputs'):
            st.dataframe(pd.DataFrame(active_unmapped_inputs), width='stretch', hide_index=True)
    st.subheader('EP Compare')
    st.dataframe(compare_df, width='stretch', hide_index=True)
    st.subheader('Line Verification')
    st.dataframe(verification_df, width='stretch', hide_index=True)
    st.subheader('State Matrix')
    st.json(active_artifacts.get('state_matrix.json', {}))
    st.subheader('Family Completeness')
    st.json(active_artifacts.get('family_completeness_matrix.json', {}))
    st.subheader('Audit Surface Manifest')
    st.json(active_artifacts.get('audit_surface_manifest.json', {}))
    st.subheader('Gap and Closure Reports')
    report_names = [
        'tower_regen_closure_report.json',
        'tower_hp_semantic_gap_report.json',
        'tower_regen_ep_semantic_gap_report.json',
        'tower_defense_absolute_semantic_gap_report.json',
        'tower_damage_runtime_gap_report.json',
    ]
    for name in report_names:
        if active_artifacts.get(name):
            with st.expander(name):
                st.json(active_artifacts.get(name))


def _render_inputs(active_artifacts, active_out_dir: Path) -> None:
    dashboard = active_artifacts.get('input_dashboard.json') or {}
    if isinstance(dashboard, dict) and dashboard.get('panels'):
        st.markdown(INPUT_DASHBOARD_CSS, unsafe_allow_html=True)
        preset_options = list(dashboard.get('preset_options') or ['Farming'])
        default_preset = str(dashboard.get('selected_preset') or preset_options[0])
        selected_preset = st.selectbox(
            'Loadout',
            options=preset_options,
            index=preset_options.index(default_preset) if default_preset in preset_options else 0,
            key='input_dashboard_preset_selector',
        )

        panel_map = {str(panel.get('panel_id')): panel for panel in (dashboard.get('panels') or []) if isinstance(panel, dict)}
        for panel_id in [
            'labs',
            'workshop',
            'workshop_enhancements',
            'ultimate_weapons',
            'cards',
            'bots',
            'relics',
            'modules',
            'vault',
            'guardians',
            'themes_and_songs',
        ]:
            panel = panel_map.get(panel_id) or {}
            panel_type = panel.get('panel_type')
            payload = panel.get('payload') or {}
            st.subheader(str(panel.get('title') or panel_id.replace('_', ' ').title()))
            if panel_type == 'labs_bucket_grid':
                st.markdown(render_labs_bucket_grid_html(payload), unsafe_allow_html=True)
            elif panel_type == 'grouped_workshop_table':
                st.markdown(render_grouped_workshop_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'grouped_enhancement_table':
                st.markdown(render_grouped_enhancement_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'uw_track_table':
                st.markdown(render_uw_track_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'cards_inventory_and_preset':
                preset_rows_by_preset = payload.get('preset_rows_by_preset') or {}
                selected_rows = preset_rows_by_preset.get(selected_preset)
                if selected_rows is None:
                    st.error(
                        'Cards panel unavailable: selected preset is missing in publication output. '
                        'Re-run pipeline to refresh input_dashboard.json.'
                    )
                    continue
                render_payload = dict(payload)
                render_payload['preset_rows'] = selected_rows
                st.markdown(render_cards_inventory_and_preset_html(render_payload), unsafe_allow_html=True)
            elif panel_type == 'track_table':
                st.markdown(render_track_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'simple_bonus_table':
                st.markdown(render_simple_bonus_table_html(payload), unsafe_allow_html=True)
            elif panel_type == 'simple_metric_panel':
                st.markdown(render_simple_metric_panel_html(payload), unsafe_allow_html=True)
            elif panel_type == 'module_slot_stack':
                module_payload_root = active_artifacts.get('module_card_payloads.json', {}) or {}
                preset_payload = ((module_payload_root.get('presets') or {}).get(selected_preset) or {})
                if not preset_payload:
                    st.warning(payload.get('message') or 'module_card_payloads.json not present for this snapshot')
                    continue
                st.markdown(MODULE_CARD_CSS, unsafe_allow_html=True)
                slot_columns = st.columns(4)
                for idx, slot in enumerate(['cannon', 'armor', 'generator', 'core']):
                    with slot_columns[idx]:
                        st.markdown(f'**{slot.title()}**')
                        slot_payload = preset_payload.get(slot) or {}
                        for role in ['primary', 'assist']:
                            card_payload = slot_payload.get(role)
                            if not card_payload:
                                st.caption(f'{role.title()}: No module equipped')
                                continue
                            st.markdown(render_module_card_html(card_payload), unsafe_allow_html=True)

        if dashboard.get('upstream_gaps'):
            st.warning('Upstream publication gaps detected')
            st.json(dashboard.get('upstream_gaps'))
        with st.expander('Advanced input artifact (input_dashboard.json)', expanded=False):
            st.json(dashboard)
    else:
        st.info('input_dashboard.json missing; showing fallback input views only.')

    with st.expander('Input lineage and artifact evidence', expanded=False):
        diagnostics = active_artifacts.get('diagnostics.json', {})
        account_state_payload = active_artifacts.get('account_state.json') or {}
        st.json(
            {
                'active_output_dir': str(active_out_dir),
                'diagnostics_summary': {
                    'section_names': diagnostics.get('section_names', []),
                    'section_row_counts': diagnostics.get('section_row_counts', {}),
                    'perk_config_resolution': diagnostics.get('perk_config_resolution', {}),
                },
                'pipeline_compare_policy': diagnostics.get('compare_situation_policy', {}),
            }
        )
        st.subheader('Artifact summary')
        st.json(
            {
                'account_state_keys': sorted(account_state_payload.keys()) if isinstance(account_state_payload, dict) else [],
                'stat_inputs_count': len(active_artifacts.get('stat_inputs.json') or []),
                'pipeline_trace_stage_count': len((active_artifacts.get('pipeline_trace.json') or {}).get('stages') or []),
            }
        )
        st.subheader('Input lineage')
        lineage_frame = input_lineage_rows_frame(
            active_artifacts.get('stat_inputs.json'),
            account_state_payload=account_state_payload if isinstance(account_state_payload, dict) else None,
        )
        if not lineage_frame.empty:
            st.dataframe(
                _arrow_safe_frame(lineage_frame, columns=('source_value', 'resolved_value')),
                width='stretch',
                hide_index=True,
            )
        else:
            st.info('No lineage rows available for this snapshot.')


def _require_boss_wave_payload_rows(boss_payload: dict, field_name: str) -> list[dict]:
    rows = boss_payload.get(field_name)
    if not isinstance(rows, list):
        raise ValueError(f"Boss Waves payload contract error: {field_name!r} must be present as a list")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Boss Waves payload contract error: {field_name!r} rows must be mappings")
    return rows


def _render_boss_waves(request: PipelineRunRequest) -> None:
    st.subheader('Boss Waves')
    control_cols = st.columns(6)
    preset_name = control_cols[0].selectbox('Boss loadout', options=['Farming', 'Tourney', 'Milestone'], index=['Farming', 'Tourney', 'Milestone'].index(request.preset) if request.preset in {'Farming', 'Tourney', 'Milestone'} else 0)
    perk_policy_preset = control_cols[1].selectbox(
        'Perk plan',
        options=list(BOSS_WAVE_PERK_POLICY_PRESETS),
        index=(
            list(BOSS_WAVE_PERK_POLICY_PRESETS).index(request.perk_policy_preset)
            if request.perk_policy_preset in BOSS_WAVE_PERK_POLICY_PRESETS
            else 1
        ),
        key='boss_waves_perk_plan',
    )
    run_type_options = ('none', *BOSS_WAVE_DISSONANCE_RUN_CATEGORIES)
    requested_run_type = str(request.dissonance_run_category or 'none')
    dissonance_run_category = control_cols[2].selectbox(
        'Run type',
        options=run_type_options,
        index=run_type_options.index(requested_run_type) if requested_run_type in run_type_options else 0,
        format_func=lambda value: BOSS_WAVE_DISSONANCE_RUN_LABELS.get(str(value), str(value)),
        key='boss_waves_run_type',
    )
    tier_number = control_cols[3].number_input('Tier', min_value=1, max_value=21, value=14, step=1)
    end_wave = control_cols[4].number_input('End wave', min_value=10, value=10000, step=10)
    boss_wave_step = control_cols[5].number_input('Checkpoint cadence (bosses)', min_value=1, max_value=1000, value=1, step=1)
    scenario_request = replace(
        request,
        preset=preset_name,
        perk_policy_preset=perk_policy_preset,
        dissonance_run_category=dissonance_run_category,
    )
    stop_on_failure = True
    tournament_wave_override = 0
    if preset_name == 'Tourney':
        tournament_wave_override = st.number_input('Legends tournament wave', min_value=1, value=100, step=10)

    with st.expander('Combat assumptions', expanded=False):
        runtime_cols = st.columns(5)
        orb_boss_total_damage_pct = runtime_cols[0].number_input('Orb damage to boss (total %)', min_value=0.0, max_value=100.0, value=6.0, step=0.1)
        electron_total_damage_pct = runtime_cols[1].number_input('Electron damage override (total %)', min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        flame_bot_damage_reduction_pct = runtime_cols[2].number_input('Flame Bot DR override (%)', min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        boss_time_to_contact_seconds = runtime_cols[3].number_input('Boss time to contact override (s)', min_value=0.0, max_value=120.0, value=0.0, step=0.1)
        death_wave_health_max_wave = runtime_cols[4].number_input('Death Wave maxed wave', min_value=1, value=1000, step=10)
        use_manual_damage_calibration = st.toggle('Override boss damage calibration', value=False)
        boss_applicable_damage_factor = 0.0
        boss_edamage_target_share = 0.0
        boss_edamage_cadence_uptime_factor = 0.0
        boss_edamage_reliability_factor = 0.0
        boss_edamage_semantic_normalizer = 0.0
        if use_manual_damage_calibration:
            gc_cols = st.columns(2)
            boss_applicable_damage_factor = gc_cols[0].number_input('Boss eDamage applicability factor', min_value=0.0, value=0.0, step=0.0001, format='%.6f')
            bridge_cols = st.columns(4)
            boss_edamage_target_share = bridge_cols[0].number_input('Boss target share', min_value=0.0, value=0.0, step=0.0001, format='%.6f')
            boss_edamage_cadence_uptime_factor = bridge_cols[1].number_input('Boss cadence uptime', min_value=0.0, value=0.0, step=0.0001, format='%.6f')
            boss_edamage_reliability_factor = bridge_cols[2].number_input('Boss reliability', min_value=0.0, value=0.0, step=0.0001, format='%.6f')
            boss_edamage_semantic_normalizer = bridge_cols[3].number_input('Boss semantic normalizer', min_value=0.0, value=0.0, step=0.0001, format='%.6f')
        terminal_cols = st.columns(4)
        fleet_terminal_max_wave = terminal_cols[0].number_input('Fleet terminal wave', min_value=0, value=0, step=10)
        elite_terminal_max_wave = terminal_cols[1].number_input('Elite terminal wave', min_value=0, value=0, step=10)
        protector_terminal_max_wave = terminal_cols[2].number_input('Protector terminal wave', min_value=0, value=0, step=10)
        armored_terminal_max_wave = terminal_cols[3].number_input('Armored terminal wave', min_value=0, value=0, step=10)
    decomposed_bridge_inputs = {
        **({'boss_edamage_target_share': boss_edamage_target_share} if boss_edamage_target_share > 0.0 else {}),
        **({'boss_edamage_cadence_uptime_factor': boss_edamage_cadence_uptime_factor} if boss_edamage_cadence_uptime_factor > 0.0 else {}),
        **({'boss_edamage_reliability_factor': boss_edamage_reliability_factor} if boss_edamage_reliability_factor > 0.0 else {}),
        **({'boss_edamage_semantic_normalizer': boss_edamage_semantic_normalizer} if boss_edamage_semantic_normalizer > 0.0 else {}),
    }
    scenario_runtime_inputs = {
        'orb_boss_total_damage_pct': orb_boss_total_damage_pct,
        **({'electron_total_damage_pct': electron_total_damage_pct} if electron_total_damage_pct > 0.0 else {}),
        **({'flame_bot_damage_reduction_pct': flame_bot_damage_reduction_pct} if flame_bot_damage_reduction_pct > 0.0 else {}),
        **({'boss_applicable_damage_factor': boss_applicable_damage_factor} if boss_applicable_damage_factor > 0.0 else {}),
        **decomposed_bridge_inputs,
        **({'boss_time_to_contact_seconds': boss_time_to_contact_seconds} if boss_time_to_contact_seconds > 0.0 else {}),
        **({'fleet_terminal_max_wave': fleet_terminal_max_wave} if fleet_terminal_max_wave > 0 else {}),
        **({'elite_terminal_max_wave': elite_terminal_max_wave} if elite_terminal_max_wave > 0 else {}),
        **({'protector_terminal_max_wave': protector_terminal_max_wave} if protector_terminal_max_wave > 0 else {}),
        **({'armored_terminal_max_wave': armored_terminal_max_wave} if armored_terminal_max_wave > 0 else {}),
        **({'tournament_wave': int(tournament_wave_override)} if preset_name == 'Tourney' and int(tournament_wave_override) > 0 else {}),
        'death_wave_health_max_wave': death_wave_health_max_wave,
    }
    try:
        boss_calc_start = time.perf_counter()
        boss_payload = build_boss_wave_payload(
            scenario_request,
            preset_name=preset_name,
            tier_number=int(tier_number),
            end_wave=int(end_wave),
            boss_wave_step=int(boss_wave_step),
            stop_on_failure=stop_on_failure,
            scenario_runtime_inputs=scenario_runtime_inputs,
            dissonance_run_category=dissonance_run_category,
        )
        boss_calc_elapsed = time.perf_counter() - boss_calc_start
    except Exception as exc:
        st.error(str(exc))
        return
    try:
        operator_rows = _require_boss_wave_payload_rows(boss_payload, 'operator_rows')
        download_rows = _require_boss_wave_payload_rows(boss_payload, 'download_rows')
    except ValueError as exc:
        st.error(str(exc))
        return
    frame = pd.DataFrame(operator_rows)
    download_frame = pd.DataFrame(download_rows)
    if not frame.empty and 'changed_workshop_tracks_last_step' in frame.columns:
        frame['changed_workshop_tracks_last_step'] = frame['changed_workshop_tracks_last_step'].fillna('')
    display_frame = _build_boss_wave_operator_frame(frame)
    payload_summary = dict(boss_payload.get('summary') or {})
    payload_diagnostics = dict(boss_payload.get('diagnostics') or {})
    primitive_inputs = dict(payload_diagnostics.get('replacement_primitive_inputs') or {})
    primitive_values = dict(primitive_inputs.get('values') or {})
    boss_damage_source = primitive_values.get('boss_damage_source') or primitive_values.get('gc_boss_damage_source') or 'unknown'
    payload_download = dict(boss_payload.get('download') or {})
    diagnostics = {
        'preset_name': payload_diagnostics.get('preset_name') or preset_name,
        'mode_id': payload_diagnostics.get('mode_id'),
        'tier_number': payload_diagnostics.get('tier_number'),
        'tier_column': payload_diagnostics.get('tier_column'),
        'league': payload_diagnostics.get('league'),
        'tournament_wave': payload_diagnostics.get('tournament_wave'),
        'tournament_wave_source': payload_diagnostics.get('tournament_wave_source'),
        'perks_enabled': bool(payload_diagnostics.get('perks_enabled')),
        'context_status': payload_diagnostics.get('context_status') or 'resolved',
        'context_error': payload_diagnostics.get('context_error'),
        'context_error_message': payload_diagnostics.get('context_error_message'),
        'actual_boss_interval_waves': payload_diagnostics.get('actual_boss_interval_waves'),
        'checkpoint_every_bosses': payload_diagnostics.get('checkpoint_every_bosses'),
        'checkpoint_stride_waves': payload_diagnostics.get('checkpoint_stride_waves'),
        'requested_start_wave': payload_diagnostics.get('requested_start_wave'),
        'first_checkpoint_wave': payload_diagnostics.get('first_checkpoint_wave'),
        'row_count': int(payload_summary.get('row_count') or len(frame)),
        'max_surviving_wave': int(payload_summary.get('max_surviving_wave') or 0),
        'selected_max_wave': int(payload_summary.get('selected_max_wave') or payload_summary.get('max_surviving_wave') or 0),
        'selected_first_failed_wave': int(payload_summary.get('selected_first_failed_wave') or 0),
        'selected_model': payload_summary.get('selected_model') or 'unified_hit_by_hit_boss_survival',
        'first_failed_wave': int(payload_summary.get('first_failed_wave') or 0),
        'pre_contact_boss_kill_max_wave': int(payload_summary.get('pre_contact_boss_kill_max_wave') or 0),
        'pre_contact_boss_kill_first_failed_wave': int(payload_summary.get('pre_contact_boss_kill_first_failed_wave') or 0),
        'gc_pre_contact_max_wave': int(payload_summary.get('gc_pre_contact_max_wave') or 0),
        'gc_pre_contact_first_failed_wave': int(payload_summary.get('gc_pre_contact_first_failed_wave') or 0),
        'contact_envelope_max_wave': int(payload_summary.get('contact_envelope_max_wave') or 0),
        'contact_envelope_first_failed_wave': int(payload_summary.get('contact_envelope_first_failed_wave') or 0),
        'max_wave': int(payload_summary.get('max_wave') or 0),
        'terminal_display_wave': int(payload_summary.get('terminal_display_wave') or 0),
        'survives_through_end': bool(payload_summary.get('survives_through_end')),
        'result_consistent_with_rows': bool(payload_summary.get('result_consistent_with_rows')),
        'state_mode': payload_diagnostics.get('state_mode'),
        'checkpoint_mode': payload_diagnostics.get('checkpoint_mode') or 'actual_boss_cadence_with_sampling',
        'stop_on_failure': bool(payload_diagnostics.get('stop_on_failure')),
        'scenario_runtime_inputs': dict(payload_diagnostics.get('scenario_runtime_inputs') or {}),
        'dissonance_run_category': payload_summary.get('dissonance_run_category') or payload_diagnostics.get('dissonance_run_category') or dissonance_run_category,
        'dissonance_run_label': payload_summary.get('dissonance_run_label') or BOSS_WAVE_DISSONANCE_RUN_LABELS.get(dissonance_run_category, str(dissonance_run_category)),
        'terminal_pressure_limiter': payload_summary.get('terminal_pressure_limiter') or payload_diagnostics.get('terminal_pressure_limiter'),
        'terminal_pressure_limited': bool(payload_summary.get('terminal_pressure_limited') or payload_diagnostics.get('terminal_pressure_limited')),
        'unsupported_pressure_missing_reference_blocked': bool(
            payload_summary.get('unsupported_pressure_missing_reference_blocked')
            or payload_diagnostics.get('unsupported_pressure_missing_reference_blocked')
        ),
        'unsupported_pressure_reference_limit': dict(
            payload_summary.get('unsupported_pressure_reference_limit')
            or payload_diagnostics.get('unsupported_pressure_reference_limit')
            or {}
        ),
        'unsupported_terminal_pressures': list(payload_diagnostics.get('unsupported_terminal_pressures') or []),
        'execution_mode': payload_diagnostics.get('execution_mode'),
        'checkpoint_resolution_mode': payload_diagnostics.get('checkpoint_resolution_mode'),
        'qe_resolution_count': int(payload_diagnostics.get('qe_resolution_count') or 0),
        'timing_recompute_count': int(payload_diagnostics.get('timing_recompute_count') or 0),
        'snapshot_reuse_count': int(payload_diagnostics.get('snapshot_reuse_count') or 0),
        'qe_dirty_reresolve_count': int(payload_diagnostics.get('qe_dirty_reresolve_count') or 0),
        'delta_fallback_count': int(payload_diagnostics.get('delta_fallback_count') or 0),
        'milestone_alignment': dict(payload_diagnostics.get('milestone_alignment') or {}),
    }

    st.metric('Max Boss Wave', diagnostics['selected_max_wave'])
    if diagnostics['terminal_pressure_limited']:
        cap = diagnostics['unsupported_pressure_reference_limit']
        if diagnostics['unsupported_pressure_missing_reference_blocked']:
            st.caption(
                f"Blocked by `{diagnostics['terminal_pressure_limiter']}`; "
                f"uncapped boss-only wave `{cap.get('uncapped_selected_max_wave') or '—'}`."
            )
        else:
            st.caption(
                f"Capped by `{diagnostics['terminal_pressure_limiter']}`; "
                f"uncapped boss-only wave `{cap.get('uncapped_selected_max_wave') or '—'}`."
            )
    st.caption(f"Result uses `{diagnostics['selected_model']}`. Calculated in `{boss_calc_elapsed:.2f}s`.")
    st.caption(
        f"`{diagnostics['preset_name']}` loadout; `{perk_policy_preset}` perk plan; "
        f"`{diagnostics['tier_column']}`; `{diagnostics['dissonance_run_label']}`; "
        f"boss cadence `{diagnostics['actual_boss_interval_waves'] or '—'}` waves; "
        f"perks `{'on' if diagnostics['perks_enabled'] else 'off'}`; "
        f"damage source `{boss_damage_source}`."
    )
    if diagnostics['selected_max_wave'] >= int(end_wave):
        st.info('Max Boss Wave reached the requested end wave. Increase End wave to search farther.')
    milestone_alignment = diagnostics['milestone_alignment']
    milestone_reference = milestone_alignment.get('reference_wave')
    if milestone_reference:
        reference_label = (
            'IDS Dissonant PB'
            if milestone_alignment.get('active_reference_kind') == 'ids_dissonant_pb_wave'
            else 'IDS milestone'
        )
        st.caption(
            f"{reference_label} reference: `{milestone_alignment.get('tier_column')}` wave `{milestone_reference}`; "
            f"solver delta `{milestone_alignment.get('delta_waves')}` waves."
        )
    contract = dict(boss_payload.get('contract') or {})
    if diagnostics['context_status'] not in {'resolved', 'complete'}:
        st.warning(diagnostics['context_error_message'] or 'Boss Waves cannot resolve the required scenario context for this request.')
    primary_columns = [
        'Result',
        'Wave',
        'Boss HP',
        'Boss Atk',
        'Tower DPS',
        'Wall HP',
        'Wall Regen',
        'Damage Reduction',
        'Boss Kill Time',
        'Contact Time',
        'Boss Hits',
        'Damage Taken',
        'Survival Margin',
        'Killed Before Contact',
    ]
    table_frame = display_frame.copy()
    if not table_frame.empty and 'Wave' in table_frame.columns:
        max_wave = diagnostics['selected_max_wave']
        table_frame['Result'] = pd.to_numeric(table_frame['Wave'], errors='coerce').map(
            lambda wave: 'max' if pd.notna(wave) and int(wave) == max_wave else ''
        )
    show_all_checkpoints = st.toggle('Show all checkpoints', value=False)
    visible_frame = table_frame if show_all_checkpoints else _focus_boss_wave_display_frame(
        table_frame,
        max_boss_wave=diagnostics['selected_max_wave'],
    )
    st.caption('Boss checkpoints')
    st.dataframe(visible_frame[[column for column in primary_columns if column in visible_frame.columns]], width='stretch', hide_index=True)
    st.download_button(
        'Download boss-wave CSV',
        data=download_frame.to_csv(index=False).encode('utf-8'),
        file_name=str(payload_download.get('file_name') or f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv'),
        mime='text/csv',
        width='stretch',
    )
    with st.expander('All-tier preset matrix'):
        st.caption('Runs the four Boss Waves perk presets across all tiers using the same assumptions as this tab.')
        matrix_cols = st.columns(2)
        matrix_end_wave = matrix_cols[0].number_input(
            'Matrix end wave',
            min_value=100,
            value=max(30000, int(end_wave)),
            step=1000,
        )
        matrix_boss_wave_step = matrix_cols[1].number_input(
            'Matrix checkpoint cadence (bosses)',
            min_value=1,
            max_value=1000,
            value=max(10, int(boss_wave_step)),
            step=1,
        )
        if st.button('Build all-tier 4-preset matrix'):
            matrix_start = time.perf_counter()
            matrix_payload = build_boss_wave_milestone_matrix(
                scenario_request,
                tiers=tuple(range(1, 22)),
                end_wave=int(matrix_end_wave),
                boss_wave_step=max(1, int(matrix_boss_wave_step)),
                stop_on_failure=True,
                scenario_runtime_inputs=scenario_runtime_inputs,
                loadout_policy_presets=BOSS_WAVE_PERK_POLICY_PRESETS,
                dissonance_run_categories=(dissonance_run_category,),
            )
            matrix_elapsed = time.perf_counter() - matrix_start
            matrix_rows = matrix_payload.get('rows') or []
            candidate_count = sum(len(row.get('candidate_results') or []) for row in matrix_rows)
            if candidate_count:
                st.caption(
                    f"Calculated `{candidate_count}` preset/tier candidates in `{matrix_elapsed:.2f}s` "
                    f"(`{matrix_elapsed / candidate_count:.2f}s` each)."
                )
            else:
                st.caption(f"Calculated in `{matrix_elapsed:.2f}s`.")
            st.dataframe(_boss_wave_preset_matrix_frame(matrix_payload), width='stretch', hide_index=True)
    with st.expander('Model assumptions'):
        st.dataframe(
            _boss_wave_assumption_frame(
                diagnostics=diagnostics,
                contract=contract,
                payload_diagnostics=payload_diagnostics,
                primitive_values=primitive_values,
                boss_damage_source=boss_damage_source,
            ),
            width='stretch',
            hide_index=True,
        )
        runtime_frame = _boss_wave_runtime_inputs_frame(diagnostics)
        if not runtime_frame.empty:
            st.caption('Runtime inputs')
            st.dataframe(runtime_frame, width='stretch', hide_index=True)
        st.caption(
            "Boss Waves is a bounded runtime estimate. The checkpoint table reflects the DR/contact assumptions used by the current run, "
            "including visible wall regen contribution."
        )
    with st.expander('Advanced boss-wave evidence'):
        evidence_tabs = st.tabs(['Full Table', 'Diagnostics', 'Raw Rows', 'Execution'])
        with evidence_tabs[0]:
            st.dataframe(display_frame, width='stretch', hide_index=True)
        with evidence_tabs[1]:
            st.json({
                'summary': diagnostics,
                'model_certification': payload_diagnostics.get('model_certification') or {},
                'contact_time_contract': payload_diagnostics.get('contact_time_contract') or {},
                'source_selection': payload_diagnostics.get('source_selection') or {},
                'replacement_model': payload_diagnostics.get('replacement_model') or {},
            })
        with evidence_tabs[2]:
            st.dataframe(frame, width='stretch', hide_index=True)
        with evidence_tabs[3]:
            st.json({
                'contract': boss_payload.get('contract') or {},
                'runtime_inputs_used': diagnostics['scenario_runtime_inputs'],
                'replacement_primitive_inputs': primitive_inputs,
                'replacement_primitive_semantics_ledger': payload_diagnostics.get('replacement_primitive_semantics_ledger') or {},
                'execution_counts': {
                    'qe_resolution_count': diagnostics['qe_resolution_count'],
                    'timing_recompute_count': diagnostics['timing_recompute_count'],
                    'snapshot_reuse_count': diagnostics['snapshot_reuse_count'],
                    'qe_dirty_reresolve_count': diagnostics['qe_dirty_reresolve_count'],
                    'delta_fallback_count': diagnostics['delta_fallback_count'],
                },
                'terminal_display_wave': diagnostics['terminal_display_wave'],
                'survives_through_end': diagnostics['survives_through_end'],
            })


def main() -> None:
    st.set_page_config(page_title='TowerSim Operations Console', layout='wide')
    st.title('TowerSim Operations Console')
    st.caption('Canonical stats, perk plans, and max-wave runs from sanctioned pipeline artifacts.')
    _init_state()
    _snapshot_sidebar()
    active_out_dir = Path(st.session_state['active_out_dir'])
    active_artifacts = load_artifacts(active_out_dir)
    request = _request_from_active_snapshot(active_out_dir, active_artifacts)
    comparison_artifacts = [
        (label, load_artifacts(Path(path)))
        for label, path in st.session_state['snapshot_dirs'].items()
        if Path(path) != active_out_dir
    ]

    inputs_tab, qe_tab, stats_tab, perks_tab, boss_waves_tab, pipeline_tab, checks_tab = st.tabs(['Input', 'QE', 'Stats', 'Perks', 'Boss Waves', 'Pipeline', 'Checks'])
    with inputs_tab:
        _render_inputs(active_artifacts, active_out_dir)
    with qe_tab:
        _render_qe(active_artifacts, request)
    with stats_tab:
        _render_stats(active_artifacts, comparison_artifacts, request)
    with perks_tab:
        _render_perk_policy_tab(request)
    with boss_waves_tab:
        _render_boss_waves(request)
    with pipeline_tab:
        _render_pipeline(active_artifacts.get('pipeline_trace.json', {}), active_artifacts.get('diagnostics.json', {}), request)
    with checks_tab:
        _render_checks(active_artifacts, request)


if __name__ == '__main__':
    main()



