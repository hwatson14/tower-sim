from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class SkipRamp:
    """Piecewise-linear skip chance ramp.

    We represent the per-wave skip probability p(w) as:
    - linear ramp from start to end over waves 1..ramp_waves
    - constant end after ramp_waves

    All probabilities are fractions (e.g. 0.30 for 30%).
    """

    start: float
    end: float
    ramp_waves: int = 1000

    def p(self, w: int) -> float:
        if w <= 0:
            return 0.0
        if w >= self.ramp_waves:
            return self.end
        if self.ramp_waves <= 1:
            return self.end
        # w in [1, ramp_waves-1] uses linear interpolation over endpoints inclusive
        t = (w - 1) / (self.ramp_waves - 1)
        return self.start + (self.end - self.start) * t


def _sum_linear_endpoints(start: float, end: float, n: int) -> float:
    """Sum of n equally-spaced linear values with endpoints start and end.

    If values are v1=start, vn=end, then sum = n*(start+end)/2.
    """
    if n <= 0:
        return 0.0
    return n * (start + end) / 2.0


def expected_skipped_waves(W_actual: int, ramp: SkipRamp) -> float:
    """Expected number of skipped waves up to actual wave W_actual.

    Deterministic expected value calculation using the ramp definition.
    """
    W = int(W_actual)
    if W <= 0:
        return 0.0

    R = max(1, int(ramp.ramp_waves))
    if W <= R:
        # Sum p(1..W) where p is linear from start at w=1 to p(R)=end.
        if W == 1:
            return max(0.0, ramp.start)
        # The value at wave W is ramp.p(W) (linear to end across 1..R)
        return _sum_linear_endpoints(ramp.start, ramp.p(W), W)

    # W > R: sum ramp region + flat region
    ramp_sum = _sum_linear_endpoints(ramp.start, ramp.end, R)
    flat_sum = (W - R) * ramp.end
    return ramp_sum + flat_sum


def enemy_wave_index(W_actual: int, ramp: SkipRamp) -> int:
    """Map actual wave -> integer enemy-stat wave index after skips.

    Rule: enemy waves are integers.
    """
    W = int(W_actual)
    skipped = expected_skipped_waves(W, ramp)
    idx = floor(W - skipped)
    return max(0, int(idx))


@dataclass(frozen=True)
class RunWaveState:
    W_actual: int
    W_attack: int
    W_health: int


def make_wave_state(W_actual: int, eals: SkipRamp, ehls: SkipRamp) -> RunWaveState:
    return RunWaveState(
        W_actual=int(W_actual),
        W_attack=enemy_wave_index(W_actual, eals),
        W_health=enemy_wave_index(W_actual, ehls),
    )
