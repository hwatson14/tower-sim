from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from tower_sim.libs.module_shards import shards_to_reach_level
from tower_sim.registry.naming_contract import validate_account_snapshot_naming
from tower_sim.libs.bots_lib import bots_from_table
from tower_sim.util.account_snapshot import (
    AccountSnapshot,
    CardSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSnapshot,
    ModuleSubstat,
    ModuleSystemState,
    PRESET_NAMES,
    ResolvedLoadout,
    SLOT_TYPES,
    TableSnapshot,
    UltimateWeaponSnapshot,
    UwPlusTrackSnapshot,
    WorkshopEntrySnapshot,
)
from tower_sim.util.ids_raw import IdsRaw

_MODULE_PRESET_LABELS = {
    "Farming": "Farming",
    "Tourney": "Tourney",
    "Testing": "Testing",
    "Placeholder 4th preset": "Preset 4",
    "Placeholder 5th preset": "Preset 5",
}
_CARD_PRESET_ALIASES = {
    "Farming": "Farming",
    "Tourney": "Tourney",
    "Testing": "Testing",
    "Preset 3": "Testing",
    "Preset 4": "Preset 4",
    "Preset 5": "Preset 5",
}
_MODULE_KNOWN_LABELS = {
    "Assist Slot",
    "Primary Slot",
    "Farming",
    "Tourney",
    "Testing",
    "Placeholder 4th preset",
    "Placeholder 5th preset",
    "Rarity",
    "Rarity Cap",
    "Multiplier Cap",
    "Substat Cap",
    "Level",
    "Stat",
}


def compile_account_snapshot(ids_raw: IdsRaw, *, default_preset: str = "Farming") -> AccountSnapshot:
    raw_sections = ids_raw.raw_sections
    labs = _parse_labs(raw_sections.get("Labs", []))
    workshop = _parse_workshop(raw_sections.get("WS", []), default_preset=default_preset)
    workshop_enhancements = _parse_table(raw_sections.get("WS+", []))
    ultimate_weapons = _parse_ultimate_weapons(raw_sections.get("UWs", []))
    uw_plus_tracks = _parse_uw_plus_tracks(raw_sections.get("UWs", []))
    relics = _parse_key_value_float(raw_sections.get("Relics", []))
    vault = _parse_key_value_int(raw_sections.get("Vault", []))
    bots, bot_upgrades = _parse_bots(raw_sections.get("Bots", []))
    guardians = _parse_table(raw_sections.get("Guardians", []))
    player_meta = _parse_key_value_str(raw_sections.get("Player & Stuff", []))
    cards_inventory, card_presets = _parse_cards(raw_sections.get("Cards", []), labs)

    module_system_state, module_presets, modules_inventory = _parse_modules(
        raw_sections.get("Modules", [])
    )

    if default_preset not in PRESET_NAMES:
        raise ValueError(
            f"Default preset must be one of {PRESET_NAMES}, got {default_preset!r}."
        )

    allocation_levels, inferred_shard_budgets = _resolve_module_allocations(
        module_presets,
        modules_inventory,
        module_system_state,
        default_preset,
    )

    snapshot = AccountSnapshot(
        ids_path=ids_raw.ids_path,
        labs=labs,
        workshop=workshop,
        workshop_enhancements=workshop_enhancements,
        ultimate_weapons=ultimate_weapons,
        relics=relics,
        vault=vault,
        bots=bots,
        bot_upgrades=bot_upgrades,
        guardians=guardians,
        player_meta=player_meta,
        cards_inventory=cards_inventory,
        card_presets=card_presets,
        module_system_state=module_system_state,
        module_presets=module_presets,
        modules_inventory=modules_inventory,
        allocation_levels=allocation_levels,
        inferred_shard_budgets=inferred_shard_budgets,
        default_preset=default_preset,
        raw_sections=raw_sections,
        uw_plus_tracks=uw_plus_tracks,
    )

    naming_errors = validate_account_snapshot_naming(snapshot)
    if naming_errors:
        raise ValueError(
            "Naming contract violations in IDS snapshot: "
            + ", ".join(naming_errors[:10])
            + (" ..." if len(naming_errors) > 10 else "")
        )

    return snapshot


def snapshot_as_dict(snapshot: AccountSnapshot) -> Dict[str, object]:
    return asdict(snapshot)


def resolve_loadout(
    snapshot: AccountSnapshot,
    preset_name: str | None = None,
) -> ResolvedLoadout:
    resolved_preset = preset_name or snapshot.default_preset
    if resolved_preset not in PRESET_NAMES:
        raise ValueError(
            f"Preset must be one of {PRESET_NAMES}, got {resolved_preset!r}."
        )
    if resolved_preset not in snapshot.card_presets:
        raise ValueError(f"Missing card preset {resolved_preset}.")
    if resolved_preset not in snapshot.module_presets:
        raise ValueError(f"Missing module preset {resolved_preset}.")
    allocation_levels, inferred_shard_budgets = _resolve_module_allocations(
        snapshot.module_presets,
        snapshot.modules_inventory,
        snapshot.module_system_state,
        resolved_preset,
    )
    return ResolvedLoadout(
        preset_name=resolved_preset,
        card_names=snapshot.card_presets[resolved_preset],
        modules_by_slot=snapshot.module_presets[resolved_preset],
        allocation_levels=allocation_levels,
        inferred_shard_budgets=inferred_shard_budgets,
    )


def _parse_labs(rows: List[List[str]]) -> Dict[str, Optional[int]]:
    labs: Dict[str, Optional[int]] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        value = _parse_optional_int(_safe_cell(row, 1))
        labs[name] = value
    return labs


def _parse_workshop(
    rows: List[List[str]], *, default_preset: str
) -> Dict[str, WorkshopEntrySnapshot]:
    level_indices = _workshop_level_indices(default_preset)
    entries: Dict[str, WorkshopEntrySnapshot] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name or name == "Workshop Upgrade":
            continue
        coin_level = _parse_optional_int(_safe_cell(row, level_indices[0]))
        end_level = _parse_optional_int(_safe_cell(row, level_indices[1]))
        max_level = _parse_optional_int(_safe_cell(row, 11))
        entries[name] = WorkshopEntrySnapshot(
            name=name,
            unlocked=_optional_str(_safe_cell(row, 1)),
            coin_level=coin_level,
            end_level=end_level,
            max_level=max_level,
            category=_optional_str(_safe_cell(row, 5)),
        )
    return entries


def _workshop_level_indices(default_preset: str) -> Tuple[int, int]:
    indices_by_preset: Dict[str, Tuple[int, int]] = {
        "Farming": (1, 2),
        "Tourney": (3, 4),
        "Testing": (5, 6),
        "Preset 4": (7, 8),
        "Preset 5": (9, 10),
    }
    if default_preset not in indices_by_preset:
        raise ValueError(
            f"Default preset must be one of {PRESET_NAMES}, got {default_preset!r}."
        )
    return indices_by_preset[default_preset]


def _parse_ultimate_weapons(rows: List[List[str]]) -> Dict[str, UltimateWeaponSnapshot]:
    entries: Dict[str, UltimateWeaponSnapshot] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name or name == "UW+":
            continue
        track_levels = [cell.strip() for cell in row[2:] if cell.strip()]
        entries[name] = UltimateWeaponSnapshot(
            name=name,
            unlocked=_optional_str(_safe_cell(row, 1)),
            track_levels=track_levels,
        )
    return entries




def _parse_uw_plus_tracks(rows: List[List[str]]) -> Dict[str, UwPlusTrackSnapshot]:
    tracks: Dict[str, UwPlusTrackSnapshot] = {}
    for i in range(0, len(rows), 4):
        block = rows[i : i + 4]
        if len(block) < 4:
            continue
        uw_name = _safe_cell(block[0], 0).strip()
        plus_track_name = _safe_cell(block[3], 2).strip()
        if not uw_name or not plus_track_name:
            continue
        current_state = _safe_cell(block[3], 3).strip()
        display_token = _safe_cell(block[3], 4).strip()
        key = f"{uw_name}::{plus_track_name}"
        tracks[key] = UwPlusTrackSnapshot(
            uw_name=uw_name,
            plus_track_name=plus_track_name,
            current_state=current_state,
            display_token=display_token,
        )
    return tracks

def _parse_key_value_int(rows: List[List[str]]) -> Dict[str, Optional[int]]:
    values: Dict[str, Optional[int]] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        values[name] = _parse_optional_int_relaxed(_safe_cell(row, 1))
    return values


def _parse_key_value_float(rows: List[List[str]]) -> Dict[str, Optional[float]]:
    values: Dict[str, Optional[float]] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        values[name] = _parse_optional_float(_safe_cell(row, 1))
    return values


def _parse_key_value_str(rows: List[List[str]]) -> Dict[str, Optional[str]]:
    values: Dict[str, Optional[str]] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        values[name] = _optional_str(_safe_cell(row, 1))
    return values


def _parse_bots(rows: List[List[str]]) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    bots: List[str] = []
    bot_values: Dict[str, Dict[str, float]] = {}
    current_bot: Optional[str] = None
    for row in rows:
        name = row[0].strip() if row else ""
        attr = row[2].strip() if len(row) > 2 else ""
        raw_value = row[3].strip() if len(row) > 3 else ""

        if name and name not in {"true", "false"}:
            current_bot = name
            bots.append(name)
        if current_bot is None or not attr or raw_value == "":
            continue
        try:
            bot_values.setdefault(current_bot, {})[attr] = float(raw_value)
        except ValueError:
            continue

    table = bots_from_table()
    bot_upgrades: Dict[str, Dict[str, int]] = {}
    for bot, attrs in bot_values.items():
        if bot not in table:
            continue
        for attr, value in attrs.items():
            if attr not in table[bot]:
                continue
            levels = table[bot][attr].values
            matched_level: Optional[int] = None
            for level, table_value in levels.items():
                if abs(table_value - value) <= 1e-9:
                    matched_level = int(level)
                    break
            if matched_level is None:
                raise ValueError(
                    f"Unable to map bot value to canonical level for {bot} {attr}: {value}"
                )
            bot_upgrades.setdefault(bot, {})[attr] = matched_level

    return bots, bot_upgrades


def _parse_table(rows: List[List[str]]) -> TableSnapshot:
    if not rows:
        return TableSnapshot(header=[], rows=[])
    header = [cell.strip() if cell.strip() else f"Column {idx + 1}" for idx, cell in enumerate(rows[0])]
    body = []
    for row in rows[1:]:
        if not _row_has_data(row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        body.append([cell.strip() for cell in padded[: len(header)]])
    return TableSnapshot(header=header, rows=body)


def _parse_cards(
    rows: List[List[str]],
    labs: Dict[str, Optional[int]],
) -> Tuple[Dict[str, CardSnapshot], Dict[str, List[str]]]:
    if not rows:
        raise ValueError("Cards section is empty.")
    header_row = rows[0]
    preset_headers = [cell.strip() for cell in header_row[3:]]
    preset_columns: Dict[int, str] = {}
    for idx, header in enumerate(preset_headers, start=3):
        if not header:
            continue
        normalized = _CARD_PRESET_ALIASES.get(header)
        if normalized is None:
            continue
        preset_columns[idx] = normalized
    missing_presets = [name for name in PRESET_NAMES if name not in preset_columns.values()]
    if missing_presets:
        raise ValueError(f"Missing card presets: {missing_presets}")

    inventory: Dict[str, CardSnapshot] = {}
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        mastery_flag = _parse_bool(_safe_cell(row, 2))
        mastery_lab_level = labs.get(f"{name} Mastery")
        inventory[name] = CardSnapshot(
            name=name,
            level=_parse_optional_int_relaxed(_safe_cell(row, 1)),
            mastery_unlocked=mastery_flag,
            mastery_lab_level=mastery_lab_level,
        )

    presets: Dict[str, List[str]] = {preset: [] for preset in PRESET_NAMES}
    for row in rows[1:]:
        for idx, preset_name in preset_columns.items():
            card_name = _safe_cell(row, idx).strip()
            if card_name:
                presets[preset_name].append(card_name)

    for preset_name, cards in presets.items():
        missing_cards = [name for name in cards if name not in inventory]
        if missing_cards:
            raise ValueError(
                f"Preset {preset_name} references missing cards: {missing_cards}"
            )
    return inventory, presets


def _parse_modules(
    rows: List[List[str]],
) -> Tuple[
    Dict[str, ModuleSystemState],
    Dict[str, Dict[str, ModulePresetSelection]],
    Dict[str, ModuleSnapshot],
]:
    module_system_state: Dict[str, ModuleSystemState] = {}
    module_presets: Dict[str, Dict[str, ModulePresetSelection]] = {
        preset: {} for preset in PRESET_NAMES
    }
    modules_inventory: Dict[str, ModuleSnapshot] = {}

    for slot_index, slot_type in enumerate(SLOT_TYPES):
        slot_rows = _slice_slot_rows(rows, slot_index)
        module_system_state[slot_type] = _parse_module_system_state(slot_rows, slot_type)
        slot_presets = _parse_module_presets(slot_rows, slot_type)
        for preset_name, selection in slot_presets.items():
            module_presets[preset_name][slot_type] = selection

        slot_inventory = _parse_module_inventory(slot_rows, slot_type)
        for name, entry in slot_inventory.items():
            if name in modules_inventory:
                suffix_name = f"{name} ({slot_type})"
                entry = ModuleSnapshot(
                    name=suffix_name,
                    slot_type=entry.slot_type,
                    rarity=entry.rarity,
                    level=entry.level,
                    stat=entry.stat,
                    substats=entry.substats,
                )
                modules_inventory[suffix_name] = entry
            else:
                modules_inventory[name] = entry

    for preset_name in PRESET_NAMES:
        if preset_name not in module_presets:
            raise ValueError(f"Missing module preset {preset_name}.")
        if set(module_presets[preset_name].keys()) != set(SLOT_TYPES):
            raise ValueError(
                f"Preset {preset_name} missing slots: "
                f"{sorted(set(SLOT_TYPES) - set(module_presets[preset_name].keys()))}"
            )

    for preset_name, slots in module_presets.items():
        for slot_type, selection in slots.items():
            if selection.primary and selection.primary not in modules_inventory:
                raise ValueError(
                    f"Preset {preset_name} {slot_type} references missing module "
                    f"{selection.primary!r}."
                )
            if selection.assist and selection.assist not in modules_inventory:
                raise ValueError(
                    f"Preset {preset_name} {slot_type} references missing assist "
                    f"{selection.assist!r}."
                )

    return module_system_state, module_presets, modules_inventory


def _slice_slot_rows(rows: List[List[str]], slot_index: int) -> List[List[str]]:
    base = slot_index * 5
    slot_rows = []
    for row in rows:
        chunk = row[base : base + 5]
        padded = chunk + [""] * max(0, 5 - len(chunk))
        slot_rows.append(padded)
    return slot_rows


def _parse_module_system_state(slot_rows: List[List[str]], slot_type: str) -> ModuleSystemState:
    assist_row = _find_row(slot_rows, "Assist Slot", match_bool=True)
    if assist_row is None:
        raise ValueError(f"Missing assist slot status for {slot_type}.")
    assist_unlocked = _parse_bool(_safe_cell(assist_row, 1))
    assist_level = _parse_required_int(_safe_cell(assist_row, 2), f"{slot_type} assist level")
    rarity_cap = _find_value(slot_rows, "Rarity Cap")
    multiplier_cap = _parse_optional_float(_find_value(slot_rows, "Multiplier Cap"))
    substat_cap = _parse_optional_float(_find_value(slot_rows, "Substat Cap"))
    return ModuleSystemState(
        slot_type=slot_type,
        assist_unlocked=assist_unlocked,
        assist_level=assist_level,
        rarity_cap=rarity_cap,
        multiplier_cap=multiplier_cap,
        substat_cap=substat_cap,
    )


def _parse_module_presets(
    slot_rows: List[List[str]],
    slot_type: str,
) -> Dict[str, ModulePresetSelection]:
    presets: Dict[str, ModulePresetSelection] = {}
    preset_indices = []
    for idx, row in enumerate(slot_rows):
        label = row[0].strip()
        if label in _MODULE_PRESET_LABELS:
            preset_indices.append((idx, _MODULE_PRESET_LABELS[label]))
    inventory_start = _find_inventory_start(slot_rows)
    for index, preset_name in preset_indices:
        block_end = _find_block_end(index, preset_indices, inventory_start, len(slot_rows))
        primary = _find_value_in_block(slot_rows[index + 1 : block_end], "Primary Slot")
        assist = _find_value_in_block(slot_rows[index + 1 : block_end], "Assist Slot")
        presets[preset_name] = ModulePresetSelection(primary=primary, assist=assist)
    missing_presets = [name for name in PRESET_NAMES if name not in presets]
    if missing_presets:
        raise ValueError(f"Missing module presets: {missing_presets}")
    return presets


def _parse_module_inventory(
    slot_rows: List[List[str]],
    slot_type: str,
) -> Dict[str, ModuleSnapshot]:
    inventory: Dict[str, ModuleSnapshot] = {}
    idx = 0
    while idx < len(slot_rows):
        row = slot_rows[idx]
        name = row[0].strip()
        if not name or name in _MODULE_KNOWN_LABELS:
            idx += 1
            continue
        if idx + 1 >= len(slot_rows) or slot_rows[idx + 1][0].strip() != "Rarity":
            idx += 1
            continue
        if idx + 2 >= len(slot_rows):
            raise ValueError(f"Missing module details for {name}.")
        data_row = slot_rows[idx + 2]
        rarity = _optional_str(_safe_cell(data_row, 0))
        level = _parse_optional_int(_safe_cell(data_row, 1))
        stat = _optional_str(_safe_cell(data_row, 2))
        substats: List[ModuleSubstat] = []
        scan = idx + 3
        while scan < len(slot_rows):
            candidate = slot_rows[scan]
            if _is_module_name_start(slot_rows, scan) or candidate[0].strip() in _MODULE_KNOWN_LABELS:
                break
            if not _row_has_data(candidate):
                scan += 1
                if scan < len(slot_rows) and _is_module_name_start(slot_rows, scan):
                    break
                continue
            substats.append(
                ModuleSubstat(
                    stat_name=candidate[0].strip(),
                    rarity=_optional_str(_safe_cell(candidate, 1)),
                    value_display=_optional_str(_safe_cell(candidate, 2)),
                    value_num=_parse_optional_float(_safe_cell(candidate, 3)),
                )
            )
            scan += 1
        inventory[name] = ModuleSnapshot(
            name=name,
            slot_type=slot_type,
            rarity=rarity,
            level=level,
            stat=stat,
            substats=substats,
        )
        idx = scan
    return inventory


def _resolve_module_allocations(
    module_presets: Dict[str, Dict[str, ModulePresetSelection]],
    modules_inventory: Dict[str, ModuleSnapshot],
    module_system_state: Dict[str, ModuleSystemState],
    preset_name: str,
) -> Tuple[Dict[str, ModuleAllocation], Dict[str, int]]:
    allocations: Dict[str, ModuleAllocation] = {}
    budgets: Dict[str, int] = {}
    preset = module_presets[preset_name]
    for slot_type in SLOT_TYPES:
        selection = preset[slot_type]
        if selection.primary is None:
            raise ValueError(f"Missing primary module for {preset_name} {slot_type}.")
        module = modules_inventory.get(selection.primary)
        if module is None:
            raise ValueError(
                f"Missing module {selection.primary!r} for {preset_name} {slot_type}."
            )
        if module.level is None:
            raise ValueError(f"Missing module level for {selection.primary!r}.")
        assist_level = module_system_state[slot_type].assist_level
        allocations[slot_type] = ModuleAllocation(
            primary_level=module.level,
            assist_level=assist_level,
        )
        budgets[slot_type] = shards_to_reach_level(module.level) + shards_to_reach_level(
            assist_level
        )
    return allocations, budgets


def _parse_optional_int(value: str) -> Optional[int]:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == "":
        return None
    try:
        return int(float(cleaned))
    except ValueError as exc:  # noqa: BLE001
        raise ValueError(f"Expected integer, got {value!r}.") from exc


def _parse_optional_int_relaxed(value: str) -> Optional[int]:
    try:
        return _parse_optional_int(value)
    except ValueError:
        return None


def _parse_required_int(value: str, label: str) -> int:
    parsed = _parse_optional_int(value)
    if parsed is None:
        raise ValueError(f"Missing required integer for {label}.")
    return parsed


def _parse_optional_float(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_bool(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned in {"true", "false"}:
        return cleaned == "true"
    if cleaned == "":
        return False
    raise ValueError(f"Expected boolean flag, got {value!r}.")


def _safe_cell(row: List[str], index: int) -> str:
    if index >= len(row):
        return ""
    return row[index]


def _optional_str(value: str) -> Optional[str]:
    cleaned = value.strip()
    return cleaned if cleaned else None


def _row_has_data(row: List[str]) -> bool:
    return any(cell.strip() for cell in row)


def _find_row(
    rows: List[List[str]],
    label: str,
    *,
    match_bool: bool = False,
) -> Optional[List[str]]:
    for row in rows:
        if row and row[0].strip() == label:
            if match_bool:
                flag = _safe_cell(row, 1).strip().lower()
                if flag in {"true", "false"}:
                    return row
                continue
            return row
    return None


def _find_value(rows: List[List[str]], label: str) -> Optional[str]:
    row = _find_row(rows, label)
    if row is None:
        return None
    return _safe_cell(row, 1).strip()


def _find_block_end(
    start_index: int,
    preset_indices: List[tuple[int, str]],
    inventory_start: int | None,
    default_end: int,
) -> int:
    for idx, _ in preset_indices:
        if idx > start_index:
            return idx
    if inventory_start is not None and inventory_start > start_index:
        return inventory_start
    return default_end


def _find_inventory_start(rows: List[List[str]]) -> Optional[int]:
    for idx in range(len(rows)):
        if _is_module_name_start(rows, idx):
            return idx
    return None


def _find_value_in_block(rows: List[List[str]], label: str) -> Optional[str]:
    for row in rows:
        if not row:
            continue
        if row[0].strip() == label:
            value = _safe_cell(row, 1).strip()
            return value if value != "" else None
    return None


def _is_module_name_start(rows: List[List[str]], index: int) -> bool:
    row = rows[index]
    name = row[0].strip()
    if not name or name in _MODULE_KNOWN_LABELS:
        return False
    if index + 1 >= len(rows):
        return False
    return rows[index + 1][0].strip() == "Rarity"
