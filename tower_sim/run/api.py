from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.engines.statbook_builder import build_statbook
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.registry.stat_registry import Phase
from tower_sim.util.ids_state import IdsState
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.loaders.sources import DatasetBundle, IdsOnlyBundle, load_ids_only_bundle, load_snapshot_bundle
from tower_sim.run.spec_loader import parse_problem_spec_data, spec_as_dict

LOGGER = logging.getLogger(__name__)

TASK_BASE_STATS = "BASE_STATS"
TASK_INVENTORY = "INVENTORY"
TASK_LOADOUT = "LOADOUT"
TASK_EHP_SLICE = "EHP_SLICE"
TASK_MAX_WAVE = "MAX_WAVE"

TASKS_REQUIRING_IDS = {
    TASK_BASE_STATS,
    TASK_INVENTORY,
    TASK_LOADOUT,
    TASK_EHP_SLICE,
    TASK_MAX_WAVE,
}


def run(
    problem_spec: ProblemSpec,
    ids_path: Optional[Path] = None,
    ids_state: Optional[IdsState] = None,
) -> Dict[str, Any]:
    return run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(problem_spec)},
        ids_path=ids_path,
        ids_state=ids_state,
    )


def run_task(
    task: str,
    args: Optional[Dict[str, Any]] = None,
    *,
    ids_path: Optional[Path] = None,
    ids_state: Optional[IdsState] = None,
) -> Dict[str, Any]:
    _validate_task_name(task)
    resolved_args = args or {}
    _validate_task_args(task, resolved_args)
    bundle = _resolve_bundle()
    resolved_ids_state = _resolve_ids_state(bundle, ids_path, ids_state)
    missing = []
    if task in TASKS_REQUIRING_IDS and resolved_ids_state is None:
        missing.append("ids_state")

    if missing:
        return _fail_closed(task, missing=missing, resolved_from=bundle.resolved_from)

    if task == TASK_BASE_STATS:
        statbook = build_statbook(resolved_ids_state)
        return _ok(
            task,
            {"statbook": [asdict(row) for row in statbook.rows]},
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_INVENTORY:
        payload = _serialize_inventory(resolved_ids_state)
        return _ok(task, payload, resolved_from=bundle.resolved_from)
    if task == TASK_LOADOUT:
        payload = _serialize_loadout(resolved_ids_state)
        return _ok(task, payload, resolved_from=bundle.resolved_from)
    if task == TASK_EHP_SLICE:
        enabled_stats = resolved_args["enabled_stats"]
        allow_out_of_scope = bool(resolved_args.get("allow_out_of_scope", False))
        values = evaluate_stats(
            resolved_ids_state,
            enabled_stats=enabled_stats,
            allow_out_of_scope=allow_out_of_scope,
        )
        return _ok(
            task,
            {"stats": values, "enabled_stats": list(enabled_stats)},
            resolved_from=bundle.resolved_from,
        )
    if task == TASK_MAX_WAVE:
        problem_spec_data = resolved_args["problem_spec"]
        problem_spec = parse_problem_spec_data(problem_spec_data)
        _log_problem_spec(problem_spec)
        evaluator = MaxWaveEvaluator()
        result = evaluator.evaluate(problem_spec, resolved_ids_state)
        result["resolved_from"] = bundle.resolved_from
        result["task"] = task
        result["ok"] = not result.get("fail_closed", False)
        return result

    return _fail_closed(task, missing=[f"task:{task}"], resolved_from=bundle.resolved_from)


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


def _resolve_ids_state(
    bundle: DatasetBundle | IdsOnlyBundle,
    ids_path: Optional[Path],
    ids_state: Optional[IdsState],
) -> Optional[IdsState]:
    if ids_state is not None:
        return ids_state
    try:
        if ids_path is not None:
            return parse_ids(ids_path)
        if isinstance(bundle, DatasetBundle) and "_IDS.csv" in bundle.files:
            return parse_ids(bundle.files["_IDS.csv"])
        if isinstance(bundle, IdsOnlyBundle):
            return parse_ids(bundle.ids_path)
    except (FileNotFoundError, ValueError):
        return None
    return None


def _log_problem_spec(problem_spec: ProblemSpec) -> None:
    payload = json.dumps(spec_as_dict(problem_spec), sort_keys=True)
    LOGGER.info("Resolved ProblemSpec: %s", payload)


def _validate_task_name(task: str) -> None:
    allowed = {
        TASK_BASE_STATS,
        TASK_INVENTORY,
        TASK_LOADOUT,
        TASK_EHP_SLICE,
        TASK_MAX_WAVE,
    }
    if task not in allowed:
        raise ValueError(f"Unknown task: {task!r}")


def _validate_task_args(task: str, args: Dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ValueError("Task args must be a mapping.")
    if task in {TASK_BASE_STATS, TASK_INVENTORY, TASK_LOADOUT}:
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


def _serialize_inventory(ids_state: IdsState) -> Dict[str, Any]:
    return {
        "labs": dict(ids_state.labs.labs),
        "workshop": {
            name: _serialize_workshop_entry(entry)
            for name, entry in ids_state.workshop.entries.items()
        },
        "workshop_plus": list(ids_state.workshop_plus.raw_rows),
        "ultimate_weapons": {
            name: _serialize_uw_entry(entry)
            for name, entry in ids_state.ultimate_weapons.entries.items()
        },
        "ultimate_weapons_plus_placeholder": ids_state.ultimate_weapons.uw_plus_placeholder,
        "cards": {
            name: _serialize_card_entry(entry)
            for name, entry in ids_state.cards.cards.items()
        },
        "relics": dict(ids_state.relics.relics),
        "vault": dict(ids_state.vault.vault),
        "bots": {
            name: _serialize_bot_entry(entry) for name, entry in ids_state.bots.bots.items()
        },
        "themes_songs": list(ids_state.themes_songs.raw_rows),
        "modules": [
            _serialize_module_slot(slot) for slot in ids_state.modules.slots
        ],
        "guardians": list(ids_state.guardians.raw_rows),
        "player_stuff": dict(ids_state.player_stuff.key_values),
    }


def _serialize_loadout(ids_state: IdsState) -> Dict[str, Any]:
    equipped_cards = [
        _serialize_card_entry(entry)
        for entry in ids_state.cards.cards.values()
        if _is_card_equipped(entry.equipped_flags)
    ]
    return {
        "cards": equipped_cards,
        "modules": [
            _serialize_module_slot(slot) for slot in ids_state.modules.slots
        ],
        "bots": [
            _serialize_bot_entry(entry) for entry in ids_state.bots.bots.values()
        ],
        "guardians": list(ids_state.guardians.raw_rows),
        "phase": Phase.START_OF_RUN.value,
    }


def _is_card_equipped(flags: list[str]) -> bool:
    return any(flag == "1" for flag in flags)


def _serialize_workshop_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "unlocked": entry.unlocked,
        "coin_level": entry.coin_level,
        "max_level": entry.max_level,
        "category": entry.category,
        "raw_row": list(entry.raw_row),
    }


def _serialize_uw_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "unlocked": entry.unlocked,
        "track_levels": list(entry.track_levels),
        "raw_row": list(entry.raw_row),
    }


def _serialize_card_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "level": entry.level,
        "equipped_flags": list(entry.equipped_flags),
        "raw_row": list(entry.raw_row),
    }


def _serialize_bot_entry(entry: Any) -> Dict[str, Any]:
    return {
        "name": entry.name,
        "raw_row": list(entry.raw_row),
    }


def _serialize_module_slot(entry: Any) -> Dict[str, Any]:
    return {
        "slot_index": entry.slot_index,
        "context": entry.context,
        "slot_type": entry.slot_type,
        "module_name": entry.module_name,
        "rarity": entry.rarity,
        "level": entry.level,
        "stat": entry.stat,
        "substats": list(entry.substats),
        "raw_rows": [list(row) for row in entry.raw_rows],
    }
