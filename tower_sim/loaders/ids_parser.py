from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from tower_sim.util.ids_state import (
    BotsState,
    BotEntry,
    CardsState,
    CardEntry,
    GuardiansState,
    IdsState,
    LabsState,
    ModulesState,
    ModuleSlot,
    PlayerStuffState,
    RelicsState,
    ThemesSongsState,
    UltimateWeaponsState,
    UltimateWeaponEntry,
    VaultState,
    WorkshopEntry,
    WorkshopPlusState,
    WorkshopState,
)


@dataclass(frozen=True)
class SectionSpec:
    name: str
    header_col: int
    start_col: int
    end_col: int


SECTION_SPECS = [
    SectionSpec("Labs", 0, 0, 3),
    SectionSpec("WS", 4, 5, 16),
    SectionSpec("WS+", 17, 17, 24),
    SectionSpec("UWs", 25, 25, 29),
    SectionSpec("Cards", 30, 30, 37),
    SectionSpec("Relics", 38, 38, 40),
    SectionSpec("Vault", 41, 41, 42),
    SectionSpec("Bots", 44, 44, 48),
    SectionSpec("Themes & Songs", 50, 50, 51),
    SectionSpec("Modules", 53, 53, 71),
    SectionSpec("Guardians", 72, 72, 76),
    SectionSpec("Player & Stuff", 77, 77, 82),
]


DEFAULT_IDS_PATHS: Sequence[Path] = (
    Path("tests/fixtures/tower-sim-data/_IDS.csv"),
    Path("tests/fixtures/_IDS.csv"),
    Path("reference/tower-sim-data/_IDS.csv"),
)


def resolve_ids_path(paths: Sequence[Path] = DEFAULT_IDS_PATHS) -> Path:
    for path in paths:
        if path.exists():
            return path
    candidates = ", ".join(str(path) for path in paths)
    raise FileNotFoundError(f"Could not find _IDS.csv. Tried: {candidates}")


def _read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def _slice_row(row: List[str], start: int, end: int) -> List[str]:
    padded = row + [""] * max(0, end + 1 - len(row))
    return padded[start : end + 1]


def _row_has_data(row: List[str]) -> bool:
    return any(cell.strip() != "" for cell in row)


def _collect_section_rows(rows: List[List[str]], spec: SectionSpec) -> List[List[str]]:
    out: List[List[str]] = []
    for row in rows[1:]:
        sliced = _slice_row(row, spec.start_col, spec.end_col)
        if _row_has_data(sliced):
            out.append(sliced)
    return out


def _fail_unknown_sections(rows: List[List[str]]) -> None:
    header = rows[0] if rows else []
    known = {spec.name for spec in SECTION_SPECS}
    allowed_metadata = {""}
    for spec in SECTION_SPECS:
        if spec.header_col >= len(header):
            raise ValueError(
                f"Missing section header for {spec.name!r} at column {spec.header_col}."
            )
        if header[spec.header_col].strip() != spec.name:
            raise ValueError(
                "Unexpected section header location in _IDS.csv: "
                f"expected {spec.name!r} at column {spec.header_col}, "
                f"found {header[spec.header_col]!r}."
            )
    for idx, cell in enumerate(header):
        value = cell.strip()
        if value == "":
            continue
        if value in known or value in allowed_metadata:
            continue
        if value.startswith("http") or value == "?" or value.startswith("v"):
            continue
        if value == "Cards Presets":
            continue
        row_values = rows[1] if len(rows) > 1 else []
        offending = row_values[idx] if idx < len(row_values) else ""
        raise ValueError(
            "Unknown section header in _IDS.csv: "
            f"{value!r} at column {idx}. First row value: {offending!r}"
        )


def _parse_labs(rows: List[List[str]]) -> LabsState:
    labs: Dict[str, Optional[str]] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        value = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        labs[name] = value
        raw_rows.append(row)
    return LabsState(labs=labs, raw_rows=raw_rows)


def _parse_workshop(rows: List[List[str]]) -> WorkshopState:
    entries: Dict[str, WorkshopEntry] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        entry = WorkshopEntry(
            name=name,
            unlocked=row[1].strip() if row[1].strip() != "" else None,
            coin_level=row[3].strip() if row[3].strip() != "" else None,
            max_level=row[11].strip() if len(row) > 11 and row[11].strip() != "" else None,
            category=row[5].strip() if len(row) > 5 and row[5].strip() != "" else None,
            raw_row=row,
        )
        entries[name] = entry
        raw_rows.append(row)
    return WorkshopState(entries=entries, raw_rows=raw_rows)


def _parse_workshop_plus(rows: List[List[str]]) -> WorkshopPlusState:
    return WorkshopPlusState(raw_rows=rows)


def _parse_uws(rows: List[List[str]]) -> UltimateWeaponsState:
    entries: Dict[str, UltimateWeaponEntry] = {}
    raw_rows: List[List[str]] = []
    uw_plus_placeholder: Optional[str] = None
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        if name == "UW+":
            uw_plus_placeholder = name
            raw_rows.append(row)
            continue
        unlocked = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        track_levels = [cell for cell in row[2:] if cell.strip() != ""]
        entries[name] = UltimateWeaponEntry(
            name=name,
            unlocked=unlocked,
            track_levels=track_levels,
            raw_row=row,
        )
        raw_rows.append(row)
    return UltimateWeaponsState(
        entries=entries,
        uw_plus_placeholder=uw_plus_placeholder,
        raw_rows=raw_rows,
    )


def _parse_cards(rows: List[List[str]]) -> CardsState:
    cards: Dict[str, CardEntry] = {}
    equipped_preset_only: List[List[str]] = []
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        if name == "Card Presets":
            equipped_preset_only.append(row)
            raw_rows.append(row)
            continue
        level = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        flags = [cell for cell in row[2:] if cell.strip() != ""]
        cards[name] = CardEntry(
            name=name,
            level=level,
            equipped_flags=flags,
            raw_row=row,
        )
        raw_rows.append(row)
    return CardsState(cards=cards, equipped_preset_only=equipped_preset_only, raw_rows=raw_rows)


def _parse_relics(rows: List[List[str]]) -> RelicsState:
    relics: Dict[str, Optional[str]] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        value = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        relics[name] = value
        raw_rows.append(row)
    return RelicsState(relics=relics, raw_rows=raw_rows)


def _parse_vault(rows: List[List[str]]) -> VaultState:
    vault: Dict[str, Optional[str]] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        value = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        vault[name] = value
        raw_rows.append(row)
    return VaultState(vault=vault, raw_rows=raw_rows)


def _parse_bots(rows: List[List[str]]) -> BotsState:
    bots: Dict[str, BotEntry] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        bots[name] = BotEntry(name=name, raw_row=row)
        raw_rows.append(row)
    return BotsState(bots=bots, raw_rows=raw_rows)


def _parse_themes_songs(rows: List[List[str]]) -> ThemesSongsState:
    return ThemesSongsState(raw_rows=rows)


def _parse_modules(rows: List[List[str]]) -> ModulesState:
    slots: List[ModuleSlot] = []
    raw_rows: List[List[str]] = []
    for idx in range(4):
        base = idx * 5
        slot_rows: List[List[str]] = []
        for row in rows:
            slot_row = row[base : base + 5]
            if _row_has_data(slot_row):
                slot_rows.append(row)
        if not slot_rows:
            continue
        context: Optional[str] = None
        slot_type: Optional[str] = None
        module_name: Optional[str] = None
        rarity: Optional[str] = None
        level: Optional[str] = None
        stat: Optional[str] = None
        substats: List[str] = []
        for row in slot_rows:
            cell = row[base].strip()
            next_cell = row[base + 1].strip() if len(row) > base + 1 else ""
            if cell in {"Farming", "Tourney", "Testing"}:
                context = cell
            if cell == "Primary Slot":
                slot_type = cell
                module_name = next_cell if next_cell != "" else None
            if cell == "Assist Slot" and module_name is None:
                slot_type = cell
                module_name = next_cell if next_cell != "" else None
        for i, row in enumerate(slot_rows):
            cell = row[base].strip()
            if cell == "Rarity" and i + 1 < len(slot_rows):
                data_row = slot_rows[i + 1]
                rarity = data_row[base].strip() if data_row[base].strip() != "" else None
                level = (
                    data_row[base + 1].strip()
                    if len(data_row) > base + 1 and data_row[base + 1].strip() != ""
                    else None
                )
                stat = (
                    data_row[base + 2].strip()
                    if len(data_row) > base + 2 and data_row[base + 2].strip() != ""
                    else None
                )
                break
        for row in slot_rows:
            for cell in row[base : base + 5]:
                value = cell.strip()
                if value in {"", "Primary Slot", "Assist Slot", "Rarity", "Level", "Stat"}:
                    continue
                substats.append(value)
        slots.append(
            ModuleSlot(
                slot_index=idx,
                context=context,
                slot_type=slot_type,
                module_name=module_name,
                rarity=rarity,
                level=level,
                stat=stat,
                substats=substats,
                raw_rows=slot_rows,
            )
        )
    for row in rows:
        raw_rows.append(row)
    return ModulesState(slots=slots, raw_rows=raw_rows)


def _parse_guardians(rows: List[List[str]]) -> GuardiansState:
    return GuardiansState(raw_rows=rows)


def _parse_player_stuff(rows: List[List[str]]) -> PlayerStuffState:
    key_values: Dict[str, Optional[str]] = {}
    raw_rows: List[List[str]] = []
    for row in rows:
        name = row[0].strip()
        if not name:
            continue
        value = row[1].strip() if len(row) > 1 and row[1].strip() != "" else None
        key_values[name] = value
        raw_rows.append(row)
    return PlayerStuffState(key_values=key_values, raw_rows=raw_rows)


def parse_ids(path: Optional[Path] = None) -> IdsState:
    ids_path = path or resolve_ids_path()
    rows = _read_csv_rows(ids_path)
    if not rows:
        raise ValueError(f"_IDS.csv is empty: {ids_path}")
    _fail_unknown_sections(rows)
    raw_sections: Dict[str, List[List[str]]] = {}
    for spec in SECTION_SPECS:
        raw_sections[spec.name] = _collect_section_rows(rows, spec)

    labs = _parse_labs(raw_sections["Labs"])
    workshop = _parse_workshop(raw_sections["WS"])
    workshop_plus = _parse_workshop_plus(raw_sections["WS+"])
    ultimate_weapons = _parse_uws(raw_sections["UWs"])
    cards = _parse_cards(raw_sections["Cards"])
    relics = _parse_relics(raw_sections["Relics"])
    vault = _parse_vault(raw_sections["Vault"])
    bots = _parse_bots(raw_sections["Bots"])
    themes_songs = _parse_themes_songs(raw_sections["Themes & Songs"])
    modules = _parse_modules(raw_sections["Modules"])
    guardians = _parse_guardians(raw_sections["Guardians"])
    player_stuff = _parse_player_stuff(raw_sections["Player & Stuff"])

    return IdsState(
        labs=labs,
        workshop=workshop,
        workshop_plus=workshop_plus,
        ultimate_weapons=ultimate_weapons,
        cards=cards,
        relics=relics,
        vault=vault,
        bots=bots,
        themes_songs=themes_songs,
        modules=modules,
        guardians=guardians,
        player_stuff=player_stuff,
        raw_sections=raw_sections,
    )
