from __future__ import annotations

import copy
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
import importlib
from pathlib import Path
from typing import Protocol
import yaml

from input.state_types import AccountState, ScenarioProjectionState, ScenarioRuntimeInputs
from qe.compat.legacy_surface_ids import (
    legacy_capability_surface_id as _compat_cap,
    legacy_canonical_surface_id as _state_from_legacy_canonical,
    legacy_context_surface_id as _compat_context,
    legacy_cosmetic_surface_id as _compat_cosmetic,
    legacy_flag_surface_id as _compat_flag,
    legacy_mechanic_surface_id as _compat_mech,
    legacy_runtime_surface_id as _compat_runtime,
)
from qe.contracts import normalize_surface_id_to_contract, to_v2_surface_id
from qe.models import BoundStatInputs, StateIdentity, StateIdentityBinding, compile_stat_inputs_with_identity
from qe.consumer_registry import resolve_consumer_bundle
from qe.dependency_registry import DependencyRegistry
from qe.materializer import BaselineContributorRow
from qe.kernel import QueryResponse, ResolvedSurfaceRow, StatQueryKernel, get_default_query_kernel
from qe.stat_resolution import (
    resolve_stats as _fallback_resolve_stats,
    resolve_stats_delta as _fallback_resolve_stats_delta,
)
from qe.models import StatInput
from qe.models import StatBook, StatRow
from qe.kb_surfaces import CANONICAL_PCT_CAPS
from qe.publication import publish_query_surfaces

_TIMING_TOURNAMENT_NO_PERKS = 'timing_tournament_no_perks'
_TIMING_FARM_WITH_PERKS = 'timing_farm_with_perks'
_PROGRESSION_START_OF_RUN = 'progression_start_of_run'
_PROGRESSION_RUNTIME_NO_PERKS = 'progression_runtime_no_perks'
_PROGRESSION_RUNTIME_WITH_PERKS = 'progression_runtime_with_perks'
_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATHS = (
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'canonical-stats.yaml',
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'mechanic-params.yaml',
    _ROOT / 'kb' / 'global-rules' / 'contracts' / 'environment-params.yaml',
)


def _state(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'state::{destination_id}')


def _extract_tier_number(value: object) -> int | None:
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _as_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


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


_FREE_UPGRADE_CHANCE_DESTINATIONS: frozenset[str] = frozenset({
    'free_attack_upgrade_chance_pct',
    'free_defense_upgrade_chance_pct',
    'free_utility_upgrade_chance_pct',
})


def _resolve_free_upgrade_chance_pct(
    destination_id: str,
    contributors: list[StatInput],
    schema: dict[str, object],
) -> tuple[float | None, str, str, dict[str, object]]:
    workshop_base = next((_as_float(row.value) for row in contributors if row.source_family == 'workshop'), None)
    if workshop_base is None:
        return None, 'mapped_not_resolved', f'Missing workshop base for {destination_id}.', schema
    enhancement_multiplier = 1.0
    additive_bonus_pp = 0.0
    for row in contributors:
        if row.source_family == 'workshop':
            continue
        value = _as_float(row.value)
        if value is None:
            continue
        if row.source_family == 'enhancement':
            enhancement_multiplier *= _canonical_source_multiplier(destination_id, row, value)
            continue
        if row.source_family in {'relic', 'vault'} and 0.0 <= value <= 1.0:
            additive_bonus_pp += value * 100.0
            continue
        additive_bonus_pp += value
    final = (workshop_base + additive_bonus_pp) * enhancement_multiplier
    cap = CANONICAL_PCT_CAPS.get(destination_id)
    if cap is not None:
        final = max(0.0, min(cap, final))
    return final, 'resolved', 'Destination-specific free-upgrade formula: additive percent-point bucket x enhancement multiplier.', schema


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
    final = workshop
    for family in ('lab', 'enhancement', 'card', 'module', 'module_substat', 'perk'):
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
    for family in ('lab', 'enhancement', 'card', 'module', 'module_substat', 'perk'):
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


def _resolve_exact_max_rend_value(contributors: list[StatInput]) -> float | None:
    enhancement_multiplier = 1.0
    has_enhancement = False
    lab_bonus = 0.0
    module_pct_bonus = 0.0
    for row in contributors:
        value = _as_float(row.value)
        if value is None:
            continue
        if row.source_family == 'enhancement':
            enhancement_multiplier *= value
            has_enhancement = True
        elif row.source_family == 'lab' and row.value_type == 'resolved_value':
            lab_bonus += value
        elif row.source_family == 'module_substat':
            if row.value_type == 'percent_display':
                module_pct_bonus += value / 100.0
            else:
                module_pct_bonus += value
    if not has_enhancement:
        return None
    pre_enhancement_cap = 8.0 + lab_bonus + (8.0 * module_pct_bonus)
    return pre_enhancement_cap * enhancement_multiplier


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
        unlock_row = resolved_rows.get(_compat_cap(f'{uw_prefix}.owned'))
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

    if destination_object_type == 'mechanic_param' and destination_id.startswith('bot.'):
        numeric_values = [_as_float(row.value) for row in contributors]
        numeric_values = [value for value in numeric_values if value is not None]
        if not numeric_values:
            return None, 'mapped_not_resolved', 'Missing numeric bot mechanic contributors.', schema

        unit = meta.get('unit', 'unknown')
        resolver = meta.get('resolver', 'unknown')
        final = sum(numeric_values)
        if unit == 'pct' and resolver in {'pct_capped_param', 'pct_capped_scalar_stat'}:
            cap = CANONICAL_PCT_CAPS.get(destination_id)
            if cap is not None:
                final = max(0.0, min(cap, final))
        if unit == 'count' or resolver == 'integer_count_stat':
            final = float(int(round(final)))
        return final, 'resolved', 'Bot additive mechanic composition resolved from unified mechanic bucket.', schema

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
        mirror_row = resolved_rows.get(_state_from_legacy_canonical('coins_per_kill_bonus'))
        if mirror_row and mirror_row.final_value is not None:
            return _as_float(mirror_row.final_value), 'resolved', f"Deprecated transition mirror of {_state_from_legacy_canonical('coins_per_kill_bonus')}.", schema
        return None, 'mapped_not_resolved', f"Deprecated transition mirror requires {_state_from_legacy_canonical('coins_per_kill_bonus')}.", schema
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
    if destination_id == 'max_rend_mult':
        value = _resolve_exact_max_rend_value(contributors)
        if value is None:
            return None, 'mapped_not_resolved', 'Missing enhancement contributor for exact max-rend formula.', schema
        return value, 'resolved', 'Destination-specific max-rend formula: (8 + lab + 8*module_substat_pct) x enhancement.', schema
    if destination_id in _FREE_UPGRADE_CHANCE_DESTINATIONS:
        return _resolve_free_upgrade_chance_pct(destination_id, contributors, schema)

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
            if row.source_family == 'enhancement':
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
                continue
            if getattr(row, 'composition_stage', '') == 'multiplicative':
                multiplier_product *= _canonical_source_multiplier(destination_id, row, value)
                consumed += 1
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
# not the legacy runtime bucket prefix.
_TIMING_V1_SURFACE_IDS: tuple[str, ...] = (
        _compat_mech('uw.black_hole.cooldown_seconds'),
        _compat_mech('uw.black_hole.duration_seconds'),
        _compat_mech('uw.golden_tower.cooldown_seconds'),
        _compat_mech('uw.golden_tower.duration_seconds'),
    'state::tower.package_chance_pct',
    'support_surface::timing.gcomp_cooldown_reduction_seconds',
    'support_surface::timing.wave_duration_seconds_effective',
    'state::cards.wave_accelerator.spawn_rate_acceleration',
    'state::cards.wave_skip.chance_pct',
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
    'state::cards.berserker.assumed_bonus_multiplier',
    'state::uw.black_hole.base_duration_seconds',
    'state::uw.black_hole.base_cooldown_seconds',
    'state::uw.golden_tower.base_duration_seconds',
    'state::uw.golden_tower.base_cooldown_seconds',
    _state('module.orbital_augment.electron_count'),
    _state('module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct'),
    _state('module.primordial_collapse.bh_damage_reduction_pct'),
    'state::bot.thunder.cooldown_seconds',
    'state::bot.thunder.duration_seconds',
    'state::bot.thunder.linger_duration_seconds',
    'state::bot.thunder.linger_slow_pct',
    'state::bot.thunder.range_m',
    'support_surface::ehp.health_relic_pct',
    'support_surface::ehp.dabs_relic_pct',
    'support_surface::ehp.def_pct_relic_pct',
    'support_surface::eecon.adstarter_theme_relic_factor',
    'support_surface::eecon.freeup_attack_relic_pct',
    'support_surface::eecon.freeup_defense_relic_pct',
    'support_surface::eecon.freeup_utility_relic_pct',
    'support_surface::ehp.black_hole_duration_seconds',
    'support_surface::ehp.black_hole_cooldown_seconds',
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
        if family_id in {_TIMING_TOURNAMENT_NO_PERKS, _TIMING_FARM_WITH_PERKS, 'timing_scenario_probe'}:
            config_from_statbook = importlib.import_module('simulators.scenario').config_from_statbook
            resolve_timing_family_query = importlib.import_module('simulators.timing').resolve_timing_family_query

            resolved_perks_enabled = (
                False if family_id in {_TIMING_TOURNAMENT_NO_PERKS, 'timing_scenario_probe'}
                else True if family_id == _TIMING_FARM_WITH_PERKS
                else bool(perks_enabled)
            ) if perks_enabled is None else bool(perks_enabled)
            snapshot = self.resolve_report_snapshot(
                account_state,
                preset_name=preset_name,
                state_mode=state_mode,
                card_preset_name=card_preset_name,
                module_preset_name=module_preset_name,
                perk_preset_name=perk_preset_name,
                perks_enabled=resolved_perks_enabled,
            )
            preset = str(preset_name or getattr(account_state, 'default_preset', '') or 'Farming')
            if family_id == _TIMING_TOURNAMENT_NO_PERKS:
                mode_id = 'tournament'
                league = (
                    getattr(account_state, 'player_meta', {}).get('Tourney League')
                    or getattr(account_state, 'player_meta', {}).get('Tournament League')
                    or getattr(account_state, 'player_meta', {}).get('League')
                )
                tier = 14
            else:
                mode_id = 'farming'
                league = None
                tier = (
                    _extract_tier_number(getattr(account_state, 'player_meta', {}).get('Farming Tier'))
                    or _extract_tier_number(getattr(account_state, 'highest_tier_unlocked_label', None))
                    or getattr(account_state, 'highest_tier_unlocked_number', None)
                    or 14
                )
            scenario_config = config_from_statbook(
                {
                    key: {'final_value': row.final_value}
                    for key, row in snapshot.statbook.rows.items()
                },
                mode_id=mode_id,
                tier=int(tier),
                league=league,
            )
            normalized_requested = tuple(str(surface_id) for surface_id in requested_surface_ids)
            key = (
                snapshot.binding.identity.account_snapshot_id,
                snapshot.binding.identity.loadout_id,
                snapshot.binding.identity.scenario_id,
                snapshot.binding.identity.runtime_branch_id,
                family_id,
                normalized_requested,
                str(trace_mode),
            )
            cached = self._family_query_cache.get(key)
            if cached is None:
                response = resolve_timing_family_query(
                    account_state=account_state,
                    family_id=family_id,
                    preset_name=preset,
                    scenario_config=scenario_config,
                    requested_surface_ids=normalized_requested,
                    state_mode=state_mode,
                    perks_enabled=resolved_perks_enabled,
                    card_preset_name=card_preset_name,
                    module_preset_name=module_preset_name,
                    perk_preset_name=perk_preset_name,
                    trace_mode=trace_mode,
                )
                cached = QEFamilyQueryResult(
                    binding=snapshot.binding,
                    stat_inputs=snapshot.stat_inputs,
                    family_id=family_id,
                    requested_surface_ids=normalized_requested,
                    response=response,
                    resolution_path='declared_timing_family_simulator_bridge',
                )
                self._family_query_cache[key] = cached
            return copy.deepcopy(cached)
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
        statbook = query_response_to_statbook(
            result.response,
            notes=notes,
            diagnostics=diagnostics,
        )
        publish_query_surfaces(statbook.rows)
        return statbook

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
        statbook = query_response_to_statbook(
            result.response,
            notes=notes,
            diagnostics=diagnostics,
        )
        publish_query_surfaces(statbook.rows)
        return statbook


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


def classify_input_routing(row: StatInput) -> str:
    """Sanctioned QE diagnostic helper surface for active non-QE consumers."""
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


def summarize_input_routing(stat_inputs: list[StatInput]) -> dict[str, object]:
    """Sanctioned QE diagnostic helper surface for active non-QE consumers."""
    from collections import Counter

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
    routing_summary = summarize_input_routing(list(bound_inputs.stat_inputs))
    diagnostics.setdefault('input_routing_class_counts', routing_summary['class_counts'])
    diagnostics.setdefault('mapped_input_count', routing_summary['routed_input_count'])
    diagnostics.setdefault('unmapped_input_count', routing_summary['truly_unrouted_input_count'])
    diagnostics.setdefault('mapped_count_by_family', routing_summary['routed_count_by_family'])
    diagnostics.setdefault(
        'input_count_by_family',
        dict(sorted(Counter(row.source_family for row in bound_inputs.stat_inputs).items())),
    )
    diagnostics.setdefault('unresolved_contributor_diagnostics', routing_summary['unresolved_contributor_diagnostics'])
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
    native_family_id = _infer_manifest_approved_family(bound_inputs.stat_inputs)
    fallback_reason: str | None = None
    fallback_error: str | None = None
    try:
        if native_family_id is None:
            fallback_reason = 'native_family_inference_unavailable'
            native_result = None
        else:
            native_result = _build_family_query_result(
                bound_inputs,
                family_id=native_family_id,
                requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[native_family_id],
                trace_mode='contributors',
            )
    except ValueError as exc:
        fallback_reason = 'native_contract_check_failed'
        fallback_error = str(exc)
        native_result = None
    if native_result is None:
        fallback_statbook = _fallback_resolve_stats(list(bound_inputs.stat_inputs))
        return _with_native_fallback_diagnostics(
            fallback_statbook,
            native_family_id=native_family_id,
            fallback_reason=fallback_reason or 'native_resolution_unavailable',
            fallback_error=fallback_error,
        )
    return query_response_to_statbook(
        native_result.response,
        notes=f'Native family statbook for manifest-approved family {native_family_id}.',
    )


def _resolve_hybrid_statbook_from_rows(
    *,
    stat_inputs: tuple[StatInput, ...],
    identity: StateIdentity,
) -> StatBook:
    native_family_id = _infer_manifest_approved_family(stat_inputs)
    fallback_reason: str | None = None
    fallback_error: str | None = None
    try:
        if native_family_id is None:
            fallback_reason = 'native_family_inference_unavailable'
            native_result = None
        else:
            native_result = _build_rows_family_query_result(
                identity=identity,
                stat_inputs=stat_inputs,
                family_id=native_family_id,
                requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[native_family_id],
                trace_mode='contributors',
            )
    except ValueError as exc:
        fallback_reason = 'native_contract_check_failed'
        fallback_error = str(exc)
        native_result = None
    if native_result is None:
        fallback_statbook = _fallback_resolve_stats(list(stat_inputs))
        return _with_native_fallback_diagnostics(
            fallback_statbook,
            native_family_id=native_family_id,
            fallback_reason=fallback_reason or 'native_resolution_unavailable',
            fallback_error=fallback_error,
        )
    return query_response_to_statbook(
        native_result.response,
        notes=f'Native family statbook for manifest-approved family {native_family_id}.',
    )


def _with_native_fallback_diagnostics(
    statbook: StatBook,
    *,
    native_family_id: str | None,
    fallback_reason: str,
    fallback_error: str | None = None,
) -> StatBook:
    diagnostics = dict(statbook.diagnostics or {})
    diagnostics['qe_native_family_fallback'] = {
        'reason': fallback_reason,
        'native_family_id': native_family_id,
    }
    if fallback_error:
        diagnostics['qe_native_family_fallback']['error'] = fallback_error
    return StatBook(rows=statbook.rows, diagnostics=diagnostics)


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
                'input_value_type': contributor.input_value_type,
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
    merged_diagnostics['dependency_trace'] = dict(response.dependency_trace or {})
    return StatBook(rows=rows, diagnostics=merged_diagnostics)


def resolve_checkpoint_surfaces(
    account_state: AccountState,
    *,
    requested_surface_ids: Sequence[str],
    preset_name: str,
    family_id: str | None = None,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool | None = None,
    runtime_branch_id: str = 'branch_checkpoint',
    scenario_runtime_inputs: ScenarioRuntimeInputs | None = None,
    scenario_projection_state: ScenarioProjectionState | None = None,
    trace_mode: str = 'contributors',
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    """
    Resolve an explicit checkpoint surface set for simulator/runtime consumers.

    This is the sanctioned lightweight QE seam for row/checkpoint execution.
    It compiles checkpoint-local stat inputs with identity, materializes only the
    requested checkpoint family, and resolves only the requested surfaces.
    """
    resolved_perks_enabled = bool(account_state.active_perk_preset) if perks_enabled is None else bool(perks_enabled)
    resolved_family_id = family_id or (
        _PROGRESSION_RUNTIME_WITH_PERKS if resolved_perks_enabled else _PROGRESSION_RUNTIME_NO_PERKS
    )
    bound_inputs = compile_stat_inputs_with_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=resolved_perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=scenario_projection_state,
        scenario_context={'mode_id': 'checkpoint'},
    )
    query_kernel = kernel or get_default_query_kernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        bound_inputs.binding.identity,
        resolved_family_id,
        bound_inputs.stat_inputs,
    )
    return query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=tuple(str(surface_id) for surface_id in requested_surface_ids),
        trace_mode=trace_mode,
    )


def _compile_checkpoint_bound_inputs(
    account_state: AccountState,
    *,
    preset_name: str,
    state_mode: str,
    card_preset_name: str | None,
    module_preset_name: str | None,
    perk_preset_name: str | None,
    perks_enabled: bool,
    runtime_branch_id: str,
    scenario_runtime_inputs: ScenarioRuntimeInputs | None,
    scenario_projection_state: ScenarioProjectionState | None,
) -> BoundStatInputs:
    return compile_stat_inputs_with_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=scenario_projection_state,
        scenario_context={'mode_id': 'checkpoint'},
    )


def resolve_checkpoint_consumer_bundle(
    account_state: AccountState,
    *,
    consumer_id: str,
    bundle_id: str,
    family_id: str,
    preset_name: str,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool = False,
    runtime_branch_id: str = 'branch_checkpoint',
    scenario_runtime_inputs: ScenarioRuntimeInputs | None = None,
    scenario_projection_state: ScenarioProjectionState | None = None,
    trace_mode: str = 'contributors',
    include_optional_surface_ids: Sequence[str] = (),
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    resolved_bundle = resolve_consumer_bundle(
        consumer_id,
        bundle_id,
        family_id=family_id,
        include_optional_surface_ids=include_optional_surface_ids,
        trace_mode=trace_mode,
    )
    bound_inputs = _compile_checkpoint_bound_inputs(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=scenario_projection_state,
    )
    query_kernel = kernel or get_default_query_kernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        bound_inputs.binding.identity,
        family_id,
        bound_inputs.stat_inputs,
    )
    return query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=resolved_bundle.surface_ids,
        trace_mode=trace_mode,
    )


def _contributor_row_from_statbook_dict(surface_id: str, contributor: dict[str, object]) -> BaselineContributorRow:
    return BaselineContributorRow(
        surface_id=surface_id,
        surface_class=str(contributor.get('surface_class') or ''),
        domain=str(contributor.get('domain') or ''),
        source_class=str(contributor.get('source_class') or ''),
        source_family=None,
        source_name=None,
        composition_stage=str(contributor.get('composition_stage') or ''),
        contributor_id=str(contributor.get('contributor_id') or ''),
        value=contributor.get('value'),
        value_type=str(contributor.get('value_type') or ''),
        input_value=contributor.get('value'),
        input_value_type=str(contributor.get('value_type') or ''),
        input_notes=None,
        active=bool(contributor.get('active', True)),
        gate_reason=None if contributor.get('gate_reason') is None else str(contributor.get('gate_reason')),
        provenance_ref=str(contributor.get('provenance_ref') or ''),
    )


def _delta_statbook_from_response(
    *,
    base_statbook: StatBook,
    response: QueryResponse,
    bundle_surface_ids: Sequence[str],
    impacted_surface_ids: Sequence[str],
    diagnostics: dict[str, object],
) -> StatBook:
    impacted_surface_set = set(impacted_surface_ids)
    response_surface_rows = {row.surface_id: row for row in response.resolved_surface_rows}
    response_contributors: dict[str, list[BaselineContributorRow]] = {}
    for contributor in response.contributor_rows:
        response_contributors.setdefault(contributor.surface_id, []).append(contributor)

    merged_rows = dict(base_statbook.rows)
    for surface_id in impacted_surface_ids:
        row = response_surface_rows.get(surface_id)
        if row is None:
            raise ValueError(f'Delta response omitted impacted surface {surface_id!r}.')
        impacted_statbook = query_response_to_statbook(
            QueryResponse(
                family_id=response.family_id,
                resolved_surface_rows=(row,),
                contributor_rows=tuple(response_contributors.get(surface_id, ())),
                dependency_trace={surface_id: dict(response.dependency_trace.get(surface_id, {}))},
            ),
            notes='Resolved through checkpoint consumer-bundle delta.',
            diagnostics=diagnostics,
        )
        merged_rows[surface_id] = impacted_statbook.rows[surface_id]

    contributor_rows: list[BaselineContributorRow] = []
    dependency_trace: dict[str, dict[str, object]] = {}
    resolved_surface_rows: list[ResolvedSurfaceRow] = []
    for surface_id in bundle_surface_ids:
        row = merged_rows.get(surface_id)
        if row is None:
            continue
        resolved_surface_rows.append(
            ResolvedSurfaceRow(
                surface_id=surface_id,
                final_value=row.final_value,
                value_type=row.value_type,
                status=row.status,
            )
        )
        if surface_id in impacted_surface_set:
            contributor_rows.extend(response_contributors.get(surface_id, ()))
            dependency_trace[surface_id] = dict(response.dependency_trace.get(surface_id, {}))
        else:
            contributor_rows.extend(
                _contributor_row_from_statbook_dict(surface_id, contributor)
                for contributor in (merged_rows[surface_id].contributors or ())
            )
            dependency_trace[surface_id] = dict(base_statbook.diagnostics.get('dependency_trace', {}).get(surface_id, {}))

    merged_response = QueryResponse(
        family_id=response.family_id,
        resolved_surface_rows=tuple(resolved_surface_rows),
        contributor_rows=tuple(contributor_rows),
        dependency_trace=dependency_trace,
    )
    return query_response_to_statbook(
        merged_response,
        notes='Resolved through checkpoint consumer-bundle delta.',
        diagnostics=diagnostics,
    )


@dataclass(frozen=True)
class QEOverlayMutationPlan:
    dirty_nodes: tuple[str, ...]
    fallback_required: bool
    fallback_reason: str | None = None


class QEOverlayMutationPlanner(Protocol):
    def __call__(
        self,
        *,
        family_id: str,
        mutation_class: str,
        trigger_keys: Sequence[str],
        consumer_id: str,
        bundle_id: str,
    ) -> QEOverlayMutationPlan: ...


def _plan_checkpoint_overlay_mutation(
    *,
    family_id: str,
    mutation_class: str,
    trigger_keys: Sequence[str],
    consumer_id: str,
    bundle_id: str,
) -> QEOverlayMutationPlan:
    registry = DependencyRegistry.load_default()
    mutated: list[str] = []
    missing: list[str] = []
    for trigger_key in trigger_keys:
        mapping = registry.mutation_mapping(mutation_class, str(trigger_key))
        if mapping is None:
            missing.append(str(trigger_key))
            continue
        mutated.append(mapping.source_node_id)
    if missing:
        return QEOverlayMutationPlan(
            dirty_nodes=(),
            fallback_required=True,
            fallback_reason=f'Unsupported mutation keys for {mutation_class}: {sorted(missing)}',
        )
    return QEOverlayMutationPlan(
        dirty_nodes=tuple(sorted(registry.closure_downstream(mutated))),
        fallback_required=False,
    )


def resolve_checkpoint_consumer_bundle_delta(
    *,
    base_statbook: StatBook,
    account_state: AccountState,
    consumer_id: str,
    bundle_id: str,
    family_id: str,
    preset_name: str,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool = False,
    runtime_branch_id: str = 'branch_checkpoint',
    scenario_runtime_inputs: ScenarioRuntimeInputs | None = None,
    scenario_projection_state: ScenarioProjectionState | None = None,
    trace_mode: str = 'contributors',
    include_optional_surface_ids: Sequence[str] = (),
    mutation_class: str = 'workshop_mutation',
    trigger_keys: Sequence[str] = (),
    kernel: StatQueryKernel | None = None,
    overlay_mutation_planner: QEOverlayMutationPlanner | None = None,
) -> StatBook:
    resolved_bundle = resolve_consumer_bundle(
        consumer_id,
        bundle_id,
        family_id=family_id,
        include_optional_surface_ids=include_optional_surface_ids,
        trace_mode=trace_mode,
    )
    mutation_plan = _plan_checkpoint_overlay_mutation if overlay_mutation_planner is None else overlay_mutation_planner
    plan = mutation_plan(
        family_id=family_id,
        mutation_class=mutation_class,
        trigger_keys=trigger_keys,
        consumer_id=consumer_id,
        bundle_id=bundle_id,
    )
    impacted_surface_ids = sorted(set(plan.dirty_nodes) & set(resolved_bundle.surface_ids))
    diagnostics = dict(base_statbook.diagnostics or {})
    diagnostics.update({
        'family_id': family_id,
        'qe_resolution_interface': 'checkpoint_consumer_bundle_delta',
        'qe_resolution_backend': 'native_family_query_delta',
        'qe_native_family_available': True,
        'qe_native_family_id': family_id,
        'consumer_id': consumer_id,
        'bundle_id': bundle_id,
        'delta_mutation_class': mutation_class,
        'delta_trigger_keys': list(trigger_keys),
        'delta_fallback_used': False,
        'delta_impacted_surface_ids': impacted_surface_ids,
    })
    if plan.fallback_required or not impacted_surface_ids:
        diagnostics['delta_fallback_used'] = True
        diagnostics['delta_fallback_reason'] = plan.fallback_reason or ('No impacted bundle surfaces for trigger keys.' if not impacted_surface_ids else 'unsupported_delta_plan')
        response = resolve_checkpoint_consumer_bundle(
            account_state,
            consumer_id=consumer_id,
            bundle_id=bundle_id,
            family_id=family_id,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            runtime_branch_id=runtime_branch_id,
            scenario_runtime_inputs=scenario_runtime_inputs,
            scenario_projection_state=scenario_projection_state,
            trace_mode=trace_mode,
            include_optional_surface_ids=include_optional_surface_ids,
            kernel=kernel,
        )
        return query_response_to_statbook(response, notes='Resolved through checkpoint consumer-bundle full fallback.', diagnostics=diagnostics)

    bound_inputs = _compile_checkpoint_bound_inputs(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=scenario_projection_state,
    )
    query_kernel = kernel or get_default_query_kernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        bound_inputs.binding.identity,
        family_id,
        bound_inputs.stat_inputs,
    )
    response = query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=tuple(impacted_surface_ids),
        trace_mode=trace_mode,
    )
    return _delta_statbook_from_response(
        base_statbook=base_statbook,
        response=response,
        bundle_surface_ids=resolved_bundle.surface_ids,
        impacted_surface_ids=impacted_surface_ids,
        diagnostics=diagnostics,
    )


def _snapshot_cache_key(bound_inputs: BoundStatInputs) -> tuple[str, str, str, str]:
    identity = bound_inputs.binding.identity
    return (
        identity.account_snapshot_id,
        identity.loadout_id,
        identity.scenario_id,
        identity.runtime_branch_id,
    )


def resolve_stats_delta(
    *,
    base_statbook: StatBook,
    base_stat_inputs: list[StatInput],
    target_stat_inputs: list[StatInput],
) -> StatBook:
    base_family_id = _infer_manifest_approved_family(base_stat_inputs)
    target_family_id = _infer_manifest_approved_family(target_stat_inputs)
    if base_family_id is not None and base_family_id == target_family_id:
        response = _resolve_manifest_approved_family(
            family_id=target_family_id,
            stat_inputs=target_stat_inputs,
        )
        merged = _merge_delegated_family_rows(
            fallback_statbook=base_statbook,
            delegated_response=response,
            family_id=target_family_id,
        )
        diagnostics = dict(merged.diagnostics or {})
        diagnostics['delta_resolution'] = {
            'path': 'native_family_query_delta_no_compat_fallback',
            'family_id': target_family_id,
        }
        return StatBook(rows=merged.rows, diagnostics=diagnostics)

    return _fallback_resolve_stats_delta(
        base_statbook,
        base_stat_inputs=base_stat_inputs,
        target_stat_inputs=target_stat_inputs,
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
                    'input_value_type': contributor.input_value_type,
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
    'resolve_checkpoint_surfaces',
    'resolve_checkpoint_consumer_bundle',
    'resolve_checkpoint_consumer_bundle_delta',
    'resolve_stats',
    'resolve_stats_delta',
    '_multiplier_from_value',
    '_canonical_source_multiplier',
]
