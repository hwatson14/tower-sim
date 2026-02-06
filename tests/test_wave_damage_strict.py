from pathlib import Path
import sys

import math
import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.wave_damage_strict import (  # noqa: E402
    EnemyWaveDamageLib,
    EnemyWaveHealthLib,
    interpolate_anchor_series,
    load_enemy_damage_tables,
    load_enemy_health_tables,
)


def test_wave_damage_table_samples_from_canonical_enemy_damage_table() -> None:
    lib = EnemyWaveDamageLib.from_repo_tables()
    assert lib.wave_damage_exact("Tier 14", 70) == pytest.approx(1.6719e11)
    assert lib.wave_damage_exact("Tier 14", 1000) == pytest.approx(8.0491e14)
    assert lib.wave_damage_exact("Tier 15", 500) == pytest.approx(3.7146e14)
    assert lib.wave_damage_exact("Champion", 1000) == pytest.approx(1.85e15)


def test_wave_health_table_samples_from_canonical_enemy_health_table() -> None:
    lib = EnemyWaveHealthLib.from_repo_tables()
    assert lib.wave_health("Tier 14", 70) == pytest.approx(1.15e18)
    assert lib.wave_health("Tier 14", 1000) == pytest.approx(2.09e24)
    assert lib.wave_health("Tier 15", 500) == pytest.approx(7.52e24)


def test_log_linear_interpolation_midpoint_contract() -> None:
    lib = EnemyWaveDamageLib.from_repo_tables()
    anchors = load_enemy_damage_tables()["Tier 14"]
    lo_wave = 100
    hi_wave = 150
    mid_wave = 125
    lo = anchors[lo_wave]
    hi = anchors[hi_wave]
    t = (mid_wave - lo_wave) / (hi_wave - lo_wave)
    expected = math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * t)
    assert lib.wave_damage("Tier 14", mid_wave) == pytest.approx(expected)


def test_log_linear_interpolation_below_min_raises() -> None:
    anchors = load_enemy_damage_tables()["Tier 14"]
    min_wave = min(anchors)
    with pytest.raises(KeyError, match=f"min anchor {min_wave}"):
        interpolate_anchor_series(anchors, min_wave - 1)


def test_log_linear_interpolation_above_max_clamps() -> None:
    anchors = load_enemy_damage_tables()["Tier 14"]
    max_wave = max(anchors)
    assert interpolate_anchor_series(anchors, max_wave + 500) == pytest.approx(anchors[max_wave])


def test_health_uses_same_log_linear_interpolation_contract() -> None:
    anchors = load_enemy_health_tables()["Tier 14"]
    lo_wave = 100
    hi_wave = 150
    mid_wave = 125
    lo = anchors[lo_wave]
    hi = anchors[hi_wave]
    t = (mid_wave - lo_wave) / (hi_wave - lo_wave)
    expected = math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * t)
    assert interpolate_anchor_series(anchors, mid_wave) == pytest.approx(expected)


def test_runtime_loader_uses_canonical_wide_enemy_tables_only(monkeypatch):
    import tower_sim.libs.wave_damage_strict as mod

    touched = []
    real_read = mod._read_csv_rows

    def _tracking_read(path):
        touched.append(path.name)
        return real_read(path)

    monkeypatch.setattr(mod, "_read_csv_rows", _tracking_read)

    mod.load_enemy_damage_tables()
    mod.load_enemy_health_tables()

    assert "enemy_damage_table.csv" in touched
    assert "enemy_health_table.csv" in touched
    assert "tier_enemy_damage.csv" not in touched
    assert "tier_enemy_health.csv" not in touched
