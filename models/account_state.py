from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

PRESET_NAMES = ["Farming", "Tourney", "Milestone", "Preset 4", "Preset 5"]
SLOT_TYPES = ["cannon", "armor", "generator", "core"]


@dataclass(frozen=True)
class TableSnapshot:
    header: List[str]
    rows: List[List[str]]


@dataclass(frozen=True)
class WorkshopEntrySnapshot:
    name: str
    unlocked: Optional[str]
    preset_levels: Dict[str, Optional[int]]
    max_level: Optional[int]
    category: Optional[str]


@dataclass(frozen=True)
class CardSnapshot:
    name: str
    level: Optional[int]
    mastery_unlocked: Optional[bool]
    mastery_lab_level: Optional[int]


@dataclass(frozen=True)
class UltimateWeaponSnapshot:
    name: str
    unlocked: Optional[str]
    track_levels: List[str]
    track_values: List[Optional[float]] = field(default_factory=list)


@dataclass(frozen=True)
class UwPlusTrackSnapshot:
    uw_name: str
    plus_track_name: str
    current_state: str
    display_token: str


@dataclass(frozen=True)
class ModuleSubstat:
    name: str
    value: Optional[str]
    raw_token: Optional[str] = None


@dataclass(frozen=True)
class ModuleSnapshot:
    name: str
    slot_type: str
    rarity: Optional[str]
    level: Optional[int]
    stat: Optional[str]
    substats: List[ModuleSubstat] = field(default_factory=list)


@dataclass(frozen=True)
class ModulePresetSelection:
    primary: Optional[str]
    assist: Optional[str]


@dataclass(frozen=True)
class PerkSelection:
    perk_id: str
    picks: int = 1


@dataclass(frozen=True)
class ModuleSystemState:
    slot_type: str
    assist_unlocked: Optional[bool]
    assist_level: Optional[int]
    rarity_cap: Optional[str]
    multiplier_cap: Optional[float]
    substat_cap: Optional[float]


@dataclass(frozen=True)
class AccountState:
    ids_path: Path
    labs: Dict[str, Optional[int]]
    workshop: Dict[str, WorkshopEntrySnapshot]
    workshop_enhancements: TableSnapshot
    ultimate_weapons: Dict[str, UltimateWeaponSnapshot]
    uw_plus_tracks: Dict[str, UwPlusTrackSnapshot]
    relics: Dict[str, Optional[float]]
    vault: Dict[str, Any]
    bots: List[str]
    bot_upgrades: Dict[str, Dict[str, int]]
    guardians: TableSnapshot
    player_meta: Dict[str, Optional[str]]
    theme_song_coin_multiplier: Optional[float]
    cards_inventory: Dict[str, CardSnapshot]
    card_slots_unlocked: Optional[int]
    card_presets: Dict[str, List[str]]
    module_system_state: Dict[str, ModuleSystemState]
    module_presets: Dict[str, Dict[str, ModulePresetSelection]]
    modules_inventory: Dict[str, ModuleSnapshot]
    perk_presets: Dict[str, List[PerkSelection]]
    active_perk_preset: Optional[str]
    active_card_preset: str
    active_module_preset: str
    default_preset: str
    raw_sections: Dict[str, List[List[str]]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
