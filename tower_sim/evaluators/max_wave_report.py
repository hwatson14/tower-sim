from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs
from tower_sim.engines.survivability_pipeline import (
    SurvivabilityPipelineError,
    _build_inventory_summary,
    _compile_base_stat_inputs,
    _compile_loadout_stat_inputs,
    _merge_stat_inputs,
)
from tower_sim.registry.stat_registry import default_registry
from tower_sim.run.context import RunContext
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.util.account_snapshot import AccountSnapshot
from tower_sim.evaluators.max_wave import (
    _default_wave_damage_tier,
    _filter_known_stat_inputs,
    _load_tier_rules,
    _maybe_build_wave_state,
    _missing_required_stat_inputs,
    _resolve_survivability_stats,
    _resolve_wave_damage_for_wave,
    _resolve_wave_snapshot,
    _resolve_wave_state_for_wave,
    _search_wmax,
)


def build_max_wave_report(
    problem_spec: ProblemSpec,
    ids_snapshot: AccountSnapshot,
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

    report["base_state"] = _extract_base_state(ids_snapshot)

    inventory = _safe_build_inventory(
        ids_snapshot,
        module_context=module_context,
        module_overrides=module_overrides,
        missing=missing,
        errors=errors,
    )
    if inventory is not None:
        report["inventory"] = inventory

    loadout_breakdown = _safe_build_loadout_breakdown(
        ids_snapshot,
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
            ids_snapshot=ids_snapshot,
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


def _extract_base_state(ids_snapshot: AccountSnapshot) -> Dict[str, Any]:
    workshop_entries = {}
    for name, entry in ids_snapshot.workshop.items():
        workshop_entries[name] = {
            "unlocked": entry.unlocked,
            "coin_level": entry.coin_level,
            "max_level": entry.max_level,
            "category": entry.category,
        }
    ultimate_weapons = {}
    for name, entry in ids_snapshot.ultimate_weapons.items():
        ultimate_weapons[name] = {
            "unlocked": entry.unlocked,
            "track_levels": entry.track_levels,
        }
    return {
        "labs": dict(ids_snapshot.labs),
        "workshop": workshop_entries,
        "relics": dict(ids_snapshot.relics),
        "ultimate_weapons": ultimate_weapons,
    }


def _safe_build_inventory(
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str,
    module_overrides: Mapping[str, Mapping[str, Optional[str]]] | None,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    try:
        return _build_inventory_summary(ids_snapshot, module_context, module_overrides)
    except SurvivabilityPipelineError as exc:
        _record_report_error("inventory", exc, missing, errors)
        return None


def _safe_build_loadout_breakdown(
    ids_snapshot: AccountSnapshot,
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
            ids_snapshot, allow_provisional=allow_provisional
        )
        loadout_inputs = _compile_loadout_stat_inputs(
            ids_snapshot,
            module_context=module_context,
            module_overrides=module_overrides,
            selected_cards=selected_cards,
            allow_provisional=allow_provisional,
        )
    except (SurvivabilityPipelineError, FileNotFoundError, ValueError, KeyError) as exc:
        _record_report_error("loadout_compilation", exc, missing, errors)
        return None

    compiled = compile_full_stat_inputs(ids_snapshot)
    stat_inputs = _merge_stat_inputs(base_inputs, loadout_inputs)
    stat_inputs = _merge_stat_inputs(stat_inputs, compiled.stat_inputs)
    registry = default_registry()
    stat_inputs, invalid_stat_inputs = _filter_known_stat_inputs(stat_inputs, registry)
    engine = StatEngine(registry=registry)
    try:
        engine_result = engine.build(stat_inputs)
    except Exception as exc:  # noqa: BLE001
        _record_report_error("stat_engine", exc, missing, errors)
        return None

    return {
        "base_stat_inputs": [_serialize_stat_input(row) for row in base_inputs],
        "loadout_stat_inputs": [_serialize_stat_input(row) for row in loadout_inputs],
        "compiled_stat_inputs": [_serialize_stat_input(row) for row in compiled.stat_inputs],
        "compiled_missing": compiled.missing,
        "invalid_stat_inputs": invalid_stat_inputs,
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
    ids_snapshot: AccountSnapshot,
    trace_depth: int,
    missing: List[str],
    errors: List[Dict[str, str]],
) -> Optional[List[Dict[str, Any]]]:
    run_context = RunContext.from_mode(
        problem_spec.scenario.mode,
        tier=str(problem_spec.scenario.tier),
    )
    spec_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
    compiled = compile_full_stat_inputs(ids_snapshot)
    stat_inputs = _merge_stat_inputs(spec_inputs, compiled.stat_inputs)
    registry = default_registry()
    stat_inputs, invalid_stat_inputs = _filter_known_stat_inputs(stat_inputs, registry)
    if invalid_stat_inputs:
        for stat_id in invalid_stat_inputs:
            errors.append(
                {"id": "stat_input_invalid", "error": f"Unknown stat_id: {stat_id}"}
            )
    missing.extend(_missing_required_stat_inputs(stat_inputs))

    wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
    missing.extend(wave_state_missing)

    tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
    missing.extend(tier_rule_missing)

    if missing:
        for item in sorted(set(missing)):
            errors.append({"id": item, "error": "Missing trace prerequisites."})
        return None

    engine = StatEngine(registry=registry)
    try:
        if tier_rules is None:
            engine_result = engine.build(stat_inputs, wave_state=wave_state)
        else:
            engine_result = engine.build_with_tier_rules(
                stat_inputs, tier_rules, wave_state=wave_state
            )
    except Exception as exc:  # noqa: BLE001
        _record_report_error("stat_engine", exc, missing, errors)
        return None

    (
        _w_max,
        _failure_wave,
        _failure_reason,
        _failure_snapshot,
        trace,
        _search_diagnostics,
        search_missing,
    ) = _search_wmax(
        problem_spec=problem_spec,
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=tier_rules,
        run_context=run_context,
        ids_snapshot=ids_snapshot,
        trace_depth=trace_depth,
    )
    if search_missing:
        for item in search_missing:
            _record_report_error(item, ValueError("Missing search inputs."), missing, errors)
        return None
    return trace


def _resolve_survivability_stats_for_report(
    problem_spec: ProblemSpec,
    *,
    ids_snapshot: AccountSnapshot,
) -> Tuple[Optional[Dict[str, float]], List[str]]:
    missing: List[str] = []
    run_context = RunContext.from_mode(
        problem_spec.scenario.mode,
        tier=str(problem_spec.scenario.tier),
    )
    spec_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
    compiled = compile_full_stat_inputs(ids_snapshot)
    stat_inputs = _merge_stat_inputs(spec_inputs, compiled.stat_inputs)
    registry = default_registry()
    stat_inputs, invalid_stat_inputs = _filter_known_stat_inputs(stat_inputs, registry)
    if invalid_stat_inputs:
        return None, ["stat_inputs_invalid"]
    missing.extend(_missing_required_stat_inputs(stat_inputs))

    wave_state, wave_state_missing = _maybe_build_wave_state(problem_spec)
    missing.extend(wave_state_missing)

    tier_rules, tier_rule_missing = _load_tier_rules(problem_spec, run_context)
    missing.extend(tier_rule_missing)

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

    diagnostics: Dict[str, Any] = {}
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
