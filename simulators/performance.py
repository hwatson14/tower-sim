from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Any, Dict

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from input.state_types import ScenarioRuntimeInputs
from simulators.contracts import DirtyLedger, NormalizedCheckpointState, ProjectedRunState, WaveCheckpoint
from simulators.perks import advance_perk_state
from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy
from simulators.perk_timeline_state import PerkTimelineEvent
from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max
from simulators.snapshot_resolver import resolve_wave_row_snapshot


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    elapsed_ms: float
    rows: int
    qe_resolution_count: int
    timing_recompute_count: int
    geometry_recompute_count: int
    extra: Dict[str, Any]


def _default_runtime_inputs():
    bundle = load_inputs()
    account_state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    return bundle, account_state


def _default_run_to_max_config(*, preset_name: str, end_wave: int) -> RunToMaxConfig:
    return RunToMaxConfig(
        preset_name=preset_name,
        start_wave=10,
        end_wave=end_wave,
        boss_wave_step=10,
        tier_column='Tier 1',
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(
            {
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hits_per_second': 5.0,
                'electron_hits_per_second': 5.0,
                'boss_contact_time_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
            }
        ),
    )


def _projected_run_state_for_wave(account_state, *, wave: int, preset_name: str):
    workshop_levels_current = {
        name: int((entry.preset_levels.get(preset_name) or 0))
        for name, entry in account_state.workshop.items()
        if entry.max_level is not None
    }
    timeline_rows, _diag = generate_timeline_from_policy(
        PerkTimelinePolicy(
            seed=42,
            target_wave=max(1, int(wave)),
        )
    )
    events = [
        PerkTimelineEvent(
            wave=int(row["wave"]),
            perk_id=str(row["effect_stat_id"] or row["perk_taken"]),
            perk_name=str(row["perk_taken"]),
            quantity=1,
            retroactive_burst=bool(row.get("retroactive_burst", False)),
        )
        for row in timeline_rows
        if row.get("wave") is not None
    ]
    perk_state, _cursor = advance_perk_state(events, wave=wave)
    checkpoint = WaveCheckpoint(display_wave=int(wave))
    return ProjectedRunState(
        checkpoint=checkpoint,
        workshop_levels_current=workshop_levels_current,
        perk_state=perk_state,
        dirty_ledger=DirtyLedger(
            progression_dirty=True,
            qe_dirty=True,
            timing_dirty=True,
            geometry_dirty=False,
        ),
    )


def bench_row_resolution(*, wave: int = 1, preset_name: str = "Farming") -> BenchmarkResult:
    _bundle, account_state = _default_runtime_inputs()
    projected = _projected_run_state_for_wave(account_state, wave=wave, preset_name=preset_name)
    normalized = NormalizedCheckpointState(
        checkpoint=projected.checkpoint,
        account_state=account_state,
        preset_name=preset_name,
        projected_run_state=projected,
    )
    start = perf_counter()
    snapshot = resolve_wave_row_snapshot(normalized)
    elapsed_ms = (perf_counter() - start) * 1000.0
    return BenchmarkResult(
        name="row_resolution",
        elapsed_ms=elapsed_ms,
        rows=1,
        qe_resolution_count=snapshot.metrics.qe_resolution_count if snapshot.metrics else 0,
        timing_recompute_count=snapshot.metrics.timing_recompute_count if snapshot.metrics else 0,
        geometry_recompute_count=snapshot.metrics.geometry_recompute_count if snapshot.metrics else 0,
        extra={"wave": wave, "preset_name": preset_name},
    )


def bench_run_to_max(*, end_wave: int = 30, preset_name: str = "Farming") -> BenchmarkResult:
    _bundle, account_state = _default_runtime_inputs()
    projected = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=_projected_run_state_for_wave(account_state, wave=0, preset_name=preset_name).perk_state,
    )
    start = perf_counter()
    result = run_to_max(
        account_state=account_state,
        initial_projected_state=projected,
        config=_default_run_to_max_config(preset_name=preset_name, end_wave=end_wave),
    )
    elapsed_ms = (perf_counter() - start) * 1000.0
    return BenchmarkResult(
        name="run_to_max",
        elapsed_ms=elapsed_ms,
        rows=result.row_count,
        qe_resolution_count=1,
        timing_recompute_count=1,
        geometry_recompute_count=0,
        extra={
            "max_wave": result.max_wave,
            "end_wave": end_wave,
            "preset_name": preset_name,
            "execution_mode": result.diagnostics.get('execution_mode'),
        },
    )


def bench_run_to_max_warm(
    *,
    end_wave: int = 100,
    preset_name: str = "Farming",
    measured_runs: int = 2,
) -> BenchmarkResult:
    _bundle, account_state = _default_runtime_inputs()
    projected = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=_projected_run_state_for_wave(account_state, wave=0, preset_name=preset_name).perk_state,
    )
    config = _default_run_to_max_config(preset_name=preset_name, end_wave=end_wave)

    # Prime kernel/module imports first so the measured runs represent steady-state performance.
    run_to_max(
        account_state=account_state,
        initial_projected_state=projected,
        config=config,
    )

    measurements: list[tuple[float, object]] = []
    for _ in range(max(1, int(measured_runs))):
        start = perf_counter()
        result = run_to_max(
            account_state=account_state,
            initial_projected_state=projected,
            config=config,
        )
        elapsed_ms = (perf_counter() - start) * 1000.0
        measurements.append((elapsed_ms, result))

    best_elapsed_ms, best_result = min(measurements, key=lambda item: item[0])
    average_elapsed_ms = sum(elapsed for elapsed, _result in measurements) / len(measurements)
    return BenchmarkResult(
        name="run_to_max_warm",
        elapsed_ms=best_elapsed_ms,
        rows=best_result.row_count,
        qe_resolution_count=1,
        timing_recompute_count=1,
        geometry_recompute_count=0,
        extra={
            "max_wave": best_result.max_wave,
            "end_wave": end_wave,
            "preset_name": preset_name,
            "execution_mode": best_result.diagnostics.get('execution_mode'),
            "average_elapsed_ms": average_elapsed_ms,
            "measured_runs": len(measurements),
        },
    )


def bench_run_to_max_table_sweep_warm(
    *,
    end_wave: int = 100,
    preset_name: str = "Farming",
    measured_runs: int = 2,
) -> BenchmarkResult:
    _bundle, account_state = _default_runtime_inputs()
    projected = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=_projected_run_state_for_wave(account_state, wave=0, preset_name=preset_name).perk_state,
    )
    config = _default_run_to_max_config(preset_name=preset_name, end_wave=end_wave)

    run_to_max(
        account_state=account_state,
        initial_projected_state=projected,
        config=config,
    )

    measurements: list[tuple[float, object]] = []
    for _ in range(max(1, int(measured_runs))):
        start = perf_counter()
        result = run_to_max(
            account_state=account_state,
            initial_projected_state=projected,
            config=config,
        )
        elapsed_ms = (perf_counter() - start) * 1000.0
        measurements.append((elapsed_ms, result))

    best_elapsed_ms, best_result = min(measurements, key=lambda item: item[0])
    average_elapsed_ms = sum(elapsed for elapsed, _result in measurements) / len(measurements)
    return BenchmarkResult(
        name="run_to_max_table_sweep_warm",
        elapsed_ms=best_elapsed_ms,
        rows=best_result.row_count,
        qe_resolution_count=int(best_result.diagnostics.get('qe_resolution_count', 0)),
        timing_recompute_count=int(best_result.diagnostics.get('timing_recompute_count', 0)),
        geometry_recompute_count=0,
        extra={
            "max_wave": best_result.max_wave,
            "end_wave": end_wave,
            "preset_name": preset_name,
            "execution_mode": best_result.diagnostics.get('execution_mode'),
            "average_elapsed_ms": average_elapsed_ms,
            "measured_runs": len(measurements),
        },
    )
