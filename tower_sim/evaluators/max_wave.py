from __future__ import annotations

from dataclasses import asdict
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
from tower_sim.loaders.bc_heat_loader import HeatDataError, load_heat_bundle
from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.run.context import RunContext
from tower_sim.engines.stat_engine import StatEngine
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.engines.tier_rule_apply import SUPPORTED_BC
from tower_sim.engines.tier_rules import build_tier_rules
from tower_sim.engines.wave_engine import SkipRamp, make_wave_state


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

        stat_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
        missing_stat_inputs = _missing_required_stat_inputs(stat_inputs)
        if missing_stat_inputs:
            diagnostics["missing_stat_inputs"] = missing_stat_inputs
            missing.extend(missing_stat_inputs)

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

        missing = sorted(set(missing))
        if missing:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": missing,
                "w_max": None,
                "diagnostics": diagnostics,
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
        wave_snapshot = _resolve_wave_snapshot(
            problem_spec,
            stat_inputs,
            engine_result_base,
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

        survivability_stats, survivability_missing = _resolve_survivability_stats(
            engine_result_base, wave_snapshot
        )
        if survivability_missing:
            diagnostics["missing_survivability_stats"] = survivability_missing
            missing.extend(survivability_missing)

        missing = sorted(set(missing))
        if missing:
            return {
                "evaluator": problem_spec.evaluator,
                "fail_closed": True,
                "missing": missing,
                "w_max": None,
                "diagnostics": diagnostics,
            }

        w_max, trace, search_diagnostics, search_missing = _search_wmax(
            problem_spec=problem_spec,
            stat_inputs=stat_inputs,
            engine_result=engine_result_base,
            registry=registry,
            tier_rules=tier_rules,
            run_context=run_context,
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
    heat_path = Path(__file__).resolve().parents[2] / "tables" / "heat_wave_scalar.csv"
    magnitudes_path = (
        Path(__file__).resolve().parents[2]
        / "tables"
        / "battle_condition_magnitudes.csv"
    )
    try:
        bundle = load_heat_bundle(heat_path, magnitudes_path)
    except (HeatDataError, FileNotFoundError) as exc:
        missing.append("heat_tables")
        diagnostics["heat_tables_error"] = str(exc)
        return None

    league = scenario.league.lower()
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
) -> AtWaveSnapshot:
    if scenario.eals_ramp is None or scenario.ehls_ramp is None:
        raise StatSnapshotError("Wave ramps are required for random-access snapshots.")
    wave_state = make_wave_state(
        wave,
        SkipRamp(
            start=scenario.eals_ramp.start,
            end=scenario.eals_ramp.end,
            ramp_waves=scenario.eals_ramp.ramp_waves,
        ),
        SkipRamp(
            start=scenario.ehls_ramp.start,
            end=scenario.ehls_ramp.end,
            ramp_waves=scenario.ehls_ramp.ramp_waves,
        ),
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
    )


def _search_wmax(
    *,
    problem_spec: ProblemSpec,
    stat_inputs: List,
    engine_result,
    registry,
    tier_rules,
    run_context: RunContext,
    trace_depth: int = 5,
) -> Tuple[Optional[int], List[Dict[str, Any]], Dict[str, Any], List[str]]:
    scenario = problem_spec.scenario
    missing: List[str] = []
    diagnostics: Dict[str, Any] = {}

    if scenario.boss_survivability is None:
        return None, [], {}, ["boss_survivability_inputs"]
    if engine_result is None:
        return None, [], {}, ["stat_engine"]
    max_wave = int(scenario.wave)
    if max_wave <= 0:
        return None, None, None, None, [], {}, ["wave_limit"]

    cache: Dict[int, Tuple[Dict[str, Any], bool, Dict[str, Any]]] = {}
    history: List[Dict[str, Any]] = []
    failure_wave: Optional[int] = None
    failure_reason: Optional[str] = None
    failure_snapshot: Optional[Dict[str, Any]] = None

    def evaluate_wave(wave: int) -> Tuple[Optional[Dict[str, Any]], Optional[bool], List[str]]:
        nonlocal failure_wave, failure_reason, failure_snapshot
        if wave in cache:
            entry, success, _result = cache[wave]
            return entry, success, []

    cache: Dict[int, Tuple[Dict[str, Any], bool, Dict[str, Any]]] = {}
    history: List[Dict[str, Any]] = []

    def evaluate_wave(wave: int) -> Tuple[Optional[Dict[str, Any]], Optional[bool], List[str]]:
        if wave in cache:
            entry, success, _result = cache[wave]
            return entry, success, []

        wave_state, wave_state_missing = _resolve_wave_state_for_wave(scenario, wave)
        if wave_state_missing:
            return None, None, wave_state_missing

        heat_missing: List[str] = []
        heat_magnitudes = _resolve_heat_magnitudes(
            problem_spec,
            registry,
            wave=wave,
            missing=heat_missing,
            diagnostics=diagnostics,
        )
        if heat_missing:
            return None, None, heat_missing

        try:
            wave_snapshot = snapshot_at_wave(
                wave,
                base_engine_result=engine_result,
                registry=registry,
                stat_inputs=stat_inputs,
                scenario=scenario,
                tier_rules=tier_rules,
                run_context=run_context,
                tables={"heat_magnitudes": heat_magnitudes},
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
            problem_spec, wave_state
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
        return None, [], diagnostics, mono_missing
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
                return None, [], diagnostics, eval_missing
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
                    return None, [], diagnostics, eval_missing
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
                return None, [], diagnostics, eval_missing
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
                    return None, [], diagnostics, inner_missing
                evaluated.add(inner_wave)
                if inner_entry is not None:
                    last_result = cache[inner_wave][2]
                if inner_success:
                    last_success = max(last_success, inner_wave)
        w_max = last_success

    trace = history[-trace_depth:] if history else []
    diagnostics.update(
        {
            "max_wave": max_wave,
            "evaluated_waves": len(evaluated),
            "trace_depth": trace_depth,
            "last_wave_result": last_result,
        }
    )
    return w_max, trace, diagnostics, missing


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


def _resolve_wave_damage_for_wave(
    problem_spec: ProblemSpec,
    wave_state,
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
    wave = wave_state.W_attack
    try:
        damage = lib.wave_damage_exact(wave_tier, wave)
    except KeyError:
        missing.append("wave_damage_table")
        return None, missing
    return damage, []
