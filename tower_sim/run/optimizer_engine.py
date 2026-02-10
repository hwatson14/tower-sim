from __future__ import annotations

import csv
import re
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
        data_complete = True
        incomplete_reasons: List[str] = []
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

        table_actions = [action for action in actions if _action_applies_to_preset(action, preset_name)]
        has_eligible_actions = any(action.get("eligible", True) for action in table_actions)
        baseline_value = adapter.evaluate(problem_spec, baseline_snapshot) if has_eligible_actions else None

        rows: List[Dict[str, Any]] = []
        for action in table_actions:
            row = _evaluate_action_row(
                action,
                baseline_snapshot,
                baseline_value,
                adapter,
                problem_spec,
                include_maxed=False,
            )
            rows.append(row)

        ranked = sorted(
            rows,
            key=lambda row: (
                row["roi"] is None,
                -(row["roi"] or 0.0),
                row["action_id"],
            ),
        )[:top_n]
        actions_by_id = {action["action_id"]: action for action in table_actions}
        _populate_ranked_maxed_values(
            ranked,
            actions_by_id,
            baseline_snapshot,
            baseline_value,
            adapter,
            problem_spec,
        )

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
    *,
    include_maxed: bool = True,
) -> Dict[str, Any]:
    if not action.get("eligible", True):
        return _row_from_ineligible(action, baseline_value)

    patched = action["apply_unlock"](baseline_snapshot)
    unlock_value = adapter.evaluate(problem_spec, patched)

    maxed_value = None
    if include_maxed and "apply_maxed" in action:
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


def _action_applies_to_preset(action: Dict[str, Any], preset_name: str) -> bool:
    action_id = action.get("action_id", "")
    if not action_id.startswith("mastery_unlock::"):
        return True
    parts = action_id.split("::", 2)
    if len(parts) < 3:
        return False
    return parts[1] == preset_name


def _populate_ranked_maxed_values(
    ranked: List[Dict[str, Any]],
    actions_by_id: Dict[str, Dict[str, Any]],
    baseline_snapshot: AccountSnapshot,
    baseline_value: float | None,
    adapter: EvaluatorAdapter,
    problem_spec: Any,
) -> None:
    if baseline_value is None:
        return
    for row in ranked:
        if not row.get("eligible", True):
            continue
        action = actions_by_id.get(row["action_id"])
        if action is None or "apply_maxed" not in action:
            continue
        maxed_value = adapter.evaluate(problem_spec, action["apply_maxed"](baseline_snapshot))
        row["maxed_candidate_value"] = maxed_value
        row["maxed_delta_value"] = None if maxed_value is None else (maxed_value - baseline_value)


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
    uw_purchase_costs = _load_uw_purchase_costs()
    uw_track_costs = _load_uw_track_ladders()
    uw_plus_costs = _load_uw_plus_ladders()
    assist_efficiency_costs = _load_assist_efficiency_costs()
    assist_slot_unlock_cost = _load_assist_slot_unlock_cost()
    assist_rarity_costs = _load_assist_unique_rarity_costs()
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

    uw_state = _parse_uw_rows(snapshot)
    next_uw_unlock_cost = uw_purchase_costs.get(uw_state["uw_unlocked_count"] + 1)
    if next_uw_unlock_cost is not None:
        for uw_name in uw_state["locked_uws"]:
            actions.append(
                _uw_unlock_action(
                    uw_name=uw_name,
                    stone_cost=float(next_uw_unlock_cost),
                )
            )

    next_uw_plus_unlock_cost = uw_purchase_costs.get(
        "uw_plus", {}
    ).get(uw_state["uw_plus_unlocked_count"] + 1)
    if next_uw_plus_unlock_cost is not None:
        for uw_name in uw_state["uw_plus_locked"]:
            actions.append(
                _uw_plus_unlock_action(
                    uw_name=uw_name,
                    stone_cost=float(next_uw_plus_unlock_cost),
                )
            )

    for track in uw_state["uw_tracks"]:
        next_level = track["current_level"] + 1
        key = (track["uw_name"], track["track_name"], next_level)
        next_cost = uw_track_costs.get(key)
        if next_cost is None:
            continue
        actions.append(
            _uw_track_upgrade_action(
                uw_name=track["uw_name"],
                track_name=track["track_name"],
                next_level=next_level,
                stone_cost=float(next_cost),
            )
        )

    for plus_track in uw_state["uw_plus_tracks"]:
        next_level = plus_track["current_level"] + 1
        key = (plus_track["uw_name"], plus_track["plus_track_name"], next_level)
        next_cost = uw_plus_costs.get(key)
        if next_cost is None:
            continue
        actions.append(
            _uw_plus_track_upgrade_action(
                uw_name=plus_track["uw_name"],
                plus_track_name=plus_track["plus_track_name"],
                next_level=next_level,
                stone_cost=float(next_cost),
            )
        )

    for slot_type, state in snapshot.module_system_state.items():
        if not state.assist_unlocked:
            actions.append(
                _assist_slot_unlock_action(
                    slot_type=slot_type,
                    stone_cost=assist_slot_unlock_cost,
                )
            )
            continue

        next_rarity = _next_assist_rarity(state.rarity_cap, assist_rarity_costs)
        if next_rarity is not None:
            actions.append(
                _assist_rarity_upgrade_action(
                    slot_type=slot_type,
                    current_rarity=state.rarity_cap or "Locked",
                    next_rarity=next_rarity,
                    stone_cost=float(assist_rarity_costs[(state.rarity_cap or "Locked", next_rarity)]),
                )
            )

        multiplier_level = _assist_cap_level_from_percent(state.multiplier_cap)
        if multiplier_level is not None and (multiplier_level + 1) in assist_efficiency_costs:
            actions.append(
                _assist_efficiency_action(
                    slot_type=slot_type,
                    target="multiplier",
                    next_level=multiplier_level + 1,
                    stone_cost=float(assist_efficiency_costs[multiplier_level + 1]),
                )
            )

        substat_level = _assist_cap_level_from_percent(state.substat_cap)
        if substat_level is not None and (substat_level + 1) in assist_efficiency_costs:
            actions.append(
                _assist_efficiency_action(
                    slot_type=slot_type,
                    target="substat",
                    next_level=substat_level + 1,
                    stone_cost=float(assist_efficiency_costs[substat_level + 1]),
                )
            )

    if not actions:
        return _placeholder_actions("stones")
    return actions


def _assist_cap_level_from_percent(value: float | None) -> int | None:
    if value is None:
        return None
    return max(0, int(round((float(value) * 100.0) - 1.0)))


def _next_assist_rarity(
    current_rarity: str | None,
    rarity_costs: Dict[tuple[str, str], int],
) -> str | None:
    source = current_rarity or "Locked"
    for from_rarity, to_rarity in rarity_costs:
        if from_rarity == source:
            return to_rarity
    return None


def _assist_slot_unlock_action(*, slot_type: str, stone_cost: float) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        state = snapshot.module_system_state[slot_type]
        patched = replace(state, assist_unlocked=True, rarity_cap="Epic")
        return replace(snapshot, module_system_state={**snapshot.module_system_state, slot_type: patched})

    return {
        "action_id": f"assist_slot_unlock::{slot_type}",
        "action_label": f"{slot_type}: unlock assist slot",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "assist_slot_unlock_costs_v1",
    }


def _assist_rarity_upgrade_action(
    *,
    slot_type: str,
    current_rarity: str,
    next_rarity: str,
    stone_cost: float,
) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        state = snapshot.module_system_state[slot_type]
        patched = replace(state, rarity_cap=next_rarity)
        return replace(snapshot, module_system_state={**snapshot.module_system_state, slot_type: patched})

    return {
        "action_id": f"assist_rarity_upgrade::{slot_type}::{current_rarity}->{next_rarity}",
        "action_label": f"{slot_type}: rarity cap {current_rarity} -> {next_rarity}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "assist_unique_rarity_upgrade_costs_v1",
    }


def _assist_efficiency_action(
    *,
    slot_type: str,
    target: str,
    next_level: int,
    stone_cost: float,
) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        state = snapshot.module_system_state[slot_type]
        next_percent = (next_level + 1) / 100.0
        if target == "multiplier":
            patched = replace(state, multiplier_cap=next_percent)
        else:
            patched = replace(state, substat_cap=next_percent)
        return replace(snapshot, module_system_state={**snapshot.module_system_state, slot_type: patched})

    return {
        "action_id": f"assist_efficiency_upgrade::{slot_type}::{target}::{next_level}",
        "action_label": f"{slot_type}: {target} efficiency -> level {next_level}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "assist_efficiency_upgrade_costs_v1",
    }


def _uw_unlock_action(*, uw_name: str, stone_cost: float) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        rows = _patched_uw_rows(snapshot, uw_name=uw_name, track_name=None, next_level=None, unlock_uw=True, unlock_plus=False)
        return _replace_snapshot_uw_state(snapshot, uw_name=uw_name, rows=rows)

    return {
        "action_id": f"uw_unlock::{uw_name}",
        "action_label": f"Unlock UW: {uw_name}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "uw_purchase_costs_v1",
    }


def _uw_plus_unlock_action(*, uw_name: str, stone_cost: float) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        rows = _patched_uw_rows(snapshot, uw_name=uw_name, track_name=None, next_level=None, unlock_uw=False, unlock_plus=True)
        return _replace_snapshot_uw_state(snapshot, uw_name=uw_name, rows=rows)

    return {
        "action_id": f"uw_plus_unlock::{uw_name}",
        "action_label": f"Unlock UW+: {uw_name}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "uw_purchase_costs_v1",
    }


def _uw_track_upgrade_action(
    *,
    uw_name: str,
    track_name: str,
    next_level: int,
    stone_cost: float,
) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        rows = _patched_uw_rows(
            snapshot,
            uw_name=uw_name,
            track_name=track_name,
            next_level=next_level,
            unlock_uw=False,
            unlock_plus=False,
        )
        return _replace_snapshot_uw_state(snapshot, uw_name=uw_name, rows=rows)

    return {
        "action_id": f"uw_track_upgrade::{uw_name}::{track_name}::{next_level}",
        "action_label": f"{uw_name}: {track_name} -> level {next_level}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "uw_track_ladders_v1",
    }


def _uw_plus_track_upgrade_action(
    *,
    uw_name: str,
    plus_track_name: str,
    next_level: int,
    stone_cost: float,
) -> Dict[str, Any]:
    def _apply_unlock(snapshot: AccountSnapshot) -> AccountSnapshot:
        rows = _patched_uw_rows(
            snapshot,
            uw_name=uw_name,
            track_name=plus_track_name,
            next_level=next_level,
            unlock_uw=False,
            unlock_plus=False,
            plus_track=True,
        )
        return _replace_snapshot_uw_state(snapshot, uw_name=uw_name, rows=rows)

    return {
        "action_id": f"uw_plus_track_upgrade::{uw_name}::{plus_track_name}::{next_level}",
        "action_label": f"{uw_name}+: {plus_track_name} -> level {next_level}",
        "eligible": True,
        "cost": float(stone_cost),
        "resource_unit": "stones",
        "apply_unlock": _apply_unlock,
        "notes": "uw_plus_ladders_v1",
    }




def _replace_snapshot_uw_state(snapshot: AccountSnapshot, *, uw_name: str, rows: List[List[str]]) -> AccountSnapshot:
    raw_sections = dict(snapshot.raw_sections)
    raw_sections["UWs"] = rows

    ultimate_weapons = dict(snapshot.ultimate_weapons)
    current = ultimate_weapons.get(uw_name)
    if current is not None:
        block = _find_uw_block(rows, uw_name)
        unlocked = block[2][1] if len(block[2]) > 1 else current.unlocked
        track_levels: List[str] = []
        for track_row in block[:3]:
            if len(track_row) > 4 and track_row[4].strip():
                track_levels.append(track_row[4].strip())
        ultimate_weapons[uw_name] = replace(current, unlocked=unlocked, track_levels=track_levels)

    return replace(snapshot, raw_sections=raw_sections, ultimate_weapons=ultimate_weapons)


def _find_uw_block(rows: List[List[str]], uw_name: str) -> List[List[str]]:
    for index in range(0, len(rows), 4):
        block = rows[index : index + 4]
        if len(block) < 4:
            continue
        name = block[0][0].strip() if block[0] else ""
        if name == uw_name:
            return block
    raise OptimizerDataError(f"UW row block not found: {uw_name}")


def _patched_uw_rows(
    snapshot: AccountSnapshot,
    *,
    uw_name: str,
    track_name: str | None,
    next_level: int | None,
    unlock_uw: bool,
    unlock_plus: bool,
    plus_track: bool = False,
) -> List[List[str]]:
    rows = [list(row) for row in snapshot.raw_sections.get("UWs", [])]
    block_index: int | None = None
    for index in range(0, len(rows), 4):
        block = rows[index : index + 4]
        if len(block) < 4:
            continue
        name = block[0][0].strip() if block[0] else ""
        if name == uw_name:
            block_index = index
            break
    if block_index is None:
        raise OptimizerDataError(f"UW row block not found: {uw_name}")

    block = rows[block_index : block_index + 4]
    if unlock_uw:
        _ensure_cell(block[2], 2)
        block[2][0] = "true"
        block[2][1] = "UW Unlocked"

    if unlock_plus:
        plus_row = block[3]
        _ensure_cell(plus_row, 5)
        if plus_row[3].strip().lower() != "locked":
            raise OptimizerDataError(f"UW+ already unlocked: {uw_name}")
        plus_row[3] = "0"
        plus_row[4] = "00 | unlocked"

    if track_name is not None and next_level is not None:
        track_row: List[str] | None = None
        search_rows = [block[3]] if plus_track else block[:3]
        for row in search_rows:
            _ensure_cell(row, 5)
            if row[2].strip() == track_name:
                track_row = row
                break
        if track_row is None:
            family = "UW+" if plus_track else "UW"
            raise OptimizerDataError(f"{family} track not found: {uw_name}:{track_name}")

        current_level = _parse_level_from_display(track_row[4])
        if current_level is None:
            raise OptimizerDataError(f"Cannot parse current level for {uw_name}:{track_name}")
        if current_level + 1 != next_level:
            raise OptimizerDataError(
                f"Invalid next level for {uw_name}:{track_name}. expected {current_level + 1}, got {next_level}"
            )
        track_row[4] = f"{next_level:02d} | patched_by_optimizer"

    rows[block_index : block_index + 4] = block
    return rows


def _ensure_cell(row: List[str], min_len: int) -> None:
    if len(row) < min_len:
        row.extend([""] * (min_len - len(row)))

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


def _load_uw_purchase_costs() -> Dict[str | int, Dict[int, int] | int]:
    path = Path("tables/uw_purchase_costs_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/uw_purchase_costs_v1.csv")
    uw_costs: Dict[int, int] = {}
    uw_plus_costs: Dict[int, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            uw_costs[int(row["uw_unlock_count"])] = int(row["uw_unlock_cost"])
            uw_plus_costs[int(row["uw_plus_unlock_count"])] = int(row["uw_plus_unlock_cost"])
    if not uw_costs or not uw_plus_costs:
        raise OptimizerDataError("uw_purchase_costs_v1.csv is empty.")
    data: Dict[str | int, Dict[int, int] | int] = dict(uw_costs)
    data["uw_plus"] = uw_plus_costs
    return data


def _load_uw_track_ladders() -> Dict[tuple[str, str, int], int]:
    path = Path("tables/uw_track_ladders_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/uw_track_ladders_v1.csv")
    values: Dict[tuple[str, str, int], int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cost = row.get("cost", "").strip()
            if not cost:
                continue
            key = (row["uw_name"], row["track_name"], int(row["level_index"]))
            values[key] = int(cost)
    if not values:
        raise OptimizerDataError("uw_track_ladders_v1.csv has no usable rows.")
    return values


def _load_uw_plus_ladders() -> Dict[tuple[str, str, int], int]:
    path = Path("tables/uw_plus_ladders_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/uw_plus_ladders_v1.csv")
    values: Dict[tuple[str, str, int], int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cost = row.get("cost", "").strip()
            if not cost:
                continue
            key = (row["uw_name"], row["plus_track_name"], int(row["level_index"]))
            values[key] = int(cost)
    if not values:
        raise OptimizerDataError("uw_plus_ladders_v1.csv has no usable rows.")
    return values


def _parse_uw_rows(snapshot: AccountSnapshot) -> Dict[str, Any]:
    rows = snapshot.raw_sections.get("UWs", [])
    uw_unlocked_count = 0
    uw_plus_unlocked_count = 0
    locked_uws: List[str] = []
    uw_plus_locked: List[str] = []
    uw_tracks: List[Dict[str, Any]] = []
    uw_plus_tracks: List[Dict[str, Any]] = []

    for i in range(0, len(rows), 4):
        block = rows[i : i + 4]
        if len(block) < 4:
            continue
        uw_name = block[0][0].strip() if block[0] else ""
        if not uw_name:
            continue

        is_unlocked = (block[2][0].strip().lower() == "true") if len(block[2]) > 0 else False
        if is_unlocked:
            uw_unlocked_count += 1
        else:
            locked_uws.append(uw_name)

        if is_unlocked:
            for track_row in block[:3]:
                if len(track_row) < 5:
                    continue
                track_name = track_row[2].strip()
                if not track_name:
                    continue
                current_level = _parse_level_from_display(track_row[4])
                if current_level is None:
                    continue
                uw_tracks.append(
                    {
                        "uw_name": uw_name,
                        "track_name": track_name,
                        "current_level": current_level,
                    }
                )

        plus_row = block[3]
        plus_track_name = plus_row[2].strip() if len(plus_row) > 2 else ""
        plus_current = plus_row[3].strip() if len(plus_row) > 3 else ""
        plus_display = plus_row[4].strip() if len(plus_row) > 4 else ""

        if plus_track_name and is_unlocked:
            if plus_current.lower() == "locked":
                uw_plus_locked.append(uw_name)
            else:
                uw_plus_unlocked_count += 1
                plus_level = _parse_level_from_display(plus_display)
                if plus_level is not None:
                    uw_plus_tracks.append(
                        {
                            "uw_name": uw_name,
                            "plus_track_name": plus_track_name,
                            "current_level": plus_level,
                        }
                    )

    return {
        "uw_unlocked_count": uw_unlocked_count,
        "uw_plus_unlocked_count": uw_plus_unlocked_count,
        "locked_uws": locked_uws,
        "uw_plus_locked": uw_plus_locked,
        "uw_tracks": uw_tracks,
        "uw_plus_tracks": uw_plus_tracks,
    }


def _parse_level_from_display(value: str) -> int | None:
    match = re.match(r"\s*(\d+)", value or "")
    if match is None:
        return None
    return int(match.group(1))


def _load_assist_efficiency_costs() -> Dict[int, int]:
    path = Path("tables/assist_efficiency_upgrade_costs_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/assist_efficiency_upgrade_costs_v1.csv")
    values: Dict[int, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values[int(row["assist_level"])] = int(row["stone_cost"])
    if not values:
        raise OptimizerDataError("assist_efficiency_upgrade_costs_v1.csv is empty.")
    return values


def _load_assist_slot_unlock_cost() -> int:
    path = Path("tables/assist_slot_unlock_costs_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/assist_slot_unlock_costs_v1.csv")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise OptimizerDataError("assist_slot_unlock_costs_v1.csv is empty.")
    return int(rows[0]["stone_cost"])


def _load_assist_unique_rarity_costs() -> Dict[tuple[str, str], int]:
    path = Path("tables/assist_unique_rarity_upgrade_costs_v1.csv")
    if not path.exists():
        raise OptimizerDataError("Missing required table: tables/assist_unique_rarity_upgrade_costs_v1.csv")
    values: Dict[tuple[str, str], int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values[(row["from_rarity"], row["to_rarity"])] = int(row["stone_cost"])
    if not values:
        raise OptimizerDataError("assist_unique_rarity_upgrade_costs_v1.csv is empty.")
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
