from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from math import isfinite
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tower_sim.combat.boss_engine import BossCombatEngine, BossCombatInputs, MissingMechanicError
from tower_sim.combat.boss_survivability import (
    BossContext,
    BossDataError,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)
from tower_sim.enemies.wave_damage_strict import EnemyWaveDamageLib
from tower_sim.bc_heat_loader import HeatDataError, load_heat_bundle
from tower_sim.ids_state import IdsState
from tower_sim.problem_spec import ProblemSpec
from tower_sim.run_context import RunContext
from tower_sim.stat_engine import StatEngine
from tower_sim.stat_registry import Phase, default_registry
from tower_sim.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
from tower_sim.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.tier_rule_apply import SUPPORTED_BC
from tower_sim.tier_rules import build_tier_rules
from tower_sim.wave_engine import SkipRamp, make_wave_state


class MaxWaveEvaluator:
    def __init__(self, bc_table_path: Optional[Path] = None) -> None:
        self._bc_table_path = bc_table_path

    def evaluate(
        self,
        problem_spec: ProblemSpec,
        ids_state: IdsState,
    ) -> Dict[str, Any]:
        missing: List[str] = []
        diagnostics: Dict[str, Any] = {}

        run_context = RunContext.from_mode(
            problem_spec.scenario.mode,
            tier=str(problem_spec.scenario.tier),
        )

        stat_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
        missing_stat_inputs = _missing_required_stat_inputs(stat_inputs)
        if missing_stat_inputs:
            diagnostics["missing_stat_inputs"] = missing_stat_inputs

        tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
        if tier_rule_missing:
            diagnostics["missing_tier_rules"] = tier_rule_missing
        wave_state = _maybe_build_wave_state(problem_spec, missing)
        if wave_state is not None:
            diagnostics["wave_state"] = asdict(wave_state)

        registry = default_registry()
        tier_rules = _load_tier_rules(problem_spec, run_context, missing)
        engine = StatEngine(registry=registry)
        try:
            if tier_rules is None:
                engine_result = engine.build(stat_inputs, wave_state=wave_state)
            else:
                engine_result = engine.build_with_tier_rules(
                    stat_inputs, tier_rules, wave_state=wave_state
                )
            diagnostics["statbook_rows"] = len(engine_result.statbook.rows)
        except Exception as exc:  # noqa: BLE001
            diagnostics["stat_engine_error"] = str(exc)
            engine_result = None

        wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
        if wave_state is not None:
            diagnostics["wave_state"] = asdict(wave_state)
        if wave_state_missing:
            diagnostics["missing_wave_state"] = wave_state_missing

        wave_damage, wave_damage_missing = _resolve_wave_damage(
            problem_spec, wave_state, diagnostics
        )
        if wave_damage_missing:
            diagnostics["missing_wave_damage"] = wave_damage_missing
        wave_damage = _resolve_wave_damage(problem_spec, wave_state, missing, diagnostics)
        wave_snapshot = _resolve_wave_snapshot(
            problem_spec,
            stat_inputs,
            engine_result,
            registry,
            tier_rules,
            run_context,
            wave_state,
            missing,
            diagnostics,
        )
        if wave_snapshot is not None:
            diagnostics["at_wave_snapshot"] = {
                "wave": wave_snapshot.wave,
                "applied_bc": wave_snapshot.applied_bc,
                "applied_heat": wave_snapshot.applied_heat,
            }

        w_max, trace, search_diagnostics, search_missing = _search_wmax(problem_spec)
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
            engine_result,
            wave_snapshot,
            wave_damage,
        )
        if boss_combat_error is not None:
            diagnostics["boss_combat_error"] = boss_combat_error

        missing = sorted(set(missing))
        return {
            "evaluator": problem_spec.evaluator,
            "fail_closed": bool(missing),
            "missing": missing,
            "w_max": w_max if not missing else None,
            "diagnostics": diagnostics,
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
        "def_pct",
    }
    present = {stat_input.stat_id for stat_input in stat_inputs}
    return [f"stat_input:{stat_id}" for stat_id in sorted(required - present)]


def _load_tier_rules(
    problem_spec: ProblemSpec,
    run_context: RunContext,
) -> Tuple[Optional[Any], List[str]]:
    missing: List[str] = []
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
    return Path(__file__).resolve().parents[1] / "tables" / "tier14_21_battle_conditions.csv"


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
        damage = lib.wave_damage_exact(wave_tier, wave)
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


def _resolve_boss_survivability(problem_spec: ProblemSpec, wave: int) -> Dict[str, Any]:
    spec = problem_spec.scenario.boss_survivability
    if spec is None:
        return {}
    try:
        boss = BossStats(
            hp=spec.boss.hp,
            attack=spec.boss.attack,
            attack_interval=spec.boss.attack_interval,
            enrage_mult=spec.boss.enrage_mult,
        )
        tower = TowerDefense(
            dr_frac=spec.tower.dr_frac,
            regen_per_sec=spec.tower.regen_per_sec,
            shields=spec.tower.shields,
        )
        ctx = BossContext(
            wave=wave,
            tier=problem_spec.scenario.tier,
            league=problem_spec.scenario.league or "",
            boss=boss,
            tower=tower,
            combat_params=spec.combat_params,
            bc_params=spec.bc_params,
        )
        return resolve_boss_fight(ctx)
    except BossDataError as exc:
        return {"error": str(exc)}


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
            missing.append("boss_combat_inputs")
            return
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
            return "boss_combat_inputs"
        inputs = BossCombatInputs(
            wave=problem_spec.scenario.wave,
            wave_damage=wave_damage,
            tower_hp=start_stats.values.get("tower_hp", 0.0),
            tower_regen=start_stats.values.get("tower_regen", 0.0),
            defense_pct=start_stats.values.get("def_pct", 0.0),
            thorns_pct=start_stats.values.get("thorns_damage_mult"),
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
            missing.append("boss_combat_inputs")
        else:
            missing.append("boss_combat_mechanics")
        diagnostics["boss_combat_error"] = message


def _resolve_wave_snapshot(
    problem_spec: ProblemSpec,
    stat_inputs: List,
    engine_result,
    registry,
    tier_rules,
    run_context: RunContext,
    wave_state,
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> Optional[AtWaveSnapshot]:
    if engine_result is None:
        missing.append("wave_snapshot_inputs")
        return None
    heat_magnitudes = _resolve_heat_magnitudes(
        problem_spec,
        registry,
        missing,
        diagnostics,
    )
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
        )
    except StatSnapshotError as exc:
        missing.append("wave_snapshot")
        diagnostics["wave_snapshot_error"] = str(exc)
        return None


def _resolve_heat_magnitudes(
    problem_spec: ProblemSpec,
    registry,
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    scenario = problem_spec.scenario
    if scenario.mode != "tournament":
        return None
    if scenario.league is None:
        missing.append("heat_league")
        return None
    heat_path = Path(__file__).resolve().parents[1] / "tables" / "heat_wave_scalar.csv"
    magnitudes_path = (
        Path(__file__).resolve().parents[1] / "tables" / "battle_condition_magnitudes.csv"
    )
    try:
        bundle = load_heat_bundle(heat_path, magnitudes_path)
    except (HeatDataError, FileNotFoundError) as exc:
        missing.append("heat_tables")
        diagnostics["heat_tables_error"] = str(exc)
        return None

    league = scenario.league.lower()
    wave = scenario.wave
    scalars = [row for row in bundle.heat_scalars if row.league == league and row.wave == wave]
    if not scalars:
        missing.append("heat_scalar")
        return None
    if any(row.scalar != 1.0 for row in scalars):
        missing.append("heat_scalar_mapping")
        diagnostics["heat_scalar_error"] = (
            "Heat scalar mapping to BC magnitudes is not implemented."
        )
        return None

    magnitudes = [
        row
        for row in bundle.magnitudes
        if row.league == league and row.wave == wave
    ]
    if not magnitudes:
        missing.append("bc_magnitudes")
        return None

    mapped: Dict[str, float] = {}
    unmapped: List[str] = []
    for row in magnitudes:
        if row.bc_id in mapped:
            missing.append("bc_magnitudes_duplicate")
            diagnostics["bc_magnitudes_error"] = f"Duplicate bc_id: {row.bc_id}"
            return None
        try:
            registry.validate_stat_id(row.bc_id)
        except Exception:  # noqa: BLE001
            unmapped.append(row.bc_id)
            continue
        mapped[row.bc_id] = row.magnitude

    if unmapped:
        missing.append("bc_magnitudes_unmapped")
        diagnostics["bc_magnitudes_unmapped"] = sorted(unmapped)
        return None
    return mapped
        return str(exc)
    return None


def _search_wmax(
    problem_spec: ProblemSpec,
    trace_depth: int = 5,
) -> Tuple[Optional[int], List[Dict[str, Any]], Dict[str, Any], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    if scenario.boss_survivability is None:
        return None, [], {}, ["boss_survivability_inputs"]
    max_wave = int(scenario.wave)
    if max_wave <= 0:
        return None, [], {}, ["wave_limit"]

    results: List[Dict[str, Any]] = []
    w_max = 0
    last_result: Dict[str, Any] = {}
    for wave in range(1, max_wave + 1):
        result = _resolve_boss_survivability(problem_spec, wave)
        if "error" in result:
            missing.append("boss_survivability_params")
            diagnostics = {"error": result["error"]}
            return None, [], diagnostics, missing
        margin = _margin_from_outcome(result)
        outcome = result.get("outcome", "unknown")
        entry = {
            "wave": wave,
            "outcome": outcome,
            "ttk_seconds": result.get("ttk_seconds"),
            "ttd_seconds": result.get("ttd_seconds"),
            "margin_seconds": margin,
        }
        results.append(entry)
        last_result = result
        if outcome == "tower_kills_boss":
            w_max = wave

    trace = results[-trace_depth:] if results else []
    diagnostics = {
        "max_wave": max_wave,
        "evaluated_waves": max_wave,
        "trace_depth": trace_depth,
        "last_wave_result": last_result,
    }
    return w_max, trace, diagnostics, missing


def _margin_from_outcome(result: Dict[str, Any]) -> Optional[float]:
    ttk = result.get("ttk_seconds")
    ttd = result.get("ttd_seconds")
    if ttk is None or ttd is None:
        return None
    if not (isfinite(ttk) or isfinite(ttd)):
        return None
    return ttd - ttk
