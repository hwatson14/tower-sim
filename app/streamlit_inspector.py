from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
import sys

import pandas as pd
try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - import-safe helper tests
    class _MissingStreamlit:
        def __getattr__(self, name):
            raise ModuleNotFoundError('streamlit is required to run the inspector UI.')

    st = _MissingStreamlit()
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.display import MODULE_CARD_CSS, render_module_card_html
from app.inspector_data import (
    compare_rows_frame,
    dual_state_statbook_rows_frame,
    load_artifacts,
    pipeline_stages_frame,
    qe_contributor_rows_frame,
    qe_dependency_nodes_frame,
    qe_plan_coverage_frame,
    qe_query_rows_frame,
    qe_surface_payload,
    qe_trace_steps_frame,
    qe_trace_summary_frame,
    run_stats_rows_frame,
    snapshot_label,
    statbook_rows_frame,
    verification_rows_frame,
)
from app.pipeline import (
    FastCheckpointRequest,
    PipelineRunRequest,
    build_verification_snapshot_set,
    execute_pipeline,
    resolve_fast_checkpoint,
)
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from input.state_types import ScenarioRuntimeInputs
from qe.contracts import normalize_surface_id_to_contract
from qe.stat_input_compiler import (
    _load_card_mastery_values,
    _load_perk_effects,
    _load_perk_entities,
    _scaled_perk_value,
)
from simulators.contracts import PerkState
from simulators.run_executor import (
    RunToMaxConfig,
    build_boss_wave_table,
    build_start_of_run_state,
)

DEFAULT_OUT = ROOT / 'out'
DEFAULT_IDS = ROOT / 'input' / 'imports' / 'ids.csv'
PERK_ENTITY_REGISTRY = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
CARD_EFFECT_REGISTRY = ROOT / 'kb' / 'cards' / 'tables' / 'card-effect-registry.csv'
CARD_BASE_LADDERS = ROOT / 'kb' / 'cards' / 'tables' / 'card-base-ladders.csv'
MODULE_UNIQUE_EFFECTS = ROOT / 'kb' / 'modules' / 'tables' / 'module-unique-effects.csv'
MODULE_UNIQUE_RUNTIME_CATALOG = ROOT / 'kb' / 'modules' / 'contracts' / 'module-unique-runtime-catalog.csv'
MODULE_SUBSTATS = ROOT / 'kb' / 'modules' / 'tables' / 'module-substats.csv'
MANUAL_INPUTS = ROOT / 'input' / 'manual_inputs.yaml'


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
def _module_unique_effect_map() -> dict[str, dict]:
    strengths: dict[str, dict] = {}
    with MODULE_UNIQUE_EFFECTS.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            strengths[_slug_text(str(row['module']).strip())] = dict(row)
    descriptions: dict[str, dict] = {}
    with MODULE_UNIQUE_RUNTIME_CATALOG.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            descriptions[_slug_text(str(row['module_name']).strip())] = dict(row)
    merged: dict[str, dict] = {}
    for key in set(strengths) | set(descriptions):
        merged[key] = {**descriptions.get(key, {}), **strengths.get(key, {})}
    return merged


@lru_cache(maxsize=1)
def _module_substat_lookup() -> dict[tuple[str, str], list[dict[str, object]]]:
    lookup: dict[tuple[str, str], list[dict[str, object]]] = {}
    with MODULE_SUBSTATS.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            slot = str(row.get('slot') or '').strip().lower()
            substat = _normalize_module_substat_name(row.get('substat'))
            rarity = str(row.get('rarity') or '').strip()
            unit = str(row.get('unit') or '').strip().lower()
            try:
                value = float(str(row.get('value') or '').strip())
            except ValueError:
                continue
            lookup.setdefault((slot, substat), []).append(
                {
                    'rarity': rarity,
                    'unit': unit,
                    'value': value,
                }
            )
    return lookup


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


@lru_cache(maxsize=1)
def _perk_entity_map() -> dict[str, dict]:
    with PERK_ENTITY_REGISTRY.open(newline='', encoding='utf-8') as handle:
        return {str(row['perk_id']).strip(): row for row in csv.DictReader(handle)}


@lru_cache(maxsize=1)
def _card_effect_map() -> dict[str, str]:
    with CARD_EFFECT_REGISTRY.open(newline='', encoding='utf-8') as handle:
        rows = {}
        for row in csv.DictReader(handle):
            if str(row.get('layer') or '').strip() != 'base_card':
                continue
            rows[str(row.get('card_id') or '').strip()] = str(row.get('effect_name') or '').strip()
        return rows


@lru_cache(maxsize=1)
def _card_value_map() -> dict[tuple[str, int], str]:
    with CARD_BASE_LADDERS.open(newline='', encoding='utf-8') as handle:
        rows: dict[tuple[str, int], str] = {}
        for row in csv.DictReader(handle):
            key = (str(row.get('card_id') or '').strip(), int(row.get('base_level') or 0))
            raw_value = str(row.get('raw_value') or '').strip()
            unit = str(row.get('unit') or '').strip()
            rows[key] = f'{raw_value} {unit}'.strip()
        return rows


@lru_cache(maxsize=1)
def _card_mastery_value_map() -> dict[tuple[str, int], tuple[float, str]]:
    return _load_card_mastery_values()


@lru_cache(maxsize=1)
def _perk_effect_map() -> dict[str, dict]:
    path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-effect-registry.csv'
    rows: dict[str, dict] = {}
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            perk_id = str(row.get('perk_id') or '').strip()
            if not perk_id or str(row.get('effect_index') or '').strip() != '1':
                continue
            rows[perk_id] = dict(row)
    return rows


@lru_cache(maxsize=1)
def _module_unique_value_map() -> dict[tuple[str, str], tuple[float, str]]:
    return _load_module_unique_effect_values()


@lru_cache(maxsize=1)
def _manual_banned_perks() -> set[str]:
    try:
        payload = yaml.safe_load(MANUAL_INPUTS.read_text(encoding='utf-8')) or {}
    except Exception:
        return set()
    banned_ids = {
        str(item).strip()
        for item in (payload.get('perk_config') or {}).get('banned_perk_ids', [])
        if str(item).strip()
    }
    banned_names = {
        str(item).strip()
        for item in (payload.get('perk_policy') or {}).get('banned_perks', [])
        if str(item).strip()
    }
    by_name = {row.get('perk_name', ''): perk_id for perk_id, row in _perk_entity_map().items()}
    for name in banned_names:
        perk_id = by_name.get(name)
        if perk_id:
            banned_ids.add(perk_id)
    return banned_ids


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


def _init_state() -> None:
    st.session_state.setdefault('snapshot_dirs', {DEFAULT_OUT.name: str(DEFAULT_OUT)})
    st.session_state.setdefault('active_out_dir', str(DEFAULT_OUT))
    st.session_state.setdefault('fast_checkpoint_result', None)


def _register_snapshot(out_dir: Path, *, preset: str, state_mode: str, perk_state: str) -> None:
    label = snapshot_label(preset=preset, state_mode=state_mode, perk_state=perk_state, out_dir=out_dir)
    st.session_state['snapshot_dirs'][label] = str(out_dir)
    st.session_state['active_out_dir'] = str(out_dir)


def _run_request(request: PipelineRunRequest) -> None:
    result = execute_pipeline(request)
    _register_snapshot(result.out_dir, preset=request.preset, state_mode=request.state_mode, perk_state=request.perk_state)


def _run_default_verification_set(base_request: PipelineRunRequest) -> None:
    for result in build_verification_snapshot_set(base_request):
        _register_snapshot(
            result.out_dir,
            preset=result.request.preset,
            state_mode=result.request.state_mode,
            perk_state=result.request.perk_state,
        )


def _sidebar() -> PipelineRunRequest:
    st.sidebar.header('Run Controls')
    ids_path = Path(st.sidebar.text_input('IDS path', value=str(DEFAULT_IDS)))
    out_dir = Path(st.sidebar.text_input('Output dir', value=st.session_state['active_out_dir']))
    manual_inputs_raw = st.sidebar.text_input('Manual inputs override', value='')
    manual_inputs = Path(manual_inputs_raw) if manual_inputs_raw.strip() else None
    preset = st.sidebar.selectbox('Preset', options=['Farming', 'Tourney', 'Milestone'], index=0)
    state_mode = st.sidebar.selectbox('State mode', options=['start_of_run', 'max_progression', 'account_baseline', 'gem_respec'], index=1)
    perk_mode = st.sidebar.selectbox('Perk mode', options=['max_progression_policy', 'none', 'runtime_timeline'], index=0)
    perk_state = st.sidebar.selectbox('Perk state', options=['auto', 'on', 'off'], index=0)
    include_slow_audits = st.sidebar.checkbox('Include slow audits', value=False)
    request = PipelineRunRequest(
        ids=ids_path,
        out=out_dir,
        preset=preset,
        state_mode=state_mode,
        manual_inputs=manual_inputs,
        perk_mode=perk_mode,
        include_slow_audits=include_slow_audits,
        perk_state=perk_state,
    )
    if st.sidebar.button('Run current request', use_container_width=True):
        _run_request(request)
    if st.sidebar.button('Build default verification set', use_container_width=True):
        _run_default_verification_set(request)
    snapshot_labels = list(st.session_state['snapshot_dirs'].keys())
    selected_label = st.sidebar.selectbox('Active snapshot', options=snapshot_labels, index=max(0, snapshot_labels.index(next((label for label, path in st.session_state['snapshot_dirs'].items() if path == st.session_state['active_out_dir']), snapshot_labels[0]))))
    st.session_state['active_out_dir'] = st.session_state['snapshot_dirs'][selected_label]
    return request


def _render_pipeline(trace_payload: dict, diagnostics: dict) -> None:
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

    with st.expander('Execution Path', expanded=True):
        st.json(execution)

    stage_df = pipeline_stages_frame(trace_payload)
    if not stage_df.empty:
        st.subheader('Stages')
        st.dataframe(stage_df, use_container_width=True, hide_index=True)
        for stage in trace_payload.get('stages') or []:
            title = f"{stage.get('title', stage.get('stage_id'))} - {stage.get('owner_module', '')}"
            with st.expander(title):
                st.write(f"`{stage.get('entry_function', '')}`")
                st.json(stage)

    st.subheader('Cache')
    st.json(
        {
            'cache_fingerprint': execution.get('cache_fingerprint'),
            'cache_validation': execution.get('cache_validation'),
            'mutated_workshop_keys': ((execution.get('incremental_plan') or {}).get('mutated_source_nodes')),
            'reused_cached_reference_statbook': execution.get('cache_status') == 'hit',
        }
    )

    st.subheader('Incremental Plan')
    st.json(execution.get('incremental_plan') or {})

    st.subheader('Runtime Consumers')
    st.json(
        {
            'runtime_consumers': execution.get('runtime_consumers') or [],
            'runtime_publication': execution.get('runtime_publication'),
        }
    )

    with st.expander('Advanced raw details'):
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


def _stats_section_name(surface_id: str) -> str:
    label = surface_id.split('::', 1)[-1]
    workshop_offense_surfaces = {
        'state::tower.attack_speed',
        'state::tower.crit_chance_pct',
        'state::tower.crit_multiplier',
        'state::tower.damage',
        'state::tower.damage_per_meter_multiplier',
        'state::tower.multishot_chance_pct',
        'state::tower.multishot_targets',
        'state::tower.range_m',
        'state::tower.rapid_fire_chance_pct',
        'state::tower.rapid_fire_duration_seconds',
        'state::tower.bounce_shot_chance_pct',
        'state::tower.bounce_shot_range_m',
        'state::tower.bounce_shot_targets',
        'state::tower.supercrit_chance_pct',
        'state::tower.supercrit_multiplier',
        'state::tower.rend_armor_chance_pct',
        'state::tower.rend_armor_multiplier',
        'state::tower.ultimate_damage_multiplier',
    }
    workshop_defense_surfaces = {
        'state::tower.hp',
        'state::tower.regen',
        'state::tower.defense_pct',
        'state::tower.defense_absolute',
        'state::tower.thorns_damage_pct',
        'state::tower.lifesteal_pct',
        'state::tower.knockback_chance_pct',
        'state::tower.knockback_force',
        'state::tower.orb_count',
        'state::tower.orb_speed_rpm',
        'state::tower.orb_size_multiplier',
        'state::tower.shockwave_interval_seconds',
        'state::tower.shockwave_size_m',
        'state::tower.death_defy_chance_pct',
        'state::tower.land_mine_chance_pct',
        'state::tower.land_mine_damage',
        'state::tower.land_mine_radius_m',
    }
    workshop_utility_surfaces = {
        'state::tower.package_chance_pct',
        'state::tower.max_recovery_multiplier',
        'state::tower.recovery_amount_pct',
        'state::tower.recovery_package_multiplier',
        'state::tower.enemy_attack_level_skip_pct',
        'state::tower.enemy_health_level_skip_pct',
        'state::tower.free_attack_upgrade_chance_pct',
        'state::tower.free_defense_upgrade_chance_pct',
        'state::tower.free_utility_upgrade_chance_pct',
        'state::tower.free_upgrade_multiplier',
    }
    if surface_id.startswith('state::cards.'):
        return 'Cards'
    if surface_id.startswith('state::uw.'):
        return 'Ultimate Weapons'
    if surface_id.startswith('state::bot.'):
        return 'Bots'
    if surface_id.startswith('state::guardian.'):
        return 'Guardians'
    if surface_id.startswith('state::module.'):
        return 'Modules'
    if surface_id.startswith('state::wall.'):
        return 'Wall'
    if surface_id.startswith('state::economy.'):
        return 'Economy'
    if surface_id in workshop_offense_surfaces:
        return 'Workshop Offense'
    if surface_id in workshop_defense_surfaces:
        return 'Workshop Defense'
    if surface_id in workshop_utility_surfaces:
        return 'Workshop Utility'
    if surface_id.startswith('support_surface::') or surface_id.startswith('derived::'):
        if surface_id.startswith(('derived::edamage', 'derived::edamage_ep', 'support_surface::timing.gcomp_')):
            return 'Workshop Offense'
        if surface_id.startswith(('derived::ehp', 'derived::ehp_ep')):
            return 'Workshop Defense'
        if surface_id.startswith(('derived::eecon', 'derived::economy')) or surface_id == 'support_surface::free_upgrade_multiplier':
            return 'Workshop Utility'
        return 'Derived / Support'
    if surface_id.startswith('context::'):
        return 'Context'
    if surface_id.startswith('state::tower.'):
        return 'Workshop Utility'
    return 'Other'


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

    st.dataframe(frame.style.apply(_style_selected, axis=1), use_container_width=True, hide_index=True)


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


def _render_perks_table(account_state: dict, *, selected_preset: str, stat_inputs_payload: object) -> None:
    st.subheader('Perks')
    perk_rows = _perk_entity_map()
    qe_perk_rows = _perk_rows_from_qe(stat_inputs_payload, selected_preset=selected_preset)
    if not qe_perk_rows:
        fallback_preset = account_state.get('active_perk_preset') or selected_preset
        qe_perk_rows = _perk_rows_from_qe(stat_inputs_payload, selected_preset=fallback_preset)
    standard_bonus, tradeoff_bonus = _perk_lab_bonus_summary(stat_inputs_payload)
    cols = st.columns(2)
    cols[0].metric('Standard Perk Bonus lab', f'{standard_bonus:g}%' if standard_bonus is not None else 'n/a')
    cols[1].metric('Trade-off Perk Bonus lab', f'{tradeoff_bonus:g}%' if tradeoff_bonus is not None else 'n/a')
    preset_for_rows = selected_preset if (account_state.get('perk_presets') or {}).get(selected_preset) is not None else (account_state.get('active_perk_preset') or selected_preset)
    selections = {
        row.get('perk_id'): int(row.get('picks') or 0)
        for row in ((account_state.get('perk_presets') or {}).get(preset_for_rows) or [])
    }
    banned_ids = _manual_banned_perks()
    perk_entities = _load_perk_entities()
    perk_effects = _load_perk_effects()
    perk_lab_state = {
        'standard_bonus_multiplier': 1.0 + ((standard_bonus or 0.0) / 100.0),
        'tradeoff_bonus_multiplier': 1.0 + ((tradeoff_bonus or 0.0) / 100.0),
    }
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
        perk_meta = perk_entities.get(perk_id) or {}
        max_picks = int(perk_meta.get('max_picks') or 0)
        for effect in (perk_effects.get(perk_id) or []):
            scaled = _scaled_perk_value(
                perk_meta=perk_meta,
                perk_effect_meta=effect,
                perk_id=perk_id,
                operation=str(effect.get('operation') or '').strip(),
                raw_value=str(effect.get('effect_value') or '').strip(),
                picks=max_picks,
                effect_index=str(effect.get('effect_index') or '').strip(),
                perk_lab_state=perk_lab_state,
            )
            formatted = _format_qe_perk_value(scaled, effect.get('operation'))
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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
            st.dataframe(pd.DataFrame(track_rows), use_container_width=True, hide_index=True)
            plus_rows = [
                row for key, row in uw_plus_tracks.items() if key.startswith(f'{uw_name}::')
            ]
            if plus_rows:
                st.dataframe(pd.DataFrame(plus_rows), use_container_width=True, hide_index=True)


def _render_loadout_panel(active_artifacts, *, preset: str, max_progression_rows: dict[str, dict]) -> None:
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
    )
    _render_uw_groups(
        account_state,
        selected_preset=preset,
        max_progression_rows=max_progression_rows,
        statbook_max_progression=active_artifacts.get('statbook_max_progression.json', {}),
        resolved_statbook_rows=_resolved_statbook_row_map(resolved_statbook),
    )


def _render_sectioned_run_stats_table(frame: pd.DataFrame, *, show_raw_ids: bool) -> None:
    frame = frame.copy()
    frame['section'] = frame['surface_id'].map(_stats_section_name)
    ordered_sections = [
        'Workshop Offense',
        'Workshop Defense',
        'Workshop Utility',
        'Wall',
        'Economy',
        'Ultimate Weapons',
        'Bots',
        'Modules',
        'Cards',
        'Guardians',
        'Derived / Support',
        'Context',
        'Other',
    ]
    for section_name in ordered_sections:
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
        st.dataframe(section_df[table_columns], use_container_width=True, hide_index=True)


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
        use_container_width=True,
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
    st.dataframe(pd.DataFrame(summary_rows, columns=['field', 'value']), use_container_width=True, hide_index=True)

    st.subheader('Contributor Lineage')
    st.dataframe(qe_contributor_rows_frame(row_payload), use_container_width=True, hide_index=True)

    st.subheader('Dependency Trace Summary')
    st.dataframe(qe_trace_summary_frame(trace_payload), use_container_width=True, hide_index=True)

    trace_cols = st.columns(2)
    with trace_cols[0]:
        st.caption('Direct upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='direct_upstream_node_ids'), use_container_width=True, hide_index=True)
        st.caption('Resolved upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='resolved_upstream_node_ids'), use_container_width=True, hide_index=True)
        st.caption('Unresolved upstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='unresolved_upstream_node_ids'), use_container_width=True, hide_index=True)
    with trace_cols[1]:
        st.caption('Direct downstream nodes')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='direct_downstream_node_ids'), use_container_width=True, hide_index=True)
        st.caption('Upstream closure')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='upstream_closure_node_ids'), use_container_width=True, hide_index=True)
        st.caption('Downstream closure')
        st.dataframe(qe_dependency_nodes_frame(trace_payload, field_name='downstream_closure_node_ids'), use_container_width=True, hide_index=True)

    st.subheader('Runtime Trace Steps')
    st.dataframe(qe_trace_steps_frame(trace_payload), use_container_width=True, hide_index=True)

    st.subheader('Active Query-Plan Coverage')
    st.dataframe(qe_plan_coverage_frame(query_plan_payload, preset=preset_name, surface_id=selected_surface), use_container_width=True, hide_index=True)

def _render_stats(active_artifacts, comparison_artifacts: list[tuple[str, object]], request: PipelineRunRequest) -> None:
    st.subheader('Stats')
    run_stats_payload = active_artifacts.get('run_stats.json', {})
    available_presets = sorted(
        set(((run_stats_payload.get('presets') or {}).keys()))
        | set((active_artifacts.get('statbook_start_of_run.json', {}) or {}).keys())
        | set((active_artifacts.get('statbook_max_progression.json', {}) or {}).keys())
    )
    active_preset = request.preset if request.preset in available_presets else (available_presets[0] if available_presets else request.preset)
    preset = st.selectbox('Preset', options=available_presets or [active_preset], index=(available_presets.index(active_preset) if active_preset in available_presets else 0))
    view_mode = st.radio('Stat source', options=['Analysis statbook (all stats)', 'Run stats (fast subset)', 'Analysis statbook (advanced)'], horizontal=True)
    show_changed_only = st.toggle('Changed in max progression only', value=False)
    show_raw_ids = st.toggle('Show raw artifact IDs', value=False)
    search_text = st.text_input('Search stats', value='').strip().lower()

    if view_mode == 'Analysis statbook (all stats)':
        active_df = dual_state_statbook_rows_frame(
            active_artifacts.get('statbook_start_of_run.json', {}),
            active_artifacts.get('statbook_max_progression.json', {}),
            preset=preset,
        )
    elif view_mode == 'Run stats (fast subset)':
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
    if not compare_df.empty:
        compare_subset = compare_df[['surface_id', 'ep_value', 'ep_value_raw', 'compare_preset', 'compare_perk_state', 'status', 'label']].copy()
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

    if view_mode in {'Analysis statbook (all stats)', 'Run stats (fast subset)'}:
        _render_loadout_panel(active_artifacts, preset=preset, max_progression_rows=_max_progression_lookup(active_df))
        filtered_active['ep delta vs max'] = pd.to_numeric(filtered_active.get('max_progression_value'), errors='coerce') - pd.to_numeric(
            filtered_active.get('ep value'),
            errors='coerce',
        )
        _render_sectioned_run_stats_table(filtered_active, show_raw_ids=show_raw_ids)
        with st.expander('Flat all-stats table'):
            table_columns = [
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
            ]
            if show_raw_ids:
                table_columns.insert(3, 'raw_surface_id')
            st.dataframe(filtered_active[table_columns], use_container_width=True, hide_index=True)
    else:
        table_columns = ['group', 'display_label', 'surface_id', 'final_value', 'display_value', 'value_type', 'status', 'contributor_count', 'ep display', 'ep value', 'ep preset', 'ep perks', 'ep status']
        if show_raw_ids:
            table_columns.insert(3, 'raw_surface_id')
        st.dataframe(filtered_active[table_columns], use_container_width=True, hide_index=True)

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
    if st.button('Resolve selected stats via fast checkpoint', use_container_width=True, disabled=not requested_surface_ids):
        fast_result = resolve_fast_checkpoint(
            FastCheckpointRequest(
                ids=request.ids,
                manual_inputs=request.manual_inputs,
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
            if view_mode in {'Analysis statbook (all stats)', 'Run stats (fast subset)'}:
                source_prefix = 'start_of_run' if fast_payload.get('request', {}).get('state_mode') == 'start_of_run' else 'max_progression'
                fast_compare = filtered_active[['surface_id', 'display_label', f'{source_prefix}_display', f'{source_prefix}_value', f'{source_prefix}_status']].copy()
                fast_compare = fast_compare.rename(
                    columns={
                        f'{source_prefix}_display': 'artifact display',
                        f'{source_prefix}_value': 'artifact value',
                        f'{source_prefix}_status': 'artifact status',
                    }
                )
            else:
                fast_compare = filtered_active[['surface_id', 'display_label', 'display_value', 'final_value', 'status']].copy()
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
            st.dataframe(fast_compare, use_container_width=True, hide_index=True)

    if comparison_artifacts:
        st.subheader('Comparison Workbench')
        labels = [label for label, _ in comparison_artifacts]
        selected = st.multiselect('Snapshots to compare', options=labels, default=labels[: min(4, len(labels))])
        comparison_frames = []
        for label, artifacts in comparison_artifacts:
            if label not in selected:
                continue
            frame = dual_state_statbook_rows_frame(
                artifacts.get('statbook_start_of_run.json', {}),
                artifacts.get('statbook_max_progression.json', {}),
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
            st.dataframe(merged, use_container_width=True, hide_index=True)

    selected_surface = st.selectbox('Contributor drilldown surface', options=filtered_active['surface_id'].tolist())
    detail_payload_name = 'statbook_start_of_run.json' if request.state_mode == 'start_of_run' else 'statbook_max_progression.json'
    selected_row = {}
    for raw_surface_id, payload in ((active_artifacts.get(detail_payload_name, {}).get('rows') or {}).items()):
        if normalize_surface_id_to_contract(raw_surface_id) == selected_surface:
            selected_row = payload
            break
    if selected_row:
        st.subheader('Contributor Drilldown')
        st.json(selected_row)


def _render_checks(active_artifacts) -> None:
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
        st.dataframe(pd.DataFrame(family_rows), use_container_width=True, hide_index=True)
    active_unmapped_inputs = diagnostics.get('active_unmapped_inputs') or []
    if active_unmapped_inputs:
        with st.expander('Active unmapped inputs'):
            st.dataframe(pd.DataFrame(active_unmapped_inputs), use_container_width=True, hide_index=True)
    st.subheader('EP Compare')
    st.dataframe(compare_df, use_container_width=True, hide_index=True)
    st.subheader('Line Verification')
    st.dataframe(verification_df, use_container_width=True, hide_index=True)
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
    diagnostics = active_artifacts.get('diagnostics.json', {})
    st.subheader('Input Visibility')
    st.write(f'Active output dir: `{active_out_dir}`')
    st.json(
        {
            'section_names': diagnostics.get('section_names', []),
            'section_row_counts': diagnostics.get('section_row_counts', {}),
            'perk_config_resolution': diagnostics.get('perk_config_resolution', {}),
            'compare_policy': diagnostics.get('compare_situation_policy', {}),
        }
    )
    st.subheader('Manifest and Input Metadata')
    st.json(
        {
            'default_preset': diagnostics.get('default_preset'),
            'state_mode': diagnostics.get('state_mode'),
            'perk_mode': diagnostics.get('perk_mode'),
            'active_card_preset': diagnostics.get('active_card_preset'),
            'active_module_preset': diagnostics.get('active_module_preset'),
            'active_perk_preset': diagnostics.get('active_perk_preset'),
        }
    )


def _render_boss_waves(request: PipelineRunRequest) -> None:
    st.subheader('Boss Waves')
    control_cols = st.columns(4)
    preset_name = control_cols[0].selectbox('Boss preset', options=['Farming', 'Tourney', 'Milestone'], index=['Farming', 'Tourney', 'Milestone'].index(request.preset) if request.preset in {'Farming', 'Tourney', 'Milestone'} else 0)
    tier_number = control_cols[1].number_input('Tier', min_value=1, max_value=18, value=14, step=1)
    end_wave = control_cols[2].number_input('End wave', min_value=10, max_value=100000, value=500, step=10)
    boss_wave_step = control_cols[3].number_input('Boss wave step', min_value=1, max_value=1000, value=10, step=1)
    stop_on_failure = st.toggle('Stop on first failed boss', value=False)

    with st.expander('Runtime assumptions', expanded=False):
        runtime_cols = st.columns(3)
        orb_boss_hit_pct = runtime_cols[0].number_input('Orb boss hit %', min_value=0.0, max_value=100.0, value=2.5, step=0.1)
        orb_boss_hits_per_second = runtime_cols[1].number_input('Orb boss hits / sec', min_value=0.1, max_value=100.0, value=5.0, step=0.1)
        electron_hits_per_second = runtime_cols[2].number_input('Electron hits / sec', min_value=0.1, max_value=100.0, value=5.0, step=0.1)
        runtime_cols_2 = st.columns(3)
        boss_contact_time_seconds = runtime_cols_2[0].number_input('Boss contact time (s)', min_value=0.0, max_value=120.0, value=1.0, step=0.1)
        effective_damage_reduction_pct = runtime_cols_2[1].number_input('Effective DR %', min_value=0.0, max_value=100.0, value=90.0, step=0.1)
        incoming_damage_multiplier = runtime_cols_2[2].number_input('Incoming damage multiplier', min_value=0.0, max_value=100.0, value=1.0, step=0.1)

    bundle = load_inputs(
        ids_path=request.ids,
        manual_inputs_path=request.manual_inputs,
    )
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    initial_state = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=PerkState(wave=0, counts={}, dirty=False),
    )
    config = RunToMaxConfig(
        execution_mode='table_sweep',
        preset_name=preset_name,
        tier_column=f'Tier {int(tier_number)}',
        start_wave=max(1, int(boss_wave_step)),
        end_wave=int(end_wave),
        boss_wave_step=int(boss_wave_step),
        state_mode='start_of_run',
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'orb_boss_hit_pct': orb_boss_hit_pct,
                'orb_boss_hits_per_second': orb_boss_hits_per_second,
                'electron_hits_per_second': electron_hits_per_second,
                'boss_contact_time_seconds': boss_contact_time_seconds,
                'effective_damage_reduction_pct': effective_damage_reduction_pct,
                'incoming_damage_multiplier': incoming_damage_multiplier,
            }
        ),
    )
    frame = pd.DataFrame(
        build_boss_wave_table(
            account_state=account_state,
            initial_projected_state=initial_state,
            config=config,
            stop_on_failure=bool(stop_on_failure),
        )
    )
    if not frame.empty and 'changed_workshop_tracks_last_step' in frame.columns:
        frame['changed_workshop_tracks_last_step'] = frame['changed_workshop_tracks_last_step'].fillna('')
    surviving_rows = frame[frame['survives_boss'] == True] if not frame.empty else frame
    diagnostics = {
        'preset_name': preset_name,
        'tier_column': config.tier_column,
        'boss_wave_step': config.boss_wave_step,
        'row_count': int(len(frame)),
        'max_surviving_wave': int(surviving_rows['display_wave'].max()) if not surviving_rows.empty else 0,
        'state_mode': config.state_mode,
        'checkpoint_mode': 'boss_wave_only',
    }

    summary_cols = st.columns(4)
    summary_cols[0].metric('Rows', diagnostics['row_count'])
    summary_cols[1].metric('Max surviving wave', diagnostics['max_surviving_wave'])
    summary_cols[2].metric('Tier', diagnostics['tier_column'])
    summary_cols[3].metric('Preset', diagnostics['preset_name'])
    st.caption(
        'Rows are stepped only at boss-wave checkpoints. Free upgrades and enemy level skips are accumulated across '
        'the intervening waves using the interval-start resolved values.'
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)
    st.download_button(
        'Download boss-wave CSV',
        data=frame.to_csv(index=False).encode('utf-8'),
        file_name=f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv',
        mime='text/csv',
        use_container_width=True,
    )
    with st.expander('Boss-wave diagnostics'):
        st.json(diagnostics)


def main() -> None:
    st.set_page_config(page_title='TowerSim Incremental Inspector', layout='wide')
    st.title('TowerSim Incremental Inspector')
    st.caption('Pipeline execution understanding, cache visibility, and stat verification workbench.')
    _init_state()
    request = _sidebar()
    active_out_dir = Path(st.session_state['active_out_dir'])
    active_artifacts = load_artifacts(active_out_dir)
    comparison_artifacts = [
        (label, load_artifacts(Path(path)))
        for label, path in st.session_state['snapshot_dirs'].items()
        if Path(path) != active_out_dir
    ]

    inputs_tab, qe_tab, stats_tab, boss_waves_tab, pipeline_tab, checks_tab = st.tabs(['Input', 'QE', 'Stats', 'Boss Waves', 'Pipeline', 'Checks'])
    with inputs_tab:
        _render_inputs(active_artifacts, active_out_dir)
    with qe_tab:
        _render_qe(active_artifacts, request)
    with stats_tab:
        _render_stats(active_artifacts, comparison_artifacts, request)
    with boss_waves_tab:
        _render_boss_waves(request)
    with pipeline_tab:
        _render_pipeline(active_artifacts.get('pipeline_trace.json', {}), active_artifacts.get('diagnostics.json', {}))
    with checks_tab:
        _render_checks(active_artifacts)

    with st.expander('Current request'):
        st.code(json.dumps(request.__dict__, indent=2, default=str))


if __name__ == '__main__':
    main()
