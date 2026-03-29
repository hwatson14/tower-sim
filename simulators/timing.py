from __future__ import annotations

import csv
from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from qe.contracts import normalize_surface_id_to_contract
from qe.materializer import FamilyBaselineContributorMap, FamilyBaselineMaterializer
from qe.consumer_registry import resolve_consumer_bundle
from simulators.scenario import ScenarioConfig, ScenarioSurfaces, compute_scenario_surfaces
from qe.models import BoundStatInputs, compile_stat_inputs_with_identity
from qe.kernel import QueryResponse, StatQueryKernel, get_default_query_kernel
from qe.routing import QEResolutionPlanner
from input.state_types import AccountState
from qe.models import StatInput

ROOT = Path(__file__).resolve().parents[1]
ORB_BOSS_HIT_LEVELS_TABLE = ROOT / "kb" / "global-rules" / "tables" / "note-derived-orb-boss-hit-levels-1-10.csv"
WAVE_TIMING_BASELINES_TABLE = ROOT / "kb" / "global-rules" / "tables" / "wave-timing-baselines.csv"


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _mech(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_mech('{destination_id}'))


def _runtime(destination_id: str) -> str:
    return normalize_surface_id_to_contract(f_runtime('{destination_id}'))


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


@lru_cache(maxsize=1)
def _load_wave_timing_baselines() -> Dict[str, float]:
    out: Dict[str, float] = {}
    with WAVE_TIMING_BASELINES_TABLE.open(newline='') as fh:
        for row in csv.DictReader(fh):
            mode_id = str(row.get('mode_id') or '').strip()
            if not mode_id:
                continue
            try:
                out[mode_id] = float(row['total_wave_duration_seconds'])
            except (TypeError, ValueError, KeyError):
                raise ValueError(f'Invalid total_wave_duration_seconds row in {WAVE_TIMING_BASELINES_TABLE}: {row!r}.')
    if 'farming' not in out or 'tournament' not in out:
        raise ValueError(f'{WAVE_TIMING_BASELINES_TABLE} must define farming and tournament base wave durations.')
    return out


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
        _runtime('combat.boss_hit_interval_seconds'),
        _runtime('combat.boss_interval_seconds'),
    ])
    if boss_hit_interval_override is not None:
        boss_hit_interval_seconds = float(boss_hit_interval_override)
        notes.append(f'Boss hit interval consumed from governed surface: {boss_hit_interval_seconds}s.')
    else:
        boss_hit_interval_seconds = float(scenario.boss_hit_interval_seconds)
        notes.append(f'Boss hit interval sourced from scenario engine: {boss_hit_interval_seconds}s.')

    orb_pct = _lookup_row_value(row_map, [
        _runtime('combat.orb_boss_hit_pct'),
        _runtime('tower.orb_boss_hit_pct'),
        _runtime('tower.orb.hit_pct_vs_boss'),
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
        _runtime('combat.orb_boss_hits_per_second'),
        _runtime('tower.orb_boss_hits_per_second'),
        _runtime('tower.orb.hits_per_second_vs_boss'),
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
        _runtime('combat.electron_hits_per_second'),
        _runtime('module.orbital_augment.electron_hits_per_second'),
        _runtime('module.orbital_augment.hits_per_second_vs_boss'),
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
        _runtime('combat.boss_contact_time_seconds'),
        _runtime('combat.contact_time_seconds_vs_boss'),
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
        _runtime('combat.effective_damage_reduction_pct'),
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


def materialize_timing_family_baseline(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    materializer: FamilyBaselineMaterializer | None = None,
) -> FamilyBaselineContributorMap:
    bound, rows = compile_timing_family_rows(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
    )
    return (materializer or FamilyBaselineMaterializer()).materialize_from_rows(bound.binding.identity, family_id, rows)


def compile_timing_family_rows(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
) -> tuple[BoundStatInputs, tuple[StatInput, ...]]:
    _validate_timing_family_request(family_id=family_id, scenario_config=scenario_config, perks_enabled=perks_enabled)
    bound = compile_stat_inputs_with_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name or preset_name,
        module_preset_name=module_preset_name or preset_name,
        perk_preset_name=perk_preset_name or preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_context={
            'mode_id': scenario_config.mode_id,
            'tier': scenario_config.tier,
            'league': scenario_config.league,
            'tournament_wave': scenario_config.tournament_wave,
        },
    )
    scenario = compute_scenario_surfaces(scenario_config)
    timing = compute_timing_surfaces(scenario_config, scenario)
    wave_acceleration_pct = _wave_acceleration_pct_from_rows(bound.stat_inputs)
    derived_rows = tuple(_timing_family_derived_rows(scenario_config, scenario, timing, wave_acceleration_pct))
    replaced_surface_keys = {
        (row.destination_object_type, row.destination_id)
        for row in derived_rows
        if row.destination_object_type and row.destination_id
    }
    base_rows = tuple(
        row for row in bound.stat_inputs
        if (row.destination_object_type, row.destination_id) not in replaced_surface_keys
    )
    return bound, base_rows + derived_rows


def resolve_timing_family_query(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    requested_surface_ids: Sequence[str],
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    trace_mode: str = 'contributors',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    query_kernel = kernel or get_default_query_kernel()
    if kernel is not None:
        query_kernel = kernel
        baseline = materialize_timing_family_baseline(
            account_state=account_state,
            family_id=family_id,
            preset_name=preset_name,
            scenario_config=scenario_config,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
            runtime_branch_id=runtime_branch_id,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            materializer=query_kernel.materializer,
        )
        return query_kernel.resolve_surfaces(baseline, requested_surface_ids=requested_surface_ids, trace_mode=trace_mode)

    planner = QEResolutionPlanner()
    bound, rows = compile_timing_family_rows(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
    )
    result = planner.resolve_rows_declared_family_query(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id=family_id,
        requested_surface_ids=requested_surface_ids,
        trace_mode=trace_mode,
    )
    return result.response


def resolve_timing_consumer_bundle(
    *,
    account_state: AccountState,
    consumer_id: str,
    bundle_id: str,
    family_id: str,
    preset_name: str,
    scenario_config: ScenarioConfig,
    perks_enabled: bool,
    include_optional_surface_ids: Sequence[str] = (),
    state_mode: str = 'start_of_run',
    runtime_branch_id: str = 'branch_base',
    trace_mode: str | None = None,
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    resolved_bundle = resolve_consumer_bundle(
        consumer_id,
        bundle_id,
        family_id=family_id,
        include_optional_surface_ids=include_optional_surface_ids,
        trace_mode=trace_mode,
    )
    effective_trace_mode = resolved_bundle.minimum_trace_mode if trace_mode is None else str(trace_mode)
    return resolve_timing_family_query(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        requested_surface_ids=resolved_bundle.surface_ids,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        trace_mode=effective_trace_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        kernel=kernel,
    )


def _validate_timing_family_request(*, family_id: str, scenario_config: ScenarioConfig, perks_enabled: bool) -> None:
    if family_id == 'timing_tournament_no_perks':
        if scenario_config.mode_id != 'tournament':
            raise ValueError('timing_tournament_no_perks requires ScenarioConfig.mode_id="tournament".')
        if perks_enabled:
            raise ValueError('timing_tournament_no_perks forbids perks_enabled=True because tournament implies perks disabled.')
    elif family_id == 'timing_farm_with_perks':
        if scenario_config.mode_id != 'farming':
            raise ValueError('timing_farm_with_perks requires ScenarioConfig.mode_id="farming".')
        if not perks_enabled:
            raise ValueError('timing_farm_with_perks requires perks_enabled=True.')
    elif family_id == 'timing_scenario_probe':
        if scenario_config.mode_id == 'tournament' and perks_enabled:
            raise ValueError('timing_scenario_probe still enforces tournament implies perks disabled.')
    else:
        raise ValueError(f'Unsupported timing family_id {family_id!r}.')


def _timing_family_derived_rows(
    config: ScenarioConfig,
    scenario: ScenarioSurfaces,
    timing: TimingSurfaces,
    wave_acceleration_pct: float,
) -> tuple[StatInput, ...]:
    base_wave_duration_seconds = _load_wave_timing_baselines()['tournament' if config.mode_id == 'tournament' else 'farming']
    effective_wave_duration_seconds = max(0.0, base_wave_duration_seconds * (1.0 - (max(0.0, wave_acceleration_pct) / 100.0)))
    return (
        StatInput(
            stat_name='Black Hole Effective Duration',
            source_family='scenario_rules',
            source_name='Black Hole',
            value=timing.bh_effective_duration_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.black_hole.effective_duration',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='mechanic_param',
            destination_id='uw.black_hole.duration_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Black Hole Effective Cooldown',
            source_family='scenario_rules',
            source_name='Black Hole',
            value=timing.bh_effective_cooldown_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.black_hole.effective_cooldown',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='mechanic_param',
            destination_id='uw.black_hole.cooldown_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Golden Tower Effective Duration',
            source_family='scenario_rules',
            source_name='Golden Tower',
            value=timing.gt_effective_duration_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.golden_tower.effective_duration',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='mechanic_param',
            destination_id='uw.golden_tower.duration_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Golden Tower Effective Cooldown',
            source_family='scenario_rules',
            source_name='Golden Tower',
            value=timing.gt_effective_cooldown_s,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.golden_tower.effective_cooldown',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='mechanic_param',
            destination_id='uw.golden_tower.cooldown_seconds',
            kb_mapped=True,
        ),
        StatInput(
            stat_name='Wave Duration Effective',
            source_family='scenario_rules',
            source_name='Wave Accelerator',
            value=effective_wave_duration_seconds,
            value_type='seconds',
            stage='scenario_runtime',
            contributor_id='timing.wave_duration_seconds_effective',
            provenance='engine.timing_engine.compute_timing_surfaces',
            destination_object_type='support_surface',
            destination_id='timing.wave_duration_seconds_effective',
            kb_mapped=True,
        ),
    )


def _wave_acceleration_pct_from_rows(rows: Sequence[StatInput]) -> float:
    for row in rows:
        if (
            row.destination_object_type == 'runtime_mechanic_param'
            and row.destination_id == 'cards.wave_accelerator.spawn_rate_acceleration'
            and row.active
        ):
            try:
                return float(row.value)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def build_default_econ_timing_mechanics(statbook_rows: Dict[str, dict]) -> List[TimingMechanic]:
    def _get(key: str, default: float = 0.0) -> float:
        row = statbook_rows.get(_sid(key)) or {}
        try:
            return float(row.get("final_value", default))
        except (TypeError, ValueError):
            return default
    def _tp(base_key: str, runtime_key: str) -> float:
        return _get(base_key) + _get(runtime_key)
    return [
        TimingMechanic(
            mechanic_id="golden_tower",
            active_duration_s=_get(_mech('uw.golden_tower.duration_seconds')),
            cooldown_s=_get(_mech('uw.golden_tower.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_mech('uw.golden_tower.bonus_multiplier'))),
        ),
        TimingMechanic(
            mechanic_id="black_hole_coin",
            active_duration_s=_tp(_mech('uw.black_hole.duration_seconds'), _runtime('uw.black_hole.duration_seconds')),
            cooldown_s=_tp(_mech('uw.black_hole.cooldown_seconds'), _runtime('uw.black_hole.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_runtime('uw.black_hole.coin_bonus_multiplier'))),
        ),
        TimingMechanic(
            mechanic_id="golden_bot",
            active_duration_s=_get(_mech('bot.golden.duration_seconds')),
            cooldown_s=_get(_mech('bot.golden.cooldown_seconds')),
            active_multiplier=max(0.0, _get(_mech('bot.golden.bonus_multiplier'))),
        ),
    ]
