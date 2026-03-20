from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

from engine.scenario_engine import ScenarioConfig, ScenarioSurfaces

ROOT = Path(__file__).resolve().parents[1]
ORB_BOSS_HIT_LEVELS_TABLE = ROOT / "kb" / "global-rules" / "tables" / "note-derived-orb-boss-hit-levels-1-10.csv"


def _uptime(duration: float, cooldown: float) -> float:
    """uptime = duration / (duration + cooldown), clamped [0, 1]."""
    total = max(0.0, duration) + max(0.0, cooldown)
    if total <= 0.0:
        return 0.0
    return min(1.0, max(0.0, duration) / total)


def _lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return max(a, b)
    return abs(a * b) // gcd(a, b)


def _fraction_from_float(value: float) -> Fraction:
    return Fraction(str(float(value))).limit_denominator(1000000)


def shared_cycle_seconds(periods: Iterable[float]) -> float:
    fracs = [_fraction_from_float(p) for p in periods if p > 0]
    if not fracs:
        return 0.0
    denom_lcm = 1
    for f in fracs:
        denom_lcm = _lcm(denom_lcm, f.denominator)
    ints = [f.numerator * (denom_lcm // f.denominator) for f in fracs]
    cycle_units = ints[0]
    for value in ints[1:]:
        cycle_units = _lcm(cycle_units, value)
    return float(Fraction(cycle_units, denom_lcm))


@dataclass(frozen=True)
class TimingMechanic:
    mechanic_id: str
    active_duration_s: float
    cooldown_s: float
    phase_offset_s: float = 0.0
    active_multiplier: float = 1.0

    @property
    def period_s(self) -> float:
        return max(0.0, self.active_duration_s) + max(0.0, self.cooldown_s)


@dataclass(frozen=True)
class TimingSegment:
    start_s: float
    end_s: float
    active_mechanics: List[str] = field(default_factory=list)
    combined_multiplier: float = 1.0


@dataclass(frozen=True)
class TimingSurfaces:
    bh_effective_duration_s: float = 0.0
    bh_effective_cooldown_s: float = 0.0
    bh_uptime_fraction: float = 0.0
    cf_effective_duration_s: float = 0.0
    cf_effective_cooldown_s: float = 0.0
    cf_uptime_fraction: float = 0.0
    gt_effective_duration_s: float = 0.0
    gt_effective_cooldown_s: float = 0.0
    gt_uptime_fraction: float = 0.0
    cf_damage_reduction_pct: float = 0.0
    cf_avg_damage_reduction_fraction: float = 0.0
    cf_slow_pct: float = 0.0
    bot_amplify_uptime_fraction: float = 0.0
    bot_golden_uptime_fraction: float = 0.0
    bot_thunder_uptime_fraction: float = 0.0
    bot_flame_cooldown_s: float = 0.0
    bot_flame_damage_reduction_pct: float = 0.0


@dataclass(frozen=True)
class CombatRuntimeSurfaces:
    boss_hit_interval_seconds: float
    orb_boss_hit_pct: Optional[float] = None
    orb_boss_hits_per_second: Optional[float] = None
    electron_hits_per_second: Optional[float] = None
    boss_contact_time_seconds: Optional[float] = None
    effective_damage_reduction_pct: Optional[float] = None
    incoming_damage_multiplier: Optional[float] = None
    source_notes: List[str] = field(default_factory=list)


def _load_orb_boss_hit_pct_by_level() -> Dict[int, float]:
    import csv
    out: Dict[int, float] = {}
    with ORB_BOSS_HIT_LEVELS_TABLE.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[int(row['level'])] = float(row['boss_max_hp_damage_pct'])
            except (TypeError, ValueError, KeyError):
                continue
    return out


def _lookup_row_value(row_map: Mapping[str, object], keys: List[str]) -> Optional[float]:
    for key in keys:
        row = row_map.get(key)
        if row is None:
            continue
        value = getattr(row, 'final_value', None) if not isinstance(row, dict) else row.get('final_value')
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def resolve_combat_runtime_surfaces(
    *,
    config: ScenarioConfig,
    scenario: ScenarioSurfaces,
    timing: TimingSurfaces,
    row_map: Optional[Mapping[str, object]] = None,
    account_state: Optional[object] = None,
    scenario_runtime_inputs: Optional[object] = None,
    orb_boss_hit_pct_override: Optional[float] = None,
    orb_boss_hits_per_second_override: Optional[float] = None,
    electron_hits_per_second_override: Optional[float] = None,
    boss_contact_time_seconds_override: Optional[float] = None,
    effective_damage_reduction_pct_override: Optional[float] = None,
    incoming_damage_multiplier_override: Optional[float] = None,
) -> CombatRuntimeSurfaces:
    notes: List[str] = []
    row_map = row_map or {}

    boss_hit_interval_override = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.boss_hit_interval_seconds',
        'runtime_mechanic_param::combat.boss_interval_seconds',
    ])
    if boss_hit_interval_override is not None:
        boss_hit_interval_seconds = float(boss_hit_interval_override)
        notes.append(f'Boss hit interval consumed from governed surface: {boss_hit_interval_seconds}s.')
    else:
        boss_hit_interval_seconds = float(scenario.boss_hit_interval_seconds)
        notes.append(f'Boss hit interval sourced from scenario engine: {boss_hit_interval_seconds}s.')

    orb_pct = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.orb_boss_hit_pct',
        'runtime_mechanic_param::tower.orb_boss_hit_pct',
        'runtime_mechanic_param::tower.orb.hit_pct_vs_boss',
    ])
    if orb_pct is not None:
        notes.append(f'Orb boss-hit pct consumed from governed surface: {orb_pct}.')
    else:
        lab_level = None
        if account_state is not None:
            labs = getattr(account_state, 'labs', {}) or {}
            try:
                lab_level = int(labs.get('Orb Boss Hit', 0) or 0)
            except (TypeError, ValueError):
                lab_level = 0
        if lab_level:
            orb_pct = _load_orb_boss_hit_pct_by_level().get(lab_level)
            if orb_pct is not None:
                notes.append(f'Orb boss-hit pct resolved from account lab level {lab_level} via KB table note-derived-orb-boss-hit-levels-1-10.csv: {orb_pct}.')
        if orb_pct is None and scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'orb_boss_hit_pct', None) is not None:
            orb_pct = float(scenario_runtime_inputs.orb_boss_hit_pct)
            notes.append(f'Orb boss-hit pct using scenario runtime input fallback: {orb_pct}.')
        if orb_pct is None and orb_boss_hit_pct_override is not None:
            orb_pct = float(orb_boss_hit_pct_override)
            notes.append(f'Orb boss-hit pct using explicit override fallback: {orb_pct}.')

    orb_hz = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.orb_boss_hits_per_second',
        'runtime_mechanic_param::tower.orb_boss_hits_per_second',
        'runtime_mechanic_param::tower.orb.hits_per_second_vs_boss',
    ])
    if orb_hz is not None:
        notes.append(f'Orb boss-hit cadence consumed from governed surface: {orb_hz} Hz.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'orb_boss_hits_per_second', None) is not None:
        orb_hz = float(scenario_runtime_inputs.orb_boss_hits_per_second)
        notes.append(f'Orb boss-hit cadence using scenario runtime input fallback: {orb_hz} Hz.')
    elif orb_boss_hits_per_second_override is not None:
        orb_hz = float(orb_boss_hits_per_second_override)
        notes.append(f'Orb boss-hit cadence using explicit override fallback: {orb_hz} Hz.')
    else:
        notes.append('Orb boss-hit cadence remains open: no defended formula in current KB/package.')

    electron_hz = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.electron_hits_per_second',
        'runtime_mechanic_param::module.orbital_augment.electron_hits_per_second',
        'runtime_mechanic_param::module.orbital_augment.hits_per_second_vs_boss',
    ])
    if electron_hz is not None:
        notes.append(f'Electron cadence consumed from governed surface: {electron_hz} Hz.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'electron_hits_per_second', None) is not None:
        electron_hz = float(scenario_runtime_inputs.electron_hits_per_second)
        notes.append(f'Electron cadence using scenario runtime input fallback: {electron_hz} Hz.')
    elif electron_hits_per_second_override is not None:
        electron_hz = float(electron_hits_per_second_override)
        notes.append(f'Electron cadence using explicit override fallback: {electron_hz} Hz.')
    else:
        notes.append('Electron cadence remains open: Orbital Augment speed is not governed in current KB/package.')

    contact_t = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.boss_contact_time_seconds',
        'runtime_mechanic_param::combat.contact_time_seconds_vs_boss',
    ])
    if contact_t is not None:
        notes.append(f'Boss contact time consumed from governed surface: {contact_t}s.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'boss_contact_time_seconds', None) is not None:
        contact_t = float(scenario_runtime_inputs.boss_contact_time_seconds)
        notes.append(f'Boss contact time using scenario runtime input fallback: {contact_t}s.')
    elif boss_contact_time_seconds_override is not None:
        contact_t = float(boss_contact_time_seconds_override)
        notes.append(f'Boss contact time using explicit override fallback: {contact_t}s.')
    else:
        notes.append('Boss contact time remains open: no defended contact-distance/speed formula in current KB/package.')

    effective_dr = _lookup_row_value(row_map, [
        'runtime_mechanic_param::combat.effective_damage_reduction_pct',
    ])
    if effective_dr is not None:
        notes.append(f'Effective damage reduction consumed from governed surface: {effective_dr}%.')
    elif scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'effective_damage_reduction_pct', None) is not None:
        effective_dr = float(scenario_runtime_inputs.effective_damage_reduction_pct)
        notes.append(f'Effective damage reduction using scenario runtime input fallback: {effective_dr}%.')
    elif effective_damage_reduction_pct_override is not None:
        effective_dr = float(effective_damage_reduction_pct_override)
        notes.append(f'Effective damage reduction using explicit override fallback: {effective_dr}%.')

    incoming_damage_multiplier = None
    if scenario_runtime_inputs is not None and getattr(scenario_runtime_inputs, 'incoming_damage_multiplier', None) is not None:
        incoming_damage_multiplier = float(scenario_runtime_inputs.incoming_damage_multiplier)
        notes.append(f'Incoming damage multiplier using scenario runtime input: {incoming_damage_multiplier}.')
    elif incoming_damage_multiplier_override is not None:
        incoming_damage_multiplier = float(incoming_damage_multiplier_override)

    return CombatRuntimeSurfaces(
        boss_hit_interval_seconds=boss_hit_interval_seconds,
        orb_boss_hit_pct=None if orb_pct is None else float(orb_pct),
        orb_boss_hits_per_second=None if orb_hz is None else float(orb_hz),
        electron_hits_per_second=None if electron_hz is None else float(electron_hz),
        boss_contact_time_seconds=None if contact_t is None else float(contact_t),
        effective_damage_reduction_pct=None if effective_dr is None else float(effective_dr),
        incoming_damage_multiplier=None if incoming_damage_multiplier is None else float(incoming_damage_multiplier),
        source_notes=notes,
    )


def is_active_at_time(mechanic: TimingMechanic, time_s: float) -> bool:
    period = mechanic.period_s
    if period <= 0.0 or mechanic.active_duration_s <= 0.0:
        return False
    local = (time_s - mechanic.phase_offset_s) % period
    return 0.0 <= local < mechanic.active_duration_s


def active_intervals_within_horizon(mechanic: TimingMechanic, horizon_s: float) -> List[tuple[float, float]]:
    period = mechanic.period_s
    if horizon_s <= 0.0 or period <= 0.0 or mechanic.active_duration_s <= 0.0:
        return []
    intervals: List[tuple[float, float]] = []
    start = mechanic.phase_offset_s
    while start < horizon_s:
        end = min(horizon_s, start + mechanic.active_duration_s)
        if end > 0.0:
            intervals.append((max(0.0, start), end))
        start += period
    return intervals




def average_active_fraction_over_interval(mechanic: TimingMechanic, start_s: float, end_s: float) -> float:
    """Average active fraction for a mechanic across a closed-open interval [start, end)."""
    start = float(start_s)
    end = float(end_s)
    if end <= start:
        return 0.0
    if mechanic.period_s <= 0.0 or mechanic.active_duration_s <= 0.0:
        return 0.0
    total_active = 0.0
    horizon = end - start
    cursor = start
    # shift to the activation that may overlap the interval start
    period = mechanic.period_s
    phase = mechanic.phase_offset_s
    k = int((start - phase) // period) - 1
    activation_start = phase + k * period
    while activation_start < end:
        activation_end = activation_start + mechanic.active_duration_s
        overlap_start = max(start, activation_start)
        overlap_end = min(end, activation_end)
        if overlap_end > overlap_start:
            total_active += overlap_end - overlap_start
        activation_start += period
    return max(0.0, min(1.0, total_active / horizon))


def build_default_defensive_timing_mechanics(timing: TimingSurfaces) -> List[TimingMechanic]:
    mechanics: List[TimingMechanic] = []
    if timing.cf_effective_duration_s > 0.0 and timing.cf_effective_cooldown_s >= 0.0 and timing.cf_damage_reduction_pct > 0.0:
        mechanics.append(
            TimingMechanic(
                mechanic_id="chrono_field_damage_reduction",
                active_duration_s=timing.cf_effective_duration_s,
                cooldown_s=timing.cf_effective_cooldown_s,
                active_multiplier=max(0.0, 1.0 - (timing.cf_damage_reduction_pct / 100.0)),
            )
        )
    return mechanics


def compute_average_damage_reduction_fraction_over_interval(timing: TimingSurfaces, start_s: float, end_s: float) -> float:
    """Average timed damage reduction fraction over an encounter interval.

    Current governed scope: Chrono Field only. Flame Bot remains excluded until
    activation/persistence timing is explicitly modelled in the timing contract.
    """
    if end_s <= start_s:
        return 0.0
    total_fraction = 0.0
    for mechanic in build_default_defensive_timing_mechanics(timing):
        if mechanic.mechanic_id == "chrono_field_damage_reduction":
            active_fraction = average_active_fraction_over_interval(mechanic, start_s, end_s)
            total_fraction += active_fraction * (timing.cf_damage_reduction_pct / 100.0)
    return max(0.0, min(0.95, total_fraction))


def build_shared_cycle_segments(mechanics: Iterable[TimingMechanic]) -> List[TimingSegment]:
    mechanics = [m for m in mechanics if m.period_s > 0.0 and m.active_duration_s > 0.0]
    if not mechanics:
        return []
    horizon = shared_cycle_seconds(m.period_s for m in mechanics)
    if horizon <= 0.0:
        return []
    cuts = {0.0, horizon}
    for m in mechanics:
        for start, end in active_intervals_within_horizon(m, horizon):
            cuts.add(start)
            cuts.add(end)
    ordered = sorted(cuts)
    segments: List[TimingSegment] = []
    for idx in range(len(ordered) - 1):
        a = ordered[idx]
        b = ordered[idx + 1]
        if b <= a:
            continue
        mid = (a + b) / 2.0
        active = [m.mechanic_id for m in mechanics if is_active_at_time(m, mid)]
        mult = 1.0
        for m in mechanics:
            if m.mechanic_id in active:
                mult *= max(0.0, m.active_multiplier)
        segments.append(TimingSegment(start_s=a, end_s=b, active_mechanics=active, combined_multiplier=mult))
    return segments


def overlap_fraction(primary: TimingMechanic, secondary: TimingMechanic) -> float:
    horizon = shared_cycle_seconds([primary.period_s, secondary.period_s])
    if horizon <= 0.0:
        return 0.0
    overlap = 0.0
    for segment in build_shared_cycle_segments([primary, secondary]):
        if primary.mechanic_id in segment.active_mechanics and secondary.mechanic_id in segment.active_mechanics:
            overlap += segment.end_s - segment.start_s
    return overlap / horizon


def compute_average_combined_multiplier(mechanics: Iterable[TimingMechanic]) -> float:
    segments = build_shared_cycle_segments(mechanics)
    if not segments:
        return 1.0
    horizon = segments[-1].end_s - segments[0].start_s
    if horizon <= 0.0:
        return 1.0
    total = 0.0
    for seg in segments:
        total += (seg.end_s - seg.start_s) * seg.combined_multiplier
    return total / horizon


def compute_timing_surfaces(config: ScenarioConfig, scenario: Optional[ScenarioSurfaces] = None) -> TimingSurfaces:
    scenario = scenario or ScenarioSurfaces()
    uw_dur_reduction = getattr(scenario, "bc_uw_duration_reduction_s", 0.0)
    bh_dur = max(0.0, config.bh_base_duration_s + config.bh_perk_duration_add_s + uw_dur_reduction)
    bh_cd = max(0.0, config.bh_base_cooldown_s + config.bh_perk_cooldown_add_s)
    cf_dur = max(0.0, config.cf_base_duration_s + config.cf_perk_duration_add_s + uw_dur_reduction)
    cf_cd = max(0.0, config.cf_base_cooldown_s)
    gt_dur = max(0.0, config.gt_base_duration_s + uw_dur_reduction)
    gt_cd = max(0.0, config.gt_base_cooldown_s)
    cf_uptime = _uptime(cf_dur, cf_cd)
    return TimingSurfaces(
        bh_effective_duration_s=bh_dur,
        bh_effective_cooldown_s=bh_cd,
        bh_uptime_fraction=_uptime(bh_dur, bh_cd),
        cf_effective_duration_s=cf_dur,
        cf_effective_cooldown_s=cf_cd,
        cf_uptime_fraction=cf_uptime,
        gt_effective_duration_s=gt_dur,
        gt_effective_cooldown_s=gt_cd,
        gt_uptime_fraction=_uptime(gt_dur, gt_cd),
        cf_damage_reduction_pct=config.cf_damage_reduction_pct,
        cf_avg_damage_reduction_fraction=cf_uptime * (config.cf_damage_reduction_pct / 100.0) if config.cf_damage_reduction_pct > 0 and cf_uptime > 0 else 0.0,
        cf_slow_pct=config.cf_slow_pct,
        bot_amplify_uptime_fraction=_uptime(config.bot_amplify_duration_s, config.bot_amplify_cooldown_s),
        bot_golden_uptime_fraction=_uptime(config.bot_golden_duration_s, config.bot_golden_cooldown_s),
        bot_thunder_uptime_fraction=_uptime(config.bot_thunder_duration_s, config.bot_thunder_cooldown_s),
        bot_flame_cooldown_s=config.bot_flame_cooldown_s,
        bot_flame_damage_reduction_pct=config.bot_flame_damage_reduction_pct,
    )


def build_default_econ_timing_mechanics(statbook_rows: Dict[str, dict]) -> List[TimingMechanic]:
    def _get(key: str, default: float = 0.0) -> float:
        row = statbook_rows.get(key) or {}
        try:
            return float(row.get("final_value", default))
        except (TypeError, ValueError):
            return default
    def _tp(base_key: str, runtime_key: str) -> float:
        return _get(base_key) + _get(runtime_key)
    return [
        TimingMechanic(
            mechanic_id="golden_tower",
            active_duration_s=_get("mechanic_param::uw.golden_tower.duration_seconds"),
            cooldown_s=_get("mechanic_param::uw.golden_tower.cooldown_seconds"),
            active_multiplier=max(0.0, 1.0 + _get("mechanic_param::uw.golden_tower.bonus_multiplier") + _get("runtime_mechanic_param::uw.golden_tower.bonus_multiplier")),
        ),
        TimingMechanic(
            mechanic_id="black_hole_coin",
            active_duration_s=_tp("mechanic_param::uw.black_hole.duration_seconds", "runtime_mechanic_param::uw.black_hole.duration_seconds"),
            cooldown_s=_tp("mechanic_param::uw.black_hole.cooldown_seconds", "runtime_mechanic_param::uw.black_hole.cooldown_seconds"),
            active_multiplier=max(0.0, 1.0 + _get("runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier")),
        ),
        TimingMechanic(
            mechanic_id="golden_bot",
            active_duration_s=_get("mechanic_param::bot.golden.duration_seconds"),
            cooldown_s=_get("mechanic_param::bot.golden.cooldown_seconds"),
            active_multiplier=max(0.0, 1.0 + _get("mechanic_param::bot.golden.bonus_multiplier")),
        ),
    ]
