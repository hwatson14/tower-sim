"""v3 deterministic pipeline composition root.

Implements the staged static and at-wave composition flow:
_IDS.csv -> ids_parser -> IdsRaw -> account_snapshot_compiler -> AccountSnapshot
-> compose_static_stage(StageRequest) -> StatBook(stage)
-> wave_engine -> RunWaveState -> runtime_overlay_materializer -> stat_engine
-> StatBook("at_wave").
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal, Mapping, Optional

from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.engines.wave_engine import RunWaveState, SkipRamp, make_wave_state
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.util.account_snapshot import AccountSnapshot, WorkshopEntrySnapshot
from tower_sim.util.statbook import StatBook
from v3.stat_input_compiler import (
    V3CompiledBaselineLoadout,
    V3CompiledStatInputs,
    V3StatInputCompilerError,
    compile_v3_baseline_loadout_stat_inputs,
    compile_v3_stat_inputs,
)

StageName = Literal[
    "baseline_account",
    "baseline_gem_respec",
    "baseline_loadout",
    "baseline_max_progression",
]
ModePolicy = Literal["normal", "tournament"]


@dataclass(frozen=True)
class StageRequest:
    stage: StageName
    loadout_context: Optional[str] = None
    card_preset: Optional[str] = None
    module_preset: Optional[str] = None
    mode_policy: Optional[ModePolicy] = None
    debug: bool = False
    family_overrides: Optional[tuple[str, ...]] = None
    strict_missing: bool = False


@dataclass(frozen=True)
class ResolvedStatBook:
    context: str
    statbook: StatBook
    resolved_targets: Mapping[str, float]
    included_families: tuple[str, ...]
    emitted_stat_inputs: tuple[StatInput, ...]
    policy: Optional[str] = None
    debug_breakdowns: Optional[Mapping[str, object]] = None


@dataclass(frozen=True)
class RuntimeStateSeed:
    at_wave: ResolvedStatBook
    wave_state: RunWaveState


@dataclass(frozen=True)
class RuntimeExecutionResult:
    terminal_state: Mapping[str, object]
    combat_result: Mapping[str, object]


_STAGE_FAMILY_CONTRACT: Mapping[StageName, tuple[str, ...]] = {
    "baseline_account": ("workshop", "labs", "relic", "enhancements", "uw_upgrade"),
    "baseline_gem_respec": ("workshop", "labs", "relic", "enhancements", "uw_upgrade", "uw_plus", "bot_upgrade", "guardian_upgrade"),
    "baseline_loadout": ("workshop", "labs", "relic", "enhancements", "uw_upgrade", "uw_plus", "bot_upgrade", "guardian_upgrade", "card", "module"),
    "baseline_max_progression": ("workshop", "labs", "relic", "enhancements", "uw_upgrade", "uw_plus", "bot_upgrade", "guardian_upgrade", "card", "module", "workshop_max_progression"),
}


def _route_categories(stat_inputs: Iterable[StatInput]) -> list[StatInput]:
    """Small category router: reject category aliases, pass concrete targets."""
    routed: list[StatInput] = []
    for item in stat_inputs:
        if item.stat_id.startswith("category__"):
            raise V3StatInputCompilerError(f"category_alias_not_allowed_in_stat_engine:{item.stat_id}")
        routed.append(item)
    return routed


def _build_resolved_statbook(
    *,
    context: str,
    stat_inputs: list[StatInput],
    included_families: tuple[str, ...],
    policy: str | None,
    debug_breakdowns: Mapping[str, object] | None,
) -> ResolvedStatBook:
    engine = StatEngine(default_registry())
    result = engine.build(stat_inputs)
    start = result.run_stats.get(Phase.START_OF_RUN)
    resolved_targets = dict(start.values) if start is not None else {}
    return ResolvedStatBook(
        context=context,
        statbook=result.statbook,
        resolved_targets=resolved_targets,
        included_families=included_families,
        emitted_stat_inputs=tuple(stat_inputs),
        policy=policy,
        debug_breakdowns=debug_breakdowns,
    )


def _compile_stage_inputs(snapshot: AccountSnapshot, request: StageRequest) -> tuple[list[StatInput], list[str], Mapping[str, object]]:
    if request.stage == "baseline_account":
        compiled: V3CompiledStatInputs = compile_v3_stat_inputs(snapshot, stage="baseline_account")
        return list(compiled.stat_inputs), list(compiled.missing), {}

    if request.stage == "baseline_gem_respec":
        compiled = compile_v3_stat_inputs(snapshot, stage="baseline_gem_respec")
        return list(compiled.stat_inputs), list(compiled.missing), {}

    if request.stage == "baseline_loadout":
        context = request.loadout_context or "Farming"
        compiled_loadout: V3CompiledBaselineLoadout = compile_v3_baseline_loadout_stat_inputs(
            snapshot,
            module_context=context,
        )
        return (
            list(compiled_loadout.stat_inputs),
            list(compiled_loadout.missing),
            {
                "module_contribution_ledger": compiled_loadout.module_contribution_ledger,
                "layer_gaps": compiled_loadout.layer_gaps,
            },
        )

    if request.stage == "baseline_max_progression":
        return _compile_baseline_max_progression_inputs(snapshot, request)

    raise V3StatInputCompilerError(f"Unsupported stage request: {request.stage}")


def _progress_snapshot_to_account_known_workshop_ceilings(snapshot: AccountSnapshot) -> AccountSnapshot:
    progressed: dict[str, WorkshopEntrySnapshot] = {}
    for name, entry in snapshot.workshop.items():
        target_level = entry.end_level if entry.end_level is not None else entry.coin_level
        progressed[name] = replace(entry, coin_level=target_level)
    return replace(snapshot, workshop=progressed)


def _compile_baseline_max_progression_inputs(
    snapshot: AccountSnapshot,
    request: StageRequest,
) -> tuple[list[StatInput], list[str], Mapping[str, object]]:
    if request.mode_policy not in {None, "normal", "tournament"}:
        raise V3StatInputCompilerError(f"Unsupported mode_policy for baseline_max_progression: {request.mode_policy}")

    base_context = request.loadout_context or "Farming"
    progressed_snapshot = _progress_snapshot_to_account_known_workshop_ceilings(snapshot)
    compiled = compile_v3_baseline_loadout_stat_inputs(
        progressed_snapshot,
        module_context=base_context,
    )

    return (
        list(compiled.stat_inputs),
        list(compiled.missing),
        {
            "module_contribution_ledger": compiled.module_contribution_ledger,
            "layer_gaps": compiled.layer_gaps,
            "mode_policy": request.mode_policy or "normal",
            "workshop_progression_rule": "coin_level := end_level when present else current coin_level",
        },
    )


def compose_static_stage(snapshot: AccountSnapshot, request: StageRequest) -> ResolvedStatBook:
    included_families = _STAGE_FAMILY_CONTRACT[request.stage]
    if request.family_overrides:
        included_families = tuple(request.family_overrides)

    stat_inputs, missing, debug = _compile_stage_inputs(snapshot, request)
    if missing and request.strict_missing:
        raise V3StatInputCompilerError(
            f"stage_missing_inputs:{request.stage}:" + ",".join(sorted(set(missing))[:20])
        )
    if missing:
        debug = dict(debug)
        debug["missing"] = sorted(set(missing))

    routed = _route_categories(stat_inputs)
    policy = request.mode_policy if request.stage == "baseline_max_progression" else None
    return _build_resolved_statbook(
        context=request.stage,
        stat_inputs=routed,
        included_families=included_families,
        policy=policy,
        debug_breakdowns=debug if request.debug else None,
    )


def compose_baseline_account(snapshot: AccountSnapshot) -> ResolvedStatBook:
    return compose_static_stage(snapshot, StageRequest(stage="baseline_account"))


def compose_baseline_gem_respec(snapshot: AccountSnapshot) -> ResolvedStatBook:
    return compose_static_stage(snapshot, StageRequest(stage="baseline_gem_respec"))


def compose_baseline_loadout(
    snapshot: AccountSnapshot,
    *,
    loadout_context: str,
) -> ResolvedStatBook:
    return compose_static_stage(
        snapshot,
        StageRequest(stage="baseline_loadout", loadout_context=loadout_context),
    )


def compose_baseline_max_progression(
    snapshot: AccountSnapshot,
    *,
    loadout_context: str,
    mode_policy: ModePolicy,
) -> ResolvedStatBook:
    return compose_static_stage(
        snapshot,
        StageRequest(
            stage="baseline_max_progression",
            loadout_context=loadout_context,
            mode_policy=mode_policy,
        ),
    )


def wave_engine(*, baseline_loadout: ResolvedStatBook, actual_wave: int) -> RunWaveState:
    eals = baseline_loadout.resolved_targets.get("eals_pct", 0.0)
    ehls = baseline_loadout.resolved_targets.get("ehls_pct", 0.0)
    return make_wave_state(
        W_actual=actual_wave,
        eals=SkipRamp(start=0.0, end=float(eals), ramp_waves=1000),
        ehls=SkipRamp(start=0.0, end=float(ehls), ramp_waves=1000),
    )


def runtime_overlay_materializer(
    *,
    baseline_loadout: ResolvedStatBook,
    wave_state: RunWaveState,
) -> list[StatInput]:
    _ = baseline_loadout
    return [
        StatInput(
            stat_id="wave_attack_index",
            phase=Phase.AT_WAVE,
            derived_value=float(wave_state.W_attack),
            provenance="overlay:wave_engine",
            contributor_family="battle_condition",
        ),
        StatInput(
            stat_id="wave_health_index",
            phase=Phase.AT_WAVE,
            derived_value=float(wave_state.W_health),
            provenance="overlay:wave_engine",
            contributor_family="battle_condition",
        ),
    ]


def compose_at_wave(
    *,
    baseline_loadout: ResolvedStatBook,
    actual_wave: int,
) -> RuntimeStateSeed:
    wave_state = wave_engine(baseline_loadout=baseline_loadout, actual_wave=actual_wave)
    overlay_inputs = runtime_overlay_materializer(
        baseline_loadout=baseline_loadout,
        wave_state=wave_state,
    )
    composed_inputs = list(baseline_loadout.emitted_stat_inputs) + overlay_inputs
    at_wave = _build_resolved_statbook(
        context="at_wave",
        stat_inputs=composed_inputs,
        included_families=baseline_loadout.included_families + ("battle_condition",),
        policy=baseline_loadout.policy,
        debug_breakdowns=None,
    )
    return RuntimeStateSeed(at_wave=at_wave, wave_state=wave_state)


def runtime_state_executor(seed: RuntimeStateSeed) -> RuntimeExecutionResult:
    """Runtime state executor placeholder (deterministic, no combat simulation yet)."""
    return RuntimeExecutionResult(
        terminal_state={
            "context": "runtime_state_executor_placeholder",
            "actual_wave": seed.wave_state.W_actual,
        },
        combat_result={
            "status": "not_implemented",
            "reason": "runtime_state_execution_not_yet_integrated",
        },
    )
