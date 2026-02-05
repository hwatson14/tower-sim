from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from tower_sim.util.account_snapshot import (
    AccountSnapshot,
    CardSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSnapshot,
    ModuleSubstat,
    ModuleSystemState,
    TableSnapshot,
    UltimateWeaponSnapshot,
    WorkshopEntrySnapshot,
)


@dataclass(frozen=True)
class SnapshotPayload:
    snapshot: Dict[str, Any]


def load_account_snapshot(payload: Dict[str, Any]) -> AccountSnapshot:
    snapshot_data = _extract_snapshot(payload)
    return _load_snapshot(snapshot_data)


def _extract_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "snapshot" in payload and isinstance(payload["snapshot"], dict):
        return payload["snapshot"]
    return payload


def _load_snapshot(data: Dict[str, Any]) -> AccountSnapshot:
    _require_keys(
        data,
        required={
            "ids_path",
            "labs",
            "workshop",
            "workshop_enhancements",
            "ultimate_weapons",
            "relics",
            "vault",
            "bots",
            "guardians",
            "player_meta",
            "cards_inventory",
            "card_presets",
            "module_system_state",
            "module_presets",
            "modules_inventory",
            "allocation_levels",
            "inferred_shard_budgets",
            "default_preset",
            "raw_sections",
        },
    )
    return AccountSnapshot(
        ids_path=Path(_require_str(data, "ids_path")),
        labs=_require_dict_of_optional_ints(data, "labs"),
        workshop=_parse_workshop(_require_dict(data, "workshop")),
        workshop_enhancements=_parse_table(_require_dict(data, "workshop_enhancements")),
        ultimate_weapons=_parse_ultimate_weapons(_require_dict(data, "ultimate_weapons")),
        relics=_require_dict_of_optional_ints(data, "relics"),
        vault=_require_dict_of_optional_ints(data, "vault"),
        bots=_require_list_of_str(data, "bots"),
        guardians=_parse_table(_require_dict(data, "guardians")),
        player_meta=_require_dict_of_optional_str(data, "player_meta"),
        cards_inventory=_parse_cards(_require_dict(data, "cards_inventory")),
        card_presets=_parse_card_presets(_require_dict(data, "card_presets")),
        module_system_state=_parse_module_system_state(_require_dict(data, "module_system_state")),
        module_presets=_parse_module_presets(_require_dict(data, "module_presets")),
        modules_inventory=_parse_modules(_require_dict(data, "modules_inventory")),
        allocation_levels=_parse_allocations(_require_dict(data, "allocation_levels")),
        inferred_shard_budgets=_require_dict_of_ints(data, "inferred_shard_budgets"),
        default_preset=_require_str(data, "default_preset"),
        raw_sections=_parse_raw_sections(_require_dict(data, "raw_sections")),
    )


def _parse_table(data: Dict[str, Any]) -> TableSnapshot:
    _require_keys(data, required={"header", "rows"})
    header = _require_list_of_str(data, "header")
    rows = _require_list_of_row(data, "rows")
    return TableSnapshot(header=header, rows=rows)


def _parse_workshop(data: Dict[str, Any]) -> Dict[str, WorkshopEntrySnapshot]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"workshop[{key}]")
        end_level = _require_optional_int(value, "end_level") if "end_level" in value else _require_optional_int(value, "max_level")
        parsed[str(key)] = WorkshopEntrySnapshot(
            name=_require_str(value, "name"),
            coin_level=_require_optional_int(value, "coin_level"),
            end_level=end_level,
            max_level=_require_optional_int(value, "max_level"),
            unlocked=_require_optional_str(value, "unlocked"),
            category=_require_optional_str(value, "category"),
        )
    return parsed


def _parse_ultimate_weapons(data: Dict[str, Any]) -> Dict[str, UltimateWeaponSnapshot]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"ultimate_weapons[{key}]")
        parsed[str(key)] = UltimateWeaponSnapshot(
            name=_require_str(value, "name"),
            unlocked=_require_optional_str(value, "unlocked"),
            track_levels=_require_list_of_str(value, "track_levels"),
        )
    return parsed


def _parse_cards(data: Dict[str, Any]) -> Dict[str, CardSnapshot]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"cards_inventory[{key}]")
        parsed[str(key)] = CardSnapshot(
            name=_require_str(value, "name"),
            level=_require_optional_int(value, "level"),
            mastery_unlocked=_require_bool(value, "mastery_unlocked"),
            mastery_lab_level=_require_optional_int(value, "mastery_lab_level"),
        )
    return parsed


def _parse_card_presets(data: Dict[str, Any]) -> Dict[str, List[str]]:
    parsed: Dict[str, List[str]] = {}
    for key, value in data.items():
        _ensure_list(value, f"card_presets[{key}]")
        parsed[str(key)] = [str(item) for item in value]
    return parsed


def _parse_modules(data: Dict[str, Any]) -> Dict[str, ModuleSnapshot]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"modules_inventory[{key}]")
        substats = []
        for idx, substat in enumerate(value.get("substats", [])):
            _ensure_dict(substat, f"modules_inventory[{key}].substats[{idx}]")
            substats.append(
                ModuleSubstat(
                    stat_name=_require_str(substat, "stat_name"),
                    rarity=_require_optional_str(substat, "rarity"),
                    value_display=_require_optional_str(substat, "value_display"),
                    value_num=_require_optional_float(substat, "value_num"),
                )
            )
        parsed[str(key)] = ModuleSnapshot(
            name=_require_str(value, "name"),
            slot_type=_require_str(value, "slot_type"),
            rarity=_require_optional_str(value, "rarity"),
            level=_require_optional_int(value, "level"),
            stat=_require_optional_str(value, "stat"),
            substats=substats,
        )
    return parsed


def _parse_module_system_state(data: Dict[str, Any]) -> Dict[str, ModuleSystemState]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"module_system_state[{key}]")
        parsed[str(key)] = ModuleSystemState(
            slot_type=_require_str(value, "slot_type"),
            assist_unlocked=_require_bool(value, "assist_unlocked"),
            assist_level=_require_int(value, "assist_level"),
            rarity_cap=_require_optional_str(value, "rarity_cap"),
            multiplier_cap=_require_optional_float(value, "multiplier_cap"),
            substat_cap=_require_optional_float(value, "substat_cap"),
        )
    return parsed


def _parse_module_presets(data: Dict[str, Any]) -> Dict[str, Dict[str, ModulePresetSelection]]:
    parsed: Dict[str, Dict[str, ModulePresetSelection]] = {}
    for key, value in data.items():
        _ensure_dict(value, f"module_presets[{key}]")
        inner: Dict[str, ModulePresetSelection] = {}
        for preset_name, preset in value.items():
            _ensure_dict(preset, f"module_presets[{key}][{preset_name}]")
            inner[str(preset_name)] = ModulePresetSelection(
                primary=_require_optional_str(preset, "primary"),
                assist=_require_optional_str(preset, "assist"),
            )
        parsed[str(key)] = inner
    return parsed


def _parse_allocations(data: Dict[str, Any]) -> Dict[str, ModuleAllocation]:
    parsed = {}
    for key, value in data.items():
        _ensure_dict(value, f"allocation_levels[{key}]")
        parsed[str(key)] = ModuleAllocation(
            primary_level=_require_int(value, "primary_level"),
            assist_level=_require_int(value, "assist_level"),
        )
    return parsed


def _parse_raw_sections(data: Dict[str, Any]) -> Dict[str, List[List[str]]]:
    parsed: Dict[str, List[List[str]]] = {}
    for key, value in data.items():
        _ensure_list(value, f"raw_sections[{key}]")
        rows: List[List[str]] = []
        for idx, row in enumerate(value):
            _ensure_list(row, f"raw_sections[{key}][{idx}]")
            rows.append([str(cell) for cell in row])
        parsed[str(key)] = rows
    return parsed


def _require_keys(data: Dict[str, Any], *, required: set[str]) -> None:
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required snapshot fields: {sorted(missing)}")


def _require_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = data.get(key)
    _ensure_dict(value, key)
    return value


def _ensure_dict(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping.")


def _ensure_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")


def _require_str(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _require_optional_str(data: Dict[str, Any], key: str) -> Optional[str]:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null.")
    return value


def _require_int(data: Dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer.")
    return value


def _require_optional_int(data: Dict[str, Any], key: str) -> Optional[int]:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer or null.")
    return value


def _require_optional_float(data: Dict[str, Any], key: str) -> Optional[float]:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number or null.")
    return float(value)


def _require_bool(data: Dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean.")
    return value


def _require_list_of_str(data: Dict[str, Any], key: str) -> List[str]:
    value = data.get(key)
    _ensure_list(value, key)
    return [str(item) for item in value]


def _require_list_of_row(data: Dict[str, Any], key: str) -> List[List[str]]:
    value = data.get(key)
    _ensure_list(value, key)
    rows: List[List[str]] = []
    for idx, row in enumerate(value):
        _ensure_list(row, f"{key}[{idx}]")
        rows.append([str(cell) for cell in row])
    return rows


def _require_dict_of_optional_ints(data: Dict[str, Any], key: str) -> Dict[str, Optional[int]]:
    value = data.get(key)
    _ensure_dict(value, key)
    parsed: Dict[str, Optional[int]] = {}
    for k, v in value.items():
        if v is None:
            parsed[str(k)] = None
        elif isinstance(v, int):
            parsed[str(k)] = v
        else:
            raise ValueError(f"{key}[{k}] must be an integer or null.")
    return parsed


def _require_dict_of_ints(data: Dict[str, Any], key: str) -> Dict[str, int]:
    value = data.get(key)
    _ensure_dict(value, key)
    parsed: Dict[str, int] = {}
    for k, v in value.items():
        if not isinstance(v, int):
            raise ValueError(f"{key}[{k}] must be an integer.")
        parsed[str(k)] = v
    return parsed


def _require_dict_of_optional_str(data: Dict[str, Any], key: str) -> Dict[str, Optional[str]]:
    value = data.get(key)
    _ensure_dict(value, key)
    parsed: Dict[str, Optional[str]] = {}
    for k, v in value.items():
        if v is None:
            parsed[str(k)] = None
        elif isinstance(v, str):
            parsed[str(k)] = v
        else:
            raise ValueError(f"{key}[{k}] must be a string or null.")
    return parsed

