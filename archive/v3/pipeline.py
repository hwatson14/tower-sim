"""v3 composition-root helpers.

This module centralizes the v3 stage composition path so callers can use a
single deterministic flow:

1) IDS parse
2) account snapshot compile
3) stat-input compilation + validation
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tower_sim.util.account_snapshot import AccountSnapshot
from v3.account_snapshot_compiler import compile_account_snapshot
from v3.ids_parser import parse_ids
from tower_sim.registry.stat_registry import Phase
from v3.kb_stat_engine import V3KBStatEngine, V3KBStatEngineError
from v3.stat_input_compiler import (
    V3CompiledBaselineLoadout,
    V3CompiledStatInputs,
    compile_v3_baseline_loadout_stat_inputs,
    compile_v3_stat_inputs,
)

StaticStage = Literal[
    "full",
    "baseline_account",
    "baseline_gem_respec",
    "baseline_loadout",
    "baseline_max_progression",
]


class V3PipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageRequest:
    stage: StaticStage
    loadout_context: str = "Farming"
    mode_policy: str = "normal"
    strict_kb_routing: bool = True
    debug: bool = False


@dataclass(frozen=True)
class StaticStageResult:
    context: str
    resolved_targets: dict[str, float]
    missing: list[str]
    debug_breakdowns: dict[str, object] | None = None


@dataclass(frozen=True)
class AtWaveContext:
    context: str


@dataclass(frozen=True)
class WaveState:
    W_actual: int


@dataclass(frozen=True)
class RuntimeStateSeed:
    at_wave: AtWaveContext
    wave_state: WaveState
    baseline_loadout: StaticStageResult


@dataclass(frozen=True)
class RuntimeStateResult:
    combat_result: dict[str, object]


def _engine_resolved_targets(stat_inputs: list, *, strict_kb_routing: bool) -> dict[str, float]:
    engine = V3KBStatEngine(strict=strict_kb_routing)
    try:
        result = engine.build(stat_inputs)
    except V3KBStatEngineError as exc:
        raise V3PipelineError(str(exc)) from exc
    start_of_run = result.run_stats.get(Phase.START_OF_RUN)
    if start_of_run is None:
        return {}
    return {k: float(v) for k, v in start_of_run.items()}


def _resolve_targets(compiled: V3CompiledStatInputs, *, strict_kb_routing: bool) -> dict[str, float]:
    return _engine_resolved_targets(compiled.stat_inputs, strict_kb_routing=strict_kb_routing)


def _resolve_targets_loadout(compiled: V3CompiledBaselineLoadout, *, strict_kb_routing: bool) -> dict[str, float]:
    return _engine_resolved_targets(compiled.stat_inputs, strict_kb_routing=strict_kb_routing)


def compose_full_stats(snapshot: AccountSnapshot, *, strict_kb_routing: bool = True, debug: bool = False) -> StaticStageResult:
    compiled = compile_v3_stat_inputs(snapshot, stage="full")
    breakdowns = None
    if debug:
        breakdowns = {
            "missing": list(compiled.missing),
            "dropped_noncanonical": list(compiled.dropped_noncanonical),
            "dropped_kb_unwired": list(compiled.dropped_kb_unwired),
        }
    return StaticStageResult(
        context="full",
        resolved_targets=_resolve_targets(compiled, strict_kb_routing=strict_kb_routing),
        missing=list(compiled.missing),
        debug_breakdowns=breakdowns,
    )


def compose_baseline_account(snapshot: AccountSnapshot, *, strict_kb_routing: bool = True, debug: bool = False) -> StaticStageResult:
    compiled = compile_v3_stat_inputs(snapshot, stage="baseline_account")
    breakdowns = None
    if debug:
        breakdowns = {
            "missing": list(compiled.missing),
            "dropped_noncanonical": list(compiled.dropped_noncanonical),
            "dropped_kb_unwired": list(compiled.dropped_kb_unwired),
        }
    return StaticStageResult(
        context="baseline_account",
        resolved_targets=_resolve_targets(compiled, strict_kb_routing=strict_kb_routing),
        missing=list(compiled.missing),
        debug_breakdowns=breakdowns,
    )


def compose_baseline_gem_respec(snapshot: AccountSnapshot, *, strict_kb_routing: bool = True, debug: bool = False) -> StaticStageResult:
    compiled = compile_v3_stat_inputs(snapshot, stage="baseline_gem_respec")
    breakdowns = None
    if debug:
        breakdowns = {
            "missing": list(compiled.missing),
            "dropped_noncanonical": list(compiled.dropped_noncanonical),
            "dropped_kb_unwired": list(compiled.dropped_kb_unwired),
        }
    return StaticStageResult(
        context="baseline_gem_respec",
        resolved_targets=_resolve_targets(compiled, strict_kb_routing=strict_kb_routing),
        missing=list(compiled.missing),
        debug_breakdowns=breakdowns,
    )


def compose_baseline_loadout(
    snapshot: AccountSnapshot,
    *,
    loadout_context: str = "Farming",
    strict_kb_routing: bool = True,
    debug: bool = False,
) -> StaticStageResult:
    compiled = compile_v3_baseline_loadout_stat_inputs(snapshot, module_context=loadout_context)
    breakdowns = None
    if debug:
        breakdowns = {
            "missing": list(compiled.missing),
            "dropped_noncanonical": list(compiled.dropped_noncanonical),
            "dropped_kb_unwired": list(compiled.dropped_kb_unwired),
            "layer_gaps": list(compiled.layer_gaps),
            "module_contribution_ledger_count": len(compiled.module_contribution_ledger),
        }
    return StaticStageResult(
        context="baseline_loadout",
        resolved_targets=_resolve_targets_loadout(compiled, strict_kb_routing=strict_kb_routing),
        missing=list(compiled.missing),
        debug_breakdowns=breakdowns,
    )


def compose_baseline_max_progression(
    snapshot: AccountSnapshot,
    *,
    loadout_context: str = "Farming",
    mode_policy: str = "normal",
    strict_kb_routing: bool = True,
    debug: bool = False,
) -> StaticStageResult:
    if mode_policy.strip() == "":
        raise V3PipelineError("mode_policy must be non-empty.")
    loadout = compose_baseline_loadout(snapshot, loadout_context=loadout_context, strict_kb_routing=strict_kb_routing, debug=debug)
    extra = dict(loadout.debug_breakdowns or {})
    if debug:
        extra["mode_policy"] = mode_policy
    return StaticStageResult(
        context="baseline_max_progression",
        resolved_targets=dict(loadout.resolved_targets),
        missing=list(loadout.missing),
        debug_breakdowns=extra or None,
    )


def compose_static_stage(snapshot: AccountSnapshot, request: StageRequest) -> StaticStageResult:
    if request.stage == "full":
        return compose_full_stats(snapshot, strict_kb_routing=request.strict_kb_routing, debug=request.debug)
    if request.stage == "baseline_account":
        return compose_baseline_account(snapshot, strict_kb_routing=request.strict_kb_routing, debug=request.debug)
    if request.stage == "baseline_gem_respec":
        return compose_baseline_gem_respec(snapshot, strict_kb_routing=request.strict_kb_routing, debug=request.debug)
    if request.stage == "baseline_loadout":
        return compose_baseline_loadout(
            snapshot,
            loadout_context=request.loadout_context,
            strict_kb_routing=request.strict_kb_routing,
            debug=request.debug,
        )
    if request.stage == "baseline_max_progression":
        return compose_baseline_max_progression(
            snapshot,
            loadout_context=request.loadout_context,
            mode_policy=request.mode_policy,
            strict_kb_routing=request.strict_kb_routing,
            debug=request.debug,
        )
    raise V3PipelineError(f"Unsupported stage: {request.stage}")


def compose_static_stage_from_ids(ids_path: Path, request: StageRequest) -> StaticStageResult:
    ids_raw = parse_ids(ids_path)
    snapshot = compile_account_snapshot(ids_raw)
    return compose_static_stage(snapshot, request)


def compose_at_wave(*, baseline_loadout: StaticStageResult, actual_wave: int) -> RuntimeStateSeed:
    if actual_wave < 1:
        raise V3PipelineError("actual_wave must be >= 1")
    return RuntimeStateSeed(
        at_wave=AtWaveContext(context="at_wave"),
        wave_state=WaveState(W_actual=int(actual_wave)),
        baseline_loadout=baseline_loadout,
    )


def runtime_state_executor(seed: RuntimeStateSeed) -> RuntimeStateResult:
    return RuntimeStateResult(
        combat_result={
            "status": "not_implemented",
            "wave": seed.wave_state.W_actual,
            "resolved_stat_count": len(seed.baseline_loadout.resolved_targets),
        }
    )
