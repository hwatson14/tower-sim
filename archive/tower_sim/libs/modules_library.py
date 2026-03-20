
"""
TowerSim - Module definitions

Sources (wiki):
- Epic Module Unique Effect: https://the-tower-idle-tower-defense.fandom.com/wiki/Epic_Module_Unique_Effect
- Sub-Module Effects: https://the-tower-idle-tower-defense.fandom.com/wiki/Sub-Module_Effects

This file encodes:
- Module "unique effects" and their rarity-scaled magnitudes.
- Sub-module effect roll ranges by slot and rarity (Cannon/Armor/Generator/Core).
- Helper math for applying assist-slot efficiencies.

NOTE: "Main effect" scaling vs module LEVEL is *not* encoded here because the wiki pages above
do not contain a machine-readable level->multiplier curve in text form. The simulator should
source the main-effect curve from the IDS / Data tables (or an explicit main-effect table),
then apply it consistently for both primary and assist modules.

All values below are direct transcription of the wiki tables (no interpolation).

Guardrail: the wiki explicitly notes assist sub-module effects do not bypass hard caps
(e.g., 98% defense, 40% death defy). Any simulation should apply caps after assist
effects are combined.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional, Literal


class Rarity(str, Enum):
    """Sub-module rarity (independent of the module's own rarity)."""

    COMMON = "Common"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"
    ANCESTRAL = "Ancestral"


RARITY_ORDER = (
    Rarity.COMMON,
    Rarity.RARE,
    Rarity.EPIC,
    Rarity.LEGENDARY,
    Rarity.MYTHIC,
    Rarity.ANCESTRAL,
)


@dataclass(frozen=True)
class UniqueEffect:
    """A module's unique effect magnitude per rarity.

    Units:
    - Most are numeric as displayed (percent, seconds, multiplier, count).
    - Interpretation is handled by effect_name / downstream logic.
    """
    module_name: str
    slot: Literal["Cannon", "Armor", "Generator", "Core"]
    effect_name: str
    ability_text: Optional[str]
    # values per rarity, keyed by Rarity
    value: Dict[Rarity, float]


# ---- Unique effects (Epic Module Unique Effect table) ----
# Note: Ability text is populated from the wiki excerpt provided in the prompt.

UNIQUE_EFFECTS: Dict[str, UniqueEffect] = {}

def _add_unique(
    module_name: str,
    slot: str,
    effect_name: str,
    epic: float,
    legendary: float,
    mythic: float,
    ancestral: float,
    *,
    ability_text: Optional[str] = None,
) -> None:
    UNIQUE_EFFECTS[module_name] = UniqueEffect(
        module_name=module_name,
        slot=slot,  # type: ignore[arg-type]
        effect_name=effect_name,
        ability_text=ability_text,
        value={
            Rarity.EPIC: float(epic),
            Rarity.LEGENDARY: float(legendary),
            Rarity.MYTHIC: float(mythic),
            Rarity.ANCESTRAL: float(ancestral),
        },
    )

# Cannons
_add_unique(
    "Astral Deliverance",
    "Cannon",
    "bounce_damage_per_bounce_pct",
    20,
    40,
    60,
    80,
    ability_text=(
        "Bounce shot range increased by 3% of tower range; each bounce increases "
        "projectile damage by 20 / 40 / 60 / 80 (E/L/M/A)."
    ),
)
_add_unique(
    "Being Annihilator",
    "Cannon",
    "guaranteed_supercrits_after_supercrit_attacks",
    3,
    4,
    5,
    6,
    ability_text=(
        "On super crit, next attacks guaranteed super crits: 3 / 4 / 5 / 6."
    ),
)
_add_unique(
    "Death Penalty",
    "Cannon",
    "mark_for_death_spawn_chance_pct",
    5,
    8,
    11,
    15,
    ability_text="Mark-on-spawn chance; first hit destroys: 5% / 8% / 11% / 15%.",
)
_add_unique(
    "Havoc Bringer",
    "Cannon",
    "rend_armor_instant_max_chance_pct",
    10,
    13,
    15,
    20,
    ability_text="Rend Armor instantly to max chance: 10% / 13% / 15% / 20%.",
)
_add_unique(
    "Shrink Ray",
    "Cannon",
    "enemy_mass_reduction_pct",
    10,
    20,
    30,
    40,
    ability_text="1% chance to apply non-stacking mass reduction: 10% / 20% / 30% / 40%.",
)
_add_unique(
    "Amplifying Strike",
    "Cannon",
    "tower_damage_5x_duration_s",
    5,
    11,
    18,
    26,
    ability_text="Killing boss/elite → Tower Damage 5x for 5s / 11s / 18s / 26s.",
)

# Armor
_add_unique(
    "Anti-Cube Portal",
    "Armor",
    "shockwave_damage_taken_mult_x",
    10,
    15,
    20,
    25,
    ability_text="After shockwave hit: enemies take 10x / 15x / 20x / 25x damage for 7s.",
)
_add_unique(
    "Negative Mass Projector",
    "Armor",
    "orb_nonkill_debuff_pct_per_hit",
    1.0,
    1.5,
    2.0,
    2.5,
    ability_text=(
        "Orb hit applies stacking debuff reducing enemy damage & speed by "
        "1.0% / 1.5% / 2.0% / 2.5% per hit (max 50%)."
    ),
)
_add_unique(
    "Wormhole Redirector",
    "Armor",
    "regen_heal_cap_pct_of_package_max_recovery",
    25,
    50,
    75,
    100,
    ability_text="Health Regen can heal up to 25% / 50% / 75% / 100% of Package Max Recovery.",
)
_add_unique(
    "Space Displacer",
    "Armor",
    "landmine_spawn_as_ilm_chance_pct",
    15,
    20,
    25,
    30,
    ability_text="Landmines spawn as ILM chance: 15% / 20% / 25% / 30% (20 max).",
)
_add_unique(
    "Sharp Fortitude",
    "Armor",
    "wall_health_regen_mult_x",
    1.25,
    1.5,
    2.0,
    2.5,
    ability_text=(
        "Wall health+regen multiplier: 1.25 / 1.5 / 2.0 / 2.5; plus "
        "+1% increased damage from wall thorns per subsequent hit."
    ),
)
_add_unique(
    "Orbital Augment",
    "Armor",
    "electrons_count",
    2,
    4,
    6,
    8,
    ability_text=(
        "Adds [x] orbiting Electrons around the tower. Each Electron deals damage equal "
        "to 15% of the enemy's remaining health (quarter effective against Bosses and Fleets)."
    ),
)

# Generators
_add_unique(
    "Singularity Harness",
    "Generator",
    "bot_range_bonus_m",
    5,
    8,
    11,
    15,
    ability_text="Bot range +5 / 8 / 11 / 15 m; Flame Bot hits cause double damage.",
)
_add_unique(
    "Galaxy Compressor",
    "Generator",
    "uw_cooldown_reduction_per_package_s",
    10,
    13,
    17,
    20,
    ability_text="Recovery package reduces UW cooldown (except Poison Swamp) by 10 / 13 / 17 / 20 s.",
)
_add_unique(
    "Pulsar Harvester",
    "Generator",
    "proj_hit_reduce_enemy_levels_chance_pct",
    1.0,
    1.5,
    2.0,
    2.5,
    ability_text=(
        "Projectile hit chance to reduce enemy health+attack level by 1: "
        "1.0% / 1.5% / 2.0% / 2.5% (diminishing returns after 100 reductions)."
    ),
)
_add_unique(
    "Black Hole Digestor",
    "Generator",
    "coins_kill_bonus_pct_per_free_upgrade_current_wave",
    3,
    5,
    7,
    10,
    ability_text=(
        "Per free-upgrade trigger: temporary extra Coins/Kill Bonus "
        "3% / 5% / 7% / 10%."
    ),
)
_add_unique(
    "Project Funding",
    "Generator",
    "tower_damage_mult_pct_per_cash_digit",
    12.5,
    25,
    50,
    100,
    ability_text=(
        "Tower damage multiplied by 12.5% / 25% / 50% / 100% of number of digits in current cash."
    ),
)
_add_unique(
    "Restorative Bonus",
    "Generator",
    "package_attack_speed_boost_duration_s",
    15,
    20,
    25,
    30,
    ability_text=(
        "Packages grant a 50% attack speed boost for [x]s, decaying for 60 seconds. "
        "Effect refreshes on another Recovery Package; duration does not stack."
    ),
)

# Cores
_add_unique(
    "Om Chip",
    "Core",
    "spotlight_boss_reflection_increase",
    2,
    4,
    7,
    15,
    ability_text=(
        "Spotlight focuses a Boss; boss reflects light to nearby enemies, increasing by "
        "2 / 4 / 7 / 15."
    ),
)
_add_unique(
    "Harmony Conductor",
    "Core",
    "poisoned_enemy_miss_attack_chance_pct",
    15,
    20,
    25,
    30,
    ability_text="Poisoned enemies miss-attack chance: 15% / 20% / 25% / 30% (boss chance halved).",
)
_add_unique(
    "Dimension Core",
    "Core",
    "shock_max_stacks",
    5,
    10,
    15,
    20,
    ability_text="Chain lightning + shock modifications; max stack 5 / 10 / 15 / 20.",
)
_add_unique(
    "Multiverse Nexus",
    "Core",
    "dw_gt_bh_cooldown_avg_offset_s",
    20,
    10,
    1,
    -10,
    ability_text=(
        "DW/GT/BH always activate together; cooldown becomes average +/- 20s / 10s / 1s / -10s."
    ),
)
_add_unique(
    "Magnetic Hook",
    "Core",
    "ilm_fired_at_bosses_count",
    1,
    2,
    3,
    4,
    ability_text="ILM fired at bosses entering range: 1 / 2 / 3 / 4; and 25% of elites get ILM fired similarly.",
)
_add_unique(
    "Primordial Collapse",
    "Core",
    "enemy_damage_reduction_inside_bh_pct",
    50,
    55,
    65,
    80,
    ability_text="+1 Black Hole; enemy damage within BH reduced by 50% / 55% / 65% / 80%.",
)


def unique_effect_value(module_name: str, rarity: Rarity) -> float:
    return UNIQUE_EFFECTS[module_name].value[rarity]


# ---- Sub-module effects ----
@dataclass(frozen=True)
class SubstatDef:
    """Sub-module effect values by *sub-module rarity*.

    The Tower wiki lists a single value per rarity (not a roll range) for each sub-module effect.
    """

    name: str
    slot: Literal["Cannon", "Armor", "Generator", "Core"]
    unit: Literal["pct", "flat", "sec", "count", "mult"]  # interpret downstream
    value: Dict[Rarity, float]


def _sv(name: str, slot: str, unit: str, *, c: float | None = None, r: float | None = None,
        e: float | None = None, l: float | None = None, m: float | None = None, a: float | None = None) -> SubstatDef:
    vals: Dict[Rarity, float] = {}
    if c is not None:
        vals[Rarity.COMMON] = float(c)
    if r is not None:
        vals[Rarity.RARE] = float(r)
    if e is not None:
        vals[Rarity.EPIC] = float(e)
    if l is not None:
        vals[Rarity.LEGENDARY] = float(l)
    if m is not None:
        vals[Rarity.MYTHIC] = float(m)
    if a is not None:
        vals[Rarity.ANCESTRAL] = float(a)
    return SubstatDef(name=name, slot=slot, unit=unit, value=vals)  # type: ignore[arg-type]


# Values from Sub-Module Effects wiki table
# Cannon Submodules (Attack)
CANNON_SUBSTATS: Dict[str, SubstatDef] = {
    "Attack Speed": _sv("Attack Speed", "Cannon", "pct", c=0.3, r=0.5, e=0.7, l=1, m=3, a=5),
    "Crit Chance": _sv("Crit Chance", "Cannon", "pct", c=2, r=3, e=4, l=6, m=8, a=10),
    "Crit Factor": _sv("Crit Factor", "Cannon", "mult", c=2, r=4, e=6, l=8, m=12, a=15),
    "Attack Range": _sv("Attack Range", "Cannon", "flat", c=2, r=4, e=8, l=12, m=20, a=30),
    "Damage / Meter": _sv("Damage / Meter", "Cannon", "mult", c=0.005, r=0.01, e=0.025, l=0.04, m=0.075, a=0.15),
    "Multishot Chance": _sv("Multishot Chance", "Cannon", "pct", r=3, e=5, l=7, m=10, a=13),
    "Multishot Targets": _sv("Multishot Targets", "Cannon", "count", e=1, l=2, m=3, a=4),
    "Rapid Fire Chance": _sv("Rapid Fire Chance", "Cannon", "pct", r=2, e=4, l=6, m=9, a=12),
    "Rapid Fire Duration": _sv("Rapid Fire Duration", "Cannon", "sec", r=0.4, e=0.8, l=1.4, m=2.5, a=3.5),
    "Bounce Shot Chance": _sv("Bounce Shot Chance", "Cannon", "pct", r=2, e=3, l=5, m=9, a=12),
    "Bounce Shot Targets": _sv("Bounce Shot Targets", "Cannon", "count", e=1, l=2, m=3, a=4),
    "Bounce Shot Range": _sv("Bounce Shot Range", "Cannon", "flat", r=0.5, e=0.8, l=1.2, m=1.8, a=2.0),
    "Super Crit Chance": _sv("Super Crit Chance", "Cannon", "pct", e=3, l=5, m=7, a=10),
    "Super Crit Multi": _sv("Super Crit Multi", "Cannon", "mult", e=2, l=3, m=5, a=7),
    "Rend Armor Chance": _sv("Rend Armor Chance", "Cannon", "pct", l=2, m=5, a=8),
    "Rend Armor Multi": _sv("Rend Armor Multi", "Cannon", "pct", l=2, m=5, a=8),
    "Max Rend Armor Multi": _sv("Max Rend Armor Multi", "Cannon", "pct", l=200, m=300, a=500),
}


# Armor Submodules (Defense)
ARMOR_SUBSTATS: Dict[str, SubstatDef] = {
    "Health Regen": _sv("Health Regen", "Armor", "pct", c=20, r=40, e=60, l=100, m=200, a=400),
    "Defense": _sv("Defense", "Armor", "pct", c=1, r=2, e=3, l=5, m=6, a=8),
    "Defense Absolute": _sv("Defense Absolute", "Armor", "pct", c=15, r=25, e=40, l=100, m=500, a=1000),
    "Recovery Package Chance": _sv("Recovery Package Chance", "Armor", "pct", r=6, e=9, l=12, m=15, a=18),
    "Recovery Package Amount": _sv("Recovery Package Amount", "Armor", "pct", r=6, e=9, l=12, m=15, a=18),
    "Thorns Damage": _sv("Thorns Damage", "Armor", "pct", e=2, l=4, m=7, a=10),
    "Lifesteal": _sv("Lifesteal", "Armor", "pct", e=0.3, l=0.5, m=1.5, a=2.0),
    "Knockback Chance": _sv("Knockback Chance", "Armor", "pct", e=2, l=4, m=6, a=9),
    "Knockback Force": _sv("Knockback Force", "Armor", "flat", e=0.1, l=0.4, m=0.9, a=1.5),
    "Orb Speed": _sv("Orb Speed", "Armor", "flat", e=1, l=1.5, m=2, a=3),
    "Orbs": _sv("Orbs", "Armor", "count", m=1, a=2),
    "Shockwave Size": _sv("Shockwave Size", "Armor", "flat", e=0.1, l=0.3, m=0.7, a=1),
    "Shockwave Frequency": _sv("Shockwave Frequency", "Armor", "sec", e=-1, l=-2, m=-3, a=-4),
    "Land Mine Damage": _sv("Land Mine Damage", "Armor", "pct", r=30, e=50, l=150, m=500, a=800),
    "Land Mine Chance": _sv("Land Mine Chance", "Armor", "pct", r=1.5, e=3, l=6, m=9, a=12),
    "Land Mine Radius": _sv("Land Mine Radius", "Armor", "flat", r=0.1, e=0.15, l=0.3, m=0.75, a=1),
    "Death Defy": _sv("Death Defy", "Armor", "pct", l=1.5, m=3.5, a=5),
    "Wall Health": _sv("Wall Health", "Armor", "pct", e=20, l=40, m=90, a=120),
    "Wall Rebuild": _sv("Wall Rebuild", "Armor", "sec", e=-20, l=-40, m=-80, a=-100),
}


# Generator Submodules (Utility)
GENERATOR_SUBSTATS: Dict[str, SubstatDef] = {
    "Cash Bonus": _sv("Cash Bonus", "Generator", "mult", c=0.1, r=0.2, e=0.3, l=0.5, m=1.2, a=2.5),
    "Cash / Wave": _sv("Cash / Wave", "Generator", "flat", c=30, r=50, e=100, l=200, m=500, a=1000),
    "Coins / Kill Bonus": _sv("Coins / Kill Bonus", "Generator", "mult", c=0.1, r=0.2, e=0.3, l=0.4, m=0.5, a=0.6),
    "Coins / Wave": _sv("Coins / Wave", "Generator", "flat", c=20, r=35, e=60, l=120, m=200, a=350),
    "Free Attack Upgrade": _sv("Free Attack Upgrade", "Generator", "pct", c=2, r=4, e=6, l=8, m=10, a=12),
    "Free Defense Upgrade": _sv("Free Defense Upgrade", "Generator", "pct", c=2, r=4, e=6, l=8, m=10, a=12),
    "Free Utility Upgrade": _sv("Free Utility Upgrade", "Generator", "pct", c=2, r=4, e=6, l=8, m=10, a=12),
    "Interest / Wave": _sv("Interest / Wave", "Generator", "pct", e=2, l=4, m=6, a=8),
    "Recovery Package Amount": _sv("Recovery Package Amount", "Generator", "pct", r=6, e=9, l=12, m=15, a=18),
    "Max Recovery": _sv("Max Recovery", "Generator", "mult", e=0.4, l=0.7, m=1.0, a=1.5),
    "Recovery Package Chance": _sv("Recovery Package Chance", "Generator", "pct", r=6, e=9, l=12, m=15, a=18),
    "Enemy Attack Level Skip": _sv("Enemy Attack Level Skip", "Generator", "pct", e=2, l=4, m=6, a=8),
    "Enemy Health Level Skip": _sv("Enemy Health Level Skip", "Generator", "pct", e=2, l=4, m=6, a=8),
}


# Core Submodules (Ultimate Weapons)
CORE_SUBSTATS: Dict[str, SubstatDef] = {
    "Golden Tower - Bonus": _sv("Golden Tower - Bonus", "Core", "flat", e=1, l=2, m=3, a=4),
    "Golden Tower - Duration": _sv("Golden Tower - Duration", "Core", "sec", l=2, m=4, a=7),
    "Golden Tower - Cooldown": _sv("Golden Tower - Cooldown", "Core", "sec", l=-5, m=-8, a=-12),
    "Black Hole - Size": _sv("Black Hole - Size", "Core", "flat", c=2, r=4, e=6, l=8, m=10, a=12),
    "Black Hole - Duration": _sv("Black Hole - Duration", "Core", "sec", l=2, m=3, a=4),
    "Black Hole - Cooldown": _sv("Black Hole - Cooldown", "Core", "sec", l=-2, m=-3, a=-4),
    "Spotlight - Bonus": _sv("Spotlight - Bonus", "Core", "flat", c=1.2, r=2.5, e=3.5, l=10, m=15, a=20),
    "Spotlight - Angle": _sv("Spotlight - Angle", "Core", "flat", e=3, l=6, m=11, a=15),
    "Chrono Field - Duration": _sv("Chrono Field - Duration", "Core", "sec", l=4, m=7, a=10),
    "Chrono Field - Speed Reduction": _sv("Chrono Field - Speed Reduction", "Core", "pct", e=3, l=8, m=11, a=15),
    "Chrono Field - Cooldown": _sv("Chrono Field - Cooldown", "Core", "sec", l=-4, m=-7, a=-10),
    "Death Wave - Damage": _sv("Death Wave - Damage", "Core", "mult", c=8, r=15, e=25, l=50, m=100, a=250),
    "Death Wave - Quantity": _sv("Death Wave - Quantity", "Core", "count", l=1, m=2, a=3),
    "Death Wave - Cooldown": _sv("Death Wave - Cooldown", "Core", "sec", l=-6, m=-10, a=-13),
    "Smart Missiles - Damage": _sv("Smart Missiles - Damage", "Core", "mult", c=8, r=15, e=25, l=50, m=100, a=250),
    "Smart Missiles - Quantity": _sv("Smart Missiles - Quantity", "Core", "count", e=1, l=2, m=4, a=5),
    "Smart Missiles - Cooldown": _sv("Smart Missiles - Cooldown", "Core", "sec", l=-2, m=-4, a=-6),
    "Inner Land Mines - Damage": _sv("Inner Land Mines - Damage", "Core", "mult", c=8, r=15, e=25, l=50, m=100, a=250),
    "Inner Land Mines - Quantity": _sv("Inner Land Mines - Quantity", "Core", "count", l=1, m=2, a=3),
    "Inner Land Mines - Cooldown": _sv("Inner Land Mines - Cooldown", "Core", "sec", e=-5, l=-8, m=-10, a=-13),
    "Poison Swamp - Damage": _sv("Poison Swamp - Damage", "Core", "mult", c=8, r=15, e=25, l=50, m=100, a=250),
    "Poison Swamp - Duration": _sv("Poison Swamp - Duration", "Core", "sec", l=2, m=5, a=10),
    "Poison Swamp - Cooldown": _sv("Poison Swamp - Cooldown", "Core", "sec", r=-2, e=-4, l=-6, m=-8, a=-10),
    "Chain Lightning - Damage": _sv("Chain Lightning - Damage", "Core", "mult", c=8, r=15, e=25, l=50, m=100, a=250),
    "Chain Lightning - Quantity": _sv("Chain Lightning - Quantity", "Core", "count", e=1, l=2, m=3, a=4),
    "Chain Lightning - Chance": _sv("Chain Lightning - Chance", "Core", "pct", c=2, r=4, e=6, l=9, m=12, a=15),
}


SUBSTATS_BY_SLOT: Dict[str, Dict[str, SubstatDef]] = {
    "Cannon": CANNON_SUBSTATS,
    "Armor": ARMOR_SUBSTATS,
    "Generator": GENERATOR_SUBSTATS,
    "Core": CORE_SUBSTATS,
}


def assist_efficiency_multiplier(main_mult: float, eff_stones_pct: float, eff_lab_pct: float) -> float:
    """Effective Paths assist multiplier formula (as observed).

    Given the *full* main multiplier of the assist module (e.g. 2.51x),
    and 'Multiplier Efficiency' from stones and lab (in percent points, e.g. 10 for 10%),
    returns the multiplier applied to the assist main effect.

    Formula:
      ((main_mult - 1) * (1 + eff_stones + eff_lab) * 0.01) + 1
    """
    return ((main_mult - 1.0) * (1.0 + eff_stones_pct + eff_lab_pct) * 0.01) + 1.0


def assist_substat_effect(raw_substat_value: float, substat_efficiency_pct: float) -> float:
    """Assist slot substat contribution rule.

    If assist substat efficiency is 10%, a +4% roll contributes +0.4%.
    """
    return raw_substat_value * (substat_efficiency_pct * 0.01)

# ---------------------------------------------------------------------------
# Compatibility aliases
#
# Some earlier TowerSim branches referenced `SUBSTAT_TABLES` and `SubstatCap`.
# The current baseline uses `SUBSTATS_BY_SLOT` and `SubstatDef`.
# We keep these aliases to avoid import breakage while the codebase is unified.
# ---------------------------------------------------------------------------

# Alias: older name used by towersim.modules
SUBSTAT_TABLES = SUBSTATS_BY_SLOT

from dataclasses import dataclass

@dataclass(frozen=True)
class SubstatCap:
    """Compatibility placeholder.

    NOTE: The authoritative per-substat roll ranges live in `SubstatDef`.
    This is retained only to satisfy historical imports.
    """
    min_value: float
    max_value: float
