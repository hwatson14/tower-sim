from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from tower_sim.modules_library import (
    Rarity,
    SUBSTATS_BY_SLOT,
    UNIQUE_EFFECTS,
    UniqueEffect,
)


@dataclass(frozen=True)
class ModulesLibrary:
    unique_effects: Dict[str, UniqueEffect]
    substats_by_slot: Dict[str, Dict[str, object]]


def load_modules_library() -> ModulesLibrary:
    return ModulesLibrary(
        unique_effects=UNIQUE_EFFECTS,
        substats_by_slot=SUBSTATS_BY_SLOT,
    )


def unique_effect_value(module_name: str, rarity: Rarity, library: ModulesLibrary) -> float:
    if module_name not in library.unique_effects:
        raise KeyError(f"Unknown module unique effect: {module_name!r}")
    return library.unique_effects[module_name].value[rarity]


def substat_definitions(slot: str, library: ModulesLibrary) -> Dict[str, object]:
    if slot not in library.substats_by_slot:
        raise KeyError(f"Unknown module slot: {slot!r}")
    return library.substats_by_slot[slot]
