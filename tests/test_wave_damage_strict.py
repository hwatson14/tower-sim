from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.enemies.wave_damage_strict import EnemyWaveDamageLib


def test_wave_damage_strict_tier_samples():
    lib = EnemyWaveDamageLib.from_repo_tables()
    assert lib.wave_damage_exact("Tier 14", 70) == pytest.approx(1.6719e11)
    assert lib.wave_damage_exact("Tier 14", 1000) == pytest.approx(8.0491e14)
    assert lib.wave_damage_exact("Tier 15", 500) == pytest.approx(3.7146e14)


def test_wave_damage_strict_tournament_samples():
    lib = EnemyWaveDamageLib.from_repo_tables()
    assert lib.wave_damage_exact("Champion", 1000) == pytest.approx(2.404e13)
    assert lib.wave_damage_exact("Legend", 150) == pytest.approx(6.595e13)
