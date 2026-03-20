from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class WorkshopEntry:
    name: str
    unlocked: Optional[str]
    coin_level: Optional[str]
    max_level: Optional[str]
    category: Optional[str]
    raw_row: List[str]


@dataclass(frozen=True)
class LabsState:
    labs: Dict[str, Optional[str]]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class WorkshopState:
    entries: Dict[str, WorkshopEntry]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class WorkshopPlusState:
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class UltimateWeaponEntry:
    name: str
    unlocked: Optional[str]
    track_levels: List[str]
    raw_row: List[str]


@dataclass(frozen=True)
class UltimateWeaponsState:
    entries: Dict[str, UltimateWeaponEntry]
    uw_plus_placeholder: Optional[str]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class CardEntry:
    name: str
    level: Optional[str]
    equipped_flags: List[str]
    raw_row: List[str]


@dataclass(frozen=True)
class CardsState:
    cards: Dict[str, CardEntry]
    equipped_preset_only: List[List[str]]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class BotEntry:
    name: str
    raw_row: List[str]


@dataclass(frozen=True)
class BotsState:
    bots: Dict[str, BotEntry]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class RelicsState:
    relics: Dict[str, Optional[str]]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class ThemesSongsState:
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class VaultState:
    vault: Dict[str, Optional[str]]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class ModuleSlot:
    slot_index: int
    context: Optional[str]
    slot_type: Optional[str]
    module_name: Optional[str]
    rarity: Optional[str]
    level: Optional[str]
    stat: Optional[str]
    substats: List[str]
    raw_rows: List[List[str]] = field(default_factory=list)


@dataclass(frozen=True)
class ModulesState:
    slots: List[ModuleSlot]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class GuardiansState:
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class PlayerStuffState:
    key_values: Dict[str, Optional[str]]
    raw_rows: List[List[str]]


@dataclass(frozen=True)
class IdsState:
    labs: LabsState
    workshop: WorkshopState
    workshop_plus: WorkshopPlusState
    ultimate_weapons: UltimateWeaponsState
    cards: CardsState
    relics: RelicsState
    vault: VaultState
    bots: BotsState
    themes_songs: ThemesSongsState
    modules: ModulesState
    guardians: GuardiansState
    player_stuff: PlayerStuffState
    raw_sections: Dict[str, List[List[str]]]
