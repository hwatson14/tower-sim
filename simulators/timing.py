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
    speed_remaining = max(0.01, (1.0 - cf_average_slow) * (1.0 - slow_aura))
    energy_net_hold = max(0.0, float(energy_net_duration_seconds or 0.0))
    contact_time = (resolved_base_seconds / speed_remaining) + energy_net_hold
    return (
        contact_time,
        source,
        {
            'base_seconds': resolved_base_seconds,
            'base_seconds_source': base_seconds_source,
            'chrono_field_average_slow_fraction': cf_average_slow,
            'slow_aura_fraction': slow_aura,
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
