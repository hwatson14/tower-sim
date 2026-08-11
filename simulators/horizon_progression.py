from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HorizonResourceRates:
    """Continuous resource-rate assumptions used by horizon planning."""

    coins_per_day: float
    stones_per_day: float
    module_shards_per_type_per_day: float

    def __post_init__(self) -> None:
        for name, value in (
            ("coins_per_day", self.coins_per_day),
            ("stones_per_day", self.stones_per_day),
            ("module_shards_per_type_per_day", self.module_shards_per_type_per_day),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


def unlock_day(
    cumulative_cost: float,
    *,
    starting_balance: float = 0.0,
    income_per_day: float,
) -> float:
    """Return continuous day-offset when a cumulative resource cost is affordable."""

    if cumulative_cost < 0:
        raise ValueError("cumulative_cost must be non-negative")
    if starting_balance < 0:
        raise ValueError("starting_balance must be non-negative")
    if cumulative_cost <= starting_balance:
        return 0.0
    if income_per_day <= 0:
        raise ValueError("income_per_day must be positive when cost exceeds starting balance")
    return (cumulative_cost - starting_balance) / income_per_day


def piecewise_income(
    horizon_days: float,
    *,
    base_income_per_day: float,
    multiplier: float = 1.0,
    multiplier_start_day: float | None = None,
    starting_balance: float = 0.0,
) -> float:
    """Accrue a base income rate with one optional permanent multiplier breakpoint."""

    if horizon_days < 0:
        raise ValueError("horizon_days must be non-negative")
    if base_income_per_day < 0:
        raise ValueError("base_income_per_day must be non-negative")
    if starting_balance < 0:
        raise ValueError("starting_balance must be non-negative")
    if multiplier < 0:
        raise ValueError("multiplier must be non-negative")

    if multiplier_start_day is None or multiplier_start_day >= horizon_days:
        return starting_balance + horizon_days * base_income_per_day

    start = max(0.0, multiplier_start_day)
    return (
        starting_balance
        + start * base_income_per_day
        + (horizon_days - start) * base_income_per_day * multiplier
    )


def module_shards_after_days(
    days: float,
    *,
    starting_shards: float,
    shards_per_day: float,
) -> float:
    """Return one module-type shard pool after continuous farming."""

    if days < 0:
        raise ValueError("days must be non-negative")
    if starting_shards < 0:
        raise ValueError("starting_shards must be non-negative")
    if shards_per_day < 0:
        raise ValueError("shards_per_day must be non-negative")
    return starting_shards + days * shards_per_day
