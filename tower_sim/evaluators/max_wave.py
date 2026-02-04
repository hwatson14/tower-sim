from __future__ import annotations

from collections import deque
from pathlib import Path
from math import isfinite
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional, Tuple

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
from tower_sim.util.ids_state import IdsState
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.run.context import RunContext
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.engines.stat_snapshots import AtWaveSnapshot, StatSnapshotError, build_at_wave_snapshot
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions
from tower_sim.engines.tier_rule_apply import SUPPORTED_BC
from tower_sim.engines.tier_rules import build_tier_rules
from tower_sim.engines.wave_engine import SkipRamp, make_wave_state
from tower_sim.engines.survivability_pipeline import (
    SurvivabilityPipelineError,
    _build_inventory_summary,
    _compile_base_stat_inputs,
    _compile_loadout_stat_inputs,
    _merge_stat_inputs,
)


class MaxWaveEvaluator:
    def __init__(self, bc_table_path: Optional[Path] = None) -> None:
        self._bc_table_path = bc_table_path

    def evaluate(
        self,
        problem_spec: ProblemSpec,
        ids_state: IdsState,
    ) -> Dict[str, Any]:
        missing: List[str] = []

        run_context = RunContext.from_mode(
            problem_spec.scenario.mode,
            tier=str(problem_spec.scenario.tier),
        )

        stat_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
        missing.extend(_missing_required_stat_inputs(stat_inputs))

        wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
        missing.extend(wave_state_missing)

        tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
        missing.extend(tier_rule_missing)

        registry = default_registry()
        engine = StatEngine(registry=registry)
        try:
            if tier_rules is None:
                engine_result = engine.build(stat_inputs, wave_state=wave_state)
            else:
                engine_result = engine.build_with_tier_rules(
                    stat_inputs, tier_rules, wave_state=wave_state
                )
        except Exception:  # noqa: BLE001
            engine_result = None
            missing.append("stat_engine")

        wave_snapshot, snapshot_missing = _resolve_wave_snapshot(
            problem_spec,
            stat_inputs,
            engine_result,
            registry,
            tier_rules,
            run_context,
            wave_state,
        )
        missing.extend(snapshot_missing)

        survivability_stats, survivability_missing = _resolve_survivability_stats(
            engine_result, wave_snapshot
        )
        missing.extend(survivability_missing)

        (
            w_max,
            failure_wave,
            failure_reason,
            failure_snapshot,
            _trace,
            search_missing,
        ) = _search_wmax(problem_spec, survivability_stats, trace_depth=0)
        missing.extend(search_missing)

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
    return Path(__file__).resolve().parents[2] / "tables" / "tier14_21_battle_conditions.csv"


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
    except KeyError:
        missing.append("wave_damage_table")
        return None, missing
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
) -> Tuple[Optional[AtWaveSnapshot], List[str]]:
    missing: List[str] = []
    if engine_result is None:
        missing.append("wave_snapshot_inputs")
        return None, missing
    heat_magnitudes, heat_missing = _resolve_heat_magnitudes(problem_spec, registry)
    missing.extend(heat_missing)
    try:
        snapshot = build_at_wave_snapshot(
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
        return snapshot, missing
    except StatSnapshotError:
        missing.append("wave_snapshot")
        return None, missing
    return None, missing


def _resolve_heat_magnitudes(
    problem_spec: ProblemSpec,
    registry,
) -> Tuple[Optional[Dict[str, float]], List[str]]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    if scenario.mode != "tournament":
        return None, missing
    if scenario.league is None:
        missing.append("heat_league")
        return None, missing
    heat_path = Path(__file__).resolve().parents[2] / "tables" / "heat_wave_scalar.csv"
    magnitudes_path = (
        Path(__file__).resolve().parents[2]
        / "tables"
        / "battle_condition_magnitudes.csv"
    )
    try:
        bundle = load_heat_bundle(heat_path, magnitudes_path)
    except (HeatDataError, FileNotFoundError):
        missing.append("heat_tables")
        return None, missing

    league = scenario.league.lower()
    wave = scenario.wave
    scalars = [row for row in bundle.heat_scalars if row.league == league and row.wave == wave]
    if not scalars:
        missing.append("heat_scalar")
        return None, missing
    if any(row.scalar != 1.0 for row in scalars):
        missing.append("heat_scalar_mapping")
        return None, missing

    magnitudes = [
        row
        for row in bundle.magnitudes
        if row.league == league and row.wave == wave
    ]
    if not magnitudes:
        missing.append("bc_magnitudes")
        return None, missing

    mapped: Dict[str, float] = {}
    unmapped: List[str] = []
    for row in magnitudes:
        if row.bc_id in mapped:
            missing.append("bc_magnitudes_duplicate")
            return None, missing
        try:
            registry.validate_stat_id(row.bc_id)
        except Exception:  # noqa: BLE001
            unmapped.append(row.bc_id)
            continue
        mapped[row.bc_id] = row.magnitude

    if unmapped:
        missing.append("bc_magnitudes_unmapped")
        return None, missing
    return mapped, missing


def _search_wmax(
    problem_spec: ProblemSpec,
    survivability_stats: Optional[Dict[str, float]],
    trace_depth: int = 0,
) -> Tuple[
    Optional[int],
    Optional[int],
    Optional[str],
    Optional[Dict[str, Any]],
    List[Dict[str, Any]],
    List[str],
]:
    missing: List[str] = []
    scenario = problem_spec.scenario
    if scenario.boss_survivability is None:
        return None, None, None, None, [], ["boss_survivability_inputs"]
    if survivability_stats is None:
        return None, None, None, None, [], ["boss_survivability_stats"]
    max_wave = int(scenario.wave)
    if max_wave <= 0:
        return None, None, None, None, [], ["wave_limit"]

    results: Deque[Dict[str, Any]] = deque(maxlen=max(trace_depth, 0))
    w_max = 0
    failure_wave: Optional[int] = None
    failure_reason: Optional[str] = None
    failure_snapshot: Optional[Dict[str, Any]] = None
    for wave in range(1, max_wave + 1):
        wave_state, wave_state_missing = _resolve_wave_state_for_wave(scenario, wave)
        if wave_state_missing:
            missing.extend(wave_state_missing)
            return None, None, None, None, [], missing
        wave_damage, wave_damage_missing = _resolve_wave_damage_for_wave(
            problem_spec, wave_state
        )
        if wave_damage_missing:
            missing.extend(wave_damage_missing)
            return None, None, None, None, [], missing
        result = _resolve_boss_survivability(
            problem_spec, wave, wave_damage, survivability_stats
        )
        if "error" in result:
            missing.append("boss_survivability_params")
            return None, None, None, None, [], missing
        margin = _margin_from_outcome(result)
        outcome = result.get("outcome", "unknown")
        if trace_depth > 0:
            entry = {
                "wave": wave,
                "outcome": outcome,
                "ttk_seconds": result.get("ttk_seconds"),
                "ttd_seconds": result.get("ttd_seconds"),
                "margin_seconds": margin,
            }
            results.append(entry)
        if outcome == "tower_kills_boss":
            w_max = wave
        elif failure_wave is None:
            failure_wave = wave
            failure_reason = outcome
            failure_snapshot = _build_failure_snapshot(
                problem_spec,
                survivability_stats,
                wave,
                wave_damage,
                result,
            )
    return (
        w_max,
        failure_wave,
        failure_reason,
        failure_snapshot,
        list(results),
        missing,
    )


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


def build_max_wave_report(
    problem_spec: ProblemSpec,
    ids_state: IdsState,
    max_wave_result: Dict[str, Any],
    *,
    module_context: str = "Testing",
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None = None,
    selected_cards: Iterable[str] | None = None,
    allow_provisional: bool = False,
    include_trace: bool = False,
    trace_depth: int = 20,
) -> Dict[str, Any]:
    missing: List[str] = []
    errors: List[Dict[str, str]] = []

    report: Dict[str, Any] = {
        "report_version": 1,
        "fail_closed": False,
        "missing": [],
        "errors": [],
        "max_wave_result": {
            "w_max": max_wave_result.get("w_max"),
            "failure_wave": max_wave_result.get("failure_wave"),
            "failure_reason": max_wave_result.get("failure_reason"),
        },
    }

    report["base_state"] = _extract_base_state(ids_state)

    inventory = _safe_build_inventory(
        ids_state,
        module_context=module_context,
        module_overrides=module_overrides,
        missing=missing,
        errors=errors,
    )
    if inventory is not None:
        report["inventory"] = inventory

    loadout_breakdown = _safe_build_loadout_breakdown(
        ids_state,
        module_context=module_context,
        module_overrides=module_overrides,
        selected_cards=selected_cards,
        allow_provisional=allow_provisional,
        missing=missing,
        errors=errors,
    )
    if loadout_breakdown is not None:
        report["loadout_compilation"] = loadout_breakdown

    wave_mapping = _build_wave_mapping_report(
        problem_spec,
        max_wave_result,
        missing=missing,
        errors=errors,
    )
    if wave_mapping is not None:
        report["wave_mapping"] = wave_mapping

    if include_trace:
        trace = _safe_build_trace(
            problem_spec,
            trace_depth=trace_depth,
            missing=missing,
            errors=errors,
        )
        if trace is not None:
            report["trace"] = trace

    missing = sorted(set(missing))
    report["missing"] = missing
    report["errors"] = errors
    report["fail_closed"] = bool(missing)
    return report


def _extract_base_state(ids_state: IdsState) -> Dict[str, Any]:
    workshop_entries = {}
    for name, entry in ids_state.workshop.entries.items():
        workshop_entries[name] = {
            "unlocked": entry.unlocked,
            "coin_level": entry.coin_level,
            "max_level": entry.max_level,
            "category": entry.category,
        }
    ultimate_weapons = {}
    for name, entry in ids_state.ultimate_weapons.entries.items():
        ultimate_weapons[name] = {
            "unlocked": entry.unlocked,
            "track_levels": entry.track_levels,
        }
    return {
        "labs": dict(ids_state.labs.labs),
        "workshop": workshop_entries,
        "relics": dict(ids_state.relics.relics),
        "ultimate_weapons": ultimate_weapons,
    }


def _safe_build_inventory(
    ids_state: IdsState,
    *,
    module_context: str,
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    try:
        return _build_inventory_summary(ids_state, module_context, module_overrides)
    except SurvivabilityPipelineError as exc:
        _record_report_error("inventory", exc, missing, errors)
        return None


def _safe_build_loadout_breakdown(
    ids_state: IdsState,
    *,
    module_context: str,
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None,
    selected_cards: Iterable[str] | None,
    allow_provisional: bool,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    try:
        base_inputs = _compile_base_stat_inputs(
            ids_state, allow_provisional=allow_provisional
        )
        loadout_inputs = _compile_loadout_stat_inputs(
            ids_state,
            module_context=module_context,
            module_overrides=module_overrides,
            selected_cards=selected_cards,
            allow_provisional=allow_provisional,
        )
    except (SurvivabilityPipelineError, FileNotFoundError, ValueError, KeyError) as exc:
        _record_report_error("loadout_compilation", exc, missing, errors)
        return None

    stat_inputs = _merge_stat_inputs(base_inputs, loadout_inputs)
    registry = default_registry()
    engine = StatEngine(registry=registry)
    try:
        engine_result = engine.build(stat_inputs)
    except Exception as exc:  # noqa: BLE001
        _record_report_error("stat_engine", exc, missing, errors)
        return None

    return {
        "base_stat_inputs": [_serialize_stat_input(row) for row in base_inputs],
        "loadout_stat_inputs": [_serialize_stat_input(row) for row in loadout_inputs],
        "statbook_rows": [_serialize_statbook_row(row) for row in engine_result.statbook.rows],
    }


def _build_wave_mapping_report(
    problem_spec: ProblemSpec,
    max_wave_result: Dict[str, Any],
    *,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    scenario = problem_spec.scenario
    waves = {scenario.wave}
    failure_wave = max_wave_result.get("failure_wave")
    if isinstance(failure_wave, int):
        waves.add(failure_wave)
    wave_details = []
    for wave in sorted(waves):
        wave_state, wave_state_missing = _resolve_wave_state_for_wave(scenario, wave)
        if wave_state_missing:
            for item in wave_state_missing:
                _record_report_error(item, ValueError("Missing wave state inputs."), missing, errors)
            continue
        wave_damage, wave_damage_missing = _resolve_wave_damage_for_wave(
            problem_spec, wave_state
        )
        if wave_damage_missing:
            for item in wave_damage_missing:
                _record_report_error(item, ValueError("Missing wave damage table."), missing, errors)
            continue
        wave_details.append(
            {
                "wave": wave,
                "wave_state": {
                    "W_actual": wave_state.W_actual,
                    "W_attack": wave_state.W_attack,
                    "W_health": wave_state.W_health,
                },
                "wave_damage_tier": scenario.wave_damage_tier
                or _default_wave_damage_tier(scenario),
                "wave_damage": wave_damage,
            }
        )
    return {
        "ramps": {
            "eals": _serialize_ramp(scenario.eals_ramp),
            "ehls": _serialize_ramp(scenario.ehls_ramp),
        },
        "waves": wave_details,
    }


def _safe_build_trace(
    problem_spec: ProblemSpec,
    *,
    trace_depth: int,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[List[Dict[str, Any]]]:
    survivability_stats, stats_missing = _resolve_survivability_stats_for_report(problem_spec)
    if stats_missing:
        for item in stats_missing:
            _record_report_error(item, ValueError("Missing survivability stats."), missing, errors)
        return None
    (
        _w_max,
        _failure_wave,
        _failure_reason,
        _failure_snapshot,
        trace,
        search_missing,
    ) = _search_wmax(problem_spec, survivability_stats, trace_depth=trace_depth)
    if search_missing:
        for item in search_missing:
            _record_report_error(item, ValueError("Missing search inputs."), missing, errors)
        return None
    return trace


def _resolve_survivability_stats_for_report(
    problem_spec: ProblemSpec,
) -> Tuple[Optional[Dict[str, float]], List[str]]:
    missing: List[str] = []
    run_context = RunContext.from_mode(
        problem_spec.scenario.mode,
        tier=str(problem_spec.scenario.tier),
    )
    stat_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
    missing.extend(_missing_required_stat_inputs(stat_inputs))

    wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
    missing.extend(wave_state_missing)

    tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
    missing.extend(tier_rule_missing)

    registry = default_registry()
    engine = StatEngine(registry=registry)
    try:
        if tier_rules is None:
            engine_result = engine.build(stat_inputs, wave_state=wave_state)
        else:
            engine_result = engine.build_with_tier_rules(
                stat_inputs, tier_rules, wave_state=wave_state
            )
    except Exception:  # noqa: BLE001
        missing.append("stat_engine")
        return None, missing

    wave_snapshot, snapshot_missing = _resolve_wave_snapshot(
        problem_spec,
        stat_inputs,
        engine_result,
        registry,
        tier_rules,
        run_context,
        wave_state,
    )
    missing.extend(snapshot_missing)

    survivability_stats, survivability_missing = _resolve_survivability_stats(
        engine_result, wave_snapshot
    )
    missing.extend(survivability_missing)

    if missing:
        return None, missing
    return survivability_stats, []


def _serialize_stat_input(stat_input: StatInput) -> Dict[str, Any]:
    return {
        "stat_id": stat_input.stat_id,
        "phase": stat_input.phase.value,
        "base_value": stat_input.base_value,
        "loadout_delta": stat_input.loadout_delta,
        "enhancement_multiplier": stat_input.enhancement_multiplier,
        "tier_rule_delta": stat_input.tier_rule_delta,
        "tier_rule_multiplier": stat_input.tier_rule_multiplier,
        "derived_value": stat_input.derived_value,
        "provenance": stat_input.provenance,
    }


def _serialize_statbook_row(row) -> Dict[str, Any]:
    return {
        "stat_id": row.stat_id,
        "phase": row.phase,
        "base_value": row.base_value,
        "loadout_delta": row.loadout_delta,
        "enhancement_multiplier": row.enhancement_multiplier,
        "tier_rule_delta_or_multiplier": row.tier_rule_delta_or_multiplier,
        "final_value": row.final_value,
        "provenance": row.provenance,
    }


def _serialize_ramp(ramp) -> Optional[Dict[str, float]]:
    if ramp is None:
        return None
    return {
        "start": ramp.start,
        "end": ramp.end,
        "ramp_waves": ramp.ramp_waves,
    }


def _record_report_error(
    identifier: str,
    exc: Exception,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> None:
    resolved_id = _missing_identifier_from_exception(exc) or identifier
    missing.append(resolved_id)
    errors.append({"id": resolved_id, "error": str(exc)})


def _missing_identifier_from_exception(exc: Exception) -> Optional[str]:
    message = str(exc)
    if message.startswith("Missing data file "):
        rest = message.split("Missing data file ", 1)[1]
        filename = rest.split(". Tried:", 1)[0].strip()
        return f"data_file:{filename}"
    if message.startswith("Missing labs values table"):
        return "labs_values_table"
    if message.startswith("Missing wave damage table"):
        return "wave_damage_table"
    if "Missing Modules section in IDS" in message:
        return "ids_section:Modules"
    if "Missing workshop level" in message:
        return "ids:workshop"
    if "Missing lab level" in message:
        return "ids:labs"
    if "Missing lab table" in message:
        return "labs_values_table"
    if "vault_stats_v1.csv" in message:
        return "vault_stats_v1.csv"
    return None
