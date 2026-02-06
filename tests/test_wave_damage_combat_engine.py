from __future__ import annotations

import math
import pytest

from tower_sim.engines.combat.combat_engine import resolve_wave_damage, resolve_wave_health
from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib


def test_resolve_wave_damage_from_canonical_table_anchor() -> None:
    assert resolve_wave_damage("Tier 12", 1) == pytest.approx(14710000.0)


def test_resolve_wave_damage_interpolates_log_linearly_between_anchors() -> None:
    # Tier 12 anchors at waves 100 and 150 are 5.49e9 and 1.557e10 in canonical table.
    lo = 5.49e9
    hi = 1.557e10
    t = (125 - 100) / (150 - 100)
    expected = math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * t)
    assert resolve_wave_damage("Tier 12", 125) == pytest.approx(expected)


def test_resolve_wave_damage_below_min_raises_and_above_max_clamps() -> None:
    with pytest.raises(KeyError, match="min anchor"):
        resolve_wave_damage("Tier 12", 0)

    max_wave = max(EnemyWaveDamageLib.from_repo_tables().tables["Tier 12"])
    assert resolve_wave_damage("Tier 12", max_wave + 1000) == pytest.approx(resolve_wave_damage("Tier 12", max_wave))


def test_resolve_wave_health_interpolates_log_linearly() -> None:
    lo = 8.96e15
    hi = 3.924e16
    t = (125 - 100) / (150 - 100)
    expected = math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * t)
    assert resolve_wave_health("Tier 13", 125) == pytest.approx(expected)
