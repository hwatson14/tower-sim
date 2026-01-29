"""TowerSim module application logic.

This file wires together:
- the module unique-effect library (tower_sim.libs.modules_library)
- the wiki-derived slot rules (tower_sim.loaders.wiki.module_rules)
- assist-slot efficiency rules from IDS (parsed elsewhere)

Important: In TowerSim, *module main effects* (e.g., Armor health multiplier)
are sourced from the user's data tables (_IDS / Data_Val_Tables) because the wiki
pages do not provide a complete level->multiplier curve in text form.

Unique effects and sub-module effect roll ranges are sourced from the wiki and
encoded in `tower_sim.libs.modules_library`.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from tower_sim.libs.modules_library import (
    Rarity,
    UNIQUE_EFFECTS,
    SUBSTAT_TABLES,
    SubstatCap,
)
from tower_sim.loaders.wiki.module_rules import max_active_substats_for_module_level

@dataclass(frozen=True)
class Substat:
    name: str
    value: float          # raw value as shown on module, in absolute units (e.g., 0.08 for 8%)
    rarity: Rarity

@dataclass(frozen=True)
class ModuleInstance:
    slot: str             # Cannon / Armor / Generator / Core
    name: str             # e.g., "Orbital Augment"
    rarity: Rarity        # actual module rarity
    level: int            # module level
    main_effect_value: float  # sourced externally (e.g., x6.44)
    substats: List[Substat]   # ordered; only first N active per level/assist rule

@dataclass(frozen=True)
class AssistContext:
    # efficiencies, expressed as decimals: 0.10 means 10%
    multiplier_efficiency: float
    substat_efficiency: float
    # assist slot cap rarity: e.g., Epic
    assist_cap_rarity: Rarity

def apply_assist_unique_effect_value(unique_value: float, module_rarity: Rarity, ctx: AssistContext) -> float:
    """Assist unique effects are capped by assist slot rarity (not by efficiencies)."""
    # Map rarity to index; choose min(module_rarity, assist_cap_rarity) in order
    order = {r:i for i,r in enumerate([Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHIC, Rarity.ANCESTRAL])}
    cap = ctx.assist_cap_rarity
    eff_rarity = module_rarity if order[module_rarity] <= order[cap] else cap
    # caller should provide the correct unique_value for that rarity already;
    # we just return it (kept here for clarity).
    return unique_value

def active_substats(module: ModuleInstance, *, is_assist: bool, ctx: Optional[AssistContext]=None) -> List[Substat]:
    """Return active substats in order.

    Rules:
    - Module level determines how many substat slots are active (wiki rule).
    - If module is in assist slot, the *effective level* may be lower (handled by caller by setting module.level).
      Additionally, players can have more substats than active; extras are ignored.
    """
    n = max_active_substats_for_module_level(module.level)
    return module.substats[:n]

def apply_substat_efficiency(raw_value: float, *, is_assist: bool, ctx: Optional[AssistContext]) -> float:
    """Substats in assist slot are multiplied by substat_efficiency (0..1)."""
    if not is_assist:
        return raw_value
    if ctx is None:
        raise ValueError("AssistContext required for assist substat efficiency")
    return raw_value * ctx.substat_efficiency

def apply_multiplier_efficiency(main_effect_value: float, ctx: AssistContext) -> float:
    """Effective Paths style: assist main-effect scaling: ((x-1)*(1+stones+lab)*0.01)+1.

    Here, ctx.multiplier_efficiency is already (stones+lab) as a decimal, e.g. 0.10 for 10%.
    So: ((x-1)*(1+eff))+1.
    """
    return ((main_effect_value - 1.0) * (1.0 + ctx.multiplier_efficiency)) + 1.0

def get_unique_effect_value(module_name: str, rarity: Rarity) -> float:
    return UNIQUE_EFFECTS[module_name][rarity]

def get_substat_cap(slot: str, rarity: Rarity) -> SubstatCap:
    return SUBSTAT_TABLES[slot].caps[rarity]
