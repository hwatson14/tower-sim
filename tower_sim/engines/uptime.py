from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from tower_sim.libs.bots_lib import get_bot_attribute
from tower_sim.libs.modules_lib import load_modules_library, unique_effect_value

Interval = Tuple[float, float]


@dataclass(frozen=True)
class TimedEffect:
    name: str
    activation_intervals: Tuple[Interval, ...]
    coin_multiplier: float = 1.0
    damage_reduction: float = 0.0
    damage_multiplier: float = 1.0


@dataclass(frozen=True)
class UptimeSummary:
    state_fractions: Dict[Tuple[str, ...], float]
    expected_coin_multiplier: float
    expected_damage_taken: float
    expected_damage_multiplier: float


def gcomp_sec(rarity: str) -> float:
    """Canonical Galaxy Compressor seconds-per-package from module effect tables."""
    return unique_effect_value("Galaxy Compressor", rarity, load_modules_library())


def build_periodic_activation_intervals(
    *,
    duration_s: float,
    cooldown_s: float,
    window_s: float,
    phase_s: float = 0.0,
) -> Tuple[Interval, ...]:
    if cooldown_s <= 0:
        raise ValueError("cooldown_s must be > 0")
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    if window_s <= 0:
        raise ValueError("window_s must be > 0")

    intervals: List[Interval] = []
    start = phase_s
    while start < window_s:
        end = min(start + duration_s, window_s)
        if end > 0 and end > start:
            intervals.append((max(0.0, start), end))
        start += cooldown_s
    return tuple(intervals)


def build_gcomp_activation_intervals(
    *,
    base_cooldown_s: float,
    duration_s: float,
    package_event_times_s: Sequence[float],
    seconds_reduced_per_package: float,
    window_s: float,
    start_on_cooldown: bool = True,
) -> Tuple[Interval, ...]:
    if base_cooldown_s <= 0:
        raise ValueError("base_cooldown_s must be > 0")
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    if window_s <= 0:
        raise ValueError("window_s must be > 0")

    events = sorted(event for event in package_event_times_s if 0.0 <= event <= window_s)
    intervals: List[Interval] = []

    remaining_cd = base_cooldown_s
    current_time = 0.0
    if not start_on_cooldown:
        end0 = min(duration_s, window_s)
        if end0 > 0.0:
            intervals.append((0.0, end0))
    idx = 0
    while current_time < window_s:
        trigger_time = current_time + remaining_cd

        while idx < len(events) and events[idx] <= trigger_time:
            event_time = events[idx]
            elapsed = event_time - current_time
            remaining_cd -= elapsed
            if seconds_reduced_per_package >= remaining_cd:
                trigger_time = event_time
                current_time = event_time
                remaining_cd = base_cooldown_s
                idx += 1
                break
            remaining_cd -= seconds_reduced_per_package
            current_time = event_time
            trigger_time = current_time + remaining_cd
            idx += 1
        else:
            current_time = trigger_time
            remaining_cd = base_cooldown_s

        if current_time >= window_s:
            break
        end = min(current_time + duration_s, window_s)
        if end > current_time:
            intervals.append((current_time, end))

    return tuple(intervals)


def overlap_fraction(
    left: Sequence[Interval],
    right: Sequence[Interval],
    *,
    window_s: float,
) -> float:
    if window_s <= 0:
        raise ValueError("window_s must be > 0")
    points = _boundaries(list(left) + list(right), window_s)
    active = 0.0
    for seg_start, seg_end in zip(points, points[1:]):
        if _is_active(left, seg_start, seg_end) and _is_active(right, seg_start, seg_end):
            active += seg_end - seg_start
    return active / window_s


def aggregate_uptime(
    effects: Iterable[TimedEffect],
    *,
    window_s: float,
) -> UptimeSummary:
    if window_s <= 0:
        raise ValueError("window_s must be > 0")
    effect_list = list(effects)
    points = _boundaries(
        [interval for effect in effect_list for interval in effect.activation_intervals],
        window_s,
    )

    state_fractions: Dict[Tuple[str, ...], float] = {}
    coin_sum = 0.0
    taken_sum = 0.0
    damage_mult_sum = 0.0
    for seg_start, seg_end in zip(points, points[1:]):
        seg_len = seg_end - seg_start
        if seg_len <= 0:
            continue
        active = [
            effect
            for effect in effect_list
            if _is_active(effect.activation_intervals, seg_start, seg_end)
        ]
        state_key = tuple(sorted(effect.name for effect in active))
        frac = seg_len / window_s
        state_fractions[state_key] = state_fractions.get(state_key, 0.0) + frac

        coin_mult = 1.0
        damage_taken = 1.0
        damage_mult = 1.0
        for effect in active:
            coin_mult *= effect.coin_multiplier
            damage_taken *= (1.0 - effect.damage_reduction)
            damage_mult *= effect.damage_multiplier
        coin_sum += frac * coin_mult
        taken_sum += frac * damage_taken
        damage_mult_sum += frac * damage_mult

    return UptimeSummary(
        state_fractions=state_fractions,
        expected_coin_multiplier=coin_sum,
        expected_damage_taken=taken_sum,
        expected_damage_multiplier=damage_mult_sum,
    )


def build_bot_effects(
    *,
    bot_levels: Dict[str, Dict[str, int]],
    window_s: float,
) -> Tuple[TimedEffect, ...]:
    effects: List[TimedEffect] = []

    def _bot_intervals(bot_name: str) -> Tuple[Interval, ...]:
        if bot_name not in bot_levels:
            return tuple()
        bot = bot_levels[bot_name]
        if "Duration" not in bot or "Cooldown" not in bot:
            return tuple()
        duration, _, _ = get_bot_attribute(bot_name, "Duration", bot["Duration"])
        cooldown, _, _ = get_bot_attribute(bot_name, "Cooldown", bot["Cooldown"])
        return build_periodic_activation_intervals(
            duration_s=float(duration),
            cooldown_s=float(cooldown),
            window_s=window_s,
            phase_s=0.0,
        )

    flame_intervals = _bot_intervals("Flame Bot")
    if flame_intervals and "Damage R." in bot_levels.get("Flame Bot", {}):
        value, _, _ = get_bot_attribute("Flame Bot", "Damage R.", bot_levels["Flame Bot"]["Damage R."])
        effects.append(TimedEffect("Flame Bot", flame_intervals, damage_reduction=float(value)))

    golden_intervals = _bot_intervals("Golden Bot")
    if golden_intervals and "Bonus" in bot_levels.get("Golden Bot", {}):
        value, _, _ = get_bot_attribute("Golden Bot", "Bonus", bot_levels["Golden Bot"]["Bonus"])
        effects.append(TimedEffect("Golden Bot", golden_intervals, coin_multiplier=float(value)))

    amplify_intervals = _bot_intervals("Amplify Bot")
    if amplify_intervals and "Bonus" in bot_levels.get("Amplify Bot", {}):
        value, _, _ = get_bot_attribute("Amplify Bot", "Bonus", bot_levels["Amplify Bot"]["Bonus"])
        effects.append(TimedEffect("Amplify Bot", amplify_intervals, damage_multiplier=float(value)))

    return tuple(effects)


def uniform_event_times_from_rate(*, rate_per_second: float, window_s: float) -> Tuple[float, ...]:
    if window_s <= 0:
        raise ValueError("window_s must be > 0")
    if rate_per_second < 0:
        raise ValueError("rate_per_second must be >= 0")
    count = int(rate_per_second * window_s)
    if count <= 0:
        return tuple()
    step = window_s / count
    return tuple(i * step for i in range(count))


def _boundaries(intervals: Sequence[Interval], window_s: float) -> List[float]:
    points = {0.0, window_s}
    for start, end in intervals:
        if end <= 0 or start >= window_s:
            continue
        points.add(max(0.0, start))
        points.add(min(window_s, end))
    return sorted(points)


def _is_active(intervals: Sequence[Interval], seg_start: float, seg_end: float) -> bool:
    for start, end in intervals:
        if start <= seg_start and seg_end <= end:
            return True
    return False
