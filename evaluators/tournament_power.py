from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChronoFieldControl:
    """Condition-aware Chrono Field control inputs.

    Fractions use [0, 1] units. `uwd_duration_penalty_seconds` is a positive
    number representing seconds removed by the Ultimate Weapon Duration battle
    condition.
    """

    base_duration_seconds: float
    cooldown_seconds: float
    speed_reduction: float
    uwd_duration_penalty_seconds: float = 0.0
    primary_duration_bonus_seconds: float = 0.0
    assist_duration_bonus_seconds: float = 0.0
    assist_substat_efficiency: float = 0.0

    def __post_init__(self) -> None:
        if self.base_duration_seconds < 0:
            raise ValueError("base_duration_seconds must be non-negative")
        if self.cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        if not 0 <= self.speed_reduction < 1:
            raise ValueError("speed_reduction must be in [0, 1)")
        if self.uwd_duration_penalty_seconds < 0:
            raise ValueError("uwd_duration_penalty_seconds must be non-negative")
        if not 0 <= self.assist_substat_efficiency:
            raise ValueError("assist_substat_efficiency must be non-negative")


@dataclass(frozen=True)
class InnerLandMineControl:
    base_quantity: float
    cooldown_seconds: float
    stun_seconds: float
    primary_quantity_bonus: float = 0.0
    assist_quantity_bonus: float = 0.0
    assist_substat_efficiency: float = 0.0

    def __post_init__(self) -> None:
        if self.base_quantity < 0:
            raise ValueError("base_quantity must be non-negative")
        if self.cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        if self.stun_seconds < 0:
            raise ValueError("stun_seconds must be non-negative")
        if not 0 <= self.assist_substat_efficiency:
            raise ValueError("assist_substat_efficiency must be non-negative")


def chrono_field_effective_duration_seconds(control: ChronoFieldControl) -> float:
    """Return CF duration after module bonuses and UWD penalty."""

    duration = (
        control.base_duration_seconds
        + control.primary_duration_bonus_seconds
        + control.assist_duration_bonus_seconds * control.assist_substat_efficiency
        - control.uwd_duration_penalty_seconds
    )
    return max(0.0, duration)


def chrono_field_uptime(control: ChronoFieldControl) -> float:
    return min(
        1.0,
        chrono_field_effective_duration_seconds(control) / control.cooldown_seconds,
    )


def chrono_field_exposure_factor(control: ChronoFieldControl) -> float:
    """Return the planner's movement/exposure proxy for intermittent CF.

    This is an accepted planning proxy, not a native game stat:
      1 / (1 - slow * uptime)

    It reduces to the usual continuous slow factor when uptime is 100%.
    """

    uptime = chrono_field_uptime(control)
    denominator = 1.0 - control.speed_reduction * uptime
    if denominator <= 0:
        raise ValueError("Chrono Field exposure denominator must be positive")
    return 1.0 / denominator


def inner_land_mine_effective_quantity(control: InnerLandMineControl) -> float:
    return (
        control.base_quantity
        + control.primary_quantity_bonus
        + control.assist_quantity_bonus * control.assist_substat_efficiency
    )


def inner_land_mine_generation_per_second(control: InnerLandMineControl) -> float:
    return inner_land_mine_effective_quantity(control) / control.cooldown_seconds


def inner_land_mine_stun_capacity_per_cycle(control: InnerLandMineControl) -> float:
    """Potential stun-seconds per natural ILM cycle before trigger/overlap effects."""

    return inner_land_mine_effective_quantity(control) * control.stun_seconds
