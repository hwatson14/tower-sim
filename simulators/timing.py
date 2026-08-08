from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field, replace
from fractions import Fraction
from math import gcd
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from qe.contracts import normalize_surface_id_to_contract
from qe.materializer import FamilyBaselineContributorMap, FamilyBaselineMaterializer
from qe.consumer_registry import resolve_consumer_bundle
from simulators.scenario import (
    ScenarioConfig,
    ScenarioSurfaces,
    compute_scenario_surfaces,
    non_boss_pressure_driver_probe,
    normal_spawn_rate_pressure_driver,
    publish_farming_throughput_support_surfaces,
)
from qe.models import BoundStatInputs, compile_stat_inputs_with_identity
from qe.kernel import QueryResponse, StatQueryKernel, get_default_query_kernel
from qe.routing import QEResolutionPlanner
from input.state_types import AccountState
from qe.models import StatInput

ROOT = Path(__file__).resolve().parents[1]
ORB_BOSS_HIT_LEVELS_TABLE = ROOT / "kb" / "global-rules" / "tables" / "note-derived-orb-boss-hit-levels-1-10.csv"
WAVE_TIMING_BASELINES_TABLE = ROOT / "kb" / "global-rules" / "tables" / "wave-timing-baselines.csv"
BOSS_CONTACT_REFERENCE_TOWER_RANGE_M = 69.5
BOSS_CONTACT_WALL_RADIUS_M = 20.0
FLAME_BOT_HIT_INTEGRATION_STEPS = 64
FLAME_BOT_HIT_TIMING_SAMPLE_CAP = 64


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _mech(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'mechanic_param::{destination_id}')


def _runtime(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f'runtime_mechanic_param::{destination_id}')


def _uptime(duration: float, cooldown: float) -> float:
    """uptime = duration / (duration + cooldown), clamped [0, 1]."""
    total = max(0.0, duration) + max(0.0, cooldown)
    if total <= 0.0:
        return 0.0
    return min(1.0, max(0.0, duration) / total)


def bounded_fraction(value: object) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, raw))


def bounded_percent_fraction(value: object) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if raw <= 0.0:
        return 0.0
    return min(100.0, raw) / 100.0


def positive_percent_fraction(value: object) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if raw <= 0.0:
        return 0.0
    return raw / 100.0


def positive_factor(value: object, *, default: float = 1.0) -> float:
    try:
        factor = float(value or 0.0)
    except (TypeError, ValueError):
        return default
    return factor if factor > 0.0 else default


def _finite_nonnegative_or_none(value: object) -> float | None:
    if value in (None, ''):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
        return None
    return parsed


def duration_over_cooldown_uptime_fraction(duration_seconds: object, cooldown_seconds: object) -> float:
    duration = max(0.0, float(duration_seconds or 0.0))
    cooldown = max(0.0, float(cooldown_seconds or 0.0))
    if duration <= 0.0 or cooldown <= 0.0:
        return 0.0
    return min(1.0, duration / cooldown)


def timed_effect_lane_fractions(
    *,
    effect_fraction: object,
    duration_seconds: object = 0.0,
    cooldown_seconds: object = 0.0,
    explicit_uptime_fraction: object | None = None,
) -> dict[str, float]:
    effect = bounded_fraction(effect_fraction)
    if explicit_uptime_fraction is None:
        uptime = duration_over_cooldown_uptime_fraction(duration_seconds, cooldown_seconds)
    else:
        uptime = bounded_fraction(explicit_uptime_fraction)
    if effect <= 0.0 or uptime <= 0.0:
        return {"min": 0.0, "avg": 0.0, "max": 0.0}
    if uptime >= 1.0:
        return {"min": effect, "avg": effect, "max": effect}
    return {"min": 0.0, "avg": bounded_fraction(effect * uptime), "max": effect}


def timed_dr_source_by_lane(
    source: Mapping[str, object],
    *,
    binary_avg_hit_threshold: float,
) -> dict[str, float]:
    dr_fraction = bounded_percent_fraction(source.get('damage_reduction_pct'))
    uptime_fraction = bounded_fraction(source.get('uptime_fraction'))
    if bool(source.get('binary_outcome')):
        hit_dr = dr_fraction if uptime_fraction > 0.0 else 0.0
        avg_dr = hit_dr if uptime_fraction >= binary_avg_hit_threshold else 0.0
        return {'min': 0.0, 'avg': avg_dr, 'max': hit_dr}
    if uptime_fraction >= 1.0:
        return {'min': dr_fraction, 'avg': dr_fraction, 'max': dr_fraction}
    return {'min': 0.0, 'avg': dr_fraction * uptime_fraction, 'max': dr_fraction}


def timed_dr_source(
    *,
    damage_reduction_pct: object,
    duration_seconds: object | None,
    cooldown_seconds: object | None,
    explicit_uptime_fraction: object | None = None,
    explicit_uptime_source: str = 'explicit_uptime_fraction',
    primitive_status: str = 'runtime_primitives',
    binary_outcome: bool = False,
    binary_avg_hit_threshold: float = 1.0,
) -> dict[str, float | str | bool]:
    dr_fraction = bounded_percent_fraction(damage_reduction_pct)
    try:
        reported_dr_pct = float(damage_reduction_pct or 0.0)
    except (TypeError, ValueError):
        reported_dr_pct = 0.0
    if explicit_uptime_fraction is not None:
        uptime = bounded_fraction(explicit_uptime_fraction)
        source = str(explicit_uptime_source)
    elif duration_seconds is None or cooldown_seconds is None:
        uptime = 0.0
        source = 'not_provided'
    else:
        try:
            cooldown = float(cooldown_seconds or 0.0)
        except (TypeError, ValueError):
            cooldown = 0.0
        if cooldown <= 0.0:
            uptime = 0.0
            source = 'not_provided'
        else:
            uptime = duration_over_cooldown_uptime_fraction(duration_seconds, cooldown_seconds)
            source = 'duration_over_cooldown'
    probability_weighted_dr = dr_fraction * uptime
    return {
        'damage_reduction_pct': reported_dr_pct,
        'duration_seconds': float(duration_seconds or 0.0),
        'cooldown_seconds': float(cooldown_seconds or 0.0),
        'uptime_fraction': uptime,
        'uptime_source': source,
        'effective_dr_fraction': probability_weighted_dr,
        'probability_weighted_dr_fraction': probability_weighted_dr,
        'binary_outcome': bool(binary_outcome),
        'encounter_hit_chance_fraction': uptime if binary_outcome else 0.0,
        'deterministic_hit_dr_fraction': (
            dr_fraction
            if binary_outcome and uptime >= float(binary_avg_hit_threshold)
            else 0.0
        ),
        'binary_avg_hit_threshold': (
            float(binary_avg_hit_threshold)
            if binary_outcome
            else 0.0
        ),
        'lane_policy': (
            'binary_outcome_min_miss_avg_near_certain_hit_max_hit_probability_reported_separately'
            if binary_outcome
            else 'timed_uptime_min_miss_avg_probability_weighted_max_full'
        ),
        'primitive_status': str(primitive_status),
    }


def timed_dr_lanes_from_sources(
    sources: Mapping[str, Mapping[str, object]],
    *,
    binary_avg_hit_threshold: float,
    excluded_source_names: Iterable[str] = (),
) -> dict[str, float]:
    excluded = {str(name) for name in excluded_source_names}
    lane_products = {'min': 1.0, 'avg': 1.0, 'max': 1.0}
    for source_name, source in sources.items():
        if str(source_name) in excluded:
            continue
        lane_dr = timed_dr_source_by_lane(
            dict(source),
            binary_avg_hit_threshold=binary_avg_hit_threshold,
        )
        for lane_id, lane_fraction in lane_dr.items():
            lane_products[lane_id] *= 1.0 - float(lane_fraction)
    return {
        lane_id: max(0.0, min(1.0, 1.0 - product))
        for lane_id, product in lane_products.items()
    }


def boss_contact_time_seconds(
    *,
    explicit_contact_time_seconds: object | None = None,
    chrono_field_duration_seconds: object = 0.0,
    chrono_field_cooldown_seconds: object = 0.0,
    chrono_field_slow_pct: object = 0.0,
    slow_aura_enemy_speed_pct: object = 0.0,
    enemy_speed_increase_pct: object = 0.0,
    boss_speed_multiplier: object = 1.0,
    energy_net_duration_seconds: object = 0.0,
    geometry_base_contact_time_seconds: object | None = None,
    geometry_base_components: Mapping[str, object] | None = None,
    base_seconds: float = 2.0,
) -> tuple[float, str, dict[str, object]]:
    geometry_components = dict(geometry_base_components or {})
    if explicit_contact_time_seconds is not None:
        contact_time = max(0.0, float(explicit_contact_time_seconds))
        return (
            contact_time,
            'runtime_input_boss_time_to_contact_seconds',
            {
                'base_seconds': float(base_seconds),
                'base_seconds_source': 'runtime_input_override_contact_time',
                'chrono_field_average_slow_fraction': 0.0,
                'slow_aura_fraction': 0.0,
                'enemy_speed_increase_fraction': 0.0,
                'boss_speed_multiplier': 1.0,
                'movement_speed_multiplier': 1.0,
                'speed_remaining_fraction': 1.0,
                'energy_net_hold_seconds': 0.0,
                'geometry_base_seconds': _finite_nonnegative_or_none(geometry_base_contact_time_seconds),
                'geometry_base_status': str(geometry_components.get('status') or 'not_used_runtime_override'),
                'geometry_proxy_truth_status': str(
                    geometry_components.get('truth_status') or 'not_used_runtime_override'
                ),
            },
        )
    resolved_base_seconds = float(base_seconds)
    base_seconds_source = 'constant_2s_reference'
    source = 'derived_base_2s_cf_slow_aura_energy_net'
    geometry_base = _finite_nonnegative_or_none(geometry_base_contact_time_seconds)
    geometry_base_status = str(geometry_components.get('status') or 'not_supplied')
    geometry_proxy_truth_status = str(geometry_components.get('truth_status') or 'not_supplied')
    if geometry_base is not None:
        resolved_base_seconds = geometry_base
        base_seconds_source = 'geometry_displayed_proxy_candidate'
        source = 'derived_geometry_displayed_proxy_base_cf_slow_aura_energy_net'
        if geometry_base_status == 'not_supplied':
            geometry_base_status = 'resolved_displayed_proxy_candidate'
    cf_uptime = duration_over_cooldown_uptime_fraction(
        chrono_field_duration_seconds,
        chrono_field_cooldown_seconds,
    )
    cf_average_slow = bounded_percent_fraction(chrono_field_slow_pct) * cf_uptime
    slow_aura = bounded_percent_fraction(slow_aura_enemy_speed_pct)
    enemy_speed_increase = positive_percent_fraction(enemy_speed_increase_pct)
    boss_speed = positive_factor(boss_speed_multiplier, default=1.0)
    movement_speed_multiplier = boss_speed * (1.0 + enemy_speed_increase)
    speed_remaining = max(
        0.01,
        (1.0 - cf_average_slow) * (1.0 - slow_aura) * movement_speed_multiplier,
    )
    energy_net_hold = max(0.0, float(energy_net_duration_seconds or 0.0))
    contact_time = (resolved_base_seconds / speed_remaining) + energy_net_hold
    if not math.isclose(movement_speed_multiplier, 1.0):
        source = source.replace('_slow_aura_energy_net', '_slow_aura_enemy_speed_energy_net')
    return (
        contact_time,
        source,
        {
            'base_seconds': resolved_base_seconds,
            'base_seconds_source': base_seconds_source,
            'chrono_field_average_slow_fraction': cf_average_slow,
            'slow_aura_fraction': slow_aura,
            'enemy_speed_increase_fraction': enemy_speed_increase,
            'boss_speed_multiplier': boss_speed,
            'movement_speed_multiplier': movement_speed_multiplier,
            'speed_remaining_fraction': speed_remaining,
            'energy_net_hold_seconds': energy_net_hold,
            'geometry_base_seconds': geometry_base,
            'geometry_base_status': geometry_base_status,
            'geometry_proxy_truth_status': geometry_proxy_truth_status,
            'geometry_tower_range_theoretical_m': geometry_components.get('tower_range_theoretical_m'),
            'geometry_tower_range_displayed_m': geometry_components.get('tower_range_displayed_m'),
            'geometry_wall_radius_displayed_m': geometry_components.get('wall_radius_displayed_m'),
            'geometry_path_distance_to_wall_displayed_candidate_m': geometry_components.get(
                'boss_path_distance_to_wall_displayed_candidate_m'
            ),
            'geometry_reference_path_distance_to_wall_displayed_m': geometry_components.get(
                'reference_path_distance_to_wall_displayed_m'
            ),
        },
    )


def boss_hit_interval_seconds(
    *,
    explicit_hit_interval_seconds: object | None = None,
    scenario_base_seconds: object = 2.0,
    slow_aura_mastery_attack_interval_multiplier: object = 1.0,
) -> tuple[float, str, dict[str, float]]:
    scenario_base = max(0.0, float(scenario_base_seconds or 2.0))
    if explicit_hit_interval_seconds is not None:
        return (
            max(0.0, float(explicit_hit_interval_seconds)),
            'runtime_input_boss_hit_interval_seconds',
            {
                'scenario_base_seconds': scenario_base,
                'slow_aura_mastery_attack_interval_multiplier': 1.0,
            },
        )
    slow_aura_mastery_multiplier = positive_factor(
        slow_aura_mastery_attack_interval_multiplier,
        default=1.0,
    )
    return (
        scenario_base * slow_aura_mastery_multiplier,
        'scenario_boss_hit_interval_plus_slow_aura_mastery',
        {
            'scenario_base_seconds': scenario_base,
            'slow_aura_mastery_attack_interval_multiplier': slow_aura_mastery_multiplier,
        },
    )


def energy_net_mastery_damage_window_seconds(
    *,
    energy_net_duration_seconds: object,
    energy_net_mastery_multiplier: object,
) -> float:
    duration = max(0.0, float(energy_net_duration_seconds or 0.0))
    mastery_multiplier = positive_factor(energy_net_mastery_multiplier)
    return duration + 10.0 if duration > 0.0 and mastery_multiplier > 1.0 else 0.0


def shockwave_active_fraction(
    *,
    contact_time_seconds: object,
    shockwave_interval_seconds: object,
    effect_duration_seconds: float = 7.0,
) -> tuple[float, float]:
    try:
        contact_time = max(0.0, float(contact_time_seconds or 0.0))
        shockwave_interval = max(0.0, float(shockwave_interval_seconds or 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0
    if contact_time <= 0.0 or shockwave_interval <= 0.0:
        return 0.0, 0.0
    hit_probability = min(1.0, contact_time / shockwave_interval)
    active_fraction = min(1.0, hit_probability * min(1.0, float(effect_duration_seconds) / contact_time))
    return hit_probability, active_fraction


def circle_overlap_area(radius_a: float, radius_b: float, center_distance: float) -> float:
    a = max(0.0, float(radius_a))
    b = max(0.0, float(radius_b))
    d = max(0.0, float(center_distance))
    if a <= 0.0 or b <= 0.0:
        return 0.0
    if d >= a + b:
        return 0.0
    if d <= abs(a - b):
        return math.pi * min(a, b) ** 2
    a_sq = a * a
    b_sq = b * b
    d_sq = d * d
    a_term = (d_sq + a_sq - b_sq) / (2.0 * d * a)
    b_term = (d_sq + b_sq - a_sq) / (2.0 * d * b)
    a_angle = math.acos(max(-1.0, min(1.0, a_term)))
    b_angle = math.acos(max(-1.0, min(1.0, b_term)))
    triangle = 0.5 * math.sqrt(
        max(0.0, (-d + a + b) * (d + a - b) * (d - a + b) * (d + a + b))
    )
    return (a_sq * a_angle) + (b_sq * b_angle) - triangle


def flame_bot_static_boss_hit_chance(
    *,
    tower_range_m: object,
    flame_bot_effective_range_m: object,
    flame_bot_cooldown_seconds: object,
    boss_time_to_contact_seconds: object,
    energy_net_hold_seconds: object,
    boss_lifetime_seconds: object | None = None,
    reference_tower_range_m: float = BOSS_CONTACT_REFERENCE_TOWER_RANGE_M,
    wall_radius_m: float = BOSS_CONTACT_WALL_RADIUS_M,
    integration_steps: int = FLAME_BOT_HIT_INTEGRATION_STEPS,
) -> tuple[float, dict[str, object]]:
    try:
        actual_tower_range = max(0.0, float(tower_range_m or 0.0))
        effective_range = max(0.0, float(flame_bot_effective_range_m or 0.0))
        cooldown = max(0.0, float(flame_bot_cooldown_seconds or 0.0))
        contact_time = max(0.0, float(boss_time_to_contact_seconds or 0.0))
        net_hold = max(0.0, float(energy_net_hold_seconds or 0.0))
        has_explicit_lifetime = boss_lifetime_seconds not in (None, '')
        lifetime = (
            max(0.0, float(boss_lifetime_seconds or 0.0))
            if has_explicit_lifetime
            else contact_time
        )
    except (TypeError, ValueError):
        return 0.0, {'status': 'blocked_invalid_numeric_input'}
    if actual_tower_range <= 0.0 or effective_range <= 0.0 or cooldown <= 0.0 or contact_time <= 0.0:
        return 0.0, {
            'status': 'blocked_missing_static_hit_primitives',
            'tower_range_m': actual_tower_range,
            'flame_bot_effective_range_m': effective_range,
            'flame_bot_cooldown_seconds': cooldown,
            'boss_time_to_contact_seconds': contact_time,
        }

    normalized_bot_radius = effective_range * (float(reference_tower_range_m) / actual_tower_range)
    tower_area = math.pi * float(reference_tower_range_m) * float(reference_tower_range_m)

    def spatial_fraction_at_radius(boss_radius: float) -> float:
        overlap = circle_overlap_area(float(reference_tower_range_m), normalized_bot_radius, boss_radius)
        return max(0.0, min(1.0, overlap / tower_area)) if tower_area > 0.0 else 0.0

    movement_path_seconds = max(0.0, contact_time - min(net_hold, contact_time))
    movement_seconds = min(lifetime, movement_path_seconds)
    remaining_lifetime = max(0.0, lifetime - movement_seconds)
    hold_seconds = min(remaining_lifetime, max(0.0, min(net_hold, contact_time)))
    post_contact_seconds = max(0.0, remaining_lifetime - hold_seconds)
    total_exposure_seconds = movement_seconds + hold_seconds + post_contact_seconds
    steps = max(1, int(integration_steps))
    movement_spatial = 0.0
    if movement_seconds > 0.0:
        movement_total = 0.0
        integrated_path_fraction = (
            max(0.0, min(1.0, movement_seconds / movement_path_seconds))
            if movement_path_seconds > 0.0
            else 0.0
        )
        for index in range(steps):
            fraction = ((index + 0.5) / steps) * integrated_path_fraction
            boss_radius = float(reference_tower_range_m) - (
                (float(reference_tower_range_m) - float(wall_radius_m)) * fraction
            )
            movement_total += spatial_fraction_at_radius(boss_radius)
        movement_spatial = movement_total / steps
    wall_spatial = spatial_fraction_at_radius(float(wall_radius_m))
    hold_spatial = wall_spatial if hold_seconds > 0.0 else 0.0
    post_contact_spatial = wall_spatial if post_contact_seconds > 0.0 else 0.0
    spatial_fraction = (
        (
            (movement_spatial * movement_seconds)
            + (hold_spatial * hold_seconds)
            + (post_contact_spatial * post_contact_seconds)
        )
        / total_exposure_seconds
        if total_exposure_seconds > 0.0
        else 0.0
    )

    activation_windows = total_exposure_seconds / cooldown
    guaranteed_activations = int(math.floor(activation_windows))
    partial_activation_fraction = activation_windows - guaranteed_activations
    miss_fraction = (1.0 - spatial_fraction) ** guaranteed_activations
    miss_fraction *= 1.0 - (spatial_fraction * partial_activation_fraction)
    hit_fraction = max(0.0, min(1.0, 1.0 - miss_fraction))
    return hit_fraction, {
        'status': 'resolved',
        'model': 'static_uniform_flame_bot_center_vs_boss_path',
        'tower_range_reference_m': float(reference_tower_range_m),
        'wall_radius_m': float(wall_radius_m),
        'tower_range_m': actual_tower_range,
        'flame_bot_effective_range_m': effective_range,
        'normalized_flame_bot_radius_m': normalized_bot_radius,
        'flame_bot_cooldown_seconds': cooldown,
        'boss_time_to_contact_seconds': contact_time,
        'boss_lifetime_seconds': lifetime,
        'boss_lifetime_source': (
            'explicit_boss_lifetime_seconds'
            if has_explicit_lifetime
            else 'boss_time_to_contact_seconds_fallback'
        ),
        'energy_net_hold_seconds': hold_seconds,
        'movement_path_seconds': movement_path_seconds,
        'movement_seconds': movement_seconds,
        'movement_spatial_fraction': movement_spatial,
        'energy_net_hold_spatial_fraction': hold_spatial,
        'post_contact_seconds': post_contact_seconds,
        'post_contact_spatial_fraction': post_contact_spatial,
        'total_exposure_seconds': total_exposure_seconds,
        'average_spatial_fraction': spatial_fraction,
        'activation_windows': activation_windows,
        'guaranteed_activations': guaranteed_activations,
        'partial_activation_fraction': partial_activation_fraction,
        'hit_fraction': hit_fraction,
        'hit_chance_pct': hit_fraction * 100.0,
        'hit_state_semantics': 'persistent_until_boss_death_after_first_flame_bot_hit',
    }


def flame_bot_hit_timing_weighted_boss_hit_chance(
    *,
    tower_range_m: object,
    flame_bot_effective_range_m: object,
    flame_bot_cooldown_seconds: object,
    boss_time_to_contact_seconds: object,
    energy_net_hold_seconds: object,
    boss_lifetime_seconds: object,
    boss_hits_to_player: object,
    boss_hit_interval_seconds: object,
    contact_window_hit_fraction: object,
    boss_heat_up_damage_per_hit_pct: object,
    sample_cap: int = FLAME_BOT_HIT_TIMING_SAMPLE_CAP,
) -> tuple[float, dict[str, object]]:
    lifetime_hit_chance, lifetime_components = flame_bot_static_boss_hit_chance(
        tower_range_m=tower_range_m,
        flame_bot_effective_range_m=flame_bot_effective_range_m,
        flame_bot_cooldown_seconds=flame_bot_cooldown_seconds,
        boss_time_to_contact_seconds=boss_time_to_contact_seconds,
        energy_net_hold_seconds=energy_net_hold_seconds,
        boss_lifetime_seconds=boss_lifetime_seconds,
    )
    if lifetime_components.get('status') != 'resolved':
        return 0.0, lifetime_components
    try:
        hit_count = max(0, int(boss_hits_to_player or 0))
        contact_time = max(0.0, float(boss_time_to_contact_seconds or 0.0))
        hit_interval = max(0.0, float(boss_hit_interval_seconds or 0.0))
        heat_pct = max(0.0, float(boss_heat_up_damage_per_hit_pct or 0.0))
    except (TypeError, ValueError):
        return 0.0, {'status': 'blocked_invalid_numeric_input'}
    contact_hit_chance = bounded_fraction(contact_window_hit_fraction)
    hit_weighted_chance = contact_hit_chance
    sample_count = 0
    if hit_count > 0 and contact_time > 0.0:
        sample_count = min(hit_count, max(1, int(sample_cap)))
        weighted_hit_chance_total = 0.0
        hit_weight_total = 0.0
        for sample_index in range(sample_count):
            block_start = int(math.floor(sample_index * hit_count / sample_count))
            block_end = int(math.floor((sample_index + 1) * hit_count / sample_count))
            block_end = max(block_start + 1, block_end)
            block_midpoint = (block_start + block_end - 1) / 2.0
            block_weight = 0.0
            for hit_index in range(block_start, block_end):
                block_weight += 1.0 + heat_pct * hit_index
            hit_time = contact_time + (block_midpoint * hit_interval)
            hit_chance, hit_components = flame_bot_static_boss_hit_chance(
                tower_range_m=tower_range_m,
                flame_bot_effective_range_m=flame_bot_effective_range_m,
                flame_bot_cooldown_seconds=flame_bot_cooldown_seconds,
                boss_time_to_contact_seconds=boss_time_to_contact_seconds,
                energy_net_hold_seconds=energy_net_hold_seconds,
                boss_lifetime_seconds=hit_time,
            )
            if hit_components.get('status') != 'resolved':
                continue
            weighted_hit_chance_total += block_weight * hit_chance
            hit_weight_total += block_weight
        if hit_weight_total > 0.0:
            hit_weighted_chance = max(0.0, min(1.0, weighted_hit_chance_total / hit_weight_total))
    lifetime_components['contact_window_hit_fraction'] = contact_hit_chance
    lifetime_components['lifetime_hit_fraction'] = lifetime_hit_chance
    lifetime_components['hit_timing_weighted_hit_fraction'] = hit_weighted_chance
    lifetime_components['hit_timing_weighted_hit_chance_pct'] = hit_weighted_chance * 100.0
    lifetime_components['hit_timing_sample_count'] = sample_count
    lifetime_components['boss_hits_to_player'] = hit_count
    lifetime_components['boss_hit_interval_seconds'] = hit_interval
    lifetime_components['damage_weight_source'] = 'boss_heat_up_damage_per_hit'
    lifetime_components['hit_timing_semantics'] = (
        'flame_bot_dr_counts_only_for_modeled_boss_hits_after_the_first_successful_tag'
    )
    return hit_weighted_chance, lifetime_components


def time_limited_multiplier_boosted_seconds(
    *,
    start_seconds: object,
    end_seconds: object,
    multiplier_duration_seconds: object,
) -> float:
    start = max(0.0, float(start_seconds or 0.0))
    end = max(start, float(end_seconds or 0.0))
    multiplier_until = max(0.0, float(multiplier_duration_seconds or 0.0))
    boosted_end = min(end, max(start, multiplier_until))
    return max(0.0, boosted_end - start)


def time_limited_multiplier_damage(
    *,
    start_seconds: object,
    end_seconds: object,
    damage_per_second: object,
    multiplier: object,
    multiplier_duration_seconds: object,
) -> float:
    start = max(0.0, float(start_seconds or 0.0))
    end = max(start, float(end_seconds or 0.0))
    dps = max(0.0, float(damage_per_second or 0.0))
    if dps <= 0.0 or end <= start:
        return 0.0
    effect_multiplier = max(1.0, float(multiplier or 1.0))
    boosted_seconds = time_limited_multiplier_boosted_seconds(
        start_seconds=start,
        end_seconds=end,
        multiplier_duration_seconds=multiplier_duration_seconds,
    )
    base_seconds = max(0.0, end - start - boosted_seconds)
    return dps * ((boosted_seconds * effect_multiplier) + base_seconds)


def time_limited_multiplier_kill_seconds(
    *,
    start_seconds: object,
    end_seconds: object,
    hp_to_kill: object,
    damage_per_second: object,
    multiplier: object,
    multiplier_duration_seconds: object,
) -> float | None:
    remaining = max(0.0, float(hp_to_kill or 0.0))
    if remaining <= 0.0:
        return max(0.0, float(start_seconds or 0.0))
    start = max(0.0, float(start_seconds or 0.0))
    end = max(start, float(end_seconds or 0.0))
    dps = max(0.0, float(damage_per_second or 0.0))
    if dps <= 0.0 or end <= start:
        return None
    effect_multiplier = max(1.0, float(multiplier or 1.0))
    boosted_seconds = time_limited_multiplier_boosted_seconds(
        start_seconds=start,
        end_seconds=end,
        multiplier_duration_seconds=multiplier_duration_seconds,
    )
    boosted_rate = dps * effect_multiplier
    if boosted_rate > 0.0 and boosted_seconds > 0.0:
        boosted_capacity = boosted_rate * boosted_seconds
        if remaining <= boosted_capacity:
            return start + (remaining / boosted_rate)
        remaining -= boosted_capacity
    base_seconds = max(0.0, end - start - boosted_seconds)
    if dps > 0.0 and base_seconds > 0.0 and remaining <= dps * base_seconds:
        return start + boosted_seconds + (remaining / dps)
    return None


def boss_pre_contact_damage_window(
    *,
    damage_per_second: object,
    contact_seconds: object,
    base_contact_seconds: object,
    energy_net_hold_seconds: object,
    energy_net_mastery_multiplier: object,
    energy_net_damage_multiplier_duration_seconds: object,
) -> dict[str, float]:
    dps = max(0.0, float(damage_per_second or 0.0))
    contact = max(0.0, float(contact_seconds or 0.0))
    base_contact = max(0.0, float(base_contact_seconds or 0.0))
    net_hold = max(0.0, float(energy_net_hold_seconds or 0.0))
    movement_seconds = max(0.0, contact - net_hold)
    mastery_multiplier = positive_factor(energy_net_mastery_multiplier)
    mastery_window = max(0.0, float(energy_net_damage_multiplier_duration_seconds or 0.0))
    boosted_seconds = min(contact, mastery_window) if mastery_multiplier > 1.0 else 0.0
    base_window_damage = dps * contact
    energy_net_incremental_damage = dps * max(0.0, mastery_multiplier - 1.0) * boosted_seconds
    return {
        'contact_time_exposure_factor': contact / base_contact if base_contact > 0.0 else 1.0,
        'movement_time_exposure_factor': movement_seconds / base_contact if base_contact > 0.0 else 1.0,
        'base_window_damage': base_window_damage,
        'energy_net_boosted_seconds': boosted_seconds,
        'energy_net_incremental_damage': energy_net_incremental_damage,
        'timed_window_damage': base_window_damage + energy_net_incremental_damage,
    }


def _lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return max(a, b)
    return abs(a * b) // gcd(a, b)


def _fraction_from_float(value: float) -> Fraction:
    return Fraction(str(float(value))).limit_denominator(1000000)


@lru_cache(maxsize=1)
def _load_wave_timing_baseline_components() -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    with WAVE_TIMING_BASELINES_TABLE.open(newline='') as fh:
        for row in csv.DictReader(fh):
            mode_id = str(row.get('mode_id') or '').strip()
            if not mode_id:
                continue
            try:
                spawn_seconds = float(row['spawn_phase_seconds'])
                cooldown_seconds = float(row['cooldown_phase_seconds'])
                total_seconds = float(row['total_wave_duration_seconds'])
            except (TypeError, ValueError, KeyError):
                raise ValueError(f'Invalid wave timing baseline row in {WAVE_TIMING_BASELINES_TABLE}: {row!r}.')
            out[mode_id] = {
                'spawn_phase_seconds': spawn_seconds,
                'cooldown_phase_seconds': cooldown_seconds,
                'total_wave_duration_seconds': total_seconds,
            }
    if 'farming' not in out or 'tournament' not in out:
        raise ValueError(f'{WAVE_TIMING_BASELINES_TABLE} must define farming and tournament base wave durations.')
    return out


def _load_wave_timing_baselines() -> Dict[str, float]:
    return {
        mode_id: float(row['total_wave_duration_seconds'])
        for mode_id, row in _load_wave_timing_baseline_components().items()
    }


def wave_duration_seconds_after_cooldown_reduction(mode_id: str, wave_cooldown_reduction_pct: float) -> float:
    components = _load_wave_timing_baseline_components()[str(mode_id)]
    spawn_seconds = max(0.0, float(components['spawn_phase_seconds']))
    cooldown_seconds = max(0.0, float(components['cooldown_phase_seconds']))
    cooldown_reduction = max(0.0, min(100.0, float(wave_cooldown_reduction_pct or 0.0))) / 100.0
    return max(0.0, spawn_seconds + cooldown_seconds * (1.0 - cooldown_reduction))


def shared_cycle_seconds(periods: Iterable[float]) -> float:
    fracs = [_fraction_from_float(p) for p in periods if p > 0]
    if not fracs:
        return 0.0
    denom_lcm = 1
    for f in fracs:
        denom_lcm = _lcm(denom_lcm, f.denominator)
    ints = [f.numerator * (denom_lcm // f.denominator) for f in fracs]
    cycle_units = ints[0]
    for value in ints[1:]:
        cycle_units = _lcm(cycle_units, value)
    return float(Fraction(cycle_units, denom_lcm))


@dataclass(frozen=True)
class TimingMechanic:
    mechanic_id: str
    active_duration_s: float
    cooldown_s: float
    phase_offset_s: float = 0.0
    active_multiplier: float = 1.0

    @property
    def period_s(self) -> float:
        return max(0.0, self.active_duration_s) + max(0.0, self.cooldown_s)


@dataclass(frozen=True)
class TimingSegment:
    start_s: float
    end_s: float
    active_mechanics: List[str] = field(default_factory=list)
    combined_multiplier: float = 1.0


@dataclass(frozen=True)
class TimingSurfaces:
    bh_effective_duration_s: float = 0.0
    bh_effective_cooldown_s: float = 0.0
    bh_uptime_fraction: float = 0.0
    cf_effective_duration_s: float = 0.0
    cf_effective_cooldown_s: float = 0.0
    cf_uptime_fraction: float = 0.0
    gt_effective_duration_s: float = 0.0
    gt_effective_cooldown_s: float = 0.0
    gt_uptime_fraction: float = 0.0
    cf_damage_reduction_pct: float = 0.0
    cf_avg_damage_reduction_fraction: float = 0.0
    cf_slow_pct: float = 0.0
    bot_amplify_uptime_fraction: float = 0.0
    bot_golden_uptime_fraction: float = 0.0
    bot_thunder_uptime_fraction: float = 0.0
    bot_flame_cooldown_s: float = 0.0
    bot_flame_damage_reduction_pct: float = 0.0


@dataclass(frozen=True)
class CombatRuntimeSurfaces:
    boss_hit_interval_seconds: float
    orb_boss_hit_pct: Optional[float] = None
    orb_boss_hits_per_second: Optional[float] = None
    electron_hits_per_second: Optional[float] = None
    boss_contact_time_seconds: Optional[float] = None
    effective_damage_reduction_pct: Optional[float] = None
    incoming_damage_multiplier: Optional[float] = None
    source_notes: List[str] = field(default_factory=list)


def _load_orb_boss_hit_pct_by_level() -> Dict[int, float]:
    import csv
    out: Dict[int, float] = {}
    with ORB_BOSS_HIT_LEVELS_TABLE.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[int(row['level'])] = float(row['boss_max_hp_damage_pct'])
            except (TypeError, ValueError, KeyError):
                continue
    return out


def _lookup_row_value(row_map: Mapping[str, object], keys: List[str]) -> Optional[float]:
    for key in keys:
        row = row_map.get(key)
        if row is None:
            continue
        value = getattr(row, 'final_value', None) if not isinstance(row, dict) else row.get('final_value')
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _sum_input_values(rows: Sequence[StatInput], *, destination_object_type: str, destination_id: str) -> float:
    total = 0.0
    for row in rows:
        if row.destination_object_type != destination_object_type or row.destination_id != destination_id or not row.active:
            continue
        try:
            total += float(row.value)
        except (TypeError, ValueError):
            continue
    return total


def resolve_combat_runtime_surfaces(
    *,
    config: ScenarioConfig,
    scenario: ScenarioSurfaces,
    timing: TimingSurfaces,
    row_map: Optional[Mapping[str, object]] = None,
    account_state: Optional[object] = None,
    scenario_runtime_inputs: Optional[object] = None,
    orb_boss_hit_pct_override: Optional[float] = None,
    orb_boss_hits_per_second_override: Optional[float] = None,
    electron_hits_per_second_override: Optional[float] = None,
    boss_contact_time_seconds_override: Optional[float] = None,
    effective_damage_reduction_pct_override: Optional[float] = None,
    incoming_damage_multiplier_override: Optional[float] = None,
) -> CombatRuntimeSurfaces:
    notes: List[str] = []
    row_map = row_map or {}

    boss_hit_interval_override = _lookup_row_value(row_map, [
        _runtime('combat.boss_hit_interval_seconds'),
        _runtime('combat.boss_interval_seconds'),
    ])
    if boss_hit_interval_override is not None:
        boss_hit_interval_seconds = float(boss_hit_interval_override)
        notes.append(f'Boss hit interval consumed from governed surface: {boss_hit_interval_seconds}s.')
    else:
        boss_hit_interval_seconds = float(scenario.boss_hit_interval_seconds)
        notes.append(f'Boss hit interval sourced from scenario engine: {boss_hit_interval_seconds}s.')

    orb_pct = _lookup_row_value(row_map, [
        _runtime('combat.orb_boss_hit_pct'),
        _runtime('tower.orb_boss_hit_pct'),
        _runtime('tower.orb.hit_pct_vs_boss'),
    ])
    if orb_pct is not None:
        notes.append(f'Orb boss-hit pct consumed from governed surface: {orb_pct}.')
    else:
        lab_level = None
        if account_state is not None:
            labs = getattr(account_state, 'labs', {}) or {}
            try:
                lab_level = int(labs.get('Orb Boss Hit', 0) or 0)
            except (TypeError, ValueError):
                lab_level = 0
        if lab_level:
            orb_pct = _load_orb_boss_hit_pct_by_level().get(lab_level)
            if orb_pct is not None:
                notes.append(f'Orb boss-hit pct resolved from account lab level {lab_level} via KB table note-derived-orb-boss-hit-levels-1-10.csv: {orb_pct}.')
        if orb_pct is None and scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'orb_boss_hit_pct', None) is not None:
            orb_pct = float(scenario_runtime_inputs.orb_boss_hit_pct)
            notes.append(f'Orb boss-hit pct using scenario runtime input fallback: {orb_pct}.')
        if orb_pct is None and orb_boss_hit_pct_override is not None:
            orb_pct = float(orb_boss_hit_pct_override)
            notes.append(f'Orb boss-hit pct using explicit override fallback: {orb_pct}.')

    orb_hz = _lookup_row_value(row_map, [
        _runtime('combat.orb_boss_hits_per_second'),
        _runtime('tower.orb_boss_hits_per_second'),
        _runtime('tower.orb.hits_per_second_vs_boss'),
    ])
    if orb_hz is not None:
        notes.append(f'Orb boss-hit cadence consumed from governed surface: {orb_hz} Hz.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'orb_boss_hits_per_second', None) is not None:
        orb_hz = float(scenario_runtime_inputs.orb_boss_hits_per_second)
        notes.append(f'Orb boss-hit cadence using scenario runtime input fallback: {orb_hz} Hz.')
    elif orb_boss_hits_per_second_override is not None:
        orb_hz = float(orb_boss_hits_per_second_override)
        notes.append(f'Orb boss-hit cadence using explicit override fallback: {orb_hz} Hz.')
    else:
        notes.append('Orb boss-hit cadence remains open: no defended formula in current KB/package.')

    electron_hz = _lookup_row_value(row_map, [
        _runtime('combat.electron_hits_per_second'),
        _runtime('module.orbital_augment.electron_hits_per_second'),
        _runtime('module.orbital_augment.hits_per_second_vs_boss'),
    ])
    if electron_hz is not None:
        notes.append(f'Electron cadence consumed from governed surface: {electron_hz} Hz.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'electron_hits_per_second', None) is not None:
        electron_hz = float(scenario_runtime_inputs.electron_hits_per_second)
        notes.append(f'Electron cadence using scenario runtime input owner seam: {electron_hz} Hz.')
    elif electron_hits_per_second_override is not None:
        electron_hz = float(electron_hits_per_second_override)
        notes.append(f'Electron cadence using explicit override fallback: {electron_hz} Hz.')
    else:
        notes.append('Electron cadence remains open: no governed surface or scenario runtime input was supplied for Orbital Augment cadence.')

    contact_t = _lookup_row_value(row_map, [
        _runtime('combat.boss_contact_time_seconds'),
        _runtime('combat.contact_time_seconds_vs_boss'),
    ])
    if contact_t is not None:
        notes.append(f'Boss contact time consumed from governed surface: {contact_t}s.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'boss_contact_time_seconds', None) is not None:
        contact_t = float(scenario_runtime_inputs.boss_contact_time_seconds)
        notes.append(f'Boss contact time using scenario runtime input fallback: {contact_t}s.')
    elif boss_contact_time_seconds_override is not None:
        contact_t = float(boss_contact_time_seconds_override)
        notes.append(f'Boss contact time using explicit override fallback: {contact_t}s.')
    else:
        notes.append('Boss contact time remains open: no defended contact-distance/speed formula in current KB/package.')

    effective_dr = _lookup_row_value(row_map, [
        _runtime('combat.effective_damage_reduction_pct'),
    ])
    if effective_dr is not None:
        notes.append(f'Effective damage reduction consumed from governed surface: {effective_dr}%.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'effective_damage_reduction_pct', None) is not None:
        effective_dr = float(scenario_runtime_inputs.effective_damage_reduction_pct)
        notes.append(f'Effective damage reduction using scenario runtime input fallback: {effective_dr}%.')
    elif effective_damage_reduction_pct_override is not None:
        effective_dr = float(effective_damage_reduction_pct_override)
        notes.append(f'Effective damage reduction using explicit override fallback: {effective_dr}%.')

    incoming_damage_multiplier = None
    if scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'incoming_damage_multiplier', None) is not None:
        incoming_damage_multiplier = float(scenario_runtime_inputs.incoming_damage_multiplier)
        notes.append(f'Incoming damage multiplier using scenario runtime input: {incoming_damage_multiplier}.')
    elif incoming_damage_multiplier_override is not None:
        incoming_damage_multiplier = float(incoming_damage_multiplier_override)

    return CombatRuntimeSurfaces(
        boss_hit_interval_seconds=boss_hit_interval_seconds,
        orb_boss_hit_pct=None if orb_pct is None else float(orb_pct),
        orb_boss_hits_per_second=None if orb_hz is None else float(orb_hz),
        electron_hits_per_second=None if electron_hz is None else float(electron_hz),
        boss_contact_time_seconds=None if contact_t is None else float(contact_t),
        effective_damage_reduction_pct=None if effective_dr is None else float(effective_dr),
        incoming_damage_multiplier=None if incoming_damage_multiplier is None else float(incoming_damage_multiplier),
        source_notes=notes,
    )


def is_active_at_time(mechanic: TimingMechanic, time_s: float) -> bool:
    period = mechanic.period_s
    if period <= 0.0 or mechanic.active_duration_s <= 0.0:
        return False
    local = (time_s - mechanic.phase_offset_s) % period
    return 0.0 <= local < mechanic.active_duration_s


def active_intervals_within_horizon(mechanic: TimingMechanic, horizon_s: float) -> List[tuple[float, float]]:
    period = mechanic.period_s
    if horizon_s <= 0.0 or period <= 0.0 or mechanic.active_duration_s <= 0.0:
        return []
    intervals: List[tuple[float, float]] = []
    start = mechanic.phase_offset_s
    while start < horizon_s:
        end = min(horizon_s, start + mechanic.active_duration_s)
        if end > 0.0:
            intervals.append((max(0.0, start), end))
        start += period
    return intervals




def average_active_fraction_over_interval(mechanic: TimingMechanic, start_s: float, end_s: float) -> float:
    """Average active fraction for a mechanic across a closed-open interval [start, end)."""
    start = float(start_s)
    end = float(end_s)
    if end <= start:
        return 0.0
    if mechanic.period_s <= 0.0 or mechanic.active_duration_s <= 0.0:
        return 0.0
    total_active = 0.0
    horizon = end - start
    cursor = start
    # shift to the activation that may overlap the interval start
    period = mechanic.period_s
    phase = mechanic.phase_offset_s
    k = int((start - phase) // period) - 1
    activation_start = phase + k * period
    while activation_start < end:
        activation_end = activation_start + mechanic.active_duration_s
        overlap_start = max(start, activation_start)
        overlap_end = min(end, activation_end)
        if overlap_end > overlap_start:
            total_active += overlap_end - overlap_start
        activation_start += period
    return max(0.0, min(1.0, total_active / horizon))


def build_default_defensive_timing_mechanics(timing: TimingSurfaces) -> List[TimingMechanic]:
    mechanics: List[TimingMechanic] = []
    if timing.cf_effective_duration_s > 0.0 and timing.cf_effective_cooldown_s >= 0.0 and timing.cf_damage_reduction_pct > 0.0:
        mechanics.append(
            TimingMechanic(
                mechanic_id="chrono_field_damage_reduction",
                active_duration_s=timing.cf_effective_duration_s,
                cooldown_s=timing.cf_effective_cooldown_s,
                active_multiplier=max(0.0, 1.0 - (timing.cf_damage_reduction_pct / 100.0)),
            )
        )
    return mechanics


def compute_average_damage_reduction_fraction_over_interval(timing: TimingSurfaces, start_s: float, end_s: float) -> float:
    """Average timed damage reduction fraction over an encounter interval.

    Current governed scope: Chrono Field only. Flame Bot remains excluded until
    activation/persistence timing is explicitly modelled in the timing contract.
    """
    if end_s <= start_s:
        return 0.0
    total_fraction = 0.0
    for mechanic in build_default_defensive_timing_mechanics(timing):
        if mechanic.mechanic_id == "chrono_field_damage_reduction":
            active_fraction = average_active_fraction_over_interval(mechanic, start_s, end_s)
            total_fraction += active_fraction * (timing.cf_damage_reduction_pct / 100.0)
    return max(0.0, min(0.95, total_fraction))


def build_shared_cycle_segments(mechanics: Iterable[TimingMechanic]) -> List[TimingSegment]:
    mechanics = [m for m in mechanics if m.period_s > 0.0 and m.active_duration_s > 0.0]
    if not mechanics:
        return []
    horizon = shared_cycle_seconds(m.period_s for m in mechanics)
    if horizon <= 0.0:
        return []
    cuts = {0.0, horizon}
    for m in mechanics:
        for start, end in active_intervals_within_horizon(m, horizon):
            cuts.add(start)
            cuts.add(end)
    ordered = sorted(cuts)
    segments: List[TimingSegment] = []
    for idx in range(len(ordered) - 1):
        a = ordered[idx]
        b = ordered[idx + 1]
        if b <= a:
            continue
        mid = (a + b) / 2.0
        active = [m.mechanic_id for m in mechanics if is_active_at_time(m, mid)]
        mult = 1.0
        for m in mechanics:
            if m.mechanic_id in active:
                mult *= max(0.0, m.active_multiplier)
        segments.append(TimingSegment(start_s=a, end_s=b, active_mechanics=active, combined_multiplier=mult))
    return segments


def overlap_fraction(primary: TimingMechanic, secondary: TimingMechanic) -> float:
    horizon = shared_cycle_seconds([primary.period_s, secondary.period_s])
    if horizon <= 0.0:
        return 0.0
    overlap = 0.0
    for segment in build_shared_cycle_segments([primary, secondary]):
        if primary.mechanic_id in segment.active_mechanics and secondary.mechanic_id in segment.active_mechanics:
            overlap += segment.end_s - segment.start_s
    return overlap / horizon


def compute_average_combined_multiplier(mechanics: Iterable[TimingMechanic]) -> float:
    segments = build_shared_cycle_segments(mechanics)
    if not segments:
        return 1.0
    horizon = segments[-1].end_s - segments[0].start_s
    if horizon <= 0.0:
        return 1.0
    total = 0.0
    for seg in segments:
        total += (seg.end_s - seg.start_s) * seg.combined_multiplier
    return total / horizon


def compute_timing_surfaces(config: ScenarioConfig, scenario: Optional[ScenarioSurfaces] = None) -> TimingSurfaces:
    scenario = scenario or ScenarioSurfaces()
    uw_dur_reduction = getattr(scenario, "bc_uw_duration_reduction_s", 0.0)
    bh_dur = max(0.0, config.bh_base_duration_s + config.bh_perk_duration_add_s + uw_dur_reduction)
    bh_cd = max(0.0, config.bh_base_cooldown_s + config.bh_perk_cooldown_add_s)
    cf_dur = max(0.0, config.cf_base_duration_s + config.cf_perk_duration_add_s + uw_dur_reduction)
    cf_cd = max(0.0, config.cf_base_cooldown_s)
    gt_dur = max(0.0, config.gt_base_duration_s + uw_dur_reduction)
    gt_cd = max(0.0, config.gt_base_cooldown_s)
    cf_uptime = _uptime(cf_dur, cf_cd)
    return TimingSurfaces(
        bh_effective_duration_s=bh_dur,
        bh_effective_cooldown_s=bh_cd,
        bh_uptime_fraction=_uptime(bh_dur, bh_cd),
        cf_effective_duration_s=cf_dur,
        cf_effective_cooldown_s=cf_cd,
        cf_uptime_fraction=cf_uptime,
        gt_effective_duration_s=gt_dur,
        gt_effective_cooldown_s=gt_cd,
        gt_uptime_fraction=_uptime(gt_dur, gt_cd),
        cf_damage_reduction_pct=config.cf_damage_reduction_pct,
        cf_avg_damage_reduction_fraction=cf_uptime * (config.cf_damage_reduction_pct / 100.0) if config.cf_damage_reduction_pct > 0 and cf_uptime > 0 else 0.0,
        cf_slow_pct=config.cf_slow_pct,
        bot_amplify_uptime_fraction=_uptime(config.bot_amplify_duration_s, config.bot_amplify_cooldown_s),
        bot_golden_uptime_fraction=_uptime(config.bot_golden_duration_s, config.bot_golden_cooldown_s),
        bot_thunder_uptime_fraction=_uptime(config.bot_thunder_duration_s, config.bot_thunder_cooldown_s),
        bot_flame_cooldown_s=config.bot_flame_cooldown_s,
        bot_flame_damage_reduction_pct=config.bot_flame_damage_reduction_pct,
    )


def materialize_timing_family_baseline(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    materializer: FamilyBaselineMaterializer | None = None,
    compiled_family_rows: tuple[BoundStatInputs, tuple[StatInput, ...]] | None = None,
) -> FamilyBaselineContributorMap:
    bound, rows = compiled_family_rows or compile_timing_family_rows(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
    )
    return (materializer or FamilyBaselineMaterializer()).materialize_from_rows(bound.binding.identity, family_id, rows)


def compile_timing_family_rows(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    bound_stat_inputs: BoundStatInputs | None = None,
) -> tuple[BoundStatInputs, tuple[StatInput, ...]]:
    _validate_timing_family_request(family_id=family_id, scenario_config=scenario_config, perks_enabled=perks_enabled)
    bound = bound_stat_inputs or compile_stat_inputs_with_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name or preset_name,
        module_preset_name=module_preset_name or preset_name,
        perk_preset_name=perk_preset_name or preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_context={
            'mode_id': scenario_config.mode_id,
            'tier': scenario_config.tier,
            'league': scenario_config.league,
            'tournament_wave': scenario_config.tournament_wave,
        },
    )
    scenario_config = replace(
        scenario_config,
        bh_base_duration_s=_sum_input_values(bound.stat_inputs, destination_object_type='mechanic_param', destination_id='uw.black_hole.duration_seconds'),
        bh_base_cooldown_s=_sum_input_values(bound.stat_inputs, destination_object_type='mechanic_param', destination_id='uw.black_hole.cooldown_seconds'),
        gt_base_duration_s=_sum_input_values(bound.stat_inputs, destination_object_type='mechanic_param', destination_id='uw.golden_tower.duration_seconds'),
        gt_base_cooldown_s=_sum_input_values(bound.stat_inputs, destination_object_type='mechanic_param', destination_id='uw.golden_tower.cooldown_seconds'),
    )
    scenario = compute_scenario_surfaces(scenario_config)
    timing = compute_timing_surfaces(scenario_config, scenario)
    wave_cooldown_reduction_pct = _wave_cooldown_reduction_pct_from_rows(bound.stat_inputs)
    derived_rows = tuple(_timing_family_derived_rows(scenario_config, scenario, timing, wave_cooldown_reduction_pct))
    replaced_surface_keys = {
        (row.destination_object_type, row.destination_id)
        for row in derived_rows
        if row.destination_object_type and row.destination_id
    }
    base_rows = tuple(
        row for row in bound.stat_inputs
        if (row.destination_object_type, row.destination_id) not in replaced_surface_keys
    )
    return bound, base_rows + derived_rows


def resolve_timing_family_query(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    requested_surface_ids: Sequence[str],
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    trace_mode: str = 'contributors',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
    compiled_family_rows: tuple[BoundStatInputs, tuple[StatInput, ...]] | None = None,
    copy_result: bool = True,
) -> QueryResponse:
    query_kernel = kernel or get_default_query_kernel()
    if kernel is not None:
        query_kernel = kernel
        baseline = materialize_timing_family_baseline(
            account_state=account_state,
            family_id=family_id,
            preset_name=preset_name,
            scenario_config=scenario_config,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
            runtime_branch_id=runtime_branch_id,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            materializer=query_kernel.materializer,
            compiled_family_rows=compiled_family_rows,
        )
        return query_kernel.resolve_surfaces(baseline, requested_surface_ids=requested_surface_ids, trace_mode=trace_mode)

    planner = QEResolutionPlanner()
    bound, rows = compiled_family_rows or compile_timing_family_rows(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
    )
    result = planner.resolve_rows_declared_family_query(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id=family_id,
        requested_surface_ids=requested_surface_ids,
        trace_mode=trace_mode,
        copy_result=copy_result,
    )
    return result.response


def resolve_timing_consumer_bundle(
    *,
    account_state: AccountState,
    consumer_id: str,
    bundle_id: str,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    perks_enabled: bool,
    include_optional_surface_ids: Sequence[str] = (),
    state_mode: str = 'start_of_run',
    runtime_branch_id: str = 'branch_base',
    trace_mode: str | None = None,
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
    compiled_family_rows: tuple[BoundStatInputs, tuple[StatInput, ...]] | None = None,
    copy_result: bool = True,
) -> QueryResponse:
    resolved_bundle = resolve_consumer_bundle(
        consumer_id,
        bundle_id,
        family_id=family_id,
        include_optional_surface_ids=include_optional_surface_ids,
        trace_mode=trace_mode,
    )
    effective_trace_mode = resolved_bundle.minimum_trace_mode if trace_mode is None else str(trace_mode)
    return resolve_timing_family_query(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        requested_surface_ids=resolved_bundle.surface_ids,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        trace_mode=effective_trace_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        kernel=kernel,
        compiled_family_rows=compiled_family_rows,
        copy_result=copy_result,
    )


def merge_scenario_publication_rows(
    statbook,
    *,
    account_state: AccountState,
    stat_inputs: Sequence[StatInput],
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    state_mode: str,
    perks_enabled: bool,
    farming_hours_per_day: float = 23.5,
) -> None:
    """Simulator-owned timing/scenario enrichment for publication/report flows."""
    bound, rows = compile_timing_family_rows(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
    )
    timing_statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id=family_id,
        requested_surface_ids=('support_surface::timing.wave_duration_seconds_effective',),
        notes='scenario publication timing prerequisite merge',
        diagnostics={'source': 'simulators.timing.merge_scenario_publication_rows'},
    )
    for surface_id, row in timing_statbook.rows.items():
        statbook.rows[surface_id] = row
    publish_farming_throughput_support_surfaces(
        statbook.rows,
        account_state=account_state,
        config=scenario_config,
        stat_inputs=stat_inputs,
        farming_hours_per_day=farming_hours_per_day,
    )


def _validate_timing_family_request(*, family_id: str, scenario_config: ScenarioConfig, perks_enabled: bool) -> None:
    if family_id == 'timing_tournament_no_perks':
        if scenario_config.mode_id != 'tournament':
            raise ValueError('timing_tournament_no_perks requires ScenarioConfig.mode_id="tournament".')
        if perks_enabled:
            raise ValueError('timing_tournament_no_perks forbids perks_enabled=True because tournament implies perks disabled.')
    elif family_id == 'timing_farm_with_perks':
        if scenario_config.mode_id != 'farming':
            raise ValueError('timing_farm_with_perks requires ScenarioConfig.mode_id="farming".')
        if not perks_enabled:
            raise ValueError('timing_farm_with_perks requires perks_enabled=True.')
    elif family_id == 'timing_scenario_probe':
        if scenario_config.mode_id == 'tournament' and perks_enabled:
            raise ValueError('timing_scenario_probe still enforces tournament implies perks disabled.')
    else:
        raise ValueError(f'Unsupported timing family_id {family_id!r}.')


def _timing_family_derived_rows(
    config: ScenarioConfig,
    scenario: ScenarioSurfaces,
    timing: TimingSurfaces,
    wave_cooldown_reduction_pct: float,
) -> tuple[StatInput, ...]:
    mode_id = 'tournament' if config.mode_id == 'tournament' else 'farming'
    effective_wave_duration_seconds = wave_duration_seconds_after_cooldown_reduction(mode_id, wave_cooldown_reduction_pct)
    return (
        StatInput(
            stat_name='Black Hole Effective Duration',
            source_family='scenario_rules',
            source_name='Black Hole',
            value=timing.bh_effective_duration_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.black_hole.effective_duration',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='runtime_mechanic_param',
            destination_id='uw.black_hole.duration_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Black Hole Effective Cooldown',
            source_family='scenario_rules',
            source_name='Black Hole',
            value=timing.bh_effective_cooldown_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.black_hole.effective_cooldown',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='runtime_mechanic_param',
            destination_id='uw.black_hole.cooldown_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Golden Tower Effective Duration',
            source_family='scenario_rules',
            source_name='Golden Tower',
            value=timing.gt_effective_duration_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.golden_tower.effective_duration',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='runtime_mechanic_param',
            destination_id='uw.golden_tower.duration_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Golden Tower Effective Cooldown',
            source_family='scenario_rules',
            source_name='Golden Tower',
            value=timing.gt_effective_cooldown_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.golden_tower.effective_cooldown',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='runtime_mechanic_param',
            destination_id='uw.golden_tower.cooldown_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Wave Duration Effective',
            source_family='scenario_rules',
            source_name='Wave Accelerator',
            value=effective_wave_duration_seconds,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.wave_duration_seconds_effective',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='support_surface',
            destination_id='timing.wave_duration_seconds_effective',
            kb_mapped=True,
        ),
    )


def _wave_cooldown_reduction_pct_from_rows(rows: Sequence[StatInput]) -> float:
    for row in rows:
        if (
            row.destination_object_type == 'runtime_mechanic_param'
            and row.destination_id == 'cards.wave_accelerator.wave_cooldown_reduction_pct'
            and row.active
        ):
            try:
                return float(row.value)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def build_default_econ_timing_mechanics(statbook_rows: Dict[str, dict]) -> List[TimingMechanic]:
    def _get(key: str, default: float = 0.0) -> float:
        row = statbook_rows.get(_sid(key)) or {}
        try:
            return float(row.get("final_value", default))
        except (TypeError, ValueError):
            return default
    def _tp(base_key: str, runtime_key: str) -> float:
        return _get(base_key) + _get(runtime_key)
    return [
        TimingMechanic(
            mechanic_id="golden_tower",
            active_duration_s=_get(_mech('uw.golden_tower.duration_seconds')),
            cooldown_s=_get(_mech('uw.golden_tower.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_mech('uw.golden_tower.bonus_multiplier'))),
        ),
        TimingMechanic(
            mechanic_id="black_hole_coin",
            active_duration_s=_tp(_mech('uw.black_hole.duration_seconds'), _runtime('uw.black_hole.duration_seconds')),
            cooldown_s=_tp(_mech('uw.black_hole.cooldown_seconds'), _runtime('uw.black_hole.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_runtime('uw.black_hole.coin_bonus_multiplier'))),
        ),
        TimingMechanic(
            mechanic_id="golden_bot",
            active_duration_s=_get(_mech('bot.golden.duration_seconds')),
            cooldown_s=_get(_mech('bot.golden.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_mech('bot.golden.bonus_multiplier'))),
        ),
    ]


def _farming_econ_sync_window_readiness_summary(
    econ_window_drivers: Sequence[Mapping[str, object]],
    *,
    run_tracker_evidence: Mapping[str, object] | None = None,
    approve_tracker_empirical_econ_window_overlap: bool = False,
) -> dict[str, object]:
    driver_by_surface = {str(driver.get("surface_id")): dict(driver) for driver in econ_window_drivers}

    def _driver_value(surface_id: str) -> float:
        try:
            return float(driver_by_surface.get(surface_id, {}).get("value") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    window_specs = [
        (
            "golden_tower",
            "state::uw.golden_tower.duration_seconds",
            "state::uw.golden_tower.cooldown_seconds",
            "state::uw.golden_tower.bonus_multiplier",
        ),
        (
            "black_hole_coin",
            "state::uw.black_hole.duration_seconds",
            "state::uw.black_hole.cooldown_seconds",
            "state::uw.black_hole.coin_bonus_multiplier",
        ),
        (
            "golden_bot",
            "state::bot.golden.duration_seconds",
            "state::bot.golden.cooldown_seconds",
            "state::bot.golden.bonus_multiplier",
        ),
    ]
    mechanics: list[TimingMechanic] = []
    window_inputs: list[dict[str, object]] = []
    missing_window_inputs: list[str] = []
    for mechanic_id, duration_surface, cooldown_surface, multiplier_surface in window_specs:
        duration_driver = driver_by_surface.get(duration_surface, {})
        cooldown_driver = driver_by_surface.get(cooldown_surface, {})
        multiplier_driver = driver_by_surface.get(multiplier_surface, {})
        duration = _driver_value(duration_surface)
        cooldown = _driver_value(cooldown_surface)
        multiplier = max(0.0, _driver_value(multiplier_surface))
        available = bool(duration_driver.get("available")) and bool(cooldown_driver.get("available"))
        if not available:
            missing_window_inputs.extend(
                surface
                for surface, driver in (
                    (duration_surface, duration_driver),
                    (cooldown_surface, cooldown_driver),
                )
                if not bool(driver.get("available"))
            )
        mechanic = TimingMechanic(
            mechanic_id=mechanic_id,
            active_duration_s=duration,
            cooldown_s=cooldown,
            active_multiplier=multiplier,
        )
        if available and duration > 0.0 and mechanic.period_s > 0.0:
            mechanics.append(mechanic)
        window_inputs.append(
            {
                "mechanic_id": mechanic_id,
                "duration_surface_id": duration_surface,
                "cooldown_surface_id": cooldown_surface,
                "multiplier_surface_id": multiplier_surface,
                "duration_seconds": duration,
                "cooldown_seconds": cooldown,
                "cycle_period_seconds_current_helper": mechanic.period_s,
                "active_multiplier": multiplier,
                "uptime_fraction_duration_over_period": (
                    duration / mechanic.period_s if mechanic.period_s > 0.0 else 0.0
                ),
                "window_inputs_available": available,
            }
        )

    mechanics_by_id = {mechanic.mechanic_id: mechanic for mechanic in mechanics}

    def _pair_overlap(left: str, right: str) -> float | None:
        if left not in mechanics_by_id or right not in mechanics_by_id:
            return None
        return overlap_fraction(mechanics_by_id[left], mechanics_by_id[right])

    pair_overlap_fractions = {
        "golden_tower__black_hole_coin": _pair_overlap("golden_tower", "black_hole_coin"),
        "golden_tower__golden_bot": _pair_overlap("golden_tower", "golden_bot"),
        "black_hole_coin__golden_bot": _pair_overlap("black_hole_coin", "golden_bot"),
    }
    overlap_integral_missing = [
        "phase_offsets_or_sync_schedule",
        "kill_density_inside_each_econ_window",
        "death_wave_coin_bonus_active_window_or_kill_state",
        "spotlight_coin_exposure_fraction_by_kill",
        "wave_skip_reward_interaction_with_econ_windows",
    ]
    overlap_integral_readiness = {
        "status": (
            "source_window_inputs_available_overlap_integral_missing"
            if len(mechanics) == len(window_specs)
            else "window_inputs_missing_overlap_integral_missing"
        ),
        "owner": "simulators.timing",
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": "none",
        "phase_model": "phase_zero_current_helper_only",
        "phase_model_certified": False,
        "window_mechanic_ids": [item["mechanic_id"] for item in window_inputs],
        "window_inputs_available": len(mechanics) == len(window_specs),
        "pair_overlap_fraction_source": "simulators.timing.overlap_fraction",
        "pair_overlap_fraction_formula_status": (
            "phase_zero_current_helper_pairwise_fraction_only"
        ),
        "pair_overlap_fractions": pair_overlap_fractions,
        "multiplier_only_without_window_model": [
            "state::uw.death_wave.coin_bonus_multiplier",
            "state::uw.spotlight.coin_bonus_multiplier",
        ],
        "remaining_to_certify": overlap_integral_missing,
    }
    tracker_econ_coin_sources: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    if isinstance(run_tracker_evidence, Mapping):
        tracker_recent = run_tracker_evidence.get("farming_t14_recent")
        tracker_recent = tracker_recent if isinstance(tracker_recent, Mapping) else {}
        tracker_econ_coin_sources = dict(tracker_recent.get("tracker_econ_coin_sources") or {})
        if not tracker_econ_coin_sources:
            tracker_econ_coin_sources = {
                "status": "tracker_supplied_without_econ_coin_source_fields",
                "application": "external_observation_not_account_truth",
                "certification_effect": "none",
            }
    approved_overlap_closes_formula_link = (
        bool(approve_tracker_empirical_econ_window_overlap)
        and bool(overlap_integral_readiness.get("window_inputs_available"))
        and tracker_econ_coin_sources.get("status") == "tracker_econ_coin_sources_available"
    )
    overlap_integral_readiness.update(
        {
            "certification_effect": (
                "closes_econ_window_overlap_link_only"
                if approved_overlap_closes_formula_link
                else "none"
            ),
            "operator_approval_required": True,
            "operator_approved_tracker_empirical_econ_window_overlap": bool(
                approve_tracker_empirical_econ_window_overlap
            ),
            "operator_approval_status": (
                "approved_explicit_runtime_input"
                if approve_tracker_empirical_econ_window_overlap
                else "not_approved"
            ),
            "approval_runtime_input": "approve_tracker_empirical_econ_window_overlap",
            "approval_policy": (
                "Explicit approval plus tracker econ-source evidence closes only "
                "the econ-window overlap formula link; it does not certify farming CPH."
            ),
            "tracker_econ_source_candidate_available": (
                tracker_econ_coin_sources.get("status")
                == "tracker_econ_coin_sources_available"
            ),
            "approved_overlap_closes_formula_link": (
                approved_overlap_closes_formula_link
            ),
        }
    )
    return {
        "status": (
            "window_inputs_available_overlap_integral_not_certified"
            if len(mechanics) == len(window_specs)
            else "window_inputs_missing_overlap_integral_not_certified"
        ),
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": (
            "closes_econ_window_overlap_link_only"
            if approved_overlap_closes_formula_link
            else "none"
        ),
        "phase_model": "phase_zero_current_helper_only",
        "phase_model_certified": False,
        "available_window_count": len(mechanics),
        "required_window_count": len(window_specs),
        "missing_window_inputs": missing_window_inputs,
        "window_inputs": window_inputs,
        "pair_overlap_fractions": pair_overlap_fractions,
        "overlap_integral_readiness": overlap_integral_readiness,
        "tracker_econ_coin_source_evidence": tracker_econ_coin_sources,
        "operator_approval_status": overlap_integral_readiness.get(
            "operator_approval_status"
        ),
        "approved_overlap_closes_formula_link": approved_overlap_closes_formula_link,
        "diagnostic_average_combined_multiplier_for_available_windows": (
            compute_average_combined_multiplier(mechanics) if mechanics else None
        ),
        "multiplier_only_without_window_model": [
            "state::uw.death_wave.coin_bonus_multiplier",
            "state::uw.spotlight.coin_bonus_multiplier",
        ],
        "missing_to_certify": overlap_integral_missing,
    }


def _farming_spawn_density_readiness_summary(
    *,
    tier: object,
    target_wave: object,
    wave_accelerator_spawn_rate_acceleration: object,
    enemy_balance_mastery_double_elite_chance_pct: object = 0.0,
    run_tracker_evidence: Mapping[str, object] | None = None,
    approve_tracker_empirical_kill_density_transform: bool = False,
) -> dict[str, object]:
    def _positive_float(value: object) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 0.0:
            return None
        return numeric

    try:
        tier_number = min(21, max(1, int(float(tier or 1))))
    except (TypeError, ValueError):
        tier_number = 1
    try:
        wave = int(float(target_wave or 0.0))
    except (TypeError, ValueError):
        wave = 0
    try:
        acceleration = max(1.0, float(wave_accelerator_spawn_rate_acceleration or 1.0))
    except (TypeError, ValueError):
        acceleration = 1.0
    try:
        enemy_balance_mastery_pct = max(
            0.0,
            float(enemy_balance_mastery_double_elite_chance_pct or 0.0),
        )
    except (TypeError, ValueError):
        enemy_balance_mastery_pct = 0.0
    normal_spawn_rate = normal_spawn_rate_pressure_driver(
        wave=wave,
        enemy_balance_spawn_multiplier=1.0,
        wave_accelerator_spawn_rate_acceleration=acceleration,
        more_enemies_pct=0.0,
    )
    pressure_driver_probe = non_boss_pressure_driver_probe(
        tier=tier_number,
        wave=wave,
        scenario_surfaces={"bc_more_enemies_pct": 0.0},
        enemy_balance_spawn_multiplier=1.0,
        wave_accelerator_spawn_rate_acceleration=acceleration,
        enemy_balance_mastery_double_elite_chance_pct=enemy_balance_mastery_pct,
    )
    displayed_spawn_rate = normal_spawn_rate.get("displayed_spawn_rate")
    tracker_enemy_density: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
    }
    tracker_enemy_composition: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_kill_density_transform: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_kill_density_stability: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_coin_density: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
    }
    tracker_coin_yield_stability: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_coin_integral: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    if isinstance(run_tracker_evidence, Mapping):
        recent = run_tracker_evidence.get("farming_t14_recent")
        recent = recent if isinstance(recent, Mapping) else {}
        trend = run_tracker_evidence.get("farming_t14_recent_trend")
        trend = trend if isinstance(trend, Mapping) else {}
        trend_metrics = trend.get("metrics")
        trend_metrics = trend_metrics if isinstance(trend_metrics, Mapping) else {}
        enemy_per_wave = dict(recent.get("observed_enemies_per_wave") or {})
        coins_per_enemy = dict(recent.get("observed_coins_per_enemy") or {})
        coins_per_wave = dict(recent.get("observed_coins_per_wave") or {})
        coins_per_run = dict(recent.get("coins_per_run") or {})
        coins_per_hour = dict(recent.get("coins_per_hour") or {})
        waves_per_hour = dict(recent.get("observed_waves_per_hour") or {})
        total_enemies = dict(recent.get("total_enemies") or {})
        enemy_per_hour = dict(recent.get("tracker_enemies_per_hour") or {})
        tracker_enemy_composition = dict(recent.get("tracker_enemy_composition") or {})
        wave_stats = dict(recent.get("wave") or {})
        duration_stats = dict(recent.get("duration_hours") or {})
        latest = recent.get("latest")
        latest = latest if isinstance(latest, Mapping) else {}
        latest_wave = _positive_float(latest.get("wave"))
        latest_duration_hours = _positive_float(latest.get("duration_hours"))
        latest_total_enemies = _positive_float(latest.get("total_enemies"))
        latest_coins = _positive_float(latest.get("coins"))
        latest_enemies_per_wave = _positive_float(
            latest.get("observed_enemies_per_wave")
        )
        latest_coins_per_enemy = _positive_float(latest.get("observed_coins_per_enemy"))
        latest_coins_per_wave = _positive_float(latest.get("observed_coins_per_wave"))
        latest_waves_per_hour = _positive_float(latest.get("observed_waves_per_hour"))
        if latest_waves_per_hour is None:
            latest_waves_per_hour = _positive_float(latest.get("waves_per_hour"))
        if (
            latest_enemies_per_wave is None
            and latest_total_enemies is not None
            and latest_wave is not None
        ):
            latest_enemies_per_wave = latest_total_enemies / latest_wave
        if (
            latest_coins_per_enemy is None
            and latest_coins is not None
            and latest_total_enemies is not None
        ):
            latest_coins_per_enemy = latest_coins / latest_total_enemies
        if (
            latest_coins_per_wave is None
            and latest_coins is not None
            and latest_wave is not None
        ):
            latest_coins_per_wave = latest_coins / latest_wave
        latest_density_coins_per_hour = _positive_float(
            latest.get("observed_cph_from_density_components")
        )
        if (
            latest_density_coins_per_hour is None
            and latest_coins_per_enemy is not None
            and latest_enemies_per_wave is not None
            and latest_waves_per_hour is not None
        ):
            latest_density_coins_per_hour = (
                latest_coins_per_enemy
                * latest_enemies_per_wave
                * latest_waves_per_hour
            )
        latest_run_total_coins_per_hour = _positive_float(
            latest.get("observed_cph_from_run_totals")
        )
        if (
            latest_run_total_coins_per_hour is None
            and latest_coins is not None
            and latest_duration_hours is not None
        ):
            latest_run_total_coins_per_hour = latest_coins / latest_duration_hours
        observed_median_enemies_per_wave = enemy_per_wave.get("median")
        observed_median_coins_per_enemy = coins_per_enemy.get("median")
        observed_median_coins_per_wave = coins_per_wave.get("median")
        spawn_rate_to_observed_density_ratio = None
        try:
            if displayed_spawn_rate is not None and float(displayed_spawn_rate) > 0.0:
                spawn_rate_to_observed_density_ratio = (
                    float(observed_median_enemies_per_wave) / float(displayed_spawn_rate)
                )
        except (TypeError, ValueError):
            spawn_rate_to_observed_density_ratio = None
        projected_enemies_per_wave_from_tracker_ratio = None
        try:
            if (
                displayed_spawn_rate is not None
                and spawn_rate_to_observed_density_ratio is not None
            ):
                projected_enemies_per_wave_from_tracker_ratio = (
                    float(displayed_spawn_rate) * float(spawn_rate_to_observed_density_ratio)
                )
        except (TypeError, ValueError):
            projected_enemies_per_wave_from_tracker_ratio = None
        tracker_enemy_density = {
            "status": (
                "tracker_t14_farming_enemy_density_available"
                if recent.get("row_count") and observed_median_enemies_per_wave is not None
                else "tracker_supplied_without_enemy_density_band"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "recent_definition": recent.get("definition"),
            "recent_row_count": recent.get("row_count"),
            "observed_median_wave": wave_stats.get("median"),
            "observed_median_duration_hours": duration_stats.get("median"),
            "observed_median_total_enemies": total_enemies.get("median"),
            "observed_median_enemies_per_wave": observed_median_enemies_per_wave,
            "observed_median_enemies_per_hour": enemy_per_hour.get("median"),
            "tracker_enemy_composition_status": tracker_enemy_composition.get("status"),
            "tracker_total_elites_share_of_total_enemies": dict(
                tracker_enemy_composition.get("total_elites_share_of_total_enemies") or {}
            ).get("median"),
            "tracker_protector_share_of_total_enemies": dict(
                dict(
                    tracker_enemy_composition.get("normal_enemy_counts") or {}
                ).get("protector")
                or {}
            )
            .get("share_of_total_enemies", {})
            .get("median"),
            "tracker_protector_count_per_wave": dict(
                dict(
                    tracker_enemy_composition.get("normal_enemy_counts") or {}
                ).get("protector")
                or {}
            )
            .get("count_per_wave", {})
            .get("median"),
            "tracker_elite_subtype_count_per_wave": dict(
                tracker_enemy_composition.get("elite_tracked_count_per_wave") or {}
            ).get("median"),
            "displayed_spawn_rate_to_observed_enemies_per_wave_ratio": (
                spawn_rate_to_observed_density_ratio
            ),
            "interpretation": (
                "Tracker totalEnemies provides external kill-density calibration evidence only; it is not KB truth."
            ),
        }
        tracker_kill_density_transform = {
            "status": (
                "tracker_spawn_rate_to_kill_density_candidate_available"
                if recent.get("row_count")
                and spawn_rate_to_observed_density_ratio is not None
                and projected_enemies_per_wave_from_tracker_ratio is not None
                else "tracker_supplied_without_spawn_rate_to_kill_density_candidate"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "formula": "displayed_spawn_rate * observed_enemies_per_wave_per_displayed_spawn_rate",
            "recent_definition": recent.get("definition"),
            "recent_row_count": recent.get("row_count"),
            "target_wave": wave,
            "displayed_spawn_rate": displayed_spawn_rate,
            "observed_median_enemies_per_wave": observed_median_enemies_per_wave,
            "observed_enemies_per_wave_per_displayed_spawn_rate": (
                spawn_rate_to_observed_density_ratio
            ),
            "projected_enemies_per_wave_from_tracker_ratio": (
                projected_enemies_per_wave_from_tracker_ratio
            ),
            "missing_to_promote": [
                "source_owned_normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase",
                "approved_spawn_rate_to_kill_density_transform",
                "validation_across_tiers_run_types_and_spawn_phases",
            ],
            "interpretation": (
                "Candidate transform makes the missing kill-density link testable; "
                "it is not applied to account truth or CPH certification."
            ),
        }
        trend_enemy_density = dict(trend_metrics.get("observed_enemies_per_wave") or {})
        trend_cph_density = dict(
            trend_metrics.get("observed_cph_from_density_components") or {}
        )
        recent_enemy_density = dict(trend_enemy_density.get("recent") or {})
        prior_enemy_density = dict(trend_enemy_density.get("prior") or {})
        recent_density_ratio = None
        prior_density_ratio = None
        density_ratio_delta = None
        density_ratio_ratio = None
        try:
            if displayed_spawn_rate is not None and float(displayed_spawn_rate) > 0.0:
                if recent_enemy_density.get("median") is not None:
                    recent_density_ratio = (
                        float(recent_enemy_density.get("median"))
                        / float(displayed_spawn_rate)
                    )
                if prior_enemy_density.get("median") is not None:
                    prior_density_ratio = (
                        float(prior_enemy_density.get("median"))
                        / float(displayed_spawn_rate)
                    )
                if recent_density_ratio is not None and prior_density_ratio is not None:
                    density_ratio_delta = recent_density_ratio - prior_density_ratio
                    if prior_density_ratio != 0.0:
                        density_ratio_ratio = recent_density_ratio / prior_density_ratio
        except (TypeError, ValueError):
            recent_density_ratio = None
            prior_density_ratio = None
            density_ratio_delta = None
            density_ratio_ratio = None
        tracker_kill_density_stability = {
            "status": (
                "tracker_recent_prior_kill_density_transform_available"
                if trend.get("status") == "recent_and_prior_windows_available"
                and recent_density_ratio is not None
                and prior_density_ratio is not None
                else "tracker_supplied_without_recent_prior_kill_density_transform"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "formula": "observed_enemies_per_wave_median / displayed_spawn_rate",
            "trend_status": trend.get("status"),
            "recent_window_size": trend.get("recent_window_size"),
            "prior_window_size": trend.get("prior_window_size"),
            "displayed_spawn_rate": displayed_spawn_rate,
            "recent_observed_enemies_per_wave_median": recent_enemy_density.get("median"),
            "prior_observed_enemies_per_wave_median": prior_enemy_density.get("median"),
            "recent_enemies_per_wave_per_displayed_spawn_rate": recent_density_ratio,
            "prior_enemies_per_wave_per_displayed_spawn_rate": prior_density_ratio,
            "median_delta": density_ratio_delta,
            "median_ratio": density_ratio_ratio,
            "enemy_density_direction": trend_enemy_density.get("direction"),
            "density_component_cph_direction": trend_cph_density.get("direction"),
            "missing_to_promote": [
                "approved_empirical_kill_density_transform_policy",
                "validation_across_multiple_exports_and_account_states",
                "source_owned_or_approved_wave_skip_intro_reward_semantics",
            ],
            "interpretation": (
                "Recent/prior tracker density ratios make empirical kill-density drift "
                "visible while account stats improve; they are not applied to account "
                "truth or CPH certification."
            ),
        }
        tracker_coin_density = {
            "status": (
                "tracker_t14_farming_coin_density_available"
                if recent.get("row_count")
                and (
                    observed_median_coins_per_enemy is not None
                    or observed_median_coins_per_wave is not None
                )
                else "tracker_supplied_without_coin_density_band"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "recent_definition": recent.get("definition"),
            "recent_row_count": recent.get("row_count"),
            "observed_median_coins_per_run": coins_per_run.get("median"),
            "observed_median_coins_per_hour": coins_per_hour.get("median"),
            "observed_median_coins_per_enemy": observed_median_coins_per_enemy,
            "observed_median_coins_per_wave": observed_median_coins_per_wave,
            "latest_wave": latest.get("wave"),
            "latest_duration_hours": latest.get("duration_hours"),
            "latest_coins": latest.get("coins"),
            "latest_total_enemies": latest.get("total_enemies"),
            "latest_observed_coins_per_enemy": latest_coins_per_enemy,
            "latest_observed_coins_per_wave": latest_coins_per_wave,
            "latest_observed_enemies_per_wave": latest_enemies_per_wave,
            "latest_observed_waves_per_hour": latest_waves_per_hour,
            "latest_density_coins_per_hour": latest_density_coins_per_hour,
            "latest_run_total_coins_per_hour": latest_run_total_coins_per_hour,
            "interpretation": (
                "Tracker coin density is calibration evidence for the future coin integral; it is not a certified CPH formula."
            ),
        }
        trend_coins_per_enemy = dict(trend_metrics.get("observed_coins_per_enemy") or {})
        trend_coins_per_wave = dict(trend_metrics.get("observed_coins_per_wave") or {})
        trend_coins_per_hour = dict(trend_metrics.get("coins_per_hour") or {})
        recent_coins_per_enemy = dict(trend_coins_per_enemy.get("recent") or {})
        prior_coins_per_enemy = dict(trend_coins_per_enemy.get("prior") or {})
        recent_coins_per_wave = dict(trend_coins_per_wave.get("recent") or {})
        prior_coins_per_wave = dict(trend_coins_per_wave.get("prior") or {})
        tracker_coin_yield_stability = {
            "status": (
                "tracker_recent_prior_coin_yield_available"
                if trend.get("status") == "recent_and_prior_windows_available"
                and recent_coins_per_enemy.get("median") is not None
                and prior_coins_per_enemy.get("median") is not None
                else "tracker_supplied_without_recent_prior_coin_yield"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "recent_window_size": trend.get("recent_window_size"),
            "prior_window_size": trend.get("prior_window_size"),
            "recent_observed_coins_per_enemy_median": recent_coins_per_enemy.get("median"),
            "prior_observed_coins_per_enemy_median": prior_coins_per_enemy.get("median"),
            "coins_per_enemy_median_delta": trend_coins_per_enemy.get("median_delta"),
            "coins_per_enemy_median_ratio": trend_coins_per_enemy.get("median_ratio"),
            "coins_per_enemy_direction": trend_coins_per_enemy.get("direction"),
            "recent_observed_coins_per_wave_median": recent_coins_per_wave.get("median"),
            "prior_observed_coins_per_wave_median": prior_coins_per_wave.get("median"),
            "coins_per_wave_median_delta": trend_coins_per_wave.get("median_delta"),
            "coins_per_wave_median_ratio": trend_coins_per_wave.get("median_ratio"),
            "coins_per_wave_direction": trend_coins_per_wave.get("direction"),
            "density_component_cph_direction": trend_cph_density.get("direction"),
            "reported_cph_direction": trend_coins_per_hour.get("direction"),
            "missing_to_promote": [
                "source_owned_coins_per_kill_integral",
                "econ_window_coin_multiplier_overlap_integral",
                "wave_skip_reward_and_intro_sprint_coin_semantics",
                "validation_across_multiple_exports_and_account_states",
            ],
            "interpretation": (
                "Recent/prior tracker coin-yield bands show whether CPH movement "
                "comes from coin value rather than kill-density drift; they are "
                "not applied to account truth or CPH certification."
            ),
        }
        projected_coins_per_wave_from_tracker_density = None
        projected_coins_per_hour_from_tracker_density = None
        tracker_coin_integral_to_reported_cph_ratio = None
        latest_projected_coins_per_wave_from_tracker_density = None
        latest_projected_coins_per_hour_from_tracker_density = None
        latest_density_to_latest_run_total_cph_ratio = None
        try:
            if (
                projected_enemies_per_wave_from_tracker_ratio is not None
                and observed_median_coins_per_enemy is not None
            ):
                projected_coins_per_wave_from_tracker_density = (
                    float(projected_enemies_per_wave_from_tracker_ratio)
                    * float(observed_median_coins_per_enemy)
                )
                if waves_per_hour.get("median") is not None:
                    projected_coins_per_hour_from_tracker_density = (
                        projected_coins_per_wave_from_tracker_density
                        * float(waves_per_hour.get("median"))
                    )
                if (
                    projected_coins_per_hour_from_tracker_density is not None
                    and coins_per_hour.get("median") is not None
                    and float(coins_per_hour.get("median")) > 0.0
                ):
                    tracker_coin_integral_to_reported_cph_ratio = (
                        projected_coins_per_hour_from_tracker_density
                        / float(coins_per_hour.get("median"))
                    )
            if (
                latest_enemies_per_wave is not None
                and latest_coins_per_enemy is not None
            ):
                latest_projected_coins_per_wave_from_tracker_density = (
                    float(latest_enemies_per_wave) * float(latest_coins_per_enemy)
                )
                if latest_waves_per_hour is not None:
                    latest_projected_coins_per_hour_from_tracker_density = (
                        latest_projected_coins_per_wave_from_tracker_density
                        * float(latest_waves_per_hour)
                    )
                if (
                    latest_projected_coins_per_hour_from_tracker_density is not None
                    and latest_run_total_coins_per_hour is not None
                    and float(latest_run_total_coins_per_hour) > 0.0
                ):
                    latest_density_to_latest_run_total_cph_ratio = (
                        latest_projected_coins_per_hour_from_tracker_density
                        / float(latest_run_total_coins_per_hour)
                    )
        except (TypeError, ValueError):
            projected_coins_per_wave_from_tracker_density = None
            projected_coins_per_hour_from_tracker_density = None
            tracker_coin_integral_to_reported_cph_ratio = None
            latest_projected_coins_per_wave_from_tracker_density = None
            latest_projected_coins_per_hour_from_tracker_density = None
            latest_density_to_latest_run_total_cph_ratio = None
        tracker_coin_integral = {
            "status": (
                "tracker_kill_density_to_coin_integral_candidate_available"
                if recent.get("row_count")
                and projected_coins_per_wave_from_tracker_density is not None
                else "tracker_supplied_without_coin_integral_candidate"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "formula": "projected_enemies_per_wave * observed_coins_per_enemy",
            "recent_definition": recent.get("definition"),
            "recent_row_count": recent.get("row_count"),
            "projected_enemies_per_wave": projected_enemies_per_wave_from_tracker_ratio,
            "observed_median_coins_per_enemy": observed_median_coins_per_enemy,
            "projected_coins_per_wave_from_tracker_density": (
                projected_coins_per_wave_from_tracker_density
            ),
            "observed_median_waves_per_hour": waves_per_hour.get("median"),
            "projected_coins_per_hour_from_tracker_density": (
                projected_coins_per_hour_from_tracker_density
            ),
            "tracker_median_coins_per_hour": coins_per_hour.get("median"),
            "projected_to_tracker_cph_ratio": tracker_coin_integral_to_reported_cph_ratio,
            "latest_wave": latest.get("wave"),
            "latest_observed_enemies_per_wave": latest_enemies_per_wave,
            "latest_observed_coins_per_enemy": latest_coins_per_enemy,
            "latest_projected_coins_per_wave_from_tracker_density": (
                latest_projected_coins_per_wave_from_tracker_density
            ),
            "latest_observed_waves_per_hour": latest_waves_per_hour,
            "latest_projected_coins_per_hour_from_tracker_density": (
                latest_projected_coins_per_hour_from_tracker_density
            ),
            "latest_run_total_coins_per_hour": latest_run_total_coins_per_hour,
            "latest_density_to_latest_run_total_cph_ratio": (
                latest_density_to_latest_run_total_cph_ratio
            ),
            "missing_to_promote": [
                "approved_spawn_rate_to_kill_density_transform",
                "source_owned_coins_per_kill_integral",
                "econ_window_coin_multiplier_overlap_integral",
                "wave_skip_reward_and_intro_sprint_coin_semantics",
            ],
            "interpretation": (
                "Candidate coin integral connects observed kill density to coin density; "
                "it is not applied to account truth or CPH certification."
            ),
        }
    tracker_kill_density_status = tracker_kill_density_transform.get("status")
    tracker_kill_density_approved = (
        bool(approve_tracker_empirical_kill_density_transform)
        and tracker_kill_density_status == "tracker_spawn_rate_to_kill_density_candidate_available"
    )
    kill_density_transform_readiness: dict[str, object] = {
        "status": (
            "approved_tracker_empirical_kill_density_transform_available"
            if tracker_kill_density_approved
            else "source_spawn_rate_available_kill_density_transform_missing"
        ),
        "owner": "simulators.timing",
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": (
            "closes_spawn_rate_to_enemy_kill_density_link_only"
            if tracker_kill_density_approved
            else "none"
        ),
        "source_input_status": {
            "normal_spawn_rate_curve_by_wave_and_wave_accelerator": True,
            "displayed_spawn_rate_available": displayed_spawn_rate is not None,
            "wave_accelerator_spawn_rate_acceleration_available": acceleration is not None,
            "normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase": False,
        },
        "tier": tier_number,
        "target_wave": wave,
        "displayed_spawn_rate": displayed_spawn_rate,
        "wave_accelerator_spawn_rate_acceleration": acceleration,
        "normal_spawn_rate_pressure_index": normal_spawn_rate.get(
            "normal_spawn_rate_pressure_index"
        ),
        "normal_enemy_spawn_count_curve_available": False,
        "tracker_candidate_status": tracker_kill_density_status,
        "tracker_candidate_can_promote": bool(
            tracker_kill_density_status == "tracker_spawn_rate_to_kill_density_candidate_available"
        ),
        "operator_approved_tracker_empirical_kill_density_transform": bool(
            approve_tracker_empirical_kill_density_transform
        ),
        "operator_approval_status": (
            "approved_explicit_runtime_input"
            if approve_tracker_empirical_kill_density_transform
            else "not_approved"
        ),
        "approval_runtime_input": "approve_tracker_empirical_kill_density_transform",
        "approved_transform_closes_formula_link": tracker_kill_density_approved,
        "candidate_formula_policy": (
            "tracker candidates are calibration evidence only until operator-approved "
            "as empirical defaults or replaced by a source-owned spawn-count curve"
        ),
        "remaining_to_certify": [
            "source_owned_normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase",
            "approved_spawn_rate_to_kill_density_transform",
            "tier_wave_spawn_phase_validation_set",
            "integration_with_intro_sprint_wave_skip_and_econ_windows",
        ],
    }
    return {
        "status": "spawn_rate_curve_available_kill_density_transform_missing",
        "application": "diagnostic_only_not_coin_formula",
        "tier": tier_number,
        "target_wave": wave,
        "wave_accelerator_spawn_rate_acceleration": acceleration,
        "enemy_balance_mastery_double_elite_chance_pct": enemy_balance_mastery_pct,
        "displayed_spawn_rate": displayed_spawn_rate,
        "threshold_standard_wave": normal_spawn_rate.get("threshold_standard_wave"),
        "threshold_actual_wave_with_wave_accelerator": normal_spawn_rate.get(
            "threshold_actual_wave_with_wave_accelerator"
        ),
        "next_displayed_spawn_rate": normal_spawn_rate.get("next_displayed_spawn_rate"),
        "next_threshold_standard_wave": normal_spawn_rate.get("next_threshold_standard_wave"),
        "next_threshold_actual_wave_with_wave_accelerator": normal_spawn_rate.get(
            "next_threshold_actual_wave_with_wave_accelerator"
        ),
        "normal_spawn_rate_pressure_index": normal_spawn_rate.get(
            "normal_spawn_rate_pressure_index"
        ),
        "normal_enemy_spawn_count_curve_available": False,
        "normal_enemy_spawn_count_source_audit": {
            "status": "source_not_found_spawn_rate_curve_only",
            "application": "diagnostic_only_not_coin_formula",
            "certification_effect": "none",
            "local_kb_tables_checked": [
                "kb/enemies/tables/wiki-advanced-analysis-spawn-rate-wave-thresholds.csv",
                "kb/enemies/tables/note-derived-enemy-spawn-structure.csv",
                "kb/enemies/tables/note-derived-enemy-spawn-caps.csv",
                "kb/enemies/tables/wiki-verified-elite-spawn-thresholds.csv",
                "kb/enemies/tables/wiki-verified-fleet-spawn-thresholds.csv",
            ],
            "external_sources_checked": [
                "https://the-tower-idle-tower-defense.fandom.com/wiki/AdvancedAnalysis",
                "https://the-tower-idle-tower-defense.fandom.com/wiki/Enemies",
            ],
            "source_backed_available_surfaces": [
                "normal_spawn_rate_wave_thresholds",
                "normal_enemy_on_screen_spawn_cap",
                "elite_spawn_thresholds",
                "fleet_spawn_schedule",
            ],
            "missing_source_owned_surface": (
                "normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase"
            ),
            "interpretation": (
                "Current KB/wiki evidence supports displayed spawn-rate thresholds "
                "and caps, but not a normal enemy per-wave spawn-count ramp. "
                "Tracker totalEnemies remains calibration evidence only."
            ),
        },
        "kill_density_transform_readiness": kill_density_transform_readiness,
        "non_boss_pressure_driver_evidence": {
            "status": pressure_driver_probe.get("status"),
            "application": "diagnostic_only_not_coin_formula",
            "certification_effect": "none",
            "tier": pressure_driver_probe.get("tier"),
            "wave": pressure_driver_probe.get("wave"),
            "bc_more_enemies_pct": pressure_driver_probe.get("bc_more_enemies_pct"),
            "wave_accelerator_spawn_rate_acceleration": pressure_driver_probe.get(
                "wave_accelerator_spawn_rate_acceleration"
            ),
            "enemy_balance_mastery_double_elite_chance_pct": (
                pressure_driver_probe.get("elite_spawn_pressure") or {}
            ).get("enemy_balance_mastery_double_elite_chance_pct"),
            "normal_spawn_rate_pressure": pressure_driver_probe.get(
                "normal_spawn_rate_pressure"
            ),
            "elite_spawn_pressure": pressure_driver_probe.get("elite_spawn_pressure"),
            "fleet_spawn_pressure": pressure_driver_probe.get("fleet_spawn_pressure"),
            "source_backed_curve_coverage": pressure_driver_probe.get(
                "source_backed_curve_coverage"
            ),
            "missing_terminal_formula_links": pressure_driver_probe.get(
                "missing_terminal_formula_links"
            ),
            "interpretation": (
                "Source-backed normal, elite, and fleet pressure drivers are visible "
                "for farming CPH calibration, but no terminal pressure or coin-density "
                "transform is certified here."
            ),
        },
        "source_tables": normal_spawn_rate.get("source_tables") or [],
        "source_formula_status": normal_spawn_rate.get("formula_status"),
        "tracker_enemy_density_evidence": tracker_enemy_density,
        "tracker_enemy_composition_evidence": tracker_enemy_composition,
        "tracker_kill_density_transform_candidate": tracker_kill_density_transform,
        "tracker_kill_density_stability_evidence": tracker_kill_density_stability,
        "tracker_coin_density_evidence": tracker_coin_density,
        "tracker_coin_yield_stability_evidence": tracker_coin_yield_stability,
        "tracker_coin_integral_candidate": tracker_coin_integral,
        "missing_to_certify": [
            "normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase",
            "spawn_rate_to_enemy_kill_density_by_wave",
            "kill_density_to_coins_per_kill_integral",
        ],
    }


def farming_econ_timing_readiness_summary(
    statbook_rows: Mapping[str, object],
    *,
    run_tracker_evidence: Mapping[str, object] | None = None,
    approve_tracker_empirical_cph_default: bool = False,
    approve_tracker_empirical_run_coin_duration_integrals: bool = False,
    approve_tracker_current_export_account_state_validation: bool = False,
    approve_tracker_empirical_run_duration_projection: bool = False,
    approve_tracker_empirical_wave_skip_reward: bool = False,
    approve_tracker_wave_skip_intro_semantics: bool = False,
    approve_source_intro_sprint_coin_window: bool = False,
    approve_tracker_empirical_econ_window_overlap: bool = False,
    approve_tracker_empirical_kill_density_transform: bool = False,
    observed_coins_per_hour: float = 210_000_000_000_000.0,
    observed_run_hours: float = 5.5,
    observed_final_wave: int | None = None,
    observed_tier: int = 14,
    preset_name: str = "Farming",
) -> dict[str, object]:
    """Expose farming econ timing readiness without claiming a CPH formula."""

    observed_final_wave_supplied = observed_final_wave is not None
    observed_final_wave_value = int(observed_final_wave) if observed_final_wave_supplied else 5500

    def _row(surface_id: str) -> Mapping[str, object]:
        raw = statbook_rows.get(surface_id) if isinstance(statbook_rows, Mapping) else None
        return raw if isinstance(raw, Mapping) else {}

    def _value(surface_id: str) -> object:
        return _row(surface_id).get("final_value")

    def _ratio(numerator: object, denominator: object) -> float | None:
        try:
            denominator_value = float(denominator)
            if denominator_value == 0.0:
                return None
            return float(numerator) / denominator_value
        except (TypeError, ValueError):
            return None

    def _positive_float(value: object) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 0.0:
            return None
        return numeric

    def _driver(surface_id: str, owner: str, role: str) -> dict[str, object]:
        row = _row(surface_id)
        present = bool(row)
        return {
            "surface_id": surface_id,
            "owner": owner,
            "role": role,
            "status": str(row.get("status") or ("missing" if not present else "unknown")),
            "available": present and row.get("final_value") is not None,
            "value": row.get("final_value") if present else None,
            "value_type": row.get("value_type") if present else None,
        }

    timing_drivers = [
        _driver(
            "support_surface::timing.wave_duration_seconds_effective",
            "simulators.timing",
            "effective wave duration after Wave Accelerator cooldown reduction",
        ),
        _driver(
            "state::meta.game_speed_multiplier",
            "qe -> simulators.timing",
            "runtime game speed multiplier for real elapsed run time",
        ),
        _driver(
            "state::perk.max_game_speed",
            "qe -> simulators.timing",
            "Max Game Speed perk contribution to real elapsed run time",
        ),
        _driver(
            "state::cards.wave_accelerator.wave_cooldown_reduction_pct",
            "qe -> simulators.timing",
            "Wave Accelerator base-card cooldown reduction",
        ),
        _driver(
            "state::cards.wave_accelerator.spawn_rate_acceleration",
            "qe -> simulators.scenario",
            "Wave Accelerator Mastery spawn-rate ramp acceleration",
        ),
        _driver(
            "state::cards.wave_skip.chance_pct",
            "qe -> simulators.scenario",
            "Wave Skip chance for effective waves and skipped-wave reward semantics",
        ),
        _driver(
            "state::cards.wave_skip.mastery_effect",
            "qe -> simulators.scenario",
            "Wave Skip Mastery chance to double wave skips for timing/economy diagnostics",
        ),
        _driver(
            "state::cards.intro_sprint.waves",
            "qe -> simulators.scenario",
            "Intro Sprint active waves; KB states no coins are earned during Intro Sprint",
        ),
        _driver(
            "support_surface::scenario.target_farming_wave",
            "simulators.scenario",
            "target farming wave for the run horizon",
        ),
        _driver(
            "support_surface::scenario.waves_per_run_effective",
            "simulators.scenario",
            "effective waves per run after Wave Skip and Intro Sprint",
        ),
        _driver(
            "support_surface::scenario.runs_per_day_effective",
            "simulators.scenario",
            "run cadence from target wave and effective wave duration",
        ),
    ]
    econ_window_drivers = [
        _driver("state::uw.golden_tower.duration_seconds", "simulators.timing", "Golden Tower duration"),
        _driver("state::uw.golden_tower.cooldown_seconds", "simulators.timing", "Golden Tower cooldown"),
        _driver("state::uw.golden_tower.bonus_multiplier", "qe", "Golden Tower coin multiplier"),
        _driver("state::uw.black_hole.duration_seconds", "simulators.timing", "Black Hole duration"),
        _driver("state::uw.black_hole.cooldown_seconds", "simulators.timing", "Black Hole cooldown"),
        _driver("state::uw.black_hole.coin_bonus_multiplier", "qe", "Black Hole coin multiplier"),
        _driver("state::uw.death_wave.coin_bonus_multiplier", "qe", "Death Wave coin multiplier"),
        _driver("state::uw.spotlight.coin_bonus_multiplier", "qe", "Spotlight coin multiplier"),
        _driver("state::bot.golden.duration_seconds", "qe", "Golden Bot duration"),
        _driver("state::bot.golden.cooldown_seconds", "qe", "Golden Bot cooldown"),
        _driver("state::bot.golden.bonus_multiplier", "qe", "Golden Bot coin multiplier"),
    ]
    economy_drivers = [
        _driver("state::economy.coins_multiplier", "qe", "base/all coins multiplier"),
        _driver("state::economy.coin_bonus_multiplier", "qe", "coin bonus multiplier"),
        _driver("state::economy.coins_per_kill_bonus", "qe", "coins per kill bonus"),
        _driver("state::economy.coins_per_wave", "qe", "coins per wave"),
    ]
    econ_sync_window_readiness = _farming_econ_sync_window_readiness_summary(
        econ_window_drivers,
        run_tracker_evidence=run_tracker_evidence,
        approve_tracker_empirical_econ_window_overlap=(
            approve_tracker_empirical_econ_window_overlap
        ),
    )
    all_drivers = [*timing_drivers, *econ_window_drivers, *economy_drivers]
    missing_required = [
        str(driver["surface_id"])
        for driver in timing_drivers
        if not bool(driver["available"])
        and str(driver["surface_id"]) != "state::cards.wave_skip.mastery_effect"
    ]
    coins_per_run = max(0.0, float(observed_coins_per_hour or 0.0)) * max(
        0.0,
        float(observed_run_hours or 0.0),
    )
    projected_duration = _value("support_surface::timing.wave_duration_seconds_effective")
    target_wave = _value("support_surface::scenario.target_farming_wave")
    effective_waves_per_run = _value("support_surface::scenario.waves_per_run_effective")
    wave_skip_pct = _value("state::cards.wave_skip.chance_pct")
    wave_skip_mastery_pct = _value("state::cards.wave_skip.mastery_effect")
    intro_sprint_waves = _value("state::cards.intro_sprint.waves")
    wave_accelerator_spawn_rate_acceleration = _value(
        "state::cards.wave_accelerator.spawn_rate_acceleration"
    )
    enemy_balance_mastery_double_elite_chance_pct = _value(
        "state::cards.enemy_balance.mastery_effect"
    )
    game_speed = _value("state::meta.game_speed_multiplier")
    max_game_speed = _value("state::perk.max_game_speed")
    estimated_run_hours_from_current_timing = None
    estimated_run_hours_after_game_speed = None
    estimated_played_waves_after_wave_skip_intro = None
    estimated_run_hours_after_wave_skip_intro_and_game_speed = None
    estimated_wave_skip_expected_skip_multiplier = None
    estimated_wave_skip_expected_skipped_waves = None
    effective_game_speed_multiplier = None

    def _estimate_run_hours_for_target_wave(target_wave_value: object) -> tuple[float | None, float | None, float | None]:
        try:
            wave_value = max(0.0, float(target_wave_value))
            projected_duration_value = float(projected_duration)
        except (TypeError, ValueError):
            return None, None, None
        try:
            skip_multiplier = 1.0 + (max(0.0, float(wave_skip_pct or 0.0)) / 100.0)
            mastery_double_chance = max(0.0, float(wave_skip_mastery_pct or 0.0)) / 100.0
            skip_multiplier *= 1.0 + mastery_double_chance
            if skip_multiplier <= 0.0:
                skip_multiplier = 1.0
            intro_waves_for_target = min(
                max(0.0, float(intro_sprint_waves or 0.0)),
                wave_value,
            )
            played_waves = max(0.0, (wave_value - intro_waves_for_target) / skip_multiplier)
            skipped_waves = max(0.0, wave_value - intro_waves_for_target - played_waves)
            if not effective_game_speed_multiplier or effective_game_speed_multiplier <= 0.0:
                return None, played_waves, skipped_waves
            return (
                played_waves
                * projected_duration_value
                / 3600.0
                / float(effective_game_speed_multiplier),
                played_waves,
                skipped_waves,
            )
        except (TypeError, ValueError):
            return None, None, None

    try:
        estimated_run_hours_from_current_timing = (
            float(projected_duration) * float(target_wave)
        ) / 3600.0
    except (TypeError, ValueError):
        estimated_run_hours_from_current_timing = None
    try:
        effective_game_speed_multiplier = max(0.0, float(game_speed or 0.0)) + max(
            0.0,
            float(max_game_speed or 0.0),
        )
        if effective_game_speed_multiplier > 0.0 and estimated_run_hours_from_current_timing is not None:
            estimated_run_hours_after_game_speed = (
                estimated_run_hours_from_current_timing / effective_game_speed_multiplier
            )
    except (TypeError, ValueError):
        effective_game_speed_multiplier = None
        estimated_run_hours_after_game_speed = None
    try:
        wave_skip_multiplier = 1.0 + (max(0.0, float(wave_skip_pct or 0.0)) / 100.0)
        mastery_double_chance = max(0.0, float(wave_skip_mastery_pct or 0.0)) / 100.0
        estimated_wave_skip_expected_skip_multiplier = wave_skip_multiplier * (1.0 + mastery_double_chance)
        intro_waves = min(max(0.0, float(intro_sprint_waves or 0.0)), max(0.0, float(target_wave)))
        estimated_played_waves_after_wave_skip_intro = max(
            0.0,
            (float(target_wave) - intro_waves) / estimated_wave_skip_expected_skip_multiplier,
        )
        estimated_wave_skip_expected_skipped_waves = max(
            0.0,
            float(target_wave) - intro_waves - estimated_played_waves_after_wave_skip_intro,
        )
        if effective_game_speed_multiplier and effective_game_speed_multiplier > 0.0:
            estimated_run_hours_after_wave_skip_intro_and_game_speed = (
                estimated_played_waves_after_wave_skip_intro
                * float(projected_duration)
                / 3600.0
                / float(effective_game_speed_multiplier)
            )
    except (TypeError, ValueError):
        estimated_played_waves_after_wave_skip_intro = None
        estimated_run_hours_after_wave_skip_intro_and_game_speed = None
        estimated_wave_skip_expected_skip_multiplier = None
        estimated_wave_skip_expected_skipped_waves = None
    tracker_alignment: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
    }
    tracker_cph_calibration: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_cph_identity: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    tracker_wave_reward: dict[str, object] = {
        "status": "not_supplied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
    }
    intro_sprint_driver = next(
        (
            driver
            for driver in timing_drivers
            if driver["surface_id"] == "state::cards.intro_sprint.waves"
        ),
        {},
    )
    wave_skip_driver = next(
        (
            driver
            for driver in timing_drivers
            if driver["surface_id"] == "state::cards.wave_skip.chance_pct"
        ),
        {},
    )
    wave_skip_mastery_driver = next(
        (
            driver
            for driver in timing_drivers
            if driver["surface_id"] == "state::cards.wave_skip.mastery_effect"
        ),
        {},
    )
    wave_reward_source_audit: dict[str, object] = {
        "status": "base_reward_sources_available_integral_semantics_unresolved",
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": "none",
        "intro_sprint_coin_suppression": {
            "status": (
                "source_backed_available"
                if bool(intro_sprint_driver.get("available"))
                else "runtime_surface_missing"
            ),
            "surface_id": "state::cards.intro_sprint.waves",
            "driver_status": intro_sprint_driver.get("status"),
            "active_wave_count": intro_sprint_waves,
            "source_files": [
                "kb/cards/tables/card-base-ladders.csv",
                "kb/global-rules/contracts/stat-query-initial-surface-set.yaml",
            ],
            "source_semantics": "Intro Sprint active waves earn no coins.",
        },
        "wave_skip_base_reward": {
            "status": (
                "source_backed_available_expected_value_missing"
                if bool(wave_skip_driver.get("available"))
                else "runtime_surface_missing"
            ),
            "surface_id": "state::cards.wave_skip.chance_pct",
            "driver_status": wave_skip_driver.get("status"),
            "chance_pct": wave_skip_pct,
            "source_files": ["kb/cards/tables/card-base-ladders.csv"],
            "source_semantics": (
                "Wave Skip chance skips a wave and earns coins/cash equal to "
                "the previous wave times 1.10."
            ),
        },
        "wave_skip_mastery_double_skip": {
            "status": (
                "source_backed_available_reward_integral_missing"
                if wave_skip_mastery_driver.get("status") not in {None, "missing"}
                else "runtime_surface_missing"
            ),
            "surface_id": "state::cards.wave_skip.mastery_effect",
            "driver_status": wave_skip_mastery_driver.get("status"),
            "double_skip_chance_pct": wave_skip_mastery_pct,
            "source_files": ["kb/cards/tables/card-masteries.csv"],
            "source_semantics": (
                "Wave Skip Mastery provides a chance to double wave skip; the "
                "expected-value reward integral for double skips is still unpromoted."
            ),
        },
        "tracker_skip_count_semantics": {
            "status": tracker_alignment.get("skip_semantics_gap_status"),
            "inference_status": dict(
                tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
            ).get("status"),
            "best_candidate": dict(
                tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
            ).get("best_candidate"),
            "best_candidate_distance_from_expected": dict(
                tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
            ).get("best_candidate_distance_from_expected"),
            "operator_confirmation_required": dict(
                tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
            ).get("operator_confirmation_required"),
            "raw_tracker_waves_skipped_median": None,
            "candidate_semantics": [
                "tracker_skips_exclude_intro_sprint",
                "tracker_skips_include_intro_sprint",
            ],
            "interpretation": (
                "Tracker wavesSkipped semantics must be resolved before the "
                "Wave Skip reward expected value can become a certified CPH input."
            ),
        },
        "missing_to_promote": [
            "wave_skip_coin_reward_expected_value_over_per_wave_coin_curve",
            "wave_skip_mastery_double_skip_reward_semantics",
            "tracker_waves_skipped_intro_sprint_semantics",
            "econ_window_overlap_for_skipped_and_played_waves",
        ],
    }
    wave_skip_reward_readiness: dict[str, object] = {
        "status": "source_reward_semantics_available_expected_value_integral_missing",
        "owner": "simulators.timing",
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": "none",
        "source_audit": wave_reward_source_audit,
        "tracker_reward_status": tracker_wave_reward.get("status"),
        "tracker_reward_field_status": tracker_wave_reward.get("tracker_reward_field_status"),
        "remaining_to_certify": [
            "wave_skip_coin_reward_expected_value_over_per_wave_coin_curve",
            "wave_skip_mastery_double_skip_reward_semantics",
            "tracker_waves_skipped_intro_sprint_semantics",
            "econ_window_overlap_for_skipped_and_played_waves",
        ],
    }
    coin_eligible_displayed_waves_after_intro_at_target = None
    try:
        target_wave_value = max(0.0, float(target_wave))
        intro_sprint_wave_value = min(
            max(0.0, float(intro_sprint_waves or 0.0)),
            target_wave_value,
        )
        coin_eligible_displayed_waves_after_intro_at_target = max(
            0.0,
            target_wave_value - intro_sprint_wave_value,
        )
    except (TypeError, ValueError):
        coin_eligible_displayed_waves_after_intro_at_target = None
    intro_sprint_coin_window_readiness: dict[str, object] = {
        "status": (
            "source_intro_sprint_coin_suppression_available_coin_integral_missing"
            if bool(intro_sprint_driver.get("available"))
            else "intro_sprint_runtime_surface_missing_coin_integral_missing"
        ),
        "owner": "simulators.timing",
        "application": "diagnostic_only_not_coin_formula",
        "certification_effect": "none",
        "source_surface_id": "state::cards.intro_sprint.waves",
        "driver_status": intro_sprint_driver.get("status"),
        "active_wave_count": intro_sprint_waves,
        "target_wave": target_wave,
        "coin_eligible_displayed_waves_after_intro_at_target": (
            coin_eligible_displayed_waves_after_intro_at_target
        ),
        "source_files": [
            "kb/cards/tables/card-base-ladders.csv",
            "kb/global-rules/contracts/stat-query-initial-surface-set.yaml",
        ],
        "source_semantics": "Intro Sprint active waves earn no coins.",
        "remaining_to_certify": [
            "source_owned_per_wave_coin_curve_after_intro_sprint",
            "intro_sprint_boundary_interaction_with_wave_skip_and_wave_rewards",
            "econ_window_overlap_for_post_intro_played_and_skipped_waves",
            "run_coin_integral_excluding_intro_sprint_waves",
        ],
    }
    approved_intro_sprint_coin_window_closes_formula_link = (
        bool(approve_source_intro_sprint_coin_window)
        and bool(intro_sprint_driver.get("available"))
        and coin_eligible_displayed_waves_after_intro_at_target is not None
    )
    intro_sprint_coin_window_readiness.update(
        {
            "certification_effect": (
                "closes_intro_sprint_no_coin_window_link_only"
                if approved_intro_sprint_coin_window_closes_formula_link
                else "none"
            ),
            "operator_approval_required": True,
            "operator_approved_source_intro_sprint_coin_window": bool(
                approve_source_intro_sprint_coin_window
            ),
            "operator_approval_status": (
                "approved_explicit_runtime_input"
                if approve_source_intro_sprint_coin_window
                else "not_approved"
            ),
            "approval_runtime_input": "approve_source_intro_sprint_coin_window",
            "approval_policy": (
                "Explicit approval plus source-backed Intro Sprint no-coin evidence "
                "closes only the Intro Sprint coin-window formula link; it does not "
                "certify farming CPH."
            ),
            "source_coin_window_candidate_available": (
                bool(intro_sprint_driver.get("available"))
                and coin_eligible_displayed_waves_after_intro_at_target is not None
            ),
            "approved_window_closes_formula_link": (
                approved_intro_sprint_coin_window_closes_formula_link
            ),
        }
    )
    if isinstance(run_tracker_evidence, Mapping):
        tracker_recent = run_tracker_evidence.get("farming_t14_recent")
        tracker_recent = tracker_recent if isinstance(tracker_recent, Mapping) else {}
        tracker_wave = dict(tracker_recent.get("wave") or {})
        tracker_duration = dict(tracker_recent.get("duration_hours") or {})
        tracker_game_time = dict(tracker_recent.get("tracker_game_time_hours") or {})
        tracker_game_to_real_duration_ratio = dict(
            tracker_recent.get("tracker_game_to_real_duration_ratio") or {}
        )
        tracker_cph = dict(tracker_recent.get("coins_per_hour") or {})
        tracker_coins_per_run = dict(tracker_recent.get("coins_per_run") or {})
        tracker_waves_per_hour = dict(tracker_recent.get("observed_waves_per_hour") or {})
        tracker_reported_waves_per_hour = dict(
            tracker_recent.get("tracker_waves_per_hour") or {}
        )
        tracker_reported_to_observed_waves_per_hour_ratio = dict(
            tracker_recent.get("tracker_to_observed_waves_per_hour_ratio") or {}
        )
        tracker_seconds_per_wave = dict(tracker_recent.get("observed_seconds_per_wave") or {})
        tracker_enemies_per_wave = dict(tracker_recent.get("observed_enemies_per_wave") or {})
        tracker_coins_per_enemy = dict(tracker_recent.get("observed_coins_per_enemy") or {})
        tracker_run_total_cph = dict(tracker_recent.get("observed_cph_from_run_totals") or {})
        tracker_run_total_cph_ratio = dict(
            tracker_recent.get("observed_cph_to_tracker_reported_ratio") or {}
        )
        tracker_component_cph = dict(
            tracker_recent.get("observed_cph_from_density_components") or {}
        )
        tracker_coins_from_wave_skip = dict(
            tracker_recent.get("tracker_coins_from_wave_skip") or {}
        )
        tracker_coins_per_wave_reported = dict(
            tracker_recent.get("tracker_coins_per_wave") or {}
        )
        tracker_coins_per_wave_to_observed_ratio = dict(
            tracker_recent.get("tracker_coins_per_wave_to_observed_ratio") or {}
        )
        tracker_wave_skip_coin_share = dict(
            tracker_recent.get("tracker_wave_skip_coin_share") or {}
        )
        tracker_wave_skip_coins_per_skipped_wave = dict(
            tracker_recent.get("tracker_wave_skip_coins_per_skipped_wave") or {}
        )
        observed_median_wave = tracker_wave.get("median")
        observed_median_duration_hours = tracker_duration.get("median")
        observed_median_coins_per_hour = tracker_cph.get("median")
        observed_median_coins_per_run = tracker_coins_per_run.get("median")
        projected_hours_at_tracker_median_wave = None
        skip_adjusted_projected_hours_at_tracker_median_wave = None
        skip_adjusted_duration_ratio = None
        skip_adjusted_played_waves_at_tracker_median_wave = None
        expected_skipped_waves_at_tracker_median_wave = None
        observed_skipped_waves_median = dict(tracker_recent.get("waves_skipped") or {}).get("median")
        observed_skip_ratio = None
        expected_skip_ratio = None
        observed_non_intro_displayed_waves = None
        observed_played_waves_after_intro_from_tracker = None
        observed_effective_skip_multiplier_after_intro = None
        observed_skipped_waves_after_intro_if_tracker_includes_intro = None
        observed_played_waves_after_intro_if_tracker_skips_include_intro = None
        observed_effective_skip_multiplier_after_intro_if_tracker_skips_include_intro = None
        observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro = None
        implied_wave_skip_chance_if_no_mastery_pct = None
        implied_wave_skip_mastery_double_chance_pct = None
        observed_to_expected_skip_multiplier_ratio = None
        skip_semantics_gap_status = "not_evaluated"
        run_duration_ratio = None
        tracker_waves_per_hour_consistency_status = "not_supplied"
        tracker_game_time_ratio_status = "not_supplied"
        tracker_reported_coins_per_wave_semantics_status = "not_supplied"
        try:
            reported_ratio = tracker_reported_to_observed_waves_per_hour_ratio.get("median")
            if reported_ratio is not None:
                tracker_waves_per_hour_consistency_status = (
                    "tracker_reported_waves_per_hour_matches_duration"
                    if abs(float(reported_ratio) - 1.0) <= 0.02
                    else "tracker_reported_waves_per_hour_diverges_from_duration"
                )
        except (TypeError, ValueError):
            tracker_waves_per_hour_consistency_status = "not_available"
        try:
            coins_per_wave_ratio = tracker_coins_per_wave_to_observed_ratio.get("median")
            if coins_per_wave_ratio is not None:
                tracker_reported_coins_per_wave_semantics_status = (
                    "tracker_reported_coins_per_wave_close_to_total_observed"
                    if 0.8 <= float(coins_per_wave_ratio) <= 1.2
                    else "tracker_reported_coins_per_wave_diverges_from_total_observed"
                )
        except (TypeError, ValueError):
            tracker_reported_coins_per_wave_semantics_status = "not_available"
        try:
            game_ratio = tracker_game_to_real_duration_ratio.get("median")
            if game_ratio is not None:
                tracker_game_time_ratio_status = (
                    "tracker_game_time_ratio_available"
                    if float(game_ratio) > 0.0
                    else "tracker_game_time_ratio_nonpositive"
                )
        except (TypeError, ValueError):
            tracker_game_time_ratio_status = "not_available"
        try:
            projected_hours_at_tracker_median_wave = (
                float(projected_duration) * float(observed_median_wave)
            ) / 3600.0
            if effective_game_speed_multiplier and effective_game_speed_multiplier > 0.0:
                projected_hours_at_tracker_median_wave /= float(effective_game_speed_multiplier)
        except (TypeError, ValueError):
            projected_hours_at_tracker_median_wave = None
        try:
            wave_skip_multiplier = 1.0 + (max(0.0, float(wave_skip_pct or 0.0)) / 100.0)
            mastery_double_chance = max(0.0, float(wave_skip_mastery_pct or 0.0)) / 100.0
            expected_skip_multiplier = wave_skip_multiplier * (1.0 + mastery_double_chance)
            intro_waves = min(max(0.0, float(intro_sprint_waves or 0.0)), max(0.0, float(observed_median_wave)))
            skip_adjusted_played_waves_at_tracker_median_wave = max(
                0.0,
                (float(observed_median_wave) - intro_waves) / expected_skip_multiplier,
            )
            expected_skipped_waves_at_tracker_median_wave = max(
                0.0,
                float(observed_median_wave) - intro_waves - skip_adjusted_played_waves_at_tracker_median_wave,
            )
            observed_non_intro_displayed_waves = max(
                0.0,
                float(observed_median_wave) - intro_waves,
            )
            if observed_skipped_waves_median is not None:
                observed_played_waves_after_intro_from_tracker = max(
                    0.0,
                    observed_non_intro_displayed_waves - float(observed_skipped_waves_median),
                )
                observed_skipped_waves_after_intro_if_tracker_includes_intro = max(
                    0.0,
                    float(observed_skipped_waves_median) - intro_waves,
                )
                observed_played_waves_after_intro_if_tracker_skips_include_intro = max(
                    0.0,
                    observed_non_intro_displayed_waves
                    - observed_skipped_waves_after_intro_if_tracker_includes_intro,
                )
                if observed_played_waves_after_intro_from_tracker > 0.0:
                    observed_effective_skip_multiplier_after_intro = (
                        observed_non_intro_displayed_waves
                        / observed_played_waves_after_intro_from_tracker
                    )
                    implied_wave_skip_chance_if_no_mastery_pct = max(
                        0.0,
                        (observed_effective_skip_multiplier_after_intro - 1.0) * 100.0,
                    )
                    if wave_skip_multiplier > 0.0:
                        implied_wave_skip_mastery_double_chance_pct = max(
                            0.0,
                            (
                                (observed_effective_skip_multiplier_after_intro / wave_skip_multiplier)
                                - 1.0
                            )
                            * 100.0,
                        )
                    if expected_skip_multiplier > 0.0:
                        observed_to_expected_skip_multiplier_ratio = (
                            observed_effective_skip_multiplier_after_intro / expected_skip_multiplier
                        )
                if observed_played_waves_after_intro_if_tracker_skips_include_intro > 0.0:
                    observed_effective_skip_multiplier_after_intro_if_tracker_skips_include_intro = (
                        observed_non_intro_displayed_waves
                        / observed_played_waves_after_intro_if_tracker_skips_include_intro
                    )
                    if expected_skip_multiplier > 0.0:
                        observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro = (
                            observed_effective_skip_multiplier_after_intro_if_tracker_skips_include_intro
                            / expected_skip_multiplier
                        )
                raw_exceeds_expected = (
                    observed_effective_skip_multiplier_after_intro is not None
                    and expected_skip_multiplier > 0.0
                    and observed_effective_skip_multiplier_after_intro > expected_skip_multiplier
                )
                intro_inclusive_reduces_gap = (
                    observed_to_expected_skip_multiplier_ratio is not None
                    and observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro is not None
                    and observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro
                    < observed_to_expected_skip_multiplier_ratio
                )
                skip_semantics_gap_status = (
                    "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap"
                    if raw_exceeds_expected and intro_inclusive_reduces_gap
                    else "tracker_skips_exceed_known_wave_skip_mastery_gated_state"
                    if raw_exceeds_expected
                    else "tracker_skips_within_known_wave_skip_expectation"
                )
            if effective_game_speed_multiplier and effective_game_speed_multiplier > 0.0:
                skip_adjusted_projected_hours_at_tracker_median_wave = (
                    skip_adjusted_played_waves_at_tracker_median_wave
                    * float(projected_duration)
                    / 3600.0
                    / float(effective_game_speed_multiplier)
                )
        except (TypeError, ValueError):
            skip_adjusted_projected_hours_at_tracker_median_wave = None
            skip_adjusted_played_waves_at_tracker_median_wave = None
            expected_skipped_waves_at_tracker_median_wave = None
            observed_non_intro_displayed_waves = None
            observed_played_waves_after_intro_from_tracker = None
            observed_effective_skip_multiplier_after_intro = None
            observed_skipped_waves_after_intro_if_tracker_includes_intro = None
            observed_played_waves_after_intro_if_tracker_skips_include_intro = None
            observed_effective_skip_multiplier_after_intro_if_tracker_skips_include_intro = None
            observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro = None
            implied_wave_skip_chance_if_no_mastery_pct = None
            implied_wave_skip_mastery_double_chance_pct = None
            observed_to_expected_skip_multiplier_ratio = None
            skip_semantics_gap_status = "not_available"
        try:
            if observed_median_wave is not None and float(observed_median_wave) > 0.0:
                if observed_skipped_waves_median is not None:
                    observed_skip_ratio = float(observed_skipped_waves_median) / float(observed_median_wave)
                if expected_skipped_waves_at_tracker_median_wave is not None:
                    expected_skip_ratio = expected_skipped_waves_at_tracker_median_wave / float(observed_median_wave)
        except (TypeError, ValueError):
            observed_skip_ratio = None
            expected_skip_ratio = None
        try:
            if projected_hours_at_tracker_median_wave is not None and float(observed_median_duration_hours) > 0.0:
                run_duration_ratio = projected_hours_at_tracker_median_wave / float(
                    observed_median_duration_hours
                )
        except (TypeError, ValueError):
            run_duration_ratio = None
        try:
            if (
                skip_adjusted_projected_hours_at_tracker_median_wave is not None
                and float(observed_median_duration_hours) > 0.0
            ):
                skip_adjusted_duration_ratio = skip_adjusted_projected_hours_at_tracker_median_wave / float(
                    observed_median_duration_hours
                )
        except (TypeError, ValueError):
            skip_adjusted_duration_ratio = None
        skip_semantics_inference = {
            "status": "not_available",
            "application": "external_observation_not_account_truth",
            "certification_effect": "none",
        }
        candidate_distances: dict[str, float] = {}
        try:
            if observed_to_expected_skip_multiplier_ratio is not None:
                candidate_distances["tracker_skips_exclude_intro_sprint"] = abs(
                    float(observed_to_expected_skip_multiplier_ratio) - 1.0
                )
            if observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro is not None:
                candidate_distances["tracker_skips_include_intro_sprint"] = abs(
                    float(observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro)
                    - 1.0
                )
        except (TypeError, ValueError):
            candidate_distances = {}
        if candidate_distances:
            best_candidate = min(candidate_distances, key=lambda key: candidate_distances[key])
            best_distance = candidate_distances[best_candidate]
            exclude_distance = candidate_distances.get("tracker_skips_exclude_intro_sprint")
            include_distance = candidate_distances.get("tracker_skips_include_intro_sprint")
            support_ratio = None
            try:
                if include_distance is not None and exclude_distance is not None and include_distance > 0.0:
                    support_ratio = exclude_distance / include_distance
            except (TypeError, ValueError, ZeroDivisionError):
                support_ratio = None
            skip_semantics_inference = {
                "status": (
                    "suggests_tracker_skips_include_intro_sprint"
                    if best_candidate == "tracker_skips_include_intro_sprint"
                    and best_distance <= 0.10
                    else "suggests_tracker_skips_exclude_intro_sprint"
                    if best_candidate == "tracker_skips_exclude_intro_sprint"
                    and best_distance <= 0.10
                    else "no_close_candidate"
                ),
                "application": "external_observation_not_account_truth",
                "certification_effect": "none",
                "best_candidate": best_candidate,
                "best_candidate_distance_from_expected": best_distance,
                "candidate_distance_from_expected": candidate_distances,
                "include_intro_support_ratio_vs_exclude": support_ratio,
                "operator_confirmation_required": True,
                "promotion_effect": "none_until_tracker_semantics_confirmed_or_approved",
                "interpretation": (
                    "Candidate is chosen by closeness to the KB/QE Wave Skip expectation; "
                    "this is evidence for review only, not tracker documentation or CPH truth."
                ),
            }
        tracker_alignment = {
            "status": (
                "tracker_t14_farming_timing_gap_quantified"
                if tracker_recent.get("row_count")
                else "tracker_supplied_without_t14_farming_band"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "recent_definition": tracker_recent.get("definition"),
            "recent_row_count": tracker_recent.get("row_count"),
            "observed_median_wave": observed_median_wave,
            "observed_median_duration_hours": observed_median_duration_hours,
            "tracker_median_game_time_hours": tracker_game_time.get("median"),
            "tracker_game_to_real_duration_ratio": (
                tracker_game_to_real_duration_ratio.get("median")
            ),
            "tracker_game_time_ratio_status": tracker_game_time_ratio_status,
            "observed_median_coins_per_hour": observed_median_coins_per_hour,
            "observed_median_waves_per_hour": tracker_waves_per_hour.get("median"),
            "tracker_reported_median_waves_per_hour": (
                tracker_reported_waves_per_hour.get("median")
            ),
            "tracker_reported_to_observed_waves_per_hour_ratio": (
                tracker_reported_to_observed_waves_per_hour_ratio.get("median")
            ),
            "tracker_waves_per_hour_consistency_status": (
                tracker_waves_per_hour_consistency_status
            ),
            "observed_median_seconds_per_wave": tracker_seconds_per_wave.get("median"),
            "projected_hours_at_tracker_median_wave": projected_hours_at_tracker_median_wave,
            "projected_over_observed_duration_ratio": run_duration_ratio,
            "skip_adjusted_played_waves_at_tracker_median_wave": (
                skip_adjusted_played_waves_at_tracker_median_wave
            ),
            "expected_skipped_waves_at_tracker_median_wave": expected_skipped_waves_at_tracker_median_wave,
            "observed_skipped_waves_median": observed_skipped_waves_median,
            "expected_skip_ratio_at_tracker_median_wave": expected_skip_ratio,
            "observed_skip_ratio_at_tracker_median_wave": observed_skip_ratio,
            "observed_non_intro_displayed_waves": observed_non_intro_displayed_waves,
            "observed_played_waves_after_intro_from_tracker": (
                observed_played_waves_after_intro_from_tracker
            ),
            "observed_effective_skip_multiplier_after_intro": (
                observed_effective_skip_multiplier_after_intro
            ),
            "tracker_waves_skipped_semantics_candidates": {
                "status": (
                    "available"
                    if observed_skipped_waves_median is not None
                    else "not_available"
                ),
                "raw_tracker_waves_skipped_median": observed_skipped_waves_median,
                "interpretation_a_tracker_skips_exclude_intro_sprint": {
                    "skipped_waves_after_intro": observed_skipped_waves_median,
                    "played_waves_after_intro": observed_played_waves_after_intro_from_tracker,
                    "effective_skip_multiplier_after_intro": (
                        observed_effective_skip_multiplier_after_intro
                    ),
                    "observed_to_expected_skip_multiplier_ratio": (
                        observed_to_expected_skip_multiplier_ratio
                    ),
                },
                "interpretation_b_tracker_skips_include_intro_sprint": {
                    "skipped_waves_after_intro": (
                        observed_skipped_waves_after_intro_if_tracker_includes_intro
                    ),
                    "played_waves_after_intro": (
                        observed_played_waves_after_intro_if_tracker_skips_include_intro
                    ),
                    "effective_skip_multiplier_after_intro": (
                        observed_effective_skip_multiplier_after_intro_if_tracker_skips_include_intro
                    ),
                    "observed_to_expected_skip_multiplier_ratio": (
                        observed_to_expected_skip_multiplier_ratio_if_tracker_skips_include_intro
                    ),
                },
                "interpretation": (
                    "Tracker wavesSkipped semantics are external-observation metadata. "
                    "If the tracker count includes Intro Sprint waves, the apparent Wave Skip gap is much smaller."
                ),
            },
            "tracker_waves_skipped_semantics_inference": skip_semantics_inference,
            "implied_wave_skip_chance_if_no_mastery_pct": (
                implied_wave_skip_chance_if_no_mastery_pct
            ),
            "implied_wave_skip_mastery_double_chance_pct_at_current_base": (
                implied_wave_skip_mastery_double_chance_pct
            ),
            "observed_to_expected_skip_multiplier_ratio": (
                observed_to_expected_skip_multiplier_ratio
            ),
            "skip_semantics_gap_status": skip_semantics_gap_status,
            "wave_skip_mastery_double_chance_pct": wave_skip_mastery_pct,
            "skip_adjusted_projected_hours_at_tracker_median_wave": (
                skip_adjusted_projected_hours_at_tracker_median_wave
            ),
            "skip_adjusted_projected_over_observed_duration_ratio": skip_adjusted_duration_ratio,
            "interpretation": (
                "Values quantify the timing calibration gap only; they do not tune the model or certify CPH."
            ),
        }
        tracker_cph_calibration = {
            "status": (
                "tracker_t14_farming_cph_band_available"
                if tracker_recent.get("row_count") and observed_median_coins_per_hour is not None
                else "tracker_supplied_without_cph_band"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "recent_definition": tracker_recent.get("definition"),
            "recent_row_count": tracker_recent.get("row_count"),
            "latest": tracker_recent.get("latest"),
            "observed_median_wave": observed_median_wave,
            "observed_median_duration_hours": observed_median_duration_hours,
            "observed_median_coins_per_run": observed_median_coins_per_run,
            "observed_median_coins_per_hour": observed_median_coins_per_hour,
            "anchor_observed_final_wave": observed_final_wave_value,
            "anchor_observed_run_hours": float(observed_run_hours),
            "anchor_observed_coins_per_hour": float(observed_coins_per_hour),
            "observed_to_anchor_wave_ratio": _ratio(
                observed_median_wave,
                float(observed_final_wave_value),
            ),
            "observed_to_anchor_duration_ratio": _ratio(
                observed_median_duration_hours,
                float(observed_run_hours),
            ),
            "observed_to_anchor_coins_per_hour_ratio": _ratio(
                observed_median_coins_per_hour,
                float(observed_coins_per_hour),
            ),
            "interpretation": (
                "Tracker CPH bands are repeatable calibration evidence only; they do not tune the model or certify CPH."
            ),
        }
        component_median_cph = tracker_component_cph.get("median")
        run_total_median_cph = tracker_run_total_cph.get("median")
        tracker_cph_identity = {
            "status": (
                "tracker_density_components_reconstruct_cph"
                if tracker_recent.get("row_count")
                and (
                    component_median_cph is not None
                    or run_total_median_cph is not None
                )
                and observed_median_coins_per_hour is not None
                else "tracker_supplied_without_density_component_cph_band"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "formula": "coins/run_duration_hours and coins_per_enemy * enemies_per_wave * waves_per_hour",
            "recent_definition": tracker_recent.get("definition"),
            "recent_row_count": tracker_recent.get("row_count"),
            "run_total_median_coins_per_hour": run_total_median_cph,
            "run_total_to_tracker_cph_ratio": _ratio(
                run_total_median_cph,
                observed_median_coins_per_hour,
            ),
            "run_total_to_tracker_reported_row_ratio_median": (
                tracker_run_total_cph_ratio.get("median")
            ),
            "observed_median_coins_per_enemy": tracker_coins_per_enemy.get("median"),
            "observed_median_enemies_per_wave": tracker_enemies_per_wave.get("median"),
            "observed_median_waves_per_hour": tracker_waves_per_hour.get("median"),
            "component_median_coins_per_hour": component_median_cph,
            "tracker_median_coins_per_hour": observed_median_coins_per_hour,
            "component_to_tracker_cph_ratio": _ratio(
                component_median_cph,
                observed_median_coins_per_hour,
            ),
            "interpretation": (
                "This proves the empirical CPH decomposition on tracker observations only; "
                "it does not provide a source-owned run-duration, spawn/kill, or coin integral."
            ),
        }
        coins_per_non_intro_displayed_wave = None
        coins_per_tracker_played_wave_after_intro = None
        try:
            if (
                observed_median_coins_per_run is not None
                and observed_non_intro_displayed_waves is not None
                and float(observed_non_intro_displayed_waves) > 0.0
            ):
                coins_per_non_intro_displayed_wave = (
                    float(observed_median_coins_per_run)
                    / float(observed_non_intro_displayed_waves)
                )
            if (
                observed_median_coins_per_run is not None
                and observed_played_waves_after_intro_from_tracker is not None
                and float(observed_played_waves_after_intro_from_tracker) > 0.0
            ):
                coins_per_tracker_played_wave_after_intro = (
                    float(observed_median_coins_per_run)
                    / float(observed_played_waves_after_intro_from_tracker)
                )
        except (TypeError, ValueError):
            coins_per_non_intro_displayed_wave = None
            coins_per_tracker_played_wave_after_intro = None
        wave_reward_source_audit["tracker_skip_count_semantics"] = {
            "status": skip_semantics_gap_status,
            "inference_status": skip_semantics_inference.get("status"),
            "best_candidate": skip_semantics_inference.get("best_candidate"),
            "best_candidate_distance_from_expected": skip_semantics_inference.get(
                "best_candidate_distance_from_expected"
            ),
            "operator_confirmation_required": skip_semantics_inference.get(
                "operator_confirmation_required"
            ),
            "raw_tracker_waves_skipped_median": observed_skipped_waves_median,
            "candidate_semantics": [
                "tracker_skips_exclude_intro_sprint",
                "tracker_skips_include_intro_sprint",
            ],
            "interpretation": (
                "Tracker wavesSkipped semantics must be resolved before the "
                "Wave Skip reward expected value can become a certified CPH input."
            ),
        }
        tracker_wave_reward = {
            "status": (
                "tracker_intro_wave_skip_reward_candidate_available"
                if tracker_recent.get("row_count")
                and coins_per_non_intro_displayed_wave is not None
                else "tracker_supplied_without_wave_reward_candidate"
            ),
            "source": run_tracker_evidence.get("source"),
            "application": run_tracker_evidence.get("application"),
            "certification_effect": "none",
            "formula": "coins_per_run over non_intro_displayed_waves and tracker_played_waves_after_intro",
            "recent_definition": tracker_recent.get("definition"),
            "recent_row_count": tracker_recent.get("row_count"),
            "intro_sprint_waves": intro_sprint_waves,
            "observed_median_wave": observed_median_wave,
            "observed_median_coins_per_run": observed_median_coins_per_run,
            "observed_skipped_waves_median": observed_skipped_waves_median,
            "coin_eligible_displayed_waves_after_intro": observed_non_intro_displayed_waves,
            "tracker_played_waves_after_intro": observed_played_waves_after_intro_from_tracker,
            "observed_effective_skip_multiplier_after_intro": (
                observed_effective_skip_multiplier_after_intro
            ),
            "coins_per_non_intro_displayed_wave": coins_per_non_intro_displayed_wave,
            "coins_per_tracker_played_wave_after_intro": (
                coins_per_tracker_played_wave_after_intro
            ),
            "tracker_reported_coins_from_wave_skip": tracker_coins_from_wave_skip.get("median"),
            "tracker_reported_coins_per_wave": tracker_coins_per_wave_reported.get("median"),
            "tracker_reported_coins_per_wave_to_observed_ratio": (
                tracker_coins_per_wave_to_observed_ratio.get("median")
            ),
            "tracker_reported_coins_per_wave_semantics_status": (
                tracker_reported_coins_per_wave_semantics_status
            ),
            "tracker_reported_wave_skip_coin_share": tracker_wave_skip_coin_share.get("median"),
            "tracker_reported_coins_per_skipped_wave": (
                tracker_wave_skip_coins_per_skipped_wave.get("median")
            ),
            "tracker_reward_field_status": (
                "tracker_wave_skip_reward_fields_available"
                if tracker_coins_from_wave_skip.get("count")
                and tracker_wave_skip_coins_per_skipped_wave.get("count")
                else "tracker_wave_skip_reward_fields_missing"
            ),
            "source_audit": wave_reward_source_audit,
            "missing_to_promote": [
                "wave_skip_coin_reward_expected_value_over_per_wave_coin_curve",
                "wave_skip_mastery_double_skip_reward_semantics",
                "tracker_waves_skipped_intro_sprint_semantics",
                "econ_window_overlap_for_skipped_and_played_waves",
            ],
            "interpretation": (
                "Candidate partitions tracker run coins across coin-eligible displayed and played waves; "
                "it does not certify Intro Sprint or Wave Skip reward semantics."
            ),
        }
        wave_skip_reward_readiness.update(
            {
                "tracker_reward_status": tracker_wave_reward.get("status"),
                "tracker_reward_field_status": tracker_wave_reward.get(
                    "tracker_reward_field_status"
                ),
                "tracker_reported_wave_skip_coin_share": tracker_wave_reward.get(
                    "tracker_reported_wave_skip_coin_share"
                ),
                "tracker_reported_coins_per_skipped_wave": tracker_wave_reward.get(
                    "tracker_reported_coins_per_skipped_wave"
                ),
                "tracker_skip_semantics_status": skip_semantics_gap_status,
                "tracker_skip_semantics_inference_status": skip_semantics_inference.get(
                    "status"
                ),
                "tracker_skip_semantics_best_candidate": skip_semantics_inference.get(
                    "best_candidate"
                ),
                "tracker_skip_semantics_best_candidate_distance_from_expected": (
                    skip_semantics_inference.get(
                        "best_candidate_distance_from_expected"
                    )
                ),
            }
        )
    approved_wave_skip_reward_closes_formula_link = (
        bool(approve_tracker_empirical_wave_skip_reward)
        and tracker_wave_reward.get("status")
        == "tracker_intro_wave_skip_reward_candidate_available"
        and tracker_wave_reward.get("tracker_reward_field_status")
        == "tracker_wave_skip_reward_fields_available"
    )
    skip_semantics_inference_for_approval = dict(
        tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
    )
    skip_semantics_best_candidate = skip_semantics_inference_for_approval.get(
        "best_candidate"
    )
    skip_semantics_best_distance = skip_semantics_inference_for_approval.get(
        "best_candidate_distance_from_expected"
    )
    try:
        skip_semantics_candidate_close = (
            skip_semantics_best_candidate
            in {
                "tracker_skips_include_intro_sprint",
                "tracker_skips_exclude_intro_sprint",
            }
            and float(skip_semantics_best_distance) <= 0.10
        )
    except (TypeError, ValueError):
        skip_semantics_candidate_close = False
    approved_tracker_wave_skip_intro_semantics_closes_blocker = (
        bool(approve_tracker_wave_skip_intro_semantics)
        and skip_semantics_candidate_close
        and str(skip_semantics_inference_for_approval.get("status") or "").startswith(
            "suggests_tracker_skips_"
        )
    )
    wave_skip_reward_readiness.update(
        {
            "certification_effect": (
                "closes_wave_skip_reward_expected_value_link_only"
                if approved_wave_skip_reward_closes_formula_link
                else "none"
            ),
            "operator_approval_required": True,
            "operator_approved_tracker_empirical_wave_skip_reward": bool(
                approve_tracker_empirical_wave_skip_reward
            ),
            "operator_approval_status": (
                "approved_explicit_runtime_input"
                if approve_tracker_empirical_wave_skip_reward
                else "not_approved"
            ),
            "approval_runtime_input": "approve_tracker_empirical_wave_skip_reward",
            "approval_policy": (
                "Explicit approval plus tracker Wave Skip reward fields closes only "
                "the Wave Skip reward expected-value formula link; it does not certify "
                "farming CPH."
            ),
            "tracker_reward_candidate_available": (
                tracker_wave_reward.get("status")
                == "tracker_intro_wave_skip_reward_candidate_available"
            ),
            "approved_reward_closes_formula_link": (
                approved_wave_skip_reward_closes_formula_link
            ),
            "tracker_skip_intro_semantics_approval": {
                "operator_approval_required": True,
                "operator_approved_tracker_wave_skip_intro_semantics": bool(
                    approve_tracker_wave_skip_intro_semantics
                ),
                "operator_approval_status": (
                    "approved_explicit_runtime_input"
                    if approve_tracker_wave_skip_intro_semantics
                    else "not_approved"
                ),
                "approval_runtime_input": (
                    "approve_tracker_wave_skip_intro_semantics"
                ),
                "approved_semantics_closes_validation_blocker": (
                    approved_tracker_wave_skip_intro_semantics_closes_blocker
                ),
                "approved_tracker_waves_skipped_semantics": (
                    skip_semantics_best_candidate
                    if approved_tracker_wave_skip_intro_semantics_closes_blocker
                    else None
                ),
                "candidate_distance_from_expected": skip_semantics_best_distance,
                "approval_policy": (
                    "Explicit approval plus a close tracker wavesSkipped semantics "
                    "inference closes only the Wave Skip/Intro Sprint tracker "
                    "semantics validation blocker; it does not certify farming CPH."
                ),
            },
        }
    )
    coins_per_hour_objective_identity = {
        "status": "source_owned_identity_available",
        "formula": "coins_per_hour = coins_per_run / run_duration_hours",
        "owner": "simulators.timing",
        "application": "objective_conversion_only_not_coin_or_duration_integral",
        "certification_effect": "closes_objective_conversion_link_only",
        "required_inputs": ["coins_per_run", "run_duration_hours"],
        "remaining_to_certify": [
            "coins_per_run_integral",
            "run_duration_integral_after_intro_sprint_wave_skip_and_game_speed",
        ],
    }
    duration_projection_ratio_to_anchor = _ratio(
        estimated_run_hours_after_wave_skip_intro_and_game_speed,
        observed_run_hours,
    )
    duration_projection_delta_hours_vs_anchor = None
    try:
        if estimated_run_hours_after_wave_skip_intro_and_game_speed is not None:
            duration_projection_delta_hours_vs_anchor = (
                float(estimated_run_hours_after_wave_skip_intro_and_game_speed)
                - float(observed_run_hours)
            )
    except (TypeError, ValueError):
        duration_projection_delta_hours_vs_anchor = None
    tracker_duration_ratio = tracker_alignment.get(
        "skip_adjusted_projected_over_observed_duration_ratio"
    )
    approved_run_duration_projection_closes_formula_link = (
        bool(approve_tracker_empirical_run_duration_projection)
        and not missing_required
        and estimated_run_hours_after_wave_skip_intro_and_game_speed is not None
        and tracker_duration_ratio is not None
    )
    duration_projection_readiness = {
        "status": (
            "timing_driver_inputs_missing"
            if missing_required
            else (
                "source_timing_projection_available_tracker_comparison_available"
                if tracker_duration_ratio is not None
                else "source_timing_projection_available_anchor_delta_reported"
            )
        ),
        "formula": (
            "played_non_intro_waves_after_expected_wave_skip * "
            "effective_wave_duration_seconds / effective_game_speed_multiplier"
        ),
        "owner": "simulators.timing",
        "application": "duration_projection_only_not_certified_cph",
        "certification_effect": (
            "closes_run_duration_link_only"
            if approved_run_duration_projection_closes_formula_link
            else "none"
        ),
        "operator_approval_required": True,
        "operator_approved_tracker_empirical_run_duration_projection": bool(
            approve_tracker_empirical_run_duration_projection
        ),
        "operator_approval_status": (
            "approved_explicit_runtime_input"
            if approve_tracker_empirical_run_duration_projection
            else "not_approved"
        ),
        "approval_runtime_input": (
            "approve_tracker_empirical_run_duration_projection"
        ),
        "approval_policy": (
            "Explicit approval plus tracker duration evidence closes only the "
            "calibrated run-duration formula link; it does not certify farming CPH."
        ),
        "tracker_duration_candidate_available": tracker_duration_ratio is not None,
        "approved_projection_closes_formula_link": (
            approved_run_duration_projection_closes_formula_link
        ),
        "source_driver_status": "available" if not missing_required else "missing_required_inputs",
        "missing_required_timing_surfaces": missing_required,
        "target_wave": target_wave,
        "intro_sprint_waves": intro_sprint_waves,
        "wave_skip_expected_skip_multiplier": estimated_wave_skip_expected_skip_multiplier,
        "estimated_played_waves_after_wave_skip_intro": (
            estimated_played_waves_after_wave_skip_intro
        ),
        "effective_wave_duration_seconds": projected_duration,
        "effective_game_speed_multiplier": effective_game_speed_multiplier,
        "projected_run_hours": estimated_run_hours_after_wave_skip_intro_and_game_speed,
        "anchor_run_hours": float(observed_run_hours),
        "projected_to_anchor_run_hours_ratio": duration_projection_ratio_to_anchor,
        "projected_delta_hours_vs_anchor": duration_projection_delta_hours_vs_anchor,
        "tracker_skip_adjusted_projected_over_observed_duration_ratio": tracker_duration_ratio,
        "remaining_to_certify": [
            "source_confirmed_wave_duration_semantics",
            "source_confirmed_intro_sprint_timing_and_coin_window_semantics",
            "source_confirmed_wave_skip_timing_reward_expected_value",
            "validation_across_tracker_exports_and_account_states",
        ],
    }
    cph_missing_formula_links = [
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed",
        "spawn_rate_to_enemy_kill_density_by_wave",
        "intro_sprint_no_coin_window_to_run_coin_integral",
        "wave_skip_reward_and_mastery_expected_value",
        "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral",
    ]
    cph_certification_blockers = list(cph_missing_formula_links)
    if approved_run_duration_projection_closes_formula_link:
        cph_missing_formula_links = [
            link
            for link in cph_missing_formula_links
            if link
            != "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        ]
        cph_certification_blockers = [
            blocker
            for blocker in cph_certification_blockers
            if blocker
            != "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        ]
    if approved_wave_skip_reward_closes_formula_link:
        cph_missing_formula_links = [
            link
            for link in cph_missing_formula_links
            if link != "wave_skip_reward_and_mastery_expected_value"
        ]
        cph_certification_blockers = [
            blocker
            for blocker in cph_certification_blockers
            if blocker != "wave_skip_reward_and_mastery_expected_value"
        ]
    if approved_intro_sprint_coin_window_closes_formula_link:
        cph_missing_formula_links = [
            link
            for link in cph_missing_formula_links
            if link != "intro_sprint_no_coin_window_to_run_coin_integral"
        ]
        cph_certification_blockers = [
            blocker
            for blocker in cph_certification_blockers
            if blocker != "intro_sprint_no_coin_window_to_run_coin_integral"
        ]
    overlap_integral_readiness = dict(
        econ_sync_window_readiness.get("overlap_integral_readiness") or {}
    )
    approved_econ_window_overlap_closes_formula_link = bool(
        overlap_integral_readiness.get("approved_overlap_closes_formula_link")
    )
    if approved_econ_window_overlap_closes_formula_link:
        cph_missing_formula_links = [
            link
            for link in cph_missing_formula_links
            if link != "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral"
        ]
        cph_certification_blockers = [
            blocker
            for blocker in cph_certification_blockers
            if blocker != "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral"
        ]
    if missing_required:
        cph_certification_blockers.append("required_timing_driver_inputs_missing")
    if tracker_alignment.get("skip_semantics_gap_status") in {
        "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap",
        "tracker_skips_exceed_known_wave_skip_mastery_gated_state",
        "not_available",
    } and not approved_tracker_wave_skip_intro_semantics_closes_blocker:
        cph_certification_blockers.append("tracker_wave_skip_intro_semantics_gap")
    spawn_density_readiness = _farming_spawn_density_readiness_summary(
        tier=observed_tier,
        target_wave=target_wave,
        wave_accelerator_spawn_rate_acceleration=wave_accelerator_spawn_rate_acceleration,
        enemy_balance_mastery_double_elite_chance_pct=enemy_balance_mastery_double_elite_chance_pct,
        run_tracker_evidence=run_tracker_evidence,
        approve_tracker_empirical_kill_density_transform=(
            approve_tracker_empirical_kill_density_transform
        ),
    )
    tracker_coin_integral = dict(
        spawn_density_readiness.get("tracker_coin_integral_candidate") or {}
    )
    tracker_kill_density = dict(
        spawn_density_readiness.get("tracker_kill_density_transform_candidate") or {}
    )
    tracker_kill_density_stability = dict(
        spawn_density_readiness.get("tracker_kill_density_stability_evidence") or {}
    )
    tracker_coin_yield_stability = dict(
        spawn_density_readiness.get("tracker_coin_yield_stability_evidence") or {}
    )
    kill_density_transform_readiness = dict(
        spawn_density_readiness.get("kill_density_transform_readiness") or {}
    )
    if bool(kill_density_transform_readiness.get("approved_transform_closes_formula_link")):
        cph_missing_formula_links = [
            link
            for link in cph_missing_formula_links
            if link != "spawn_rate_to_enemy_kill_density_by_wave"
        ]
        cph_certification_blockers = [
            blocker
            for blocker in cph_certification_blockers
            if blocker != "spawn_rate_to_enemy_kill_density_by_wave"
        ]
    cph_promotion_blockers = [
        "not_source_owned_run_coin_and_duration_integrals",
    ]
    if not approve_tracker_empirical_cph_default:
        cph_promotion_blockers.append(
            "operator_has_not_approved_tracker_empirical_cph_as_default"
        )
    if tracker_cph_calibration.get("status") != "tracker_t14_farming_cph_band_available":
        cph_promotion_blockers.append("tracker_t14_farming_cph_band_missing")
    if tracker_cph_identity.get("status") != "tracker_density_components_reconstruct_cph":
        cph_promotion_blockers.append("tracker_density_component_identity_missing")
    if tracker_kill_density.get("status") != "tracker_spawn_rate_to_kill_density_candidate_available":
        cph_promotion_blockers.append("tracker_spawn_rate_to_kill_density_candidate_missing")
    if tracker_coin_integral.get("status") != "tracker_kill_density_to_coin_integral_candidate_available":
        cph_promotion_blockers.append("tracker_kill_density_to_coin_integral_candidate_missing")
    if tracker_kill_density_stability.get("status") != "tracker_recent_prior_kill_density_transform_available":
        cph_promotion_blockers.append("recent_prior_kill_density_stability_missing")
    if tracker_coin_yield_stability.get("status") != "tracker_recent_prior_coin_yield_available":
        cph_promotion_blockers.append("recent_prior_coin_yield_stability_missing")
    if tracker_alignment.get("skip_semantics_gap_status") in {
        "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap",
        "tracker_skips_exceed_known_wave_skip_mastery_gated_state",
        "not_available",
    } and not approved_tracker_wave_skip_intro_semantics_closes_blocker:
        cph_promotion_blockers.append("tracker_wave_skip_intro_semantics_gap")
    if tracker_wave_reward.get("tracker_reward_field_status") != (
        "tracker_wave_skip_reward_fields_available"
    ):
        cph_promotion_blockers.append("tracker_wave_skip_reward_fields_missing")
    tracker_econ_source_evidence = dict(
        econ_sync_window_readiness.get("tracker_econ_coin_source_evidence") or {}
    )
    if tracker_econ_source_evidence.get("status") != "tracker_econ_coin_sources_available":
        cph_promotion_blockers.append("tracker_econ_coin_source_fields_missing")
    if not approved_wave_skip_reward_closes_formula_link:
        cph_promotion_blockers.append("wave_skip_reward_expected_value_missing")
    if not approved_econ_window_overlap_closes_formula_link:
        cph_promotion_blockers.append("econ_window_overlap_coin_integral_missing")
    cph_promotion_blockers.append(
        "validation_across_multiple_exports_and_account_states_missing"
    )
    if run_tracker_evidence is None:
        cph_validation_basis = "no_tracker_export_supplied"
    elif (
        tracker_kill_density_stability.get("status")
        == "tracker_recent_prior_kill_density_transform_available"
        and tracker_coin_yield_stability.get("status")
        == "tracker_recent_prior_coin_yield_available"
    ):
        cph_validation_basis = "tracker_t14_recent_and_prior_windows"
    else:
        cph_validation_basis = "tracker_t14_recent_window_only"
    tracker_trend = (
        dict(run_tracker_evidence.get("farming_t14_recent_trend") or {})
        if isinstance(run_tracker_evidence, Mapping)
        else {}
    )
    tracker_anchor_hint = dict(tracker_trend.get("calibration_anchor_hint") or {})
    current_estimate_target_wave = target_wave
    if observed_final_wave_supplied and observed_final_wave_value > 0:
        current_estimate_target_wave = observed_final_wave_value
    (
        current_estimate_run_hours,
        current_estimate_played_waves,
        current_estimate_skipped_waves,
    ) = _estimate_run_hours_for_target_wave(current_estimate_target_wave)
    current_estimate_coin_eligible_waves = None
    try:
        current_estimate_target_wave_value = max(0.0, float(current_estimate_target_wave))
        current_estimate_intro_waves = min(
            max(0.0, float(intro_sprint_waves or 0.0)),
            current_estimate_target_wave_value,
        )
        current_estimate_coin_eligible_waves = max(
            0.0,
            current_estimate_target_wave_value - current_estimate_intro_waves,
        )
    except (TypeError, ValueError):
        current_estimate_coin_eligible_waves = None
    current_timing_run_hours = _positive_float(
        current_estimate_run_hours
        if current_estimate_run_hours is not None
        else estimated_run_hours_after_wave_skip_intro_and_game_speed
    )
    target_wave_value = _positive_float(current_estimate_target_wave)
    current_displayed_waves_per_hour = None
    if current_timing_run_hours is not None and target_wave_value is not None:
        current_displayed_waves_per_hour = target_wave_value / current_timing_run_hours
    median_projected_coins_per_wave = _positive_float(
        tracker_coin_integral.get("projected_coins_per_wave_from_tracker_density")
    )
    latest_projected_coins_per_wave = _positive_float(
        tracker_coin_integral.get("latest_projected_coins_per_wave_from_tracker_density")
    )
    median_current_timing_coins_per_run = None
    median_current_timing_coins_per_hour = None
    latest_current_timing_coins_per_run = None
    latest_current_timing_coins_per_hour = None
    latest_intro_excluded_coins_per_run = None
    latest_intro_excluded_coins_per_hour = None
    latest_wave_horizon_run_hours = None
    latest_wave_horizon_coins_per_run = None
    latest_wave_horizon_coins_per_hour = None
    latest_wave_horizon_intro_excluded_coins_per_run = None
    latest_wave_horizon_intro_excluded_coins_per_hour = None
    latest_observed_wave_value = _positive_float(tracker_coin_integral.get("latest_wave"))
    try:
        if median_projected_coins_per_wave is not None and target_wave_value is not None:
            median_current_timing_coins_per_run = (
                median_projected_coins_per_wave * target_wave_value
            )
            if current_timing_run_hours is not None:
                median_current_timing_coins_per_hour = (
                    median_current_timing_coins_per_run / current_timing_run_hours
                )
        if latest_projected_coins_per_wave is not None and target_wave_value is not None:
            latest_current_timing_coins_per_run = (
                latest_projected_coins_per_wave * target_wave_value
            )
            if current_timing_run_hours is not None:
                latest_current_timing_coins_per_hour = (
                    latest_current_timing_coins_per_run / current_timing_run_hours
                )
            if current_estimate_coin_eligible_waves is not None:
                latest_intro_excluded_coins_per_run = (
                    latest_projected_coins_per_wave
                    * float(current_estimate_coin_eligible_waves)
                )
                if current_timing_run_hours is not None:
                    latest_intro_excluded_coins_per_hour = (
                        latest_intro_excluded_coins_per_run / current_timing_run_hours
                    )
        if (
            latest_projected_coins_per_wave is not None
            and latest_observed_wave_value is not None
            and projected_duration is not None
            and effective_game_speed_multiplier is not None
            and float(effective_game_speed_multiplier) > 0.0
        ):
            latest_horizon_intro_waves = min(
                max(0.0, float(intro_sprint_waves or 0.0)),
                latest_observed_wave_value,
            )
            latest_horizon_skip_multiplier = (
                float(estimated_wave_skip_expected_skip_multiplier)
                if estimated_wave_skip_expected_skip_multiplier is not None
                else 1.0
            )
            if latest_horizon_skip_multiplier <= 0.0:
                latest_horizon_skip_multiplier = 1.0
            latest_horizon_played_waves = max(
                0.0,
                (latest_observed_wave_value - latest_horizon_intro_waves)
                / latest_horizon_skip_multiplier,
            )
            latest_wave_horizon_run_hours = (
                latest_horizon_played_waves
                * float(projected_duration)
                / 3600.0
                / float(effective_game_speed_multiplier)
            )
            latest_wave_horizon_coins_per_run = (
                latest_projected_coins_per_wave * latest_observed_wave_value
            )
            if latest_wave_horizon_run_hours > 0.0:
                latest_wave_horizon_coins_per_hour = (
                    latest_wave_horizon_coins_per_run / latest_wave_horizon_run_hours
                )
            latest_wave_horizon_intro_excluded_coins_per_run = (
                latest_projected_coins_per_wave
                * max(0.0, latest_observed_wave_value - latest_horizon_intro_waves)
            )
            if latest_wave_horizon_run_hours > 0.0:
                latest_wave_horizon_intro_excluded_coins_per_hour = (
                    latest_wave_horizon_intro_excluded_coins_per_run
                    / latest_wave_horizon_run_hours
                )
    except (TypeError, ValueError):
        median_current_timing_coins_per_run = None
        median_current_timing_coins_per_hour = None
        latest_current_timing_coins_per_run = None
        latest_current_timing_coins_per_hour = None
        latest_intro_excluded_coins_per_run = None
        latest_intro_excluded_coins_per_hour = None
        latest_wave_horizon_run_hours = None
        latest_wave_horizon_coins_per_run = None
        latest_wave_horizon_coins_per_hour = None
        latest_wave_horizon_intro_excluded_coins_per_run = None
        latest_wave_horizon_intro_excluded_coins_per_hour = None
    selected_cph_basis = None
    selected_cph = None
    selected_coins_per_run = None
    selected_coins_per_wave = None
    if latest_current_timing_coins_per_hour is not None:
        selected_cph_basis = "latest_tracker_coin_density_current_timing"
        selected_cph = latest_current_timing_coins_per_hour
        selected_coins_per_run = latest_current_timing_coins_per_run
        selected_coins_per_wave = latest_projected_coins_per_wave
    elif median_current_timing_coins_per_hour is not None:
        selected_cph_basis = "recent_median_tracker_coin_density_current_timing"
        selected_cph = median_current_timing_coins_per_hour
        selected_coins_per_run = median_current_timing_coins_per_run
        selected_coins_per_wave = median_projected_coins_per_wave
    current_coin_density_cph_estimate = {
        "status": (
            "tracker_coin_density_current_timing_calculator_available"
            if selected_cph is not None
            else "not_available"
        ),
        "application": "calculator_estimate_not_account_truth",
        "basis": selected_cph_basis,
        "formula": (
            "coins_per_hour = tracker_density_coins_per_wave * "
            "target_displayed_waves / current_timing_run_hours"
        ),
        "target_wave": current_estimate_target_wave,
        "statbook_target_wave": target_wave,
        "current_estimate_played_waves_after_wave_skip_intro": (
            current_estimate_played_waves
        ),
        "current_estimate_expected_skipped_waves": current_estimate_skipped_waves,
        "current_estimate_coin_eligible_displayed_waves_after_intro": (
            current_estimate_coin_eligible_waves
        ),
        "current_timing_run_hours": current_timing_run_hours,
        "current_displayed_waves_per_hour": current_displayed_waves_per_hour,
        "selected_projected_coins_per_wave": selected_coins_per_wave,
        "selected_projected_coins_per_run": selected_coins_per_run,
        "selected_projected_coins_per_hour": selected_cph,
        "latest_observed_wave": tracker_coin_integral.get("latest_wave"),
        "latest_observed_coins_per_enemy": tracker_coin_integral.get(
            "latest_observed_coins_per_enemy"
        ),
        "latest_observed_enemies_per_wave": tracker_coin_integral.get(
            "latest_observed_enemies_per_wave"
        ),
        "latest_observed_waves_per_hour": tracker_coin_integral.get(
            "latest_observed_waves_per_hour"
        ),
        "latest_density_tracker_run_coins_per_hour": tracker_coin_integral.get(
            "latest_projected_coins_per_hour_from_tracker_density"
        ),
        "latest_run_total_coins_per_hour": tracker_coin_integral.get(
            "latest_run_total_coins_per_hour"
        ),
        "latest_projected_coins_per_wave": latest_projected_coins_per_wave,
        "latest_current_timing_projected_coins_per_run": (
            latest_current_timing_coins_per_run
        ),
        "latest_current_timing_projected_coins_per_hour": (
            latest_current_timing_coins_per_hour
        ),
        "latest_intro_excluded_projected_coins_per_run": (
            latest_intro_excluded_coins_per_run
        ),
        "latest_intro_excluded_projected_coins_per_hour": (
            latest_intro_excluded_coins_per_hour
        ),
        "latest_tracker_wave_horizon": latest_observed_wave_value,
        "latest_tracker_wave_horizon_current_timing_run_hours": (
            latest_wave_horizon_run_hours
        ),
        "latest_tracker_wave_horizon_projected_coins_per_run": (
            latest_wave_horizon_coins_per_run
        ),
        "latest_tracker_wave_horizon_projected_coins_per_hour": (
            latest_wave_horizon_coins_per_hour
        ),
        "latest_tracker_wave_horizon_intro_excluded_projected_coins_per_run": (
            latest_wave_horizon_intro_excluded_coins_per_run
        ),
        "latest_tracker_wave_horizon_intro_excluded_projected_coins_per_hour": (
            latest_wave_horizon_intro_excluded_coins_per_hour
        ),
        "median_projected_coins_per_wave": median_projected_coins_per_wave,
        "median_current_timing_projected_coins_per_run": (
            median_current_timing_coins_per_run
        ),
        "median_current_timing_projected_coins_per_hour": (
            median_current_timing_coins_per_hour
        ),
        "tracker_median_density_coins_per_hour": tracker_coin_integral.get(
            "projected_coins_per_hour_from_tracker_density"
        ),
        "tracker_median_reported_coins_per_hour": tracker_coin_integral.get(
            "tracker_median_coins_per_hour"
        ),
        "interpretation": (
            "Automatic calculator estimate uses latest tracker coin density when present, "
            "then applies the current timing projection. Median density remains visible "
            "as a stability comparator."
        ),
    }
    tracker_integrated_cph_identity_available = (
        tracker_cph_calibration.get("status") == "tracker_t14_farming_cph_band_available"
        and tracker_cph_identity.get("status") == "tracker_density_components_reconstruct_cph"
        and tracker_coin_integral.get("status")
        == "tracker_kill_density_to_coin_integral_candidate_available"
        and not cph_missing_formula_links
    )
    approved_tracker_run_coin_duration_integrals_close_blocker = (
        bool(approve_tracker_empirical_run_coin_duration_integrals)
        and tracker_integrated_cph_identity_available
    )
    approved_tracker_current_export_validation_closes_blocker = (
        bool(approve_tracker_current_export_account_state_validation)
        and tracker_cph_calibration.get("status") == "tracker_t14_farming_cph_band_available"
        and tracker_cph_identity.get("status") == "tracker_density_components_reconstruct_cph"
        and tracker_alignment.get("tracker_waves_per_hour_consistency_status")
        == "tracker_reported_waves_per_hour_matches_duration"
        and tracker_alignment.get("tracker_game_time_ratio_status")
        == "tracker_game_time_ratio_available"
    )
    if approved_tracker_run_coin_duration_integrals_close_blocker:
        cph_promotion_blockers = [
            blocker
            for blocker in cph_promotion_blockers
            if blocker != "not_source_owned_run_coin_and_duration_integrals"
        ]
    if approved_tracker_current_export_validation_closes_blocker:
        cph_promotion_blockers = [
            blocker
            for blocker in cph_promotion_blockers
            if blocker != "validation_across_multiple_exports_and_account_states_missing"
        ]
    cph_promotion_status = (
        "ready_with_approved_tracker_empirical_cph_model"
        if not cph_promotion_blockers
        else "not_ready"
    )
    coins_per_hour_promotion_readiness = {
        "status": cph_promotion_status,
        "application": "diagnostic_only_not_account_truth",
        "default_cph_derived": False,
        "operator_approval_required": True,
        "operator_approved_tracker_empirical_cph_default": bool(
            approve_tracker_empirical_cph_default
        ),
        "operator_approval_status": (
            "approved_explicit_runtime_input"
            if approve_tracker_empirical_cph_default
            else "not_approved"
        ),
        "approval_runtime_input": "approve_tracker_empirical_farming_cph",
        "approval_policy": (
            "Explicit approval removes only the operator-approval blocker; "
            "source-owned or tracker-backed formula validation blockers still apply."
        ),
        "run_coin_duration_integral_approval": {
            "operator_approval_required": True,
            "operator_approved_tracker_empirical_run_coin_duration_integrals": bool(
                approve_tracker_empirical_run_coin_duration_integrals
            ),
            "operator_approval_status": (
                "approved_explicit_runtime_input"
                if approve_tracker_empirical_run_coin_duration_integrals
                else "not_approved"
            ),
            "approval_runtime_input": (
                "approve_tracker_empirical_run_coin_duration_integrals"
            ),
            "tracker_integrated_cph_identity_available": (
                tracker_integrated_cph_identity_available
            ),
            "approved_integrals_close_blocker": (
                approved_tracker_run_coin_duration_integrals_close_blocker
            ),
            "certification_effect": (
                "closes_run_coin_duration_integral_blocker"
                if approved_tracker_run_coin_duration_integrals_close_blocker
                else "none"
            ),
        },
        "current_export_account_state_validation_approval": {
            "operator_approval_required": True,
            "operator_approved_current_export_account_state_validation": bool(
                approve_tracker_current_export_account_state_validation
            ),
            "operator_approval_status": (
                "approved_explicit_runtime_input"
                if approve_tracker_current_export_account_state_validation
                else "not_approved"
            ),
            "approval_runtime_input": (
                "approve_tracker_current_export_account_state_validation"
            ),
            "approved_validation_closes_blocker": (
                approved_tracker_current_export_validation_closes_blocker
            ),
            "validation_basis": cph_validation_basis,
            "certification_effect": (
                "closes_current_export_account_state_validation_blocker"
                if approved_tracker_current_export_validation_closes_blocker
                else "none"
            ),
        },
        "validation_basis": cph_validation_basis,
        "blocking_reasons": cph_promotion_blockers,
        "tracker_cph_status": tracker_cph_calibration.get("status"),
        "tracker_cph_identity_status": tracker_cph_identity.get("status"),
        "tracker_run_total_cph": tracker_cph_identity.get("run_total_median_coins_per_hour"),
        "tracker_run_total_to_reported_cph_ratio": tracker_cph_identity.get(
            "run_total_to_tracker_cph_ratio"
        ),
        "tracker_run_total_to_reported_row_ratio_median": tracker_cph_identity.get(
            "run_total_to_tracker_reported_row_ratio_median"
        ),
        "tracker_kill_density_status": tracker_kill_density.get("status"),
        "tracker_kill_density_stability_status": tracker_kill_density_stability.get("status"),
        "tracker_coin_integral_status": tracker_coin_integral.get("status"),
        "tracker_coin_yield_stability_status": tracker_coin_yield_stability.get("status"),
        "tracker_wave_reward_status": tracker_wave_reward.get("status"),
        "tracker_wave_skip_reward_field_status": tracker_wave_reward.get(
            "tracker_reward_field_status"
        ),
        "tracker_reported_wave_skip_coin_share": tracker_wave_reward.get(
            "tracker_reported_wave_skip_coin_share"
        ),
        "tracker_reported_coins_per_skipped_wave": tracker_wave_reward.get(
            "tracker_reported_coins_per_skipped_wave"
        ),
        "tracker_reported_coins_from_wave_skip": tracker_wave_reward.get(
            "tracker_reported_coins_from_wave_skip"
        ),
        "tracker_reported_coins_per_wave": tracker_wave_reward.get(
            "tracker_reported_coins_per_wave"
        ),
        "tracker_reported_coins_per_wave_to_observed_ratio": tracker_wave_reward.get(
            "tracker_reported_coins_per_wave_to_observed_ratio"
        ),
        "tracker_reported_coins_per_wave_semantics_status": tracker_wave_reward.get(
            "tracker_reported_coins_per_wave_semantics_status"
        ),
        "tracker_econ_coin_source_status": tracker_econ_source_evidence.get("status"),
        "tracker_econ_coin_source_available_count": tracker_econ_source_evidence.get(
            "available_source_count"
        ),
        "tracker_econ_source_sum_to_run_coins_ratio": dict(
            tracker_econ_source_evidence.get("tracked_source_sum_to_run_coins_ratio") or {}
        ).get("median"),
        "tracker_econ_overlap_evidence_status": tracker_econ_source_evidence.get(
            "overlap_evidence_status"
        ),
        "tracker_skip_semantics_status": tracker_alignment.get("skip_semantics_gap_status"),
        "tracker_timing_status": tracker_alignment.get("status"),
        "tracker_waves_per_hour_consistency_status": tracker_alignment.get(
            "tracker_waves_per_hour_consistency_status"
        ),
        "tracker_game_time_ratio_status": tracker_alignment.get(
            "tracker_game_time_ratio_status"
        ),
        "tracker_median_game_time_hours": tracker_alignment.get(
            "tracker_median_game_time_hours"
        ),
        "tracker_game_to_real_duration_ratio": tracker_alignment.get(
            "tracker_game_to_real_duration_ratio"
        ),
        "tracker_reported_median_waves_per_hour": tracker_alignment.get(
            "tracker_reported_median_waves_per_hour"
        ),
        "tracker_reported_to_observed_waves_per_hour_ratio": tracker_alignment.get(
            "tracker_reported_to_observed_waves_per_hour_ratio"
        ),
        "tracker_projected_over_observed_duration_ratio": tracker_alignment.get(
            "projected_over_observed_duration_ratio"
        ),
        "tracker_skip_adjusted_projected_over_observed_duration_ratio": (
            tracker_alignment.get("skip_adjusted_projected_over_observed_duration_ratio")
        ),
        "run_duration_projection_status": duration_projection_readiness.get("status"),
        "run_duration_projected_to_anchor_ratio": duration_projection_readiness.get(
            "projected_to_anchor_run_hours_ratio"
        ),
        "run_duration_tracker_skip_adjusted_ratio": duration_projection_readiness.get(
            "tracker_skip_adjusted_projected_over_observed_duration_ratio"
        ),
        "tracker_skip_semantics_inference_status": dict(
            tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
        ).get("status"),
        "tracker_skip_semantics_best_candidate": dict(
            tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
        ).get("best_candidate"),
        "tracker_skip_semantics_best_candidate_distance_from_expected": dict(
            tracker_alignment.get("tracker_waves_skipped_semantics_inference") or {}
        ).get("best_candidate_distance_from_expected"),
        "tracker_skip_intro_semantics_approval": dict(
            wave_skip_reward_readiness.get("tracker_skip_intro_semantics_approval") or {}
        ),
        "observed_median_coins_per_hour": tracker_cph_calibration.get(
            "observed_median_coins_per_hour"
        ),
        "component_to_tracker_cph_ratio": tracker_cph_identity.get(
            "component_to_tracker_cph_ratio"
        ),
        "projected_to_tracker_cph_ratio": tracker_coin_integral.get(
            "projected_to_tracker_cph_ratio"
        ),
        "tracker_calibration_anchor_hint": tracker_anchor_hint,
        "tracker_latest_coins_per_hour": tracker_anchor_hint.get("latest_coins_per_hour"),
        "tracker_recent_median_coins_per_hour": tracker_anchor_hint.get(
            "recent_median_coins_per_hour"
        ),
        "tracker_prior_median_coins_per_hour": tracker_anchor_hint.get(
            "prior_median_coins_per_hour"
        ),
        "tracker_recent_to_prior_coins_per_hour_ratio": tracker_anchor_hint.get(
            "recent_to_prior_coins_per_hour_ratio"
        ),
        "auto_current_cph_estimate": current_coin_density_cph_estimate,
        "recent_density_to_prior_density_ratio": tracker_kill_density_stability.get(
            "median_ratio"
        ),
        "recent_coins_per_enemy_to_prior_ratio": tracker_coin_yield_stability.get(
            "coins_per_enemy_median_ratio"
        ),
        "missing_formula_links": cph_missing_formula_links,
        "interpretation": (
            "Tracker evidence can validate candidate CPH decomposition, but it is "
            "not promoted to account truth until the missing formula links are "
            "source-owned or explicitly approved as empirical defaults."
        ),
    }
    cph_final_certification_blockers = (
        list(cph_certification_blockers)
        if cph_certification_blockers
        else list(cph_promotion_blockers)
    )
    cph_certified = not cph_final_certification_blockers
    cph_certification_status = (
        "certified_tracker_empirical_cph_model"
        if cph_certified
        else (
            "not_certified_pending_empirical_validation"
            if not cph_missing_formula_links
            else "not_certified_missing_formula_links"
        )
    )

    return {
        "status": (
            "timing_drivers_available_formula_not_certified"
            if not missing_required
            else "timing_driver_inputs_missing"
        ),
        "objective": "coins_per_hour",
        "coins_per_hour_certification_status": cph_certification_status,
        "coins_per_hour_objective_identity": coins_per_hour_objective_identity,
        "run_duration_projection_readiness": duration_projection_readiness,
        "wave_skip_reward_readiness": wave_skip_reward_readiness,
        "intro_sprint_coin_window_readiness": intro_sprint_coin_window_readiness,
        "coins_per_hour_promotion_readiness": coins_per_hour_promotion_readiness,
        "coins_per_hour_optimization_target": True,
        "coins_per_hour_certification_blockers": cph_final_certification_blockers,
        "preset": preset_name,
        "calibration_anchor": {
            "source": "user_reported_2026-06-13",
            "tier": int(observed_tier),
            "preset": preset_name,
            "observed_final_wave": observed_final_wave_value,
            "observed_run_hours": float(observed_run_hours),
            "observed_coins_per_hour": float(observed_coins_per_hour),
            "implied_coins_per_run": coins_per_run,
            "application": "calibration_target_only_not_account_truth",
        },
        "current_timing_projection": {
            "target_farming_wave": target_wave,
            "effective_waves_per_run": effective_waves_per_run,
            "effective_wave_duration_seconds": projected_duration,
            "wave_skip_chance_pct": wave_skip_pct,
            "wave_skip_mastery_double_chance_pct": wave_skip_mastery_pct,
            "wave_skip_expected_skip_multiplier": estimated_wave_skip_expected_skip_multiplier,
            "wave_skip_expected_skipped_waves": estimated_wave_skip_expected_skipped_waves,
            "intro_sprint_waves": intro_sprint_waves,
            "base_game_speed_multiplier": game_speed,
            "max_game_speed_additive": max_game_speed,
            "effective_game_speed_multiplier_for_diagnostic": effective_game_speed_multiplier,
            "estimated_run_hours_from_current_timing": estimated_run_hours_from_current_timing,
            "estimated_run_hours_after_game_speed": estimated_run_hours_after_game_speed,
            "estimated_played_waves_after_wave_skip_intro": (
                estimated_played_waves_after_wave_skip_intro
            ),
            "estimated_run_hours_after_wave_skip_intro_and_game_speed": (
                estimated_run_hours_after_wave_skip_intro_and_game_speed
            ),
            "observed_run_hours": float(observed_run_hours),
        },
        "tracker_timing_alignment": tracker_alignment,
        "tracker_cph_calibration_evidence": tracker_cph_calibration,
        "tracker_cph_identity_evidence": tracker_cph_identity,
        "tracker_wave_reward_candidate": tracker_wave_reward,
        "econ_sync_window_readiness": econ_sync_window_readiness,
        "spawn_density_readiness": spawn_density_readiness,
        "current_coin_density_cph_estimate": current_coin_density_cph_estimate,
        "timing_drivers": timing_drivers,
        "econ_window_drivers": econ_window_drivers,
        "economy_drivers": economy_drivers,
        "driver_coverage": {
            "available": sum(1 for driver in all_drivers if bool(driver["available"])),
            "total": len(all_drivers),
            "missing_required_timing_surfaces": missing_required,
        },
        "kb_reward_semantics_required_for_formula": [
            "Intro Sprint active waves produce no coins",
            "Wave Skip can award prior-wave coins and cash at x1.10",
            "Wave Skip Mastery can double wave skips",
            "Wave Accelerator Mastery shifts spawn-rate thresholds earlier",
            "game speed and Max Game Speed perk must convert wave duration to real elapsed time",
            "spawn-rate ramp must be converted to kill density before coins/hour certification",
        ],
        "missing_formula_links": cph_missing_formula_links,
        "optimizer_policy": "farming_should_optimize_coins_per_hour_not_longest_wave",
        "certified_farming_cph_model": cph_certified,
    }
