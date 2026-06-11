from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


GEOMETRY_SCHEMA_VERSION = 1
GEOMETRY_ENGINE_ID = "simulators.geometry"
GEOMETRY_STATUS_RESOLVED = "resolved_displayed_proxy"
GEOMETRY_STATUS_PARTIAL = "partial_displayed_proxy"
GEOMETRY_STATUS_MISSING_RANGE = "unresolved_missing_tower_range_theoretical_m"

TOWER_DISPLAYED_BREAKPOINT_M = 80.0
TOWER_DISPLAYED_SLOPE_AFTER_BREAKPOINT = 0.75678429
TOWER_DISPLAYED_INTERCEPT_AFTER_BREAKPOINT = 22.52263342
BLACK_HOLE_CENTER_DISTANCE_FACTOR = 0.85
BLACK_HOLE_DIAMETER_DISPLAY_FACTOR = 1.33
GEOMETRY_REFERENCE_TOWER_RANGE_M = 69.5
BOSS_CONTACT_REFERENCE_SECONDS = 2.0
DEFAULT_GEOMETRY_EXPOSURE_SAMPLES = 720

_TOWER_RANGE_ALIASES = (
    "state::tower.range_m",
    "canonical_stat::tower_range_m",
    "tower_range_m",
)
_BLACK_HOLE_SIZE_ALIASES = (
    "state::uw.black_hole.size_m",
    "mechanic_param::uw.black_hole.size_m",
    "runtime_mechanic_param::uw.black_hole.size_m",
)
_CHRONO_FIELD_RANGE_ALIASES = (
    "state::uw.chrono_field.range_m",
    "mechanic_param::uw.chrono_field.range_m",
    "runtime_mechanic_param::uw.chrono_field.range_m",
)
_GOLDEN_BOT_RANGE_ALIASES = (
    "runtime_mechanic_param::bot.golden_bot.range_meters",
    "state::bot.golden.range_m",
    "mechanic_param::bot.golden.range_m",
    "runtime_mechanic_param::bot.golden.range_m",
)
_GOLDEN_BOT_OWNED_ALIASES = (
    "state::bot.golden.owned",
    "capability::bot.golden.owned",
)
_SPOTLIGHT_COUNT_ALIASES = (
    "state::uw.spotlight.count",
    "mechanic_param::uw.spotlight.count",
    "runtime_mechanic_param::uw.spotlight.count",
    "mechanic_param::uw.spotlight.quantity",
)
_SPOTLIGHT_ANGLE_ALIASES = (
    "state::uw.spotlight.angle_degrees",
    "mechanic_param::uw.spotlight.angle_degrees",
    "runtime_mechanic_param::uw.spotlight.angle_degrees",
)

PROXY_ALLOWED_USES = (
    "coverage_proxy_weighting",
    "overlap_proxy_weighting",
    "relative_exposure_comparison",
    "range_sensitive_contact_time_proxy_base",
    "diagnostic_reporting",
)
PROXY_BLOCKED_USES = (
    "boss_contact_time_truth",
    "wall_contact_truth",
    "effective_damage_reduction_truth",
    "tagged_enemy_fraction_truth",
    "density_weighted_coin_truth",
    "exact_boss_path_modulation",
    "wall_contact_scaffold_truth",
)


def clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _nonnegative_float(value: Any) -> float:
    parsed = _finite_float(value)
    if parsed is None:
        return 0.0
    return max(0.0, parsed)


def _row_final_value(row: Any) -> Any:
    if isinstance(row, Mapping):
        return row.get("final_value")
    return getattr(row, "final_value", row)


def _lookup_number(row_map: Mapping[str, Any], aliases: Iterable[str]) -> tuple[float | None, str | None]:
    for surface_id in aliases:
        if surface_id not in row_map:
            continue
        value = _finite_float(_row_final_value(row_map[surface_id]))
        if value is not None:
            return value, surface_id
    return None, None


def _lookup_bool(row_map: Mapping[str, Any], aliases: Iterable[str]) -> tuple[bool | None, str | None]:
    for surface_id in aliases:
        if surface_id not in row_map:
            continue
        value = _row_final_value(row_map[surface_id])
        if isinstance(value, bool):
            return value, surface_id
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"true", "yes", "1", "owned"}:
                return True, surface_id
            if normalized in {"false", "no", "0", "locked", "unowned"}:
                return False, surface_id
        number = _finite_float(value)
        if number is not None:
            return number != 0.0, surface_id
    return None, None


def tower_range_displayed_from_theoretical(tower_range_theoretical_m: float) -> float:
    theoretical = _nonnegative_float(tower_range_theoretical_m)
    if theoretical <= TOWER_DISPLAYED_BREAKPOINT_M:
        return theoretical
    return (
        TOWER_DISPLAYED_SLOPE_AFTER_BREAKPOINT * theoretical
        + TOWER_DISPLAYED_INTERCEPT_AFTER_BREAKPOINT
    )


def tower_range_theoretical_from_displayed(tower_range_displayed_m: float) -> float:
    displayed = _nonnegative_float(tower_range_displayed_m)
    if displayed <= TOWER_DISPLAYED_BREAKPOINT_M:
        return displayed
    return (displayed - TOWER_DISPLAYED_INTERCEPT_AFTER_BREAKPOINT) / TOWER_DISPLAYED_SLOPE_AFTER_BREAKPOINT


def wall_radius_displayed_from_tower_displayed(tower_range_displayed_m: float) -> float:
    return 0.2202 * _nonnegative_float(tower_range_displayed_m) + 10.075


def boss_wall_travel_displayed_proxy_from_tower_range(
    *,
    tower_range_theoretical_m: object,
    reference_tower_range_theoretical_m: float = GEOMETRY_REFERENCE_TOWER_RANGE_M,
    reference_contact_time_seconds: float = BOSS_CONTACT_REFERENCE_SECONDS,
) -> dict[str, Any]:
    tower_range = _finite_float(tower_range_theoretical_m)
    reference_range = _finite_float(reference_tower_range_theoretical_m)
    reference_seconds = _finite_float(reference_contact_time_seconds)
    if tower_range is None or tower_range <= 0.0:
        return {
            "status": "blocked_missing_tower_range_theoretical_m",
            "truth_status": "blocked_not_wall_contact_truth",
        }
    if reference_range is None or reference_range <= 0.0 or reference_seconds is None or reference_seconds < 0.0:
        return {
            "status": "blocked_invalid_reference_contact_time",
            "truth_status": "blocked_not_wall_contact_truth",
            "tower_range_theoretical_m": tower_range,
        }

    tower_displayed = tower_range_displayed_from_theoretical(tower_range)
    wall_radius = wall_radius_displayed_from_tower_displayed(tower_displayed)
    path_to_wall = max(0.0, tower_displayed - wall_radius)
    reference_displayed = tower_range_displayed_from_theoretical(reference_range)
    reference_wall_radius = wall_radius_displayed_from_tower_displayed(reference_displayed)
    reference_path_to_wall = max(0.0, reference_displayed - reference_wall_radius)
    if reference_path_to_wall <= 0.0:
        return {
            "status": "blocked_invalid_reference_path_distance",
            "truth_status": "blocked_not_wall_contact_truth",
            "tower_range_theoretical_m": tower_range,
            "tower_range_displayed_m": tower_displayed,
            "wall_radius_displayed_m": wall_radius,
            "boss_path_distance_to_wall_displayed_candidate_m": path_to_wall,
        }

    contact_seconds = reference_seconds * (path_to_wall / reference_path_to_wall)
    return {
        "status": "resolved_displayed_proxy_candidate",
        "truth_status": "displayed_proxy_candidate_not_wall_contact_truth",
        "timing_use": "default_base_candidate_only_manual_override_wins",
        "tower_range_theoretical_m": tower_range,
        "tower_range_displayed_m": tower_displayed,
        "wall_radius_displayed_m": wall_radius,
        "boss_path_distance_to_tower_displayed_candidate_m": tower_displayed,
        "boss_path_distance_to_wall_displayed_candidate_m": path_to_wall,
        "reference_tower_range_theoretical_m": reference_range,
        "reference_tower_range_displayed_m": reference_displayed,
        "reference_wall_radius_displayed_m": reference_wall_radius,
        "reference_path_distance_to_wall_displayed_m": reference_path_to_wall,
        "reference_contact_time_seconds": reference_seconds,
        "boss_contact_time_displayed_proxy_seconds": contact_seconds,
    }


def regular_orb_radius_displayed_from_tower_displayed(tower_range_displayed_m: float) -> float:
    return 0.3856 * _nonnegative_float(tower_range_displayed_m) + 46.853


def extra_orb_radius_displayed_from_tower_displayed(tower_range_displayed_m: float) -> float:
    return 0.3542 * _nonnegative_float(tower_range_displayed_m) + 40.635


def black_hole_center_distance_displayed_from_tower_displayed(tower_range_displayed_m: float) -> float:
    return BLACK_HOLE_CENTER_DISTANCE_FACTOR * _nonnegative_float(tower_range_displayed_m)


def black_hole_displayed_diameter_from_base_and_tower_displayed(
    *,
    black_hole_base_diameter_m: float,
    tower_range_displayed_m: float,
) -> float:
    base_diameter = _nonnegative_float(black_hole_base_diameter_m)
    displayed_range = _nonnegative_float(tower_range_displayed_m)
    if base_diameter <= 0.0 or displayed_range <= 0.0:
        return 0.0
    return (
        BLACK_HOLE_DIAMETER_DISPLAY_FACTOR
        * base_diameter
        * math.sqrt(displayed_range / GEOMETRY_REFERENCE_TOWER_RANGE_M)
    )


def golden_bot_radius_displayed_from_bot_and_tower_displayed(
    *,
    golden_bot_range_m: float,
    tower_range_displayed_m: float,
) -> float:
    return (
        _nonnegative_float(golden_bot_range_m)
        * BLACK_HOLE_DIAMETER_DISPLAY_FACTOR
        * (_nonnegative_float(tower_range_displayed_m) / GEOMETRY_REFERENCE_TOWER_RANGE_M)
    )


def chrono_field_radius_displayed_from_tower_displayed(
    *,
    tower_range_displayed_m: float,
    chrono_field_range_beyond_tower_m: float,
) -> float:
    return _nonnegative_float(tower_range_displayed_m) + _nonnegative_float(chrono_field_range_beyond_tower_m)


def spotlight_angular_coverage_fraction_proxy(*, quantity: float, angle_degrees: float) -> float:
    return clamp01(_nonnegative_float(quantity) * _nonnegative_float(angle_degrees) / 360.0)


def damage_per_meter_floor_distance_m(distance_m: float) -> int:
    return max(0, int(math.floor(_nonnegative_float(distance_m))))


def circle_area(radius_m: float) -> float:
    radius = _nonnegative_float(radius_m)
    return math.pi * radius * radius


def circle_circle_overlap_area(radius_a_m: float, radius_b_m: float, center_distance_m: float) -> float:
    r0 = _nonnegative_float(radius_a_m)
    r1 = _nonnegative_float(radius_b_m)
    d = _nonnegative_float(center_distance_m)

    if r0 == 0.0 or r1 == 0.0:
        return 0.0
    if d >= r0 + r1:
        return 0.0
    if d <= abs(r0 - r1):
        return circle_area(min(r0, r1))

    x0 = clamp(-1.0, 1.0, (d * d + r0 * r0 - r1 * r1) / (2.0 * d * r0))
    x1 = clamp(-1.0, 1.0, (d * d + r1 * r1 - r0 * r0) / (2.0 * d * r1))
    term0 = r0 * r0 * math.acos(x0)
    term1 = r1 * r1 * math.acos(x1)
    term2 = 0.5 * math.sqrt(
        max(
            0.0,
            (-d + r0 + r1)
            * (d + r0 - r1)
            * (d - r0 + r1)
            * (d + r0 + r1),
        )
    )
    return term0 + term1 - term2


def clamp(lower: float, upper: float, value: float) -> float:
    return min(upper, max(lower, value))


def overlap_fraction_of_target(
    *,
    zone_radius_m: float,
    target_radius_m: float,
    center_distance_m: float,
) -> float:
    denom = circle_area(target_radius_m)
    if denom <= 0.0:
        return 0.0
    return clamp01(circle_circle_overlap_area(zone_radius_m, target_radius_m, center_distance_m) / denom)


def overlap_fraction_of_zone(
    *,
    zone_radius_m: float,
    target_radius_m: float,
    center_distance_m: float,
) -> float:
    denom = circle_area(zone_radius_m)
    if denom <= 0.0:
        return 0.0
    return clamp01(circle_circle_overlap_area(zone_radius_m, target_radius_m, center_distance_m) / denom)


def annulus_overlap_fraction_of_circle(
    *,
    circle_radius_m: float,
    annulus_inner_radius_m: float,
    annulus_outer_radius_m: float,
    circle_center_distance_m: float,
) -> float:
    inner = _nonnegative_float(annulus_inner_radius_m)
    outer = max(inner, _nonnegative_float(annulus_outer_radius_m))
    outer_overlap = circle_circle_overlap_area(circle_radius_m, outer, circle_center_distance_m)
    inner_overlap = circle_circle_overlap_area(circle_radius_m, inner, circle_center_distance_m)
    denom = circle_area(circle_radius_m)
    if denom <= 0.0:
        return 0.0
    return clamp01(max(0.0, outer_overlap - inner_overlap) / denom)


def radial_path_length_inside_offset_circle(
    *,
    zone_radius_m: float,
    zone_center_distance_m: float,
    path_heading_rad: float,
) -> float:
    radius = _nonnegative_float(zone_radius_m)
    center_distance = _nonnegative_float(zone_center_distance_m)
    if radius <= 0.0:
        return 0.0
    min_distance = abs(center_distance * math.sin(float(path_heading_rad)))
    if min_distance >= radius:
        return 0.0
    return 2.0 * math.sqrt(max(0.0, radius * radius - min_distance * min_distance))


def average_radial_path_exposure_fraction(
    *,
    zone_radius_m: float,
    zone_center_distance_m: float,
    samples: int = DEFAULT_GEOMETRY_EXPOSURE_SAMPLES,
) -> float:
    radius = _nonnegative_float(zone_radius_m)
    if radius <= 0.0:
        return 0.0
    sample_count = max(12, int(samples))
    norm = 2.0 * radius
    total = 0.0
    for index in range(sample_count):
        theta = (2.0 * math.pi * index) / sample_count
        total += radial_path_length_inside_offset_circle(
            zone_radius_m=radius,
            zone_center_distance_m=zone_center_distance_m,
            path_heading_rad=theta,
        ) / norm
    return clamp01(total / sample_count)


def ray_subtended_angle_degrees_proxy(*, zone_radius_m: float, zone_center_distance_m: float) -> float:
    radius = _nonnegative_float(zone_radius_m)
    center_distance = _nonnegative_float(zone_center_distance_m)
    if radius <= 0.0 or center_distance <= 0.0:
        return 0.0
    if radius >= center_distance:
        return 360.0
    return math.degrees(2.0 * math.asin(clamp(0.0, 1.0, radius / center_distance)))


def tower_ring_intersection_angle_degrees_proxy(
    *,
    ring_radius_m: float,
    zone_radius_m: float,
    zone_center_distance_m: float,
) -> float:
    ring_radius = _nonnegative_float(ring_radius_m)
    zone_radius = _nonnegative_float(zone_radius_m)
    center_distance = _nonnegative_float(zone_center_distance_m)
    if ring_radius <= 0.0 or zone_radius <= 0.0 or center_distance <= 0.0:
        return 0.0
    if center_distance + zone_radius < ring_radius:
        return 0.0
    if center_distance + ring_radius <= zone_radius:
        return 360.0
    if center_distance >= ring_radius + zone_radius:
        return 0.0
    cos_theta = clamp(
        -1.0,
        1.0,
        (center_distance * center_distance + ring_radius * ring_radius - zone_radius * zone_radius)
        / (2.0 * center_distance * ring_radius),
    )
    return math.degrees(2.0 * math.acos(cos_theta))


def build_geometry_proxy_governance_payload() -> dict[str, Any]:
    return {
        "artifact": "geometry_proxy_governance.json",
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "geometry_proxy_governance": {
            "status": "active",
            "owner": GEOMETRY_ENGINE_ID,
            "allowed_uses": list(PROXY_ALLOWED_USES),
            "blocked_uses": list(PROXY_BLOCKED_USES),
        },
    }


def build_geometry_consumer_interfaces_payload() -> dict[str, Any]:
    return {
        "artifact": "geometry_consumer_interfaces.json",
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "owner": GEOMETRY_ENGINE_ID,
        "interfaces": {
            "timing": {
                "status": "wired_displayed_space_and_contact_time_proxy_base",
                "safe_exports": [
                    "tower_range_displayed_m",
                    "wall_radius_displayed_m",
                    "boss_path_distance_to_wall_displayed_candidate_m",
                    "boss_contact_time_displayed_proxy_seconds",
                    "chrono_field_radius_displayed_m",
                    "black_hole_radius_displayed_m",
                    "black_hole_center_distance_displayed_m",
                    "golden_bot_radius_displayed_m",
                    "chrono_field_inbound_path_exposure_fraction_proxy",
                    "black_hole_inbound_path_exposure_fraction_proxy",
                    "golden_bot_inbound_path_exposure_fraction_proxy",
                    "black_hole_overlap_fraction_of_golden_bot",
                ],
                "blocked": [
                    "cadence_derivation",
                    "boss_contact_time_truth",
                    "effective_travel_geometry",
                ],
            },
            "survivability": {
                "status": "proxy_only",
                "safe_exports": [
                    "tower_radius_displayed_m",
                    "wall_radius_displayed_m",
                    "chrono_field_radius_displayed_m",
                    "black_hole_radius_displayed_m",
                    "black_hole_center_distance_displayed_m",
                    "black_hole_overlap_fraction_of_tower",
                    "black_hole_overlap_fraction_of_wall",
                    "chrono_field_inbound_path_exposure_fraction_proxy",
                    "ranged_enemy_inside_black_hole_fraction_proxy",
                ],
                "blocked": [
                    "wall_contact_truth",
                    "boss_hit_sequencing",
                    "exact_damage_intake_geometry",
                ],
            },
            "econ": {
                "status": "proxy_only",
                "safe_exports": [
                    "black_hole_radius_displayed_m",
                    "black_hole_center_distance_displayed_m",
                    "golden_bot_radius_displayed_m",
                    "black_hole_inbound_path_exposure_fraction_proxy",
                    "golden_bot_inbound_path_exposure_fraction_proxy",
                    "black_hole_overlap_fraction_of_golden_bot",
                    "killed_within_black_hole_fraction_proxy",
                ],
                "blocked": [
                    "exact_tagged_enemy_fraction",
                    "exact_density_weighted_coin_modelling",
                    "exact_kill_location_distribution",
                ],
            },
        },
    }


def _surface_meta(surface_type: str, truth_status: str, source_unit_system: str, evidence: str) -> dict[str, str]:
    return {
        "surface_type": surface_type,
        "truth_status": truth_status,
        "source_unit_system": source_unit_system,
        "evidence": evidence,
    }


def _base_blocked_surfaces() -> dict[str, dict[str, str]]:
    return {
        "wall_contact_radius_effective_u": {
            "surface_type": "effective",
            "status": "blocked",
            "reason": "displayed wall radius is not promoted to effective wall contact truth",
        },
        "boss_contact_time_from_geometry_seconds": {
            "surface_type": "effective",
            "status": "blocked",
            "reason": "measured boss contact time truth remains blocked; only displayed proxy base seconds may feed simulators.timing with diagnostics",
        },
        "ranged_enemy_firing_distance_m": {
            "surface_type": "effective_or_displayed",
            "status": "blocked_legacy_candidate",
            "reason": "legacy formula is not current validated truth",
        },
        "flame_bot_displayed_radius_m": {
            "surface_type": "displayed",
            "status": "blocked_unresolved_candidate",
            "reason": "Golden Bot displayed-radius formula is not generalized to non-GB bots",
        },
        "amplify_bot_displayed_radius_m": {
            "surface_type": "displayed",
            "status": "blocked_unresolved_candidate",
            "reason": "Golden Bot displayed-radius formula is not generalized to non-GB bots",
        },
        "thunder_bot_displayed_radius_m": {
            "surface_type": "displayed",
            "status": "blocked_unresolved_candidate",
            "reason": "Golden Bot displayed-radius formula is not generalized to non-GB bots",
        },
        "bot_pathing_distribution": {
            "surface_type": "runtime_pathing",
            "status": "blocked",
            "reason": "post-v28 bot movement and synchronicity need separate validation",
        },
    }


def build_geometry_payload(row_map: Mapping[str, Any], *, strict: bool = False) -> dict[str, Any]:
    tower_range, tower_source = _lookup_number(row_map, _TOWER_RANGE_ALIASES)
    if tower_range is None:
        if strict:
            raise ValueError("tower_range_theoretical_m is required to build geometry payload")
        return {
            "engine": "geometry_engine",
            "owner": GEOMETRY_ENGINE_ID,
            "schema_version": GEOMETRY_SCHEMA_VERSION,
            "status": GEOMETRY_STATUS_MISSING_RANGE,
            "input_surfaces": {},
            "surfaces": {},
            "overlaps": {},
            "encounters": {},
            "surface_metadata": {},
            "blocked_surfaces": _base_blocked_surfaces(),
            "unresolved_notes": [
                "Tower theoretical range is absent; geometry payload emitted as unresolved only.",
                "Displayed-to-effective gameplay geometry remains unresolved and is intentionally omitted.",
            ],
        }

    black_hole_size, black_hole_source = _lookup_number(row_map, _BLACK_HOLE_SIZE_ALIASES)
    chrono_range, chrono_source = _lookup_number(row_map, _CHRONO_FIELD_RANGE_ALIASES)
    golden_range, golden_source = _lookup_number(row_map, _GOLDEN_BOT_RANGE_ALIASES)
    golden_owned, golden_owned_source = _lookup_bool(row_map, _GOLDEN_BOT_OWNED_ALIASES)
    spotlight_count, spotlight_count_source = _lookup_number(row_map, _SPOTLIGHT_COUNT_ALIASES)
    spotlight_angle, spotlight_angle_source = _lookup_number(row_map, _SPOTLIGHT_ANGLE_ALIASES)

    if golden_owned is False:
        golden_range = 0.0

    input_surfaces: dict[str, dict[str, Any]] = {
        "tower_range_theoretical_m": {
            "value": tower_range,
            "source_surface_id": tower_source,
            "source_unit_system": "tower_range_theoretical_m",
            "truth_status": "qe_resolved_stat_input",
        },
    }
    optional_inputs = (
        ("black_hole_base_diameter_m", black_hole_size, black_hole_source, "black_hole_base_diameter_m"),
        ("chrono_field_range_beyond_tower_m", chrono_range, chrono_source, "chrono_field_extension_m"),
        ("golden_bot_range_m", golden_range, golden_source, "golden_bot_range_m"),
        ("golden_bot_owned", golden_owned, golden_owned_source, "boolean"),
        ("spotlight_count", spotlight_count, spotlight_count_source, "count"),
        ("spotlight_angle_degrees", spotlight_angle, spotlight_angle_source, "angle_degrees"),
    )
    for name, value, source, unit in optional_inputs:
        if source is None:
            continue
        input_surfaces[name] = {
            "value": value,
            "source_surface_id": source,
            "source_unit_system": unit,
            "truth_status": "qe_resolved_stat_input",
        }

    tower_displayed = tower_range_displayed_from_theoretical(tower_range)
    boss_wall_proxy = boss_wall_travel_displayed_proxy_from_tower_range(
        tower_range_theoretical_m=tower_range,
    )
    surfaces: dict[str, float | dict[str, float | str]] = {
        "tower_range_displayed_m": tower_displayed,
        "tower_radius_displayed_m": tower_displayed,
        "wall_radius_displayed_m": wall_radius_displayed_from_tower_displayed(tower_displayed),
        "boss_path_distance_to_tower_displayed_candidate_m": float(
            boss_wall_proxy.get("boss_path_distance_to_tower_displayed_candidate_m") or 0.0
        ),
        "boss_path_distance_to_wall_displayed_candidate_m": float(
            boss_wall_proxy.get("boss_path_distance_to_wall_displayed_candidate_m") or 0.0
        ),
        "regular_orb_radius_displayed_m": regular_orb_radius_displayed_from_tower_displayed(tower_displayed),
        "extra_orb_radius_displayed_m": extra_orb_radius_displayed_from_tower_displayed(tower_displayed),
    }
    surface_metadata = {
        "tower_range_displayed_m": _surface_meta(
            "displayed",
            "community_fit_current",
            "tower_range_theoretical_m",
            "geometry_handoff_v3:S2",
        ),
        "tower_radius_displayed_m": _surface_meta(
            "displayed",
            "community_fit_current",
            "tower_range_displayed_m",
            "geometry_handoff_v3:S2",
        ),
        "wall_radius_displayed_m": _surface_meta(
            "displayed",
            "user_supplied_advanced_analysis_image",
            "tower_range_displayed_m",
            "geometry_handoff_v3:S4",
        ),
        "boss_path_distance_to_tower_displayed_candidate_m": _surface_meta(
            "displayed_candidate",
            "proxy_scaffold_not_contact_truth",
            "tower_range_displayed_m",
            "geometry_handoff_v3:wall_contact_scaffold",
        ),
        "boss_path_distance_to_wall_displayed_candidate_m": _surface_meta(
            "displayed_candidate",
            "proxy_scaffold_not_contact_truth",
            "tower_range_displayed_m_minus_wall_radius_displayed_m",
            "geometry_handoff_v3:wall_contact_scaffold",
        ),
        "regular_orb_radius_displayed_m": _surface_meta(
            "displayed",
            "user_supplied_advanced_analysis_image",
            "tower_range_displayed_m",
            "geometry_handoff_v3:S4",
        ),
        "extra_orb_radius_displayed_m": _surface_meta(
            "displayed",
            "user_supplied_advanced_analysis_image",
            "tower_range_displayed_m",
            "geometry_handoff_v3:S4",
        ),
    }

    overlaps: dict[str, float] = {}
    encounters: dict[str, float | dict[str, Any]] = {
        "boss_wall_travel_displayed_proxy": boss_wall_proxy,
    }
    if boss_wall_proxy.get("status") == "resolved_displayed_proxy_candidate":
        encounters["boss_contact_time_displayed_proxy_seconds"] = float(
            boss_wall_proxy["boss_contact_time_displayed_proxy_seconds"]
        )
    unresolved_notes: list[str] = []

    black_hole_radius = 0.0
    black_hole_center = 0.0
    if black_hole_size is not None:
        black_hole_center = black_hole_center_distance_displayed_from_tower_displayed(tower_displayed)
        black_hole_diameter = black_hole_displayed_diameter_from_base_and_tower_displayed(
            black_hole_base_diameter_m=black_hole_size,
            tower_range_displayed_m=tower_displayed,
        )
        black_hole_radius = black_hole_diameter / 2.0
        surfaces.update(
            {
                "black_hole_center_distance_displayed_m": black_hole_center,
                "black_hole_displayed_diameter_m": black_hole_diameter,
                "black_hole_radius_displayed_m": black_hole_radius,
                "black_hole_single_zone_center_displayed_m": {"x": black_hole_center, "y": 0.0},
                "extra_black_hole_opposite_center_candidate_displayed_m": {
                    "x": -black_hole_center,
                    "y": 0.0,
                    "status": "registered_blocked_until_extra_bh_count_surface",
                },
            }
        )
        for name in (
            "black_hole_center_distance_displayed_m",
            "black_hole_displayed_diameter_m",
            "black_hole_radius_displayed_m",
        ):
            surface_metadata[name] = _surface_meta(
                "displayed",
                "community_formula_current_displayed_proxy",
                "black_hole_base_diameter_m + tower_range_displayed_m",
                "geometry_handoff_v3:S3",
            )
        overlaps.update(
            {
                "black_hole_overlap_fraction_of_tower": overlap_fraction_of_target(
                    zone_radius_m=black_hole_radius,
                    target_radius_m=tower_displayed,
                    center_distance_m=black_hole_center,
                ),
                "tower_overlap_fraction_of_black_hole": overlap_fraction_of_zone(
                    zone_radius_m=black_hole_radius,
                    target_radius_m=tower_displayed,
                    center_distance_m=black_hole_center,
                ),
                "black_hole_overlap_fraction_of_wall": overlap_fraction_of_target(
                    zone_radius_m=black_hole_radius,
                    target_radius_m=float(surfaces["wall_radius_displayed_m"]),
                    center_distance_m=black_hole_center,
                ),
                "wall_overlap_fraction_of_black_hole": overlap_fraction_of_zone(
                    zone_radius_m=black_hole_radius,
                    target_radius_m=float(surfaces["wall_radius_displayed_m"]),
                    center_distance_m=black_hole_center,
                ),
            }
        )
        encounters.update(
            {
                "black_hole_inbound_path_exposure_fraction_proxy": average_radial_path_exposure_fraction(
                    zone_radius_m=black_hole_radius,
                    zone_center_distance_m=black_hole_center,
                ),
                "black_hole_ray_subtended_angle_degrees_proxy": ray_subtended_angle_degrees_proxy(
                    zone_radius_m=black_hole_radius,
                    zone_center_distance_m=black_hole_center,
                ),
                "black_hole_intersection_angle_on_tower_ring_degrees_proxy": tower_ring_intersection_angle_degrees_proxy(
                    ring_radius_m=tower_displayed,
                    zone_radius_m=black_hole_radius,
                    zone_center_distance_m=black_hole_center,
                ),
                "killed_within_black_hole_fraction_proxy": {
                    "status": "proxy_only",
                    "source": "black_hole_inbound_path_exposure_fraction_proxy",
                    "warning": "BH coin bonus depends on enemies killed within BH, not killed by BH.",
                },
                "ranged_enemy_inside_black_hole_fraction_proxy": {
                    "status": "proxy_only",
                    "source": "black_hole_inbound_path_exposure_fraction_proxy",
                    "warning": "BH Disable Ranged Enemies may consume this proxy; it is not firing-distance truth.",
                },
            }
        )
    else:
        unresolved_notes.append("Black Hole size is absent; BH displayed surfaces and overlap proxies were omitted.")

    if chrono_range is not None:
        chrono_radius = chrono_field_radius_displayed_from_tower_displayed(
            tower_range_displayed_m=tower_displayed,
            chrono_field_range_beyond_tower_m=chrono_range,
        )
        surfaces["chrono_field_radius_displayed_m"] = chrono_radius
        surface_metadata["chrono_field_radius_displayed_m"] = _surface_meta(
            "displayed",
            "exact_wiki_stat_plus_surface_contract",
            "tower_range_displayed_m + chrono_field_range_beyond_tower_m",
            "geometry_handoff_v3:S7",
        )
        encounters["chrono_field_inbound_path_exposure_fraction_proxy"] = 1.0 if chrono_radius > 0.0 else 0.0
    else:
        unresolved_notes.append("Chrono Field range extension is absent; CF displayed radius proxy was omitted.")

    if golden_range is not None:
        golden_radius = golden_bot_radius_displayed_from_bot_and_tower_displayed(
            golden_bot_range_m=golden_range,
            tower_range_displayed_m=tower_displayed,
        )
        surfaces["golden_bot_radius_displayed_m"] = golden_radius
        surface_metadata["golden_bot_radius_displayed_m"] = _surface_meta(
            "displayed",
            "community_formula_current_displayed_proxy_golden_bot_only",
            "golden_bot_range_m + tower_range_displayed_m",
            "geometry_handoff_v3:S3/S6",
        )
        encounters["golden_bot_inbound_path_exposure_fraction_proxy"] = 1.0 if golden_radius > 0.0 else 0.0
        if black_hole_radius > 0.0:
            overlaps["black_hole_overlap_fraction_of_golden_bot"] = overlap_fraction_of_target(
                zone_radius_m=black_hole_radius,
                target_radius_m=golden_radius,
                center_distance_m=black_hole_center,
            )
            overlaps["golden_bot_overlap_fraction_of_black_hole"] = overlap_fraction_of_zone(
                zone_radius_m=black_hole_radius,
                target_radius_m=golden_radius,
                center_distance_m=black_hole_center,
            )
    else:
        unresolved_notes.append("Golden Bot range is absent; GB displayed radius proxy was omitted.")

    if spotlight_count is not None and spotlight_angle is not None:
        coverage = spotlight_angular_coverage_fraction_proxy(
            quantity=spotlight_count,
            angle_degrees=spotlight_angle,
        )
        surfaces["spotlight_radius_displayed_proxy_m"] = tower_displayed
        surfaces["spotlight_sector_area_proxy_m2"] = circle_area(tower_displayed) * coverage
        encounters["spotlight_angular_coverage_fraction_proxy"] = coverage
        for name in ("spotlight_radius_displayed_proxy_m", "spotlight_sector_area_proxy_m2"):
            surface_metadata[name] = _surface_meta(
                "derived_proxy",
                "proxy_only_until_validated",
                "tower_range_displayed_m + spotlight quantity/angle",
                "geometry_handoff_v3:S13",
            )
    else:
        unresolved_notes.append("Spotlight count or angle is absent; spotlight wedge proxy was omitted.")

    for name in overlaps:
        surface_metadata[name] = _surface_meta(
            "derived_proxy",
            "proxy_only",
            "displayed_geometry",
            "geometry_handoff_v3:derived_math",
        )
    for name, value in encounters.items():
        if isinstance(value, Mapping):
            continue
        surface_metadata[name] = _surface_meta(
            "derived_proxy",
            "proxy_only",
            "displayed_geometry",
            "geometry_handoff_v3:derived_math",
        )

    status = GEOMETRY_STATUS_RESOLVED if not unresolved_notes else GEOMETRY_STATUS_PARTIAL
    return {
        "engine": "geometry_engine",
        "owner": GEOMETRY_ENGINE_ID,
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "status": status,
        "input_surfaces": input_surfaces,
        "surfaces": surfaces,
        "overlaps": overlaps,
        "encounters": encounters,
        "surface_metadata": surface_metadata,
        "blocked_surfaces": _base_blocked_surfaces(),
        "unresolved_notes": [
            *unresolved_notes,
            "Displayed/proxy geometry is not effective/contact truth.",
            "Proxy overlaps do not equal exact captured, tagged, killed, or density-weighted enemy fractions.",
        ],
    }


def _state_payload_from_statbook(statbook_payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = statbook_payload.get("rows") if isinstance(statbook_payload, Mapping) else None
    return build_geometry_payload(rows or {})


def build_geometry_range_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for preset_name, preset_payload in (payload.get("presets") or {}).items():
        for state_mode, state_payload in (preset_payload or {}).items():
            inputs = state_payload.get("input_surfaces") or {}
            surfaces = state_payload.get("surfaces") or {}
            tower_input = inputs.get("tower_range_theoretical_m") or {}
            theoretical = tower_input.get("value")
            displayed = surfaces.get("tower_range_displayed_m")
            rows.append(
                {
                    "preset": preset_name,
                    "state_mode": state_mode,
                    "status": state_payload.get("status"),
                    "tower_range_input_surface_id": tower_input.get("source_surface_id"),
                    "tower_range_theoretical_m": theoretical,
                    "tower_range_displayed_m": displayed,
                    "displayed_delta_m": (
                        None
                        if theoretical is None or displayed is None
                        else float(displayed) - float(theoretical)
                    ),
                    "displayed_to_theoretical_ratio": (
                        None
                        if theoretical in (None, 0)
                        else float(displayed or 0.0) / float(theoretical)
                    ),
                    "transform_status": (
                        "identity_to_80"
                        if _finite_float(theoretical) is not None
                        and float(theoretical) <= TOWER_DISPLAYED_BREAKPOINT_M
                        else "compressed_above_80"
                        if _finite_float(theoretical) is not None
                        else "missing"
                    ),
                }
            )
    return {
        "artifact": "geometry_range_report.json",
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "owner": GEOMETRY_ENGINE_ID,
        "rows": rows,
        "diagnostics": {
            "row_count": len(rows),
            "unresolved_count": sum(1 for row in rows if str(row.get("status") or "").startswith("unresolved")),
            "surface_split": "tower_range_theoretical_m -> tower_range_displayed_m",
        },
    }


def geometry_range_report_csv(report: Mapping[str, Any]) -> str:
    fieldnames = (
        "preset",
        "state_mode",
        "status",
        "tower_range_input_surface_id",
        "tower_range_theoretical_m",
        "tower_range_displayed_m",
        "displayed_delta_m",
        "displayed_to_theoretical_ratio",
        "transform_status",
    )
    lines = [",".join(fieldnames)]
    for row in report.get("rows") or []:
        values = []
        for field in fieldnames:
            value = row.get(field)
            if value is None:
                values.append("")
            else:
                text = str(value).replace('"', '""')
                values.append(f'"{text}"' if "," in text else text)
        lines.append(",".join(values))
    return "\n".join(lines) + "\n"


def build_run_stats_geometry_artifacts(
    *,
    start_books_by_preset: Mapping[str, Any],
    max_books_by_preset: Mapping[str, Any],
) -> dict[str, Any]:
    presets: dict[str, dict[str, Any]] = {}
    preset_names = tuple(dict.fromkeys([*start_books_by_preset.keys(), *max_books_by_preset.keys()]))
    for preset_name in preset_names:
        presets[preset_name] = {
            "start_of_run": _state_payload_from_statbook(start_books_by_preset.get(preset_name) or {}),
            "max_progression": _state_payload_from_statbook(max_books_by_preset.get(preset_name) or {}),
        }

    state_payloads = [
        state_payload
        for preset_payload in presets.values()
        for state_payload in preset_payload.values()
    ]
    resolved_count = sum(1 for state in state_payloads if state.get("status") == GEOMETRY_STATUS_RESOLVED)
    partial_count = sum(1 for state in state_payloads if state.get("status") == GEOMETRY_STATUS_PARTIAL)
    unresolved_count = sum(1 for state in state_payloads if str(state.get("status") or "").startswith("unresolved"))
    geometry_payload = {
        "artifact": "geometry_engine_payload.json",
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "engine": "geometry_engine",
        "owner": GEOMETRY_ENGINE_ID,
        "status": (
            GEOMETRY_STATUS_RESOLVED
            if resolved_count == len(state_payloads)
            else GEOMETRY_STATUS_PARTIAL
            if resolved_count or partial_count
            else GEOMETRY_STATUS_MISSING_RANGE
        ),
        "presets": presets,
        "diagnostics": {
            "state_count": len(state_payloads),
            "resolved_state_count": resolved_count,
            "partial_state_count": partial_count,
            "unresolved_state_count": unresolved_count,
            "effective_contact_truth_promoted": False,
            "proxy_governance_status": "active",
        },
    }
    range_report = build_geometry_range_report(geometry_payload)
    return {
        "geometry_engine_payload": geometry_payload,
        "geometry_range_report": range_report,
        "geometry_range_report_csv": geometry_range_report_csv(range_report),
        "geometry_consumer_interfaces": build_geometry_consumer_interfaces_payload(),
        "geometry_proxy_governance": build_geometry_proxy_governance_payload(),
        "diagnostics": {
            "status": geometry_payload["status"],
            "artifact": "geometry_engine_payload.json",
            "range_report_artifact": "geometry_range_report.json",
            "range_report_csv_artifact": "geometry_range_report.csv",
            "consumer_interfaces_artifact": "geometry_consumer_interfaces.json",
            "proxy_governance_artifact": "geometry_proxy_governance.json",
            **geometry_payload["diagnostics"],
        },
    }
