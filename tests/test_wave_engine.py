from __future__ import annotations

from pathlib import Path
import sys


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.wave_engine import (  # noqa: E402
    SkipRamp,
    enemy_wave_index,
    expected_skipped_waves,
    make_wave_state,
)


def test_skip_ramp_interpolation() -> None:
    ramp = SkipRamp(start=0.0, end=1.0, ramp_waves=3)

    assert ramp.p(0) == 0.0
    assert ramp.p(1) == 0.0
    assert ramp.p(2) == 0.5
    assert ramp.p(3) == 1.0
    assert ramp.p(4) == 1.0


def test_expected_skipped_waves_linear_then_flat() -> None:
    ramp = SkipRamp(start=0.0, end=1.0, ramp_waves=3)

    assert expected_skipped_waves(0, ramp) == 0.0
    assert expected_skipped_waves(1, ramp) == 0.0
    assert expected_skipped_waves(2, ramp) == 0.5
    assert expected_skipped_waves(3, ramp) == 1.5
    assert expected_skipped_waves(4, ramp) == 2.5


def test_enemy_wave_index_and_state() -> None:
    ramp = SkipRamp(start=0.0, end=1.0, ramp_waves=3)

    assert enemy_wave_index(0, ramp) == 0
    assert enemy_wave_index(1, ramp) == 1
    assert enemy_wave_index(4, ramp) == 1

    state = make_wave_state(4, eals=ramp, ehls=ramp)
    assert state.W_actual == 4
    assert state.W_attack == 1
    assert state.W_health == 1
