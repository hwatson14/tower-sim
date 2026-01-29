from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
        missing.extend(_missing_required_stat_inputs(stat_inputs))

        tier_rules = _load_tier_rules(problem_spec, run_context, missing)
        engine = StatEngine(registry=default_registry())
        try:
            if tier_rules is None:
                engine_result = engine.build(stat_inputs)
            else:
                engine_result = engine.build_with_tier_rules(stat_inputs, tier_rules)
            diagnostics["statbook_rows"] = len(engine_result.statbook.rows)
        except Exception as exc:  # noqa: BLE001
            missing.append("stat_engine")
            diagnostics["stat_engine_error"] = str(exc)
            engine_result = None

        wave_state = _maybe_build_wave_state(problem_spec, missing)
        if wave_state is not None:
            diagnostics["wave_state"] = asdict(wave_state)

        wave_damage = _resolve_wave_damage(problem_spec, wave_state, missing, diagnostics)

        if problem_spec.scenario.boss_survivability is None:
            missing.append("boss_survivability_inputs")
        else:
            diagnostics["boss_survivability"] = _resolve_boss_survivability(
                problem_spec, wave_state
            )

        _probe_boss_combat(
            problem_spec,
            engine_result,
            wave_damage,
            missing,
            diagnostics,
        )

        missing = sorted(set(missing))
        return {
            "evaluator": problem_spec.evaluator,
            "fail_closed": bool(missing),
            "missing": missing,
            "w_max": None,
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
    missing: List[str],
):
    bc_path = _resolve_bc_path(problem_spec)
    try:
        catalog = load_tier_battle_conditions(bc_path, allow_incomplete=True)
    except FileNotFoundError:
        missing.append("tier_battle_conditions_table")
        return None
    try:
        rules = build_tier_rules(problem_spec.scenario.tier, run_context, catalog)
    except ValueError:
        missing.append("tier_battle_conditions")
        return None
    unsupported = [
        condition
        for condition in rules.conditions
        if (condition.name, condition.kind, condition.unit) not in SUPPORTED_BC
    ]
    if unsupported:
        missing.append("tier_battle_conditions_unsupported")
        return None
    return rules


def _resolve_bc_path(problem_spec: ProblemSpec) -> Path:
    return Path(__file__).resolve().parents[1] / "tables" / "tier14_21_battle_conditions.csv"


def _maybe_build_wave_state(problem_spec: ProblemSpec, missing: List[str]):
    scenario = problem_spec.scenario
    if scenario.eals_ramp is None:
        missing.append("skip_ramp:eals")
    if scenario.ehls_ramp is None:
        missing.append("skip_ramp:ehls")
    if scenario.eals_ramp is None or scenario.ehls_ramp is None:
        return None
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
    return make_wave_state(scenario.wave, eals, ehls)


def _resolve_wave_damage(
    problem_spec: ProblemSpec,
    wave_state,
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> Optional[float]:
    scenario = problem_spec.scenario
    wave_tier = scenario.wave_damage_tier
    if wave_tier is None:
        wave_tier = _default_wave_damage_tier(scenario)
    if wave_tier is None:
        missing.append("wave_damage_tier")
        return None

    lib = EnemyWaveDamageLib.from_pasted_default()
    wave = scenario.wave if wave_state is None else wave_state.W_attack
    try:
        damage = lib.wave_damage_exact(wave_tier, wave)
    except KeyError as exc:
        missing.append("wave_damage_table")
        diagnostics["wave_damage_error"] = str(exc)
        return None
    diagnostics["wave_damage_tier"] = wave_tier
    diagnostics["wave_damage_wave"] = wave
    diagnostics["wave_damage"] = damage
    return damage


def _default_wave_damage_tier(scenario) -> Optional[str]:
    if scenario.mode == "farming":
        return f"Tier {scenario.tier}"
    if scenario.league:
        return scenario.league
    return None


def _resolve_boss_survivability(problem_spec: ProblemSpec, wave_state) -> Dict[str, Any]:
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
            wave=problem_spec.scenario.wave,
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
    missing: List[str],
    diagnostics: Dict[str, Any],
) -> None:
    if engine_result is None or wave_damage is None:
        missing.append("boss_combat_inputs")
        return
    try:
        start_stats = engine_result.run_stats.get(Phase.START_OF_RUN)
        if start_stats is None:
            missing.append("boss_combat_inputs")
            return
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
        message = str(exc)
        if "Missing required boss combat inputs" in message:
            missing.append("boss_combat_inputs")
        else:
            missing.append("boss_combat_mechanics")
        diagnostics["boss_combat_error"] = message
