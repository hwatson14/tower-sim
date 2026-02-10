from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Protocol

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.loaders.account_snapshot_loader import load_account_snapshot
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.util.account_snapshot import AccountSnapshot, CardSnapshot, WorkshopEntrySnapshot

TOP_N_DEFAULT = 10
INTERNAL_PRESET_SEQUENCE = ("Farming", "Tourney", "Testing")
PRESET_LABELS = {"Farming": "Farming", "Tourney": "Tournament", "Testing": "Milestone"}

# Canonical stone-spend table manifest required before a full stone optimizer can run.
REQUIRED_STONE_TABLES = (
    "tables/uw_purchase_costs_v1.csv",
    "tables/uw_track_ladders_v1.csv",
    "tables/uw_plus_ladders_v1.csv",
    "tables/assist_slot_unlock_costs_v1.csv",
    "tables/assist_unique_rarity_upgrade_costs_v1.csv",
    "tables/assist_efficiency_upgrade_costs_v1.csv",
    "tables/card_masteries_v1.csv",
)


class OptimizerDataError(ValueError):
    """Raised when required optimizer source data is missing."""


class EvaluatorAdapter(Protocol):
    evaluator_name: str
    metric_name: str

    def evaluate(self, problem_spec: Any, snapshot: AccountSnapshot) -> float | None: ...


class MaxWaveAdapter:
    evaluator_name = "max_wave"
    metric_name = "w_max"

    def __init__(self) -> None:
        self._evaluator = MaxWaveEvaluator()

    def evaluate(self, problem_spec: Any, snapshot: AccountSnapshot) -> float | None:
        result = self._evaluator.evaluate(problem_spec, snapshot)
        value = result.get("w_max")
        return None if value is None else float(value)


def run_resource_optimizer(task: str, args: Dict[str, Any]) -> Dict[str, Any]:
    objective = args["objective"]
    if objective != "MAX_WAVE":
        return _fail_closed(task, ["econ_evaluator_not_implemented"])

    adapter: EvaluatorAdapter = MaxWaveAdapter()
    snapshot = load_account_snapshot(args["account_snapshot"])
    top_n = int(args.get("top_n", TOP_N_DEFAULT))
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer.")

    problem_spec = _resolve_problem_spec(args)
    base_patch = args.get("snapshot_patch")

    if task == "OPTIMIZE_STONES":
        missing_tables = _missing_required_tables(REQUIRED_STONE_TABLES)
        if missing_tables:
            return _fail_closed(task, [f"missing_table:{path}" for path in missing_tables])
        actions = _stone_actions(snapshot)
        data_complete = False
        incomplete_reasons = ["stone_actions_uw_uwplus_assist_not_implemented"]
    elif task == "OPTIMIZE_COINS":
        actions = _placeholder_actions("coins")
        data_complete = False
        incomplete_reasons = ["coin_actions_not_implemented"]
    elif task == "OPTIMIZE_LABS":
        actions = _placeholder_actions("lab_hours")
        data_complete = False
        incomplete_reasons = ["lab_actions_not_implemented"]
    else:
        return _fail_closed(task, ["optimizer_not_implemented"])

    tables: List[Dict[str, Any]] = []
    for preset_name in _optimizer_presets(snapshot):
        baseline_snapshot = replace(snapshot, default_preset=preset_name)
        if base_patch is not None:
            baseline_snapshot = _apply_snapshot_patch(baseline_snapshot, base_patch)
        baseline_value = adapter.evaluate(problem_spec, baseline_snapshot)

        rows: List[Dict[str, Any]] = []
        for action in actions:
            row = _evaluate_action_row(action, baseline_snapshot, baseline_value, adapter, problem_spec)
            rows.append(row)

        ranked = sorted(
            rows,
            key=lambda row: (
                row["roi"] is None,
                -(row["roi"] or 0.0),
                row["action_id"],
            ),
        )[:top_n]
        tables.append(
            {
                "preset_name": preset_name,
                "preset_label": PRESET_LABELS.get(preset_name, preset_name),
                "baseline_value": baseline_value,
                "ranked_actions": ranked,
            }
        )

    return {
        "task": task,
        "ok": True,
        "fail_closed": False,
        "missing": [],
        "resolved_from": "account_snapshot_payload",
        "result": {
            "resource": _task_resource(task),
            "objective": objective,
            "evaluator": adapter.evaluator_name,
            "metric": adapter.metric_name,
            "top_n": top_n,
            "data_complete": data_complete,
            "incomplete_reasons": incomplete_reasons,
            "tables": tables,
        },
    }


def _evaluate_action_row(
    action: Dict[str, Any],
    baseline_snapshot: AccountSnapshot,
    baseline_value: float | None,
    adapter: EvaluatorAdapter,
    problem_spec: Any,
) -> Dict[str, Any]:
    if not action.get("eligible", True):
        return _row_from_ineligible(action, baseline_value)

    patched = action["apply_unlock"](baseline_snapshot)
    unlock_value = adapter.evaluate(problem_spec, patched)

    maxed_value = None
    if "apply_maxed" in action:
        maxed_value = adapter.evaluate(problem_spec, action["apply_maxed"](baseline_snapshot))

    roi = None
    delta_value = None
    maxed_delta_value = None
    if baseline_value is not None and unlock_value is not None:
        delta_value = unlock_value - baseline_value
        cost = action["cost"]
        roi = None if cost <= 0 else (delta_value / cost)
    if baseline_value is not None and maxed_value is not None:
        maxed_delta_value = maxed_value - baseline_value

    return {
        "action_id": action["action_id"],
        "action_label": action["action_label"],
        "eligible": True,
        "baseline_value": baseline_value,
        "candidate_value": unlock_value,
        "delta_value": delta_value,
        "maxed_candidate_value": maxed_value,
        "maxed_delta_value": maxed_delta_value,
        "cost": action["cost"],
        "resource_unit": action["resource_unit"],
        "roi": roi,
        "notes": action.get("notes"),
    }


def _task_resource(task: str) -> str:
    return {
        "OPTIMIZE_STONES": "stones",
        "OPTIMIZE_COINS": "coins",
        "OPTIMIZE_LABS": "lab_hours",
    }[task]


def _resolve_problem_spec(args: Dict[str, Any]):
    if "problem_spec" in args:
        from tower_sim.run.spec_loader import parse_problem_spec_data

        return parse_problem_spec_data(args["problem_spec"])
    return load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))


def _fail_closed(task: str, missing: List[str]) -> Dict[str, Any]:
    return {
        "task": task,
        "ok": False,
        "fail_closed": True,
        "missing": sorted(set(missing)),
        "resolved_from": "account_snapshot_payload",
        "result": None,
    }


def _placeholder_actions(unit: str) -> List[Dict[str, Any]]:
    return [
        {
            "action_id": f"{unit}_authoritative_cost_missing",
            "action_label": f"{unit} spend action (authoritative costs required)",
            "eligible": False,
            "cost": 1.0,
            "resource_unit": unit,
            "notes": "missing_authoritative_cost_table",
        }
    ]


def _row_from_ineligible(action: Dict[str, Any], baseline_value: Any) -> Dict[str, Any]:
    return {
        "action_id": action["action_id"],
        "action_label": action["action_label"],
        "eligible": False,
        "baseline_value": baseline_value,
        "candidate_value": None,
        "delta_value": None,
        "maxed_candidate_value": None,
        "maxed_delta_value": None,
        "cost": action["cost"],
        "resource_unit": action["resource_unit"],
        "roi": None,
        "notes": action.get("notes"),
    }


def _stone_actions(snapshot: AccountSnapshot) -> List[Dict[str, Any]]:
    card_masteries = _load_card_masteries()
    actions: List[Dict[str, Any]] = []
    for preset_name in _optimizer_presets(snapshot):
        equipped = snapshot.card_presets.get(preset_name, [])
        for card_name in equipped:
            if snapshot.cards_inventory.get(card_name) is None:
                continue
            if card_name not in card_masteries:
                continue
            stone_cost = card_masteries[card_name]
            actions.append(
                _mastery_action(
                    action_id=f"mastery_unlock::{preset_name}::{card_name}",
                    action_label=f"{preset_name}: unlock {card_name} mastery",
                    card_name=card_name,
                    stone_cost=stone_cost,
                )
            )
    if not actions:
        return _placeholder_actions("stones")
    return actions


def _mastery_action(
    *,
    action_id: str,
    action_label: str,
    card_name: str,
    stone_cost: float,
) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        cards = dict(snapshot.cards_inventory)
        current = cards[card_name]
        cards[card_name] = CardSnapshot(
            name=current.name,
            level=current.level,
            mastery_unlocked=True,
            mastery_lab_level=current.mastery_lab_level,
        )
        return replace(snapshot, cards_inventory=cards)

    def _apply_maxed(snapshot: AccountSnapshot) -> AccountSnapshot:
        cards = dict(snapshot.cards_inventory)
        current = cards[card_name]
        cards[card_name] = CardSnapshot(
            name=current.name,
            level=current.level,
            mastery_unlocked=True,
            mastery_lab_level=9,
        )
        return replace(snapshot, cards_inventory=cards)

    return {
        "action_id": action_id,
        "action_label": action_label,
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "apply_maxed": _apply_maxed,
        "notes": "card_masteries_v1",
    }


def _load_card_masteries() -> Dict[str, int]:
    path = Path("tables/card_masteries_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/card_masteries_v1.csv")
    values: Dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values[row["card_mastery"]] = int(row["stone_cost"])
    return values


def _apply_snapshot_patch(snapshot: AccountSnapshot, patch: Dict[str, Any]) -> AccountSnapshot:
    patched = snapshot
    for entry in patch.get("labs", []):
        stat_id = entry["stat_id"]
        if stat_id not in patched.labs:
            raise OptimizerDataError(f"Unknown lab stat_id in snapshot_patch: {stat_id}")
        current = patched.labs[stat_id] or 0
        next_value = current + entry["delta_levels"]
        patched = replace(patched, labs={**patched.labs, stat_id: next_value})

    for entry in patch.get("workshop", []):
        stat_id = entry["stat_id"]
        if stat_id not in patched.workshop:
            raise OptimizerDataError(f"Unknown workshop stat_id in snapshot_patch: {stat_id}")
        workshop_entry = patched.workshop[stat_id]
        coin_level = workshop_entry.coin_level or 0
        delta = entry["delta_levels"]
        patched_entry = WorkshopEntrySnapshot(
            name=workshop_entry.name,
            coin_level=coin_level + delta,
            end_level=workshop_entry.end_level,
            max_level=workshop_entry.max_level,
            unlocked=workshop_entry.unlocked,
            category=workshop_entry.category,
        )
        patched = replace(patched, workshop={**patched.workshop, stat_id: patched_entry})

    return patched


def _optimizer_presets(snapshot: AccountSnapshot) -> List[str]:
    missing = [
        preset
        for preset in INTERNAL_PRESET_SEQUENCE
        if preset not in snapshot.card_presets or preset not in snapshot.module_presets
    ]
    if missing:
        raise OptimizerDataError(f"Missing required optimizer presets: {missing}")
    return list(INTERNAL_PRESET_SEQUENCE)


def _missing_required_tables(paths: tuple[str, ...]) -> List[str]:
    return [path for path in paths if not Path(path).exists()]
