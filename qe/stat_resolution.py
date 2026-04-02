"""Quarantined report/compat statbook resolver.

This module is explicitly compat/report-only and is not an active authority owner for
native QE runtime composition. Native simulator-facing paths must route through
`qe.routing` declared-family query/statbook APIs and bounded resolver helpers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from qe.contracts import (
    compat_surface_from_legacy_capability,
    compat_surface_from_legacy_canonical,
    compat_surface_from_legacy_context,
    compat_surface_from_legacy_cosmetic,
    compat_surface_from_legacy_flag,
    compat_surface_from_legacy_mechanic,
    compat_surface_from_legacy_runtime,
    to_legacy_surface_id,
)
from qe.models import StatInput
from qe.models import StatBook, StatRow

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATHS = [
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'canonical-stats.yaml',
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'mechanic-params.yaml',
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'environment-params.yaml',
]

_DELTA_SUCCESSORS_BY_BUCKET_KEY: dict[str, tuple[str, ...]] = {
    'canonical_stat::tower_hp': ('canonical_stat::wall_hp',),
    'canonical_stat::tower_regen': ('canonical_stat::wall_regen',),
    'canonical_stat::tower_damage': ('canonical_stat::tower_land_mine_damage',),
    'canonical_stat::tower_crit_chance_pct': ('canonical_stat::tower_land_mine_damage',),
    'canonical_stat::tower_crit_multiplier': ('canonical_stat::tower_land_mine_damage',),
    'canonical_stat::tower_supercrit_chance_pct': ('canonical_stat::tower_land_mine_damage',),
    'canonical_stat::tower_supercrit_multiplier': ('canonical_stat::tower_land_mine_damage',),
    'canonical_stat::coins_per_kill_bonus': ('canonical_stat::coin_kill_multiplier',),
    'canonical_stat::free_upgrade_multiplier': (
        'canonical_stat::free_attack_upgrade_chance_pct',
        'canonical_stat::free_defense_upgrade_chance_pct',
        'canonical_stat::free_utility_upgrade_chance_pct',
    ),
}


def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)


def _compat_mech(destination_id: str) -> str:
    return compat_surface_from_legacy_mechanic(destination_id)


def _compat_runtime(destination_id: str) -> str:
    return compat_surface_from_legacy_runtime(destination_id)


def _compat_flag(destination_id: str) -> str:
    return compat_surface_from_legacy_flag(destination_id)


def _compat_context(destination_id: str) -> str:
    return compat_surface_from_legacy_context(destination_id)


def _compat_cap(destination_id: str) -> str:
    return compat_surface_from_legacy_capability(destination_id)


def _compat_cosmetic(destination_id: str) -> str:
    return compat_surface_from_legacy_cosmetic(destination_id)


def _canonical_bucket_key(destination_id: str) -> str:
    return f'canonical_stat::{destination_id}'


_RESOLVED_ROW_ALIAS_KEYS = {
    _state('free_upgrade_multiplier'): 'support_surface::free_upgrade_multiplier',
}


def _resolved_row_lookup(resolved_rows: Dict[str, StatRow], row_key: str) -> StatRow | None:
    row = resolved_rows.get(row_key)
    if row is not None:
        return row
    alias_key = _RESOLVED_ROW_ALIAS_KEYS.get(str(row_key))
    if alias_key is not None:
        row = resolved_rows.get(alias_key)
        if row is not None:
            return row
    legacy_key = to_legacy_surface_id(str(row_key))
    if legacy_key != row_key:
        row = resolved_rows.get(legacy_key)
        if row is not None:
            return row
    return None


def _resolved_float_lookup(resolved_rows: Dict[str, StatRow], row_key: str) -> float | None:
    row = _resolved_row_lookup(resolved_rows, row_key)
    if row is None or row.final_value is None:
        return None
    return _as_float(row.final_value)


def _resolved_bool_lookup(resolved_rows: Dict[str, StatRow], row_key: str) -> bool | None:
    row = _resolved_row_lookup(resolved_rows, row_key)
    if row is None:
        return None
    if row.final_value is None:
        return None
    return bool(row.final_value)


@lru_cache(maxsize=1)
def _load_canonical_stats() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for path in CONTRACT_PATHS:
        data = yaml.safe_load(path.read_text())
        for domain, entries in data['domains'].items():
            for entry in entries:
                out[entry['id']] = {
                    'domain': domain,
                    'unit': entry['unit'],
                    'resolver': entry['resolver'],
                }
    return out


def _destination_type_schema(destination_id: str, meta: Dict[str, str]) -> Dict[str, object]:
    unit = meta.get('unit', 'unknown')
    resolver = meta.get('resolver', 'unknown')
    allowed = {'resolved_value', 'flat', 'pct', 'multiplier', 'percent_display', 'multiplier_display', 'bool', 'count'}
    # Native bounded timing/runtime rows already carry concrete unit value_types such as
    # "seconds"; allow those exact unit tokens through the publish gate instead of forcing
    # them to masquerade as generic resolved_value rows.
    if unit and unit != 'unknown':
        allowed.add(unit)
    expected_semantics = []
    if unit == 'pct':
        expected_semantics = ['percentage_points', 'percentage_multiplier', 'resolved_percent']
    elif unit == 'multiplier':
        expected_semantics = ['base_multiplier', 'multiplier_factor', 'multiplier_display']
    elif unit in {'seconds', 'm', 'rpm', 'count', 'hp', 'damage', 'hp_per_second', 'attacks_per_second', 'damage_block', 'force', 'cash', 'coins'}:
        expected_semantics = ['resolved_unit_value', 'unit_multiplier']
    else:
        expected_semantics = ['resolved_numeric', 'percentage_points', 'multiplier_display', 'multiplier_factor']
    overrides = {
        'tower_attack_speed': ['resolved_unit_value', 'unit_multiplier', 'percentage_points'],
        'tower_crit_multiplier': ['base_multiplier', 'multiplier_factor', 'multiplier_display', 'percentage_points'],
        'coin_kill_multiplier': ['base_multiplier', 'multiplier_factor', 'multiplier_display', 'percentage_points', 'resolved_numeric'],
        'coins_per_kill_bonus': ['base_multiplier', 'multiplier_factor', 'multiplier_display', 'percentage_points', 'resolved_numeric'],
        'coin_bonus_multiplier': ['multiplier_factor', 'multiplier_display', 'resolved_numeric'],
        'coins_multiplier': ['multiplier_factor', 'multiplier_display', 'percentage_points', 'resolved_numeric'],
        'all_coin_bonus_multiplier': ['multiplier_factor', 'multiplier_display', 'resolved_numeric'],
        'cash_kill_multiplier': ['base_multiplier', 'multiplier_factor', 'multiplier_display', 'percentage_points', 'resolved_numeric'],
        'wall_thorns_damage_pct': ['percentage_points', 'percentage_multiplier', 'resolved_percent', 'resolved_numeric'],
        'tower_damage': ['resolved_unit_value', 'unit_multiplier', 'percentage_points', 'multiplier_display', 'multiplier_factor'],
        'tower_hp': ['resolved_unit_value', 'unit_multiplier', 'percentage_points', 'multiplier_display', 'multiplier_factor'],
        'tower_regen': ['resolved_unit_value', 'unit_multiplier', 'percentage_points', 'multiplier_factor'],
        'wall_hp': ['resolved_unit_value', 'unit_multiplier', 'percentage_points', 'multiplier_display', 'multiplier_factor'],
        'wall_regen': ['resolved_unit_value', 'unit_multiplier', 'percentage_points', 'multiplier_display', 'multiplier_factor'],
    }
    if destination_id in overrides:
        expected_semantics = overrides[destination_id]
    explicit_caps = {}
    if destination_id in CANONICAL_PCT_CAPS:
        explicit_caps['max'] = CANONICAL_PCT_CAPS[destination_id]
    return {
        'unit': unit,
        'resolver': resolver,
        'allowed_input_value_types': sorted(allowed),
        'disallowed_input_value_types': ['level', 'raw_text', 'display_token', 'missing_inventory'],
        'publish_gate_rules': [
            'no_numeric_publish_if_any_contributor_is_unresolved',
            'no_numeric_publish_if_any_contributor_value_type_is_level',
            'no_numeric_publish_if_any_contributor_is_semantically_incompatible',
        ],
        'expected_input_semantics': expected_semantics,
        'explicit_caps': explicit_caps,
    }


def _row_semantic_class(row: StatInput) -> str:
    if isinstance(row.value, bool):
        return 'bool'
    vt = row.value_type or ''
    if vt == 'level':
        return 'unresolved_level'
    if vt in {'raw_text', 'display_token', 'missing_inventory'}:
        return 'unresolved_non_numeric'
    if row.value is None:
        return 'unresolved_none'
    if vt == 'percent_display':
        return 'percentage_points'
    if vt == 'multiplier_display':
        return 'multiplier_display'
    if vt == 'pct':
        return 'percentage_points'
    if vt == 'multiplier':
        return 'multiplier_factor'
    if vt == 'count':
        return 'resolved_numeric'
    return 'resolved_numeric'


def _is_unresolved_contributor(row: StatInput) -> bool:
    note = (row.notes or '').lower()
    return row.value_type in {'level', 'raw_text', 'display_token', 'missing_inventory'} or row.value is None or 'unresolved' in note


def _is_semantically_compatible(row: StatInput, destination_object_type: str, destination_id: str, schema: Dict[str, object]) -> bool:
    if destination_object_type == 'capability':
        if destination_id.endswith('.enabled'):
            return isinstance(row.value, bool) or row.value_type == 'bool'
        if destination_id.endswith('.count'):
            return row.value_type in {'resolved_value', 'flat'} and _as_float(row.value) is not None
        return (isinstance(row.value, bool) or row.value_type == 'bool' or
                (row.value_type in {'resolved_value', 'flat'} and _as_float(row.value) is not None))
    if destination_object_type == 'account_flag':
        if destination_id.endswith('.automation') or destination_id.endswith('.presets') or destination_id.endswith('.adjuster') or destination_id.endswith('.sliders') or destination_id.endswith('.reroll'):
            return isinstance(row.value, bool) or row.value_type == 'bool'
        return (isinstance(row.value, bool) or row.value_type == 'bool' or
                (row.value_type in {'resolved_value', 'flat', 'pct', 'percent_display', 'multiplier', 'multiplier_display'} and _as_float(row.value) is not None))
    if row.value_type not in set(schema['allowed_input_value_types']) and not isinstance(row.value, bool):
        return False
    semantic = _row_semantic_class(row)
    if semantic.startswith('unresolved'):
        return False
    expected = set(schema['expected_input_semantics'])
    if semantic == 'bool':
        return 'bool' in expected or destination_object_type == 'capability'
    if semantic == 'percentage_points':
        return 'percentage_points' in expected or 'resolved_percent' in expected or schema['unit'] in {'pct', 'multiplier'}
    if semantic == 'multiplier_display':
        return 'multiplier_display' in expected or 'multiplier_factor' in expected or schema['unit'] == 'multiplier'
    if semantic == 'multiplier_factor':
        return 'multiplier_factor' in expected or 'unit_multiplier' in expected or schema['unit'] in {'pct', 'multiplier'}
    return True


def _publish_gate_check(destination_object_type: str, destination_id: str, contributors: List[StatInput], meta: Dict[str, str]) -> Tuple[bool, str, List[str], Dict[str, object]]:
    schema = _destination_type_schema(destination_id, meta)
    failures = []
    bad = []
    for row in contributors:
        reason = None
        if _is_unresolved_contributor(row):
            reason = 'unresolved_or_level'
        elif not _is_semantically_compatible(row, destination_object_type, destination_id, schema):
            reason = 'semantically_incompatible'
        if reason:
            bad.append(f"{row.source_family}:{row.source_name}:{reason}:{row.value_type}")
    if bad:
        failures.append('publish_gate_blocked')
        return False, 'Publish gate blocked numeric output because one or more contributors are unresolved, still typed as level, or semantically incompatible.', bad, schema
    return True, 'Publish gate passed.', bad, schema


def _contributor_measure(row: StatInput) -> str:
    if row.contributor_id and '__' in row.contributor_id:
        return row.contributor_id.split('__')[-1]
    if row.destination_id and 'module_substat' in row.source_family:
        unit_hint = ''
        return 'pct' if isinstance(row.value, float) and abs(row.value) < 1 else 'flat'
    return row.value_type


def _as_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _multiplier_from_value(v: float) -> float:
    return v if v >= 1.0 else 1.0 + v


def _module_substat_multiplier(row: StatInput, v: float) -> float:
    if row.value_type == 'percent_display':
        return 1.0 + (v / 100.0)
    if row.value_type == 'multiplier_display':
        return 1.0 + v
    return _multiplier_from_value(v)


def _canonical_source_multiplier(destination_id: str, row: StatInput, v: float) -> float:
    if row.source_family == 'module_substat':
        return _module_substat_multiplier(row, v)
    if row.source_family == 'enhancement':
        return v
    if row.source_family == 'perk' and row.value_type == 'multiplier':
        return v
    if row.source_family == 'relic' and destination_id in {'tower_defense_pct'}:
        return 1.0 + v
    return _multiplier_from_value(v)




def _resolve_base_times_post_multipliers(destination_id: str, contributors: List[StatInput], schema: Dict[str, object], *, include_relic_vault_as_bonus: bool = True, note_label: str = 'Shared base-times-post-multipliers family') -> Tuple[float | None, str, str, Dict[str, object]]:
    workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    lab_mult = next((_as_float(r.value) for r in [r for r in contributors if r.source_family == 'lab']), 1.0) or 1.0
    final = workshop * lab_mult
    for fam in ('enhancement', 'card', 'module', 'module_substat', 'perk'):
        for r in [r for r in contributors if r.source_family == fam]:
            v = _as_float(r.value)
            if v is None:
                continue
            if fam == 'module_substat' and r.value_type == 'percent_display':
                final *= (1.0 + v / 100.0)
            else:
                final *= _canonical_source_multiplier(destination_id, r, v)
    if include_relic_vault_as_bonus:
        for fam in ('relic', 'vault'):
            for r in [r for r in contributors if r.source_family == fam]:
                v = _as_float(r.value)
                if v is not None:
                    final *= (1.0 + v)
    return final, 'resolved', f'{note_label}: workshop x lab x post multipliers.', schema


def _resolve_decimal_base_times_post_multipliers(destination_id: str, contributors: List[StatInput], schema: Dict[str, object], *, divisor: float = 1000.0, note_label: str = 'Promoted decimal-base-times-post-multipliers family') -> Tuple[float | None, str, str, Dict[str, object]]:
    workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    final = workshop / divisor
    lab_mult = next((_as_float(r.value) for r in contributors if r.source_family == 'lab'), 1.0) or 1.0
    final *= lab_mult
    for fam in ('enhancement', 'card', 'module', 'module_substat', 'perk'):
        for r in [r for r in contributors if r.source_family == fam]:
            v = _as_float(r.value)
            if v is None:
                continue
            if fam == 'module_substat' and r.value_type == 'percent_display':
                final *= (1.0 + v / 100.0)
            else:
                final *= _canonical_source_multiplier(destination_id, r, v)
    for fam in ('relic', 'vault'):
        for r in [r for r in contributors if r.source_family == fam]:
            v = _as_float(r.value)
            if v is not None:
                final *= (1.0 + v)
    return final, 'resolved', f'{note_label}: decimal workshop bonus x lab x post multipliers.', schema


def _resolve_additive_base_plus_bonuses_pct(destination_id: str, contributors: List[StatInput], schema: Dict[str, object], *, note_label: str = 'Promoted additive-base-plus-bonuses pct family') -> Tuple[float | None, str, str, Dict[str, object]]:
    workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    additive_pp = 0.0
    for r in contributors:
        if r.source_family == 'workshop':
            continue
        v = _as_float(r.value)
        if v is None:
            continue
        additive_pp += v
    final = workshop + additive_pp
    return final, 'resolved', f'{note_label}: workshop base plus additive percent-point bonuses, uncapped.', schema


def _resolve_exact_max_rend_value(contributors: List[StatInput]) -> float | None:
    enhancement_multiplier = 1.0
    has_enhancement = False
    lab_bonus = 0.0
    module_pct_bonus = 0.0
    for row in contributors:
        v = _as_float(row.value)
        if v is None:
            continue
        if row.source_family == 'enhancement':
            enhancement_multiplier *= v
            has_enhancement = True
        elif row.source_family == 'lab':
            if row.value_type == 'resolved_value':
                lab_bonus += v
        elif row.source_family == 'module_substat':
            if row.value_type == 'percent_display':
                module_pct_bonus += v / 100.0
            else:
                module_pct_bonus += v
    if not has_enhancement:
        return None
    pre_enhancement_cap = 8.0 + lab_bonus + (8.0 * module_pct_bonus)
    return pre_enhancement_cap * enhancement_multiplier


def _resolve_survivability_base_times_multipliers(destination_id: str, contributors: List[StatInput], schema: Dict[str, object], *, module_substat_family: str = 'generic', note_label: str = 'Promoted survivability base-times-multipliers family') -> Tuple[float | None, str, str, Dict[str, object]]:
    workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    final = workshop
    module_rows: List[StatInput] = []
    for r in [r for r in contributors if r.source_family != 'workshop']:
        v = _as_float(r.value)
        if v is None:
            continue
        if r.source_family == 'module_substat' and module_substat_family == 'tower_regen_ep':
            module_rows.append(r)
            continue
        if r.source_family in {'relic', 'vault'}:
            final *= (1.0 + v)
        elif r.source_family == 'module_substat' and r.value_type == 'percent_display':
            final *= (1.0 + v / 100.0)
        else:
            final *= _canonical_source_multiplier(destination_id, r, v)
    if module_substat_family == 'tower_regen_ep' and module_rows:
        final *= _tower_regen_compare_module_multiplier(module_rows)
    return final, 'resolved', f'{note_label}: workshop x survivability multipliers.', schema

# Source-backed stat caps: loaded from KB table, not defined as literals here.
# Source: kb/global-rules/tables/game-mechanic-stat-caps.csv
from qe.kb_surfaces import CANONICAL_PCT_CAPS  # noqa: E402

BASE_FLAT_MULTIPLIED_STATS = {
    'tower_attack_speed',
    'tower_damage',
    'tower_hp',
    'tower_regen',
}

BASE_MULTIPLIER_STATS = {
    'coin_kill_multiplier',
    'cash_kill_multiplier',
    'cells_kill_multiplier',
    'tower_crit_multiplier',
    'tower_damage_per_meter_multiplier',
    'tower_supercrit_multiplier',
    'tower_rend_armor_multiplier',
    'free_upgrade_multiplier',
    'recovery_package_multiplier',
    'wall_fortification_multiplier',
}

DIRECT_ADDITIVE_ONLY_STATS = {
    'free_upgrade_multiplier',
    'recovery_package_multiplier',
    'cells_kill_multiplier',
}

WALL_RATIO_STATS = {
    'wall_thorns_damage_pct',
}


def _tower_regen_compare_module_multiplier(contributors: List[StatInput]) -> float:
    primary_bonus = 0.0
    assist_bonus = 0.0
    for row in contributors:
        v = _as_float(row.value)
        if v is None:
            continue
        note = str(row.notes or '').lower()
        if row.value_type == 'percent_display':
            if 'module_substat_assist' in note:
                # Assist display values are one order smaller than the EP ass_sub input:
                # 40.0 display -> 4.0 ass_sub, then x 10% SAC -> 0.4 effective.
                bonus = v / 10.0
            else:
                bonus = v / 100.0
        elif row.value_type == 'multiplier_display':
            bonus = v
        else:
            bonus = max(0.0, v - 1.0)
        if 'module_substat_assist' in note:
            # Effective Paths / KB eRegen formula uses SUBSTAT = 1 + prim_sub + ass_sub * SAC.
            # Current account compare state resolves SAC = 10% (9 stone sacrifice, 0 lab).
            assist_bonus += bonus * 0.10
        else:
            primary_bonus += bonus
    return 1.0 + primary_bonus + assist_bonus


def _safe_single_or_uniform_resolution(destination_object_type: str, destination_id: str, contributors: List[StatInput]) -> Tuple[float | bool | None, str, str]:
    numeric = []
    for row in contributors:
        v = _as_float(row.value)
        if v is not None:
            numeric.append((row, v))
    bools = [bool(row.value) for row in contributors if isinstance(row.value, bool) or row.value_type == 'bool']
    if destination_object_type in {'capability','account_flag'} and destination_id.endswith('.count') and numeric:
        if len(numeric)==1:
            return numeric[0][1], 'resolved', 'Mapped capability count surface resolved from numeric contributor.'
        return sum(v for _,v in numeric), 'resolved', 'Mapped capability count surface resolved additively from numeric contributors.'
    if bools and len(bools) == len(contributors):
        return all(bools), 'resolved', 'Mapped boolean flag surface resolved with logical-and over all contributors.'
    if len(contributors) == 1:
        row = contributors[0]
        v = _as_float(row.value)
        if v is not None:
            return v, 'resolved', 'Single mapped contributor; direct value preserved.'
        if isinstance(row.value, bool) or row.value_type == 'bool':
            return bool(row.value), 'resolved', 'Single mapped contributor; boolean preserved.'
        if row.value_type in {'display_token', 'raw_text', 'missing_inventory'}:
            return None, 'mapped_not_resolved', 'Single mapped contributor is non-numeric text.'
    if not numeric:
        return None, 'mapped_not_resolved', 'No numeric contributor values available.'

    if len(numeric) >= 1 and len(numeric) < len(contributors):
        nums = [v for _, v in numeric]
        if len(nums) == 1:
            return nums[0], 'resolved', 'Resolved from the available numeric contributor; non-numeric mapped contributors were ignored.'

    suffix = destination_id.split('.')[-1]
    additive_suffixes = (
        'seconds', 'duration', 'cooldown', 'cooldown_seconds', 'duration_seconds',
        'meters', 'range', 'range_m', 'angle', 'angle_degrees', 'count', 'quantity', 'targets',
        'chance', 'chance_pct', 'pct', 'bonus_pct', 'damage_reduction_pct', 'speed_reduction_pct',
        'size', 'radius', 'radius_m', 'amount', 'waves_required_delta'
    )
    multiplier_suffixes = ('multiplier', 'multiplier_x')

    if len(numeric) == len(contributors):
        vals = [v for _, v in numeric]
        if suffix.endswith(additive_suffixes) or destination_id in {'bot.global.range_bonus_m'}:
            return sum(vals), 'resolved', 'Mapped runtime/meta surface resolved with additive suffix rule.'
        if suffix.endswith(multiplier_suffixes):
            prod = 1.0
            for v in vals:
                prod *= _multiplier_from_value(v)
            return prod, 'resolved', 'Mapped runtime/meta surface resolved with multiplier suffix rule.'
        if len(vals) == 1:
            return vals[0], 'resolved', 'Single numeric contributor preserved.'
    return None, 'mapped_not_resolved', 'Mapped destination retained but no validated generic resolver rule applied.'


def _resolve_bucket(destination_object_type: str, destination_id: str, contributors: List[StatInput], meta: Dict[str, str]) -> Tuple[float | None, str, str, Dict[str, object]]:
    """Compat/report delegation wrapper to the active bounded resolver owner in qe.routing."""
    from qe.routing import resolve_bounded_bucket

    return resolve_bounded_bucket(destination_object_type, destination_id, contributors, meta)

def _build_stat_row(
    *,
    bucket_key: str,
    contributors: List[StatInput],
    meta: Dict[str, str],
    final_value: float | None,
    status: str,
    notes: str,
    schema: Dict[str, object],
) -> StatRow:
    return StatRow(
        stat_name=bucket_key,
        final_value=final_value,
        value_type=meta['unit'],
        source_count=len(contributors),
        status=status,
        notes=notes,
        contributors=[c.to_dict() for c in contributors],
        schema=schema,
    )


def _resolve_mapped_rows(
    *,
    mapped_buckets: Dict[str, List[StatInput]],
    canonical_stats: Dict[str, Dict[str, str]],
    existing_rows: Dict[str, StatRow] | None = None,
) -> Dict[str, StatRow]:
    rows: Dict[str, StatRow] = {} if existing_rows is None else existing_rows
    pending: Dict[str, List[StatInput]] = dict(mapped_buckets)

    while pending:
        progress = False
        for bucket_key in list(pending):
            contributors = pending[bucket_key]
            destination_object_type, destination_id = bucket_key.split('::', 1)
            meta = canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'})
            if destination_object_type != 'canonical_stat' and meta.get('unit') == 'unknown':
                meta = {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}
            meta = dict(meta)
            meta['_resolved_rows'] = rows
            final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
            if status == 'mapped_not_resolved':
                continue
            rows[bucket_key] = _build_stat_row(
                bucket_key=bucket_key,
                contributors=contributors,
                meta=meta,
                final_value=final_value,
                status=status,
                notes=notes,
                schema=schema,
            )
            pending.pop(bucket_key, None)
            progress = True
        if progress:
            continue
        for bucket_key, contributors in pending.items():
            destination_object_type, destination_id = bucket_key.split('::', 1)
            meta = canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'})
            if destination_object_type != 'canonical_stat' and meta.get('unit') == 'unknown':
                meta = {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}
            meta = dict(meta)
            meta['_resolved_rows'] = rows
            final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
            rows[bucket_key] = _build_stat_row(
                bucket_key=bucket_key,
                contributors=contributors,
                meta=meta,
                final_value=final_value,
                status=status,
                notes=notes,
                schema=schema,
            )
        pending.clear()
    return rows


def classify_input_routing(row: StatInput) -> str:
    note = str(row.notes or '')
    if 'module_substat_parse_failed:' in note:
        return 'unresolved_module_substat_parse'
    if note.startswith('parser_drop'):
        return 'parser_drop_junk'
    if note.startswith('account_metadata_'):
        return 'account_metadata'
    if note.startswith('capability_policy_'):
        return 'capability_policy'
    if note.startswith('governed_numeric_pending_'):
        return 'governed_numeric_pending_value'
    if row.destination_object_type in {'runtime_mechanic_param', 'mechanic_param', 'account_flag'} and row.destination_id:
        return 'intentionally_non_publish_runtime_only'
    if row.destination_id:
        return 'resolved'
    return 'truly_unrouted_unknown'


def summarize_input_routing(stat_inputs: List[StatInput]) -> dict[str, Any]:
    class_counts = Counter(classify_input_routing(row) for row in stat_inputs)
    family_routed_counts = Counter(row.source_family for row in stat_inputs if row.destination_id)
    family_unrouted_counts = Counter(
        row.source_family for row in stat_inputs if classify_input_routing(row) == 'truly_unrouted_unknown'
    )
    module_substat_parse_failed = [
        row for row in stat_inputs
        if 'module_substat_parse_failed:' in str(row.notes or '')
    ]
    parse_failed_by_substat = Counter(row.stat_name for row in module_substat_parse_failed)
    return {
        'class_counts': dict(sorted(class_counts.items())),
        'routed_input_count': sum(1 for row in stat_inputs if row.destination_id),
        'truly_unrouted_input_count': class_counts.get('truly_unrouted_unknown', 0),
        'routed_count_by_family': dict(sorted(family_routed_counts.items())),
        'truly_unrouted_count_by_family': dict(sorted(family_unrouted_counts.items())),
        'unresolved_contributor_diagnostics': {
            'module_substat_parse_failed_count': len(module_substat_parse_failed),
            'module_substat_parse_failed_by_substat': dict(sorted(parse_failed_by_substat.items())),
        },
    }


def _bucket_stat_inputs(stat_inputs: List[StatInput]) -> tuple[Dict[str, List[StatInput]], Dict[str, List[StatInput]]]:
    mapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)
    unmapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)
    for row in stat_inputs:
        if row.destination_id:
            mapped_buckets[f"{row.destination_object_type}::{row.destination_id}"].append(row)
        else:
            unmapped_buckets[row.stat_name].append(row)
    return mapped_buckets, unmapped_buckets


def _bucket_signature(rows: List[StatInput]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            row.stat_name,
            row.source_family,
            row.source_name,
            row.value,
            row.value_type,
            row.stage,
            row.active,
            row.preset_name,
            row.provenance,
            row.notes,
            row.contributor_id,
            row.destination_object_type,
            row.destination_id,
            row.resolver_id,
            row.kb_mapped,
            row.raw_level,
            row.resolved_value,
            row.resolved_unit,
        )
        for row in rows
    )


def _expand_delta_bucket_keys(changed_bucket_keys: set[str]) -> set[str]:
    expanded = set(changed_bucket_keys)
    queue = list(changed_bucket_keys)
    while queue:
        bucket_key = queue.pop()
        for successor in _DELTA_SUCCESSORS_BY_BUCKET_KEY.get(bucket_key, ()):
            if successor in expanded:
                continue
            expanded.add(successor)
            queue.append(successor)
    return expanded


def _clone_stat_row(row: StatRow) -> StatRow:
    return StatRow(
        stat_name=row.stat_name,
        final_value=row.final_value,
        value_type=row.value_type,
        source_count=row.source_count,
        status=row.status,
        notes=row.notes,
        contributors=[dict(contributor) for contributor in row.contributors],
        schema=None if row.schema is None else dict(row.schema),
    )


def _build_statbook_diagnostics(
    *,
    stat_inputs: List[StatInput],
    rows: Dict[str, StatRow],
    canonical_stats: Dict[str, Dict[str, str]],
    routing_summary: dict[str, Any],
) -> dict[str, Any]:
    family_counts = Counter(row.source_family for row in stat_inputs)
    mapped_family_counts = Counter(row.source_family for row in stat_inputs if row.destination_id)
    resolved_count = sum(1 for row in rows.values() if row.status == 'resolved')
    partial_count = sum(1 for row in rows.values() if row.status == 'partially_resolved')
    unresolved_count = sum(
        1 for key, row in rows.items()
        if not key.startswith('raw::') and row.status not in {'resolved', 'partially_resolved'}
    )
    return {
        'resolver_status': 'publish_gate_enforced_resolution',
        'destination_type_schema': {k: _destination_type_schema(k, v) for k, v in sorted(canonical_stats.items())},
        'mapped_input_count': routing_summary['routed_input_count'],
        'unmapped_input_count': routing_summary['truly_unrouted_input_count'],
        'input_count_by_family': dict(sorted(family_counts.items())),
        'mapped_count_by_family': dict(sorted(mapped_family_counts.items())),
        'input_routing_class_counts': routing_summary['class_counts'],
        'truly_unrouted_count_by_family': routing_summary['truly_unrouted_count_by_family'],
        'unresolved_contributor_diagnostics': routing_summary['unresolved_contributor_diagnostics'],
        'resolved_stat_count': resolved_count,
        'partially_resolved_stat_count': partial_count,
        'mapped_unresolved_stat_count': unresolved_count,
        'notes': [
            'Input routing counts distinguish true unknown/unrouted rows from parser-drop, metadata, capability, governed-pending, and runtime-only classes.',
            'This iteration resolves canonical stats with cautious unit-aware rules and also preserves direct numeric values for single-source mapped runtime/meta/capability surfaces.',
            'Multi-source mechanic params remain fail-closed unless a simple suffix-based generic rule is explicitly safe to apply.',
        ],
    }


def resolve_stats(stat_inputs: List[StatInput]) -> StatBook:
    canonical_stats = _load_canonical_stats()
    mapped_buckets, unmapped_buckets = _bucket_stat_inputs(stat_inputs)
    routing_summary = summarize_input_routing(stat_inputs)

    rows: Dict[str, StatRow] = _resolve_mapped_rows(
        mapped_buckets=mapped_buckets,
        canonical_stats=canonical_stats,
    )

    for stat_name, contributors in unmapped_buckets.items():
        rows[f'raw::{stat_name}'] = StatRow(
            stat_name=stat_name,
            final_value=None,
            value_type='raw_unmapped_input',
            source_count=len(contributors),
            status='unmapped',
            notes='Preserved for traceability. No validated canonical-stat routing or no canonical-stat destination attached yet.',
            contributors=[c.to_dict() for c in contributors],
            schema=None,
        )

    diagnostics = _build_statbook_diagnostics(
        stat_inputs=stat_inputs,
        rows=rows,
        canonical_stats=canonical_stats,
        routing_summary=routing_summary,
    )
    return StatBook(rows=rows, diagnostics=diagnostics)


def resolve_bucket_value(
    destination_object_type: str,
    destination_id: str,
    contributors: List[StatInput],
    *,
    resolved_rows: Dict[str, StatRow] | None = None,
) -> tuple[float | None, str, str, Dict[str, object], Dict[str, str]]:
    canonical_stats = _load_canonical_stats()
    meta = canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'})
    if destination_object_type != 'canonical_stat' and meta.get('unit') == 'unknown':
        meta = {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}
    meta = dict(meta)
    meta['_resolved_rows'] = dict(resolved_rows or {})
    final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
    return final_value, status, notes, schema, meta


def resolve_stats_delta(
    base_statbook: StatBook,
    *,
    base_stat_inputs: List[StatInput],
    target_stat_inputs: List[StatInput],
) -> StatBook:
    canonical_stats = _load_canonical_stats()
    base_mapped_buckets, base_unmapped_buckets = _bucket_stat_inputs(base_stat_inputs)
    target_mapped_buckets, target_unmapped_buckets = _bucket_stat_inputs(target_stat_inputs)
    target_routing_summary = summarize_input_routing(target_stat_inputs)

    changed_bucket_keys = {
        bucket_key
        for bucket_key in set(base_mapped_buckets) | set(target_mapped_buckets)
        if _bucket_signature(base_mapped_buckets.get(bucket_key, [])) != _bucket_signature(target_mapped_buckets.get(bucket_key, []))
    }
    impacted_bucket_keys = _expand_delta_bucket_keys(changed_bucket_keys)
    changed_unmapped_keys = {
        stat_name
        for stat_name in set(base_unmapped_buckets) | set(target_unmapped_buckets)
        if _bucket_signature(base_unmapped_buckets.get(stat_name, [])) != _bucket_signature(target_unmapped_buckets.get(stat_name, []))
    }

    rows: Dict[str, StatRow] = {key: _clone_stat_row(row) for key, row in base_statbook.rows.items()}

    for bucket_key in impacted_bucket_keys:
        if bucket_key not in target_mapped_buckets:
            rows.pop(bucket_key, None)

    impacted_target_buckets = {
        bucket_key: contributors
        for bucket_key, contributors in target_mapped_buckets.items()
        if bucket_key in impacted_bucket_keys
    }
    _resolve_mapped_rows(
        mapped_buckets=impacted_target_buckets,
        canonical_stats=canonical_stats,
        existing_rows=rows,
    )

    for stat_name in changed_unmapped_keys:
        raw_key = f'raw::{stat_name}'
        contributors = target_unmapped_buckets.get(stat_name)
        if not contributors:
            rows.pop(raw_key, None)
            continue
        rows[raw_key] = StatRow(
            stat_name=stat_name,
            final_value=None,
            value_type='raw_unmapped_input',
            source_count=len(contributors),
            status='unmapped',
            notes='Preserved for traceability. No validated canonical-stat routing or no canonical-stat destination attached yet.',
            contributors=[c.to_dict() for c in contributors],
            schema=None,
        )

    diagnostics = _build_statbook_diagnostics(
        stat_inputs=target_stat_inputs,
        rows=rows,
        canonical_stats=canonical_stats,
        routing_summary=target_routing_summary,
    )
    diagnostics['delta_resolution'] = {
        'changed_bucket_count': len(changed_bucket_keys),
        'impacted_bucket_count': len(impacted_bucket_keys),
        'changed_unmapped_count': len(changed_unmapped_keys),
        'changed_bucket_keys': sorted(changed_bucket_keys),
        'impacted_bucket_keys': sorted(impacted_bucket_keys),
    }
    return StatBook(rows=rows, diagnostics=diagnostics)
