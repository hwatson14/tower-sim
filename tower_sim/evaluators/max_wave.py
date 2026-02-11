from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from math import isfinite
import time
from typing import Any, Dict, List, Optional, Tuple

from tower_sim.engines.combat.boss_engine import BossCombatEngine, BossCombatInputs, MissingMechanicError
from tower_sim.engines.combat_stat_derivation import (
    build_canonical_stat_inputs,
    build_canonical_wave_row,
    build_canonical_wave_snapshot,
    cached_tournament_heat_table,
    canonical_stat_inputs_for_wave,
    derive_canonical_combat_snapshot,
    resolve_canonical_heat_magnitudes,
    resolve_canonical_wave_damage,
    resolve_canonical_wave_damage_for_attack_wave,
    validate_boss_survivability_spec,
)
from tower_sim.engines.combat.boss_survivability import (
    BossContext,
    BossDataError,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)
from tower_sim.libs.boss_hit_interval import BossHitIntervalError, boss_hit_interval_seconds
from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.run.context import RunContext
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.registry.naming_contract import (
    alias_to_stat_id_map,
    unsupported_or_unmapped_items,
    validate_registry_parity,
)
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.engines.tier_rule_apply import SUPPORTED_BC
from tower_sim.engines.tier_rules import build_tier_rules
from tower_sim.engines.wave_engine import RunWaveState, SkipRamp, make_wave_state
from tower_sim.engines.uptime import (
    TimedEffect,
    aggregate_uptime,
    gcomp_sec,
    build_bot_effects,
    build_gcomp_activation_intervals,
    build_periodic_activation_intervals,
    overlap_fraction,
    uniform_event_times_from_rate,
)
from tower_sim.engines.wave_time import wa_reduction_from_snapshot, wave_seconds
from tower_sim.loaders.account_snapshot_compiler import resolve_loadout


class MaxWaveEvaluator:
    def __init__(self, bc_table_path: Optional[Path] = None) -> None:
        self._bc_table_path = bc_table_path

    def preflight(
        self,
        problem_spec: ProblemSpec,
        ids_snapshot: AccountSnapshot,
    ) -> Dict[str, Any]:
        preflight = _run_preflight(problem_spec=problem_spec, ids_snapshot=ids_snapshot)
        return {
            "evaluator": problem_spec.evaluator,
            "fail_closed": bool(preflight.missing or preflight.override_collisions),
            "missing": preflight.missing,
            "override_collisions": preflight.override_collisions,
            "w_max": None,
            "diagnostics": preflight.diagnostics,
            "assumptions_manifest": preflight.assumptions_manifest,
        }

    def evaluate(
        self,
        problem_spec: ProblemSpec,
        ids_snapshot: AccountSnapshot,
    ) -> Dict[str, Any]:
        preflight = _run_preflight(problem_spec=problem_spec, ids_snapshot=ids_snapshot)
        if preflight.missing or preflight.override_collisions:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": preflight.missing,
                "override_collisions": preflight.override_collisions,
                "w_max": None,
                "diagnostics": preflight.diagnostics,
                "assumptions_manifest": preflight.assumptions_manifest,
            }

        diagnostics = dict(preflight.diagnostics)
        missing: List[str] = []

        engine = StatEngine(registry=preflight.registry)
        engine_result = None
        engine_result_base = None
        try:
            if preflight.tier_rules is None:
                engine_result = engine.build(preflight.stat_inputs, wave_state=preflight.wave_state)
                engine_result_base = engine.build(preflight.stat_inputs)
            else:
                engine_result = engine.build_with_tier_rules(
                    preflight.stat_inputs,
                    preflight.tier_rules,
                    wave_state=preflight.wave_state,
                )
                engine_result_base = engine.build_with_tier_rules(
                    preflight.stat_inputs,
                    preflight.tier_rules,
                )
            diagnostics["statbook_rows"] = len(engine_result.statbook.rows)
        except Exception as exc:  # noqa: BLE001
            diagnostics["stat_engine_error"] = str(exc)
            missing.append("stat_engine")

        stat_inputs_for_scenario_wave, perk_diag = canonical_stat_inputs_for_wave(
            registry=preflight.registry,
            stat_inputs=preflight.stat_inputs,
            scenario=problem_spec.scenario,
            wave=problem_spec.scenario.wave,
        )
        diagnostics["perk_timeline_scenario_wave"] = perk_diag

        wave_snapshot = _resolve_wave_snapshot(
            problem_spec,
            stat_inputs_for_scenario_wave,
            engine_result_base,
            preflight.registry,
            preflight.tier_rules,
            preflight.run_context,
            preflight.wave_state,
            ids_snapshot,
            missing,
            diagnostics,
        )
        if wave_snapshot is not None:
            diagnostics["at_wave_snapshot"] = {
                "wave": wave_snapshot.wave,
                "applied_bc": wave_snapshot.applied_bc,
                "applied_heat": wave_snapshot.applied_heat,
            }

        combat_snapshot, survivability_missing = derive_canonical_combat_snapshot(
            engine_result_base, wave_snapshot
        )
        if combat_snapshot is not None:
            diagnostics["combat_snapshot_sources_scenario_wave"] = {
                stat_id: [contrib.source for contrib in contribs]
                for stat_id, contribs in combat_snapshot.contributions.items()
            }
        uptime_diag = _build_timing_uptime_diagnostics(
            problem_spec=problem_spec,
            ids_snapshot=ids_snapshot,
            wave_snapshot=wave_snapshot,
        )
        diagnostics["timing_uptime"] = uptime_diag
        if survivability_missing:
            diagnostics["missing_survivability_stats"] = survivability_missing
            missing.extend(survivability_missing)

        wave_damage, wave_damage_missing, wave_damage_diag = resolve_canonical_wave_damage(
            problem_spec=problem_spec,
            wave_state=preflight.wave_state,
        )
        diagnostics.update({k: v for k, v in wave_damage_diag.items() if k not in diagnostics})
        if wave_damage_missing:
            diagnostics["missing_wave_damage"] = wave_damage_missing
            missing.extend(wave_damage_missing)

        if missing:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": sorted(set(missing)),
                "override_collisions": [],
                "w_max": None,
                "diagnostics": diagnostics,
                "assumptions_manifest": preflight.assumptions_manifest,
            }

        (
            w_max,
            failure_wave,
            failure_reason,
            failure_snapshot,
            trace,
            search_diagnostics,
            search_missing,
        ) = _search_wmax(
            problem_spec=problem_spec,
            stat_inputs=preflight.stat_inputs,
            engine_result=engine_result_base,
            registry=preflight.registry,
            tier_rules=preflight.tier_rules,
            run_context=preflight.run_context,
            ids_snapshot=ids_snapshot,
        )
        if search_missing:
            missing.extend(search_missing)
            if search_diagnostics:
                diagnostics["w_max_search"] = search_diagnostics
        else:
            diagnostics["w_max_search"] = search_diagnostics
            diagnostics["margin_trace"] = trace
            diagnostics["boss_survivability"] = search_diagnostics["last_wave_result"]

        boss_combat_error = _probe_boss_combat(
            problem_spec,
            engine_result_base,
            wave_snapshot,
            wave_damage,
        )
        if boss_combat_error is not None:
            diagnostics["boss_combat_error"] = boss_combat_error

        missing = sorted(set(missing))
        fail_closed = bool(missing)
        return {
            "evaluator": problem_spec.evaluator,
            "fail_closed": fail_closed,
            "missing": missing,
            "override_collisions": [],
            "w_max": w_max if not fail_closed else None,
            "failure_wave": None if fail_closed else failure_wave,
            "failure_reason": None if fail_closed else failure_reason,
            "at_failure_snapshot": None if fail_closed else failure_snapshot,
            "diagnostics": diagnostics,
            "assumptions_manifest": preflight.assumptions_manifest,
        }


@dataclass(frozen=True)
class _PreflightResult:
    missing: List[str]
    override_collisions: List[str]
    diagnostics: Dict[str, Any]
    assumptions_manifest: Dict[str, Any]
    stat_inputs: List[StatInput]
    registry: Any
    run_context: RunContext
    tier_rules: Optional[Any]
    wave_state: Optional[RunWaveState]


def _run_preflight(
    *,
    problem_spec: ProblemSpec,
    ids_snapshot: AccountSnapshot,
) -> _PreflightResult:
    preflight_started = time.perf_counter()
    missing: List[str] = []
    diagnostics: Dict[str, Any] = {}
    override_collisions: List[str] = []
    run_context = RunContext.from_mode(
        problem_spec.scenario.mode,
        tier=str(problem_spec.scenario.tier),
    )

    canonical_inputs = build_canonical_stat_inputs(
        problem_spec=problem_spec,
        ids_snapshot=ids_snapshot,
        registry=default_registry(),
    )
    stat_inputs = canonical_inputs.stat_inputs
    diagnostics["core_stat_override_policy"] = canonical_inputs.core_stat_override_policy
    if canonical_inputs.compiled_missing:
        diagnostics["compiled_missing"] = canonical_inputs.compiled_missing
    if canonical_inputs.blocked_core_overrides:
        diagnostics["blocked_core_stat_overrides"] = canonical_inputs.blocked_core_overrides
        override_collisions = canonical_inputs.blocked_core_overrides
    if canonical_inputs.invalid_stat_inputs:
        diagnostics["invalid_stat_inputs"] = canonical_inputs.invalid_stat_inputs
        missing.extend(canonical_inputs.invalid_stat_inputs)
    if canonical_inputs.missing_required_stat_inputs:
        diagnostics["missing_stat_inputs"] = canonical_inputs.missing_required_stat_inputs
        missing.extend(canonical_inputs.missing_required_stat_inputs)

    wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
    if wave_state is not None:
        diagnostics["wave_state"] = asdict(wave_state)
    if wave_state_missing:
        diagnostics["missing_wave_state"] = wave_state_missing
        missing.extend(wave_state_missing)

    tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
    if tier_rule_missing:
        diagnostics["missing_tier_rules"] = tier_rule_missing
        missing.extend(tier_rule_missing)
    registry = default_registry()

    naming_errors = list(validate_registry_parity(registry))
    if naming_errors:
        diagnostics["naming_contract_errors"] = naming_errors
        missing.extend(naming_errors)
    diagnostics["canonical_naming_contract"] = {
        "aliases": dict(sorted(alias_to_stat_id_map().items())),
        "status": "ok" if not naming_errors else "error",
    }

    unsupported_items = list(unsupported_or_unmapped_items(canonical_inputs.compiled_missing))
    if unsupported_items:
        diagnostics["unsupported_decisive_items"] = unsupported_items
        missing.extend(f"ids_unmapped_or_unsupported:{item}" for item in unsupported_items)

    wave_damage, wave_damage_missing, wave_damage_diag = resolve_canonical_wave_damage(
        problem_spec=problem_spec,
        wave_state=wave_state,
    )
    diagnostics.update(wave_damage_diag)
    if wave_damage_missing:
        diagnostics["missing_wave_damage"] = wave_damage_missing
        missing.extend(wave_damage_missing)

    boss_missing, boss_diagnostics = validate_boss_survivability_spec(problem_spec)
    if boss_missing:
        diagnostics["missing_boss_survivability"] = boss_missing
        missing.extend(boss_missing)
    if boss_diagnostics:
        diagnostics["boss_survivability_validation"] = boss_diagnostics

    _, heat_row, heat_missing = resolve_canonical_heat_magnitudes(
        problem_spec=problem_spec,
        registry=registry,
        wave=problem_spec.scenario.wave,
    )
    if heat_row is not None:
        diagnostics.setdefault("wave_rows", {})[str(problem_spec.scenario.wave)] = heat_row
    if heat_missing:
        diagnostics["missing_heat"] = heat_missing
        missing.extend(heat_missing)

    diagnostics["preflight_ms"] = (time.perf_counter() - preflight_started) * 1000.0
    return _PreflightResult(
        missing=sorted(set(missing)),
        override_collisions=sorted(set(override_collisions)),
        diagnostics=diagnostics,
        assumptions_manifest=_build_assumptions_manifest(problem_spec),
        stat_inputs=stat_inputs,
        registry=registry,
        run_context=run_context,
        tier_rules=tier_rules,
        wave_state=wave_state,
    )



def _build_assumptions_manifest(problem_spec: ProblemSpec) -> Dict[str, Any]:
    scenario = problem_spec.scenario
    mode = (scenario.mode or "").strip().lower()
    is_tournament = mode == "tournament"
    league = (scenario.league or "").strip().lower()
    return {
        "schema_version": "v1",
        "policy_version": "v1",
        "tolerance_version": "v1",
        "determinism": {
            "randomness_allowed": False,
            "perk_timeline_external_only": True,
        },
        "perk_timeline": {
            "required": not is_tournament,
            "enabled": not is_tournament,
            "source": None if is_tournament else getattr(scenario, "perk_timeline_path", None),
        },
        "tournament": {
            "heat_required": is_tournament,
            "bc_required": is_tournament,
            "perks_allowed": not is_tournament,
            "league": league or None,
            "supported_leagues": ["champion", "legend"],
        },
        "parity_tolerances": {
            "wmax_wave_relative": 0.10,
            "stats_relative": 0.01,
            "status": "provisional",
        },
    }

def _load_tier_rules(
    problem_spec: ProblemSpec,
    run_context: RunContext,
) -> Tuple[Optional[Any], List[str]]:
    missing: List[str] = []
    if problem_spec.scenario.tier < 14:
        return None, missing
    bc_path = _resolve_bc_path(problem_spec)
    try:
        catalog = load_tier_battle_conditions(bc_path, allow_incomplete=True)
    except FileNotFoundError:
        missing.append("tier_battle_conditions_table")
        return None, missing
    try:
        rules = build_tier_rules(problem_spec.scenario.tier, run_context, catalog)
    except ValueError:
        missing.append("tier_battle_conditions")
        return None, missing
    unsupported = [
        condition
        for condition in rules.conditions
        if (condition.name, condition.kind, condition.unit) not in SUPPORTED_BC
    ]
    if unsupported:
        missing.append("tier_battle_conditions_unsupported")
        return None, missing
    return rules, missing


def _resolve_bc_path(problem_spec: ProblemSpec) -> Path:
    return resolve_table_path("tier_battle_conditions")


def _maybe_build_wave_state(problem_spec: ProblemSpec) -> Tuple[Optional[Any], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if scenario.eals_ramp is None or scenario.ehls_ramp is None:
        return None, missing
    eals = SkipRamp(
        start=scenario.eals_ramp.start,
        end=scenario.eals_ramp.end,
        ramp_waves=scenario.eals_ramp.ramp_waves,
    )
    ehls = SkipRamp(
        start=scenario.ehls_ramp.start,
        end=scenario.ehls_ramp.end,
        ramp_waves=scenario.ehls_ramp.ramp_waves,
    )
    return make_wave_state(scenario.wave, eals, ehls), missing


def _probe_boss_combat(
    problem_spec: ProblemSpec,
    engine_result,
    wave_snapshot: Optional[AtWaveSnapshot],
    wave_damage: Optional[float],
) -> Optional[str]:
    if engine_result is None or wave_damage is None:
        return "boss_combat_inputs"
    try:
        combat_snapshot, combat_missing = derive_canonical_combat_snapshot(engine_result, wave_snapshot)
        if combat_missing or combat_snapshot is None:
            return "boss_combat_inputs"
        inputs = BossCombatInputs(
            wave=problem_spec.scenario.wave,
            wave_damage=wave_damage,
            tower_hp=combat_snapshot.values["tower_hp"],
            tower_regen=combat_snapshot.values["tower_regen"],
            defense_pct=combat_snapshot.values["def_pct"],
            thorns_pct=combat_snapshot.values["thorns_damage_mult"],
            pc_frac=None,
            pc_boss_mult=None,
            package_chance=None,
            package_heal=None,
            damage_reduction=None,
            provenance="problem_spec",
        )
        BossCombatEngine().evaluate(inputs)
    except MissingMechanicError as exc:
        message = str(exc)
        if "Missing required boss combat inputs" in message:
            return "boss_combat_inputs"
        else:
            return "boss_combat_mechanics"
    return None


def _resolve_wave_snapshot(
    problem_spec: ProblemSpec,
    stat_inputs: List,
    engine_result,
    registry,
    tier_rules,
    run_context: RunContext,
    wave_state,
    ids_snapshot: AccountSnapshot,
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> Optional[AtWaveSnapshot]:
    if engine_result is None:
        missing.append("wave_snapshot_inputs")
        return None
    heat_magnitudes, heat_row, heat_missing = resolve_canonical_heat_magnitudes(
        problem_spec=problem_spec,
        registry=registry,
        wave=problem_spec.scenario.wave,
    )
    if heat_row is not None:
        diagnostics.setdefault("wave_rows", {})[str(problem_spec.scenario.wave)] = heat_row
    if heat_missing:
        missing.extend(heat_missing)
    try:
        wave_row = {
            "wave": int(problem_spec.scenario.wave),
            "enemy_attack_wave": int(wave_state.W_attack) if wave_state is not None else int(problem_spec.scenario.wave),
            "enemy_health_wave": int(wave_state.W_health) if wave_state is not None else int(problem_spec.scenario.wave),
        }
        wave_snapshot, wave_snapshot_missing = build_canonical_wave_snapshot(
            ids_snapshot=ids_snapshot,
            wave=problem_spec.scenario.wave,
            stat_inputs=stat_inputs,
            engine_result=engine_result,
            registry=registry,
            tier_rules=tier_rules,
            run_context=run_context,
            heat_magnitudes=heat_magnitudes,
            wave_row=wave_row,
        )
        if wave_snapshot_missing:
            missing.extend(wave_snapshot_missing)
            return None
        return wave_snapshot
    except StatSnapshotError as exc:
        missing.append("wave_snapshot")
        diagnostics["wave_snapshot_error"] = str(exc)
        return None


def _search_wmax(
    *,
    problem_spec: ProblemSpec,
    stat_inputs: List,
    engine_result,
    registry,
    tier_rules,
    run_context: RunContext,
    ids_snapshot: AccountSnapshot,
    trace_depth: int = 5,
) -> Tuple[
    Optional[int],
    Optional[int],
    Optional[str],
    Optional[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, Any],
    List[str],
]:
    scenario = problem_spec.scenario
    missing: List[str] = []
    diagnostics: Dict[str, Any] = {}

    if scenario.boss_survivability is None:
        return None, None, None, None, [], {}, ["boss_survivability_inputs"]
    if engine_result is None:
        return None, None, None, None, [], {}, ["stat_engine"]
    max_wave = int(scenario.wave)
    if max_wave <= 0:
        return None, None, None, None, [], {}, ["wave_limit"]

    cache: Dict[int, Tuple[Dict[str, Any], bool, Dict[str, Any]]] = {}
    failure_snapshots: Dict[int, Dict[str, Any]] = {}
    history: List[Dict[str, Any]] = []
    failure_wave: Optional[int] = None
    failure_reason: Optional[str] = None
    failure_snapshot: Optional[Dict[str, Any]] = None

    def evaluate_wave(wave: int) -> Tuple[Optional[Dict[str, Any]], Optional[bool], List[str]]:
        nonlocal failure_wave, failure_reason, failure_snapshot
        if wave in cache:
            entry, success, _result = cache[wave]
            return entry, success, []

        wave_row, wave_row_missing = build_canonical_wave_row(problem_spec, registry, wave=wave)
        if wave_row_missing or wave_row is None:
            return None, None, wave_row_missing

        stat_inputs_at_wave, perk_diag = canonical_stat_inputs_for_wave(
            registry=registry,
            stat_inputs=stat_inputs,
            scenario=scenario,
            wave=wave,
        )
        diagnostics.setdefault("perk_timeline", {})[str(wave)] = perk_diag

        try:
            wave_snapshot, wave_snapshot_missing = build_canonical_wave_snapshot(
                ids_snapshot=ids_snapshot,
                wave=wave,
                stat_inputs=stat_inputs_at_wave,
                engine_result=engine_result,
                registry=registry,
                tier_rules=tier_rules,
                run_context=run_context,
                heat_magnitudes=wave_row.get("heat_magnitudes"),
                wave_row=wave_row,
            )
            if wave_snapshot_missing:
                return None, None, wave_snapshot_missing
        except StatSnapshotError as exc:
            diagnostics["wave_snapshot_error"] = str(exc)
            return None, None, ["wave_snapshot"]

        combat_snapshot, survivability_missing = derive_canonical_combat_snapshot(
            engine_result, wave_snapshot
        )
        survivability_stats = None if combat_snapshot is None else combat_snapshot.values
        if combat_snapshot is not None:
            diagnostics.setdefault("combat_snapshot_sources", {})[str(wave)] = {
                stat_id: [contrib.source for contrib in contribs]
                for stat_id, contribs in combat_snapshot.contributions.items()
            }
        if survivability_missing:
            return None, None, survivability_missing

        attack_wave = int(wave_row["enemy_attack_wave"])
        wave_damage, wave_damage_missing = resolve_canonical_wave_damage_for_attack_wave(
            problem_spec=problem_spec,
            attack_wave=attack_wave,
        )
        if wave_damage_missing:
            return None, None, wave_damage_missing

        result = _resolve_boss_survivability(
            problem_spec, wave, wave_damage, survivability_stats
        )
        if "error" in result:
            diagnostics["boss_survivability_error"] = result["error"]
            return None, None, ["boss_survivability_params"]

        margin = _margin_from_outcome(result)
        outcome = result.get("outcome", "unknown")
        entry = {
            "wave": wave,
            "outcome": outcome,
            "ttk_seconds": result.get("ttk_seconds"),
            "ttd_seconds": result.get("ttd_seconds"),
            "margin_seconds": margin,
        }
        success = outcome == "tower_kills_boss"
        cache[wave] = (entry, success, result)
        history.append(entry)
        if not success:
            failure_snapshots[wave] = _build_failure_snapshot(
                problem_spec=problem_spec,
                survivability_stats=survivability_stats,
                wave=wave,
                wave_damage=wave_damage,
                result=result,
            )
            if failure_wave is None or wave < failure_wave:
                failure_wave = wave
                failure_reason = outcome
                failure_snapshot = failure_snapshots[wave]
        return entry, success, []

    def check_monotonicity() -> Tuple[Optional[bool], List[str]]:
        samples = max(3, min(7, max_wave))
        step = max(1, (max_wave - 1) // (samples - 1)) if max_wave > 1 else 1
        sample_waves = sorted(
            {
                wave
                for wave in ({1, max_wave} | {1 + step * i for i in range(samples)})
                if 1 <= wave <= max_wave
            }
        )
        seen_fail = False
        for wave in sample_waves:
            _, success, sample_missing = evaluate_wave(wave)
            if sample_missing:
                return None, sample_missing
            if success is False:
                seen_fail = True
            if success is True and seen_fail:
                diagnostics["monotonicity_inversion"] = {"at_wave": wave}
                return False, []
        return True, []

    monotonic, mono_missing = check_monotonicity()
    if mono_missing:
        return None, None, None, None, [], diagnostics, mono_missing
    diagnostics["monotonic"] = monotonic

    last_result: Dict[str, Any] = {}
    evaluated: set[int] = set(cache.keys())
    w_max = 0

    if monotonic:
        diagnostics["search_strategy"] = "exponential_binary"
        low = 0
        high = 1
        while high <= max_wave:
            entry, success, eval_missing = evaluate_wave(high)
            if eval_missing:
                return None, None, None, None, [], diagnostics, eval_missing
            evaluated.add(high)
            if entry is not None:
                last_result = cache[high][2]
            if success:
                low = high
                high *= 2
            else:
                break
        if high > max_wave:
            w_max = max_wave if low <= max_wave else 0
        else:
            left = low + 1
            right = min(high - 1, max_wave)
            w_max = low
            while left <= right:
                mid = (left + right) // 2
                entry, success, eval_missing = evaluate_wave(mid)
                if eval_missing:
                    return None, None, None, None, [], diagnostics, eval_missing
                evaluated.add(mid)
                if entry is not None:
                    last_result = cache[mid][2]
                if success:
                    w_max = mid
                    left = mid + 1
                else:
                    right = mid - 1
    else:
        diagnostics["search_strategy"] = "grid_refine"
        step = max(50, max_wave // 20) if max_wave > 0 else 1
        sampled = list(range(1, max_wave + 1, step))
        if sampled[-1] != max_wave:
            sampled.append(max_wave)
        last_success = 0
        for idx, wave in enumerate(sampled):
            entry, success, eval_missing = evaluate_wave(wave)
            if eval_missing:
                return None, None, None, None, [], diagnostics, eval_missing
            evaluated.add(wave)
            if entry is not None:
                last_result = cache[wave][2]
            if success:
                last_success = max(last_success, wave)
            if idx == 0:
                continue
            prev_wave = sampled[idx - 1]
            if prev_wave + 1 > wave:
                continue
            for inner_wave in range(prev_wave + 1, wave):
                inner_entry, inner_success, inner_missing = evaluate_wave(inner_wave)
                if inner_missing:
                    return None, None, None, None, [], diagnostics, inner_missing
                evaluated.add(inner_wave)
                if inner_entry is not None:
                    last_result = cache[inner_wave][2]
                if inner_success:
                    last_success = max(last_success, inner_wave)
        w_max = last_success

    trace = history[-trace_depth:] if history else []

    if w_max < max_wave:
        boundary_wave = w_max + 1
        _, boundary_success, boundary_missing = evaluate_wave(boundary_wave)
        if boundary_missing:
            return None, None, None, None, [], diagnostics, boundary_missing
        if boundary_success is False:
            failure_wave = boundary_wave
            failure_reason = cache[boundary_wave][0].get("outcome")
            failure_snapshot = failure_snapshots.get(boundary_wave)

    diagnostics.update(
        {
            "max_wave": max_wave,
            "evaluated_waves": len(evaluated),
            "trace_depth": trace_depth,
            "last_wave_result": last_result,
        }
    )
    return w_max, failure_wave, failure_reason, failure_snapshot, trace, diagnostics, missing


def _margin_from_outcome(result: Dict[str, Any]) -> Optional[float]:
    ttk = result.get("ttk_seconds")
    ttd = result.get("ttd_seconds")
    if ttk is None or ttd is None:
        return None
    if not (isfinite(ttk) or isfinite(ttd)):
        return None
    return ttd - ttk


def _build_failure_snapshot(
    problem_spec: ProblemSpec,
    survivability_stats: Dict[str, float],
    wave: int,
    wave_damage: float,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    spec = problem_spec.scenario.boss_survivability
    if spec is None:
        return {}
    hit_interval_id = spec.combat_params.get("hit_interval_id", "default")
    hit_interval = boss_hit_interval_seconds(str(hit_interval_id))
    combat_params = dict(spec.combat_params)
    combat_params.update(
        {
            "tower_hp": survivability_stats["tower_hp"],
            "tower_regen": survivability_stats["tower_regen"],
            "defense_pct": survivability_stats["def_pct"],
            "wall_hp": survivability_stats["wall_hp"],
            "wall_regen": survivability_stats["wall_regen"],
            "thorns_frac": survivability_stats["thorns_damage_mult"],
        }
    )
    used_keys = [
        "tower_hp",
        "tower_regen",
        "defense_pct",
        "wall_hp",
        "wall_regen",
        "defense_abs",
        "damage_reduction",
        "thorns_frac",
        "pc_frac",
        "pc_boss_mult",
        "orb_damage_frac",
        "electrons_damage_frac",
    ]
    tower_stats = {key: combat_params.get(key) for key in used_keys if key in combat_params}
    return {
        "wave": wave,
        "tower_stats": tower_stats,
        "boss_stats": {
            "attack": wave_damage,
            "attack_interval": hit_interval,
            "enrage_mult": spec.boss.enrage_mult or 1.0,
        },
        "margins": {
            "ttk_seconds": result.get("ttk_seconds"),
            "ttd_seconds": result.get("ttd_seconds"),
            "margin_seconds": _margin_from_outcome(result),
        },
    }


def _resolve_boss_survivability(
    problem_spec: ProblemSpec,
    wave: int,
    wave_damage: float,
    survivability_stats: Dict[str, float],
) -> Dict[str, Any]:
    spec = problem_spec.scenario.boss_survivability
    if spec is None:
        return {}
    try:
        hit_interval_id = spec.combat_params.get("hit_interval_id", "default")
        hit_interval = boss_hit_interval_seconds(str(hit_interval_id))
        boss = BossStats(
            hp=None,
            attack=wave_damage,
            attack_interval=hit_interval,
            enrage_mult=spec.boss.enrage_mult or 1.0,
        )
        tower = TowerDefense(
            dr_frac=spec.tower.dr_frac,
            regen_per_sec=spec.tower.regen_per_sec,
            shields=spec.tower.shields,
        )
        combat_params = dict(spec.combat_params)
        combat_params["tower_hp"] = survivability_stats["tower_hp"]
        combat_params["tower_regen"] = survivability_stats["tower_regen"]
        combat_params["defense_pct"] = survivability_stats["def_pct"]
        combat_params["wall_hp"] = survivability_stats["wall_hp"]
        combat_params["wall_regen"] = survivability_stats["wall_regen"]
        combat_params["thorns_frac"] = survivability_stats["thorns_damage_mult"]
        ctx = BossContext(
            wave=wave,
            tier=problem_spec.scenario.tier,
            league=problem_spec.scenario.league or "",
            boss=boss,
            tower=tower,
            combat_params=combat_params,
            bc_params=spec.bc_params,
        )
        return resolve_boss_fight(ctx)
    except (BossDataError, BossHitIntervalError) as exc:
        return {"error": str(exc)}


def _build_timing_uptime_diagnostics(
    *,
    problem_spec: ProblemSpec,
    ids_snapshot: AccountSnapshot,
    wave_snapshot: Optional[AtWaveSnapshot],
) -> Dict[str, Any]:
    window_s = 600.0
    run_type = str(getattr(problem_spec.scenario.mode, "value", problem_spec.scenario.mode)).lower().strip()
    wa_reduction = wa_reduction_from_snapshot(snapshot=ids_snapshot, run_type=run_type)
    ws = wave_seconds(wa_reduction=wa_reduction, tournament=run_type == "tournament")

    snapshot_values = wave_snapshot.values if wave_snapshot is not None else {}
    package_chance_stat_id = "workshop_package_chance"
    package_chance_raw = snapshot_values.get(package_chance_stat_id)
    package_chance_missing = package_chance_raw is None
    package_chance = float(package_chance_raw or 0.0)

    preset_name = (
        "Tourney" if run_type == "tournament" else "Farming" if run_type == "farming" else ids_snapshot.default_preset
    )
    loadout = resolve_loadout(ids_snapshot, preset_name)

    gcomp_enabled = False
    gcomp_rarity = None
    gcomp_seconds = 0.0
    generator_primary = loadout.modules_by_slot["Generator"].primary
    if generator_primary == "Galaxy Compressor":
        module = ids_snapshot.modules_inventory.get("Galaxy Compressor")
        if module is None or module.rarity is None:
            raise ValueError("Galaxy Compressor equipped but inventory rarity is missing.")
        gcomp_rarity = _normalize_module_rarity(module.rarity)
        gcomp_enabled = True
        gcomp_seconds = gcomp_sec(gcomp_rarity)

    if gcomp_enabled and package_chance_missing:
        raise ValueError(
            f"Missing required package chance stat ({package_chance_stat_id}) while Galaxy Compressor is equipped."
        )

    packages_per_second = package_chance / ws if ws > 0 else 0.0
    package_events = uniform_event_times_from_rate(rate_per_second=packages_per_second, window_s=window_s)

    gt_cooldown = float(snapshot_values.get("uw_golden_tower_cooldown", 0.0) or 0.0)
    gt_duration = float(snapshot_values.get("uw_golden_tower_duration", 0.0) or 0.0)
    gt_mult = float(snapshot_values.get("uw_golden_tower_multiplier", 1.0) or 1.0)

    uw_pairs = [
        ("uw_smart_missiles", "uw_smart_missiles_cooldown", None),
        ("uw_death_wave", "uw_death_wave_cooldown", None),
        ("uw_chrono_field", "uw_chrono_field_cooldown", "uw_chrono_field_duration"),
        ("uw_inner_land_mines", "uw_inner_land_mines_cooldown", None),
        ("uw_golden_tower", "uw_golden_tower_cooldown", "uw_golden_tower_duration"),
        ("uw_black_hole", "uw_black_hole_cooldown", "uw_black_hole_duration"),
    ]

    uw_intervals: Dict[str, Any] = {}
    for uw_name, cooldown_id, duration_id in uw_pairs:
        cooldown = float(snapshot_values.get(cooldown_id, 0.0) or 0.0)
        duration = float(snapshot_values.get(duration_id, 0.0) or 0.0) if duration_id else 0.0
        if cooldown <= 0.0:
            continue
        if gcomp_enabled:
            intervals = build_gcomp_activation_intervals(
                base_cooldown_s=cooldown,
                duration_s=duration,
                package_event_times_s=package_events,
                seconds_reduced_per_package=gcomp_seconds,
                window_s=window_s,
                start_on_cooldown=True,
            )
        else:
            intervals = build_periodic_activation_intervals(
                duration_s=duration,
                cooldown_s=cooldown,
                window_s=window_s,
                phase_s=0.0,
            )
        uw_intervals[uw_name] = intervals

    if gt_cooldown <= 0:
        return {
            "window_s": window_s,
            "wa_reduction": wa_reduction,
            "wave_seconds": ws,
            "package_event_model": "uniform_from_rate",
            "package_chance_stat_id": package_chance_stat_id,
            "package_chance_missing": package_chance_missing,
            "packages_per_second": packages_per_second,
            "gcomp_enabled": gcomp_enabled,
            "gcomp_rarity": gcomp_rarity,
            "missing": ["uw_golden_tower_cooldown"],
        }

    gt_intervals = uw_intervals.get("uw_golden_tower", tuple())
    bh_intervals = uw_intervals.get("uw_black_hole", tuple())

    effects = [TimedEffect(name="GT", activation_intervals=gt_intervals, coin_multiplier=gt_mult)]
    bot_levels = ids_snapshot.bot_upgrades
    bot_diag = "present" if bot_levels else "missing"
    if bot_levels:
        effects.extend(build_bot_effects(bot_levels=bot_levels, window_s=window_s))

    summary = aggregate_uptime(effects, window_s=window_s)
    output: Dict[str, Any] = {
        "window_s": window_s,
        "wa_reduction": wa_reduction,
        "wave_seconds": ws,
        "package_event_model": "uniform_from_rate",
        "package_chance_stat_id": package_chance_stat_id,
        "package_chance_missing": package_chance_missing,
        "packages_per_second": packages_per_second,
        "gcomp_enabled": gcomp_enabled,
        "gcomp_rarity": gcomp_rarity,
        "gcomp_seconds_per_package": gcomp_seconds,
        "gt_bh_overlap": overlap_fraction(gt_intervals, bh_intervals, window_s=window_s) if bh_intervals else None,
        "expected_coin_multiplier": summary.expected_coin_multiplier,
        "expected_damage_taken": summary.expected_damage_taken,
        "expected_damage_multiplier": summary.expected_damage_multiplier,
        "bot_levels_source": bot_diag,
        "package_event_count": len(package_events),
        "uw_interval_counts": {name: len(intervals) for name, intervals in uw_intervals.items()},
    }
    if gcomp_enabled and not bh_intervals:
        output.setdefault("warnings", []).append("uw_black_hole_intervals_missing")
    return output


def _normalize_module_rarity(raw_rarity: str) -> str:
    cleaned = raw_rarity.strip()
    while cleaned.endswith("+"):
        cleaned = cleaned[:-1]
    canonical = cleaned.capitalize()
    if canonical not in {"Epic", "Legendary", "Mythic", "Ancestral"}:
        raise ValueError(f"Unsupported module rarity for canonical lookup: {raw_rarity!r}")
    return canonical
