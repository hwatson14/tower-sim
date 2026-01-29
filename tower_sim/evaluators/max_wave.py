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
from tower_sim.ids_state import IdsState
from tower_sim.problem_spec import ProblemSpec
from tower_sim.run_context import RunContext
from tower_sim.stat_engine import StatEngine
from tower_sim.stat_registry import Phase, default_registry
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
        engine = StatEngine(registry=default_registry())
        try:
            if tier_rules is None:
                engine_result = engine.build(stat_inputs)
            else:
                engine_result = engine.build_with_tier_rules(stat_inputs, tier_rules)
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

    lib = EnemyWaveDamageLib.from_pasted_default()
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
    wave_damage: Optional[float],
) -> Optional[str]:
    if engine_result is None or wave_damage is None:
        return "boss_combat_inputs"
    try:
        start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
        if start_stats is None:
            return "boss_combat_inputs"
        inputs = BossCombatInputs(
            wave=problem_spec.scenario.wave,
            wave_damage=wave_damage,
            tower_hp=start_stats.values.get("tower_hp", 0.0),
            tower_regen=start_stats.values.get("tower_regen", 0.0),
            defense_pct=start_stats.values.get("def_pct", 0.0),
            thorns_pct=start_stats.values.get("thorns_damage_mult"),
            package_chance=None,
            package_heal=None,
            damage_reduction=None,
            provenance="problem_spec",
        )
        BossCombatEngine().evaluate(inputs)
    except MissingMechanicError as exc:
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
