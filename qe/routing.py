from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import yaml

from qe.contracts import normalize_surface_id_to_contract, to_v2_surface_id
from qe.models import BoundStatInputs, StateIdentity, StateIdentityBinding, compile_stat_inputs_with_identity
from qe.kernel import QueryResponse, StatQueryKernel, get_default_query_kernel
from qe.stat_resolution import (
    resolve_stats as _fallback_resolve_stats,
)
from qe.models import StatInput
from qe.models import StatBook, StatRow
from qe.kb_surfaces import CANONICAL_PCT_CAPS

_TIMING_TOURNAMENT_NO_PERKS = 'timing_tournament_no_perks'
_TIMING_FARM_WITH_PERKS = 'timing_farm_with_perks'
_PROGRESSION_START_OF_RUN = 'progression_start_of_run'
_PROGRESSION_RUNTIME_WITH_PERKS = 'progression_runtime_with_perks'
_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATHS = (
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'canonical-stats.yaml',
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'mechanic-params.yaml',
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'environment-params.yaml',
)


def _mech(destination_id: str) -> str:
    return f'mechanic_param::{destination_id}'


def _state(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'state::{destination_id}')


def _canon(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'canonical_stat::{destination_id}')


def _runtime(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'runtime_mechanic_param::{destination_id}')


def _flag(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'account_flag::{destination_id}')


def _context(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'account_context::{destination_id}')


def _cosmetic(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'cosmetic_bonus::{destination_id}')


def _cap(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'capability::{destination_id}')


def _as_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _phase3_statinput_from_dict(data: dict[str, object]) -> StatInput:
    return StatInput(**{key: data.get(key) for key in StatInput.__dataclass_fields__.keys()})


def _resolve_additive_base_plus_bonuses_pct(
    destination_id: str,
    contributors: list[StatInput],
    schema: dict[str, object],
    *,
    note_label: str = 'Promoted additive-base-plus-bonuses pct family',
) -> tuple[float | None, str, str, dict[str, object]]:
    workshop = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    additive_pp = 0.0
    for row in contributors:
        if row.source_family == 'workshop':
            continue
        value = _as_float(row.value)
        if value is None:
            continue
        additive_pp += value
    final = workshop + additive_pp
    return final, 'resolved', f'{note_label}: workshop base plus additive percent-point bonuses, uncapped.', schema


def _destination_type_schema(destination_id: str, meta: dict[str, str]) -> dict[str, object]:
    unit = meta.get('unit', 'unknown')
    resolver = meta.get('resolver', 'unknown')
    allowed = {'resolved_value', 'flat', 'pct', 'multiplier', 'percent_display', 'multiplier_display', 'bool', 'count'}
    if unit and unit != 'unknown':
        allowed.add(unit)
    expected_semantics: list[str] = []
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
    value_type = row.value_type or ''
    if value_type == 'level':
        return 'unresolved_level'
    if value_type in {'raw_text', 'display_token', 'missing_inventory'}:
        return 'unresolved_non_numeric'
    if row.value is None:
        return 'unresolved_none'
    if value_type in {'percent_display', 'pct'}:
        return 'percentage_points'
    if value_type == 'multiplier_display':
        return 'multiplier_display'
    if value_type == 'multiplier':
        return 'multiplier_factor'
    if value_type == 'count':
        return 'resolved_numeric'
    if value_type in {'seconds', 'm', 'rpm', 'hp', 'damage', 'hp_per_second', 'attacks_per_second', 'damage_block', 'force', 'cash', 'coins'}:
        return 'resolved_unit_value'
    return 'resolved_numeric'


def _is_unresolved_contributor(row: StatInput) -> bool:
    note = (row.notes or '').lower()
    return row.value_type in {'level', 'raw_text', 'display_token', 'missing_inventory'} or row.value is None or 'unresolved' in note


def _is_semantically_compatible(row: StatInput, destination_object_type: str, destination_id: str, schema: dict[str, object]) -> bool:
    if destination_object_type == 'capability':
        if destination_id.endswith('.enabled'):
            return isinstance(row.value, bool) or row.value_type == 'bool'
        if destination_id.endswith('.count'):
            return row.value_type in {'resolved_value', 'flat'} and _as_float(row.value) is not None
        return (
            isinstance(row.value, bool)
            or row.value_type == 'bool'
            or (row.value_type in {'resolved_value', 'flat'} and _as_float(row.value) is not None)
        )
    if destination_object_type == 'account_flag':
        if destination_id.endswith('.automation') or destination_id.endswith('.presets') or destination_id.endswith('.adjuster') or destination_id.endswith('.sliders') or destination_id.endswith('.reroll'):
            return isinstance(row.value, bool) or row.value_type == 'bool'
        return (
            isinstance(row.value, bool)
            or row.value_type == 'bool'
            or (row.value_type in {'resolved_value', 'flat', 'pct', 'percent_display', 'multiplier', 'multiplier_display'} and _as_float(row.value) is not None)
        )
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
    if semantic == 'resolved_unit_value':
        return 'resolved_unit_value' in expected or 'resolved_numeric' in expected or 'unit_multiplier' in expected
    return True


def _publish_gate_check(destination_object_type: str, destination_id: str, contributors: list[StatInput], meta: dict[str, str]) -> tuple[bool, str, list[str], dict[str, object]]:
    schema = _destination_type_schema(destination_id, meta)
    bad: list[str] = []
    for row in contributors:
        reason = None
        if _is_unresolved_contributor(row):
            reason = 'unresolved_or_level'
        elif not _is_semantically_compatible(row, destination_object_type, destination_id, schema):
            reason = 'semantically_incompatible'
        if reason:
            bad.append(f"{row.source_family}:{row.source_name}:{reason}:{row.value_type}")
    if bad:
        return False, 'Publish gate blocked numeric output because one or more contributors are unresolved, still typed as level, or semantically incompatible.', bad, schema
    return True, 'Publish gate passed.', bad, schema


def _contributor_measure(row: StatInput) -> str:
    if row.contributor_id and '__' in row.contributor_id:
        return row.contributor_id.split('__')[-1]
    if row.destination_id and 'module_substat' in row.source_family:
        return 'pct' if isinstance(row.value, float) and abs(row.value) < 1 else 'flat'
    return row.value_type


def _multiplier_from_value(value: float) -> float:
    return value if value >= 1.0 else 1.0 + value


def _module_substat_multiplier(row: StatInput, value: float) -> float:
    if row.value_type == 'percent_display':
        return 1.0 + (value / 100.0)
    if row.value_type == 'multiplier_display':
        return 1.0 + value
    return _multiplier_from_value(value)


def _canonical_source_multiplier(destination_id: str, row: StatInput, value: float) -> float:
    if row.source_family == 'module_substat':
        return _module_substat_multiplier(row, value)
    if row.source_family == 'enhancement':
        return value
    if row.source_family == 'perk' and row.value_type == 'multiplier':
        return value
    if row.source_family == 'relic' and destination_id in {'tower_defense_pct'}:
        return 1.0 + value
    return _multiplier_from_value(value)


def _resolve_base_times_post_multipliers(destination_id: str, contributors: list[StatInput], schema: dict[str, object], *, include_relic_vault_as_bonus: bool = True, note_label: str = 'Shared base-times-post-multipliers family') -> tuple[float | None, str, str, dict[str, object]]:
    workshop = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    lab_mult = next((_as_float(row.value) for row in [row for row in contributors if row.source_family == 'lab']), 1.0) or 1.0
    final = workshop * lab_mult
    for family in ('enhancement', 'card', 'module', 'module_substat', 'perk'):
        for row in [row for row in contributors if row.source_family == family]:
            value = _as_float(row.value)
            if value is None:
                continue
            if family == 'module_substat' and row.value_type == 'percent_display':
                final *= 1.0 + value / 100.0
            else:
                final *= _canonical_source_multiplier(destination_id, row, value)
    if include_relic_vault_as_bonus:
        for family in ('relic', 'vault'):
            for row in [row for row in contributors if row.source_family == family]:
                value = _as_float(row.value)
                if value is not None:
                    final *= 1.0 + value
    return final, 'resolved', f'{note_label}: workshop x lab x post multipliers.', schema


def _resolve_decimal_base_times_post_multipliers(destination_id: str, contributors: list[StatInput], schema: dict[str, object], *, divisor: float = 1000.0, note_label: str = 'Promoted decimal-base-times-post-multipliers family') -> tuple[float | None, str, str, dict[str, object]]:
    workshop = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    final = workshop / divisor
    lab_mult = next((_as_float(row.value) for row in contributors if row.source_family == 'lab'), 1.0) or 1.0
    final *= lab_mult
    for family in ('enhancement', 'card', 'module', 'module_substat', 'perk'):
        for row in [row for row in contributors if row.source_family == family]:
            value = _as_float(row.value)
            if value is None:
                continue
            if family == 'module_substat' and row.value_type == 'percent_display':
                final *= 1.0 + value / 100.0
            else:
                final *= _canonical_source_multiplier(destination_id, row, value)
    for family in ('relic', 'vault'):
        for row in [row for row in contributors if row.source_family == family]:
            value = _as_float(row.value)
            if value is not None:
                final *= 1.0 + value
    return final, 'resolved', f'{note_label}: decimal workshop bonus x lab x post multipliers.', schema


def _tower_regen_compare_module_multiplier(contributors: list[StatInput]) -> float:
    primary_bonus = 0.0
    assist_bonus = 0.0
    for row in contributors:
        value = _as_float(row.value)
        if value is None:
            continue
        note = str(row.notes or '').lower()
        if row.value_type == 'percent_display':
            bonus = value / 10.0 if 'module_substat_assist' in note else value / 100.0
        elif row.value_type == 'multiplier_display':
            bonus = value
        else:
            bonus = max(0.0, value - 1.0)
        if 'module_substat_assist' in note:
            assist_bonus += bonus * 0.10
        else:
            primary_bonus += bonus
    return 1.0 + primary_bonus + assist_bonus


def _resolve_survivability_base_times_multipliers(destination_id: str, contributors: list[StatInput], schema: dict[str, object], *, module_substat_family: str = 'generic', note_label: str = 'Promoted survivability base-times-multipliers family') -> tuple[float | None, str, str, dict[str, object]]:
    workshop = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
    if workshop is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    final = workshop
    module_rows: list[StatInput] = []
    for row in [row for row in contributors if row.source_family != 'workshop']:
        value = _as_float(row.value)
        if value is None:
            continue
        if row.source_family == 'module_substat' and module_substat_family == 'tower_regen_ep':
            module_rows.append(row)
            continue
        if row.source_family in {'relic', 'vault'}:
            final *= 1.0 + value
        elif row.source_family == 'module_substat' and row.value_type == 'percent_display':
            final *= 1.0 + value / 100.0
        else:
            final *= _canonical_source_multiplier(destination_id, row, value)
    if module_substat_family == 'tower_regen_ep' and module_rows:
        final *= _tower_regen_compare_module_multiplier(module_rows)
    return final, 'resolved', f'{note_label}: workshop x survivability multipliers.', schema


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


def _safe_single_or_uniform_resolution(destination_object_type: str, destination_id: str, contributors: list[StatInput]) -> tuple[float | bool | None, str, str]:
    numeric: list[tuple[StatInput, float]] = []
    for row in contributors:
        value = _as_float(row.value)
        if value is not None:
            numeric.append((row, value))
    bools = [bool(row.value) for row in contributors if isinstance(row.value, bool) or row.value_type == 'bool']
    if destination_object_type in {'capability', 'account_flag'} and destination_id.endswith('.count') and numeric:
        if len(numeric) == 1:
            return numeric[0][1], 'resolved', 'Mapped capability count surface resolved from numeric contributor.'
        return sum(value for _, value in numeric), 'resolved', 'Mapped capability count surface resolved additively from numeric contributors.'
    if bools and len(bools) == len(contributors):
        return all(bools), 'resolved', 'Mapped boolean flag surface resolved with logical-and over all contributors.'
    if len(contributors) == 1:
        row = contributors[0]
        value = _as_float(row.value)
        if value is not None:
            return value, 'resolved', 'Single mapped contributor; direct value preserved.'
        if isinstance(row.value, bool) or row.value_type == 'bool':
            return bool(row.value), 'resolved', 'Single mapped contributor; boolean preserved.'
        if row.value_type in {'display_token', 'raw_text', 'missing_inventory'}:
            return None, 'mapped_not_resolved', 'Single mapped contributor is non-numeric text.'
    if not numeric:
        return None, 'mapped_not_resolved', 'No numeric contributor values available.'
    if len(numeric) >= 1 and len(numeric) < len(contributors):
        nums = [value for _, value in numeric]
        if len(nums) == 1:
            return nums[0], 'resolved', 'Resolved from the available numeric contributor; non-numeric mapped contributors were ignored.'
    suffix = destination_id.split('.')[-1]
    additive_suffixes = (
        'seconds', 'duration', 'cooldown', 'cooldown_seconds', 'duration_seconds',
        'meters', 'range', 'range_m', 'angle', 'angle_degrees', 'count', 'quantity', 'targets',
        'chance', 'chance_pct', 'pct', 'bonus_pct', 'damage_reduction_pct', 'speed_reduction_pct',
        'size', 'radius', 'radius_m', 'amount', 'waves_required_delta',
    )
    multiplier_suffixes = ('multiplier', 'multiplier_x')
    if len(numeric) == len(contributors):
        values = [value for _, value in numeric]
        if suffix.endswith(additive_suffixes) or destination_id in {'bot.global.range_bonus_m'}:
            return sum(values), 'resolved', 'Mapped runtime/meta surface resolved with additive suffix rule.'
        if suffix.endswith(multiplier_suffixes):
            product = 1.0
            for value in values:
                product *= _multiplier_from_value(value)
            return product, 'resolved', 'Mapped runtime/meta surface resolved with multiplier suffix rule.'
        if len(values) == 1:
            return values[0], 'resolved', 'Single numeric contributor preserved.'
    return None, 'mapped_not_resolved', 'Mapped destination retained but no validated generic resolver rule applied.'


def _resolve_bucket(
    destination_object_type: str,
    destination_id: str,
    contributors: list[StatInput],
    meta: dict[str, str],
) -> tuple[float | None, str, str, dict[str, object]]:
    schema = _destination_type_schema(destination_id, meta)
    publish_ok, publish_note, bad_contributors, schema = _publish_gate_check(
        destination_object_type, destination_id, contributors, meta
    )
    if not publish_ok:
        return (
            None,
            'mapped_not_resolved',
            publish_note + (' Offending contributors: ' + ', '.join(bad_contributors[:12]) if bad_contributors else ''),
            schema,
        )

    if destination_object_type == 'mechanic_param' and destination_id.startswith('uw.'):
        resolved_rows = meta.get('_resolved_rows', {})
        uw_prefix = '.'.join(destination_id.split('.')[:2])
        unlock_row = resolved_rows.get(_cap(f'{uw_prefix}.owned'))
        if unlock_row is not None and bool(unlock_row.final_value) is False:
            return 0.0, 'resolved', f'UW unlock-gated to zero because {uw_prefix} is not owned.', schema

        def _sum_rows(*families: str) -> float:
            total = 0.0
            for row in contributors:
                if families and row.source_family not in set(families):
                    continue
                value = _as_float(row.value)
                if value is not None:
                    total += value
            return total

        def _product_rows(*families: str) -> float:
            product = 1.0
            seen = False
            for row in contributors:
                if families and row.source_family not in set(families):
                    continue
                value = _as_float(row.value)
                if value is None:
                    continue
                product *= _canonical_source_multiplier(destination_id, row, value)
                seen = True
            return product if seen else 1.0

        additive_scalar_uw = {
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
        }
        additive_pct_uw = {
            'uw.chain_lightning.chance_pct',
            'uw.chrono_field.slow_pct',
            'uw.chrono_field.damage_reduction_pct',
            'uw.poison_swamp.stun_chance_pct',
            'uw.black_hole.damage_pct_enemy_hp_per_second',
            'uw.chain_lightning.max_enemy_damage_reduction_pct',
        }
        additive_multiplier_uw = {
            'uw.golden_tower.bonus_multiplier',
            'uw.spotlight.bonus_multiplier',
            'uw.chain_lightning.damage_multiplier',
            'uw.death_wave.damage_multiplier',
            'uw.poison_swamp.damage_multiplier',
            'uw.smart_missiles.damage_multiplier',
        }
        additive_count_uw = {
            'uw.chain_lightning.quantity',
            'uw.death_wave.effect_wave_count',
            'uw.inner_land_mines.quantity',
            'uw.smart_missiles.quantity',
            'uw.smart_missiles.barrage_quantity',
            'uw.spotlight.count',
            'uw.poison_swamp.rend_additional_enemies',
        }
        if destination_id in additive_multiplier_uw:
            return (
                _sum_rows('uw', 'lab', 'module_substat') * _product_rows('perk'),
                'resolved',
                'UW additive-then-perk-multiplier composition resolved from unified mechanic bucket.',
                schema,
            )
        if destination_id in additive_scalar_uw:
            return _sum_rows('uw', 'lab', 'module_substat', 'perk'), 'resolved', 'UW additive scalar composition resolved from unified mechanic bucket.', schema
        if destination_id in additive_pct_uw:
            return _sum_rows('uw', 'lab', 'module_substat', 'perk'), 'resolved', 'UW additive percentage composition resolved from unified mechanic bucket.', schema
        if destination_id in additive_count_uw:
            return float(int(_sum_rows('uw', 'lab', 'module_substat', 'perk'))), 'resolved', 'UW integer-count composition resolved from unified mechanic bucket.', schema
        value, status, notes = _safe_single_or_uniform_resolution(destination_object_type, destination_id, contributors)
        return value, status, notes, schema

    if destination_object_type != 'canonical_stat' and not (destination_object_type == 'mechanic_param' and destination_id.startswith('bot.')):
        value, status, notes = _safe_single_or_uniform_resolution(destination_object_type, destination_id, contributors)
        return value, status, notes, schema

    resolved_rows = meta.get('_resolved_rows', {})

    if destination_id == 'tower_defense_absolute':
        return _resolve_base_times_post_multipliers(destination_id, contributors, schema, note_label='Promoted shared base-times-post-multipliers family')
    if destination_id == 'tower_damage_per_meter_multiplier':
        return _resolve_decimal_base_times_post_multipliers(destination_id, contributors, schema)
    if destination_id == 'wall_fortification_multiplier':
        lab_pct = next((_as_float(row.value) for row in contributors if row.source_family == 'lab'), None)
        if lab_pct is None:
            return None, 'mapped_not_resolved', 'Missing wall fortification lab value.', schema
        return 1.0 + (lab_pct / 100.0), 'resolved', 'Destination-specific wall fortification formula: 1 + lab percent / 100.', schema
    if destination_id == 'wall_invincibility_duration_seconds':
        lab_seconds = next((_as_float(row.value) for row in contributors if row.source_family == 'lab'), None)
        if lab_seconds is None:
            return None, 'mapped_not_resolved', 'Missing wall invincibility lab value.', schema
        return lab_seconds, 'resolved', 'Destination-specific wall invincibility formula: direct lab seconds.', schema
    if destination_id == 'module.orbital_augment.electron_count':
        values = [_as_float(row.value) for row in contributors]
        values = [value for value in values if value is not None]
        if not values:
            return None, 'mapped_not_resolved', 'Missing Orbital Augment unique-effect count contributor.', schema
        return int(max(values)), 'resolved', 'Destination-specific Orbital Augment electron-count formula: rarity-derived integer unique-effect count.', schema
    if destination_id == 'coin_kill_multiplier':
        mirror_row = resolved_rows.get(_canon('coins_per_kill_bonus'))
        if mirror_row and mirror_row.final_value is not None:
            return _as_float(mirror_row.final_value), 'resolved', f"Deprecated transition mirror of {_canon('coins_per_kill_bonus')}.", schema
        return None, 'mapped_not_resolved', f"Deprecated transition mirror requires {_canon('coins_per_kill_bonus')}.", schema
    if destination_id == 'wall_thorns_damage_pct':
        wall_ratio = next((_as_float(row.value) for row in contributors if row.source_family == 'lab'), None)
        tower_thorns = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
        if wall_ratio is None:
            return None, 'mapped_not_resolved', 'Missing wall thorns ratio or tower thorns base.', schema
        if wall_ratio > 1.0:
            wall_ratio /= 100.0
        if tower_thorns is None:
            return wall_ratio * 100.0, 'resolved', 'Destination-specific wall thorns fallback: lab ratio preserved as percent because tower-thorns base is external to this bucket.', schema
        return tower_thorns * wall_ratio, 'resolved', 'Destination-specific wall thorns formula: tower thorns x wall-thorns ratio.', schema

    unit = meta.get('unit', 'unknown')
    resolver = meta.get('resolver', 'unknown')
    add_sum = 0.0
    multiplier_product = 1.0
    additive_pct = 0.0
    consumed = 0
    unsupported: list[str] = []
    additive_units = {'count', 'seconds', 'm', 'rpm', 'hp', 'damage', 'hp_per_second', 'attacks_per_second', 'damage_block', 'force', 'cash', 'coins'}

    for row in contributors:
        value = _as_float(row.value)
        if value is None:
            unsupported.append(f'{row.source_family}:{row.source_name}:non_numeric')
            continue
        measure = _contributor_measure(row)
        if unit in additive_units:
            if measure == 'level':
                unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                continue
            if unit == 'count':
                if row.value_type == 'multiplier_display':
                    multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                else:
                    add_sum += value
                consumed += 1
                continue
            if measure in {'flat', 'count', 'seconds', 'm', 'rpm', 'resolved_value'} and row.source_family == 'workshop':
                add_sum += value
                consumed += 1
                continue
            if row.source_family in {'lab', 'relic', 'card', 'enhancement', 'module_substat', 'module', 'vault'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
                continue
            if measure == 'pct' and unit in {'m', 'rpm', 'damage_block', 'force', 'cash', 'coins'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
                continue
        if unit == 'pct':
            if measure == 'level':
                unsupported.append(f'{row.source_family}:{row.source_name}:unresolved_level_token')
                continue
            if measure == 'multiplier':
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
                continue
            if measure in {'pct', 'resolved_value', 'flat'}:
                if row.source_family == 'module_substat' and row.value_type == 'percent_display' and 0.0 <= value <= 100.0:
                    additive_pct += value
                elif row.source_family == 'module_substat' and 0.0 <= value <= 1.0:
                    additive_pct += value * 100.0
                elif row.source_family in {'relic', 'vault'} and 0.0 <= value <= 1.0:
                    additive_pct += value * 100.0
                else:
                    additive_pct += value
                consumed += 1
                continue
        if unit == 'multiplier':
            if row.source_family in {'lab', 'relic', 'card', 'enhancement', 'module_substat', 'module', 'vault'}:
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
                continue
            add_sum += value
            consumed += 1
            continue
        unsupported.append(f'{row.source_family}:{row.source_name}:{measure}')

    if consumed > 0:
        if unit == 'pct':
            final = (add_sum + additive_pct) * multiplier_product
            if resolver == 'pct_capped_scalar_stat':
                cap = CANONICAL_PCT_CAPS.get(destination_id)
                if cap is not None:
                    final = max(0.0, min(cap, final))
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

    raise ValueError(
        f'No native bounded bucket resolver path is available for {destination_object_type}::{destination_id}.'
    )


def _apply_free_upgrade_chance_formula_from_routed_contributors(rows: dict[str, StatRow]) -> None:
    support_row = rows.get(_canon('free_upgrade_multiplier'))
    support_multiplier = 1.0
    support_contributors: list[dict[str, object]] = []
    if support_row is not None:
        for contributor in support_row.contributors:
            row = _phase3_statinput_from_dict(contributor)
            value = _as_float(contributor.get('value'))
            if value is None:
                continue
            if row.source_family == 'enhancement':
                support_multiplier *= value
                support_contributors.append(dict(contributor))

    ordered_targets = [
        _canon('free_attack_upgrade_chance_pct'),
        _canon('free_defense_upgrade_chance_pct'),
        _canon('free_utility_upgrade_chance_pct'),
    ]
    shared_additive = None
    shared_additive_contributors: list[dict[str, object]] = []

    for key in ordered_targets:
        stat_row = rows.get(key)
        if stat_row is None:
            continue
        shared_total = 0.0
        local_total = 0.0
        local_contributors: list[dict[str, object]] = []
        shared_contributors_for_row: list[dict[str, object]] = []
        for contributor in stat_row.contributors:
            row = _phase3_statinput_from_dict(contributor)
            value = _as_float(contributor.get('value'))
            if value is None:
                continue
            if row.source_family in {'card', 'perk'}:
                shared_total += value
                shared_contributors_for_row.append(dict(contributor))
                continue
            if row.source_family in {'relic', 'vault'} and 0.0 <= value <= 1.0:
                value *= 100.0
            local_total += value
            local_contributors.append(dict(contributor))

        if shared_additive is None:
            shared_additive = shared_total
            shared_additive_contributors = shared_contributors_for_row
            rows[_canon('free_upgrade_shared_add_pct')] = StatRow(
                stat_name=_canon('free_upgrade_shared_add_pct'),
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


def _apply_exact_max_rend_formula(rows: dict[str, StatRow]) -> None:
    max_rend_row = rows.get(_canon('max_rend_mult'))
    if not max_rend_row:
        return
    enhancement_multiplier = 1.0
    has_enhancement = False
    lab_bonus = 0.0
    module_pct_bonus = 0.0
    for contributor in max_rend_row.contributors:
        row = _phase3_statinput_from_dict(contributor)
        value = _as_float(contributor.get('value'))
        if value is None:
            continue
        if row.source_family == 'enhancement':
            enhancement_multiplier *= value
            has_enhancement = True
        elif row.source_family == 'lab':
            if row.value_type == 'resolved_value':
                lab_bonus += value
        elif row.source_family == 'module_substat':
            if row.value_type == 'percent_display':
                module_pct_bonus += value / 100.0
            else:
                module_pct_bonus += value
    if not has_enhancement:
        return
    pre_enhancement_cap = 8.0 + lab_bonus + (8.0 * module_pct_bonus)
    max_rend_row.final_value = pre_enhancement_cap * enhancement_multiplier
    max_rend_row.status = 'resolved'
    max_rend_row.notes = 'Phase 3 exact Max Rend formula from EP/KB: (8 + lab max-rend bonus + 8 x module-substat max-rend pct bonus) x Rend Armor enhancement multiplier.'


def _load_pack_multiplier_map() -> dict[str, float]:
    import csv

    table = _ROOT / 'kb' / 'global-rules' / 'tables' / 'player-pack-coin-multipliers.csv'
    out: dict[str, float] = {}
    try:
        with table.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            for record in reader:
                out[record['flag_destination']] = float(record['multiplier'])
    except Exception:
        out = {
            'account_flag.disable_ads': 1.5,
            'account_flag.starter_pack': 2.0,
            'account_flag.epic_pack': 3.0,
        }
    return out


def _load_tier_coin_bonus(tier_display_raw) -> float | None:
    if not isinstance(tier_display_raw, str):
        return None
    import csv
    import re

    match = re.search(r'(\d+)', tier_display_raw)
    if not match:
        return None
    tier_num = int(match.group(1))
    try:
        tier_table = _ROOT / 'kb' / 'tournaments' / 'tables' / 'tier-battle-condition-levels.csv'
        with tier_table.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            for record in reader:
                if int(record['tier']) == tier_num:
                    return float(record['coin_bonus'])
    except Exception:
        return None
    return None


def _apply_phase3_postprocessing(rows: dict[str, StatRow]) -> None:
    _apply_free_upgrade_chance_formula_from_routed_contributors(rows)
    _apply_exact_max_rend_formula(rows)

    coins_per_kill_row = rows.get(_canon('coins_per_kill_bonus'))
    if coins_per_kill_row is not None:
        rows[_canon('coin_kill_multiplier')] = StatRow(
            stat_name=_canon('coin_kill_multiplier'),
            final_value=coins_per_kill_row.final_value,
            value_type=coins_per_kill_row.value_type,
            source_count=coins_per_kill_row.source_count,
            status=coins_per_kill_row.status,
            notes=f"Deprecated transition mirror of {_canon('coins_per_kill_bonus')}.",
            contributors=list(coins_per_kill_row.contributors),
            schema=coins_per_kill_row.schema,
        )

    disable_ads_row = rows.get(_flag('account_flag.disable_ads'))
    starter_pack_row = rows.get(_flag('account_flag.starter_pack'))
    epic_pack_row = rows.get(_flag('account_flag.epic_pack'))
    farming_tier_row = rows.get(_context('account_context.farming_tier'))
    legacy_coin_display_row = rows.get(_context('account_context.coin_multiplier_display'))
    helper_contributors: list[dict[str, object]] = []

    def _helper_value(row_key: str, label: str) -> float | None:
        row = rows.get(row_key)
        if not row:
            return None
        helper_contributors.append({
            'stat_name': label,
            'source_family': 'helper_surface',
            'source_name': label,
            'value': row.final_value,
            'value_type': row.value_type,
            'stage': 'phase3_composition',
            'destination_object_type': 'canonical_stat',
            'destination_id': 'all_coin_bonus_multiplier',
            'resolver_id': 'standard_scalar_stat',
            'kb_mapped': True,
        })
        return _as_float(row.final_value)

    coin_bonus_val = _helper_value(_canon('coin_bonus_multiplier'), _canon('coin_bonus_multiplier'))
    coins_mult_val = _helper_value(_canon('coins_multiplier'), _canon('coins_multiplier'))
    theme_val = _helper_value(_cosmetic('cosmetic_bonus.theme_song_coin_multiplier'), 'cosmetic_bonus.theme_song_coin_multiplier')
    pack_multiplier_map = _load_pack_multiplier_map()

    def _flag_pack_multiplier(row: StatRow | None, label: str) -> float:
        multiplier = float(pack_multiplier_map.get(label, 1.0))
        enabled = bool(getattr(row, 'final_value', False)) if row is not None else False
        helper_contributors.append({
            'stat_name': label,
            'source_family': 'helper_surface',
            'source_name': label,
            'value': multiplier if enabled else 1.0,
            'value_type': 'multiplier',
            'stage': 'phase3_composition',
            'destination_object_type': 'canonical_stat',
            'destination_id': 'all_coin_bonus_multiplier',
            'resolver_id': 'standard_scalar_stat',
            'kb_mapped': True,
            'notes': 'kb_pack_flag_multiplier_if_true' if enabled else 'kb_pack_flag_multiplier_if_false',
        })
        return multiplier if enabled else 1.0

    disable_ads_mult = _flag_pack_multiplier(disable_ads_row, 'account_flag.disable_ads')
    starter_pack_mult = _flag_pack_multiplier(starter_pack_row, 'account_flag.starter_pack')
    epic_pack_mult = _flag_pack_multiplier(epic_pack_row, 'account_flag.epic_pack')

    tier_display_raw = None if farming_tier_row is None else (
        farming_tier_row.contributors[0].get('value') if farming_tier_row.contributors else farming_tier_row.final_value
    )
    helper_contributors.append({
        'stat_name': 'account_context.farming_tier',
        'source_family': 'helper_surface',
        'source_name': 'account_context.farming_tier',
        'value': tier_display_raw,
        'value_type': 'raw_text',
        'stage': 'phase3_composition',
        'destination_object_type': 'canonical_stat',
        'destination_id': 'all_coin_bonus_multiplier',
        'resolver_id': 'standard_scalar_stat',
        'kb_mapped': True,
    })
    helper_contributors.append({
        'stat_name': 'account_context.coin_multiplier_display',
        'source_family': 'helper_surface',
        'source_name': 'account_context.coin_multiplier_display',
        'value': None if legacy_coin_display_row is None else (
            legacy_coin_display_row.contributors[0].get('value') if legacy_coin_display_row.contributors else legacy_coin_display_row.final_value
        ),
        'value_type': 'raw_text',
        'stage': 'phase3_composition',
        'destination_object_type': 'canonical_stat',
        'destination_id': 'all_coin_bonus_multiplier',
        'resolver_id': 'standard_scalar_stat',
        'kb_mapped': True,
        'notes': 'legacy_trace_only_not_used_numerically',
    })

    tier_multiplier_val = _load_tier_coin_bonus(tier_display_raw)
    helper_contributors.append({
        'stat_name': 'account_context.farming_tier_coin_multiplier',
        'source_family': 'helper_surface',
        'source_name': 'account_context.farming_tier_coin_multiplier',
        'value': tier_multiplier_val,
        'value_type': 'multiplier' if tier_multiplier_val is not None else 'unresolved',
        'stage': 'phase3_composition',
        'destination_object_type': 'canonical_stat',
        'destination_id': 'all_coin_bonus_multiplier',
        'resolver_id': 'standard_scalar_stat',
        'kb_mapped': True,
        'notes': 'kb_tier_coin_bonus_lookup',
    })

    all_coin_value = None
    all_coin_status = 'mapped_not_resolved'
    all_coin_notes = 'Derived all-coin display surface: coin_bonus_multiplier x coins_multiplier x theme song coin multiplier x farming-tier coin bonus x numeric premium-pack multipliers (Disable Ads 1.5x, Starter Pack 2x, Epic Pack 3x when unlocked). Legacy account coin multiplier display remains trace-only.'
    if coin_bonus_val is not None and coins_mult_val is not None and theme_val is not None and tier_multiplier_val is not None:
        all_coin_value = coin_bonus_val * coins_mult_val * theme_val * tier_multiplier_val * disable_ads_mult * starter_pack_mult * epic_pack_mult
        all_coin_status = 'resolved'
    else:
        all_coin_notes += ' One or more required numeric helper surfaces were unavailable.'
    rows[_canon('all_coin_bonus_multiplier')] = StatRow(
        stat_name=_canon('all_coin_bonus_multiplier'),
        final_value=all_coin_value,
        value_type='multiplier',
        source_count=len(helper_contributors),
        status=all_coin_status,
        notes=all_coin_notes,
        contributors=helper_contributors,
        schema={'unit': 'multiplier', 'resolver': 'standard_scalar_stat'},
    )

    tower_regen_row = rows.get(_canon('tower_regen'))
    wall_regen_row = rows.get(_canon('wall_regen'))
    if tower_regen_row and wall_regen_row and tower_regen_row.final_value is not None:
        tower_regen = _as_float(tower_regen_row.final_value)
        if tower_regen is not None:
            wall_regen_ratio = None
            multiplier = 1.0
            for contributor in wall_regen_row.contributors:
                row = _phase3_statinput_from_dict(contributor)
                value = _as_float(contributor.get('value'))
                if value is None:
                    continue
                if row.source_family == 'lab':
                    wall_regen_ratio = value / 100.0
                elif row.source_family == 'module' and row.value_type == 'multiplier_display':
                    multiplier *= value
                elif row.source_family == 'module_substat':
                    multiplier *= 1.0 + (value / 100.0)
            if wall_regen_ratio is not None:
                wall_regen_row.final_value = tower_regen * wall_regen_ratio * multiplier
                wall_regen_row.status = 'resolved'
                wall_regen_row.notes = 'Phase 3 exact wall regen formula from KB: tower_regen x wall-regen ratio x wall-regen multipliers.'

    package_row = rows.get(_canon('package_chance_pct'))
    if package_row:
        final, status, note, _ = _resolve_additive_base_plus_bonuses_pct(
            'package_chance_pct',
            [_phase3_statinput_from_dict(contributor) for contributor in package_row.contributors],
            {'unit': 'pct', 'resolver': 'pct_capped_scalar_stat'},
        )
        if final is not None:
            cap = CANONICAL_PCT_CAPS.get('package_chance_pct')
            if cap is not None:
                final = max(0.0, min(cap, final))
            package_row.final_value = final
            package_row.status = status
            package_row.notes = note

    runtime_mirror_map = {
        _mech('uw.chain_lightning.chance_pct'): _runtime('uw.chain_lightning.chance_pct'),
        _mech('uw.chain_lightning.damage_multiplier'): _runtime('uw.chain_lightning.damage_multiplier'),
        _mech('uw.spotlight.bonus_multiplier'): _runtime('uw.spotlight.bonus_multiplier'),
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


@lru_cache(maxsize=1)
def _load_bounded_resolution_metadata_cached() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in _CONTRACT_PATHS:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        for domain, entries in data['domains'].items():
            for entry in entries:
                out[entry['id']] = {
                    'domain': domain,
                    'unit': entry['unit'],
                    'resolver': entry['resolver'],
                }
    return out

# Canonical timing-v1 surface IDs declared in stat-query-initial-surface-set.yaml (timing_v1 group).
# All declared timing families share this surface set.
# wave_accelerator uses state:: (canonical per naming-contract-pack-v2-remap.csv and KB contracts),
# not the legacy runtime_mechanic_param:: prefix.
_TIMING_V1_SURFACE_IDS: tuple[str, ...] = (
    _mech('uw.black_hole.cooldown_seconds'),
    _mech('uw.black_hole.duration_seconds'),
    _mech('uw.golden_tower.cooldown_seconds'),
    _mech('uw.golden_tower.duration_seconds'),
    'state::tower.package_chance_pct',
    'support_surface::timing.gcomp_cooldown_reduction_seconds',
    'support_surface::timing.wave_duration_seconds_effective',
    'state::cards.wave_accelerator.spawn_rate_acceleration',
)

# Declared progression-family surface set. All three declared progression families share the
# same surface denominator at the flat statbook compatibility boundary; their semantic split
# only matters once bounded runtime/overlay execution begins inside the QE-owned progression stack.
_PROGRESSION_V1_SURFACE_IDS: tuple[str, ...] = (
    'state::tower.hp',
    'state::wall.hp',
    'state::wall.regen',
    'state::wall.fortification_multiplier',
    'state::tower.defense_pct',
    'state::tower.thorns_damage_pct',
    'state::tower.orb_count',
    'state::tower.orb_speed_rpm',
    'state::cards.plasma_cannon.effect_pct',
    _state('module.orbital_augment.electron_count'),
    _state('module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'),
    _state('module.primordial_collapse.bh_damage_reduction_pct'),
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'support_surface::free_upgrade_multiplier',
)

_TIMING_SURFACE_IDS: tuple[str, ...] = _TIMING_V1_SURFACE_IDS
_PROGRESSION_SURFACE_ID_SET = frozenset(_PROGRESSION_V1_SURFACE_IDS)

_DELEGATED_FAMILY_SURFACE_IDS: dict[str, tuple[str, ...]] = {
    _TIMING_TOURNAMENT_NO_PERKS: _TIMING_V1_SURFACE_IDS,
    _TIMING_FARM_WITH_PERKS: _TIMING_V1_SURFACE_IDS,
    # timing_scenario_probe surface set declared; not in _TIMING_FAMILY_BY_PRESET because it
    # shares the 'Farming' preset with timing_farm_with_perks (no fixed detection convention).
    'timing_scenario_probe': _TIMING_V1_SURFACE_IDS,
    # progression_start_of_run is the flat-statbook compatibility contract used by resolve_stats().
    # progression_runtime_no_perks shares this exact bounded surface set and remains QE-owned
    # through the direct progression helpers and runtime-consumer bundles.
    _PROGRESSION_START_OF_RUN: _PROGRESSION_V1_SURFACE_IDS,
    _PROGRESSION_RUNTIME_WITH_PERKS: _PROGRESSION_V1_SURFACE_IDS,
}

# Unambiguous preset-name → declared timing family mapping used by _infer_manifest_approved_family.
# timing_scenario_probe is not included: it has no fixed preset-name convention and is not
# delegated through the resolve_stats compatibility entrypoint in PH4-B.
_TIMING_FAMILY_BY_PRESET: dict[str, str] = {
    'Tourney': _TIMING_TOURNAMENT_NO_PERKS,
    'Farming': _TIMING_FARM_WITH_PERKS,
}


@dataclass(frozen=True)
class QEResolvedSnapshot:
    binding: StateIdentityBinding
    stat_inputs: tuple[StatInput, ...]
    statbook: StatBook
    resolution_path: str
    native_family_id: str | None = None


@dataclass(frozen=True)
class QEFamilyQueryResult:
    binding: StateIdentityBinding | None
    stat_inputs: tuple[StatInput, ...]
    family_id: str
    requested_surface_ids: tuple[str, ...]
    response: QueryResponse
    resolution_path: str


class QEResolutionPlanner:
    """Canonical request-keyed QE snapshot planner.

    The hot path should resolve a normalized QE request once, then reuse the
    resulting stat inputs/statbook across compare, diagnostics, and publication
    consumers. This planner centralizes that cache so callers stop rebuilding
    near-identical statbooks ad hoc.

    The current backend still routes through the compatibility full-statbook
    resolver where broader family-native coverage is not available yet. That
    compatibility detail is intentionally hidden behind this planner so callers
    can stay on a stable native QE request interface.
    """

    def __init__(self) -> None:
        self._snapshot_cache: dict[tuple[str, str, str, str], QEResolvedSnapshot] = {}
        self._family_query_cache: dict[tuple[str, str, str, str, str, tuple[str, ...], str], QEFamilyQueryResult] = {}

    def resolve_report_snapshot(
        self,
        account_state,
        *,
        preset_name: str | None = None,
        state_mode: str = 'start_of_run',
        card_preset_name: str | None = None,
        module_preset_name: str | None = None,
        perk_preset_name: str | None = None,
        perks_enabled: bool | None = None,
    ) -> QEResolvedSnapshot:
        bound_inputs = compile_stat_inputs_with_identity(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
        )
        return self.resolve_bound_report_snapshot(bound_inputs)

    def resolve_bound_report_snapshot(self, bound_inputs: BoundStatInputs) -> QEResolvedSnapshot:
        key = _snapshot_cache_key(bound_inputs)
        cached = self._snapshot_cache.get(key)
        if cached is None:
            cached = _build_report_snapshot(bound_inputs)
            self._snapshot_cache[key] = cached
        return copy.deepcopy(cached)

    def resolve_family_query(
        self,
        account_state,
        *,
        requested_surface_ids: Sequence[str],
        preset_name: str | None = None,
        state_mode: str = 'start_of_run',
        card_preset_name: str | None = None,
        module_preset_name: str | None = None,
        perk_preset_name: str | None = None,
        perks_enabled: bool | None = None,
        trace_mode: str = 'contributors',
    ) -> QEFamilyQueryResult:
        bound_inputs = compile_stat_inputs_with_identity(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
        )
        return self.resolve_bound_family_query(
            bound_inputs,
            requested_surface_ids=requested_surface_ids,
            trace_mode=trace_mode,
        )

    def resolve_bound_family_query(
        self,
        bound_inputs: BoundStatInputs,
        *,
        requested_surface_ids: Sequence[str],
        trace_mode: str = 'contributors',
    ) -> QEFamilyQueryResult:
        family_id = _infer_manifest_approved_family(bound_inputs.stat_inputs)
        if family_id is None:
            raise ValueError('Requested QE family query has no manifest-approved native family for the supplied stat inputs.')
        return self.resolve_bound_declared_family_query(
            bound_inputs,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            trace_mode=trace_mode,
        )

    def resolve_bound_declared_family_query(
        self,
        bound_inputs: BoundStatInputs,
        *,
        family_id: str,
        requested_surface_ids: Sequence[str],
        trace_mode: str = 'contributors',
    ) -> QEFamilyQueryResult:
        normalized_requested = tuple(str(surface_id) for surface_id in requested_surface_ids)
        key = _snapshot_cache_key(bound_inputs) + (family_id, normalized_requested, str(trace_mode))
        cached = self._family_query_cache.get(key)
        if cached is None:
            cached = _build_family_query_result(
                bound_inputs,
                family_id=family_id,
                requested_surface_ids=normalized_requested,
                trace_mode=trace_mode,
            )
            self._family_query_cache[key] = cached
        return copy.deepcopy(cached)

    def resolve_declared_family_query(
        self,
        account_state,
        *,
        family_id: str,
        requested_surface_ids: Sequence[str],
        preset_name: str | None = None,
        state_mode: str = 'start_of_run',
        card_preset_name: str | None = None,
        module_preset_name: str | None = None,
        perk_preset_name: str | None = None,
        perks_enabled: bool | None = None,
        trace_mode: str = 'contributors',
    ) -> QEFamilyQueryResult:
        bound_inputs = compile_stat_inputs_with_identity(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
        )
        return self.resolve_bound_declared_family_query(
            bound_inputs,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            trace_mode=trace_mode,
        )

    def resolve_declared_family_statbook(
        self,
        account_state,
        *,
        family_id: str,
        requested_surface_ids: Sequence[str],
        notes: str,
        diagnostics: dict[str, object] | None = None,
        preset_name: str | None = None,
        state_mode: str = 'start_of_run',
        card_preset_name: str | None = None,
        module_preset_name: str | None = None,
        perk_preset_name: str | None = None,
        perks_enabled: bool | None = None,
        trace_mode: str = 'contributors',
    ) -> StatBook:
        result = self.resolve_declared_family_query(
            account_state,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            trace_mode=trace_mode,
        )
        return query_response_to_statbook(
            result.response,
            notes=notes,
            diagnostics=diagnostics,
        )

    def resolve_rows_declared_family_query(
        self,
        *,
        identity: StateIdentity,
        stat_inputs: Sequence[StatInput],
        family_id: str,
        requested_surface_ids: Sequence[str],
        trace_mode: str = 'contributors',
    ) -> QEFamilyQueryResult:
        normalized_requested = tuple(str(surface_id) for surface_id in requested_surface_ids)
        key = (
            identity.account_snapshot_id,
            identity.loadout_id,
            identity.scenario_id,
            identity.runtime_branch_id,
            family_id,
            normalized_requested,
            str(trace_mode),
        )
        cached = self._family_query_cache.get(key)
        if cached is None:
            cached = _build_rows_family_query_result(
                identity=identity,
                stat_inputs=tuple(stat_inputs),
                family_id=family_id,
                requested_surface_ids=normalized_requested,
                trace_mode=trace_mode,
            )
            self._family_query_cache[key] = cached
        return copy.deepcopy(cached)

    def resolve_rows_declared_family_statbook(
        self,
        *,
        identity: StateIdentity,
        stat_inputs: Sequence[StatInput],
        family_id: str,
        requested_surface_ids: Sequence[str],
        notes: str,
        diagnostics: dict[str, object] | None = None,
        trace_mode: str = 'contributors',
    ) -> StatBook:
        result = self.resolve_rows_declared_family_query(
            identity=identity,
            stat_inputs=stat_inputs,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            trace_mode=trace_mode,
        )
        return query_response_to_statbook(
            result.response,
            notes=notes,
            diagnostics=diagnostics,
        )


def load_bounded_resolution_metadata() -> dict[str, dict[str, str]]:
    """Sanctioned QE support surface for bounded native/runtime consumers."""
    return dict(_load_bounded_resolution_metadata_cached())


def resolve_bounded_bucket(
    destination_object_type: str,
    destination_id: str,
    contributors: list[StatInput],
    meta: dict[str, str],
):
    """Sanctioned QE support surface for bounded native/runtime consumers."""
    return _resolve_bucket(destination_object_type, destination_id, contributors, meta)


def apply_bounded_phase3_postprocessing(rows: dict[str, StatRow]) -> None:
    """Sanctioned QE support surface for bounded native/runtime consumers."""
    _apply_phase3_postprocessing(rows)


def classify_input_routing(row: StatInput) -> str:
    """Sanctioned QE diagnostic helper surface for active non-QE consumers."""
    note = str(row.notes or '')
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


def summarize_input_routing(stat_inputs: list[StatInput]) -> dict[str, object]:
    """Sanctioned QE diagnostic helper surface for active non-QE consumers."""
    from collections import Counter

    class_counts = Counter(classify_input_routing(row) for row in stat_inputs)
    family_routed_counts = Counter(row.source_family for row in stat_inputs if row.destination_id)
    family_unrouted_counts = Counter(
        row.source_family for row in stat_inputs if classify_input_routing(row) == 'truly_unrouted_unknown'
    )
    return {
        'class_counts': dict(sorted(class_counts.items())),
        'routed_input_count': sum(1 for row in stat_inputs if row.destination_id),
        'truly_unrouted_input_count': class_counts.get('truly_unrouted_unknown', 0),
        'routed_count_by_family': dict(sorted(family_routed_counts.items())),
        'truly_unrouted_count_by_family': dict(sorted(family_unrouted_counts.items())),
    }


def resolve_stats(stat_inputs: list[StatInput]) -> StatBook:
    identity = StateIdentity(
        account_snapshot_id='resolve_stats_compatibility_entrypoint',
        loadout_id='resolve_stats_compatibility_entrypoint',
        scenario_id='resolve_stats_compatibility_entrypoint',
        runtime_branch_id='branch_base',
    )
    return _resolve_hybrid_statbook_from_rows(
        stat_inputs=tuple(stat_inputs),
        identity=identity,
    )


def _resolve_compat_statbook(stat_inputs: Sequence[StatInput]) -> StatBook:
    identity = StateIdentity(
        account_snapshot_id='resolve_stats_compatibility_entrypoint',
        loadout_id='resolve_stats_compatibility_entrypoint',
        scenario_id='resolve_stats_compatibility_entrypoint',
        runtime_branch_id='branch_base',
    )
    return _resolve_hybrid_statbook_from_rows(
        stat_inputs=tuple(stat_inputs),
        identity=identity,
    )


def _build_report_snapshot(bound_inputs: BoundStatInputs) -> QEResolvedSnapshot:
    native_family_id = _infer_manifest_approved_family(bound_inputs.stat_inputs)
    resolution_path = 'report_snapshot_compat'
    statbook = _resolve_hybrid_statbook_from_bound_inputs(bound_inputs)
    if native_family_id is not None:
        resolution_path = 'report_snapshot_hybrid'
    diagnostics = dict(statbook.diagnostics)
    diagnostics['qe_resolution_interface'] = 'report_snapshot_planner'
    diagnostics['qe_resolution_backend'] = resolution_path
    diagnostics['qe_native_family_available'] = native_family_id is not None
    diagnostics['qe_native_family_id'] = native_family_id
    statbook = StatBook(rows=statbook.rows, diagnostics=diagnostics)
    return QEResolvedSnapshot(
        binding=bound_inputs.binding,
        stat_inputs=tuple(bound_inputs.stat_inputs),
        statbook=statbook,
        resolution_path=resolution_path,
        native_family_id=native_family_id,
    )


def _build_family_query_result(
    bound_inputs: BoundStatInputs,
    *,
    family_id: str,
    requested_surface_ids: tuple[str, ...],
    trace_mode: str,
) -> QEFamilyQueryResult:
    query_kernel = StatQueryKernel()
    baseline = query_kernel.materialise_family_baseline(bound_inputs, family_id)
    response = query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=requested_surface_ids,
        trace_mode=trace_mode,
    )
    return QEFamilyQueryResult(
        binding=bound_inputs.binding,
        stat_inputs=tuple(bound_inputs.stat_inputs),
        family_id=family_id,
        requested_surface_ids=requested_surface_ids,
        response=response,
        resolution_path='native_family_query',
    )


def _resolve_hybrid_statbook_from_bound_inputs(bound_inputs: BoundStatInputs) -> StatBook:
    fallback_statbook = _fallback_resolve_stats(list(bound_inputs.stat_inputs))
    native_family_id = _infer_manifest_approved_family(bound_inputs.stat_inputs)
    if native_family_id is None:
        return fallback_statbook
    native_result = _build_family_query_result(
        bound_inputs,
        family_id=native_family_id,
        requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[native_family_id],
        trace_mode='contributors',
    )
    return _merge_delegated_family_rows(
        fallback_statbook=fallback_statbook,
        delegated_response=native_result.response,
        family_id=native_family_id,
    )


def _resolve_hybrid_statbook_from_rows(
    *,
    stat_inputs: tuple[StatInput, ...],
    identity: StateIdentity,
) -> StatBook:
    fallback_statbook = _fallback_resolve_stats(list(stat_inputs))
    native_family_id = _infer_manifest_approved_family(stat_inputs)
    if native_family_id is None:
        return fallback_statbook
    native_result = _build_rows_family_query_result(
        identity=identity,
        stat_inputs=stat_inputs,
        family_id=native_family_id,
        requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[native_family_id],
        trace_mode='contributors',
    )
    return _merge_delegated_family_rows(
        fallback_statbook=fallback_statbook,
        delegated_response=native_result.response,
        family_id=native_family_id,
    )


def _build_rows_family_query_result(
    *,
    identity: StateIdentity,
    stat_inputs: tuple[StatInput, ...],
    family_id: str,
    requested_surface_ids: tuple[str, ...],
    trace_mode: str,
) -> QEFamilyQueryResult:
    query_kernel = StatQueryKernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        identity,
        family_id,
        stat_inputs,
    )
    response = query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=requested_surface_ids,
        trace_mode=trace_mode,
    )
    return QEFamilyQueryResult(
        binding=StateIdentityBinding(identity=identity, account_state=None, scenario_runtime_inputs=None),
        stat_inputs=stat_inputs,
        family_id=family_id,
        requested_surface_ids=requested_surface_ids,
        response=response,
        resolution_path='native_family_query',
    )


def query_response_to_statbook(
    response: QueryResponse,
    *,
    notes: str,
    diagnostics: dict[str, object] | None = None,
) -> StatBook:
    contributors_by_surface: dict[str, list[dict[str, object]]] = {}
    for contributor in response.contributor_rows:
        contributors_by_surface.setdefault(contributor.surface_id, []).append(
            {
                'surface_id': contributor.surface_id,
                'surface_class': contributor.surface_class,
                'domain': contributor.domain,
                'source_class': contributor.source_class,
                'composition_stage': contributor.composition_stage,
                'contributor_id': contributor.contributor_id,
                'value': contributor.value,
                'value_type': contributor.value_type,
                'active': contributor.active,
                'gate_reason': contributor.gate_reason,
                'provenance_ref': contributor.provenance_ref,
            }
        )
    rows = {
        row.surface_id: StatRow(
            stat_name=row.surface_id,
            final_value=row.final_value,
            value_type=row.value_type,
            source_count=len(contributors_by_surface.get(row.surface_id, ())),
            status=row.status,
            notes=notes,
            contributors=contributors_by_surface.get(row.surface_id, []),
        )
        for row in response.resolved_surface_rows
    }
    merged_diagnostics = dict(diagnostics or {})
    merged_diagnostics.setdefault('family_id', response.family_id)
    merged_diagnostics['qe_resolution_interface'] = 'native_family_query'
    merged_diagnostics['qe_resolution_backend'] = 'native_family_query'
    merged_diagnostics['qe_native_family_available'] = True
    merged_diagnostics['qe_native_family_id'] = response.family_id
    return StatBook(rows=rows, diagnostics=merged_diagnostics)


def _snapshot_cache_key(bound_inputs: BoundStatInputs) -> tuple[str, str, str, str]:
    identity = bound_inputs.binding.identity
    return (
        identity.account_snapshot_id,
        identity.loadout_id,
        identity.scenario_id,
        identity.runtime_branch_id,
    )


def _infer_manifest_approved_family(stat_inputs: Sequence[StatInput]) -> str | None:
    preset_names = {str(row.preset_name).strip() for row in stat_inputs if row.preset_name}
    if len(preset_names) != 1:
        return None

    preset_name = next(iter(preset_names))
    has_timing_rows = any(row.source_family == 'scenario_rules' for row in stat_inputs)
    if has_timing_rows:
        return _TIMING_FAMILY_BY_PRESET.get(preset_name)

    if _looks_like_progression_family_rows(stat_inputs):
        # Flat stat_inputs do not preserve enough metadata to distinguish
        # progression_start_of_run from progression_runtime_no_perks. The shared bounded
        # surface contract is still QE-owned, so the compatibility entrypoint delegates
        # against the start-of-run contract unless explicit perk rows are present.
        if any(row.source_family == 'perk' for row in stat_inputs):
            return _PROGRESSION_RUNTIME_WITH_PERKS
        return _PROGRESSION_START_OF_RUN

    return None


def _looks_like_progression_family_rows(stat_inputs: Sequence[StatInput]) -> bool:
    return any(_normalized_surface_id(row) in _PROGRESSION_SURFACE_ID_SET for row in stat_inputs)


def _normalized_surface_id(row: StatInput) -> str | None:
    if not row.destination_object_type or not row.destination_id:
        return None
    return to_v2_surface_id(f'{row.destination_object_type}::{row.destination_id}')

def _resolve_manifest_approved_family(*, family_id: str, stat_inputs: Sequence[StatInput]) -> QueryResponse:
    if family_id not in _DELEGATED_FAMILY_SURFACE_IDS:
        raise ValueError(f'Unsupported manifest-approved resolve_stats delegation family {family_id!r}.')
    query_kernel = get_default_query_kernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        StateIdentity(
            account_snapshot_id='resolve_stats_compatibility_entrypoint',
            loadout_id=f'resolve_stats_{family_id}_loadout',
            scenario_id=f'resolve_stats_{family_id}',
            runtime_branch_id='branch_base',
        ),
        family_id,
        stat_inputs,
    )
    return query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[family_id],
        trace_mode='contributors',
    )
def _merge_delegated_family_rows(
    *,
    fallback_statbook: StatBook,
    delegated_response: QueryResponse,
    family_id: str,
) -> StatBook:
    merged_rows = dict(fallback_statbook.rows)
    for row in delegated_response.resolved_surface_rows:
        if row.surface_id not in fallback_statbook.rows:
            continue
        merged_rows[row.surface_id] = StatRow(
            stat_name=row.surface_id,
            final_value=row.final_value,
            value_type=row.value_type,
            source_count=len([contributor for contributor in delegated_response.contributor_rows if contributor.surface_id == row.surface_id]),
            status=row.status,
            notes=f'Delegated through query kernel for manifest-approved family {family_id}.',
            contributors=[
                {
                    'surface_id': contributor.surface_id,
                    'surface_class': contributor.surface_class,
                    'domain': contributor.domain,
                    'source_class': contributor.source_class,
                    'composition_stage': contributor.composition_stage,
                    'contributor_id': contributor.contributor_id,
                    'value': contributor.value,
                    'value_type': contributor.value_type,
                    'active': contributor.active,
                    'gate_reason': contributor.gate_reason,
                    'provenance_ref': contributor.provenance_ref,
                }
                for contributor in delegated_response.contributor_rows
                if contributor.surface_id == row.surface_id
            ],
            schema={'delegated_family_id': family_id, 'source': 'query_kernel'},
        )
    diagnostics = dict(fallback_statbook.diagnostics)
    diagnostics['qe_native_family_merge'] = {
        'family_id': family_id,
        'merged_surface_ids': list(_DELEGATED_FAMILY_SURFACE_IDS[family_id]),
        'fallback_owner': 'qe.stat_resolution.resolve_stats',
        'bounded_only': True,
    }
    if family_id == _PROGRESSION_START_OF_RUN:
        diagnostics['qe_native_family_merge']['compat_equivalent_declared_families'] = [
            'progression_start_of_run',
            'progression_runtime_no_perks',
        ]
    return StatBook(rows=merged_rows, diagnostics=diagnostics)


__all__ = [
    'QEFamilyQueryResult',
    'QEResolutionPlanner',
    'QEResolvedSnapshot',
    'query_response_to_statbook',
    'resolve_stats',
]
