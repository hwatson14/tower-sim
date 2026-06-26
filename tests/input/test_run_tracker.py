from __future__ import annotations

from pathlib import Path

import pytest

from input.run_tracker import (
    parse_tracker_duration_seconds,
    parse_tracker_number,
    summarize_run_tracker_csv,
)

pytestmark = pytest.mark.live


TRACKER_CSV = """verified,createdAt,updatedAt,source,tier,wave,duration,coins,cells,killedBy,note,runDate,runTime,type,gameTime,coinsPerHour,cellsPerHour,wavesSkipped,coinsFromWaveSkip,coinsPerWave,mostCoinsFromWaveSkip,totalEnemies,basic,fast,tank,ranged,boss,protector,totalElites,vampires,rays,scatters,saboteurs,commanders,overcharges,coinsFromDeathWave,coinsFromGoldenTower,coinsFromBlackhole,coinsFromSpotlight,goldenBotCoinsEarned,coinsFromGoldenCombo,wavesPerHour
,2026-06-08T00:00:00Z,2026-06-08T00:00:00Z,web,14,5502,5h30m36s,1.18q,180K,Scatter,,2026-06-08,13:00:00,Farming,1d0h0m0s,213.59T,32K,2243,286.20T,218.92B,6.03T,700000,250000,200000,150000,99000,500,500,800,300,250,250,0,0,0,838.42T,809.16T,776.27T,413.89T,708.82T,256.23T,998.55
,2026-06-13T00:00:00Z,2026-06-13T00:00:00Z,web,14,6518,6h46m0s,1.63q,234.37K,Scatter,,2026-06-13,13:29:00,Farming,1d9h43m44s,240.70T,34.64K,2460,403.00T,286.20B,6.89T,952172,300000,250000,220000,180000,650,1522,931,320,300,311,0,0,0,1.20q,1.16q,1.11q,600.95T,1.01q,403.00T,963.25
true,2026-06-12T00:00:00Z,2026-06-12T00:00:00Z,web,15,5049,5h42m58s,23.13T,121.23K,Boss,Health Disco,2026-06-10,21:27:00,Dissonance,1d4h13m1s,4.05T,21.21K,2130,0,0,0,350087,100000,90000,80000,79000,400,687,746,250,250,246,0,0,0,0,0,0,0,0,0,883.36
"""


def test_tracker_number_and_duration_parsers_handle_export_units() -> None:
    assert parse_tracker_number("240.70T") == 240_700_000_000_000.0
    assert parse_tracker_number("1.63q") == 1_630_000_000_000_000.0
    assert parse_tracker_number("234.37K") == 234_370.0
    assert parse_tracker_duration_seconds("1d9h43m44s") == 121424.0


def test_summarize_run_tracker_csv_publishes_external_observation_summary(tmp_path: Path) -> None:
    tracker = tmp_path / "runs.csv"
    tracker.write_text(TRACKER_CSV, encoding="utf-8")

    summary = summarize_run_tracker_csv(tracker)

    assert summary["source"] == "tower_run_tracker_csv"
    assert summary["application"] == "external_observation_not_account_truth"
    assert summary["calibration_policy"]["status"] == "evidence_available_not_auto_applied"
    assert summary["row_count"] == 3
    assert summary["run_type_counts"] == {"Dissonance": 1, "Farming": 2}
    assert summary["farming_t14_recent"]["latest"]["wave"] == 6518
    assert summary["farming_t14_recent"]["latest"]["observed_coins_per_enemy"] == pytest.approx(
        1_711_875_585.5034595
    )
    assert summary["farming_t14_recent"]["latest"]["observed_enemies_per_wave"] == pytest.approx(
        146.08346118441239
    )
    assert summary["farming_t14_recent"]["latest"]["observed_coins_per_wave"] == pytest.approx(
        250_076_710_647.43784
    )
    assert summary["farming_t14_recent"]["latest"][
        "observed_cph_from_density_components"
    ] == pytest.approx(240_886_699_507_389.16)
    assert summary["farming_t14_recent"]["coins_per_hour"]["median"] == pytest.approx(
        227_145_000_000_000.0
    )
    assert summary["farming_t14_recent"]["tracker_game_time_hours"]["median"] == pytest.approx(
        28.864444444444445
    )
    assert summary["farming_t14_recent"]["tracker_game_to_real_duration_ratio"][
        "median"
    ] == pytest.approx(4.670140869414917)
    assert summary["farming_t14_recent"]["observed_waves_per_hour"]["median"] == pytest.approx(
        980.8996629504798
    )
    assert summary["farming_t14_recent"]["tracker_waves_per_hour"]["median"] == pytest.approx(
        980.9
    )
    assert summary["farming_t14_recent"]["tracker_to_observed_waves_per_hour_ratio"][
        "median"
    ] == pytest.approx(1.0000003149430778)
    assert summary["farming_t14_recent"]["observed_seconds_per_wave"]["median"] == pytest.approx(
        3.6712886016845223
    )
    assert summary["farming_t14_recent"]["observed_enemies_per_wave"]["median"] == pytest.approx(
        136.65496214436905
    )
    composition = summary["farming_t14_recent"]["tracker_enemy_composition"]
    assert composition["status"] == "tracker_enemy_composition_available"
    assert composition["available_normal_enemy_field_count"] == 6
    assert composition["available_elite_enemy_field_count"] == 6
    assert composition["normal_enemy_counts"]["basic"]["count"]["median"] == pytest.approx(
        275_000.0
    )
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
    assert summary["farming_t14_recent"]["observed_coins_per_enemy"]["median"] == pytest.approx(
        1_698_794_935.6088724
    )
    assert summary["farming_t14_recent"]["observed_coins_per_wave"]["median"] == pytest.approx(
        232_272_088_511.65057
    )
    assert summary["farming_t14_recent"]["observed_cph_from_run_totals"]["median"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert summary["farming_t14_recent"]["observed_cph_to_tracker_reported_ratio"][
        "median"
    ] == pytest.approx(1.0017129814796646)
    assert summary["farming_t14_recent"]["tracker_coins_from_wave_skip"]["median"] == pytest.approx(
        344_600_000_000_000.0
    )
    assert summary["farming_t14_recent"]["tracker_coins_per_wave"]["median"] == pytest.approx(
        252_560_000_000.0
    )
    assert summary["farming_t14_recent"]["tracker_coins_per_wave_to_observed_ratio"][
        "median"
    ] == pytest.approx(1.0826048578558802)
    assert summary["farming_t14_recent"]["tracker_wave_skip_coin_share"]["median"] == pytest.approx(
        0.24489081834251847
    )
    assert summary["farming_t14_recent"]["tracker_wave_skip_coins_per_skipped_wave"][
        "median"
    ] == pytest.approx(145_709_053_278.67368)
    econ_sources = summary["farming_t14_recent"]["tracker_econ_coin_sources"]
    assert econ_sources["status"] == "tracker_econ_coin_sources_available"
    assert econ_sources["available_source_count"] == 6
    assert econ_sources["tracked_source_coin_sum"]["median"] == pytest.approx(
        4_643_370_000_000_000.0
    )
    assert econ_sources["tracked_source_sum_to_run_coins_ratio"]["median"] == pytest.approx(
        3.2935449464489963
    )
    assert econ_sources["overlap_evidence_status"] == "source_splits_overlap_or_double_count"
    assert econ_sources["sources"]["coins_from_golden_tower"]["coins"]["median"] == pytest.approx(
        984_580_000_000_000.0
    )
    assert econ_sources["sources"]["coins_from_golden_tower"]["share_of_run_coins"][
        "median"
    ] == pytest.approx(0.6986926276385568)
    assert econ_sources["sources"]["coins_from_black_hole"]["share_of_run_coins"][
        "median"
    ] == pytest.approx(0.6694187636477071)
    assert econ_sources["sources"]["golden_bot_coins_earned"]["share_of_run_coins"][
        "median"
    ] == pytest.approx(0.610163408547364)
    assert summary["farming_t14_recent"]["observed_cph_from_density_components"]["median"] == pytest.approx(
        227_521_389_681_099.3
    )
    assert summary["input_schema"]["missing_required_columns"] == []
