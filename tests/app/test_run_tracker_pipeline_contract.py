from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


TRACKER_CSV = """verified,createdAt,updatedAt,source,tier,wave,duration,coins,cells,killedBy,note,runDate,runTime,type,gameTime,coinsPerHour,cellsPerHour,wavesSkipped,coinsFromWaveSkip,coinsPerWave,mostCoinsFromWaveSkip,totalEnemies,basic,fast,tank,ranged,boss,protector,totalElites,vampires,rays,scatters,saboteurs,commanders,overcharges,coinsFromDeathWave,coinsFromGoldenTower,coinsFromBlackhole,coinsFromSpotlight,goldenBotCoinsEarned,coinsFromGoldenCombo,wavesPerHour
,2026-06-08T00:00:00Z,2026-06-08T00:00:00Z,web,14,5502,5h30m36s,1.18q,180K,Scatter,,2026-06-08,13:00:00,Farming,1d0h0m0s,213.59T,32K,2243,286.20T,218.92B,6.03T,700000,250000,200000,150000,99000,500,500,800,300,250,250,0,0,0,838.42T,809.16T,776.27T,413.89T,708.82T,256.23T,998.55
,2026-06-13T00:00:00Z,2026-06-13T00:00:00Z,web,14,6518,6h46m0s,1.63q,234.37K,Scatter,,2026-06-13,13:29:00,Farming,1d9h43m44s,240.70T,34.64K,2460,403.00T,286.20B,6.89T,952172,300000,250000,220000,180000,650,1522,931,320,300,311,0,0,0,1.20q,1.16q,1.11q,600.95T,1.01q,403.00T,963.25
true,2026-06-12T00:00:00Z,2026-06-12T00:00:00Z,web,15,5049,5h42m58s,23.13T,121.23K,Boss,Health Disco,2026-06-10,21:27:00,Dissonance,1d4h13m1s,4.05T,21.21K,2130,0,0,0,350087,100000,90000,80000,79000,400,687,746,250,250,246,0,0,0,0,0,0,0,0,0,883.36
"""

TREND_TRACKER_CSV = """verified,createdAt,updatedAt,source,tier,wave,duration,coins,cells,killedBy,note,runDate,runTime,type,gameTime,coinsPerHour,cellsPerHour,wavesSkipped,totalEnemies,totalElites
,2026-06-01T00:00:00Z,2026-06-01T00:00:00Z,web,14,5000,5h0m0s,900T,100K,Scatter,,2026-06-01,10:00:00,Farming,1d0h0m0s,180T,20K,2000,600000,700
,2026-06-02T00:00:00Z,2026-06-02T00:00:00Z,web,14,5200,5h12m0s,1.04q,110K,Scatter,,2026-06-02,10:00:00,Farming,1d0h0m0s,200T,21K,2100,650000,720
,2026-06-03T00:00:00Z,2026-06-03T00:00:00Z,web,14,5600,5h30m0s,1.16q,120K,Scatter,,2026-06-03,10:00:00,Farming,1d0h0m0s,210T,22K,2250,750000,760
,2026-06-04T00:00:00Z,2026-06-04T00:00:00Z,web,14,6000,6h0m0s,1.32q,130K,Scatter,,2026-06-04,10:00:00,Farming,1d0h0m0s,220T,23K,2350,840000,790
"""


def test_run_stats_pipeline_publishes_optional_run_tracker_evidence(tmp_path: Path) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
    )

    assert run_stats_pipeline(args) == 0

    run_stats = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))
    evidence = run_stats["diagnostics"]["run_tracker_calibration_evidence"]
    assert evidence["application"] == "external_observation_not_account_truth"
    assert evidence["farming_t14_recent"]["latest"]["wave"] == 6518
    readiness = run_stats["diagnostics"]["farming_econ_model_readiness"]
    alignment = readiness["tracker_timing_alignment"]
    tracker_cph = readiness["tracker_cph_calibration_evidence"]
    tracker_cph_identity = readiness["tracker_cph_identity_evidence"]
    tracker_wave_reward = readiness["tracker_wave_reward_candidate"]
    assert alignment["status"] == "tracker_t14_farming_timing_gap_quantified"
    assert alignment["tracker_median_game_time_hours"] == pytest.approx(
        28.864444444444445
    )
    assert alignment["tracker_game_to_real_duration_ratio"] == pytest.approx(
        4.670140869414917
    )
    assert alignment["tracker_game_time_ratio_status"] == "tracker_game_time_ratio_available"
    assert alignment["observed_median_waves_per_hour"] == pytest.approx(980.8996629504798)
    assert alignment["tracker_reported_median_waves_per_hour"] == pytest.approx(980.9)
    assert alignment["tracker_reported_to_observed_waves_per_hour_ratio"] == pytest.approx(
        1.0000003149430778
    )
    assert alignment["tracker_waves_per_hour_consistency_status"] == (
        "tracker_reported_waves_per_hour_matches_duration"
    )
    assert alignment["projected_over_observed_duration_ratio"] is not None
    assert alignment["skip_adjusted_projected_over_observed_duration_ratio"] is not None
    assert (
        alignment["skip_adjusted_projected_over_observed_duration_ratio"]
        < alignment["projected_over_observed_duration_ratio"]
    )
    assert alignment["observed_skipped_waves_median"] == pytest.approx(2351.5)
    assert alignment["expected_skipped_waves_at_tracker_median_wave"] == pytest.approx(
        729.6638655462184
    )
    assert alignment["observed_skip_ratio_at_tracker_median_wave"] > alignment[
        "expected_skip_ratio_at_tracker_median_wave"
    ]
    assert alignment["observed_non_intro_displayed_waves"] == pytest.approx(4570.0)
    assert alignment["observed_played_waves_after_intro_from_tracker"] == pytest.approx(2218.5)
    assert alignment["observed_effective_skip_multiplier_after_intro"] == pytest.approx(
        2.0599504169483884
    )
    skip_semantics_candidates = alignment["tracker_waves_skipped_semantics_candidates"]
    skip_semantics_inference = alignment["tracker_waves_skipped_semantics_inference"]
    assert skip_semantics_candidates["status"] == "available"
    assert skip_semantics_candidates["raw_tracker_waves_skipped_median"] == pytest.approx(
        2351.5
    )
    assert skip_semantics_candidates[
        "interpretation_a_tracker_skips_exclude_intro_sprint"
    ]["effective_skip_multiplier_after_intro"] == pytest.approx(2.0599504169483884)
    assert skip_semantics_candidates[
        "interpretation_a_tracker_skips_exclude_intro_sprint"
    ]["observed_to_expected_skip_multiplier_ratio"] == pytest.approx(
        1.7310507705448643
    )
    assert skip_semantics_candidates[
        "interpretation_b_tracker_skips_include_intro_sprint"
    ]["skipped_waves_after_intro"] == pytest.approx(911.5)
    assert skip_semantics_candidates[
        "interpretation_b_tracker_skips_include_intro_sprint"
    ]["played_waves_after_intro"] == pytest.approx(3658.5)
    assert skip_semantics_candidates[
        "interpretation_b_tracker_skips_include_intro_sprint"
    ]["effective_skip_multiplier_after_intro"] == pytest.approx(1.2491458247915812)
    assert skip_semantics_candidates[
        "interpretation_b_tracker_skips_include_intro_sprint"
    ]["observed_to_expected_skip_multiplier_ratio"] == pytest.approx(
        1.049702373774438
    )
    assert skip_semantics_inference["status"] == "suggests_tracker_skips_include_intro_sprint"
    assert skip_semantics_inference["best_candidate"] == "tracker_skips_include_intro_sprint"
    assert skip_semantics_inference["best_candidate_distance_from_expected"] == pytest.approx(
        0.04970237377443802
    )
    assert skip_semantics_inference["candidate_distance_from_expected"] == {
        "tracker_skips_exclude_intro_sprint": pytest.approx(0.7310507705448643),
        "tracker_skips_include_intro_sprint": pytest.approx(0.04970237377443802),
    }
    assert skip_semantics_inference["include_intro_support_ratio_vs_exclude"] == pytest.approx(
        0.7310507705448643 / 0.04970237377443802
    )
    assert skip_semantics_inference["operator_confirmation_required"] is True
    assert alignment["implied_wave_skip_mastery_double_chance_pct_at_current_base"] == pytest.approx(
        73.10507705448643
    )
    assert alignment["observed_to_expected_skip_multiplier_ratio"] == pytest.approx(
        1.7310507705448643
    )
    assert alignment["skip_semantics_gap_status"] == (
        "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap"
    )
    assert tracker_cph["status"] == "tracker_t14_farming_cph_band_available"
    assert tracker_cph["observed_median_coins_per_hour"] == pytest.approx(
        227_145_000_000_000.0
    )
    assert tracker_cph["observed_to_anchor_coins_per_hour_ratio"] == pytest.approx(
        1.081642857142857
    )
    assert tracker_cph_identity["status"] == "tracker_density_components_reconstruct_cph"
    assert tracker_cph_identity["formula"] == (
        "coins/run_duration_hours and coins_per_enemy * enemies_per_wave * waves_per_hour"
    )
    assert tracker_cph_identity["run_total_median_coins_per_hour"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert tracker_cph_identity["run_total_to_tracker_cph_ratio"] == pytest.approx(
        1.0016570458566083
    )
    assert tracker_cph_identity[
        "run_total_to_tracker_reported_row_ratio_median"
    ] == pytest.approx(
        1.0017129814796646
    )
    assert tracker_cph_identity["component_median_coins_per_hour"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert tracker_cph_identity["component_to_tracker_cph_ratio"] == pytest.approx(
        1.0016570458566083
    )
    assert tracker_wave_reward["status"] == (
        "tracker_intro_wave_skip_reward_candidate_available"
    )
    assert tracker_wave_reward["certification_effect"] == "none"
    assert tracker_wave_reward["coin_eligible_displayed_waves_after_intro"] == pytest.approx(
        4570.0
    )
    assert tracker_wave_reward["tracker_played_waves_after_intro"] == pytest.approx(2218.5)
    assert tracker_wave_reward["coins_per_non_intro_displayed_wave"] == pytest.approx(
        307_439_824_945.2954
    )
    assert tracker_wave_reward["coins_per_tracker_played_wave_after_intro"] == pytest.approx(
        633_310_795_582.6008
    )
    assert tracker_wave_reward["tracker_reward_field_status"] == (
        "tracker_wave_skip_reward_fields_available"
    )
    assert tracker_wave_reward["tracker_reported_coins_from_wave_skip"] == pytest.approx(
        344_600_000_000_000.0
    )
    assert tracker_wave_reward["tracker_reported_coins_per_wave"] == pytest.approx(
        252_560_000_000.0
    )
    assert tracker_wave_reward[
        "tracker_reported_coins_per_wave_to_observed_ratio"
    ] == pytest.approx(1.0826048578558802)
    assert tracker_wave_reward["tracker_reported_coins_per_wave_semantics_status"] == (
        "tracker_reported_coins_per_wave_close_to_total_observed"
    )
    assert tracker_wave_reward["tracker_reported_wave_skip_coin_share"] == pytest.approx(
        0.24489081834251847
    )
    assert tracker_wave_reward["tracker_reported_coins_per_skipped_wave"] == pytest.approx(
        145_709_053_278.67368
    )
    wave_reward_audit = tracker_wave_reward["source_audit"]
    assert wave_reward_audit["status"] == (
        "base_reward_sources_available_integral_semantics_unresolved"
    )
    assert wave_reward_audit["certification_effect"] == "none"
    assert wave_reward_audit["intro_sprint_coin_suppression"]["status"] == (
        "source_backed_available"
    )
    assert wave_reward_audit["intro_sprint_coin_suppression"]["active_wave_count"] == pytest.approx(
        1440.0
    )
    assert wave_reward_audit["wave_skip_base_reward"]["status"] == (
        "source_backed_available_expected_value_missing"
    )
    assert wave_reward_audit["wave_skip_base_reward"]["chance_pct"] == pytest.approx(19.0)
    assert wave_reward_audit["wave_skip_mastery_double_skip"]["status"] == (
        "source_backed_available_reward_integral_missing"
    )
    assert wave_reward_audit["wave_skip_mastery_double_skip"]["driver_status"] == "gated_off"
    assert wave_reward_audit["tracker_skip_count_semantics"]["status"] == (
        "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap"
    )
    assert wave_reward_audit["tracker_skip_count_semantics"]["inference_status"] == (
        "suggests_tracker_skips_include_intro_sprint"
    )
    assert wave_reward_audit["tracker_skip_count_semantics"]["best_candidate"] == (
        "tracker_skips_include_intro_sprint"
    )
    wave_skip_reward = readiness["wave_skip_reward_readiness"]
    assert wave_skip_reward["status"] == (
        "source_reward_semantics_available_expected_value_integral_missing"
    )
    assert wave_skip_reward["source_audit"] == wave_reward_audit
    assert wave_skip_reward["tracker_reward_status"] == (
        "tracker_intro_wave_skip_reward_candidate_available"
    )
    assert wave_skip_reward["tracker_reward_field_status"] == (
        "tracker_wave_skip_reward_fields_available"
    )
    assert wave_skip_reward["tracker_skip_semantics_inference_status"] == (
        "suggests_tracker_skips_include_intro_sprint"
    )
    assert "tracker_waves_skipped_intro_sprint_semantics" in wave_reward_audit[
        "missing_to_promote"
    ]
    assert "wave_skip_coin_reward_expected_value_over_per_wave_coin_curve" in tracker_wave_reward[
        "missing_to_promote"
    ]
    assert "tracker_waves_skipped_intro_sprint_semantics" in tracker_wave_reward[
        "missing_to_promote"
    ]
    spawn_density = readiness["spawn_density_readiness"]
    tracker_density = spawn_density["tracker_enemy_density_evidence"]
    tracker_kill_density = spawn_density["tracker_kill_density_transform_candidate"]
    tracker_kill_density_stability = spawn_density["tracker_kill_density_stability_evidence"]
    tracker_coin_density = spawn_density["tracker_coin_density_evidence"]
    tracker_coin_yield_stability = spawn_density["tracker_coin_yield_stability_evidence"]
    tracker_coin_integral = spawn_density["tracker_coin_integral_candidate"]
    assert spawn_density["displayed_spawn_rate"] == pytest.approx(56.0)
    assert tracker_density["status"] == "tracker_t14_farming_enemy_density_available"
    assert tracker_density["recent_row_count"] == 2
    assert tracker_density["observed_median_total_enemies"] == pytest.approx(826_086.0)
    assert tracker_density["observed_median_enemies_per_wave"] == pytest.approx(
        136.65496214436905
    )
    assert tracker_density["tracker_enemy_composition_status"] == (
        "tracker_enemy_composition_available"
    )
    assert tracker_density["tracker_total_elites_share_of_total_enemies"] == pytest.approx(
        0.0010603108321965839
    )
    assert tracker_density["tracker_protector_share_of_total_enemies"] == pytest.approx(
        0.0011563682071846562
    )
    assert tracker_density["tracker_protector_count_per_wave"] == pytest.approx(
        0.16219162793768876
    )
    assert tracker_density["tracker_elite_subtype_count_per_wave"] == pytest.approx(
        0.14411844882426642
    )
    assert tracker_density[
        "displayed_spawn_rate_to_observed_enemies_per_wave_ratio"
    ] == pytest.approx(136.65496214436905 / 56.0)
    assert tracker_kill_density["status"] == (
        "tracker_spawn_rate_to_kill_density_candidate_available"
    )
    assert tracker_kill_density["certification_effect"] == "none"
    assert tracker_kill_density[
        "observed_enemies_per_wave_per_displayed_spawn_rate"
    ] == pytest.approx(136.65496214436905 / 56.0)
    assert tracker_kill_density[
        "projected_enemies_per_wave_from_tracker_ratio"
    ] == pytest.approx(136.65496214436905)
    assert (
        "approved_spawn_rate_to_kill_density_transform"
        in tracker_kill_density["missing_to_promote"]
    )
    assert tracker_kill_density_stability["status"] == (
        "tracker_supplied_without_recent_prior_kill_density_transform"
    )
    assert tracker_kill_density_stability["certification_effect"] == "none"
    assert tracker_kill_density_stability[
        "recent_enemies_per_wave_per_displayed_spawn_rate"
    ] == pytest.approx(136.65496214436905 / 56.0)
    assert tracker_kill_density_stability["prior_enemies_per_wave_per_displayed_spawn_rate"] is None
    assert tracker_coin_density["status"] == "tracker_t14_farming_coin_density_available"
    assert tracker_coin_density["observed_median_coins_per_enemy"] == pytest.approx(
        1_698_794_935.6088724
    )
    assert tracker_coin_density["observed_median_coins_per_wave"] == pytest.approx(
        232_272_088_511.65057
    )
    assert tracker_coin_yield_stability["status"] == (
        "tracker_supplied_without_recent_prior_coin_yield"
    )
    assert tracker_coin_yield_stability["certification_effect"] == "none"
    assert tracker_coin_yield_stability[
        "recent_observed_coins_per_enemy_median"
    ] == pytest.approx(1_698_794_935.6088724)
    assert tracker_coin_yield_stability["prior_observed_coins_per_enemy_median"] is None
    assert tracker_coin_integral["status"] == (
        "tracker_kill_density_to_coin_integral_candidate_available"
    )
    assert tracker_coin_integral["certification_effect"] == "none"
    assert tracker_coin_integral[
        "projected_coins_per_wave_from_tracker_density"
    ] == pytest.approx(232_148_757_616.67633)
    assert tracker_coin_integral[
        "projected_coins_per_hour_from_tracker_density"
    ] == pytest.approx(227_714_638_100_570.44)
    assert tracker_coin_integral["projected_to_tracker_cph_ratio"] == pytest.approx(
        1.002507817035684
    )
    assert tracker_coin_integral["latest_observed_coins_per_enemy"] == pytest.approx(
        1_711_875_585.5034595
    )
    assert tracker_coin_integral["latest_observed_enemies_per_wave"] == pytest.approx(
        146.08346118441239
    )
    assert tracker_coin_integral[
        "latest_projected_coins_per_wave_from_tracker_density"
    ] == pytest.approx(250_076_710_647.43784)
    assert tracker_coin_integral[
        "latest_projected_coins_per_hour_from_tracker_density"
    ] == pytest.approx(240_886_699_507_389.16)
    assert tracker_coin_integral["latest_run_total_coins_per_hour"] == pytest.approx(
        240_886_699_507_389.16
    )
    assert tracker_coin_integral[
        "latest_density_to_latest_run_total_cph_ratio"
    ] == pytest.approx(1.0)
    assert "source_owned_coins_per_kill_integral" in tracker_coin_integral["missing_to_promote"]
    current_cph_estimate = readiness["current_coin_density_cph_estimate"]
    assert current_cph_estimate["status"] == (
        "tracker_coin_density_current_timing_calculator_available"
    )
    assert current_cph_estimate["basis"] == "latest_tracker_coin_density_current_timing"
    assert current_cph_estimate["latest_observed_coins_per_enemy"] == pytest.approx(
        1_711_875_585.5034595
    )
    assert current_cph_estimate["current_timing_run_hours"] == pytest.approx(
        4.864050046685341
    )
    assert current_cph_estimate["selected_projected_coins_per_run"] == pytest.approx(
        1_440_691_930_039_889.2
    )
    assert current_cph_estimate["selected_projected_coins_per_hour"] == pytest.approx(
        296_191_839_354_462.3
    )
    assert current_cph_estimate[
        "latest_intro_excluded_projected_coins_per_hour"
    ] == pytest.approx(222_156_732_832_951.16)
    assert current_cph_estimate["latest_tracker_wave_horizon"] == pytest.approx(6518.0)
    assert current_cph_estimate[
        "latest_tracker_wave_horizon_current_timing_run_hours"
    ] == pytest.approx(5.716187488328666)
    assert current_cph_estimate[
        "latest_tracker_wave_horizon_projected_coins_per_run"
    ] == pytest.approx(1_630_000_000_000_000.0)
    assert current_cph_estimate[
        "latest_tracker_wave_horizon_projected_coins_per_hour"
    ] == pytest.approx(285_155_097_401_570.56)
    assert current_cph_estimate[
        "latest_tracker_wave_horizon_intro_excluded_projected_coins_per_hour"
    ] == pytest.approx(222_156_732_832_951.1)
    cph_promotion = readiness["coins_per_hour_promotion_readiness"]
    assert cph_promotion["status"] == "not_ready"
    assert cph_promotion["application"] == "diagnostic_only_not_account_truth"
    assert cph_promotion["default_cph_derived"] is False
    assert cph_promotion["operator_approval_required"] is True
    assert cph_promotion["validation_basis"] == "tracker_t14_recent_window_only"
    assert cph_promotion["tracker_cph_status"] == "tracker_t14_farming_cph_band_available"
    assert cph_promotion["tracker_cph_identity_status"] == "tracker_density_components_reconstruct_cph"
    assert cph_promotion["tracker_kill_density_status"] == (
        "tracker_spawn_rate_to_kill_density_candidate_available"
    )
    assert cph_promotion["tracker_coin_integral_status"] == (
        "tracker_kill_density_to_coin_integral_candidate_available"
    )
    assert cph_promotion["tracker_wave_skip_reward_field_status"] == (
        "tracker_wave_skip_reward_fields_available"
    )
    assert cph_promotion["tracker_econ_coin_source_status"] == (
        "tracker_econ_coin_sources_available"
    )
    assert cph_promotion["tracker_econ_coin_source_available_count"] == 6
    assert cph_promotion["tracker_econ_source_sum_to_run_coins_ratio"] == pytest.approx(
        3.2935449464489963
    )
    assert cph_promotion["tracker_econ_overlap_evidence_status"] == (
        "source_splits_overlap_or_double_count"
    )
    assert cph_promotion["observed_median_coins_per_hour"] == pytest.approx(
        227_145_000_000_000.0
    )
    assert cph_promotion["component_to_tracker_cph_ratio"] == pytest.approx(
        1.0016570458566083
    )
    assert cph_promotion["tracker_run_total_cph"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert cph_promotion["tracker_run_total_to_reported_cph_ratio"] == pytest.approx(
        1.0016570458566083
    )
    assert cph_promotion[
        "tracker_run_total_to_reported_row_ratio_median"
    ] == pytest.approx(1.0017129814796646)
    assert cph_promotion["projected_to_tracker_cph_ratio"] == pytest.approx(
        1.002507817035684
    )
    assert cph_promotion["tracker_timing_status"] == "tracker_t14_farming_timing_gap_quantified"
    assert cph_promotion["tracker_waves_per_hour_consistency_status"] == (
        "tracker_reported_waves_per_hour_matches_duration"
    )
    assert cph_promotion["tracker_game_time_ratio_status"] == "tracker_game_time_ratio_available"
    assert cph_promotion["tracker_median_game_time_hours"] == pytest.approx(
        28.864444444444445
    )
    assert cph_promotion["tracker_game_to_real_duration_ratio"] == pytest.approx(
        4.670140869414917
    )
    assert cph_promotion["tracker_reported_median_waves_per_hour"] == pytest.approx(980.9)
    assert cph_promotion["tracker_reported_to_observed_waves_per_hour_ratio"] == pytest.approx(
        1.0000003149430778
    )
    assert cph_promotion["tracker_projected_over_observed_duration_ratio"] is not None
    assert (
        cph_promotion["tracker_skip_adjusted_projected_over_observed_duration_ratio"]
        is not None
    )
    assert cph_promotion["tracker_reported_coins_per_wave"] == pytest.approx(
        252_560_000_000.0
    )
    assert cph_promotion[
        "tracker_reported_coins_per_wave_to_observed_ratio"
    ] == pytest.approx(1.0826048578558802)
    assert cph_promotion["tracker_reported_coins_per_wave_semantics_status"] == (
        "tracker_reported_coins_per_wave_close_to_total_observed"
    )
    assert cph_promotion["tracker_reported_wave_skip_coin_share"] == pytest.approx(
        0.24489081834251847
    )
    assert cph_promotion["tracker_reported_coins_per_skipped_wave"] == pytest.approx(
        145_709_053_278.67368
    )
    tracker_econ_sources = readiness["econ_sync_window_readiness"][
        "tracker_econ_coin_source_evidence"
    ]
    assert tracker_econ_sources["status"] == "tracker_econ_coin_sources_available"
    assert tracker_econ_sources["available_source_count"] == 6
    assert tracker_econ_sources["tracked_source_sum_to_run_coins_ratio"]["median"] == pytest.approx(
        3.2935449464489963
    )
    assert tracker_econ_sources["overlap_evidence_status"] == (
        "source_splits_overlap_or_double_count"
    )
    assert tracker_econ_sources["sources"]["coins_from_golden_tower"]["share_of_run_coins"][
        "median"
    ] == pytest.approx(0.6986926276385568)
    assert cph_promotion["tracker_skip_semantics_inference_status"] == (
        "suggests_tracker_skips_include_intro_sprint"
    )
    assert cph_promotion["tracker_skip_semantics_best_candidate"] == (
        "tracker_skips_include_intro_sprint"
    )
    assert cph_promotion[
        "tracker_skip_semantics_best_candidate_distance_from_expected"
    ] == pytest.approx(0.04970237377443802)
    assert cph_promotion["tracker_calibration_anchor_hint"]["status"] == (
        "recent_band_available_not_auto_applied"
    )
    assert cph_promotion["tracker_latest_coins_per_hour"] == pytest.approx(
        240_700_000_000_000.0
    )
    assert cph_promotion["tracker_recent_median_coins_per_hour"] == pytest.approx(
        227_145_000_000_000.0
    )
    assert cph_promotion["tracker_prior_median_coins_per_hour"] is None
    assert cph_promotion["tracker_recent_to_prior_coins_per_hour_ratio"] is None
    assert cph_promotion["auto_current_cph_estimate"] == current_cph_estimate
    assert cph_promotion["blocking_reasons"] == [
        "not_source_owned_run_coin_and_duration_integrals",
        "operator_has_not_approved_tracker_empirical_cph_as_default",
        "recent_prior_kill_density_stability_missing",
        "recent_prior_coin_yield_stability_missing",
        "tracker_wave_skip_intro_semantics_gap",
        "wave_skip_reward_expected_value_missing",
        "econ_window_overlap_coin_integral_missing",
        "validation_across_multiple_exports_and_account_states_missing",
    ]
    timing_drivers = {
        row["surface_id"]: row for row in readiness["timing_drivers"]
    }
    assert timing_drivers["state::cards.wave_skip.mastery_effect"]["status"] == "gated_off"

    diagnostics = json.loads((out_dir / "diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["run_tracker_calibration_evidence"]["row_count"] == 3


def test_tracker_empirical_farming_cph_approval_removes_only_operator_blocker(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_farming_cph=True,
    )

    assert run_stats_pipeline(args) == 0

    run_stats = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))
    cph_promotion = run_stats["diagnostics"]["farming_econ_model_readiness"][
        "coins_per_hour_promotion_readiness"
    ]
    assert cph_promotion["status"] == "not_ready"
    assert cph_promotion["default_cph_derived"] is False
    assert cph_promotion["operator_approval_required"] is True
    assert cph_promotion["operator_approved_tracker_empirical_cph_default"] is True
    assert cph_promotion["operator_approval_status"] == "approved_explicit_runtime_input"
    assert (
        "operator_has_not_approved_tracker_empirical_cph_as_default"
        not in cph_promotion["blocking_reasons"]
    )
    assert "not_source_owned_run_coin_and_duration_integrals" in cph_promotion[
        "blocking_reasons"
    ]
    assert "wave_skip_reward_expected_value_missing" in cph_promotion[
        "blocking_reasons"
    ]
    assert "econ_window_overlap_coin_integral_missing" in cph_promotion[
        "blocking_reasons"
    ]


def test_tracker_empirical_kill_density_approval_closes_only_kill_density_link(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_kill_density_transform=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    kill_density = readiness["spawn_density_readiness"]["kill_density_transform_readiness"]
    assert kill_density["operator_approval_status"] == "approved_explicit_runtime_input"
    assert kill_density["approved_transform_closes_formula_link"] is True
    assert kill_density["certification_effect"] == (
        "closes_spawn_rate_to_enemy_kill_density_link_only"
    )
    assert "spawn_rate_to_enemy_kill_density_by_wave" not in readiness[
        "missing_formula_links"
    ]
    assert "spawn_rate_to_enemy_kill_density_by_wave" not in readiness[
        "coins_per_hour_certification_blockers"
    ]
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_missing_formula_links"
    )
    assert "wave_skip_reward_and_mastery_expected_value" in readiness[
        "missing_formula_links"
    ]
    assert "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral" in readiness[
        "missing_formula_links"
    ]


def test_tracker_empirical_run_duration_approval_closes_only_duration_link(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_run_duration_projection=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    duration = readiness["run_duration_projection_readiness"]
    assert duration["operator_approval_status"] == "approved_explicit_runtime_input"
    assert duration["tracker_duration_candidate_available"] is True
    assert duration["approved_projection_closes_formula_link"] is True
    assert duration["certification_effect"] == "closes_run_duration_link_only"
    assert (
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        not in readiness["missing_formula_links"]
    )
    assert (
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        not in readiness["coins_per_hour_certification_blockers"]
    )
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_missing_formula_links"
    )
    assert "spawn_rate_to_enemy_kill_density_by_wave" in readiness[
        "missing_formula_links"
    ]
    assert "wave_skip_reward_and_mastery_expected_value" in readiness[
        "missing_formula_links"
    ]


def test_tracker_empirical_wave_skip_reward_approval_closes_only_reward_link(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_wave_skip_reward=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    reward = readiness["wave_skip_reward_readiness"]
    assert reward["operator_approval_status"] == "approved_explicit_runtime_input"
    assert reward["tracker_reward_candidate_available"] is True
    assert reward["approved_reward_closes_formula_link"] is True
    assert reward["certification_effect"] == (
        "closes_wave_skip_reward_expected_value_link_only"
    )
    assert "wave_skip_reward_and_mastery_expected_value" not in readiness[
        "missing_formula_links"
    ]
    assert "wave_skip_reward_and_mastery_expected_value" not in readiness[
        "coins_per_hour_certification_blockers"
    ]
    cph_promotion = readiness["coins_per_hour_promotion_readiness"]
    assert "wave_skip_reward_expected_value_missing" not in cph_promotion[
        "blocking_reasons"
    ]
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_missing_formula_links"
    )
    assert (
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        in readiness["missing_formula_links"]
    )
    assert "spawn_rate_to_enemy_kill_density_by_wave" in readiness[
        "missing_formula_links"
    ]
    assert "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral" in readiness[
        "missing_formula_links"
    ]


def test_tracker_wave_skip_intro_semantics_approval_closes_only_semantics_blocker(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_farming_cph=True,
        approve_tracker_empirical_run_duration_projection=True,
        approve_tracker_empirical_wave_skip_reward=True,
        approve_tracker_wave_skip_intro_semantics=True,
        approve_source_intro_sprint_coin_window=True,
        approve_tracker_empirical_econ_window_overlap=True,
        approve_tracker_empirical_kill_density_transform=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    reward = readiness["wave_skip_reward_readiness"]
    approval = reward["tracker_skip_intro_semantics_approval"]
    cph_promotion = readiness["coins_per_hour_promotion_readiness"]
    assert approval["operator_approval_status"] == "approved_explicit_runtime_input"
    assert approval["approved_semantics_closes_validation_blocker"] is True
    assert approval["approved_tracker_waves_skipped_semantics"] == (
        "tracker_skips_include_intro_sprint"
    )
    assert approval["candidate_distance_from_expected"] == pytest.approx(
        0.04970237377443798
    )
    assert readiness["missing_formula_links"] == []
    assert "tracker_wave_skip_intro_semantics_gap" not in readiness[
        "coins_per_hour_certification_blockers"
    ]
    assert "tracker_wave_skip_intro_semantics_gap" not in cph_promotion[
        "blocking_reasons"
    ]
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_pending_empirical_validation"
    )
    assert readiness["certified_farming_cph_model"] is False
    assert readiness["coins_per_hour_certification_blockers"] == [
        "not_source_owned_run_coin_and_duration_integrals",
        "recent_prior_kill_density_stability_missing",
        "recent_prior_coin_yield_stability_missing",
        "validation_across_multiple_exports_and_account_states_missing",
    ]


def test_tracker_final_cph_approvals_keep_prior_window_validation_blockers(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_farming_cph=True,
        approve_tracker_empirical_run_coin_duration_integrals=True,
        approve_tracker_current_export_account_state_validation=True,
        approve_tracker_empirical_run_duration_projection=True,
        approve_tracker_empirical_wave_skip_reward=True,
        approve_tracker_wave_skip_intro_semantics=True,
        approve_source_intro_sprint_coin_window=True,
        approve_tracker_empirical_econ_window_overlap=True,
        approve_tracker_empirical_kill_density_transform=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    cph_promotion = readiness["coins_per_hour_promotion_readiness"]
    integral_approval = cph_promotion["run_coin_duration_integral_approval"]
    validation_approval = cph_promotion[
        "current_export_account_state_validation_approval"
    ]
    assert integral_approval["operator_approval_status"] == (
        "approved_explicit_runtime_input"
    )
    assert integral_approval["approved_integrals_close_blocker"] is True
    assert validation_approval["operator_approval_status"] == (
        "approved_explicit_runtime_input"
    )
    assert validation_approval["approved_validation_closes_blocker"] is True
    assert readiness["missing_formula_links"] == []
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_pending_empirical_validation"
    )
    assert readiness["certified_farming_cph_model"] is False
    assert readiness["coins_per_hour_certification_blockers"] == [
        "recent_prior_kill_density_stability_missing",
        "recent_prior_coin_yield_stability_missing",
    ]


def test_source_intro_sprint_coin_window_approval_closes_only_intro_link(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=None,
        approve_source_intro_sprint_coin_window=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    intro = readiness["intro_sprint_coin_window_readiness"]
    assert intro["operator_approval_status"] == "approved_explicit_runtime_input"
    assert intro["source_coin_window_candidate_available"] is True
    assert intro["approved_window_closes_formula_link"] is True
    assert intro["certification_effect"] == (
        "closes_intro_sprint_no_coin_window_link_only"
    )
    assert "intro_sprint_no_coin_window_to_run_coin_integral" not in readiness[
        "missing_formula_links"
    ]
    assert "intro_sprint_no_coin_window_to_run_coin_integral" not in readiness[
        "coins_per_hour_certification_blockers"
    ]
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_missing_formula_links"
    )
    assert (
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        in readiness["missing_formula_links"]
    )
    assert "spawn_rate_to_enemy_kill_density_by_wave" in readiness[
        "missing_formula_links"
    ]
    assert "wave_skip_reward_and_mastery_expected_value" in readiness[
        "missing_formula_links"
    ]
    assert "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral" in readiness[
        "missing_formula_links"
    ]


def test_tracker_empirical_econ_overlap_approval_closes_only_overlap_link(
    tmp_path: Path,
) -> None:
    from app.pipeline import run_stats_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = SimpleNamespace(
        ids=ROOT / "input" / "imports" / "ids.csv",
        out=out_dir,
        manual_inputs=None,
        runtime_state_overlay=None,
        perk_mode="max_progression_policy",
        perk_policy_preset=None,
        perk_state="auto",
        tier=None,
        dissonance_run_category=None,
        include_boss_wave_milestone_matrix=False,
        boss_wave_align_clean_reference_rows=True,
        run_tracker_csv=tracker,
        approve_tracker_empirical_econ_window_overlap=True,
    )

    assert run_stats_pipeline(args) == 0

    readiness = json.loads((out_dir / "run_stats.json").read_text(encoding="utf-8"))[
        "diagnostics"
    ]["farming_econ_model_readiness"]
    overlap = readiness["econ_sync_window_readiness"]["overlap_integral_readiness"]
    assert overlap["operator_approval_status"] == "approved_explicit_runtime_input"
    assert overlap["tracker_econ_source_candidate_available"] is True
    assert overlap["approved_overlap_closes_formula_link"] is True
    assert overlap["certification_effect"] == "closes_econ_window_overlap_link_only"
    assert "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral" not in readiness[
        "missing_formula_links"
    ]
    assert "gt_bh_dw_spotlight_golden_bot_overlap_coin_integral" not in readiness[
        "coins_per_hour_certification_blockers"
    ]
    cph_promotion = readiness["coins_per_hour_promotion_readiness"]
    assert "econ_window_overlap_coin_integral_missing" not in cph_promotion[
        "blocking_reasons"
    ]
    assert readiness["coins_per_hour_certification_status"] == (
        "not_certified_missing_formula_links"
    )
    assert (
        "calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed"
        in readiness["missing_formula_links"]
    )
    assert "spawn_rate_to_enemy_kill_density_by_wave" in readiness[
        "missing_formula_links"
    ]
    assert "wave_skip_reward_and_mastery_expected_value" in readiness[
        "missing_formula_links"
    ]


def test_run_tracker_summary_publishes_recent_vs_prior_t14_farming_trend(tmp_path: Path) -> None:
    from input.run_tracker import parse_run_tracker_csv, summarize_run_tracker_records

    tracker = tmp_path / "trend_runs.csv"
    tracker.write_text(TREND_TRACKER_CSV, encoding="utf-8")
    evidence = summarize_run_tracker_records(parse_run_tracker_csv(tracker), recent_window=2)

    trend = evidence["farming_t14_recent_trend"]
    assert trend["status"] == "recent_and_prior_windows_available"
    assert trend["application"] == "external_observation_not_account_truth"
    assert trend["certification_effect"] == "none"
    assert trend["recent_row_count"] == 2
    assert trend["prior_row_count"] == 2
    assert trend["recent_date_range"] == {
        "min_run_date": "2026-06-03",
        "max_run_date": "2026-06-04",
    }
    assert trend["prior_date_range"] == {
        "min_run_date": "2026-06-01",
        "max_run_date": "2026-06-02",
    }
    cph = trend["metrics"]["coins_per_hour"]
    assert cph["prior"]["median"] == pytest.approx(190_000_000_000_000.0)
    assert cph["recent"]["median"] == pytest.approx(215_000_000_000_000.0)
    assert cph["median_delta"] == pytest.approx(25_000_000_000_000.0)
    assert cph["median_ratio"] == pytest.approx(215 / 190)
    assert cph["direction"] == "up"
    coins_per_wave = trend["metrics"]["observed_coins_per_wave"]
    assert coins_per_wave["prior"]["median"] == pytest.approx(
        (900_000_000_000_000.0 / 5000.0 + 1_040_000_000_000_000.0 / 5200.0) / 2.0
    )
    assert coins_per_wave["recent"]["median"] == pytest.approx(
        (1_160_000_000_000_000.0 / 5600.0 + 1_320_000_000_000_000.0 / 6000.0) / 2.0
    )
    assert coins_per_wave["direction"] == "up"
    assert trend["calibration_anchor_hint"] == {
        "status": "recent_band_available_not_auto_applied",
        "latest_coins_per_hour": 220_000_000_000_000.0,
        "recent_median_coins_per_hour": 215_000_000_000_000.0,
        "prior_median_coins_per_hour": 190_000_000_000_000.0,
        "recent_to_prior_coins_per_hour_ratio": pytest.approx(215 / 190),
        "interpretation": (
            "Use as calibration evidence for account-improvement drift only; "
            "do not apply as KB truth or certified farming CPH."
        ),
    }


def test_execute_pipeline_mirrors_optional_run_tracker_evidence(tmp_path: Path) -> None:
    from app.pipeline import PipelineRunRequest, execute_pipeline

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    out_dir = tmp_path / "full_out"

    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / "input" / "imports" / "ids.csv",
            out=out_dir,
            run_tracker_csv=tracker,
        )
    )

    assert result.exit_code == 0
    diagnostics = json.loads((out_dir / "diagnostics.json").read_text(encoding="utf-8"))
    evidence = diagnostics["run_tracker_calibration_evidence"]
    assert evidence["calibration_policy"]["status"] == "evidence_available_not_auto_applied"
    assert evidence["farming_t14_recent"]["latest"]["coins_per_hour"] == 240_700_000_000_000.0
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "status"
    ] == "tracker_t14_farming_timing_gap_quantified"
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "skip_adjusted_projected_hours_at_tracker_median_wave"
    ] is not None
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "observed_skip_ratio_at_tracker_median_wave"
    ] > diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "expected_skip_ratio_at_tracker_median_wave"
    ]
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "skip_semantics_gap_status"
    ] == "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap"
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "tracker_waves_skipped_semantics_candidates"
    ]["interpretation_b_tracker_skips_include_intro_sprint"][
        "observed_to_expected_skip_multiplier_ratio"
    ] == pytest.approx(
        1.049702373774438
    )
    assert diagnostics["farming_econ_model_readiness"]["tracker_timing_alignment"][
        "tracker_waves_skipped_semantics_inference"
    ]["status"] == "suggests_tracker_skips_include_intro_sprint"
    assert diagnostics["farming_econ_model_readiness"]["tracker_cph_calibration_evidence"][
        "status"
    ] == "tracker_t14_farming_cph_band_available"
    assert diagnostics["farming_econ_model_readiness"]["tracker_cph_calibration_evidence"][
        "observed_to_anchor_coins_per_hour_ratio"
    ] == pytest.approx(1.081642857142857)
    assert diagnostics["farming_econ_model_readiness"]["tracker_cph_identity_evidence"][
        "status"
    ] == "tracker_density_components_reconstruct_cph"
    assert diagnostics["farming_econ_model_readiness"]["tracker_cph_identity_evidence"][
        "component_to_tracker_cph_ratio"
    ] == pytest.approx(1.0016570458566083)
    assert diagnostics["farming_econ_model_readiness"]["tracker_wave_reward_candidate"][
        "status"
    ] == "tracker_intro_wave_skip_reward_candidate_available"
    assert diagnostics["farming_econ_model_readiness"]["tracker_wave_reward_candidate"][
        "coins_per_tracker_played_wave_after_intro"
    ] == pytest.approx(633_310_795_582.6008)
    assert diagnostics["farming_econ_model_readiness"]["tracker_wave_reward_candidate"][
        "tracker_reward_field_status"
    ] == "tracker_wave_skip_reward_fields_available"
    assert diagnostics["farming_econ_model_readiness"]["tracker_wave_reward_candidate"][
        "tracker_reported_wave_skip_coin_share"
    ] == pytest.approx(0.24489081834251847)
    wave_reward_audit = diagnostics["farming_econ_model_readiness"][
        "tracker_wave_reward_candidate"
    ]["source_audit"]
    assert wave_reward_audit["status"] == (
        "base_reward_sources_available_integral_semantics_unresolved"
    )
    assert wave_reward_audit["intro_sprint_coin_suppression"]["status"] == (
        "source_backed_available"
    )
    assert wave_reward_audit["wave_skip_base_reward"]["status"] == (
        "source_backed_available_expected_value_missing"
    )
    assert wave_reward_audit["wave_skip_mastery_double_skip"]["driver_status"] == "gated_off"
    assert wave_reward_audit["tracker_skip_count_semantics"]["status"] == (
        "tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap"
    )
    assert wave_reward_audit["tracker_skip_count_semantics"]["best_candidate"] == (
        "tracker_skips_include_intro_sprint"
    )
    tracker_density = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_enemy_density_evidence"
    ]
    tracker_kill_density = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_kill_density_transform_candidate"
    ]
    tracker_kill_density_stability = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_kill_density_stability_evidence"
    ]
    tracker_coin_density = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_coin_density_evidence"
    ]
    tracker_coin_yield_stability = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_coin_yield_stability_evidence"
    ]
    tracker_coin_integral = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_coin_integral_candidate"
    ]
    composition = diagnostics["farming_econ_model_readiness"]["spawn_density_readiness"][
        "tracker_enemy_composition_evidence"
    ]
    assert tracker_density["status"] == "tracker_t14_farming_enemy_density_available"
    assert tracker_density["observed_median_enemies_per_wave"] == pytest.approx(
        136.65496214436905
    )
    assert composition["status"] == "tracker_enemy_composition_available"
    assert composition["normal_enemy_counts"]["protector"]["share_of_total_enemies"][
        "median"
    ] == pytest.approx(0.0011563682071846562)
    assert composition["normal_enemy_counts"]["protector"]["count_per_wave"][
        "median"
    ] == pytest.approx(0.16219162793768876)
    assert composition["elite_tracked_count_per_wave"]["median"] == pytest.approx(
        0.14411844882426642
    )
    assert composition["total_elites_share_of_total_enemies"]["median"] == pytest.approx(
        0.0010603108321965839
    )
    assert tracker_kill_density["status"] == (
        "tracker_spawn_rate_to_kill_density_candidate_available"
    )
    assert tracker_kill_density[
        "projected_enemies_per_wave_from_tracker_ratio"
    ] == pytest.approx(136.65496214436905)
    assert tracker_kill_density_stability["status"] == (
        "tracker_supplied_without_recent_prior_kill_density_transform"
    )
    assert tracker_coin_density["status"] == "tracker_t14_farming_coin_density_available"
    assert tracker_coin_density["observed_median_coins_per_enemy"] == pytest.approx(
        1_698_794_935.6088724
    )
    assert tracker_coin_yield_stability["status"] == (
        "tracker_supplied_without_recent_prior_coin_yield"
    )
    assert tracker_coin_integral["status"] == (
        "tracker_kill_density_to_coin_integral_candidate_available"
    )
    assert tracker_coin_integral["projected_to_tracker_cph_ratio"] == pytest.approx(
        1.002507817035684
    )
    assert tracker_coin_integral[
        "latest_projected_coins_per_hour_from_tracker_density"
    ] == pytest.approx(240_886_699_507_389.16)
    cph_promotion = diagnostics["farming_econ_model_readiness"][
        "coins_per_hour_promotion_readiness"
    ]
    assert cph_promotion["status"] == "not_ready"
    assert cph_promotion["tracker_cph_status"] == "tracker_t14_farming_cph_band_available"
    assert cph_promotion["tracker_cph_identity_status"] == "tracker_density_components_reconstruct_cph"
    assert cph_promotion["tracker_coin_integral_status"] == (
        "tracker_kill_density_to_coin_integral_candidate_available"
    )
    assert cph_promotion["tracker_wave_skip_reward_field_status"] == (
        "tracker_wave_skip_reward_fields_available"
    )
    assert cph_promotion["tracker_econ_coin_source_status"] == (
        "tracker_econ_coin_sources_available"
    )
    assert cph_promotion["tracker_econ_overlap_evidence_status"] == (
        "source_splits_overlap_or_double_count"
    )
    assert cph_promotion["projected_to_tracker_cph_ratio"] == pytest.approx(
        1.002507817035684
    )
    assert cph_promotion["tracker_run_total_cph"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert cph_promotion["tracker_run_total_to_reported_cph_ratio"] == pytest.approx(
        1.0016570458566083
    )
    assert cph_promotion["tracker_waves_per_hour_consistency_status"] == (
        "tracker_reported_waves_per_hour_matches_duration"
    )
    assert cph_promotion["tracker_game_time_ratio_status"] == "tracker_game_time_ratio_available"
    assert cph_promotion["tracker_median_game_time_hours"] == pytest.approx(
        28.864444444444445
    )
    assert cph_promotion["tracker_game_to_real_duration_ratio"] == pytest.approx(
        4.670140869414917
    )
    assert cph_promotion["tracker_reported_median_waves_per_hour"] == pytest.approx(980.9)
    assert cph_promotion["tracker_reported_to_observed_waves_per_hour_ratio"] == pytest.approx(
        1.0000003149430778
    )
    assert cph_promotion["tracker_reported_coins_per_wave_semantics_status"] == (
        "tracker_reported_coins_per_wave_close_to_total_observed"
    )
    assert cph_promotion["tracker_reported_coins_per_skipped_wave"] == pytest.approx(
        145_709_053_278.67368
    )
    assert cph_promotion["tracker_skip_semantics_inference_status"] == (
        "suggests_tracker_skips_include_intro_sprint"
    )
    assert cph_promotion["tracker_latest_coins_per_hour"] == pytest.approx(
        240_700_000_000_000.0
    )
    assert cph_promotion["tracker_recent_median_coins_per_hour"] == pytest.approx(
        227_145_000_000_000.0
    )
    assert cph_promotion["auto_current_cph_estimate"]["basis"] == (
        "latest_tracker_coin_density_current_timing"
    )
    assert cph_promotion["auto_current_cph_estimate"][
        "selected_projected_coins_per_hour"
    ] == pytest.approx(296_191_839_354_462.3)
    assert "tracker_wave_skip_intro_semantics_gap" in cph_promotion["blocking_reasons"]
    assert "operator_has_not_approved_tracker_empirical_cph_as_default" in cph_promotion[
        "blocking_reasons"
    ]

    trace = json.loads((out_dir / "pipeline_trace.json").read_text(encoding="utf-8"))
    assert trace["request"]["run_tracker_csv"].endswith("runs.csv")
    assert trace["stages"][0]["outputs_summary"]["run_tracker_csv"].endswith("runs.csv")


def test_boss_wave_tracker_reference_evidence_keeps_external_rows_non_authoritative(
    tmp_path: Path,
) -> None:
    from app.pipeline import _boss_wave_tracker_reference_evidence
    from input.run_tracker import summarize_run_tracker_csv

    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")
    evidence = summarize_run_tracker_csv(tracker)

    summary = _boss_wave_tracker_reference_evidence(
        [
            {
                "tier": 14,
                "dissonance_run_category": "none",
                "best_calculated_selected_max_wave": 7839,
                "best_selected_max_wave": 5761,
                "best_loadout_policy_preset": "eHP Max Waves",
                "model_closure_status": "partial_missing_required_model_inputs",
                "model_completion_blockers": ["source_owned_non_boss_terminal_pressure_formulas"],
            },
            {
                "tier": 15,
                "dissonance_run_category": "defense",
                "best_calculated_selected_max_wave": 5049,
                "best_selected_max_wave": 5049,
                "best_loadout_policy_preset": "eHP Max Waves",
                "model_closure_status": "partial_missing_required_model_inputs",
                "model_completion_blockers": ["source_owned_non_boss_terminal_pressure_formulas"],
            },
        ],
        evidence,
    )

    assert summary["status"] == "tracker_boss_wave_reference_evidence_available_not_applied"
    assert summary["certification_effect"] == "none"
    assert summary["matched_regular_reference_count"] == 1
    assert summary["dissonance_category_hint_reference_count"] == 1
    assert summary["unmapped_dissonance_reference_count"] == 0
    matched = summary["matched_regular_references"][0]
    assert matched["run_type"] == "Farming"
    assert matched["tracker_max_wave"] == 6518
    assert matched["matrix_dissonance_run_category"] == "none"
    assert matched["calculated_delta_vs_tracker_max_wave"] == 1321
    assert matched["selected_delta_vs_tracker_max_wave"] == -757
    hinted = summary["dissonance_category_hint_references"][0]
    assert hinted["run_type"] == "Dissonance"
    assert hinted["mapping_status"] == "tracker_dissonance_category_hint_available_not_applied"
    assert hinted["category_hint"]["category"] == "defense"
    assert hinted["category_hint"]["matched_token"] == "health"
    assert hinted["matrix_dissonance_run_category"] == "defense"
    assert hinted["calculated_delta_vs_tracker_max_wave"] == 0
    assert hinted["selected_delta_vs_tracker_max_wave"] == 0
    assert hinted["dissonance_bonus_cap_policy"] == {
        "user_reported_bonus_cap_wave": 5000,
        "tracker_at_or_above_bonus_cap": True,
        "application": "reference_context_only_not_selected_wave_cap",
    }
    assert hinted["tracker_dissonance_calibration_filter"] == {
        "status": "excluded_dissonance_bonus_cap_reference",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "user_reported_bonus_cap_wave": 5000,
        "tracker_at_or_above_bonus_cap": True,
        "tracker_below_3000_wave": False,
        "category_hint_available": True,
        "clean_tracker_calibration_candidate": False,
        "policy": (
            "Exclude Dissonance cap-floor rows; report sub-3000 rows as caveated "
            "sensitivity because perk variance can dominate; never auto-apply tracker rows."
        ),
    }
    assert summary["dissonance_tracker_calibration_filter"] == {
        "status": "tracker_dissonance_filter_evidence_available",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "dissonance_pb_5000_cap_policy": "excluded_from_calibration_lower_bound_only",
        "below_3000_wave_policy": "reported_as_caveated_sensitivity_not_clean_calibration",
        "dissonance_pb_5000_cap_reference_count": 1,
        "below_3000_wave_reference_count": 0,
        "clean_tracker_calibration_candidate_count": 0,
    }
    assert summary["dissonance_tracker_alignment_summary"] == {
        "status": "tracker_dissonance_alignment_available_not_applied",
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "reference_count": 1,
        "category_hint_reference_count": 1,
        "unmapped_reference_count": 0,
        "filter_status_counts": {"excluded_dissonance_bonus_cap_reference": 1},
        "category_hint_counts": {"defense": 1},
        "selected_delta_vs_tracker_max_wave_median": 0.0,
        "calculated_delta_vs_tracker_max_wave_median": 0.0,
        "selected_to_tracker_max_wave_ratio_median": 1.0,
        "calculated_to_tracker_max_wave_ratio_median": 1.0,
        "by_category": [
            {
                "dissonance_run_category": "defense",
                "reference_count": 1,
                "selected_delta_vs_tracker_max_wave_median": 0.0,
                "calculated_delta_vs_tracker_max_wave_median": 0.0,
                "selected_to_tracker_max_wave_ratio_median": 1.0,
                "calculated_to_tracker_max_wave_ratio_median": 1.0,
            }
        ],
        "interpretation": (
            "Category-hinted tracker Dissonance rows are summarized for review only; "
            "cap-floor and sub-3000 policies still decide calibration eligibility."
        ),
    }


def test_boss_wave_tracker_dissonance_filter_marks_sub_3000_as_caveated() -> None:
    from app.pipeline import _boss_wave_tracker_reference_evidence

    summary = _boss_wave_tracker_reference_evidence(
        [
            {
                "tier": 12,
                "dissonance_run_category": "utility",
                "best_calculated_selected_max_wave": 2500,
                "best_selected_max_wave": 2500,
            },
            {
                "tier": 13,
                "dissonance_run_category": "defense",
                "best_calculated_selected_max_wave": 3500,
                "best_selected_max_wave": 3500,
            },
        ],
        {
            "source": "fixture",
            "application": "external_observation_not_account_truth",
            "type_tier_summaries": [
                {
                    "run_type": "Dissonance",
                    "tier": 12,
                    "max_wave": 2500,
                    "row_count": 1,
                    "latest": {"wave": 2500},
                    "max_wave_record": {"note": "Econ Disco"},
                },
                {
                    "run_type": "Dissonance",
                    "tier": 13,
                    "max_wave": 3500,
                    "row_count": 1,
                    "latest": {"wave": 3500},
                    "max_wave_record": {"note": "Health Disco"},
                },
            ],
        },
    )

    filters = [
        row["tracker_dissonance_calibration_filter"]
        for row in summary["dissonance_category_hint_references"]
    ]
    assert filters[0]["status"] == "caveated_below_3000_reference"
    assert filters[0]["clean_tracker_calibration_candidate"] is False
    assert filters[1]["status"] == "candidate_category_hint_available_not_applied"
    assert filters[1]["clean_tracker_calibration_candidate"] is True
    assert summary["dissonance_tracker_calibration_filter"][
        "below_3000_wave_reference_count"
    ] == 1
    assert summary["dissonance_tracker_calibration_filter"][
        "clean_tracker_calibration_candidate_count"
    ] == 1
    alignment = summary["dissonance_tracker_alignment_summary"]
    assert alignment["status"] == "tracker_dissonance_alignment_available_not_applied"
    assert alignment["reference_count"] == 2
    assert alignment["category_hint_reference_count"] == 2
    assert alignment["filter_status_counts"] == {
        "candidate_category_hint_available_not_applied": 1,
        "caveated_below_3000_reference": 1,
    }
    assert alignment["category_hint_counts"] == {"defense": 1, "utility": 1}
    assert alignment["selected_to_tracker_max_wave_ratio_median"] == 1.0


def test_dissonance_tracker_note_hint_prefers_primary_econ_label() -> None:
    from app.pipeline import _tracker_dissonance_category_hint

    hint = _tracker_dissonance_category_hint(
        {
            "max_wave_record": {
                "note": "Econ Disco (eHP)",
            },
        }
    )

    assert hint["status"] == "available_not_authoritative"
    assert hint["category"] == "utility"
    assert hint["matched_token"] == "econ"
