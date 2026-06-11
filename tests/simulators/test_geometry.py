from __future__ import annotations

import pytest


def test_tower_display_transform_identity_to_80_and_inverse_roundtrip():
    from simulators.geometry import (
        tower_range_displayed_from_theoretical,
        tower_range_theoretical_from_displayed,
    )

    assert tower_range_displayed_from_theoretical(30.0) == pytest.approx(30.0)
    assert tower_range_displayed_from_theoretical(80.0) == pytest.approx(80.0)
    displayed = tower_range_displayed_from_theoretical(109.56)

    assert displayed == pytest.approx(105.4359202324)
    assert tower_range_theoretical_from_displayed(displayed) == pytest.approx(109.56)


def test_circle_overlap_zero_disjoint_and_full_containment():
    from simulators.geometry import circle_area, circle_circle_overlap_area

    assert circle_circle_overlap_area(10.0, 5.0, 20.0) == pytest.approx(0.0)
    assert circle_circle_overlap_area(10.0, 5.0, 3.0) == pytest.approx(circle_area(5.0))


def test_overlap_fraction_names_are_denominator_explicit():
    from simulators.geometry import overlap_fraction_of_target, overlap_fraction_of_zone

    target_fraction = overlap_fraction_of_target(
        zone_radius_m=5.0,
        target_radius_m=10.0,
        center_distance_m=0.0,
    )
    zone_fraction = overlap_fraction_of_zone(
        zone_radius_m=5.0,
        target_radius_m=10.0,
        center_distance_m=0.0,
    )

    assert target_fraction == pytest.approx(0.25)
    assert zone_fraction == pytest.approx(1.0)


def test_geometry_payload_computes_displayed_proxy_surfaces():
    from simulators.geometry import build_geometry_payload

    payload = build_geometry_payload(
        {
            "state::tower.range_m": {"final_value": 109.56},
            "state::uw.black_hole.size_m": {"final_value": 48.0},
            "state::uw.chrono_field.range_m": {"final_value": 51.0},
            "state::bot.golden.range_m": {"final_value": 56.0},
            "state::uw.spotlight.count": {"final_value": 3.0},
            "state::uw.spotlight.angle_degrees": {"final_value": 40.0},
        }
    )
    surfaces = payload["surfaces"]
    overlaps = payload["overlaps"]
    encounters = payload["encounters"]

    assert payload["status"] == "resolved_displayed_proxy"
    assert surfaces["tower_range_displayed_m"] == pytest.approx(105.4359202324)
    assert surfaces["wall_radius_displayed_m"] == pytest.approx(33.2919896352)
    assert surfaces["regular_orb_radius_displayed_m"] == pytest.approx(87.5090908416)
    assert surfaces["extra_orb_radius_displayed_m"] == pytest.approx(77.9804029463)
    assert surfaces["black_hole_center_distance_displayed_m"] == pytest.approx(89.6205321975)
    assert surfaces["black_hole_radius_displayed_m"] == pytest.approx(39.3155881356)
    assert surfaces["golden_bot_radius_displayed_m"] == pytest.approx(112.9908969627)
    assert surfaces["chrono_field_radius_displayed_m"] == pytest.approx(156.4359202324)
    assert overlaps["black_hole_overlap_fraction_of_tower"] == pytest.approx(0.099363, abs=1e-6)
    assert overlaps["black_hole_overlap_fraction_of_golden_bot"] == pytest.approx(0.100721, abs=1e-6)
    assert encounters["black_hole_inbound_path_exposure_fraction_proxy"] == pytest.approx(0.225007, abs=1e-6)
    assert encounters["spotlight_angular_coverage_fraction_proxy"] == pytest.approx(1.0 / 3.0)
    assert surfaces["boss_path_distance_to_wall_displayed_candidate_m"] == pytest.approx(72.1439305972)
    assert encounters["boss_contact_time_displayed_proxy_seconds"] == pytest.approx(3.2702689007)
    assert (
        encounters["boss_wall_travel_displayed_proxy"]["truth_status"]
        == "displayed_proxy_candidate_not_wall_contact_truth"
    )
    assert payload["blocked_surfaces"]["boss_contact_time_from_geometry_seconds"]["status"] == "blocked"


def test_boss_wall_travel_proxy_increases_with_displayed_range():
    from simulators.geometry import boss_wall_travel_displayed_proxy_from_tower_range

    small = boss_wall_travel_displayed_proxy_from_tower_range(tower_range_theoretical_m=30.0)
    reference = boss_wall_travel_displayed_proxy_from_tower_range(tower_range_theoretical_m=69.5)
    large = boss_wall_travel_displayed_proxy_from_tower_range(tower_range_theoretical_m=109.56)

    assert small["status"] == "resolved_displayed_proxy_candidate"
    assert reference["boss_contact_time_displayed_proxy_seconds"] == pytest.approx(2.0)
    assert small["boss_contact_time_displayed_proxy_seconds"] < reference["boss_contact_time_displayed_proxy_seconds"]
    assert large["boss_contact_time_displayed_proxy_seconds"] > reference["boss_contact_time_displayed_proxy_seconds"]
    assert large["boss_path_distance_to_wall_displayed_candidate_m"] > small[
        "boss_path_distance_to_wall_displayed_candidate_m"
    ]


def test_geometry_payload_missing_range_fails_closed():
    from simulators.geometry import build_geometry_payload

    payload = build_geometry_payload({"state::uw.black_hole.size_m": {"final_value": 48.0}})

    assert payload["status"] == "unresolved_missing_tower_range_theoretical_m"
    assert payload["surfaces"] == {}
    assert payload["overlaps"] == {}
    assert payload["encounters"] == {}
    assert "wall_contact_radius_effective_u" in payload["blocked_surfaces"]


def test_geometry_payload_exports_proxy_governance():
    from simulators.geometry import build_geometry_proxy_governance_payload

    payload = build_geometry_proxy_governance_payload()
    governance = payload["geometry_proxy_governance"]

    assert governance["status"] == "active"
    assert "coverage_proxy_weighting" in governance["allowed_uses"]
    assert "boss_contact_time_truth" in governance["blocked_uses"]
