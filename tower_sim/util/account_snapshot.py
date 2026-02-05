from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


PRESET_NAMES = ("Farming", "Tourney", "Testing", "Preset 4", "Preset 5")
SLOT_TYPES = ("Cannon", "Armor", "Generator", "Core")


@dataclass(frozen=True)
class TableSnapshot:
    header: List[str]
    rows: List[List[str]]


@dataclass(frozen=True)
class WorkshopEntrySnapshot:
    name: str
    coin_level: Optional[int]
    end_level: Optional[int]
    max_level: Optional[int]
    unlocked: Optional[str]
    category: Optional[str]


@dataclass(frozen=True)
class UltimateWeaponSnapshot:
    name: str
    unlocked: Optional[str]
    track_levels: List[str]


@dataclass(frozen=True)
class CardSnapshot:
    name: str
    level: Optional[int]
    mastery_unlocked: bool
    mastery_lab_level: Optional[int]


@dataclass(frozen=True)
class ModuleSubstat:
    stat_name: str
    rarity: Optional[str]
    value_display: Optional[str]
    value_num: Optional[float]


@dataclass(frozen=True)
class ModuleSnapshot:
    name: str
    slot_type: str
    rarity: Optional[str]
    level: Optional[int]
    stat: Optional[str]
    substats: List[ModuleSubstat]


@dataclass(frozen=True)
class ModuleSystemState:
    slot_type: str
    assist_unlocked: bool
    assist_level: int
    rarity_cap: Optional[str]
    multiplier_cap: Optional[float]
    substat_cap: Optional[float]


@dataclass(frozen=True)
class ModulePresetSelection:
    primary: Optional[str]
    assist: Optional[str]


@dataclass(frozen=True)
class ModuleAllocation:
    primary_level: int
    assist_level: int


@dataclass(frozen=True)
class AccountSnapshot:
    ids_path: Path
    labs: Dict[str, Optional[int]]
    workshop: Dict[str, WorkshopEntrySnapshot]
    workshop_enhancements: TableSnapshot
    ultimate_weapons: Dict[str, UltimateWeaponSnapshot]
    relics: Dict[str, Optional[int]]
    vault: Dict[str, Optional[int]]
    bots: List[str]
    guardians: TableSnapshot
    player_meta: Dict[str, Optional[str]]
    cards_inventory: Dict[str, CardSnapshot]
    card_presets: Dict[str, List[str]]
    module_system_state: Dict[str, ModuleSystemState]
    module_presets: Dict[str, Dict[str, ModulePresetSelection]]
    modules_inventory: Dict[str, ModuleSnapshot]
    allocation_levels: Dict[str, ModuleAllocation]
    inferred_shard_budgets: Dict[str, int]
    default_preset: str
    raw_sections: Dict[str, List[List[str]]]


@dataclass(frozen=True)
class ResolvedLoadout:
    preset_name: str
    card_names: List[str]
    modules_by_slot: Dict[str, ModulePresetSelection]
    allocation_levels: Dict[str, ModuleAllocation]
    inferred_shard_budgets: Dict[str, int]
