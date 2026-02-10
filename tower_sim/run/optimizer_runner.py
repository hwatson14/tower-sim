from __future__ import annotations

from typing import Any, Dict

from tower_sim.loaders.account_snapshot_loader import load_account_snapshot
from tower_sim.run.optimizer_engine import run_resource_optimizer
from tower_sim.run.optimizer_patch import validate_loadout_patch, validate_snapshot_patch

OPTIMIZER_TASKS = {
    "OPTIMIZE_LOADOUT",
    "OPTIMIZE_MODULE_SUBSTATS",
    "OPTIMIZE_STONES",
    "OPTIMIZE_COINS",
    "OPTIMIZE_LABS",
    "SENSITIVITY_REPORT",
}

OBJECTIVES = {"MAX_WAVE", "ECON_PER_HOUR"}
MISSING_NOT_IMPLEMENTED = "optimizer_not_implemented"
RESOURCE_TASKS = {"OPTIMIZE_STONES", "OPTIMIZE_COINS", "OPTIMIZE_LABS"}


def run_optimizer_task(task: str, args: Dict[str, Any]) -> Dict[str, Any]:
    _validate_task_name(task)
    _validate_task_args(args)
    snapshot_payload = args["account_snapshot"]
    try:
        load_account_snapshot(snapshot_payload)
    except ValueError:
        return _fail_closed(task, missing=["account_snapshot"], resolved_from="account_snapshot_payload")

    snapshot_patch = args.get("snapshot_patch")
    if snapshot_patch is not None:
        validate_snapshot_patch(snapshot_patch)
    loadout_patch = args.get("loadout_patch")
    if loadout_patch is not None:
        validate_loadout_patch(loadout_patch)

    if task in RESOURCE_TASKS:
        return run_resource_optimizer(task, args)

    return _fail_closed(task, missing=[MISSING_NOT_IMPLEMENTED], resolved_from="account_snapshot_payload")


def _validate_task_name(task: str) -> None:
    if task not in OPTIMIZER_TASKS:
        raise ValueError(f"Unknown optimizer task: {task!r}")


def _validate_task_args(args: Dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ValueError("Task args must be a mapping.")
    _require_keys(
        args,
        required={"objective", "account_snapshot"},
        optional={
            "snapshot_patch",
            "loadout_patch",
            "loadout_override",
            "constraints",
            "debug",
            "problem_spec",
            "top_n",
        },
    )
    objective = args["objective"]
    if not isinstance(objective, str) or objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {sorted(OBJECTIVES)}.")
    if not isinstance(args["account_snapshot"], dict):
        raise ValueError("account_snapshot must be a mapping.")
    if "snapshot_patch" in args and not isinstance(args["snapshot_patch"], dict):
        raise ValueError("snapshot_patch must be a mapping.")
    if "loadout_patch" in args and not isinstance(args["loadout_patch"], dict):
        raise ValueError("loadout_patch must be a mapping.")
    if "loadout_override" in args and not isinstance(args["loadout_override"], dict):
        raise ValueError("loadout_override must be a mapping.")
    if "constraints" in args and not isinstance(args["constraints"], dict):
        raise ValueError("constraints must be a mapping.")
    if "debug" in args and not isinstance(args["debug"], dict):
        raise ValueError("debug must be a mapping.")
    if "problem_spec" in args and not isinstance(args["problem_spec"], dict):
        raise ValueError("problem_spec must be a mapping.")
    if "top_n" in args and (not isinstance(args["top_n"], int) or args["top_n"] <= 0):
        raise ValueError("top_n must be a positive integer.")


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
