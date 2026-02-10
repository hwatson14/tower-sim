from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from math import isfinite
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tower_sim.engines.combat.boss_engine import BossCombatEngine, BossCombatInputs, MissingMechanicError
from tower_sim.engines.combat.boss_survivability import (
    BossContext,
    BossDataError,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)
from tower_sim.libs.boss_hit_interval import BossHitIntervalError, boss_hit_interval_seconds
from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib
from tower_sim.loaders.bc_heat_loader import HeatDataError, load_tournament_heat_table
from tower_sim.loaders.perk_timeline_loader import apply_perk_timeline_to_inputs
from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.run.context import RunContext
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs, compile_workshop_values_at_wave
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
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


@lru_cache(maxsize=1)
def _cached_tournament_heat_table(scale_path: str, registry_path: str):
    """Cache parsed tournament heat table for repeated per-wave MAX_WAVE lookups.

    Provenance: tables/heat_scale_long.csv + tables/heat_bc_registry.csv
    via tower_sim.loaders.bc_heat_loader.load_tournament_heat_table.
    """
    return load_tournament_heat_table(Path(scale_path), Path(registry_path))


class MaxWaveEvaluator:
    def __init__(self, bc_table_path: Optional[Path] = None) -> None:
        self._bc_table_path = bc_table_path

    def evaluate(
        self,
        problem_spec: ProblemSpec,
        ids_snapshot: AccountSnapshot,
    ) -> Dict[str, Any]:
        missing: List[str] = []
        diagnostics: Dict[str, Any] = {}

        run_context = RunContext.from_mode(
            problem_spec.scenario.mode,
            tier=str(problem_spec.scenario.tier),
        )

        spec_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
        compiled = compile_full_stat_inputs(ids_snapshot)
        stat_inputs = _merge_stat_inputs(spec_inputs, compiled.stat_inputs)
        if compiled.missing:
            diagnostics["compiled_missing"] = compiled.missing

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
        stat_inputs, invalid_stat_inputs = _filter_known_stat_inputs(stat_inputs, registry)
        if invalid_stat_inputs:
            diagnostics["invalid_stat_inputs"] = invalid_stat_inputs
            missing.extend(invalid_stat_inputs)
        missing_stat_inputs = _missing_required_stat_inputs(stat_inputs)
        if missing_stat_inputs:
            diagnostics["missing_stat_inputs"] = missing_stat_inputs
            missing.extend(missing_stat_inputs)

        wave_damage, wave_damage_missing = _resolve_wave_damage(
            problem_spec, wave_state, diagnostics
        )
        if wave_damage_missing:
            diagnostics["missing_wave_damage"] = wave_damage_missing
            missing.extend(wave_damage_missing)
        boss_missing, boss_diagnostics = _validate_boss_survivability_inputs(problem_spec)
        if boss_missing:
            diagnostics["missing_boss_survivability"] = boss_missing
            missing.extend(boss_missing)
        if boss_diagnostics:
            diagnostics["boss_survivability_validation"] = boss_diagnostics
        _resolve_heat_magnitudes(
            problem_spec,
            registry,
            wave=problem_spec.scenario.wave,
            missing=missing,
            diagnostics=diagnostics,
        )

        assumptions_manifest = _build_assumptions_manifest(problem_spec)
        missing = sorted(set(missing))
        if missing:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": missing,
                "w_max": None,
                "diagnostics": diagnostics,
                "assumptions_manifest": assumptions_manifest,
            }

        engine = StatEngine(registry=registry)
        engine_result = None
        engine_result_base = None
        try:
            if tier_rules is None:
                engine_result = engine.build(stat_inputs, wave_state=wave_state)
                engine_result_base = engine.build(stat_inputs)
            else:
                engine_result = engine.build_with_tier_rules(
                    stat_inputs, tier_rules, wave_state=wave_state
                )
                engine_result_base = engine.build_with_tier_rules(stat_inputs, tier_rules)
            diagnostics["statbook_rows"] = len(engine_result.statbook.rows)
        except Exception as exc:  # noqa: BLE001
            diagnostics["stat_engine_error"] = str(exc)
            missing.append("stat_engine")
        stat_inputs_for_scenario_wave, perk_diag = _stat_inputs_for_wave(
            registry=registry,
            stat_inputs=stat_inputs,
            scenario=problem_spec.scenario,
            wave=problem_spec.scenario.wave,
        )
        diagnostics["perk_timeline_scenario_wave"] = perk_diag

        wave_snapshot = _resolve_wave_snapshot(
            problem_spec,
            stat_inputs_for_scenario_wave,
            engine_result_base,
            registry,
            tier_rules,
            run_context,
            wave_state,
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

        survivability_stats, survivability_missing = _resolve_survivability_stats(
            engine_result_base, wave_snapshot
        )
        uptime_diag = _build_timing_uptime_diagnostics(
            problem_spec=problem_spec,
            ids_snapshot=ids_snapshot,
            wave_snapshot=wave_snapshot,
        )
        diagnostics["timing_uptime"] = uptime_diag

        if survivability_missing:
            diagnostics["missing_survivability_stats"] = survivability_missing
            missing.extend(survivability_missing)

        assumptions_manifest = _build_assumptions_manifest(problem_spec)
        missing = sorted(set(missing))
        if missing:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": missing,
                "w_max": None,
                "diagnostics": diagnostics,
                "assumptions_manifest": assumptions_manifest,
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
            stat_inputs=stat_inputs,
            engine_result=engine_result_base,
            registry=registry,
            tier_rules=tier_rules,
            run_context=run_context,
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
            "w_max": w_max if not fail_closed else None,
            "failure_wave": None if fail_closed else failure_wave,
            "failure_reason": None if fail_closed else failure_reason,
            "at_failure_snapshot": None if fail_closed else failure_snapshot,
            "diagnostics": diagnostics,
            "assumptions_manifest": assumptions_manifest,
        }



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

def _missing_required_stat_inputs(stat_inputs: Iterable) -> List[str]:
    required = {
        "eals_pct",
        "ehls_pct",
        "orb_damage_mult",
        "death_ray_damage_mult",
        "thorns_damage_mult",
        "plasma_cannon_damage_mult",
        "knockback_mult",
        "tower_hp",
        "tower_regen",
        "wall_hp",
        "wall_regen",
        "def_pct",
    }
    present = {stat_input.stat_id for stat_input in stat_inputs}
    return [f"stat_input:{stat_id}" for stat_id in sorted(required - present)]


def _merge_stat_inputs(
    spec_inputs: List[StatInput],
    compiled_inputs: List[StatInput],
) -> List[StatInput]:
    existing = {(item.stat_id, item.phase) for item in spec_inputs}
    merged = list(spec_inputs)
    for item in compiled_inputs:
        if (item.stat_id, item.phase) in existing:
            continue
        merged.append(item)
    return merged


def _filter_known_stat_inputs(
    stat_inputs: List[StatInput],
    registry,
) -> Tuple[List[StatInput], List[str]]:
    filtered: List[StatInput] = []
    invalid: List[str] = []
    for item in stat_inputs:
        try:
            registry.validate_stat_id(item.stat_id)
        except Exception:  # noqa: BLE001
            invalid.append(item.stat_id)
            continue
        filtered.append(item)
    return filtered, sorted(set(invalid))


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
    return Path(__file__).resolve().parents[2] / "tables" / "tier_battle_conditions.csv"


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


def _resolve_wave_damage(
    problem_spec: ProblemSpec,
    wave_state,
    diagnostics: Dict[str, Any],
) -> Tuple[Optional[float], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = _default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing

    lib = EnemyWaveDamageLib.from_repo_tables()
    wave = scenario.wave if wave_state is None else wave_state.W_attack
    try:
        damage = lib.wave_damage(wave_tier, wave)
    except KeyError as exc:
        missing.append("wave_damage_table")
        diagnostics["wave_damage_error"] = str(exc)
        return None, missing
    diagnostics["wave_damage_tier"] = wave_tier
    diagnostics["wave_damage_wave"] = wave
    diagnostics["wave_damage"] = damage
    return damage, missing


def _default_wave_damage_tier(scenario) -> Optional[str]:
    if scenario.mode == "farming":
        return f"Tier {scenario.tier}"
    if scenario.league:
        return scenario.league
    return None


def _probe_boss_combat(
    problem_spec: ProblemSpec,
    engine_result,
    wave_snapshot: Optional[AtWaveSnapshot],
    wave_damage: Optional[float],
) -> Optional[str]:
    if engine_result is None or wave_damage is None:
        return "boss_combat_inputs"
    try:
        start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
        if start_stats is None:
            return "boss_combat_inputs"
        snapshot_values = wave_snapshot.values if wave_snapshot is not None else {}
        tower_hp = snapshot_values.get("tower_hp", start_stats.values.get("tower_hp", 0.0))
        tower_regen = snapshot_values.get(
            "tower_regen", start_stats.values.get("tower_regen", 0.0)
        )
        defense_pct = snapshot_values.get("def_pct", start_stats.values.get("def_pct", 0.0))
        thorns_pct = snapshot_values.get(
            "thorns_damage_mult", start_stats.values.get("thorns_damage_mult")
        )
        inputs = BossCombatInputs(
            wave=problem_spec.scenario.wave,
            wave_damage=wave_damage,
            tower_hp=tower_hp,
            tower_regen=tower_regen,
            defense_pct=defense_pct,
            thorns_pct=thorns_pct,
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
    heat_magnitudes = _resolve_heat_magnitudes(
        problem_spec,
        registry,
        wave=problem_spec.scenario.wave,
        missing=missing,
        diagnostics=diagnostics,
    )
    workshop_at_wave, workshop_missing = compile_workshop_values_at_wave(
        ids_snapshot,
        wave=problem_spec.scenario.wave,
    )
    if workshop_missing:
        missing.extend(workshop_missing)
        return None

    try:
        return build_at_wave_snapshot(
            stat_inputs=stat_inputs,
            engine_result=engine_result,
            registry=registry,
            tier_rules=tier_rules,
            battle_conditions=None,
            wave_state=wave_state,
            wave=problem_spec.scenario.wave,
            run_context=run_context,
            heat_magnitudes=heat_magnitudes,
            per_wave_overrides=workshop_at_wave,
        )
    except StatSnapshotError as exc:
        missing.append("wave_snapshot")
        diagnostics["wave_snapshot_error"] = str(exc)
        return None


def _resolve_heat_magnitudes(
    problem_spec: ProblemSpec,
    registry,
    *,
    wave: int,
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    scenario = problem_spec.scenario
    if scenario.mode != "tournament":
        return None
    if scenario.league is None:
        missing.append("heat_league")
        return None

    row, row_missing = _build_wave_row(problem_spec, registry, wave=wave)
    if row_missing:
        missing.extend(row_missing)
        return None
    diagnostics.setdefault("wave_rows", {})[str(wave)] = row
    return row.get("heat_magnitudes")


def _stat_inputs_for_wave(
    *,
    registry,
    stat_inputs: List,
    scenario,
    wave: int,
) -> Tuple[List, Dict[str, Any]]:
    if scenario.mode == "tournament":
        return stat_inputs, {"enabled": False, "reason": "tournament_mode"}
    return apply_perk_timeline_to_inputs(
        registry=registry,
        stat_inputs=stat_inputs,
        perk_timeline_path=getattr(scenario, "perk_timeline_path", None),
        current_wave=wave,
    )


def _build_wave_row(
    problem_spec: ProblemSpec,
    registry,
    *,
    wave: int,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    wave_state, wave_missing = _resolve_wave_state_for_wave(problem_spec.scenario, wave)
    if wave_missing or wave_state is None:
        return None, wave_missing

    row: Dict[str, Any] = {
        # Wide-row v1 contract: MAX_WAVE consumes these stable keys directly.
        "wave": int(wave),
        "enemy_attack_wave": int(wave_state.W_attack),
        "enemy_health_wave": int(wave_state.W_health),
    }

    if problem_spec.scenario.mode != "tournament":
        return row, []

    table_path = Path(__file__).resolve().parents[2] / "tables" / "heat_scale_long.csv"
    registry_path = Path(__file__).resolve().parents[2] / "tables" / "heat_bc_registry.csv"
    try:
        table = _cached_tournament_heat_table(str(table_path), str(registry_path))
    except (HeatDataError, FileNotFoundError):
        return None, ["heat_tables"]

    league = (problem_spec.scenario.league or "").strip().lower()
    if not league:
        return None, ["heat_league"]

    # Existing tier-rule provenance mapping reused for v1 tournament heat rows.
    bc_to_stats = {
        "orb_resistance:": ["orb_damage_mult"],
        "death_ray_resistance:": ["death_ray_damage_mult"],
        "thorns_resistance:": ["thorns_damage_mult"],
        "plasma_cannon_resistance:": ["plasma_cannon_damage_mult"],
        "knockback_resistance:": ["knockback_mult"],
    }
    bc_values: Dict[str, float] = {}
    heat_magnitudes: Dict[str, float] = {}
    for bc_id in bc_to_stats:
        try:
            value = table.value_at(league=league, wave_actual=wave, bc_id=bc_id).value_num
        except HeatDataError:
            continue
        bc_values[bc_id] = float(value)
        for stat_id in bc_to_stats[bc_id]:
            registry.validate_stat_id(stat_id)
            heat_magnitudes[stat_id] = float(value)

    row["battle_conditions"] = bc_values
    row["heat_magnitudes"] = heat_magnitudes
    return row, []


def _validate_boss_survivability_inputs(
    problem_spec: ProblemSpec,
) -> Tuple[List[str], Dict[str, Any]]:
    missing: List[str] = []
    diagnostics: Dict[str, Any] = {}
    spec = problem_spec.scenario.boss_survivability
    if spec is None:
        missing.append("boss_survivability_inputs")
        return missing, diagnostics
    hit_interval_id = spec.combat_params.get("hit_interval_id", "default")
    try:
        boss_hit_interval_seconds(str(hit_interval_id))
    except BossHitIntervalError as exc:
        missing.append("boss_hit_interval")
        diagnostics["boss_hit_interval_error"] = str(exc)
    return missing, diagnostics


def snapshot_at_wave(
    wave: int,
    *,
    base_engine_result,
    registry,
    stat_inputs: List,
    scenario,
    tier_rules,
    run_context: RunContext,
    tables: Dict[str, Any],
    ids_snapshot: AccountSnapshot,
    wave_row: Dict[str, Any],
) -> AtWaveSnapshot:
    wave_state = _wave_state_from_row(wave_row)
    workshop_at_wave, workshop_missing = compile_workshop_values_at_wave(
        ids_snapshot,
        wave=wave,
    )
    if workshop_missing:
        raise StatSnapshotError(
            "Missing workshop progression inputs: " + ", ".join(sorted(set(workshop_missing)))
        )

    return build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=base_engine_result,
        registry=registry,
        tier_rules=tier_rules,
        battle_conditions=None,
        wave_state=wave_state,
        wave=wave,
        run_context=run_context,
        heat_magnitudes=tables.get("heat_magnitudes"),
        per_wave_overrides=workshop_at_wave,
    )


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

        wave_row, wave_row_missing = _build_wave_row(problem_spec, registry, wave=wave)
        if wave_row_missing or wave_row is None:
            return None, None, wave_row_missing

        stat_inputs_at_wave, perk_diag = _stat_inputs_for_wave(
            registry=registry,
            stat_inputs=stat_inputs,
            scenario=scenario,
            wave=wave,
        )
        diagnostics.setdefault("perk_timeline", {})[str(wave)] = perk_diag

        try:
            wave_snapshot = snapshot_at_wave(
                wave,
                base_engine_result=engine_result,
                registry=registry,
                stat_inputs=stat_inputs_at_wave,
                scenario=scenario,
                tier_rules=tier_rules,
                run_context=run_context,
                tables={"heat_magnitudes": wave_row.get("heat_magnitudes")},
                wave_row=wave_row,
                ids_snapshot=ids_snapshot,
            )
        except StatSnapshotError as exc:
            diagnostics["wave_snapshot_error"] = str(exc)
            return None, None, ["wave_snapshot"]

        survivability_stats, survivability_missing = _resolve_survivability_stats(
            engine_result, wave_snapshot
        )
        if survivability_missing:
            return None, None, survivability_missing

        wave_damage, wave_damage_missing = _resolve_wave_damage_for_wave(
            problem_spec, wave_row
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


def _resolve_survivability_stats(
    engine_result,
    wave_snapshot: Optional[AtWaveSnapshot],
) -> Tuple[Optional[Dict[str, float]], List[str]]:
    if engine_result is None:
        return None, ["stat_engine"]
    start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
    if start_stats is None:
        return None, ["start_stats"]
    snapshot_values = wave_snapshot.values if wave_snapshot is not None else {}
    required = ["tower_hp", "tower_regen", "def_pct", "wall_hp", "wall_regen", "thorns_damage_mult"]
    values: Dict[str, float] = {}
    missing = []
    for stat_id in required:
        value = snapshot_values.get(stat_id, start_stats.values.get(stat_id))
        if value is None:
            missing.append(stat_id)
            continue
        values[stat_id] = float(value)
    if missing:
        return None, [f"stat:{stat_id}" for stat_id in missing]
    return values, []



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

def _resolve_wave_state_for_wave(
    scenario,
    wave: int,
) -> Tuple[Optional[Any], List[str]]:
    missing: List[str] = []
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if missing:
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
    return make_wave_state(wave, eals, ehls), []




def _wave_state_from_row(wave_row: Dict[str, Any]) -> RunWaveState:
    if "wave" not in wave_row or "enemy_attack_wave" not in wave_row or "enemy_health_wave" not in wave_row:
        raise StatSnapshotError("Wave row missing required keys: wave/enemy_attack_wave/enemy_health_wave")
    return RunWaveState(
        W_actual=int(wave_row["wave"]),
        W_attack=int(wave_row["enemy_attack_wave"]),
        W_health=int(wave_row["enemy_health_wave"]),
    )
def _resolve_wave_damage_for_wave(
    problem_spec: ProblemSpec,
    wave_row: Dict[str, Any] | RunWaveState,
) -> Tuple[Optional[float], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = _default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None, missing
    lib = EnemyWaveDamageLib.from_repo_tables()
    if isinstance(wave_row, RunWaveState):
        wave = int(wave_row.W_attack)
    else:
        wave = int(wave_row["enemy_attack_wave"])
    try:
        damage = lib.wave_damage(wave_tier, wave)
    except KeyError:
        missing.append("wave_damage_table")
        return None, missing
    return damage, []
