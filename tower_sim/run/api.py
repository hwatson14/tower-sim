from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.engines.statbook_builder import build_statbook
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import (
    compile_account_snapshot,
    resolve_loadout,
)
from tower_sim.util.account_snapshot import AccountSnapshot, ModuleSnapshot, ResolvedLoadout
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.run.optimizer_runner import OPTIMIZER_TASKS, run_optimizer_task
from tower_sim.loaders.sources import DatasetBundle, IdsOnlyBundle, load_ids_only_bundle, load_snapshot_bundle
from tower_sim.run.spec_loader import parse_problem_spec_data, spec_as_dict

LOGGER = logging.getLogger(__name__)

TASK_BASE_STATS = "BASE_STATS"
TASK_STAT_INPUTS = "STAT_INPUTS"
TASK_INVENTORY = "INVENTORY"
TASK_LOADOUT = "LOADOUT"
TASK_EHP_SLICE = "EHP_SLICE"
TASK_MAX_WAVE = "MAX_WAVE"
TASK_OPTIMIZE_LOADOUT = "OPTIMIZE_LOADOUT"
TASK_OPTIMIZE_MODULE_SUBSTATS = "OPTIMIZE_MODULE_SUBSTATS"
TASK_OPTIMIZE_STONES = "OPTIMIZE_STONES"
TASK_OPTIMIZE_COINS = "OPTIMIZE_COINS"
TASK_OPTIMIZE_LABS = "OPTIMIZE_LABS"
TASK_SENSITIVITY_REPORT = "SENSITIVITY_REPORT"

TASKS_REQUIRING_IDS = {
    TASK_BASE_STATS,
    TASK_STAT_INPUTS,
    TASK_INVENTORY,
    TASK_LOADOUT,
    TASK_EHP_SLICE,
    TASK_MAX_WAVE,
}


def run(
    problem_spec: ProblemSpec,
    ids_path: Optional[Path] = None,
    ids_snapshot: Optional[AccountSnapshot] = None,
) -> Dict[str, Any]:
    return run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(problem_spec)},
        ids_path=ids_path,
        ids_snapshot=ids_snapshot,
    )


def run_task(
    task: str,
    args: Optional[Dict[str, Any]] = None,
    *,
    ids_path: Optional[Path] = None,
    ids_snapshot: Optional[AccountSnapshot] = None,
) -> Dict[str, Any]:
    _validate_task_name(task)
    resolved_args = args or {}
    _validate_task_args(task, resolved_args)
    if task in OPTIMIZER_TASKS:
        return run_optimizer_task(task, resolved_args)
    bundle = _resolve_bundle()
    resolved_ids_snapshot = _resolve_ids_snapshot(bundle, ids_path, ids_snapshot)
    missing: list[str] = []
    if resolved_ids_snapshot is None:
        missing.append("ids_snapshot")
        return _fail_closed(task, missing=missing, resolved_from=bundle.resolved_from)

    if task == TASK_BASE_STATS:
        statbook = build_statbook(resolved_ids_snapshot)
        return _ok(
            task,
            {"statbook": asdict(statbook)},
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_STAT_INPUTS:
        compiled = compile_full_stat_inputs(resolved_ids_snapshot)
        return _ok(
            task,
            {
                "stat_inputs": [_serialize_stat_input(item) for item in compiled.stat_inputs],
                "missing": compiled.missing,
                "fail_closed": bool(compiled.missing),
            },
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_INVENTORY:
        return _ok(
            task,
            _serialize_inventory(resolved_ids_snapshot),
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_LOADOUT:
        return _ok(
            task,
            _serialize_loadout(resolved_ids_snapshot),
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_EHP_SLICE:
        enabled_stats = resolved_args["enabled_stats"]
        allow_out_of_scope = resolved_args.get("allow_out_of_scope", False)
        stats = evaluate_stats(
            resolved_ids_snapshot,
            enabled_stats,
            allow_out_of_scope=allow_out_of_scope,
        )
        return _ok(
            task,
            {"stats": stats},
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_MAX_WAVE:
        problem_spec = parse_problem_spec_data(resolved_args["problem_spec"])
        _log_problem_spec(problem_spec)
        evaluator = MaxWaveEvaluator()
        result = evaluator.evaluate(problem_spec, resolved_ids_snapshot)
        return _ok(task, result, resolved_from=bundle.resolved_from)
    raise ValueError(f"Unknown task: {task!r}")


def _resolve_bundle() -> DatasetBundle | IdsOnlyBundle:
    try:
        return load_snapshot_bundle(_default_cache_dirs())
    except FileNotFoundError:
        return load_ids_only_bundle(_default_ids_paths())


def _default_cache_dirs():
    from tower_sim.libs.data_paths import DEFAULT_DATA_DIRS

    return list(DEFAULT_DATA_DIRS)


def _default_ids_paths():
    from tower_sim.loaders.ids_parser import DEFAULT_IDS_PATHS

    return list(DEFAULT_IDS_PATHS)


def _resolve_ids_snapshot(
    bundle: DatasetBundle | IdsOnlyBundle,
    ids_path: Optional[Path],
    ids_snapshot: Optional[AccountSnapshot],
) -> Optional[AccountSnapshot]:
    if ids_snapshot is not None:
        return ids_snapshot
    try:
        if ids_path is not None:
            return compile_account_snapshot(parse_ids(ids_path))
        if isinstance(bundle, DatasetBundle) and "_IDS.csv" in bundle.files:
            return compile_account_snapshot(parse_ids(bundle.files["_IDS.csv"]))
        if isinstance(bundle, IdsOnlyBundle):
            return compile_account_snapshot(parse_ids(bundle.ids_path))
    except (FileNotFoundError, ValueError):
        return None
    return None


def _log_problem_spec(problem_spec: ProblemSpec) -> None:
    payload = json.dumps(spec_as_dict(problem_spec), sort_keys=True)
    LOGGER.info("Resolved ProblemSpec: %s", payload)


def _validate_task_name(task: str) -> None:
    allowed = {
        TASK_BASE_STATS,
        TASK_STAT_INPUTS,
        TASK_INVENTORY,
        TASK_LOADOUT,
        TASK_EHP_SLICE,
        TASK_MAX_WAVE,
    }
    if task not in allowed and task not in OPTIMIZER_TASKS:
        raise ValueError(f"Unknown task: {task!r}")


def _validate_task_args(task: str, args: Dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ValueError("Task args must be a mapping.")
    if task in {TASK_BASE_STATS, TASK_STAT_INPUTS, TASK_INVENTORY, TASK_LOADOUT}:
        if args:
            raise ValueError(f"Task {task} does not accept args.")
        return
    if task == TASK_EHP_SLICE:
        _require_keys(args, required={"enabled_stats"}, optional={"allow_out_of_scope"})
        enabled_stats = args["enabled_stats"]
        if not isinstance(enabled_stats, list) or not all(
            isinstance(item, str) for item in enabled_stats
        ):
            raise ValueError("enabled_stats must be a list of strings.")
        allow_out_of_scope = args.get("allow_out_of_scope", False)
        if not isinstance(allow_out_of_scope, bool):
            raise ValueError("allow_out_of_scope must be a boolean.")
        return
    if task == TASK_MAX_WAVE:
        _require_keys(args, required={"problem_spec"}, optional=set())
        if not isinstance(args["problem_spec"], dict):
            raise ValueError("problem_spec must be a mapping.")
        return
    if task in OPTIMIZER_TASKS:
        return
    raise ValueError(f"Unknown task: {task!r}")


def _require_keys(
    data: Dict[str, Any],
    *,
    required: set[str],
    optional: set[str],
) -> None:
    keys = set(data.keys())
    missing = required - keys
    if missing:
        raise ValueError(f"Missing required args: {sorted(missing)}")
    unknown = keys - required - optional
    if unknown:
        raise ValueError(f"Unknown args: {sorted(unknown)}")


def _fail_closed(task: str, *, missing: list[str], resolved_from: str) -> Dict[str, Any]:
    return {
        "task": task,
        "ok": False,
        "fail_closed": True,
        "missing": missing,
        "resolved_from": resolved_from,
        "result": None,
    }


def _ok(task: str, result: Dict[str, Any], *, resolved_from: str) -> Dict[str, Any]:
    return {
        "task": task,
        "ok": True,
        "fail_closed": False,
        "missing": [],
        "resolved_from": resolved_from,
        "result": result,
    }


def _serialize_inventory(ids_snapshot: AccountSnapshot) -> Dict[str, Any]:
    return {
        "labs": dict(ids_snapshot.labs),
        "workshop": {
            name: _serialize_workshop_entry(entry)
            for name, entry in ids_snapshot.workshop.items()
        },
        "ultimate_weapons": {
            name: _serialize_uw_entry(entry)
            for name, entry in ids_snapshot.ultimate_weapons.items()
        },
        "cards": {
            name: _serialize_card_entry(entry)
            for name, entry in ids_snapshot.cards_inventory.items()
        },
        "relics": dict(ids_snapshot.relics),
        "vault": dict(ids_snapshot.vault),
        "bots": list(ids_snapshot.bots),
        "modules": {
            name: _serialize_module_entry(entry)
            for name, entry in ids_snapshot.modules_inventory.items()
        },
        "guardians": list(ids_snapshot.guardians.rows),
    }


def _serialize_loadout(
    ids_snapshot: AccountSnapshot, preset_name: str | None = None
) -> Dict[str, Any]:
    resolved = _resolve_preset(ids_snapshot, preset_name)
    equipped_cards = [
        _serialize_card_entry(ids_snapshot.cards_inventory[card_name])
        for card_name in resolved.card_names
        if card_name in ids_snapshot.cards_inventory
    ]
    modules = {}
    for slot, selection in resolved.modules_by_slot.items():
        primary = (
            _serialize_module_entry(ids_snapshot.modules_inventory[selection.primary])
            if selection.primary and selection.primary in ids_snapshot.modules_inventory
            else None
        )
        assist = (
            _serialize_module_entry(ids_snapshot.modules_inventory[selection.assist])
            if selection.assist and selection.assist in ids_snapshot.modules_inventory
            else None
        )
        allocation = resolved.allocation_levels.get(slot)
        modules[slot] = {
            "primary": primary,
            "assist": assist,
            "allocation": _serialize_module_allocation(allocation) if allocation else None,
        }
    return {
        "preset_name": resolved.preset_name,
        "cards": equipped_cards,
        "modules": modules,
        "bots": list(ids_snapshot.bots),
        "guardians": list(ids_snapshot.guardians.rows),
    }


def _resolve_preset(
    ids_snapshot: AccountSnapshot, preset_name: str | None
) -> ResolvedLoadout:
    try:
        return resolve_loadout(ids_snapshot, preset_name)
    except ValueError as exc:
        raise ValueError(f"Invalid loadout preset: {exc}") from exc


def _serialize_workshop_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "unlocked": entry.unlocked,
        "coin_level": entry.coin_level,
        "max_level": entry.max_level,
        "category": entry.category,
    }


def _serialize_uw_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "unlocked": entry.unlocked,
        "track_levels": list(entry.track_levels),
    }


def _serialize_stat_input(stat_input: Any) -> Dict[str, Any]:
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


def _serialize_card_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "level": entry.level,
        "mastery_unlocked": entry.mastery_unlocked,
        "mastery_lab_level": entry.mastery_lab_level,
    }


def _serialize_module_entry(entry: ModuleSnapshot) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "slot_type": entry.slot_type,
        "rarity": entry.rarity,
        "level": entry.level,
        "stat": entry.stat,
        "substats": [
            {
                "stat_name": substat.stat_name,
                "rarity": substat.rarity,
                "value_display": substat.value_display,
                "value_num": substat.value_num,
            }
            for substat in entry.substats
        ],
    }


def _serialize_module_allocation(entry: Any) -> Dict[str, Any]:
    return {
        "primary_level": entry.primary_level,
        "assist_level": entry.assist_level,
    }
