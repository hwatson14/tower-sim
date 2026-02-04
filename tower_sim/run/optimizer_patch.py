from __future__ import annotations

from typing import Any, Dict, List

MODULE_SLOTS = {"primary", "assist"}


def validate_snapshot_patch(patch: Dict[str, Any]) -> None:
    _require_type(patch, "snapshot_patch")
    _require_only_keys(
        patch,
        {
            "type",
            "labs",
            "workshop",
            "stones",
            "coins",
            "lab_time",
        },
    )
    _validate_stat_deltas(patch.get("labs", []), "labs")
    _validate_stat_deltas(patch.get("workshop", []), "workshop")
    _validate_resource_deltas(patch.get("stones", []), "stones")
    _validate_resource_deltas(patch.get("coins", []), "coins")
    _validate_time_deltas(patch.get("lab_time", []), "lab_time")


def validate_loadout_patch(patch: Dict[str, Any]) -> None:
    _require_type(patch, "loadout_patch")
    _require_only_keys(patch, {"type", "cards", "modules"})
    _validate_card_actions(patch.get("cards", []))
    _validate_module_actions(patch.get("modules", []))


def _require_type(patch: Dict[str, Any], expected: str) -> None:
    if patch.get("type") != expected:
        raise ValueError(f"Patch type must be {expected!r}.")


def _require_only_keys(patch: Dict[str, Any], allowed: set[str]) -> None:
    unknown = set(patch.keys()) - allowed
    if unknown:
        raise ValueError(f"Unknown patch keys: {sorted(unknown)}")


def _ensure_list(value: Any, label: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{idx}] must be a mapping.")
    return value


def _validate_stat_deltas(entries: Any, label: str) -> None:
    for idx, entry in enumerate(_ensure_list(entries, label)):
        _require_only_keys(entry, {"stat_id", "delta_levels"})
        _require_str(entry, "stat_id", f"{label}[{idx}].stat_id")
        _require_int(entry, "delta_levels", f"{label}[{idx}].delta_levels")


def _validate_resource_deltas(entries: Any, label: str) -> None:
    for idx, entry in enumerate(_ensure_list(entries, label)):
        _require_only_keys(entry, {"target", "id", "stat_id", "delta_levels"})
        _require_str(entry, "target", f"{label}[{idx}].target")
        if "id" in entry:
            _require_str(entry, "id", f"{label}[{idx}].id")
        if "stat_id" in entry:
            _require_str(entry, "stat_id", f"{label}[{idx}].stat_id")
        _require_int(entry, "delta_levels", f"{label}[{idx}].delta_levels")


def _validate_time_deltas(entries: Any, label: str) -> None:
    for idx, entry in enumerate(_ensure_list(entries, label)):
        _require_only_keys(entry, {"stat_id", "delta_seconds"})
        _require_str(entry, "stat_id", f"{label}[{idx}].stat_id")
        _require_int(entry, "delta_seconds", f"{label}[{idx}].delta_seconds")


def _validate_card_actions(entries: Any) -> None:
    for idx, entry in enumerate(_ensure_list(entries, "cards")):
        action = entry.get("action")
        if action == "swap":
            _require_only_keys(entry, {"action", "from", "to"})
            _require_str(entry, "from", f"cards[{idx}].from")
            _require_str(entry, "to", f"cards[{idx}].to")
        elif action == "set_level":
            _require_only_keys(entry, {"action", "card_id", "level"})
            _require_str(entry, "card_id", f"cards[{idx}].card_id")
            _require_int(entry, "level", f"cards[{idx}].level")
        else:
            raise ValueError(f"cards[{idx}].action must be 'swap' or 'set_level'.")


def _validate_module_actions(entries: Any) -> None:
    for idx, entry in enumerate(_ensure_list(entries, "modules")):
        action = entry.get("action")
        if action != "assign":
            raise ValueError(f"modules[{idx}].action must be 'assign'.")
        _require_only_keys(entry, {"action", "slot", "module_id"})
        slot = _require_str(entry, "slot", f"modules[{idx}].slot")
        if slot not in MODULE_SLOTS:
            raise ValueError(f"modules[{idx}].slot must be one of {sorted(MODULE_SLOTS)}.")
        _require_str(entry, "module_id", f"modules[{idx}].module_id")


def _require_str(entry: Dict[str, Any], key: str, label: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string.")
    return value


def _require_int(entry: Dict[str, Any], key: str, label: str) -> int:
    value = entry.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{label} must be an integer.")
    return value
