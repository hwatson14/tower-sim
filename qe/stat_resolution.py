from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from qe.models import StatInput
from qe.models import StatBook, StatRow

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATHS = [
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'canonical-stats.yaml',
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'mechanic-params.yaml',
    ROOT / 'kb' / 'global-rules' / 'contracts' / 'environment-params.yaml',
]


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
    schema = _destination_type_schema(destination_id, meta)
    publish_ok, publish_note, bad_contributors, schema = _publish_gate_check(destination_object_type, destination_id, contributors, meta)
    if not publish_ok:
        return None, 'mapped_not_resolved', publish_note + (' Offending contributors: ' + ', '.join(bad_contributors[:12]) if bad_contributors else ''), schema
    unit = meta.get('unit', 'unknown')
    resolver = meta.get('resolver', 'unknown')
    add_sum = 0.0
    multiplier_product = 1.0
    additive_pct = 0.0
    consumed = 0
    unsupported = []


    if destination_object_type == 'mechanic_param' and destination_id.startswith('uw.'):
        resolved_rows = meta.get('_resolved_rows', {})
        uw_prefix = '.'.join(destination_id.split('.')[:2])
        unlock_row = resolved_rows.get(f'capability::{uw_prefix}.owned')
        if unlock_row is not None and bool(unlock_row.final_value) is False:
            unit = meta.get('unit', 'unknown')
            if unit == 'count':
                locked_value = 0.0
            elif unit in {'pct', 'multiplier', 'seconds', 'm', 'rpm', 'damage', 'hp_per_second'}:
                locked_value = 0.0
            else:
                locked_value = 0.0
            return locked_value, 'resolved', f'UW unlock-gated to zero because {uw_prefix} is not owned.', schema

        def _fam_rows(*families: str):
            return [r for r in contributors if r.source_family in set(families)]

        def _sum_rows(*families: str, multiplier_display_as_flat: bool = False) -> float:
            total = 0.0
            for r in contributors:
                if families and r.source_family not in set(families):
                    continue
                v = _as_float(r.value)
                if v is None:
                    continue
                total += v
            return total

        def _product_rows(*families: str) -> float:
            product = 1.0
            seen = False
            for r in contributors:
                if families and r.source_family not in set(families):
                    continue
                v = _as_float(r.value)
                if v is None:
                    continue
                product *= _canonical_source_multiplier(destination_id, r, v)
                seen = True
            return product if seen else 1.0

        if destination_id in {
            'uw.golden_tower.bonus_multiplier',
            'uw.spotlight.bonus_multiplier',
            'uw.chain_lightning.damage_multiplier',
            'uw.death_wave.damage_multiplier',
            'uw.poison_swamp.damage_multiplier',
            'uw.smart_missiles.damage_multiplier',
        }:
            base = _sum_rows('uw', 'lab', 'module_substat', multiplier_display_as_flat=True)
            final = base * _product_rows('perk')
            return final, 'resolved', 'UW additive-then-perk-multiplier composition resolved from unified mechanic bucket.', schema

        if destination_id in {
            'uw.black_hole.duration_seconds',
            'uw.black_hole.cooldown_seconds',
            'uw.chrono_field.duration_seconds',
            'uw.chrono_field.cooldown_seconds',
            'uw.golden_tower.duration_seconds',
            'uw.golden_tower.cooldown_seconds',
            'uw.death_wave.cooldown_seconds',
            'uw.spotlight.angle_degrees',
            'uw.black_hole.size_m',
            'uw.chrono_field.range_m',
            'uw.spotlight.missiles_frequency_seconds',
            'uw.smart_missiles.cooldown_seconds',
            'uw.smart_missiles.despawn_time_seconds',
            'uw.smart_missiles.explosion_radius_m',
            'uw.smart_missiles.recharge_barrage_waves',
            'uw.poison_swamp.duration_seconds',
            'uw.poison_swamp.cooldown_seconds',
            'uw.poison_swamp.radius_m',
            'uw.poison_swamp.stun_duration_seconds',
            'uw.inner_land_mines.cooldown_seconds',
            'uw.inner_land_mines.blast_radius_m',
            'uw.inner_land_mines.rotation_speed',
            'uw.inner_land_mines.chrono_jump_seconds',
        }:
            final = _sum_rows('uw', 'lab', 'module_substat', 'perk')
            return final, 'resolved', 'UW additive scalar composition resolved from unified mechanic bucket.', schema

        if destination_id in {
            'uw.chain_lightning.chance_pct',
            'uw.chrono_field.slow_pct',
            'uw.chrono_field.damage_reduction_pct',
            'uw.poison_swamp.stun_chance_pct',
            'uw.black_hole.damage_pct_enemy_hp_per_second',
            'uw.chain_lightning.max_enemy_damage_reduction_pct',
        }:
            final = _sum_rows('uw', 'lab', 'module_substat', 'perk')
            return final, 'resolved', 'UW additive percentage composition resolved from unified mechanic bucket.', schema

        if destination_id in {
            'uw.chain_lightning.quantity',
            'uw.death_wave.effect_wave_count',
            'uw.inner_land_mines.quantity',
            'uw.smart_missiles.quantity',
            'uw.smart_missiles.barrage_quantity',
            'uw.spotlight.count',
            'uw.poison_swamp.rend_additional_enemies',
        }:
            final = float(int(_sum_rows('uw', 'lab', 'module_substat', 'perk')))
            return final, 'resolved', 'UW integer-count composition resolved from unified mechanic bucket.', schema

        if destination_id in {
            'uw.chain_lightning.scatter_multiplier',
            'uw.death_wave.cells_bonus_multiplier',
            'uw.death_wave.damage_amplifier_multiplier_per_effect_wave',
            'uw.smart_missiles.chain_hit_damage_multiplier',
            'uw.inner_land_mines.damage',
        }:
            final = _sum_rows('uw', 'lab', 'module_substat', multiplier_display_as_flat=True)
            return final, 'resolved', 'UW additive multiplier-display composition resolved from unified mechanic bucket.', schema


        value, status, notes = _safe_single_or_uniform_resolution(destination_object_type, destination_id, contributors)
        return value, status, notes, schema

    if destination_object_type != 'canonical_stat' and not (destination_object_type == 'mechanic_param' and destination_id.startswith('bot.')):
        value, status, notes = _safe_single_or_uniform_resolution(destination_object_type, destination_id, contributors)
        return value, status, notes, schema

    resolved_rows = meta.get('_resolved_rows', {})

    def _rows(family: str):
        return [r for r in contributors if r.source_family == family]

    if destination_id == 'tower_attack_speed':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for attack speed.', schema
        lab_mult = next((_as_float(r.value) for r in _rows('lab')), 1.0) or 1.0
        if lab_mult and lab_mult > 10:
            lab_mult = 1.0 + 0.02 * lab_mult
        card_mult = next((_as_float(r.value) for r in _rows('card')), 1.0) or 1.0
        enhancement_mult = next((_as_float(r.value) for r in _rows('enhancement')), 1.0) or 1.0
        relic_mult = 1.0
        for r in _rows('relic') + _rows('vault'):
            v = _as_float(r.value)
            if v is not None:
                relic_mult *= (1.0 + v)
        module_add = 0.0
        for r in _rows('module_substat'):
            v = _as_float(r.value)
            if v is not None:
                module_add += v
        final = ((workshop * lab_mult * card_mult) + module_add) * enhancement_mult * relic_mult
        return final, 'resolved', 'Destination-specific attack speed formula: (Workshop x Lab x Card + Module Sub Effect) x Enhancement x relic/vault multipliers.', schema

    if destination_id == 'tower_crit_multiplier':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for critical factor.', schema
        lab_mult = next((_as_float(r.value) for r in _rows('lab')), 1.0) or 1.0
        base = workshop * lab_mult
        for r in _rows('module_substat'):
            v = _as_float(r.value)
            if v is not None:
                if r.value_type == 'multiplier_display':
                    base += v
                elif r.value_type == 'percent_display':
                    base += v / 100.0
                else:
                    base += v
        post_mult = 1.0
        for fam in ('enhancement', 'relic', 'vault'):
            for r in _rows(fam):
                v = _as_float(r.value)
                if v is None:
                    continue
                post_mult *= _canonical_source_multiplier(destination_id, r, v)
        final = base * post_mult
        return final, 'resolved', 'Destination-specific critical factor formula: (Workshop x Crit Factor Lab + module flat/x adds) x post multipliers.', schema


    if destination_id == 'tower_supercrit_multiplier':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for super crit multiplier.', schema
        lab_mult = next((_as_float(r.value) for r in _rows('lab')), 1.0) or 1.0
        base = workshop * lab_mult
        for r in _rows('module_substat'):
            v = _as_float(r.value)
            if v is not None:
                if r.value_type == 'multiplier_display':
                    base += v
                elif r.value_type == 'percent_display':
                    base += v / 100.0
                else:
                    base += v
        post_mult = 1.0
        for fam in ('enhancement', 'relic', 'vault'):
            for r in _rows(fam):
                v = _as_float(r.value)
                if v is None:
                    continue
                post_mult *= _canonical_source_multiplier(destination_id, r, v)
        final = base * post_mult
        return final, 'resolved', 'Destination-specific super crit multiplier formula: (Workshop x Lab + module flat/x adds) x post multipliers.', schema

    if destination_id == 'wall_rebuild_seconds':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for wall rebuild.', schema
        reduction = 0.0
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family == 'lab':
                reduction += abs(v)
            elif r.source_family in {'relic','vault','module_substat'}:
                reduction += abs(v)
            else:
                reduction += abs(v)
        final = max(CANONICAL_PCT_CAPS.get('wall_rebuild_seconds', 150.0), workshop - reduction)
        return final, 'resolved', 'Destination-specific wall rebuild formula: workshop base minus reductions, floored at hard cap.', schema

    if destination_id == 'coins_per_kill_bonus':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for coins_per_kill_bonus.', schema
        lab_mult = next((_as_float(r.value) for r in _rows('lab')), 1.0) or 1.0
        substat_add = 0.0
        for r in _rows('module_substat'):
            v = _as_float(r.value)
            if v is None:
                continue
            substat_add += v
        enhancement_spillover = 1.0
        for r in _rows('enhancement'):
            v = _as_float(r.value)
            if v is not None:
                enhancement_spillover *= v
        vault_multiplier = 1.0
        for r in _rows('vault'):
            v = _as_float(r.value)
            if v is not None:
                vault_multiplier *= (1.0 + v if 0.0 <= v <= 1.0 else v)
        perk_multiplier = 1.0
        for r in _rows('perk'):
            v = _as_float(r.value)
            if v is None:
                continue
            perk_multiplier *= _canonical_source_multiplier(destination_id, r, v)
        final = ((workshop * lab_mult) + substat_add) * enhancement_spillover * vault_multiplier * perk_multiplier
        return final, 'resolved', 'KB-repaired coins_per_kill_bonus formula: (((workshop x lab) + generator substat sum) x enhancement spillover x (1+vault)) x all-coin perk multipliers.', schema

    if destination_id == 'coin_bonus_multiplier':
        final = 1.0
        consumed = 0
        for fam in ('enhancement', 'module'):
            for r in _rows(fam):
                v = _as_float(r.value)
                if v is None:
                    continue
                final *= _canonical_source_multiplier(destination_id, r, v)
                consumed += 1
        if consumed == 0:
            return None, 'mapped_not_resolved', 'No direct broad-coin contributors for coin_bonus_multiplier.', schema
        return final, 'resolved', 'KB-repaired coin_bonus_multiplier formula: direct Coin Bonus enhancement x generator main Coin Bonus only.', schema

    if destination_id == 'coins_multiplier':
        final = 1.0
        consumed = 0
        for fam in ('card', 'relic'):
            for r in _rows(fam):
                v = _as_float(r.value)
                if v is None:
                    continue
                if fam == 'relic':
                    final *= (1.0 + v if 0.0 <= v <= 1.0 else v)
                else:
                    final *= _canonical_source_multiplier(destination_id, r, v)
                consumed += 1
        if consumed == 0:
            return None, 'mapped_not_resolved', 'No broad card/relic coin contributors for coins_multiplier.', schema
        return final, 'resolved', 'KB helper coins_multiplier formula: product of card and relic broad-coin multipliers only.', schema

    if destination_id == 'coin_kill_multiplier':
        mirror_row = resolved_rows.get('canonical_stat::coins_per_kill_bonus')
        if mirror_row and mirror_row.final_value is not None:
            return _as_float(mirror_row.final_value), 'resolved', 'Deprecated transition mirror of canonical_stat::coins_per_kill_bonus.', schema
        return None, 'mapped_not_resolved', 'Deprecated transition mirror requires canonical_stat::coins_per_kill_bonus.', schema

    if destination_id == 'tower_defense_absolute':
        return _resolve_base_times_post_multipliers(destination_id, contributors, schema, note_label='Promoted shared base-times-post-multipliers family')

    if destination_id == 'tower_damage_per_meter_multiplier':
        return _resolve_decimal_base_times_post_multipliers(destination_id, contributors, schema)

    if destination_id == 'wall_fortification_multiplier':
        lab_pct = next((_as_float(r.value) for r in _rows('lab')), None)
        if lab_pct is None:
            return None, 'mapped_not_resolved', 'Missing wall fortification lab value.', schema
        final = 1.0 + (lab_pct / 100.0)
        return final, 'resolved', 'Destination-specific wall fortification formula: 1 + lab percent / 100.', schema

    if destination_object_type == 'mechanic_param' and destination_id.startswith('bot.'):
        resolved_rows = meta.get('_resolved_rows', {})
        bot_name = destination_id.split('.')[1]
        if destination_id == 'bot.global.range_bonus_m':
            total = 0.0
            seen = False
            for r in contributors:
                v = _as_float(r.value)
                if v is None:
                    continue
                total += v
                seen = True
            if not seen:
                return None, 'mapped_not_resolved', 'Missing global bot range contributors.', schema
            return total, 'resolved', 'Bot global range bonus formula: additive relic, vault, and module unique contributions.', schema
        if bot_name != 'global':
            unlock_row = resolved_rows.get(f'capability::bot.{bot_name}.owned')
            if unlock_row is not None and bool(unlock_row.final_value) is False:
                return 0.0, 'resolved', 'Bot mechanic row gated to zero because the bot is not owned.', schema
        if destination_id.endswith('.range_m'):
            base = 0.0
            seen = False
            for r in contributors:
                v = _as_float(r.value)
                if v is None:
                    continue
                if r.source_family == 'bot':
                    base += v
                    seen = True
            global_bonus_row = resolved_rows.get('mechanic_param::bot.global.range_bonus_m')
            global_bonus = _as_float(global_bonus_row.final_value) if global_bonus_row and global_bonus_row.final_value is not None else 0.0
            if not seen and global_bonus == 0.0:
                return None, 'mapped_not_resolved', 'Missing base bot range contributor.', schema
            return base + global_bonus, 'resolved', 'Bot canonical range formula: base bot range plus global bot range bonus.', schema
        if destination_id.endswith('.duration_seconds') or destination_id.endswith('.cooldown_seconds') or destination_id.endswith('.linger_duration_seconds'):
            total = 0.0
            seen = False
            for r in contributors:
                v = _as_float(r.value)
                if v is None:
                    continue
                total += v
                seen = True
            if not seen:
                return None, 'mapped_not_resolved', 'Missing bot timing contributors.', schema
            return total, 'resolved', 'Bot canonical timing formula: additive base track plus lab timing adjustments.', schema
        if destination_id.endswith('.bonus_multiplier') or destination_id.endswith('.damage_multiplier'):
            total = 0.0
            seen = False
            for r in contributors:
                v = _as_float(r.value)
                if v is None:
                    continue
                total += v
                seen = True
            if not seen:
                return None, 'mapped_not_resolved', 'Missing bot multiplier contributors.', schema
            return total, 'resolved', 'Bot canonical multiplier formula: direct bot multiplier track with additive supporting rows if present.', schema
        if destination_id.endswith('.damage_reduction_pct') or destination_id.endswith('.linger_slow_pct'):
            total = 0.0
            seen = False
            for r in contributors:
                v = _as_float(r.value)
                if v is None:
                    continue
                total += v
                seen = True
            if not seen:
                return None, 'mapped_not_resolved', 'Missing bot percentage contributors.', schema
            return total, 'resolved', 'Bot canonical percent formula: additive percent contributors.', schema

    if destination_id == 'wall_invincibility_duration_seconds':
        lab_seconds = next((_as_float(r.value) for r in _rows('lab')), None)
        if lab_seconds is None:
            return None, 'mapped_not_resolved', 'Missing wall invincibility lab value.', schema
        return lab_seconds, 'resolved', 'Destination-specific wall invincibility formula: direct lab seconds.', schema

    if destination_id == 'tower_knockback_force':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for knockback force.', schema
        base = workshop
        multiplier = 1.0
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family in {'relic', 'vault'}:
                base += v
            elif r.source_family == 'module_substat':
                base += v
            else:
                multiplier *= _canonical_source_multiplier(destination_id, r, v)
        return base * multiplier, 'resolved', 'Destination-specific knockback-force formula: (workshop + additive force bonuses) x force multipliers.', schema

    if destination_id == 'cash_per_wave':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for cash per wave.', schema
        final = workshop
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family in {'perk', 'enhancement', 'card', 'module', 'module_substat'}:
                final *= _canonical_source_multiplier(destination_id, r, v)
            elif r.source_family in {'relic', 'vault'}:
                final *= (1.0 + v)
            elif r.source_family == 'lab':
                final *= v
        return final, 'resolved', 'Destination-specific cash-per-wave formula: workshop x cash-per-wave multipliers.', schema

    if destination_id == 'interest_per_wave_pct':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for interest per wave.', schema
        final = workshop
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family == 'lab':
                final *= v
            elif r.source_family == 'module_substat':
                final += v
            elif r.source_family in {'relic', 'vault'}:
                final *= (1.0 + v)
            else:
                final *= _canonical_source_multiplier(destination_id, r, v)
        return final, 'resolved', 'Destination-specific interest-per-wave formula: workshop x interest lab multiplier, plus additive substat bonuses, then post multipliers.', schema


    if destination_id == 'module.orbital_augment.electron_count':
        count_value = None
        for r in contributors:
            v = _as_float(r.value)
            if v is None:
                continue
            count_value = v if count_value is None else max(count_value, v)
        if count_value is None:
            return None, 'mapped_not_resolved', 'Missing Orbital Augment unique-effect count contributor.', schema
        final = int(count_value)
        return final, 'resolved', 'Destination-specific Orbital Augment electron-count formula: rarity-derived integer unique-effect count.', schema

    if destination_id == 'tower_land_mine_damage':
        land_mine_mult = None
        for r in contributors:
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family == 'workshop':
                land_mine_mult = v if land_mine_mult is None else land_mine_mult * v
            elif r.source_family in {'enhancement', 'perk', 'module'}:
                land_mine_mult = (1.0 if land_mine_mult is None else land_mine_mult) * _canonical_source_multiplier(destination_id, r, v)
            elif r.source_family in {'relic', 'vault'}:
                land_mine_mult = (1.0 if land_mine_mult is None else land_mine_mult) * (1.0 + v)
            elif r.source_family == 'module_substat':
                if r.value_type in {'pct', 'percent_display'}:
                    mult = 1.0 + (v / 100.0)
                else:
                    mult = _canonical_source_multiplier(destination_id, r, v)
                land_mine_mult = (1.0 if land_mine_mult is None else land_mine_mult) * mult
            elif r.source_family == 'lab':
                if r.value_type in {'pct', 'percent_display', 'resolved_value'}:
                    mult = 1.0 + (v / 100.0) if v > 1.0 else 1.0 + v
                else:
                    mult = _canonical_source_multiplier(destination_id, r, v)
                land_mine_mult = (1.0 if land_mine_mult is None else land_mine_mult) * mult
        tower_damage = next((_as_float(r.final_value) for k, r in resolved_rows.items() if k == 'canonical_stat::tower_damage'), None)
        crit_chance = next((_as_float(r.final_value) for k, r in resolved_rows.items() if k == 'canonical_stat::tower_crit_chance_pct'), None)
        crit_factor = next((_as_float(r.final_value) for k, r in resolved_rows.items() if k == 'canonical_stat::tower_crit_multiplier'), None)
        supercrit_chance = next((_as_float(r.final_value) for k, r in resolved_rows.items() if k == 'canonical_stat::tower_supercrit_chance_pct'), None)
        supercrit_factor = next((_as_float(r.final_value) for k, r in resolved_rows.items() if k == 'canonical_stat::tower_supercrit_multiplier'), None)
        pieces = [land_mine_mult, tower_damage, crit_chance, crit_factor, supercrit_chance, supercrit_factor]
        if any(v is None for v in pieces):
            return None, 'mapped_not_resolved', 'Runtime-damage family requires land-mine multiplier assembly plus tower_damage, crit, and super-crit surfaces.', schema
        crit_chance = crit_chance / 100.0 if crit_chance > 1.0 else crit_chance
        supercrit_chance = supercrit_chance / 100.0 if supercrit_chance > 1.0 else supercrit_chance
        final = land_mine_mult * tower_damage * (1.0 + crit_factor * crit_chance) * (1.0 + supercrit_factor * supercrit_chance * crit_chance)
        return final, 'resolved', 'Promoted runtime-damage family: assembled land-mine damage multiplier x tower_damage x crit composite x super-crit composite, with chance surfaces normalized from pct to decimal.', schema

    if destination_id == 'wall_thorns_damage_pct':
        wall_ratio = next((_as_float(r.value) for r in _rows('lab')), None)
        tower_thorns = next((_as_float(r.value) for r in _rows('workshop')), None)
        if wall_ratio is None:
            return None, 'mapped_not_resolved', 'Missing wall thorns ratio or tower thorns base.', schema
        if wall_ratio > 1.0:
            wall_ratio = wall_ratio / 100.0
        if tower_thorns is None:
            return wall_ratio * 100.0, 'resolved', 'Destination-specific wall thorns fallback: lab ratio preserved as percent because tower-thorns base is external to this bucket.', schema
        return tower_thorns * wall_ratio, 'resolved', 'Destination-specific wall thorns formula: tower thorns x wall-thorns ratio.', schema

    if destination_id == 'max_recovery_multiplier':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for max recovery.', schema
        additive_pp = 0.0
        mult = 1.0
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family in {'lab', 'module_substat'}:
                additive_pp += v
            elif r.source_family in {'enhancement'}:
                mult *= v
            elif r.source_family in {'relic', 'vault', 'card'}:
                mult *= (1.0 + v)
        final = (workshop + additive_pp) * mult
        return final, 'resolved', 'Destination-specific max recovery formula: workshop base plus additive package bonuses, then post multipliers.', schema

    if destination_id == 'recovery_amount_pct':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop is None:
            return None, 'mapped_not_resolved', 'Missing workshop base for recovery amount.', schema
        additive_pp = 0.0
        mult = 1.0
        for r in contributors:
            if r.source_family == 'workshop':
                continue
            v = _as_float(r.value)
            if v is None:
                continue
            if r.source_family in {'lab', 'module_substat'}:
                additive_pp += v
            elif r.source_family in {'enhancement'}:
                mult *= v
            elif r.source_family in {'relic', 'vault', 'card'}:
                additive_pp += v * 100.0 if 0.0 <= v <= 1.0 else v
        final = (workshop + additive_pp) * mult
        return final, 'resolved', 'Destination-specific recovery amount formula: workshop base plus additive package amount bonuses, then enhancement multipliers.', schema

    if destination_id == 'wall_hp':
        tower_hp_row = resolved_rows.get('canonical_stat::tower_hp')
        tower_hp_value = _as_float(getattr(tower_hp_row, 'final_value', None)) if tower_hp_row is not None else None
        workshop_ratio = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), None)
        if workshop_ratio is None:
            return None, 'mapped_not_resolved', 'Missing workshop wall-health ratio base.', schema
        ratio_multiplier = workshop_ratio
        post_multiplier = 1.0
        consumed = 0
        unsupported = []
        for r in contributors:
            v = _as_float(r.value)
            if v is None:
                unsupported.append(f'{r.source_family}:{r.source_name}:non_numeric')
                continue
            if r.source_family == 'workshop':
                consumed += 1
                continue
            if r.source_family in {'lab', 'module_substat'}:
                if r.value_type in {'percent_display', 'pct'} or v > 10.0:
                    ratio_multiplier += v / 100.0
                else:
                    ratio_multiplier += v
                consumed += 1
                continue
            if r.source_family in {'enhancement', 'module', 'card', 'perk', 'relic', 'vault'}:
                if r.source_family in {'relic', 'vault'} and 0.0 <= v <= 1.0:
                    post_multiplier *= (1.0 + v)
                else:
                    post_multiplier *= _canonical_source_multiplier(destination_id, r, v)
                consumed += 1
                continue
            unsupported.append(f'{r.source_family}:{r.source_name}:{r.value_type}')
        ratio_value = ratio_multiplier * post_multiplier
        if tower_hp_value is not None:
            final = tower_hp_value * ratio_value
            note = 'Wall HP formula from KB: tower_hp x (workshop wall-health ratio + additive wall-health ratio bonuses) x wall-health multipliers.'
        else:
            final = ratio_value * 100.0
            note = 'Wall HP ratio fallback from KB: (workshop wall-health ratio + additive wall-health ratio bonuses) x wall-health multipliers, expressed as percentage points because tower_hp was unavailable.'
        if unsupported:
            note += ' Unsupported contributors preserved: ' + ', '.join(unsupported[:8])
        return final, 'resolved' if not unsupported else 'partially_resolved', note, schema

    if destination_id == 'tower_orb_count':
        workshop = next((_as_float(r.value) for r in contributors if r.source_family == 'workshop'), 0.0) or 0.0
        extra = 0.0
        consumed = 0
        for r in contributors:
            if r.source_family == 'workshop':
                consumed += 1
                continue
            if r.source_family == 'card' and r.source_name == 'Extra Orb':
                extra += 1.0
                consumed += 1
            elif r.source_family == 'lab' and r.source_name == 'Extra Extra Orbs':
                v = _as_float(r.value)
                if v is not None:
                    extra += v
                    consumed += 1
            elif r.source_family in {'module_substat', 'vault', 'perk'}:
                v = _as_float(r.value)
                if v is not None:
                    extra += v
                    consumed += 1
        return round(workshop + extra), 'resolved', f'Consumed {consumed}/{len(contributors)} contributors with destination-specific orb-count semantics.', schema

    additive_units = {'count', 'seconds', 'm', 'rpm', 'hp', 'damage', 'hp_per_second', 'attacks_per_second', 'damage_block', 'force', 'cash', 'coins'}

    if destination_id in BASE_FLAT_MULTIPLIED_STATS:
        if destination_id in {'tower_damage'}:
            return _resolve_base_times_post_multipliers(destination_id, contributors, schema, note_label='Promoted shared base-times-post-multipliers family')
        if destination_id == 'tower_hp':
            return _resolve_survivability_base_times_multipliers(destination_id, contributors, schema, module_substat_family='generic')
        if destination_id == 'tower_regen':
            return _resolve_survivability_base_times_multipliers(destination_id, contributors, schema, module_substat_family='tower_regen_ep')
        base_value = None
        tower_regen_module_rows: List[StatInput] = []
        for row in contributors:
            v = _as_float(row.value)
            if v is None:
                unsupported.append(f'{row.source_family}:{row.source_name}:non_numeric')
                continue
            if row.source_family == 'workshop':
                if row.value_type == 'level':
                    unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                    continue
                base_value = v
                consumed += 1
            else:
                if destination_id == 'tower_regen' and row.source_family == 'module_substat':
                    tower_regen_module_rows.append(row)
                    consumed += 1
                    continue
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
        if destination_id == 'tower_regen' and tower_regen_module_rows:
            multiplier_product *= _tower_regen_compare_module_multiplier(tower_regen_module_rows)
        if consumed == 0 or base_value is None:
            return None, 'mapped_not_resolved', 'Missing validated workshop base for flat-times-multipliers stat.', schema
        final = base_value * multiplier_product
        notes = f'Consumed {consumed}/{len(contributors)} contributors with destination-specific flat-base semantics.'
        if unsupported:
            notes += ' Unsupported contributors preserved: ' + ', '.join(unsupported[:8])
        return final, 'resolved' if not unsupported else 'partially_resolved', notes, schema

    if destination_id in BASE_MULTIPLIER_STATS:
        if destination_id in DIRECT_ADDITIVE_ONLY_STATS:
            total = 0.0
            for row in contributors:
                v = _as_float(row.value)
                if v is None:
                    unsupported.append(f'{row.source_family}:{row.source_name}:non_numeric')
                    continue
                total += v
                consumed += 1
            if consumed == 0:
                return None, 'mapped_not_resolved', 'No numeric contributors for additive-only multiplier stat.', schema
            notes = f'Consumed {consumed}/{len(contributors)} contributors with additive-only multiplier semantics.'
            if unsupported:
                notes += ' Unsupported contributors preserved: ' + ', '.join(unsupported[:8])
            return total, 'resolved' if not unsupported else 'partially_resolved', notes, schema
        base_value = None
        for row in contributors:
            v = _as_float(row.value)
            if v is None:
                unsupported.append(f'{row.source_family}:{row.source_name}:non_numeric')
                continue
            if row.source_family == 'workshop':
                if row.value_type == 'level':
                    unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                    continue
                base_value = v
                consumed += 1
            elif row.source_family == 'module_substat' and row.value_type == 'multiplier_display':
                base_value = (base_value or 0.0) + v
                consumed += 1
            else:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
        if consumed == 0 or base_value is None:
            return None, 'mapped_not_resolved', 'Missing validated workshop base for multiplier-base stat.', schema
        final = base_value * multiplier_product
        notes = f'Consumed {consumed}/{len(contributors)} contributors with destination-specific multiplier-base semantics.'
        if unsupported:
            notes += ' Unsupported contributors preserved: ' + ', '.join(unsupported[:8])
        return final, 'resolved' if not unsupported else 'partially_resolved', notes, schema

    for row in contributors:
        v = _as_float(row.value)
        if v is None:
            unsupported.append(f'{row.source_family}:{row.source_name}:non_numeric')
            continue
        measure = _contributor_measure(row)
        if unit in additive_units:
            if measure == 'level':
                unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                continue
            if unit == 'count':
                if row.value_type == 'multiplier_display':
                    multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                else:
                    add_sum += v
                consumed += 1
                continue
            if measure in {'flat', 'count', 'seconds', 'm', 'rpm', 'resolved_value'} and row.source_family in {'workshop'}:
                add_sum += v
                consumed += 1
                continue
            if row.source_family in {'lab', 'relic', 'card', 'enhancement', 'module_substat', 'module', 'vault'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
                continue
            if measure == 'pct' and unit in {'m', 'rpm', 'damage_block', 'force', 'cash', 'coins'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
                continue
        if unit == 'pct':
            if measure == 'level':
                unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                continue
            if measure == 'multiplier':
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
                continue
            if measure in {'pct', 'resolved_value', 'flat'}:
                if row.source_family == 'module_substat' and row.value_type == 'percent_display' and 0.0 <= v <= 100.0:
                    additive_pct += v
                elif row.source_family == 'module_substat' and 0.0 <= v <= 1.0:
                    additive_pct += v * 100.0
                elif row.source_family in {'relic', 'vault'} and 0.0 <= v <= 1.0:
                    additive_pct += v * 100.0
                else:
                    additive_pct += v
                consumed += 1
                continue
        if unit == 'multiplier':
            if row.source_family in {'lab', 'relic', 'card', 'enhancement', 'module_substat', 'module', 'vault'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, v)
                consumed += 1
                continue
            add_sum += v
            consumed += 1
            continue
        unsupported.append(f'{row.source_family}:{row.source_name}:{measure}')

    if consumed == 0:
        return None, 'mapped_not_resolved', 'No numeric combiner rule implemented for this mapped contributor mix.', schema

    if unit == 'pct':
        final = (add_sum + additive_pct) * multiplier_product
        if resolver == 'pct_capped_scalar_stat':
            cap = CANONICAL_PCT_CAPS.get(destination_id)
            if cap is not None:
                final = max(0.0, min(cap, final))
    elif destination_id == 'wall_rebuild_seconds':
        final = max(CANONICAL_PCT_CAPS.get(destination_id, 150.0), add_sum * multiplier_product if add_sum != 0.0 else multiplier_product)
    elif add_sum != 0.0:
        final = add_sum * multiplier_product
    else:
        final = multiplier_product

    if resolver == 'integer_count_stat':
        final = round(final)
    notes = f'Consumed {consumed}/{len(contributors)} contributors with cautious resolver-aware rules.'
    if unsupported:
        notes += ' Unsupported contributors preserved: ' + ', '.join(unsupported[:8])
    return final, 'resolved' if not unsupported else 'partially_resolved', notes, schema



def _phase3_statinput_from_dict(d: Dict[str, object]) -> StatInput:
    return StatInput(**{k: d.get(k) for k in StatInput.__dataclass_fields__.keys()})


def _apply_shared_support_multiplier_family(rows: Dict[str, StatRow], *, support_key: str, targets: List[str], note: str) -> None:
    support_row = rows.get(support_key)
    if not support_row:
        return
    multiplier = 1.0
    for contributor in support_row.contributors:
        row = _phase3_statinput_from_dict(contributor)
        v = _as_float(contributor.get('value'))
        if v is None:
            continue
        if row.source_family == 'enhancement':
            multiplier *= v
    if multiplier == 1.0:
        return
    for key in targets:
        stat_row = rows.get(key)
        if stat_row and stat_row.final_value is not None:
            base = _as_float(stat_row.final_value)
            if base is not None:
                stat_row.final_value = base * multiplier
                stat_row.status = 'resolved'
                stat_row.notes = note


def _apply_free_upgrade_chance_formula_from_routed_contributors(rows: Dict[str, StatRow]) -> None:
    support_row = rows.get('canonical_stat::free_upgrade_multiplier')
    support_multiplier = 1.0
    support_contributors: List[Dict[str, Any]] = []
    if support_row is not None:
        for contributor in support_row.contributors:
            row = _phase3_statinput_from_dict(contributor)
            v = _as_float(contributor.get('value'))
            if v is None:
                continue
            if row.source_family == 'enhancement':
                support_multiplier *= v
                support_contributors.append(dict(contributor))

    ordered_targets = [
        'canonical_stat::free_attack_upgrade_chance_pct',
        'canonical_stat::free_defense_upgrade_chance_pct',
        'canonical_stat::free_utility_upgrade_chance_pct',
    ]
    shared_additive = None
    shared_additive_contributors: List[Dict[str, Any]] = []

    for key in ordered_targets:
        stat_row = rows.get(key)
        if stat_row is None:
            continue
        shared_total = 0.0
        local_total = 0.0
        local_contributors: List[Dict[str, Any]] = []
        shared_contributors_for_row: List[Dict[str, Any]] = []
        for contributor in stat_row.contributors:
            row = _phase3_statinput_from_dict(contributor)
            v = _as_float(contributor.get('value'))
            if v is None:
                continue
            if row.source_family in {'card', 'perk'}:
                shared_total += v
                shared_contributors_for_row.append(dict(contributor))
                continue
            if row.source_family in {'relic', 'vault'} and 0.0 <= v <= 1.0:
                v *= 100.0
            local_total += v
            local_contributors.append(dict(contributor))

        if shared_additive is None:
            shared_additive = shared_total
            shared_additive_contributors = shared_contributors_for_row
            rows['canonical_stat::free_upgrade_shared_add_pct'] = StatRow(
                stat_name='canonical_stat::free_upgrade_shared_add_pct',
                final_value=shared_total,
                value_type='pct',
                source_count=len(shared_contributors_for_row),
                status='resolved',
                notes='Shared free-upgrade additive support from cards and perks.',
                contributors=shared_contributors_for_row,
                schema={'unit': 'pct'},
            )

        stat_row.final_value = (local_total + (shared_additive or 0.0)) * support_multiplier
        stat_row.status = 'resolved'
        stat_row.notes = 'Free-upgrade formula from routed contributors: (lane workshop + lane relic/vault + lane module-substat + shared card/perk additive support) x shared free-upgrade enhancement multiplier. Promoted shared support-multiplier family.'
        stat_row.source_count = len(local_contributors) + len(shared_additive_contributors) + len(support_contributors)


def _apply_exact_max_rend_formula(rows: Dict[str, StatRow]) -> None:
    max_rend_row = rows.get('canonical_stat::max_rend_mult')
    if not max_rend_row:
        return
    enhancement_multiplier = 1.0
    has_enhancement = False
    lab_bonus = 0.0
    module_pct_bonus = 0.0
    for contributor in max_rend_row.contributors:
        row = _phase3_statinput_from_dict(contributor)
        v = _as_float(contributor.get('value'))
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
        return
    pre_enhancement_cap = 8.0 + lab_bonus + (8.0 * module_pct_bonus)
    max_rend_row.final_value = pre_enhancement_cap * enhancement_multiplier
    max_rend_row.status = 'resolved'
    max_rend_row.notes = 'Phase 3 exact Max Rend formula from EP/KB: (8 + lab max-rend bonus + 8 x module-substat max-rend pct bonus) x Rend Armor enhancement multiplier.'


def _apply_phase3_postprocessing(rows: Dict[str, StatRow]) -> None:
    _apply_free_upgrade_chance_formula_from_routed_contributors(rows)
    _apply_exact_max_rend_formula(rows)

    coins_per_kill_row = rows.get('canonical_stat::coins_per_kill_bonus')
    if coins_per_kill_row is not None:
        rows['canonical_stat::coin_kill_multiplier'] = StatRow(
            stat_name='canonical_stat::coin_kill_multiplier',
            final_value=coins_per_kill_row.final_value,
            value_type=coins_per_kill_row.value_type,
            source_count=coins_per_kill_row.source_count,
            status=coins_per_kill_row.status,
            notes='Deprecated transition mirror of canonical_stat::coins_per_kill_bonus.',
            contributors=list(coins_per_kill_row.contributors),
            schema=coins_per_kill_row.schema,
        )

    disable_ads_row = rows.get('account_flag::account_flag.disable_ads')
    starter_pack_row = rows.get('account_flag::account_flag.starter_pack')
    epic_pack_row = rows.get('account_flag::account_flag.epic_pack')
    farming_tier_row = rows.get('account_context::account_context.farming_tier')
    legacy_coin_display_row = rows.get('account_context::account_context.coin_multiplier_display')
    helper_contributors = []

    def _helper_value(row_key, label):
        row = rows.get(row_key)
        if not row:
            return None
        helper_contributors.append({'stat_name': label, 'source_family': 'helper_surface', 'source_name': label, 'value': row.final_value, 'value_type': row.value_type, 'stage': 'phase3_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True})
        return _as_float(row.final_value)

    coin_bonus_val = _helper_value('canonical_stat::coin_bonus_multiplier', 'canonical_stat::coin_bonus_multiplier')
    coins_mult_val = _helper_value('canonical_stat::coins_multiplier', 'canonical_stat::coins_multiplier')
    theme_val = _helper_value('cosmetic_bonus::cosmetic_bonus.theme_song_coin_multiplier', 'cosmetic_bonus.theme_song_coin_multiplier')

    def _load_pack_multiplier_map():
        import csv
        from pathlib import Path
        table = Path(__file__).resolve().parents[1] / 'kb' / 'global-rules' / 'tables' / 'player-pack-coin-multipliers.csv'
        out = {}
        try:
            with table.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for rec in reader:
                    out[rec['flag_destination']] = float(rec['multiplier'])
        except Exception:
            out = {
                'account_flag.disable_ads': 1.5,
                'account_flag.starter_pack': 2.0,
                'account_flag.epic_pack': 3.0,
            }
        return out

    pack_multiplier_map = _load_pack_multiplier_map()

    def _flag_pack_multiplier(row, label):
        multiplier = float(pack_multiplier_map.get(label, 1.0))
        enabled = bool(getattr(row, 'final_value', False)) if row is not None else False
        helper_contributors.append({'stat_name': label, 'source_family': 'helper_surface', 'source_name': label, 'value': multiplier if enabled else 1.0, 'value_type': 'multiplier', 'stage': 'phase3_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True, 'notes': 'kb_pack_flag_multiplier_if_true' if enabled else 'kb_pack_flag_multiplier_if_false'})
        return multiplier if enabled else 1.0

    disable_ads_mult = _flag_pack_multiplier(disable_ads_row, 'account_flag.disable_ads')
    starter_pack_mult = _flag_pack_multiplier(starter_pack_row, 'account_flag.starter_pack')
    epic_pack_mult = _flag_pack_multiplier(epic_pack_row, 'account_flag.epic_pack')

    tier_display_raw = None if farming_tier_row is None else (farming_tier_row.contributors[0].get('value') if farming_tier_row.contributors else farming_tier_row.final_value)
    helper_contributors.append({'stat_name': 'account_context.farming_tier', 'source_family': 'helper_surface', 'source_name': 'account_context.farming_tier', 'value': tier_display_raw, 'value_type': 'raw_text', 'stage': 'phase3_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True})
    helper_contributors.append({'stat_name': 'account_context.coin_multiplier_display', 'source_family': 'helper_surface', 'source_name': 'account_context.coin_multiplier_display', 'value': None if legacy_coin_display_row is None else (legacy_coin_display_row.contributors[0].get('value') if legacy_coin_display_row.contributors else legacy_coin_display_row.final_value), 'value_type': 'raw_text', 'stage': 'phase3_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True, 'notes': 'legacy_trace_only_not_used_numerically'})

    tier_multiplier_val = None
    if isinstance(tier_display_raw, str):
        import re
        m = re.search(r'(\d+)', tier_display_raw)
        if m:
            tier_num = int(m.group(1))
            try:
                import csv
                from pathlib import Path
                tier_table = Path(__file__).resolve().parents[1] / 'kb' / 'tournaments' / 'tables' / 'tier-battle-condition-levels.csv'
                with tier_table.open(newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for rec in reader:
                        if int(rec['tier']) == tier_num:
                            tier_multiplier_val = float(rec['coin_bonus'])
                            break
            except Exception:
                tier_multiplier_val = None
    helper_contributors.append({'stat_name': 'account_context.farming_tier_coin_multiplier', 'source_family': 'helper_surface', 'source_name': 'account_context.farming_tier_coin_multiplier', 'value': tier_multiplier_val, 'value_type': 'multiplier' if tier_multiplier_val is not None else 'unresolved', 'stage': 'phase3_composition', 'destination_object_type': 'canonical_stat', 'destination_id': 'all_coin_bonus_multiplier', 'resolver_id': 'standard_scalar_stat', 'kb_mapped': True, 'notes': 'kb_tier_coin_bonus_lookup'})

    all_coin_value = None
    all_coin_status = 'mapped_not_resolved'
    all_coin_notes = 'Derived all-coin display surface: coin_bonus_multiplier x coins_multiplier x theme song coin multiplier x farming-tier coin bonus x numeric premium-pack multipliers (Disable Ads 1.5x, Starter Pack 2x, Epic Pack 3x when unlocked). Legacy account coin multiplier display remains trace-only.'
    if coin_bonus_val is not None and coins_mult_val is not None and theme_val is not None and tier_multiplier_val is not None:
        all_coin_value = coin_bonus_val * coins_mult_val * theme_val * tier_multiplier_val * disable_ads_mult * starter_pack_mult * epic_pack_mult
        all_coin_status = 'resolved'
    else:
        all_coin_notes += ' One or more required numeric helper surfaces were unavailable.'
    rows['canonical_stat::all_coin_bonus_multiplier'] = StatRow(
        stat_name='canonical_stat::all_coin_bonus_multiplier',
        final_value=all_coin_value,
        value_type='multiplier',
        source_count=len(helper_contributors),
        status=all_coin_status,
        notes=all_coin_notes,
        contributors=helper_contributors,
        schema={'unit': 'multiplier', 'resolver': 'standard_scalar_stat'},
    )

    tower_regen_row = rows.get('canonical_stat::tower_regen')
    wall_regen_row = rows.get('canonical_stat::wall_regen')
    if tower_regen_row and wall_regen_row and tower_regen_row.final_value is not None:
        tower_regen = _as_float(tower_regen_row.final_value)
        if tower_regen is not None:
            wall_regen_ratio = None
            multiplier = 1.0
            for contributor in wall_regen_row.contributors:
                row = _phase3_statinput_from_dict(contributor)
                v = _as_float(contributor.get('value'))
                if v is None:
                    continue
                if row.source_family == 'lab':
                    wall_regen_ratio = v / 100.0
                elif row.source_family == 'module' and row.value_type == 'multiplier_display':
                    multiplier *= v
                elif row.source_family == 'module_substat':
                    multiplier *= 1.0 + (v / 100.0)
            if wall_regen_ratio is not None:
                wall_regen_row.final_value = tower_regen * wall_regen_ratio * multiplier
                wall_regen_row.status = 'resolved'
                wall_regen_row.notes = 'Phase 3 exact wall regen formula from KB: tower_regen x wall-regen ratio x wall-regen multipliers.'

    package_row = rows.get('canonical_stat::package_chance_pct')
    if package_row:
        final, status, note, _ = _resolve_additive_base_plus_bonuses_pct('package_chance_pct', [_phase3_statinput_from_dict(c) for c in package_row.contributors], {'unit': 'pct'})
        if final is not None:
            package_row.final_value = final
            package_row.status = status
            package_row.notes = note

    runtime_mirror_map = {
        'mechanic_param::uw.chain_lightning.chance_pct': 'runtime_mechanic_param::uw.chain_lightning.chance_pct',
        'mechanic_param::uw.chain_lightning.damage_multiplier': 'runtime_mechanic_param::uw.chain_lightning.damage_multiplier',
        'mechanic_param::uw.spotlight.bonus_multiplier': 'runtime_mechanic_param::uw.spotlight.bonus_multiplier',
    }
    for source_key, runtime_key in runtime_mirror_map.items():
        source_row = rows.get(source_key)
        if source_row is None:
            continue
        rows[runtime_key] = StatRow(
            stat_name=runtime_key,
            final_value=source_row.final_value,
            value_type=source_row.value_type,
            source_count=source_row.source_count,
            status=source_row.status,
            notes='Phase 3 runtime mirror of resolved mechanic_param surface for runtime consumers and shipped outputs.',
            contributors=list(source_row.contributors),
            schema=dict(source_row.schema or {}),
        )


def resolve_stats(stat_inputs: List[StatInput]) -> StatBook:
    canonical_stats = _load_canonical_stats()
    mapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)
    unmapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)

    for row in stat_inputs:
        if row.kb_mapped and row.destination_id:
            mapped_buckets[f"{row.destination_object_type}::{row.destination_id}"].append(row)
        else:
            unmapped_buckets[row.stat_name].append(row)

    rows: Dict[str, StatRow] = {}
    resolved_count = 0
    partial_count = 0
    unresolved_count = 0

    for bucket_key, contributors in mapped_buckets.items():
        destination_object_type, destination_id = bucket_key.split('::', 1)
        meta = canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'})
        if destination_object_type != 'canonical_stat' and meta.get('unit') == 'unknown':
            meta = {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}
        meta = dict(meta)
        meta['_resolved_rows'] = rows
        final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
        if status == 'resolved':
            resolved_count += 1
        elif status == 'partially_resolved':
            partial_count += 1
        else:
            unresolved_count += 1
        rows[bucket_key] = StatRow(
            stat_name=bucket_key,
            final_value=final_value,
            value_type=meta['unit'],
            source_count=len(contributors),
            status=status,
            notes=notes,
            contributors=[c.to_dict() for c in contributors],
            schema=schema,
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
            schema=schema,
        )

    _apply_phase3_postprocessing(rows)

    family_counts = Counter(row.source_family for row in stat_inputs)
    mapped_family_counts = Counter(row.source_family for row in stat_inputs if row.kb_mapped)
    diagnostics = {
        'resolver_status': 'publish_gate_enforced_resolution',
        'destination_type_schema': {k: _destination_type_schema(k, v) for k, v in sorted(canonical_stats.items())},
        'mapped_input_count': sum(1 for row in stat_inputs if row.kb_mapped),
        'unmapped_input_count': sum(1 for row in stat_inputs if not row.kb_mapped),
        'input_count_by_family': dict(sorted(family_counts.items())),
        'mapped_count_by_family': dict(sorted(mapped_family_counts.items())),
        'resolved_stat_count': resolved_count,
        'partially_resolved_stat_count': partial_count,
        'mapped_unresolved_stat_count': unresolved_count,
        'notes': [
            'This iteration resolves canonical stats with cautious unit-aware rules and also preserves direct numeric values for single-source mapped runtime/meta/capability surfaces.',
            'Multi-source mechanic params remain fail-closed unless a simple suffix-based generic rule is explicitly safe to apply.',
        ],
    }
    return StatBook(rows=rows, diagnostics=diagnostics)
