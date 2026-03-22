from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent

def _relpath_str(path_like) -> str:
    p = Path(path_like)
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        try:
            return str(p.relative_to(ROOT))
        except Exception:
            return str(p)

def _json_sanitize(obj):
    if isinstance(obj, Path):
        return _relpath_str(obj)
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, str) and obj.startswith('/'):
        try:
            return _relpath_str(obj)
        except Exception:
            return obj
    return obj

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parsers.ids_parser import parse_ids
from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs, SUPPORTED_STATE_MODES, normalize_state_mode, state_mode_support
from engine.display import (
    _format_display_number,
    annotate_compare_display_fields as _annotate_compare_display_fields,
    annotate_display_fields as _annotate_display_fields,
)
from engine.stat_engine import resolve_stats
from engine.verification import (
    annotate_compare_display_fields as _annotate_compare_display_fields,
    build_compare_status_summary as _build_compare_status_summary,
    build_ep_compare as _build_ep_compare,
    build_line_by_line_verification as _build_line_by_line_verification,
    build_survivability_residue_analysis as _build_survivability_residue_analysis,
    build_survivor_closure_report as _build_survivor_closure_report,
    ensure_compare_authoritative_verdict_fields as _ensure_compare_authoritative_verdict_fields,
    ensure_line_verification_authoritative_verdict_fields as _ensure_line_verification_authoritative_verdict_fields,
)
from optimizer.scorer import compute_optimizer_scores

from models.stat_input import StatInput
from models.statbook import StatBook, StatRow

FORMULA_LEDGER_PATH = ROOT / 'config' / 'destination_formula_ledger.yaml'
LOADOUT_CONFIG_PATH = ROOT / 'input' / 'loadout.json'
PERKS_CONFIG_PATH = ROOT / 'input' / 'perks.json'
PROJECTED_MAX_PERKS_CONFIG_PATH = ROOT / 'input' / 'perks_projected_max.json'


def _load_json_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}




def _perk_config_has_active_preset(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    active = config.get('active_perk_preset')
    presets = config.get('perk_presets') or {}
    return bool(active) and active in presets and bool(presets.get(active))



_PERK_MAX_POLICY_PATH = ROOT / 'input' / 'perks_max_progression_policy.json'


def _load_perk_entity_registry() -> list[dict]:
    path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


def _default_tradeoff_alias_map() -> dict[str, str]:
    return {
        "TO1": "x1.50 Tower Damage, but Bosses Have 8x Health",
        "TO2": "x1.80 coins, but Tower Max Health -70%",
        "TO3": "Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%",
        "TO4": "Enemies Damage -50%, but Tower Damage -50%",
        "TO5": "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3",
        "TO6": "Enemies Speed -40%, But Enemies Damage x2.5",
        "TO7": "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash",
        "TO8": "Tower Health Regen x8.00, But Tower Max Max Health -60%",
        "TO9": "Boss Health -70%, But Boss Speed +50%",
        "TO10": "Lifesteal x2.50, But Knockback force -70%",
    }


def _resolve_policy_banned_perk_names(raw_policy: dict) -> list[str]:
    alias_map = _default_tradeoff_alias_map()
    ordered: list[str] = []
    seen: set[str] = set()
    for alias in list(raw_policy.get("banned_perk_aliases", []) or []):
        key = str(alias).strip().upper()
        name = alias_map.get(key)
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in list(raw_policy.get("banned_perks", []) or []):
        perk_name = str(name).strip()
        if perk_name and perk_name not in seen:
            ordered.append(perk_name)
            seen.add(perk_name)
    return ordered


def _ids_player_value(ids_raw, name: str, default: int = 0) -> int:
    rows = ids_raw.raw_sections.get('Player & Stuff', []) if ids_raw else []
    for row in rows:
        if row and str(row[0]).strip() == name:
            token = str(row[1]).strip() if len(row) > 1 else ''
            try:
                return int(float(token.replace(',', '')))
            except Exception:
                return default
    return default


def _build_generated_max_progression_perk_config(ids_raw, primary_config: dict | None = None, *, default_policy_path: Path = _PERK_MAX_POLICY_PATH) -> tuple[dict, dict]:
    from engine.perk_timeline_generator import generate_timeline, perk_state_at_wave

    primary_config = primary_config or {}
    policy_seed = 42
    target_wave = 50000
    priority_order = []
    first_perk_choice = None
    policy_notes = []
    raw_policy = {}
    policy_banned_names: list[str] = []
    if default_policy_path.exists():
        try:
            raw_policy = json.loads(default_policy_path.read_text(encoding='utf-8'))
            policy_seed = int(raw_policy.get('seed', policy_seed))
            target_wave = int(raw_policy.get('target_wave', target_wave))
            priority_order = list(raw_policy.get('priority_order', []) or [])
            first_perk_choice = raw_policy.get('first_perk_choice')
            policy_banned_names = _resolve_policy_banned_perk_names(raw_policy)
            if raw_policy.get('notes'):
                policy_notes.append(str(raw_policy.get('notes')))
        except Exception as exc:
            policy_notes.append(f'Failed to parse policy file {_relpath_str(default_policy_path)}: {exc}')

    fallback_banned_ids = []
    if PROJECTED_MAX_PERKS_CONFIG_PATH.exists():
        try:
            fallback_cfg = _load_json_config(PROJECTED_MAX_PERKS_CONFIG_PATH)
            fallback_banned_ids = list(fallback_cfg.get('banned_perk_ids') or [])
        except Exception:
            fallback_banned_ids = []
    banned_ids = list(primary_config.get('banned_perk_ids') or fallback_banned_ids)

    entities = _load_perk_entity_registry()
    by_id = {row.get('perk_id'): row for row in entities if row.get('perk_id')}
    by_name = {row.get('perk_name'): row for row in entities if row.get('perk_name')}
    primary_banned_names = [by_id[perk_id]['perk_name'] for perk_id in banned_ids if perk_id in by_id and by_id[perk_id].get('perk_name')]
    banned_names = list(primary_banned_names or policy_banned_names)
    if not banned_ids and banned_names:
        banned_ids = [row.get('perk_id') for row in entities if row.get('perk_name') in set(banned_names) and row.get('perk_id')]

    lab_rows = ids_raw.raw_sections.get('Labs', []) if ids_raw else []
    labs = {}
    for row in lab_rows:
        if row and str(row[0]).strip():
            try:
                labs[str(row[0]).strip()] = int(float(str(row[1]).strip().replace(',', '')))
            except Exception:
                pass

    standard_perk_bonus_level = labs.get('Standard Perks Bonus', 0)
    ids_ban_capacity = _ids_player_value(ids_raw, 'Ban Perks', 0)
    effective_ban_capacity = max(ids_ban_capacity, len(banned_names))
    policy_payload = {
        'seed': policy_seed,
        'target_wave': target_wave,
        'waves_required_lab': int(labs.get('Waves Required', 0) or 0),
        'standard_perk_bonus': float(standard_perk_bonus_level) / 100.0,
        'perk_option_quantity': _ids_player_value(ids_raw, 'Perk Option Quantity', 0),
        'ban_perks_capacity': effective_ban_capacity,
        'banned_perks': banned_names,
        'priority_order': priority_order,
        'first_perk_choice': first_perk_choice,
    }
    policy_runtime_path = ROOT / 'input' / 'perks_max_progression_policy.runtime.json'
    policy_runtime_path.write_text(json.dumps(policy_payload, indent=2), encoding='utf-8')
    timeline, diag = generate_timeline(policy_runtime_path)
    taken_counts = perk_state_at_wave(timeline, policy_payload['target_wave'])
    selections = []
    unknown_names = []
    for perk_name, picks in sorted(taken_counts.items()):
        meta = by_name.get(perk_name)
        if not meta or not meta.get('perk_id'):
            unknown_names.append(perk_name)
            continue
        selections.append({'perk_id': meta['perk_id'], 'picks': int(picks)})
    generated = {
        'perk_presets': {
            'ProjectedMax_AllAllowedExceptBanned': selections,
        },
        'active_perk_preset': 'ProjectedMax_AllAllowedExceptBanned',
        'banned_perk_ids': banned_ids,
        'notes': 'Generated from perk timeline policy + IDS-backed perk controls; this preset is authoritative for max_progression when primary perk config has no active preset.',
        'generator': {
            'policy_file': _relpath_str(default_policy_path),
            'runtime_policy_file': _relpath_str(policy_runtime_path),
            'waves_required_lab': policy_payload['waves_required_lab'],
            'standard_perk_bonus_level': standard_perk_bonus_level,
            'perk_option_quantity': policy_payload['perk_option_quantity'],
            'ban_perks_capacity_ids': ids_ban_capacity,
            'ban_perks_capacity_effective': policy_payload['ban_perks_capacity'],
            'target_wave': policy_payload['target_wave'],
            'seed': policy_payload['seed'],
            'priority_order': priority_order,
            'first_perk_choice': first_perk_choice,
            'banned_perks_effective': banned_names,
            'banned_perk_aliases': list(raw_policy.get('banned_perk_aliases', []) or []),
            'unknown_generated_perk_names': unknown_names,
            'timeline_file': 'input/perks_projected_max.timeline.json',
            'final_state_file': 'input/perks_projected_max.final_state.json',
            'diagnostics_file': 'input/perks_projected_max.diagnostics.json',
        }
    }
    (ROOT / 'input' / 'perks_projected_max.timeline.json').write_text(json.dumps(timeline, indent=2), encoding='utf-8')
    (ROOT / 'input' / 'perks_projected_max.final_state.json').write_text(json.dumps({'target_wave': policy_payload['target_wave'], 'taken_counts': taken_counts}, indent=2), encoding='utf-8')
    (ROOT / 'input' / 'perks_projected_max.diagnostics.json').write_text(json.dumps(diag, indent=2), encoding='utf-8')
    PROJECTED_MAX_PERKS_CONFIG_PATH.write_text(json.dumps(generated, indent=2), encoding='utf-8')
    metadata = {
        'requested_perks_path': str(PERKS_CONFIG_PATH),
        'resolved_perks_path': str(PROJECTED_MAX_PERKS_CONFIG_PATH),
        'fallback_applied': True,
        'fallback_reason': 'max_progression_generated_from_timeline_policy',
        'generation_policy_path': str(default_policy_path),
        'generated_timeline_path': str(ROOT / 'input' / 'perks_projected_max.timeline.json'),
        'generated_diagnostics_path': str(ROOT / 'input' / 'perks_projected_max.diagnostics.json'),
        'generated_runtime_policy_path': str(policy_runtime_path),
    }
    return generated, metadata

def _resolve_perk_config(path: Path, state_mode: str, ids_raw=None) -> tuple[dict, dict]:
    primary = _load_json_config(path)
    metadata = {
        'requested_perks_path': str(path),
        'resolved_perks_path': str(path),
        'fallback_applied': False,
        'fallback_reason': None,
    }
    if state_mode == 'max_progression' and not _perk_config_has_active_preset(primary):
        try:
            generated, gen_meta = _build_generated_max_progression_perk_config(ids_raw, primary)
            return generated, gen_meta
        except Exception as exc:
            metadata['generation_error'] = str(exc)
            fallback = _load_json_config(PROJECTED_MAX_PERKS_CONFIG_PATH)
            if _perk_config_has_active_preset(fallback):
                metadata.update({
                    'resolved_perks_path': str(PROJECTED_MAX_PERKS_CONFIG_PATH),
                    'fallback_applied': True,
                    'fallback_reason': 'max_progression_requested_but_timeline_generation_failed_and_static_projected_max_used',
                })
                return fallback, metadata
    return primary, metadata

def _load_formula_ledger(path: Path) -> dict:
    if not path.exists():
        return {'version': 0, 'policy': {}, 'surfaces': {}}
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault('version', 0)
    data.setdefault('policy', {})
    data.setdefault('surfaces', {})
    return data


def _formula_contract(ledger: dict, destination: str) -> dict:
    surface = dict((ledger.get('surfaces') or {}).get(destination) or {})
    surface.setdefault('formula_class', 'unclassified')
    surface.setdefault('publish_policy', 'allow')
    surface.setdefault('compare_policy', 'normal')
    surface.setdefault('rationale', '')
    return surface


def _normalize_compare_values(destination: str, compare_policy: str, package_value, ep_value):
    pkg = package_value
    ep = ep_value
    notes = []
    if compare_policy == 'normalize_percent_scale' and ep is not None:
        if 0 <= ep <= 2.0:
            ep = ep * 100.0
            notes.append('ep_decimal_fraction_scaled_to_percent_points')
    return pkg, ep, notes


def _build_publishable_statbook(statbook_dict: dict, formula_ledger: dict) -> dict:
    from dataclasses import replace
    out = copy.deepcopy(statbook_dict)
    rows = out.get('rows', {})
    blocked = []
    for destination, row in rows.items():
        contract = _formula_contract(formula_ledger, destination)
        row.setdefault('formula_contract', contract)
        row.setdefault('publishable', True)
        if destination.startswith('raw::'):
            row['publishable'] = False
            row['publish_notes'] = 'Trace-only raw surface.'
            continue
        if contract.get('publish_policy') == 'block' and row.get('status') == 'resolved':
            row['publishable'] = False
            row['publish_block_reason'] = 'blocked_by_formula_ledger'
            row['status'] = 'blocked_formula_pending'
            note = row.get('notes') or ''
            row['notes'] = (note + ' | ' if note else '') + 'Blocked from publish by destination formula ledger pending exact formula closure.'
            row['final_value'] = None
            blocked.append(destination)
        elif row.get('status') != 'resolved':
            row['publishable'] = False
    out.setdefault('diagnostics', {})['publishable_blocked_destinations'] = blocked
    out['diagnostics']['publishable_blocked_count'] = len(blocked)
    out['diagnostics']['formula_ledger_version'] = formula_ledger.get('version')
    out['diagnostics']['oracle_policy'] = 'forbidden_for_publish'
    return out

def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0



COMPARE_PRESET_OVERRIDES = {
    'canonical_stat::tower_attack_speed': 'Tourney',
    'canonical_stat::tower_crit_chance_pct': 'Tourney',
    'canonical_stat::tower_crit_multiplier': 'Tourney',
    'canonical_stat::tower_range_m': 'Tourney',
    'canonical_stat::tower_damage_per_meter_multiplier': 'Tourney',
    'canonical_stat::tower_multishot_chance_pct': 'Tourney',
    'canonical_stat::tower_multishot_targets': 'Tourney',
    'canonical_stat::tower_rapid_fire_chance_pct': 'Tourney',
    'canonical_stat::tower_rapid_fire_duration_seconds': 'Tourney',
    'canonical_stat::tower_bounce_shot_chance_pct': 'Tourney',
    'canonical_stat::tower_bounce_shot_targets': 'Tourney',
    'canonical_stat::tower_supercrit_chance_pct': 'Tourney',
    'canonical_stat::tower_supercrit_multiplier': 'Tourney',
    'canonical_stat::tower_damage': 'Tourney',
    'canonical_stat::package_chance_pct': 'Tourney',
}

COMPARE_SITUATION_OVERRIDES = {
    'canonical_stat::tower_damage': {'preset': 'Tourney', 'perk_state': 'off', 'ep_run_state': 'tournament_perks_off'},
    'canonical_stat::package_chance_pct': {'preset': 'Tourney', 'perk_state': 'off', 'ep_run_state': 'tournament_perks_off'},
    'canonical_stat::tower_hp': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::tower_regen': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::tower_defense_absolute': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::wall_hp': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::wall_regen': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::coin_kill_multiplier': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    'canonical_stat::coins_per_kill_bonus': {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
}

COMPARE_DESTINATION_RUNTIME_CARD_FACETS = {
    'canonical_stat::tower_damage': {
        'Berserker': 'conditional_runtime_card__berserker_damage',
    },
}

def _load_lineage_backed_run_perk_destinations() -> set[str]:
    from compilers.stat_input_compiler import _load_perk_effects, PERK_TARGET_DESTINATION_OVERRIDES
    from engine.query_routing import compiler_routing_indexes

    perk_effects = _load_perk_effects()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()
    destinations: set[str] = set()
    for effects in perk_effects.values():
        for effect in effects:
            if str(effect.get('scope', '')).strip() != 'run':
                continue
            target_stat_id = str(effect.get('target_stat_id', '')).strip()
            if not target_stat_id:
                continue
            destination_object_type = None
            destination_id = None
            if target_stat_id in PERK_TARGET_DESTINATION_OVERRIDES:
                destination_object_type, destination_id = PERK_TARGET_DESTINATION_OVERRIDES[target_stat_id]
            elif target_stat_id in canon_stats:
                destination_object_type, destination_id = 'canonical_stat', target_stat_id
            else:
                alias_slug = _slug(target_stat_id.replace('_', ' '))
                alias_match = alias_index.get(alias_slug)
                if alias_match is not None:
                    destination_object_type, destination_id = alias_match
            if destination_object_type == 'canonical_stat' and destination_id:
                destinations.add(f'canonical_stat::{destination_id}')
    return destinations


COMPARE_DESTINATION_RUN_PERK_FACETS = {
    destination: ['run_perks']
    for destination in sorted(_load_lineage_backed_run_perk_destinations())
}

COMPARE_DESTINATION_TRANSITIVE_DEPENDENCIES = {
    'canonical_stat::wall_hp': ['canonical_stat::tower_hp'],
    'canonical_stat::wall_regen': ['canonical_stat::tower_regen'],
}

PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS = {
    ('canonical_stat::tower_damage', 'Berserker'): {
        'multiplier': 8.0,
        'note': 'assumed_maxed_berserker_x8_under_max_progression',
    },
}

PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS = {
    ('canonical_stat::tower_damage', 'Project Funding'): {
        'cash': 50_000_000_000.0,
        'note': 'assumed_project_funding_at_cash_50b_under_max_progression',
    },
}

PROJECT_FUNDING_RARITY_COEFFICIENTS = {
    'Epic': 0.125,
    'Legendary': 0.25,
    'Mythic': 0.50,
    'Ancestral': 1.00,
}


def _compare_preset_for_destination(destination: str, default_preset: str = 'Farming') -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation and situation.get('preset'):
        return situation['preset']
    return COMPARE_PRESET_OVERRIDES.get(destination, default_preset)


def _compare_perk_state_for_preset(preset: str, default_perk_state: str, forced_by_preset: dict | None = None, destination: str | None = None) -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination or '')
    if situation and situation.get('perk_state') is not None:
        return _normalize_perk_state(situation['perk_state'])
    forced_by_preset = forced_by_preset or {}
    if preset in forced_by_preset:
        return _normalize_perk_state(forced_by_preset[preset])
    if preset == 'Tourney':
        return 'off'
    return _normalize_perk_state(default_perk_state)



def _compare_state_key_for_destination(destination: str, default_preset: str = 'Farming') -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation:
        preset = situation.get('preset', _compare_preset_for_destination(destination, default_preset))
        perk_state = _normalize_perk_state(situation.get('perk_state', 'auto'))
        return f'{preset}__perks_{perk_state}'
    preset = _compare_preset_for_destination(destination, default_preset)
    return preset

def _ep_stage_context_for_destination(destination: str, package_stage_context: dict | None = None) -> dict:
    package_stage_context = package_stage_context or {}
    preset = _compare_preset_for_destination(destination, package_stage_context.get('default_compare_preset', 'Farming'))
    offense_surface = preset == 'Tourney'

    package_state_mode = package_stage_context.get('state_mode', 'start_of_run')
    perk_materialized_by_preset = package_stage_context.get('perk_materialized_by_preset') or {}
    perk_state_by_preset = package_stage_context.get('perk_state_by_preset') or {}
    preset_perk_state = _compare_perk_state_for_preset(preset, package_stage_context.get('perk_state', 'auto'), package_stage_context.get('forced_preset_perk_states', {}), destination)
    perk_support_enabled = bool(perk_materialized_by_preset.get(preset, package_stage_context.get('perk_materialized')))
    active_cards_by_preset = package_stage_context.get('active_cards_by_preset') or {}
    preset_active_cards = set(active_cards_by_preset.get(preset) or [])

    supports_max_progression = package_state_mode == 'max_progression'
    supports_max_workshop = package_state_mode == 'max_progression'
    supports_run_perks = perk_support_enabled

    unsupported_facets = []
    notes = []

    if not supports_max_progression:
        unsupported_facets.append('max_progression')
        notes.append('EP export is max progression rather than the current package progression state.')
    if not supports_max_workshop:
        unsupported_facets.append('max_workshop')
        notes.append('EP export assumes max workshop rather than the current package workshop state.')
    destination_run_perk_facets = list(COMPARE_DESTINATION_RUN_PERK_FACETS.get(destination, []))
    if not offense_surface and not supports_run_perks:
        transitive_dependencies = COMPARE_DESTINATION_TRANSITIVE_DEPENDENCIES.get(destination, [])
        if any(dep in COMPARE_DESTINATION_RUN_PERK_FACETS for dep in transitive_dependencies):
            destination_run_perk_facets.append('run_perks')
        if destination_run_perk_facets:
            unsupported_facets.extend(sorted(set(destination_run_perk_facets)))
            notes.append('EP surface depends on perk-affected stats that are not materialized in the current package run.')

    runtime_card_facets = COMPARE_DESTINATION_RUNTIME_CARD_FACETS.get(destination, {})
    for card_name, facet in runtime_card_facets.items():
        if card_name not in preset_active_cards:
            continue
        assumption = PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS.get((destination, card_name))
        if package_state_mode == 'max_progression' and assumption:
            notes.append(f'Projected compare assumes {card_name} is maxed under max progression using compare-only runtime normalization.')
            continue
        unsupported_facets.append(facet)
        notes.append(f'EP surface may include conditional runtime card state from {card_name}, which is not materialized in the package compare path.')

    if package_state_mode == 'max_progression':
        package_progression_state = 'projected_max_progression'
        package_workshop_state = 'projected_max_workshop'
    else:
        package_progression_state = 'current_ids_snapshot'
        package_workshop_state = 'current_ids_workshop'

    if offense_surface:
        package_run_state = f'{preset.lower()}_perks_off'
    elif supports_run_perks:
        package_run_state = f'{preset.lower()}_perks_on'
    else:
        package_run_state = f'{preset.lower()}_perks_off'

    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation and situation.get('ep_run_state'):
        ep_run_state = situation['ep_run_state']
    elif preset == 'Tourney':
        ep_run_state = 'tournament_perks_off'
    else:
        ep_run_state = 'farming_or_milestone_perk_state_unspecified' if preset_perk_state == 'auto' else f'{preset.lower()}_perks_{preset_perk_state}'

    return {
        'compare_preset': preset,
        'compare_perk_state': preset_perk_state,
        'ep_progression_state': 'max_progression',
        'ep_workshop_state': 'max_workshop',
        'ep_run_state': ep_run_state,
        'package_progression_state': package_progression_state,
        'package_workshop_state': package_workshop_state,
        'package_run_state': package_run_state,
        'unsupported_facets': unsupported_facets,
        'notes': notes,
    }

DISPLAY_SUFFIXES = [
    (1e24, 'S'),
    (1e21, 's'),
    (1e18, 'Q'),
    (1e15, 'q'),
    (1e12, 'T'),
    (1e9, 'B'),
    (1e6, 'M'),
    (1e3, 'k'),
]


def _trim_decimal_string(text: str) -> str:
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _format_display_number(value) -> str | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    sign = '-' if v < 0 else ''
    av = abs(v)
    for threshold, suffix in DISPLAY_SUFFIXES:
        if av >= threshold:
            scaled = av / threshold
            decimals = 2 if scaled < 10 else (1 if scaled < 100 else 0)
            txt = _trim_decimal_string(f"{scaled:.{decimals}f}")
            return f"{sign}{txt}{suffix}"
    if av == int(av):
        return f"{int(v)}"
    return _trim_decimal_string(f"{v:.3f}")


def _format_display_value(value, value_type: str | None) -> str | None:
    if value is None:
        return None
    vt = value_type or ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if vt in {'pct', 'percent_display'}:
        num = _format_display_number(value)
        return f"{num}%" if num is not None else str(value)
    if vt in {'multiplier', 'multiplier_display'}:
        num = _format_display_number(value)
        return f"x{num}" if num is not None else f"x{value}"
    return _format_display_number(value) or str(value)


def _annotate_display_fields(statbook_dict: dict) -> None:
    for row in statbook_dict.get('rows', {}).values():
        row['display_value'] = _format_display_value(row.get('final_value'), row.get('value_type'))
        for contributor in row.get('contributors', []):
            contributor['display_value'] = _format_display_value(contributor.get('value'), contributor.get('value_type'))


def _build_tower_regen_closure_report(ep_compare: dict) -> dict:
    dest = 'canonical_stat::tower_regen'
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []
    multiplier_product = 1.0
    workshop_base = None
    ledger = []
    for c in contributors:
        v = c.get('value')
        try:
            vf = float(v)
        except Exception:
            vf = None
        family = c.get('source_family')
        value_type = c.get('value_type')
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and value_type == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family in {'lab', 'card', 'perk'}:
            factor = vf if vf > 1.0 else 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            multiplier_product *= factor
        ledger.append({
            'source_family': family,
            'source_name': c.get('source_name'),
            'preset_name': c.get('preset_name'),
            'raw_value': v,
            'value_type': value_type,
            'applied_factor': factor,
        })
    recomputed = None if workshop_base is None else workshop_base * multiplier_product
    ep_value = row.get('ep_value')
    required_missing_multiplier = None
    if isinstance(recomputed, (int, float)) and isinstance(ep_value, (int, float)) and recomputed:
        required_missing_multiplier = ep_value / recomputed
    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': row.get('package_value'),
        'ep_value': ep_value,
        'relative_delta_pct': row.get('relative_delta_pct'),
        'workshop_base': workshop_base,
        'multiplier_product': multiplier_product,
        'recomputed_package_value': recomputed,
        'required_missing_multiplier_to_match_ep': required_missing_multiplier,
        'contributors': ledger,
    }



def _build_tower_regen_ep_semantic_gap_report(ep_compare: dict) -> dict:
    dest = 'canonical_stat::tower_regen'
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    contributor_meta = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor
        contributor_meta[key] = c

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    ep_value = row.get('ep_value')
    package_value = row.get('package_value')
    package_from_factors = _recompute(current_factors)

    standard_key = 'perk::x1.75 Health Regen'
    tradeoff_key = 'perk::Tower Health Regen x8.00, But Tower Max Max Health -60%'
    enhancement_key = 'enhancement::Health Regen +'

    current_standard = current_factors.get(standard_key)
    current_tradeoff = current_factors.get(tradeoff_key)
    current_enhancement = current_factors.get(enhancement_key)

    ep_standard = None if current_standard is None else (1.0 + 0.75 * 5.0) * (1.0 + 0.01 * 25.0)
    ep_tradeoff = None if current_tradeoff is None else 8.0 * (1.0 + 0.01 * 10.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario(
        'current_package_semantics',
        {},
        'Current calculator semantics: standard perk and trade-off perk improve the delta only; enhancement handled as direct multiplier row.'
    )

    if ep_standard is not None:
        add_scenario(
            'ep_standard_perk_semantics_only',
            {standard_key: ep_standard},
            'EP EPH_REGEN formula multiplies the full perk result by Standard Perks Bonus rather than scaling only the perk delta.'
        )

    if ep_tradeoff is not None:
        add_scenario(
            'ep_tradeoff_semantics_only',
            {tradeoff_key: ep_tradeoff},
            'EP EPH_REGEN formula applies Improve Trade-Off Perks to the full x8 regen multiplier rather than scaling only the +7 delta.'
        )

    if ep_standard is not None and ep_tradeoff is not None:
        add_scenario(
            'ep_perk_semantics_bundle',
            {standard_key: ep_standard, tradeoff_key: ep_tradeoff},
            'Apply both EP-style perk semantics while leaving the rest of the calculator unchanged.'
        )
        bundle_value = scenarios[-1]['package_value']
        residual_after_bundle = scenarios[-1]['required_residual_multiplier_to_match_ep']
    else:
        bundle_value = None
        residual_after_bundle = None

    inferred_wse_level_after_bundle = None
    integer_wse_candidate = None
    integer_wse_multiplier = None
    if isinstance(residual_after_bundle, (int, float)) and residual_after_bundle > 0:
        inferred_wse_level_after_bundle = (residual_after_bundle - 1.0) / 0.01
        integer_wse_candidate = round(inferred_wse_level_after_bundle)
        integer_wse_multiplier = 1.0 + 0.01 * integer_wse_candidate
        add_scenario(
            'ep_perk_semantics_plus_inferred_wse',
            {
                standard_key: ep_standard,
                tradeoff_key: ep_tradeoff,
                enhancement_key: (current_enhancement or 1.0) * integer_wse_multiplier,
            },
            'Model the remaining residual as an EP-only WSE multiplier applied on top of the existing enhancement multiplier. This is a semantic audit scenario, not a calculator truth claim.'
        )

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': package_from_factors,
        'current_factors': {
            'standard_perk_factor': current_standard,
            'tradeoff_regen_factor': current_tradeoff,
            'enhancement_factor': current_enhancement,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'ep_tradeoff_regen_factor': ep_tradeoff,
            'residual_multiplier_after_ep_perk_semantics': residual_after_bundle,
            'inferred_wse_level_after_ep_perk_semantics': inferred_wse_level_after_bundle,
            'nearest_integer_wse_level_candidate': integer_wse_candidate,
            'nearest_integer_wse_multiplier': integer_wse_multiplier,
        },
        'scenarios': scenarios,
        'assessment': {
            'best_fit_hypothesis': 'EP regen delta is largely explained by EP-specific semantics: full-result standard perk scaling, full-result trade-off scaling, and an unresolved WSE multiplier near +8%.',
            'calculator_change_recommended': False,
            'reason': 'These semantics appear to be EP workbook behavior and are not yet KB-backed as true in-game calculator rules.'
        }
    }





def _project_funding_cash_evidence() -> dict:
    return {
        'assumed_cash': PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS[('canonical_stat::tower_damage', 'Project Funding')]['cash'],
        'evidence_strength': 'user_provided_for_current_ep_compare_basis',
        'note': 'User clarified that EP uses 50b cash for Project Funding compare. This is treated as an explicit compare-policy input rather than a calculator truth claim.',
    }


def _build_tower_damage_runtime_gap_report(ep_compare: dict) -> dict:
    dest = 'canonical_stat::tower_damage'
    row = (ep_compare or {}).get(dest) or {}
    base_value = row.get('package_value_before_runtime_assumptions')
    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    assumptions = list(row.get('runtime_compare_assumptions') or [])
    applied_runtime_multiplier = None
    if isinstance(base_value, (int, float)) and base_value not in (None, 0) and isinstance(package_value, (int, float)):
        applied_runtime_multiplier = package_value / base_value
    required_total_runtime_multiplier = None
    if isinstance(base_value, (int, float)) and base_value not in (None, 0) and isinstance(ep_value, (int, float)):
        required_total_runtime_multiplier = ep_value / base_value

    pf_cash = PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS[('canonical_stat::tower_damage', 'Project Funding')]['cash']
    pf_coeff = PROJECT_FUNDING_RARITY_COEFFICIENTS['Mythic']
    pf_multiplier = 1.0 + math.log10(float(pf_cash)) * float(pf_coeff)
    required_berserker_if_pf_fixed = None
    if required_total_runtime_multiplier is not None and pf_multiplier not in (None, 0):
        required_berserker_if_pf_fixed = required_total_runtime_multiplier / pf_multiplier

    scenarios = []
    def add_scenario(name: str, runtime_multiplier: float | None, note: str):
        value = None if runtime_multiplier is None or base_value in (None, 0) else float(base_value) * float(runtime_multiplier)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'runtime_multiplier': runtime_multiplier,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_runtime_assumptions', applied_runtime_multiplier, 'Current compare-only runtime assumptions as emitted by the package.')
    add_scenario('ep_cash_50b_with_berserker_x8', 8.0 * pf_multiplier, 'EP compare uses Project Funding cash assumption of 50b; this scenario keeps Berserker at x8 and swaps only the PF cash assumption.')
    if required_berserker_if_pf_fixed is not None:
        add_scenario('ep_cash_50b_with_fitted_berserker', required_berserker_if_pf_fixed * pf_multiplier, 'Diagnostic only: if 50b cash is fixed, this is the Berserker multiplier that would exactly close the EP row.')

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value_before_runtime_assumptions': base_value,
        'package_value_after_runtime_assumptions': package_value,
        'ep_value': ep_value,
        'runtime_compare_assumptions': assumptions,
        'ep_evidence': _project_funding_cash_evidence(),
        'current_assumption_parameters': {
            'project_funding_cash_assumption': pf_cash,
            'project_funding_rarity_family': 'Mythic',
            'project_funding_multiplier_at_assumed_cash': pf_multiplier,
            'berserker_assumption_multiplier': 8.0,
        },
        'derived_fit': {
            'applied_runtime_multiplier': applied_runtime_multiplier,
            'required_total_runtime_multiplier_to_match_ep': required_total_runtime_multiplier,
            'required_berserker_multiplier_if_project_funding_cash_assumption_fixed': required_berserker_if_pf_fixed,
        },
        'assessment': {
            'calculator_change_recommended': False,
            'compare_assumption_change_recommended': True,
            'reason': 'tower_damage residue sits in the compare-only runtime normalization layer, not the base damage resolver. With EP cash assumption fixed at 50b, the current x8 Berserker assumption nearly exactly closes the EP row.',
        },
        'scenarios': scenarios,
    }


def _build_tower_defense_absolute_semantic_gap_report(ep_compare: dict) -> dict:
    dest = 'canonical_stat::tower_defense_absolute'
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    recomputed = _recompute(current_factors)

    standard_key = 'perk::x1.15 Defense Absolute'
    current_standard = current_factors.get(standard_key)
    ep_standard = None if current_standard is None else (1.0 + 5.0 * 0.15) * (1.0 + 0.01 * 25.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_semantics', {}, 'Current calculator semantics and compare-row inputs as emitted.')
    if ep_standard is not None:
        add_scenario('ep_standard_perk_semantics_only', {standard_key: ep_standard}, 'EP Defense Absolute appears to scale the full standard-perk result by Standard Perk Bonus rather than scaling only the perk delta. This is treated as workbook semantics, not calculator truth.')

    best_fit = scenarios[-1] if scenarios else None

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': recomputed,
        'current_factors': {
            'standard_perk_factor': current_standard,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'residual_multiplier_after_ep_standard_perk_semantics': None if best_fit is None else best_fit.get('required_residual_multiplier_to_match_ep'),
        },
        'scenarios': scenarios,
        'assessment': {
            'best_fit_hypothesis': 'tower_defense_absolute EP delta is almost exactly explained by EP-style full-result Standard Perk Bonus scaling on the Defense Absolute standard perk.',
            'calculator_change_recommended': False,
            'reason': 'The package row is internally consistent and the EP value is matched almost exactly by swapping only the standard-perk semantic to the workbook-style full-result scaling.'
        }
    }


def _build_tower_hp_semantic_gap_report(ep_compare: dict) -> dict:
    dest = 'canonical_stat::tower_hp'
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family == 'module' and c.get('value_type') == 'multiplier_display':
            factor = vf if vf >= 1.0 else 1.0 + vf
        elif family == 'perk' and c.get('value_type') == 'multiplier':
            factor = vf
        else:
            factor = vf if vf >= 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    recomputed = _recompute(current_factors)

    standard_key = 'perk::x1.20 Max Health'
    coin_to_key = 'perk::x1.80 coins, but Tower Max Health -70%'
    regen_to_key = 'perk::Tower Health Regen x8.00, But Tower Max Max Health -60%'

    current_standard = current_factors.get(standard_key)
    current_coin_to = current_factors.get(coin_to_key)
    current_regen_to = current_factors.get(regen_to_key)

    ep_standard = None if current_standard is None else (1.0 + 0.2 * 5.0) * (1.0 + 0.01 * 25.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_semantics', {}, 'Current calculator semantics and compare-row inputs as emitted.')
    if ep_standard is not None:
        add_scenario('ep_standard_perk_semantics_only', {standard_key: ep_standard}, 'EP EPH_HEALTH formula multiplies the full perk result by Standard Perks Bonus. This is an EP workbook scenario, not a calculator truth claim.')

    dwhp_level = None
    ids_lines = Path('input/_IDS.csv').read_text().splitlines()
    for line in ids_lines:
        if line.startswith('Death Wave Health,'):
            try:
                dwhp_level = int(line.split(',', 1)[1].strip())
            except Exception:
                dwhp_level = None
            break
    dwhp_multiplier = None if dwhp_level is None else (5.0 + 0.25 * dwhp_level)
    dwhp_key = 'lab::Death Wave Health'
    current_dwhp = current_factors.get(dwhp_key)
    armor_primary = current_factors.get('module::Sharp Fortitude')
    armor_assist = current_factors.get('module::Orbital Augment')

    if dwhp_multiplier is not None and current_dwhp is None:
        add_scenario('current_package_plus_account_dwhp', {'runtime::Death Wave Health': dwhp_multiplier}, 'Model account Death Wave Health as an extra compare-only multiplier to test whether missing run-state bonus explains the EP delta. This is diagnostic only.')
    if ep_standard is not None and current_standard not in (None, 0):
        add_scenario('current_package_with_ep_standard_perk_semantics', {standard_key: ep_standard}, 'Model EP workbook full-result Standard Perk Bonus semantics on top of the current package contributors.')

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': recomputed,
        'current_factors': {
            'standard_perk_factor': current_standard,
            'coin_health_tradeoff_factor': current_coin_to,
            'regen_health_tradeoff_factor': current_regen_to,
            'death_wave_health_factor': current_dwhp,
            'armor_primary_factor': armor_primary,
            'armor_assist_factor': armor_assist,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'account_death_wave_health_level': dwhp_level,
            'account_death_wave_health_multiplier_if_applied': dwhp_multiplier,
        },
        'assessment': {
            'remaining_fraction_bug_present_in_live_compare_row': False if (current_coin_to is not None and current_regen_to is not None and abs(current_coin_to - 0.3) < 1e-9 and abs(current_regen_to - 0.4) < 1e-9) else None,
            'death_wave_health_wired_in_live_compare_row': current_dwhp == dwhp_multiplier if (current_dwhp is not None and dwhp_multiplier is not None) else None,
            'reason': 'Current compare row carries the two HP trade-off drawbacks correctly and now also includes the Death Wave Health multiplier plus the EP-style armor assist factor. The remaining gap is primarily the EP workbook Standard Perk Bonus semantic drift.',
            'calculator_change_recommended': False,
        },
        'scenarios': scenarios,
    }

def _build_kb_only_health_family_audit(stat_inputs, statbook_rows: dict) -> dict:
    relevant_destinations = {
        'tower_hp', 'tower_regen', 'wall_hp', 'wall_regen', 'package_chance_pct'
    }
    relevant_rows = [
        row for row in stat_inputs
        if (row.destination_id in relevant_destinations)
        or ('health' in (row.stat_name or '').lower())
        or ('regen' in (row.stat_name or '').lower())
        or ('package' in (row.stat_name or '').lower())
        or ('wall' in (row.stat_name or '').lower())
    ]
    unmapped_relevant = [
        {
            'source_family': row.source_family,
            'stat_name': row.stat_name,
            'value': row.value,
            'value_type': row.value_type,
            'notes': row.notes,
        }
        for row in relevant_rows if not row.kb_mapped
    ]
    grouped = {}
    for destination in sorted(relevant_destinations):
        row = statbook_rows.get(f'canonical_stat::{destination}')
        if not row:
            continue
        grouped[destination] = {
            'status': row.get('status'),
            'final_value': row.get('final_value'),
            'display_value': row.get('display_value'),
            'contributor_families': sorted({c.get('source_family') for c in row.get('contributors', []) if c.get('source_family')}),
            'contributors': [
                {
                    'source_family': c.get('source_family'),
                    'source_name': c.get('source_name'),
                    'value': c.get('value'),
                    'display_value': c.get('display_value'),
                    'value_type': c.get('value_type'),
                    'notes': c.get('notes'),
                }
                for c in row.get('contributors', [])
            ],
        }
    findings = [
        {
            'severity': 'high',
            'surface': 'package_chance_pct',
            'finding': 'Workshop package-chance formula was inconsistent with KB and corrected in this iteration.',
            'kb_basis': 'KB workshop summary states 6% base and +0.40 percentage points per level, max 30% workshop-only.',
            'fix_applied': "WORKSHOP_FORMULA_VALUES['Package Chance'] changed from 10 + 0.5*level to 6 + 0.4*level.",
        },
        {
            'severity': 'high',
            'surface': 'tower_hp',
            'finding': 'tower_hp relic semantics were previously too vague in the KB. They are now repaired to explicit pct_bonus semantics, consistent with live-wiki guidance that relic bonuses are additive with similar relics and multiplicative with other bonuses.',
            'kb_basis': 'kb/global-rules/tables/relic-input-registry.csv now uses semantic_unit_hint pct_bonus for relic__tower__health__pct.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'tower_regen',
            'finding': 'tower_regen relic semantics were previously too vague in the KB. They are now repaired to explicit pct_bonus semantics, consistent with live-wiki guidance that relic bonuses are additive with similar relics and multiplicative with other bonuses.',
            'kb_basis': 'kb/global-rules/tables/relic-input-registry.csv now uses semantic_unit_hint pct_bonus for relic__tower__health_regen__pct.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'wall_hp',
            'finding': 'wall_hp KB semantics were repaired by aligning Wall Health lab application metadata to the wiki-verified percent ladder.',
            'kb_basis': 'kb/labs/tables/lab-application-registry.csv now classifies LAB_WALL_HEALTH as additive_percent_points / percent_points and points to the dedicated wall-health table.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'wall_regen',
            'finding': 'wall_regen can publish again because upstream tower_regen contract ambiguity was repaired and the wall-regen lab was already represented as a percent ladder in the KB.',
            'kb_basis': 'Current phase-3 override derives wall_regen from tower_regen multiplied by wall-only contributors; wall regen lab table remains wiki-verified percent values.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
    ]
    return {
        'scope': 'kb_only_health_family_audit',
        'display_rule': 'rendered/exported display fields use k, M, B, T, q, Q, s, S abbreviations; raw numeric values remain unchanged',
        'strict_kb_publish_recommendation': {
            'block_destinations': [],
            'allow_destinations': ['package_chance_pct', 'tower_hp', 'tower_regen', 'wall_hp', 'wall_regen'],
            'reason': 'Strict KB-only governance now allows the health family to publish because the specific KB contract ambiguities were repaired with wiki-verified semantics.',
        },
        'surfaces': grouped,
        'unmapped_relevant_rows': unmapped_relevant,
        'findings': findings,
    }



def _build_damage_defabs_scope_audit(account_state, stat_inputs, statbook_rows: dict) -> dict:
    surfaces = {
        'tower_damage': {
            'destination_key': 'canonical_stat::tower_damage',
            'admissible_families': ['workshop', 'lab', 'card', 'module', 'enhancement', 'relic', 'vault'],
        },
        'tower_defense_absolute': {
            'destination_key': 'canonical_stat::tower_defense_absolute',
            'admissible_families': ['workshop', 'lab', 'module_substat', 'enhancement', 'relic', 'vault'],
        },
    }
    active_preset = account_state.default_preset
    active_cards = set(account_state.card_presets.get(active_preset, []))
    other_presets_with_card = [
        preset for preset, cards in account_state.card_presets.items()
        if preset != active_preset and 'Damage' in cards
    ]
    active_modules = account_state.module_presets.get(active_preset, {})
    active_armor_selection = active_modules.get('armor') if hasattr(active_modules, 'get') else None
    active_armor_modules = []
    for role in ('primary', 'assist'):
        mod_name = getattr(active_armor_selection, role, None) if active_armor_selection is not None else None
        if mod_name:
            mod = account_state.modules_inventory.get(mod_name)
            if mod:
                active_armor_modules.append((role, mod_name, mod))

    def _surface_unmapped_rows(surface_id: str):
        out = []
        for row in stat_inputs:
            if row.destination_id == surface_id and not row.kb_mapped:
                out.append({
                    'source_family': row.source_family,
                    'source_name': row.source_name,
                    'stat_name': row.stat_name,
                    'value': row.value,
                    'value_type': row.value_type,
                    'notes': row.notes,
                })
        return out

    payload = {
        'scope': 'kb_only_damage_defense_absolute_scope_audit',
        'active_preset': active_preset,
        'surfaces': {},
        'findings': [],
    }

    for surface_id, meta in surfaces.items():
        row = statbook_rows.get(meta['destination_key']) or {}
        contributors = row.get('contributors', [])
        contributor_families = sorted({c.get('source_family') for c in contributors if c.get('source_family')})
        contributor_names = sorted({c.get('source_name') for c in contributors if c.get('source_name')})
        payload['surfaces'][surface_id] = {
            'status': row.get('status'),
            'final_value': row.get('final_value'),
            'display_value': row.get('display_value'),
            'admissible_families': meta['admissible_families'],
            'active_contributor_families': contributor_families,
            'active_contributor_names': contributor_names,
            'missing_admissible_families_in_active_preset': [f for f in meta['admissible_families'] if f not in contributor_families],
            'unmapped_rows_bound_to_surface': _surface_unmapped_rows(surface_id),
        }

    damage_inventory = account_state.cards_inventory.get('Damage')
    damage_card_detail = {
        'owned_in_inventory': damage_inventory is not None,
        'inventory_level': damage_inventory.level if damage_inventory is not None else None,
        'active_in_current_preset': 'Damage' in active_cards,
        'other_presets_with_card_active': other_presets_with_card,
    }
    payload['surfaces']['tower_damage']['inactive_admissible_contributors'] = {
        'damage_card': damage_card_detail,
    }

    defense_abs_armor_substats = []
    for role, mod_name, mod in active_armor_modules:
        for sub in mod.substats:
            if (sub.name or '').strip().lower() == 'defense absolute':
                defense_abs_armor_substats.append({
                    'role': role,
                    'module_name': mod_name,
                    'raw_token': sub.raw_token,
                    'display_value': sub.value,
                })
    payload['surfaces']['tower_defense_absolute']['inactive_admissible_contributors'] = {
        'active_armor_module_defense_absolute_substats': defense_abs_armor_substats,
    }

    if damage_inventory is not None and 'Damage' not in active_cards:
        payload['findings'].append({
            'severity': 'medium',
            'surface': 'tower_damage',
            'finding': 'Damage card is owned but not active in the current preset, so card-family damage contribution is legitimately absent from this stat path.',
            'kb_basis': 'kb/cards/tables/card-effect-registry.csv routes DAMAGE base-card effect to tower.damage_multiplier and kb/cards/tables/card-base-ladders.csv provides the ladder.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'damage_card_inventory_level': damage_inventory.level,
                'other_presets_with_card_active': other_presets_with_card,
            },
            'fix_applied': 'No formula patch applied; audit surfaced preset-scoped contributor absence only.',
        })
    elif damage_inventory is None and other_presets_with_card:
        payload['findings'].append({
            'severity': 'high',
            'surface': 'tower_damage',
            'finding': 'Card preset data references Damage in another preset, but cards_inventory has no Damage snapshot. That is an account-state inconsistency worth treating as a parser or source-shape bug until proven otherwise.',
            'kb_basis': 'kb/cards/tables/card-entity-registry.csv and card-base-ladders.csv define DAMAGE as a valid card surface; a preset should not reference a non-existent inventory card silently.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'other_presets_with_card_active': other_presets_with_card,
                'cards_inventory_contains_damage': False,
            },
            'fix_applied': 'No formula patch applied in this iteration; audit surfaced a likely account-state/parser inconsistency.',
        })
    else:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_damage',
            'finding': 'No admissible current-preset contributor family was proven missing from the KB-routed tower_damage path.',
            'kb_basis': 'Active contributors already include workshop, lab, enhancement, relic, vault, and module.',
            'fix_applied': 'None; current mismatch remains unexplained within the active-preset static path.',
        })

    if not defense_abs_armor_substats:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_defense_absolute',
            'finding': 'No active armor-module Defense Absolute substat exists in the current preset, so module-substat contribution is legitimately absent from tower_defense_absolute.',
            'kb_basis': 'kb/modules/tables/module-substats.csv defines Armor -> Defense Absolute as an admissible routed family when present.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'active_armor_modules': [
                    {
                        'role': role,
                        'module_name': mod_name,
                    }
                    for role, mod_name, _ in active_armor_modules
                ],
            },
            'fix_applied': 'No formula patch applied; audit surfaced current-preset contributor absence only.',
        })
    else:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_defense_absolute',
            'finding': 'Active armor module already exposes Defense Absolute substat(s); no missing-family conclusion was warranted.',
            'kb_basis': 'Active armor-module substats include Defense Absolute in the current preset.',
            'fix_applied': 'None.',
        })

    return payload


LAB_APPLICATION_SCOPE = {
    'Attack Speed', 'Damage', 'Health', 'Critical Factor', 'Game Speed', 'Labs Speed', 'Range',
    'Defense %', 'Recovery Package Chance', 'Enemy Attack Level Skip', 'Enemy Health Level Skip',
    'Chrono Field Duration', 'Waves Required', 'Cash Bonus', 'Coins / Kill Bonus', 'Health Regen',
}
VAULT_ADMIN_EXCLUDED = {
    'Keys spent', 'Total Bonuses', 'Misc.', 'Attack', 'Defense', 'Utility',
    'Cash / Wave', 'Coins / Kill', 'Coins / Wave', 'Interest / Wave', 'Unlocks',
}
MODULE_SCOPE_EXCLUDED = set()



EP_NONCOMPARABLE_DESTINATIONS = {
    'canonical_stat::free_attack_upgrade_chance_pct',
    'canonical_stat::free_defense_upgrade_chance_pct',
    'canonical_stat::free_utility_upgrade_chance_pct',
}

EP_LABEL_TO_DESTINATION = {
    'Attack Speed': 'canonical_stat::tower_attack_speed',
    'Critical Chance': 'canonical_stat::tower_crit_chance_pct',
    'Critical Factor': 'canonical_stat::tower_crit_multiplier',
    'Range': 'canonical_stat::tower_range_m',
    'Damage / Meter': 'canonical_stat::tower_damage_per_meter_multiplier',
    'Multishot Chance': 'canonical_stat::tower_multishot_chance_pct',
    'Multishot Targets': 'canonical_stat::tower_multishot_targets',
    'Rapid Fire Chance': 'canonical_stat::tower_rapid_fire_chance_pct',
    'Rapid Fire Duration': 'canonical_stat::tower_rapid_fire_duration_seconds',
    'Bounce Shot Chance': 'canonical_stat::tower_bounce_shot_chance_pct',
    'Bounce Shot Targets': 'canonical_stat::tower_bounce_shot_targets',
    'Super Crit Chance': 'canonical_stat::tower_supercrit_chance_pct',
    'Super Crit Multiplier': 'canonical_stat::tower_supercrit_multiplier',
    'Recovery Package Chance': 'canonical_stat::package_chance_pct',
    'Health': 'canonical_stat::tower_hp',
    'Health Regen': 'canonical_stat::tower_regen',
    'Defense Absolute': 'canonical_stat::tower_defense_absolute',
    'Defense %': 'canonical_stat::tower_defense_pct',
    'Wall Health': 'canonical_stat::wall_hp',
    'Wall Fortification': 'canonical_stat::wall_fortification_multiplier',
    'Wall Regen': 'canonical_stat::wall_regen',
    'Max Recovery': 'canonical_stat::max_recovery_multiplier',
    'Coins / Kill Bonus': 'canonical_stat::coins_per_kill_bonus',
    'Free Attack Upgrade': 'canonical_stat::free_attack_upgrade_chance_pct',
    'Free Defense Upgrade': 'canonical_stat::free_defense_upgrade_chance_pct',
    'Free Utility Upgrade': 'canonical_stat::free_utility_upgrade_chance_pct',
    'Damage': 'canonical_stat::tower_damage',
}

def _parse_ep_value(raw):
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None, None
    if s.startswith('x'):
        try:
            return float(s[1:]), 'multiplier_display'
        except ValueError:
            return None, None
    suffixes = {'K':1e3,'M':1e6,'B':1e9,'T':1e12,'q':1e15,'Q':1e18,'O':1e27}
    m = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*([KMBTqQO])', s)
    if m:
        return float(m.group(1))*suffixes[m.group(2)], 'scaled_number'
    try:
        return float(s), 'number'
    except ValueError:
        return None, None

def _load_ep_oracle(ep_path: Path):
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


def _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger):
    blocked_formula_contracts = []
    for destination_id, contract in (formula_ledger.get('surfaces') or {}).items():
        if contract.get('publish_policy') == 'block':
            blocked_formula_contracts.append({
                'destination_id': destination_id,
                'formula_class': contract.get('formula_class'),
                'rationale': contract.get('rationale'),
            })

    active_unmapped_inputs = []
    for row in stat_inputs:
        if row.kb_mapped:
            continue
        if row.source_family == 'raw':
            continue
        active_unmapped_inputs.append({
            'source_family': row.source_family,
            'stat_name': row.stat_name,
            'value_type': row.value_type,
            'contributor_id': row.contributor_id,
        })
    active_unmapped_inputs.sort(key=lambda item: (item['source_family'], item['stat_name']))
    active_unmapped_by_family = {}
    for item in active_unmapped_inputs:
        fam = item['source_family']
        active_unmapped_by_family[fam] = active_unmapped_by_family.get(fam, 0) + 1

    resolved_unknown_schema_units = []
    for destination_id, row in (statbook_publishable_dict.get('rows') or {}).items():
        if row.get('status') != 'resolved':
            continue
        schema = row.get('schema') or {}
        if schema.get('unit') != 'unknown':
            continue
        resolved_unknown_schema_units.append({
            'destination_id': destination_id,
            'resolver': schema.get('resolver'),
            'value_type': row.get('value_type'),
            'final_value': row.get('final_value'),
        })
    resolved_unknown_schema_units.sort(key=lambda item: item['destination_id'])

    relic_registry_rows = _load_csv_rows(ROOT / 'kb' / 'global-rules' / 'tables' / 'relic-input-registry.csv')
    ambiguous_relic_semantics = []
    for rec in relic_registry_rows:
        if (rec.get('semantic_unit_hint') or '').strip() == 'percent_points_or_pct_bonus':
            ambiguous_relic_semantics.append({
                'registry_key': rec.get('registry_key'),
                'destination_id': f"{rec.get('destination_object_type','').strip()}::{rec.get('destination_id','').strip()}" if rec.get('destination_id') else None,
            })
    ambiguous_relic_semantics.sort(key=lambda item: item['registry_key'] or '')

    return {
        'summary': {
            'blocked_formula_contract_count': len(blocked_formula_contracts),
            'active_unmapped_input_count': len(active_unmapped_inputs),
            'resolved_unknown_schema_unit_count': len(resolved_unknown_schema_units),
            'ambiguous_relic_semantic_hint_count': len(ambiguous_relic_semantics),
        },
        'priority_gaps': ([
            item for item in active_unmapped_inputs
            if item['stat_name'] == 'Dimension Core::main'
        ] + blocked_formula_contracts + active_unmapped_inputs[:12]),
        'blocked_formula_contracts': blocked_formula_contracts,
        'active_unmapped_by_family': active_unmapped_by_family,
        'active_unmapped_inputs': active_unmapped_inputs,
        'resolved_unknown_schema_units': resolved_unknown_schema_units,
        'ambiguous_relic_semantic_hints': ambiguous_relic_semantics,
        'notes': [
            'Active unmapped inputs are live calculator inputs without a KB destination contract in the current package.',
            'Resolved rows with schema.unit=unknown are publishable bridges, but not convergence-grade clean contracts.',
            'ambiguous_relic_semantic_hints lists KB registry rows that still admit multiple semantic interpretations and may need future wiki-backed tightening.',
        ],
    }


def _classify_unmapped_input_gap(item):
    source_family = (item.get('source_family') or '').strip().lower()
    stat_name = (item.get('stat_name') or '').strip()
    contributor_id = item.get('contributor_id')

    if contributor_id:
        return 'Calculator wiring / implementation gap'

    runtime_only_patterns = [
        r'Mastery$',
        r'Effect Bans',
        r'Assist Module',
        r'Enemy',
        r'Boss',
        r'Protector',
        r'Ranged',
        r'Fast',
        r'Tank',
        r'Vampire',
        r'Scatter',
        r'Ray',
        r'Resistance',
        r'Ultimate',
        r'Battle Condition',
        r'Card Presets',
        r'Buy Multiplier',
        r'More Round Stats',
        r'Auto Pick',
        r'Ban Perks',
        r'Perk Option Quantity',
        r'First Perk Choice',
        r'Standard Perks Bonus',
        r'Unlock Perks',
        r'END OF ARRAY',
        r'Keys spent',
        r'Total Bonuses',
        r'Misc\.',
        r'Unlocks$',
        r'Discount',
        r'Shards',
        r'Module Coin Cost',
        r'Rare Drop Chance',
        r'Unmerge Module',
        r'Shatter Shards',
    ]
    if any(re.search(pattern, stat_name) for pattern in runtime_only_patterns):
        return 'Intentional non-goal / runtime-only surface'

    if source_family == 'vault' and stat_name in {
        'Attack', 'Defense', 'Utility', 'Cash / Wave', 'Coins / Kill',
        'Coins / Wave', 'Interest / Wave', 'Keys spent', 'Misc.',
        'Total Bonuses', 'Unlocks'
    }:
        return 'Intentional non-goal / runtime-only surface'

    if source_family in {'lab', 'vault'}:
        return 'KB missing executable contract'
    return 'KB missing fact'


def _build_kb_gap_register(kb_incomplete_areas, audits):
    register = []

    for item in kb_incomplete_areas.get('blocked_formula_contracts', []):
        register.append({
            'gap_id': f"formula_contract::{item['destination_id']}",
            'bucket': 'KB missing executable contract',
            'surface': item['destination_id'],
            'files': ['config/destination_formula_ledger.yaml', 'engine/stat_engine.py'],
            'evidence': f"publish_policy=block for {item['destination_id']}",
            'why_it_matters': 'Surface remains intentionally fail-closed until formula contract is fully closed.',
            'what_would_close_it': 'Tighten the KB/contract rationale and verify the implemented destination-specific formula is correct enough to publish.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    for item in kb_incomplete_areas.get('active_unmapped_inputs', []):
        register.append({
            'gap_id': f"unmapped::{item['source_family']}::{item['stat_name']}",
            'bucket': _classify_unmapped_input_gap(item),
            'surface': item['stat_name'],
            'files': [
                'compilers/stat_input_compiler.py',
                'kb/global-rules/contracts/contributor-mappings-full.yaml',
                'kb/labs/tables/lab-application-registry.csv',
                'kb/cards/tables/card-effect-registry.csv',
                'kb/global-rules/tables/relic-input-registry.csv',
            ],
            'evidence': f"Active {item['source_family']} input remains unmapped in current package.",
            'why_it_matters': 'Live calculator input is preserved but not yet closed into a governed destination contract.',
            'what_would_close_it': 'Either add the missing KB destination/contract coverage or route the input through existing KB contracts in the compiler.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    for item in kb_incomplete_areas.get('ambiguous_relic_semantic_hints', []):
        register.append({
            'gap_id': f"ambiguous_relic::{item['registry_key']}",
            'bucket': 'KB contract ambiguous',
            'surface': item.get('destination_id') or item['registry_key'],
            'files': ['kb/global-rules/tables/relic-input-registry.csv'],
            'evidence': f"semantic_unit_hint remains percent_points_or_pct_bonus for {item['registry_key']}",
            'why_it_matters': 'Ambiguous relic semantics can block strict fail-closed destination formulas.',
            'what_would_close_it': 'Resolve the relic semantic hint to a single contract form using KB evidence and wiki verification where needed.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    for item in kb_incomplete_areas.get('resolved_unknown_schema_units', []):
        register.append({
            'gap_id': f"unknown_unit::{item['destination_id']}",
            'bucket': 'Intentional non-goal / runtime-only surface' if str(item['destination_id']).startswith(('runtime_mechanic_param::', 'mechanic_param::', 'account_flag::', 'capability::', 'raw::')) else 'KB missing executable contract',
            'surface': item['destination_id'],
            'files': ['engine/stat_engine.py', 'run_stats.py'],
            'evidence': f"Resolved publishable row still has schema.unit=unknown for {item['destination_id']}",
            'why_it_matters': 'The surface publishes, but its schema is not convergence-grade clean.',
            'what_would_close_it': 'Assign a precise schema unit or explicitly classify the surface as runtime-only/administrative.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    compare_issues = audits.get('compare_layer_destination_unit_inconsistencies', []) if isinstance(audits, dict) else []
    for issue in compare_issues:
        if issue.get('status') not in {'mismatch', 'formula_blocked'}:
            continue
        register.append({
            'gap_id': f"compare::{issue.get('destination')}",
            'bucket': 'Calculator wiring / implementation gap',
            'surface': issue.get('destination'),
            'files': ['run_stats.py', 'engine/stat_engine.py', 'compilers/stat_input_compiler.py'],
            'evidence': f"Compare layer still reports {issue.get('status')} for {issue.get('destination')}",
            'why_it_matters': 'This is a live survivor surface after current state binding and compare normalization.',
            'what_would_close_it': 'Close the remaining contributor/formula gap or explicitly reclassify the surface as blocked/non-comparable.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    # Deduplicate by gap_id while preserving order
    seen = set()
    out = []
    for entry in register:
        gid = entry['gap_id']
        if gid in seen:
            continue
        seen.add(gid)
        out.append(entry)
    summary = Counter(entry['bucket'] for entry in out)
    return {
        'summary': dict(sorted(summary.items())),
        'entries': out,
    }


def _build_publish_gate_audits(stat_inputs, statbook_dict, ep_compare, formula_ledger):
    mapped_level_rows = []
    for row in stat_inputs:
        if row.kb_mapped and row.destination_id and row.value_type == 'level':
            mapped_level_rows.append({
                'source_family': row.source_family,
                'source_name': row.source_name,
                'destination_object_type': row.destination_object_type,
                'destination_id': row.destination_id,
                'value': row.value,
                'notes': row.notes,
            })
    resolved_with_unresolved = []
    capability_non_boolean = []
    compare_inconsistencies = []
    for key, row in statbook_dict['rows'].items():
        status = row.get('status')
        contributors = row.get('contributors', [])
        unresolved = [c for c in contributors if c.get('value_type') == 'level' or c.get('value') is None or 'unresolved' in str(c.get('notes') or '').lower()]
        if status == 'resolved' and unresolved:
            resolved_with_unresolved.append({
                'destination': key,
                'unresolved_contributors': unresolved,
            })
        if key.startswith('capability::') and key.endswith('.enabled') and status == 'resolved' and not isinstance(row.get('final_value'), bool):
            capability_non_boolean.append({
                'destination': key,
                'final_value': row.get('final_value'),
                'status': status,
            })
    for dest, compare in ep_compare.items():
        pkg_row = statbook_dict['rows'].get(dest)
        if pkg_row is None:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'missing_from_package',
                'ep_label': compare.get('label'),
            })
            continue
        pkg_unit = pkg_row.get('value_type')
        ep_type = compare.get('ep_value_type')
        ep_value = compare.get('ep_value_parsed')
        status = compare.get('status')
        notes = set(compare.get('compare_notes') or [])
        expected_pct = dest.endswith('_pct')
        if expected_pct and ep_type == 'number' and ep_value is not None and ep_value <= 1.0:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'ep_decimal_fraction_percent_surface',
                'package_unit': pkg_unit,
                'ep_type': ep_type,
                'normalized_ep_percent_points': ep_value * 100.0,
                'package_value': compare.get('package_value'),
                'status': status,
            })
        if 'ep_compare_uses_unsupported_stage_facets' in notes:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'stage_scope_gap',
                'unsupported_facets': [note for note in compare.get('compare_notes', []) if note in {'max_progression', 'max_workshop', 'run_perks'}],
                'compare_preset': compare.get('compare_preset'),
                'status': status,
            })
        if status in {'non_comparable', 'non_numeric_compare', 'formula_blocked'}:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': status,
                'compare_preset': compare.get('compare_preset'),
            })
    return {
        'mapped_rows_still_level': mapped_level_rows,
        'resolved_stats_with_unresolved_contributors': resolved_with_unresolved,
        'capability_destinations_non_boolean': capability_non_boolean,
        'blocked_boolean_type_mismatches': [r['stat_name'] for r in statbook_dict['rows'].values() if r.get('status')=='mapped_not_resolved' and 'boolean' in (r.get('notes') or '')],
        'compare_layer_destination_unit_inconsistencies': compare_inconsistencies,
    }

def _apply_projected_runtime_compare_assumptions(destination: str, package_row: dict | None, stage_context: dict) -> tuple[dict | None, list[str]]:
    if package_row is None:
        return None, []
    if stage_context.get('package_progression_state') != 'projected_max_progression':
        return package_row, []
    compare_preset = stage_context.get('compare_preset')
    active_cards = set((stage_context.get('active_cards_by_preset') or {}).get(compare_preset) or [])
    adjusted = dict(package_row)
    notes = []
    for card_name in active_cards:
        assumption = PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS.get((destination, card_name))
        if not assumption:
            continue
        try:
            adjusted['final_value'] = float(adjusted.get('final_value')) * float(assumption['multiplier'])
            notes.append(assumption['note'])
        except Exception:
            continue
    if destination == 'canonical_stat::tower_damage':
        try:
            pf_multiplier, pf_note = _project_funding_compare_multiplier(stage_context)
            if pf_multiplier is not None:
                adjusted['final_value'] = float(adjusted.get('final_value')) * float(pf_multiplier)
                notes.append(pf_note)
        except Exception:
            pass
    return adjusted, notes


def _normalize_module_rarity_family(rarity: str | None) -> str | None:
    if not rarity:
        return None
    rarity = str(rarity).strip()
    for base in ('Ancestral', 'Mythic', 'Legendary', 'Epic'):
        if rarity.startswith(base):
            return base
    return rarity


def _project_funding_compare_multiplier(stage_context: dict) -> tuple[float | None, str | None]:
    compare_preset = stage_context.get('compare_preset')
    active_modules = (stage_context.get('active_modules_by_preset') or {}).get(compare_preset) or {}
    generator = active_modules.get('generator') or {}
    primary_name = generator.get('primary')
    if primary_name != 'Project Funding':
        return None, None
    assumption = PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS.get(('canonical_stat::tower_damage', 'Project Funding'))
    if not assumption:
        return None, None
    modules_inventory = stage_context.get('modules_inventory') or {}
    module_row = modules_inventory.get('Project Funding') or {}
    rarity_family = _normalize_module_rarity_family(module_row.get('rarity'))
    coeff = PROJECT_FUNDING_RARITY_COEFFICIENTS.get(rarity_family)
    cash = assumption.get('cash')
    if coeff is None or not cash or cash <= 0:
        return None, None
    multiplier = max(1.0, 1.0 + math.log10(float(cash)) * float(coeff))
    note = f"{assumption['note']}__rarity_family_{rarity_family.lower()}__multiplier_{multiplier:.6f}"
    return multiplier, note


def _contributor_snapshot(row: dict | None) -> list[dict]:
    if not isinstance(row, dict):
        return []
    out = []
    for c in row.get('contributors', []) or []:
        out.append({
            'source_family': c.get('source_family'),
            'source_name': c.get('source_name'),
            'preset_name': c.get('preset_name'),
            'value': c.get('value'),
            'value_type': c.get('value_type'),
            'notes': c.get('notes'),
        })
    return out


def _build_run_perk_residue_analysis(ep_compare: dict) -> dict:
    out = {
        'lineage_backed_destinations': sorted(COMPARE_DESTINATION_RUN_PERK_FACETS.keys()),
        'stage_scope_rows': [],
    }
    for destination, row in sorted(ep_compare.items()):
        if row.get('status') != 'stage_scope_mismatch':
            continue
        if destination not in COMPARE_DESTINATION_RUN_PERK_FACETS:
            continue
        try:
            package_value = float(row.get('package_value'))
        except Exception:
            package_value = None
        try:
            ep_value = float(row.get('ep_value'))
        except Exception:
            ep_value = None
        required_effective_multiplier = None
        if package_value not in (None, 0.0) and ep_value is not None:
            required_effective_multiplier = ep_value / package_value
        out['stage_scope_rows'].append({
            'destination': destination,
            'package_value': package_value,
            'ep_value': ep_value,
            'required_effective_multiplier_to_match_ep': required_effective_multiplier,
            'unsupported_facets': list(row.get('unsupported_compare_facets') or []),
            'compare_notes': list(row.get('compare_notes') or []),
        })
    out['stage_scope_row_count'] = len(out['stage_scope_rows'])
    return out

def _build_tradeoff_routing_audit(ids_raw, loadout_config, perk_config, *, preset: str, state_mode: str, perk_state: str) -> dict:
    from compilers.account_state_compiler import compile_account_state
    from compilers.stat_input_compiler import compile_stat_inputs, _load_perk_entities, TRADE_OFF_BENEFIT_EFFECT_INDEXES

    state = compile_account_state(ids_raw, default_preset=preset, loadout_config=loadout_config, perk_config=perk_config)
    perks_enabled = _perks_enabled_for_state(state.active_perk_preset, perk_state)
    rows = compile_stat_inputs(state, preset_name=preset, state_mode=state_mode, perks_enabled=perks_enabled)
    perk_entities = _load_perk_entities()
    banned_ids = {str(item).strip() for item in (perk_config or {}).get('banned_perk_ids', []) if str(item).strip()}

    by_perk = {}
    for row in rows:
        if row.source_family != 'perk' or not row.contributor_id or '::effect_' not in row.contributor_id:
            continue
        contrib = row.contributor_id
        if not contrib.startswith('perk::'):
            continue
        perk_id = contrib.split('::', 2)[1]
        meta = perk_entities.get(perk_id, {})
        if str(meta.get('category') or '').strip().lower() != 'trade_off':
            continue
        by_perk.setdefault(perk_id, []).append(row)

    perk_rows = []
    active_tradeoff_count = 0
    compile_error_count = 0
    banned_present = []
    for perk_id, meta in sorted(perk_entities.items()):
        if str(meta.get('category') or '').strip().lower() != 'trade_off':
            continue
        rows_for_perk = by_perk.get(perk_id, [])
        active = len(rows_for_perk) > 0
        if active:
            active_tradeoff_count += 1
        if perk_id in banned_ids and active:
            banned_present.append(perk_id)
        benefit_indexes = set(TRADE_OFF_BENEFIT_EFFECT_INDEXES.get(perk_id, set()))
        compiled_indexes = set()
        destinations = []
        benefit_rows = 0
        drawback_rows = 0
        for row in rows_for_perk:
            effect_index = (row.contributor_id or '').rsplit('_', 1)[-1]
            compiled_indexes.add(effect_index)
            destinations.append({
                'effect_index': effect_index,
                'destination_object_type': row.destination_object_type,
                'destination_id': row.destination_id,
                'value': row.value,
                'value_type': row.value_type,
            })
            if effect_index in benefit_indexes:
                benefit_rows += 1
            else:
                drawback_rows += 1
        expected_two_sided = bool(benefit_indexes)
        both_sides_materialized = active and benefit_rows > 0 and drawback_rows > 0
        compile_error = active and expected_two_sided and not both_sides_materialized
        if compile_error:
            compile_error_count += 1
        perk_rows.append({
            'perk_id': perk_id,
            'perk_name': meta.get('perk_name'),
            'active': active,
            'banned': perk_id in banned_ids,
            'compiled_effect_indexes': sorted(compiled_indexes),
            'benefit_effect_indexes': sorted(benefit_indexes),
            'benefit_rows': benefit_rows,
            'drawback_rows': drawback_rows,
            'both_sides_materialized': both_sides_materialized,
            'compile_error': compile_error,
            'destinations': destinations,
        })

    return {
        'perk_state': perk_state,
        'preset': preset,
        'state_mode': state_mode,
        'active_tradeoff_count': active_tradeoff_count,
        'compile_error_count': compile_error_count,
        'banned_tradeoffs_present_count': len(banned_present),
        'banned_tradeoffs_present': banned_present,
        'rows': perk_rows,
    }

def _build_tower_damage_residue_analysis(ep_compare: dict) -> dict:
    row = ep_compare.get('canonical_stat::tower_damage') or {}
    pre_runtime = row.get('package_value_before_runtime_assumptions')
    post_runtime = row.get('package_value')
    ep_value = row.get('ep_value')
    assumptions = list(row.get('runtime_compare_assumptions') or [])

    def _as_float(value):
        try:
            return float(value)
        except Exception:
            return None

    pre_runtime_f = _as_float(pre_runtime)
    post_runtime_f = _as_float(post_runtime)
    ep_value_f = _as_float(ep_value)

    applied_runtime_multiplier = None
    required_total_runtime_multiplier = None
    required_project_funding_multiplier_if_berserker_x8 = None
    required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = None
    residue = None
    residue_relative_pct = None

    if pre_runtime_f not in (None, 0.0) and post_runtime_f is not None:
        applied_runtime_multiplier = post_runtime_f / pre_runtime_f
    if pre_runtime_f not in (None, 0.0) and ep_value_f is not None:
        required_total_runtime_multiplier = ep_value_f / pre_runtime_f
    if required_total_runtime_multiplier is not None:
        required_project_funding_multiplier_if_berserker_x8 = required_total_runtime_multiplier / 8.0
        cash = 500_000_000_000.0
        required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = (required_project_funding_multiplier_if_berserker_x8 - 1.0) / math.log10(cash)
    if post_runtime_f is not None and ep_value_f is not None:
        residue = post_runtime_f - ep_value_f
        if ep_value_f != 0:
            residue_relative_pct = 100.0 * residue / ep_value_f

    return {
        'destination': 'canonical_stat::tower_damage',
        'package_value_before_runtime_assumptions': pre_runtime_f,
        'package_value_after_runtime_assumptions': post_runtime_f,
        'ep_value': ep_value_f,
        'runtime_compare_assumptions': assumptions,
        'applied_runtime_multiplier': applied_runtime_multiplier,
        'required_total_runtime_multiplier_to_match_ep': required_total_runtime_multiplier,
        'required_project_funding_multiplier_at_berserker_x8_to_match_ep': required_project_funding_multiplier_if_berserker_x8,
        'required_project_funding_coefficient_at_cash_50b_if_berserker_x8_to_match_ep': required_project_funding_coefficient_at_cash_500b_if_berserker_x8,
        'residue_after_current_assumptions': residue,
        'residue_relative_pct_after_current_assumptions': residue_relative_pct,
    }


def _normalize_perk_state(perk_state: str) -> str:
    value = str(perk_state or 'auto').strip().lower()
    if value not in {'auto', 'on', 'off'}:
        raise ValueError(f'Unsupported perk state: {perk_state}')
    return value


def _perks_enabled_for_state(active_perk_preset: str | None, perk_state: str) -> bool:
    normalized = _normalize_perk_state(perk_state)
    if normalized == 'on':
        return True
    if normalized == 'off':
        return False
    return bool(active_perk_preset)


def _build_perk_contributor_audit(ids_raw, loadout_config, perk_config, state_mode: str, default_preset: str) -> dict:
    destinations_of_interest = {
        "canonical_stat::tower_damage",
        "canonical_stat::tower_hp",
        "canonical_stat::tower_regen",
        "canonical_stat::tower_defense_absolute",
        "canonical_stat::tower_bounce_shot_targets",
        "canonical_stat::wall_hp",
        "canonical_stat::wall_regen",
    }
    audit: dict[str, dict] = {}
    for preset_name in ("Farming", "Tourney"):
        account_state = compile_account_state(
            ids_raw,
            default_preset=default_preset,
            loadout_config=loadout_config,
            perk_config=perk_config,
        )
        stat_inputs = compile_stat_inputs(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            perks_enabled=True,
        )
        for item in stat_inputs:
            if item.source_family != 'perk':
                continue
            destination = f"{item.destination_object_type}::{item.destination_id}"
            if destination not in destinations_of_interest:
                continue
            audit.setdefault(destination, {}).setdefault(preset_name, []).append({
                'perk_name': item.source_name,
                'contributor_id': item.contributor_id,
                'value': item.value,
                'value_type': item.value_type,
                'notes': item.notes,
                'preset_name': item.preset_name,
            })
    for destination_payload in audit.values():
        for rows in destination_payload.values():
            rows.sort(key=lambda r: (r['perk_name'], r['contributor_id']))
    return dict(sorted(audit.items()))




def _build_compare_situation_fit_matrix(ids_raw, loadout_config, perk_config, formula_ledger, ep_oracle: dict) -> dict:
    states = [
        ('farming__perks_off', 'Farming', 'off', None),
        ('farming__perks_on', 'Farming', 'on', None),
        ('tourney__perks_off', 'Tourney', 'off', None),
        ('tourney__perks_on', 'Tourney', 'on', {'Tourney': 'on'}),
    ]
    views = {}
    best_fit_by_destination = {}
    for state_key, preset, perk_state, forced_preset_perk_states in states:
        _default_state, rows_by_preset, _publishable_rows_by_preset, stage_context = _build_compare_rows_by_preset(
            ids_raw,
            loadout_config,
            perk_config,
            formula_ledger,
            'max_progression',
            preset,
            ep_oracle,
            perk_state,
            forced_preset_perk_states,
        )
        compare = _build_ep_compare(ep_oracle, rows_by_preset, formula_ledger, stage_context, ep_stage_context_for_destination=_ep_stage_context_for_destination, compare_state_key_for_destination=_compare_state_key_for_destination, contributor_snapshot=_contributor_snapshot, apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions, formula_contract=_formula_contract, normalize_compare_values=_normalize_compare_values)
        views[state_key] = {
            'preset': preset,
            'perk_state': perk_state,
            **_build_compare_status_summary(compare),
        }
        for destination, row in compare.items():
            rel = row.get('relative_delta_pct')
            abs_rel = abs(float(rel)) if rel is not None else float('inf')
            candidate = {
                'state_key': state_key,
                'preset': preset,
                'perk_state': perk_state,
                'status': row.get('status'),
                'package_value': row.get('package_value'),
                'ep_value': row.get('ep_value'),
                'relative_delta_pct': rel,
                'abs_relative_delta_pct': None if rel is None else abs_rel,
            }
            current = best_fit_by_destination.get(destination)
            if current is None or abs_rel < (current.get('abs_relative_delta_pct') if current.get('abs_relative_delta_pct') is not None else float('inf')):
                best_fit_by_destination[destination] = candidate
    best_fit_state_counts = Counter(v['state_key'] for v in best_fit_by_destination.values())
    best_fit_status_counts = Counter(v['status'] for v in best_fit_by_destination.values())
    return {
        'states': views,
        'best_fit_by_destination': dict(sorted(best_fit_by_destination.items())),
        'destination_count': len(best_fit_by_destination),
        'best_fit_state_counts': dict(sorted(best_fit_state_counts.items())),
        'best_fit_status_counts': dict(sorted(best_fit_status_counts.items())),
    }

def _build_compare_rows_by_preset(ids_raw, loadout_config, perk_config, formula_ledger, state_mode: str, default_preset: str, ep_oracle: dict, perk_state: str, forced_preset_perk_states: dict | None = None):
    compare_rows_by_preset = {}
    compare_publishable_rows_by_preset = {}

    perk_state_by_preset = {}
    perk_materialized_by_preset = {}

    def _materialize(preset_name: str, forced_perk_state: str | None = None):
        state = compile_account_state(ids_raw, default_preset=preset_name, loadout_config=loadout_config, perk_config=perk_config)
        preset_perk_state = _normalize_perk_state(forced_perk_state) if forced_perk_state is not None else _compare_perk_state_for_preset(preset_name, perk_state, forced_preset_perk_states)
        perks_enabled = _perks_enabled_for_state(state.active_perk_preset, preset_perk_state)
        state_key = f'{preset_name}__perks_{preset_perk_state}' if forced_perk_state is not None else preset_name
        perk_state_by_preset[state_key] = preset_perk_state
        perk_materialized_by_preset[state_key] = perks_enabled
        inputs = compile_stat_inputs(state, preset_name=preset_name, state_mode=state_mode, perks_enabled=perks_enabled)
        statbook_dict = resolve_stats(inputs).to_dict()
        for destination, row in statbook_dict.get('rows', {}).items():
            row['formula_contract'] = _formula_contract(formula_ledger, destination)
        _annotate_display_fields(statbook_dict)
        publishable = _build_publishable_statbook(statbook_dict, formula_ledger)
        _annotate_display_fields(publishable)
        compare_rows_by_preset[state_key] = statbook_dict['rows']
        compare_publishable_rows_by_preset[state_key] = publishable['rows']
        return state

    default_state = _materialize(default_preset)
    required_state_keys = {_compare_state_key_for_destination(dest, default_preset) for dest in ep_oracle}
    if any(key.startswith('Tourney') for key in required_state_keys):
        if 'Tourney' in required_state_keys:
            _materialize('Tourney')
        if 'Tourney__perks_on' in required_state_keys:
            _materialize('Tourney', forced_perk_state='on')
        if 'Tourney__perks_off' in required_state_keys and 'Tourney' not in required_state_keys:
            _materialize('Tourney', forced_perk_state='off')
    if any(key.startswith('Farming__perks_on') for key in required_state_keys):
        _materialize('Farming', forced_perk_state='on')
    if any(key.startswith('Farming__perks_off') for key in required_state_keys) and default_preset != 'Farming':
        _materialize('Farming', forced_perk_state='off')

    package_stage_context = {
        'state_mode': state_mode,
        'perk_state': _normalize_perk_state(perk_state),
        'perk_materialized': _perks_enabled_for_state(default_state.active_perk_preset, _compare_perk_state_for_preset(default_preset, perk_state, forced_preset_perk_states)),
        'perk_state_by_preset': dict(sorted(perk_state_by_preset.items())),
        'perk_materialized_by_preset': dict(sorted(perk_materialized_by_preset.items())),
        'active_perk_preset': default_state.active_perk_preset,
        'default_compare_preset': default_preset,
        'forced_preset_perk_states': dict(sorted((forced_preset_perk_states or {}).items())),
        'active_cards_by_preset': {
            preset_name: list(state.card_presets.get(preset_name, []))
            for preset_name, state in [(default_preset, default_state)]
        },
        'active_modules_by_preset': {
            preset_name: {
                slot: {
                    'primary': selection.primary,
                    'assist': selection.assist,
                }
                for slot, selection in state.module_presets.get(preset_name, {}).items()
            }
            for preset_name, state in [(default_preset, default_state)]
        },
        'modules_inventory': {
            name: {
                'rarity': mod.rarity,
                'level': mod.level,
                'stat': mod.stat,
            }
            for name, mod in default_state.modules_inventory.items()
        },
    }
    for preset_name in compare_rows_by_preset:
        base_preset_name = preset_name.split('__perks_', 1)[0]
        if preset_name == default_preset:
            continue
        state = compile_account_state(ids_raw, default_preset=base_preset_name, loadout_config=loadout_config, perk_config=perk_config)
        package_stage_context['active_cards_by_preset'][base_preset_name] = list(state.card_presets.get(base_preset_name, []))
        package_stage_context['active_modules_by_preset'][base_preset_name] = {
            slot: {
                'primary': selection.primary,
                'assist': selection.assist,
            }
            for slot, selection in state.module_presets.get(base_preset_name, {}).items()
        }
    return default_state, compare_rows_by_preset, compare_publishable_rows_by_preset, package_stage_context





def _is_calculator_scope_row(row) -> bool:
    if row.source_family == 'lab':
        return row.stat_name in LAB_APPLICATION_SCOPE
    if row.source_family == 'vault':
        return row.stat_name not in VAULT_ADMIN_EXCLUDED
    if row.source_family == 'module':
        return row.stat_name not in MODULE_SCOPE_EXCLUDED
    return row.source_family in {'workshop', 'enhancement', 'relic', 'bot', 'guardian', 'uw', 'uw_plus', 'module', 'module_substat', 'card', 'vault', 'lab'}



def _perk_operation_supported(operation: str) -> bool:
    return operation in {
        'multiplier',
        'remaining_fraction',
        'percentage_points_add',
        'count_add',
        'seconds_add',
        'raw_add',
        'set_to',
        'special_unlock',
        'special_reduction',
    }


def _build_perk_coverage_audit(ids_raw, account_state, canonical_stats, perks_input_path: Path):
    from compilers.stat_input_compiler import _load_perk_entities, _load_perk_effects, compile_stat_inputs, PERK_TARGET_DESTINATION_OVERRIDES
    from engine.query_routing import compiler_routing_indexes
    from models.account_state import PerkSelection
    from dataclasses import replace

    perk_entities = _load_perk_entities()
    perk_effects = _load_perk_effects()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()

    audit_perk_presets = {
        '__audit_all_perks__': [PerkSelection(perk_id=perk_id, picks=int(meta.get('max_picks') or 1)) for perk_id, meta in sorted(perk_entities.items())]
    }
    audit_state = replace(
        account_state,
        perk_presets=audit_perk_presets,
        active_perk_preset='__audit_all_perks__',
    )
    audit_rows = [row for row in compile_stat_inputs(audit_state, preset_name=account_state.default_preset, state_mode='start_of_run') if row.source_family == 'perk']
    audit_row_index = Counter()
    sample_row_index = {}
    for row in audit_rows:
        m = re.search(r'perk::(.+?)::effect_(\d+)$', row.contributor_id or '')
        if not m:
            continue
        perk_id, effect_index = m.group(1), m.group(2)
        audit_row_index[(perk_id, effect_index)] += 1
        sample_row_index.setdefault((perk_id, effect_index), row)

    summary = Counter()
    destination_summary = Counter()
    per_perk = []
    for perk_id, meta in sorted(perk_entities.items()):
        effects = perk_effects.get(perk_id, [])
        effect_details = []
        perk_categories = set()
        for effect in effects:
            effect_index = effect.get('effect_index', '').strip()
            operation = effect.get('operation', '').strip()
            target_stat_id = effect.get('target_stat_id', '').strip()
            route_category = 'unbound'
            destination_object_type = None
            destination_id = None
            if target_stat_id in PERK_TARGET_DESTINATION_OVERRIDES:
                destination_object_type, destination_id = PERK_TARGET_DESTINATION_OVERRIDES[target_stat_id]
                route_category = f'routed::{destination_object_type}'
            elif target_stat_id in canon_stats:
                destination_object_type, destination_id = 'canonical_stat', target_stat_id
                route_category = 'routed::canonical_stat_direct'
            else:
                alias_slug = _slug(target_stat_id.replace('_', ' '))
                alias_match = alias_index.get(alias_slug)
                if alias_match is not None:
                    destination_object_type, destination_id = alias_match
                    route_category = f'routed_alias::{destination_object_type}'
            operation_supported = _perk_operation_supported(operation)
            picks = int(meta.get('max_picks') or 1)
            compiled_count = audit_row_index.get((perk_id, effect_index), 0)
            sample_row = sample_row_index.get((perk_id, effect_index))
            expected_rows = picks
            compile_status = 'compiled' if compiled_count >= 1 else 'missing_compiled_row'
            if route_category == 'unbound':
                coverage = 'unbound_target'
            elif not operation_supported:
                coverage = 'unsupported_operation'
            elif compile_status != 'compiled':
                coverage = 'compile_gap'
            elif destination_object_type == 'canonical_stat':
                coverage = 'canonical_stat_routed'
            elif destination_object_type in {'runtime_mechanic_param', 'mechanic_param', 'environment_param', 'meta_progression_param'}:
                coverage = 'runtime_param_routed'
            elif destination_object_type in {'capability', 'account_flag'}:
                coverage = 'capability_routed'
            else:
                coverage = 'other_routed'
            summary[coverage] += 1
            destination_summary[destination_object_type or 'unbound'] += 1
            perk_categories.add(coverage)
            effect_details.append({
                'effect_index': effect_index,
                'target_stat_id': target_stat_id,
                'operation': operation,
                'effect_value': effect.get('effect_value', '').strip(),
                'scope': effect.get('scope', '').strip(),
                'route_category': route_category,
                'destination_object_type': destination_object_type,
                'destination_id': destination_id,
                'operation_supported': operation_supported,
                'compile_status': compile_status,
                'coverage': coverage,
                'compiled_row_count': compiled_count,
                'expected_row_count_from_max_picks': expected_rows,
                'sample_compiled_row': None if sample_row is None else {
                    'destination_object_type': sample_row.destination_object_type,
                    'destination_id': sample_row.destination_id,
                    'value_type': sample_row.value_type,
                    'resolver_id': sample_row.resolver_id,
                    'kb_mapped': sample_row.kb_mapped,
                },
            })
        per_perk.append({
            'perk_id': perk_id,
            'perk_name': meta.get('perk_name'),
            'category': meta.get('category'),
            'max_picks': meta.get('max_picks'),
            'stacking_type': meta.get('stacking_type'),
            'effect_count': len(effect_details),
            'coverage_categories': sorted(perk_categories),
            'effects': effect_details,
        })

    return {
        'entity_count': len(perk_entities),
        'effect_count': sum(len(v) for v in perk_effects.values()),
        'input_file': _relpath_str(perks_input_path),
        'active_perk_state_source': 'external_json_config',
        'summary_by_coverage': dict(sorted(summary.items())),
        'summary_by_destination_object_type': dict(sorted(destination_summary.items())),
        'all_perks_compile_audit_row_count': len(audit_rows),
        'perks': per_perk,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', type=Path, default=ROOT / 'input' / '_IDS.csv')
    parser.add_argument('--out', '--output-dir', dest='out', type=Path, default=ROOT / 'out')
    parser.add_argument('--preset', type=str, default='Farming')
    parser.add_argument('--state-mode', type=str, default='max_progression')
    parser.add_argument('--loadout', type=str, default=str(LOADOUT_CONFIG_PATH))
    parser.add_argument('--perks', type=str, default=str(PERKS_CONFIG_PATH))
    parser.add_argument('--perk-state', type=str, default='auto', choices=['auto', 'on', 'off'])
    args = parser.parse_args()

    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.out.mkdir(parents=True, exist_ok=True)
    ids_raw = parse_ids(args.ids)
    loadout_config = _load_json_config(Path(args.loadout))
    perk_config, perk_config_resolution = _resolve_perk_config(Path(args.perks), args.state_mode, ids_raw=ids_raw)
    formula_ledger = _load_formula_ledger(FORMULA_LEDGER_PATH)
    ep_oracle = _load_ep_oracle(ROOT / 'input' / 'EP_Export.csv')
    account_state, compare_rows_by_preset, compare_publishable_rows_by_preset, package_stage_context = _build_compare_rows_by_preset(
        ids_raw=ids_raw,
        loadout_config=loadout_config,
        perk_config=perk_config,
        formula_ledger=formula_ledger,
        state_mode=args.state_mode,
        default_preset=args.preset,
        ep_oracle=ep_oracle,
        perk_state=args.perk_state,
    )
    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, args.perk_state)
    stat_inputs = compile_stat_inputs(account_state, preset_name=args.preset, state_mode=args.state_mode, perks_enabled=perks_enabled)
    statbook = resolve_stats(stat_inputs)
    statbook_dict = statbook.to_dict()
    for destination, row in statbook_dict.get('rows', {}).items():
        row['formula_contract'] = _formula_contract(formula_ledger, destination)
    _annotate_display_fields(statbook_dict)
    statbook_publishable_dict = _build_publishable_statbook(statbook_dict, formula_ledger)
    _annotate_display_fields(statbook_publishable_dict)

    state_matrix = {}
    for state_mode in SUPPORTED_STATE_MODES:
        matrix_inputs = compile_stat_inputs(account_state, preset_name=args.preset, state_mode=state_mode, perks_enabled=perks_enabled)
        matrix_statbook = resolve_stats(matrix_inputs).to_dict()
        state_matrix[state_mode] = {
            'support': state_mode_support(state_mode),
            'input_count': len(matrix_inputs),
            'mapped_input_count': sum(1 for row in matrix_inputs if row.kb_mapped),
            'resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('resolved_stat_count', 0),
            'partially_resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('partially_resolved_stat_count', 0),
        }

    ep_compare = _build_ep_compare(ep_oracle, compare_rows_by_preset, formula_ledger, package_stage_context, ep_stage_context_for_destination=_ep_stage_context_for_destination, compare_state_key_for_destination=_compare_state_key_for_destination, contributor_snapshot=_contributor_snapshot, apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions, formula_contract=_formula_contract, normalize_compare_values=_normalize_compare_values)
    ep_compare_publishable = _build_ep_compare(ep_oracle, compare_publishable_rows_by_preset, formula_ledger, package_stage_context, ep_stage_context_for_destination=_ep_stage_context_for_destination, compare_state_key_for_destination=_compare_state_key_for_destination, contributor_snapshot=_contributor_snapshot, apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions, formula_contract=_formula_contract, normalize_compare_values=_normalize_compare_values)
    _annotate_compare_display_fields(ep_compare)
    _annotate_compare_display_fields(ep_compare_publishable)
    current_compare_summary = _build_compare_status_summary(ep_compare_publishable)

    projected_account_state, projected_compare_rows_by_preset, projected_compare_publishable_rows_by_preset, projected_stage_context = _build_compare_rows_by_preset(
        ids_raw=ids_raw,
        loadout_config=loadout_config,
        perk_config=perk_config,
        formula_ledger=formula_ledger,
        state_mode='max_progression',
        default_preset=args.preset,
        ep_oracle=ep_oracle,
        perk_state=args.perk_state,
    )
    projected_ep_compare_publishable = _build_ep_compare(ep_oracle, projected_compare_publishable_rows_by_preset, formula_ledger, projected_stage_context, ep_stage_context_for_destination=_ep_stage_context_for_destination, compare_state_key_for_destination=_compare_state_key_for_destination, contributor_snapshot=_contributor_snapshot, apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions, formula_contract=_formula_contract, normalize_compare_values=_normalize_compare_values)
    _annotate_compare_display_fields(projected_ep_compare_publishable)
    projected_compare_summary = _build_compare_status_summary(projected_ep_compare_publishable)

    unmapped_examples = {}
    for row in stat_inputs:
        if not row.kb_mapped and row.source_family not in unmapped_examples:
            unmapped_examples[row.source_family] = row.stat_name

    mapped_counter = Counter(row.source_family for row in stat_inputs if row.kb_mapped)
    total_counter = Counter(row.source_family for row in stat_inputs)

    card_preset_sizes = {name: len(cards) for name, cards in account_state.card_presets.items()}
    card_slot_limit_exceeded = {name: size for name, size in card_preset_sizes.items() if account_state.card_slots_unlocked is not None and size > account_state.card_slots_unlocked}

    resolved_surface_count = statbook.diagnostics.get('resolved_stat_count', 0)
    partial_surface_count = statbook.diagnostics.get('partially_resolved_stat_count', 0)
    mapped_input_count = sum(1 for row in stat_inputs if row.kb_mapped)
    total_input_count = len(stat_inputs)
    family_burn_down = {
        family: {
            'mapped': mapped_counter.get(family, 0),
            'total': total_counter.get(family, 0),
            'pct': _safe_pct(mapped_counter.get(family, 0), total_counter.get(family, 0)),
        }
        for family in sorted(total_counter)
    }
    scoped_rows = [row for row in stat_inputs if _is_calculator_scope_row(row)]
    scoped_total = len(scoped_rows)
    scoped_mapped = sum(1 for row in scoped_rows if row.kb_mapped)
    scope_excluded_rows = [row for row in stat_inputs if not _is_calculator_scope_row(row)]
    scoped_family_totals = Counter(row.source_family for row in scoped_rows)

    audits = _build_publish_gate_audits(stat_inputs, statbook_publishable_dict, ep_compare_publishable, formula_ledger)
    kb_incomplete_areas = _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger)
    kb_gap_register = _build_kb_gap_register(kb_incomplete_areas, audits)
    ep_compare_publishable = _ensure_compare_authoritative_verdict_fields(ep_compare_publishable)
    line_verification = _build_line_by_line_verification(statbook_publishable_dict, ep_compare_publishable, formula_ledger, _formula_contract)
    line_verification = _ensure_line_verification_authoritative_verdict_fields(line_verification)
    survivor_closure_report = _build_survivor_closure_report(ep_compare_publishable, line_verification)
    verification_counter = Counter(v['verification_status'] for v in line_verification.values())
    diagnostics = {
        'section_names': list(ids_raw.raw_sections.keys()),
        'section_row_counts': {k: len(v) for k, v in ids_raw.raw_sections.items()},
        'default_preset': args.preset,
        'state_mode': args.state_mode,
        'perk_config_resolution': perk_config_resolution,
        'state_mode_support': state_mode_support(args.state_mode),
        'supported_state_modes': list(SUPPORTED_STATE_MODES),
        'state_matrix': state_matrix,
        'stat_input_count': len(stat_inputs),
        'statbook_row_count': len(statbook.rows),
        'engine_status': statbook.diagnostics.get('resolver_status'),
        'publish_status': statbook_publishable_dict.get('diagnostics', {}).get('oracle_policy'),
        'formula_ledger_version': formula_ledger.get('version'),
        'ep_compare_stage_rules': {
            'default_compare_preset': 'Farming',
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'ep_progression_state': 'max_progression',
            'ep_workshop_state': 'derived_from_max_progression',
            'ep_run_state_default': 'farming',
            'ep_run_state_tourney_offense': 'tourney_present',
            'package_compare_capability': {
                'progression_state': 'dynamic_current_or_projected_max_by_state_mode',
                'workshop_state': 'dynamic_current_or_projected_max_by_state_mode',
                'perk_state': args.perk_state,
                'perk_materialization': perks_enabled,
                'perk_ids_parser_support': False,
                'perk_external_config_support': True,
                'perk_account_state_support': True,
                'perk_stat_input_support': True,
                'perk_resolver_support': True,
                'loadout_external_config_support': True,
                'active_perk_preset': account_state.active_perk_preset,
                'state_mode': args.state_mode,
            },
            'notes': [
                'EP export compare uses run-situation policy: offense surfaces use Tourney loadout with perks off; non-offense surfaces use Farming by default and follow the selected engine perk state.',
                'EP export max progression implies max workshop and farming-side perk application beyond the current IDS/loadout-present package state.',
                f"The current package can store externally selected perk presets from {_relpath_str(Path(args.perks))}, compile perk stat inputs, and resolve supported perk contributors into final stats.",
                'Perk selections are not parsed from IDS itself; they must be supplied explicitly when a run state needs them.',
                'Perk application is controlled at engine scope via --perk-state auto|on|off; perks are either materialized for the run or fully disabled.',
                'When values do not match and EP uses unsupported stage facets, compare status is stage_scope_mismatch rather than a hard formula mismatch.',
                'Max Recovery EP export is treated as a non-comparable health-at-cap surface, not a multiplier.'
            ],
        },
        'destination_type_schema': statbook.diagnostics.get('destination_type_schema', {}),
        'mapped_stat_input_count': mapped_input_count,
        'unmapped_stat_input_count': sum(1 for row in stat_inputs if not row.kb_mapped),
        'resolved_stat_count': resolved_surface_count,
        'partially_resolved_stat_count': partial_surface_count,
        'burn_down': {
            'input_mapping_pct': _safe_pct(mapped_input_count, total_input_count),
            'fully_resolved_surface_pct_of_inputs': _safe_pct(resolved_surface_count, total_input_count),
            'resolved_or_partial_surface_pct_of_inputs': _safe_pct(resolved_surface_count + partial_surface_count, total_input_count),
            'family_mapping_pct': family_burn_down,
            'calculator_scope_total_inputs': scoped_total,
            'calculator_scope_mapped_inputs': scoped_mapped,
            'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
            'calculator_scope_excluded_inputs': len(scope_excluded_rows),
            'calculator_scope_excluded_examples': sorted({row.stat_name for row in scope_excluded_rows})[:20],
            'calculator_scope_family_totals': dict(sorted(scoped_family_totals.items())),
            'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.kb_mapped})[:20],
            'note': 'calculator_scope excludes preserved-only lab/admin/runtime rows and grouping/admin surfaces that are intentionally outside the current calculator publish surface.',
        },
        'tests_passed': 'not_run_by_run_stats',
        'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
        'calculator_scope_excluded_inputs': len(scope_excluded_rows),
        'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.kb_mapped})[:20],
        'card_slots_unlocked': account_state.card_slots_unlocked,
        'active_perk_preset': account_state.active_perk_preset,
        'configured_perk_presets': {name: [selection.perk_id for selection in selections] for name, selections in account_state.perk_presets.items()},
        'active_card_preset': account_state.active_card_preset,
        'active_module_preset': account_state.active_module_preset,
        'perk_input_file': _relpath_str(Path(args.perks)),
        'compare_package_value_provenance': {
            'statbook_default_output_preset': args.preset,
            'ep_compare_uses_rows_by_preset': True,
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'note': 'ep_oracle_compare package_value may differ from statbook.json when compare_preset differs from the default output preset.',
        },
        'kb_incomplete_areas': kb_incomplete_areas,
        'kb_gap_register': kb_gap_register,
        'blocked_formula_contract_count': kb_incomplete_areas['summary']['blocked_formula_contract_count'],
        'active_unmapped_input_count': kb_incomplete_areas['summary']['active_unmapped_input_count'],
        'resolved_unknown_schema_unit_count': kb_incomplete_areas['summary']['resolved_unknown_schema_unit_count'],
        'ambiguous_relic_semantic_hint_count': kb_incomplete_areas['summary']['ambiguous_relic_semantic_hint_count'],
        'perk_support': {
            'perk_ids_parser_support': False,
            'perk_ids_parser_note': 'Perk selections are not parsed from IDS; they are supplied through external perk config.',
            'perk_external_config_support': True,
            'perk_account_state_support': True,
            'perk_stat_input_support': True,
            'perk_resolver_support': True,
            'perk_state': args.perk_state,
            'perk_materialization': perks_enabled,
        },
        'card_preset_sizes': card_preset_sizes,
        'card_slot_limit_exceeded': card_slot_limit_exceeded,
        'mapped_count_by_family': dict(sorted(mapped_counter.items())),
        'total_count_by_family': dict(sorted(total_counter.items())),
        'unmapped_example_by_family': unmapped_examples,
        'ep_compare_summary': current_compare_summary,
        **current_compare_summary,
        'ep_compare_projection_views': {
            'current_state_mode': {
                'state_mode': args.state_mode,
                'perk_state': args.perk_state,
                'active_perk_preset': account_state.active_perk_preset,
                **current_compare_summary,
            },
            'projected_max_progression': {
                'state_mode': 'max_progression',
                'perk_state': args.perk_state,
                'active_perk_preset': projected_account_state.active_perk_preset,
                **projected_compare_summary,
            },
        },
        'lineage_backed_run_perk_destinations': sorted(COMPARE_DESTINATION_RUN_PERK_FACETS.keys()),
        'compare_layer_destination_unit_inconsistencies': audits.get('compare_layer_destination_unit_inconsistencies', []),
        'audits': audits,
        'line_verification_summary': dict(sorted(verification_counter.items())),
        'presentation': {
            'scope': 'display_fields_only',
            'raw_value_policy': 'preserve_full_precision_raw_numeric_values',
            'abbreviations': ['k', 'M', 'B', 'T', 'q', 'Q', 's', 'S'],
            'percent_policy': 'pct_and_percent_display_render_with_percent_sign',
            'multiplier_policy': 'multiplier_and_multiplier_display_render_with_leading_x',
        },
        'kb_only_health_family_audit': _build_kb_only_health_family_audit(stat_inputs, statbook_publishable_dict['rows']),
        'kb_only_damage_defense_absolute_scope_audit': _build_damage_defabs_scope_audit(account_state, stat_inputs, statbook_publishable_dict['rows']),
        'perk_coverage_audit': _build_perk_coverage_audit(ids_raw, account_state, statbook.diagnostics.get('destination_type_schema', {}), Path(args.perks)),
        'tower_damage_residue_analysis': _build_tower_damage_residue_analysis(projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable),
        'run_perk_residue_analysis': _build_run_perk_residue_analysis(projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable),
        'tradeoff_routing_audit': _build_tradeoff_routing_audit(ids_raw, loadout_config, perk_config, preset=args.preset, state_mode=args.state_mode, perk_state=args.perk_state),
        'perk_contributor_audit': _build_perk_contributor_audit(ids_raw, loadout_config, perk_config, args.state_mode, args.preset),
        'compare_situation_fit_matrix': _build_compare_situation_fit_matrix(ids_raw, loadout_config, perk_config, formula_ledger, ep_oracle),
    }
    diagnostics['survivability_residue_analysis'] = _build_survivability_residue_analysis(ep_compare_publishable, diagnostics['compare_situation_fit_matrix'], statbook_dict)
    diagnostics['tower_regen_closure_report'] = _build_tower_regen_closure_report(ep_compare_publishable)
    diagnostics['tower_hp_semantic_gap_report'] = _build_tower_hp_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_regen_ep_semantic_gap_report'] = _build_tower_regen_ep_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_defense_absolute_semantic_gap_report'] = _build_tower_defense_absolute_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_damage_runtime_gap_report'] = _build_tower_damage_runtime_gap_report(ep_compare_publishable)
    diagnostics['compare_situation_policy'] = {
        'tournament': {'preset': 'Tourney', 'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Tourney', 'off')},
        'farming': {'preset': 'Farming', 'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Farming', args.perk_state)},
        'milestone_engine': {'preset': args.preset, 'perk_state': package_stage_context.get('perk_state_by_preset', {}).get(args.preset, args.perk_state)},
        'milestone_compare_policy': {'preset': 'Milestone', 'perk_state': 'on', 'note': 'Milestone is a real engine preset with perks on, but EP compare excludes milestone loadout.'},
        'policy_note': 'Perks are controlled by run situation. Tournament compare uses Tourney loadout with perks off; farming follows the selected engine perk state; milestone is a real engine preset with perks on, but EP compare excludes milestone loadout.',
    }
    diagnostics['perk_support'] = diagnostics['ep_compare_stage_rules']['package_compare_capability']
    stale_outputs = [
        'ep_oracle_compare_backfilled.json',
        'statbook_oracle_backfilled.json',
        'destination_formula_ledger.json',
        'forensic_debug_focus.json',
    ]
    for stale_name in stale_outputs:
        stale_path = args.out / stale_name
        if stale_path.exists():
            stale_path.unlink()
    (args.out / 'diagnostics.json').write_text(json.dumps(_json_sanitize(diagnostics), indent=2, default=str))
    (args.out / 'account_state.json').write_text(json.dumps(_json_sanitize(account_state.to_dict()), indent=2, default=str))
    (args.out / 'stat_inputs.json').write_text(json.dumps(_json_sanitize([row.to_dict() for row in stat_inputs]), indent=2, default=str))
    (args.out / 'statbook.json').write_text(json.dumps(_json_sanitize(statbook_dict), indent=2, default=str))
    (args.out / 'statbook_publishable.json').write_text(json.dumps(_json_sanitize(statbook_publishable_dict), indent=2, default=str))
    (args.out / 'ep_oracle_compare.json').write_text(json.dumps(_json_sanitize(ep_compare_publishable), indent=2, default=str))
    (args.out / 'line_by_line_verification.json').write_text(json.dumps(_json_sanitize(line_verification), indent=2, default=str))
    (args.out / 'survivor_closure_report.json').write_text(json.dumps(_json_sanitize(survivor_closure_report), indent=2, default=str))
    (args.out / 'tower_regen_closure_report.json').write_text(json.dumps(_json_sanitize(diagnostics['tower_regen_closure_report']), indent=2, default=str))
    (args.out / 'tower_hp_semantic_gap_report.json').write_text(json.dumps(_json_sanitize(diagnostics['tower_hp_semantic_gap_report']), indent=2, default=str))
    (args.out / 'tower_regen_ep_semantic_gap_report.json').write_text(json.dumps(_json_sanitize(diagnostics['tower_regen_ep_semantic_gap_report']), indent=2, default=str))
    (args.out / 'tower_defense_absolute_semantic_gap_report.json').write_text(json.dumps(_json_sanitize(diagnostics['tower_defense_absolute_semantic_gap_report']), indent=2, default=str))
    (args.out / 'tower_damage_runtime_gap_report.json').write_text(json.dumps(_json_sanitize(diagnostics['tower_damage_runtime_gap_report']), indent=2, default=str))
    (args.out / 'state_matrix.json').write_text(json.dumps(_json_sanitize(state_matrix), indent=2, default=str))
    optimizer_scores = compute_optimizer_scores(statbook_dict)
    (args.out / 'optimizer_scores.json').write_text(json.dumps(_json_sanitize(optimizer_scores), indent=2, default=str))
    verification_rows = [
        {
            'destination': k,
            **v,
        }
        for k, v in line_verification.items()
    ]
    verification_df = pd.DataFrame(verification_rows)
    verification_df.to_csv(args.out / 'line_by_line_verification.csv', index=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
