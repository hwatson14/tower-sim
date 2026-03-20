from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.libs.workshop_lib import WorkshopTables, load_workshop_tables, workshop_value
from tower_sim.loaders.table_paths import resolve_table_path
import yaml
from tower_sim.registry.stat_registry import Phase
from tower_sim.util.account_snapshot import AccountSnapshot, WorkshopEntrySnapshot
from tower_sim.engines.free_upgrades import FreeUpgradeChances
from tower_sim.engines.workshop_progression import WSCategory, WorkshopStat, simulate_workshop_progression, uniform_allocation
from tower_sim.libs.bots_lib import get_bot_attribute
from tower_sim.libs.labs_lib import load_labs_values
from tower_sim.loaders.wiki.enemy_level_skip import workshop_level_to_chance
from tower_sim.libs.assist_efficiency import AssistEfficiencyInputs, apply_bonus_eff_to_main_effect, compute_efficiencies
from tower_sim.libs.modules_library import Rarity, SUBSTAT_TABLES, UNIQUE_EFFECTS
from tower_sim.loaders.wiki.assist_module_labs import AssistLabLevels
from tower_sim.loaders.wiki.cards import CardEffect, get_card_effect
from tower_sim.loaders.wiki.module_rules import max_active_substats_for_module_level
from tower_sim.util.account_snapshot import ModuleSnapshot

@dataclass(frozen=True)
class CompiledStatInputs:
    stat_inputs: List[StatInput]
    missing: List[str]


@dataclass(frozen=True)
class CompiledBaselineLoadout:
    stat_inputs: List[StatInput]
    missing: List[str]
    module_contribution_ledger: List[Dict[str, object]]
    layer_gaps: List[str]


class StatInputCompilerError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkshopStatSpec:
    stat_id: str
    wsvalues_key: Optional[str] = None
    dvt_keys: Tuple[str, ...] = ()


@dataclass(frozen=True)
class UWTrackSpec:
    stat_id: str
    csv_file: Optional[str] = None
    dvt_value_column: Optional[str] = None
    dvt_cost_column: Optional[str] = None


_UW_LEVEL_RE = re.compile(r"^(\d+)")
_UW_NEXT_COST_RE = re.compile(r"\bNext\s+([0-9]+(?:\.[0-9]+)?)")


_WORKSHOP_STAT_SPECS: Dict[str, WorkshopStatSpec] = {
    "Damage": WorkshopStatSpec(stat_id="workshop_damage", wsvalues_key="Damage"),
    "Health": WorkshopStatSpec(stat_id="workshop_health", wsvalues_key="Health"),
    "Health Regen": WorkshopStatSpec(
        stat_id="workshop_health_regen",
        wsvalues_key="HPregen",
        dvt_keys=("Health Regen",),
    ),
    "Defense Absolute": WorkshopStatSpec(
        stat_id="workshop_defense_absolute",
        wsvalues_key="DefAbs",
        dvt_keys=("Defense Absolute",),
    ),
    "Damage / Meter": WorkshopStatSpec(
        stat_id="workshop_damage_per_meter",
        wsvalues_key="Damage / Meter",
        dvt_keys=("Damage / Meter", "Damage/Meter"),
    ),
    "Damage/Meter": WorkshopStatSpec(
        stat_id="workshop_damage_per_meter",
        wsvalues_key="Damage / Meter",
        dvt_keys=("Damage / Meter", "Damage/Meter"),
    ),
    "Lifesteal": WorkshopStatSpec(stat_id="workshop_lifesteal", wsvalues_key="Lifesteal"),
    "Attack Speed": WorkshopStatSpec(stat_id="workshop_attack_speed"),
    "Critical Factor": WorkshopStatSpec(
        stat_id="workshop_critical_factor", dvt_keys=("Critical Factor",)
    ),
    "Super Crit Mult": WorkshopStatSpec(
        stat_id="workshop_super_crit_mult", dvt_keys=("Super Crit Mult",)
    ),
    "Critical Chance": WorkshopStatSpec(stat_id="workshop_critical_chance"),
    "Range": WorkshopStatSpec(stat_id="workshop_range_meters"),
    "Defense %": WorkshopStatSpec(stat_id="workshop_defense_percent"),
    "Thorn Damage": WorkshopStatSpec(stat_id="workshop_thorn_damage"),
    "Death Defy": WorkshopStatSpec(stat_id="workshop_death_defy"),
    "Wall Regen": WorkshopStatSpec(stat_id="workshop_wall_regen"),
    "Wall Fortification": WorkshopStatSpec(stat_id="workshop_wall_fortification"),
    "Cash / Wave": WorkshopStatSpec(stat_id="workshop_cash_per_wave"),
    "Coin / Wave": WorkshopStatSpec(stat_id="workshop_coins_per_wave"),
    "Interest / Wave": WorkshopStatSpec(stat_id="workshop_interest"),
    "Max Recovery": WorkshopStatSpec(stat_id="workshop_max_recovery"),
    "Recovery Package Chance": WorkshopStatSpec(stat_id="workshop_recovery_packages"),
    "Land Mine Damage": WorkshopStatSpec(
        stat_id="workshop_land_mine_damage", dvt_keys=("Land Mine Damage",)
    ),
    "Land Mine Chance": WorkshopStatSpec(stat_id="workshop_land_mine_chance"),
    "Land Mine Radius": WorkshopStatSpec(stat_id="workshop_land_mine_radius"),
    "Orbs": WorkshopStatSpec(stat_id="workshop_orbs"),
    "Orb Speed": WorkshopStatSpec(stat_id="workshop_orb_speed"),
    "Package Chance": WorkshopStatSpec(stat_id="workshop_package_chance"),
    "Wall Rebuild": WorkshopStatSpec(stat_id="workshop_wall_rebuild"),
    "Coins per Kill": WorkshopStatSpec(
        stat_id="workshop_coins_per_kill_bonus",
        dvt_keys=("Coin / Kill Bonus", "Coins per Kill"),
    ),
    "Coin / Kill Bonus": WorkshopStatSpec(
        stat_id="workshop_coins_per_kill_bonus",
        dvt_keys=("Coin / Kill Bonus",),
    ),
    "Wall Health": WorkshopStatSpec(stat_id="workshop_wall_health"),
    "Orb Size": WorkshopStatSpec(stat_id="workshop_orb_size", dvt_keys=("Orb Size",)),
    "Cash Bonus": WorkshopStatSpec(stat_id="workshop_cash_bonus", dvt_keys=("Cash Bonus",)),
    "Coin Bonus": WorkshopStatSpec(
        stat_id="workshop_coins_per_kill_bonus", dvt_keys=("Coin Bonus",)
    ),
    "Cells / Kill Bonus": WorkshopStatSpec(
        stat_id="workshop_cells_per_kill_bonus", dvt_keys=("Cells / Kill Bonus",)
    ),
    "Free Upgrades": WorkshopStatSpec(stat_id="workshop_free_upgrades", dvt_keys=("Free Upgrades",)),
    "Free Attack Upgrade": WorkshopStatSpec(stat_id="workshop_free_attack_upgrade"),
    "Free Defense Upgrade": WorkshopStatSpec(stat_id="workshop_free_defense_upgrade"),
    "Free Utility Upgrade": WorkshopStatSpec(stat_id="workshop_free_utility_upgrade"),
    "Recovery Package": WorkshopStatSpec(
        stat_id="workshop_recovery_packages", dvt_keys=("Recovery Package",)
    ),
    "Enemy Level Skip": WorkshopStatSpec(
        stat_id="workshop_enemy_level_skip", dvt_keys=("Enemy Level Skip",)
    ),
    "Enemy Attack Level Skip": WorkshopStatSpec(stat_id="workshop_enemy_attack_level_skip"),
    "Enemy Health Level Skip": WorkshopStatSpec(stat_id="workshop_enemy_health_level_skip"),
    "Rend Armor": WorkshopStatSpec(stat_id="workshop_rend_armor", dvt_keys=("Rend Armor",)),
    "Rend Armor Chance": WorkshopStatSpec(stat_id="workshop_rend_armor_chance"),
    "Rend Armor Mult": WorkshopStatSpec(stat_id="workshop_rend_armor_mult"),
    "Knockback Chance": WorkshopStatSpec(stat_id="workshop_knockback_chance"),
    "Knockback Force": WorkshopStatSpec(stat_id="workshop_knockback_force"),
    "Shockwave Size": WorkshopStatSpec(stat_id="workshop_shockwave_size"),
    "Shockwave Frequency": WorkshopStatSpec(stat_id="workshop_shockwave_frequency"),
    "Multishot Chance": WorkshopStatSpec(stat_id="workshop_multishot_chance"),
    "Multishot Targets": WorkshopStatSpec(stat_id="workshop_multishot_targets"),
    "Rapid Fire Chance": WorkshopStatSpec(stat_id="workshop_rapid_fire_chance"),
    "Rapid Fire Duration": WorkshopStatSpec(stat_id="workshop_rapid_fire_duration"),
    "Bounce Shot Chance": WorkshopStatSpec(stat_id="workshop_bounce_shot_chance"),
    "Bounce Shot Targets": WorkshopStatSpec(stat_id="workshop_bounce_shot_targets"),
    "Bounce Shot Range": WorkshopStatSpec(stat_id="workshop_bounce_shot_range"),
    "Super Critical Chance": WorkshopStatSpec(stat_id="workshop_super_crit_chance"),
    "Super Critical Mult": WorkshopStatSpec(stat_id="workshop_super_crit_mult_alt"),
    "Recovery Amount": WorkshopStatSpec(stat_id="workshop_recovery_amount"),
    "Max Amount": WorkshopStatSpec(stat_id="workshop_max_recovery"),
}

_WORKSHOP_CANONICAL_ALIASES: Dict[str, str] = {
    "Damage": "tower_damage",
    "Health": "tower_hp",
    "Health Regen": "tower_regen",
    "Absolute Defense": "tower_defense_absolute",
    "Damage / Meter": "tower_damage_per_meter_multiplier",
    "Lifesteal": "tower_lifesteal_pct",
    "Attack Speed": "tower_attack_speed",
    "Critical Factor": "tower_crit_multiplier",
    "Critical Chance": "tower_crit_chance_pct",
    "Range": "tower_range_m",
    "Defense %": "tower_defense_pct",
    "Thorn Damage": "tower_thorns_damage_pct",
    "Death Defy": "tower_death_defy_chance_pct",
    "Cash / Wave": "cash_per_wave",
    "Coin / Wave": "coins_per_wave",
    "Interest / Wave": "interest_per_wave_pct",
    "Max Recovery": "max_recovery_multiplier",
    "Recovery Package Chance": "package_chance_pct",
    "Land Mine Damage": "tower_land_mine_damage",
    "Land Mine Chance": "tower_land_mine_chance_pct",
    "Land Mine Radius": "tower_land_mine_radius_m",
    "Orbs": "tower_orb_count",
    "Orb Speed": "tower_orb_speed_rpm",
    "Package Chance": "package_chance_pct",
    "Wall Rebuild": "wall_rebuild_seconds",
    "Coins / Kill Bonus": "coin_kill_multiplier",
    "Cash Bonus": "cash_kill_multiplier",
    "Coin Bonus": "coin_kill_multiplier",
    "Free Attack Upgrade": "free_attack_upgrade_chance_pct",
    "Free Defense Upgrade": "free_defense_upgrade_chance_pct",
    "Free Utility Upgrade": "free_utility_upgrade_chance_pct",
    "Enemy Attack Level Skip": "enemy_attack_level_skip_pct",
    "Enemy Health Level Skip": "enemy_health_level_skip_pct",
    "Rend Armor Chance": "tower_rend_armor_chance_pct",
    "Rend Armor Mult": "tower_rend_armor_multiplier",
    "Knockback Chance": "tower_knockback_chance_pct",
    "Knockback Force": "tower_knockback_force",
    "Shockwave Size": "tower_shockwave_size_m",
    "Shockwave Frequency": "tower_shockwave_interval_seconds",
    "Multishot Chance": "tower_multishot_chance_pct",
    "Multishot Targets": "tower_multishot_targets",
    "Rapid Fire Chance": "tower_rapid_fire_chance_pct",
    "Rapid Fire Duration": "tower_rapid_fire_duration_seconds",
    "Bounce Shot Chance": "tower_bounce_shot_chance_pct",
    "Bounce Shot Targets": "tower_bounce_shot_targets",
    "Bounce Shot Range": "tower_bounce_shot_range_m",
    "Super Critical Chance": "tower_supercrit_chance_pct",
    "Super Critical Mult": "tower_supercrit_multiplier",
    "Recovery Amount": "recovery_amount_pct",
}



def _canonicalize_workshop_values(values: Dict[str, float]) -> Dict[str, float]:
    """Emit canonical aliases for workshop-derived values.

    Canonical max-wave/runtime consumers read survivability stats by canonical IDs,
    while workshop progression still tracks source-specific `workshop_*` IDs.
    Keep both representations deterministic and in-sync.
    """

    canonicalized = dict(values)
    for workshop_name, canonical_stat_id in _WORKSHOP_CANONICAL_ALIASES.items():
        spec = _WORKSHOP_STAT_SPECS.get(workshop_name)
        if spec is None:
            continue
        source_value = canonicalized.get(spec.stat_id)
        if source_value is None:
            continue
        canonicalized[canonical_stat_id] = float(source_value)
    return canonicalized


def _pct(value: float) -> float:
    return value / 100.0


def _workshop_recovery_package_chance(level: int) -> float | None:
    if level == 0:
        return 0.0
    if level < 0 or level > 60:
        return None
    return 0.06 + (0.004 * (level - 1))


def _workshop_land_mine_chance(level: int) -> float | None:
    """Return land mine proc chance as a fraction.

    Convention: workshop ``coin_level`` is treated as upgrade-count-applied in [0, 50].
    At 50 applied upgrades, chance reaches the documented 30.00% cap.
    """

    return _bounded_linear(
        level,
        min_level=0,
        max_level=50,
        base=0.0,
        per_level=0.006,
    )


def _bounded_linear(level: int, *, min_level: int, max_level: int, base: float, per_level: float) -> float | None:
    if level < min_level or level > max_level:
        return None
    return base + (per_level * level)


_WORKSHOP_FORMULAS: Dict[str, callable] = {
    "Multishot Chance": lambda level: _pct(0.5 * level),
    "Multishot Targets": lambda level: 2 + level,
    "Rapid Fire Chance": lambda level: _pct(0.4 * level),
    "Rapid Fire Duration": lambda level: 0.6 + 0.05 * level,
    "Bounce Shot Chance": lambda level: _pct(0.8 * level),
    "Bounce Shot Targets": lambda level: 1 + level,
    "Bounce Shot Range": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=60,
        base=2.0,
        per_level=0.1,
    ),
    "Super Critical Chance": lambda level: _pct(0.2 * level),
    "Super Critical Mult": lambda level: 1.2 + 0.1 * level,
    "Rend Armor Chance": lambda level: _pct(0.1 + 0.1 * level),
    "Rend Armor Mult": lambda level: 0.001 + 0.001 * level,
    "Knockback Chance": lambda level: _pct(1.0 * level),
    "Knockback Force": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=40,
        base=0.4,
        per_level=0.142,
    ),
    "Shockwave Size": lambda level: 0.6 + 0.05 * level,
    "Shockwave Frequency": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=40,
        base=20.0,
        per_level=-0.15,
    ),
    "Land Mine Chance": _workshop_land_mine_chance,
    "Land Mine Damage": lambda level: 1 + _pct(10.0 * level),
    "Land Mine Radius": lambda level: 0.5 + 0.02 * level,
    "Orbs": lambda level: level,
    "Orb Speed": lambda level: 0.4 + 0.15 * level,
    "Recovery Amount": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=300,
        base=0.14,
        per_level=0.004,
    ),
    "Package Chance": lambda level: _pct(6 + 0.4 * level),
    "Recovery Package Chance": _workshop_recovery_package_chance,
    "Wall Rebuild": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=300,
        base=1200.0,
        per_level=-2.0,
    ),
    "Wall Regen": lambda level: _bounded_linear(level, min_level=0, max_level=30, base=0.0, per_level=0.1),
    "Wall Fortification": lambda level: _bounded_linear(level, min_level=0, max_level=60, base=0.0, per_level=0.2),
    "Coins per Kill": lambda level: 1 + _pct(1.0 * level),
    "Coin / Kill Bonus": lambda level: 1 + _pct(1.0 * level),
    "Cash Bonus": lambda level: 1 + _pct(1.0 * level),
    "Critical Factor": lambda level: 1.2 + 0.1 * level,
    "Enemy Attack Level Skip": lambda level: workshop_level_to_chance(level),
    "Enemy Health Level Skip": lambda level: workshop_level_to_chance(level),
    "Free Attack Upgrade": lambda level: _pct(0.5 * level),
    "Free Defense Upgrade": lambda level: _pct(0.5 * level),
    "Free Utility Upgrade": lambda level: _pct(0.5 * level),
    "Max Amount": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=500,
        base=1.0,
        per_level=0.031,
    ),
    "Max Recovery": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=500,
        base=1.0,
        per_level=0.031,
    ),
    "Attack Speed": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=99,
        base=1.0,
        per_level=0.05,
    ),
    "Wall Health": lambda level: _bounded_linear(
        level,
        min_level=0,
        max_level=1800,
        base=0.2,
        per_level=0.001,
    ),
    "Cash / Wave": lambda level: 4 * level,
    "Coin / Wave": lambda level: 1 + level,
    "Critical Chance": lambda level: _pct(1 + 1 * level),
    "Death Defy": lambda level: _pct(0.4 * level),
    "Defense %": lambda level: _pct(0.5 * level),
    "Interest / Wave": lambda level: _pct(0.06 * level),
    "Range": lambda level: 30 + (0.5 * level),
    "Thorn Damage": lambda level: _pct(1 * level),
}




_WORKSHOP_LAB_DELTA_STATS = {
    "Enemy Attack Level Skip",
    "Enemy Health Level Skip",
    "Defense %",
}

_UW_LAB_ADDITIVE_STATS = {
    "uw_chrono_field_duration": "Chrono Field Duration",
}

_UW_LAB_CANONICAL_ID = {
    "uw_chrono_field_duration": "LAB_CHRONO_FIELD_DURATION",
}

_UW_TRACK_SPECS: Dict[str, Dict[str, UWTrackSpec]] = {
    "Chain Lightning": {
        "Damage": UWTrackSpec(stat_id="uw_chain_lightning_damage", csv_file="AUW_CL_DMG_ARRAY.csv"),
        "Quantity": UWTrackSpec(stat_id="uw_chain_lightning_quantity", csv_file="AUW_CL_QTY_ARRAY.csv"),
        "Chance": UWTrackSpec(stat_id="uw_chain_lightning_chance", csv_file="AUW_CL_Chance_ARRAY.csv"),
        "Smite": UWTrackSpec(stat_id="uw_chain_lightning_smite", csv_file="AUW_CL_SMITE_ARRAY.csv"),
    },
    "Smart Missiles": {
        "Damage": UWTrackSpec(stat_id="uw_smart_missiles_damage", csv_file="AUW_SM_DMG_ARRAY.csv"),
        "Quantity": UWTrackSpec(stat_id="uw_smart_missiles_quantity", csv_file="AUW_SM_QTY_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_smart_missiles_cooldown", csv_file="AUW_SM_CD_ARRAY.csv"),
        "Cover Fire": UWTrackSpec(stat_id="uw_smart_missiles_cover_fire", csv_file="AUW_SM_CF_ARRAY.csv"),
    },
    "Death Wave": {
        "Damage": UWTrackSpec(stat_id="uw_death_wave_damage", csv_file="AUW_DW_DMG_ARRAY.csv"),
        "Quantity": UWTrackSpec(stat_id="uw_death_wave_quantity", csv_file="AUW_DW_QTY_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_death_wave_cooldown", csv_file="AUW_DW_CD_ARRAY.csv"),
        "Kill Wall": UWTrackSpec(stat_id="uw_death_wave_kill_wall", csv_file="AUW_DW_PLUS_ARRAY.csv"),
    },
    "Chrono Field": {
        "Duration": UWTrackSpec(stat_id="uw_chrono_field_duration", csv_file="AUW_CF_DUR_ARRAY.csv"),
        "Speed Reduction": UWTrackSpec(
            stat_id="uw_chrono_field_speed_reduction", csv_file="AUW_CF_SR_ARRAY.csv"
        ),
        "Cooldown": UWTrackSpec(stat_id="uw_chrono_field_cooldown", csv_file="AUW_CF_CD_ARRAY.csv"),
        "Chrono Loop": UWTrackSpec(stat_id="uw_chrono_field_chrono_loop", csv_file="AUW_CF_CL_ARRAY.csv"),
    },
    "Inner Land Mines": {
        "Damage": UWTrackSpec(stat_id="uw_inner_land_mines_damage", csv_file="AUW_ILM_DMG_ARRAY.csv"),
        "Quantity": UWTrackSpec(stat_id="uw_inner_land_mines_quantity", csv_file="AUW_ILM_QTY_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_inner_land_mines_cooldown", csv_file="AUW_ILM_CD_ARRAY.csv"),
        "Charged Mines": UWTrackSpec(
            stat_id="uw_inner_land_mines_charged_mines", csv_file="AUW_ILM_PLUS_ARRAY.csv"
        ),
    },
    "Golden Tower": {
        "Multiplier": UWTrackSpec(stat_id="uw_golden_tower_multiplier", csv_file="AUW_GT_MULT_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_golden_tower_cooldown", csv_file="AUW_GT_CD_ARRAY.csv"),
        "Golden Combo": UWTrackSpec(stat_id="uw_golden_tower_golden_combo", csv_file="AUW_GT_GC_ARRAY.csv"),
        "Duration": UWTrackSpec(
            stat_id="uw_golden_tower_duration",
            dvt_value_column="CI",
            dvt_cost_column="CJ",
        ),
    },
    "Poison Swamp": {
        "Damage": UWTrackSpec(stat_id="uw_poison_swamp_damage", csv_file="AUW_PS_DMG_ARRAY.csv"),
        "Duration": UWTrackSpec(stat_id="uw_poison_swamp_duration", csv_file="AUW_PS_Duration_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_poison_swamp_cooldown", csv_file="AUW_PS_CD_ARRAY.csv"),
        "Death Creep": UWTrackSpec(stat_id="uw_poison_swamp_death_creep", csv_file="AUW_PS_PLUS_ARRAY.csv"),
    },
    "Black Hole": {
        "Size": UWTrackSpec(stat_id="uw_black_hole_size", csv_file="AUW_BH_SIZE_ARRAY.csv"),
        "Duration": UWTrackSpec(stat_id="uw_black_hole_duration", csv_file="AUW_BH_DUR_ARRAY.csv"),
        "Cooldown": UWTrackSpec(stat_id="uw_black_hole_cooldown", csv_file="AUW_BH_CD_ARRAY.csv"),
        "Consume": UWTrackSpec(
            stat_id="uw_black_hole_consume",
            dvt_value_column="DO",
            dvt_cost_column="DP",
        ),
    },
    "Spotlight": {
        "Multiplier": UWTrackSpec(stat_id="uw_spotlight_multiplier", csv_file="AUW_SL_DMG_ARRAY.csv"),
        "Angle": UWTrackSpec(stat_id="uw_spotlight_angle", csv_file="AUW_SL_ANGLE_ARRAY.csv"),
        "Quantity": UWTrackSpec(stat_id="uw_spotlight_quantity", csv_file="AUW_SL_QTY_ARRAY.csv"),
        "Light Range": UWTrackSpec(stat_id="uw_spotlight_light_range", csv_file="AUW_SL_LR_ARRAY.csv"),
    },
}


@dataclass(frozen=True)
class ModuleSubstat:
    name: str
    rarity: Rarity
    value: float


@dataclass(frozen=True)
class ModuleRecord:
    name: str
    slot: str
    rarity: Rarity
    level: int
    main_effect: float
    substats: List[ModuleSubstat]


@dataclass(frozen=True)
class ModuleLoadout:
    slot: str
    primary: Optional[str]
    assist: Optional[str]
    assist_enabled: bool
    assist_stone_level: int
    assist_cap_rarity: Optional[Rarity]


@dataclass(frozen=True)
class ModuleBlock:
    loadout_by_context: Dict[str, ModuleLoadout]
    inventory: Dict[str, ModuleRecord]


_SUBSTAT_MAPPINGS: Dict[str, tuple[str, str]] = {
    "Attack Speed": ("tower_attack_speed", "multiplier"),
    "Black Hole - Cooldown": ("uw_black_hole_cooldown", "delta"),
    "Black Hole - Duration": ("uw_black_hole_duration", "delta"),
    "Bounce Shot Chance": ("workshop_bounce_shot_chance", "delta"),
    "Cash Bonus": ("cash_bonus", "delta"),
    "Chain Lightning - Chance": ("chain_lightning_chance", "delta"),
    "Chain Lightning - Damage": ("chain_lightning_damage", "delta"),
    "Chain Lightning - Quantity": ("chain_lightning_quantity", "delta"),
    "Chrono Field - Cooldown": ("chrono_field_cooldown", "delta"),
    "Chrono Field - Duration": ("chrono_field_duration", "delta"),
    "Chrono Field - Speed Reduction": ("chrono_field_speed_reduction", "delta"),
    "Crit Chance": ("tower_crit_chance", "delta"),
    "Crit Factor": ("tower_crit_multiplier", "delta"),
    "Damage / Meter": ("damage_per_meter", "delta"),
    "Death Wave - Cooldown": ("death_wave_cooldown", "delta"),
    "Death Wave - Damage": ("death_wave_damage", "delta"),
    "Death Wave - Quantity": ("death_wave_quantity", "delta"),
    "Defense": ("def_pct", "delta"),
    "Defense Absolute": ("defense_absolute", "delta"),
    "Enemy Attack Level Skip": ("eals_pct", "delta"),
    "Enemy Health Level Skip": ("ehls_pct", "delta"),
    "Free Attack Upgrade": ("free_attack_upgrade", "delta"),
    "Free Defense Upgrade": ("free_defense_upgrade", "delta"),
    "Free Utility Upgrade": ("free_utility_upgrade", "delta"),
    "Golden Tower - Bonus": ("golden_tower_multiplier", "delta"),
    "Golden Tower - Cooldown": ("golden_tower_cooldown", "delta"),
    "Golden Tower - Duration": ("golden_tower_duration", "delta"),
    "Health Regen": ("tower_regen", "multiplier"),
    "Inner Land Mines - Cooldown": ("inner_land_mines_cooldown", "delta"),
    "Inner Land Mines - Damage": ("inner_land_mines_damage", "delta"),
    "Inner Land Mines - Quantity": ("inner_land_mines_quantity", "delta"),
    "Land Mine Chance": ("workshop_land_mine_chance", "delta"),
    "Knockback Force": ("tower_knockback_force", "delta"),
    "Multishot Targets": ("workshop_multishot_targets", "delta"),
    "Orb Speed": ("orb_speed", "delta"),
    "Poison Swamp - Cooldown": ("poison_swamp_cooldown", "delta"),
    "Poison Swamp - Damage": ("poison_swamp_damage", "delta"),
    "Poison Swamp - Duration": ("poison_swamp_duration", "delta"),
    "Recovery Amount": ("recovery_amount", "delta"),
    "Recovery Package Chance": ("workshop_package_chance", "delta"),
    "Smart Missiles - Cooldown": ("smart_missiles_cooldown", "delta"),
    "Smart Missiles - Damage": ("smart_missiles_damage", "delta"),
    "Smart Missiles - Quantity": ("smart_missiles_quantity", "delta"),
    "Spotlight - Angle": ("spotlight_angle", "delta"),
    "Spotlight - Bonus": ("spotlight_multiplier", "delta"),
    "Super Crit Chance": ("super_crit_chance", "delta"),
    "Super Crit Multi": ("super_crit_mult", "delta"),
    "Thorns Damage": ("thorns_damage_mult", "delta"),
    "Wall Health": ("wall_hp", "multiplier"),
    "Wall Rebuild": ("wall_rebuild", "delta"),
    "Coins / Kill Bonus": ("workshop_coins_per_kill_bonus", "delta"),
}


_WORKSHOP_THORNS_MAX_LEVEL = 99  # Wiki excerpt in prompt: 99 upgrades at +1% each.
_WORKSHOP_THORNS_PER_LEVEL = 0.01  # Wiki excerpt in prompt: +1% per workshop level.


_CARD_NOOP_CANONICALS = {
    # Known cards whose mechanics are modeled in other surfaces (runtime/events/econ)
    # and therefore intentionally contribute no start-of-run survivability scalar here.
    "CARD_AREA_OF_EFFECT",
        "CARD_CRITICAL_COIN",
    "CARD_DEATH_RAY",
    "CARD_DEMON_MODE",
    "CARD_ENEMY_BALANCE",
    "CARD_ENERGY_NET",
    "CARD_ENERGY_SHIELD",
    "CARD_EXTRA_ORBS",
    "CARD_INTRO_SPRINT",
    "CARD_LAND_MINE_STUN",
    "CARD_NUKE",
    "CARD_SECOND_WIND",
    "CARD_SLOW_AURA",
    "CARD_SUPER_TOWER",
        "CARD_WAVE_ACCELERATOR",
    "CARD_WAVE_SKIP",
}

SLOT_ORDER = {
    0: "Cannon",
    1: "Armor",
    2: "Generator",
    3: "Core",
}



def _parse_module_blocks(ids_snapshot: AccountSnapshot) -> Dict[str, ModuleBlock]:
    blocks: Dict[str, ModuleBlock] = {}
    for slot_name in SLOT_ORDER.values():
        system_state = ids_snapshot.module_system_state.get(slot_name)
        if system_state is None:
            raise StatInputCompilerError(
                f"Missing module system state for {slot_name!r}."
            )
        assist_cap = None
        if system_state.rarity_cap:
            assist_cap = _parse_rarity(system_state.rarity_cap)
        loadout_by_context: Dict[str, ModuleLoadout] = {}
        for preset_name, preset in ids_snapshot.module_presets.items():
            selection = preset.get(slot_name)
            if selection is None:
                raise StatInputCompilerError(
                    f"Missing module preset {preset_name} for {slot_name!r}."
                )
            loadout_by_context[preset_name] = ModuleLoadout(
                slot=slot_name,
                primary=selection.primary,
                assist=selection.assist,
                assist_enabled=system_state.assist_unlocked,
                assist_stone_level=system_state.assist_level,
                assist_cap_rarity=assist_cap,
            )
        inventory: Dict[str, ModuleRecord] = {}
        for name, entry in ids_snapshot.modules_inventory.items():
            if entry.slot_type != slot_name:
                continue
            inventory[name] = _module_record_from_snapshot(entry, slot_name)
        blocks[slot_name] = ModuleBlock(
            loadout_by_context=loadout_by_context,
            inventory=inventory,
        )
    return blocks


def _module_record_from_snapshot(
    entry: ModuleSnapshot, slot_name: str
) -> ModuleRecord:
    if entry.rarity is None:
        raise StatInputCompilerError(
            f"Missing rarity for module {entry.name!r} in {slot_name}."
        )
    rarity = _parse_rarity(entry.rarity)
    if rarity is None:
        raise StatInputCompilerError(
            f"Missing rarity for module {entry.name!r} in {slot_name}."
        )
    if entry.level is None:
        raise StatInputCompilerError(
            f"Missing level for module {entry.name!r} in {slot_name}."
        )
    if entry.stat is None:
        raise StatInputCompilerError(
            f"Missing main effect for module {entry.name!r} in {slot_name}."
        )
    try:
        main_effect = float(entry.stat)
    except ValueError as exc:
        raise StatInputCompilerError(
            f"Invalid main effect for module {entry.name!r}: {entry.stat!r}"
        ) from exc
    substats: List[ModuleSubstat] = []
    for substat in entry.substats:
        if not substat.stat_name:
            continue
        normalized = _normalize_substat_name(substat.stat_name)
        if substat.rarity is None:
            raw_value = substat.value_num
            if raw_value is None:
                raw_value = _parse_substat_display_number(substat.value_display)
            if raw_value is None:
                continue
            rarity_value = Rarity.COMMON
            substat_value = _coerce_substat_value_from_number(slot_name, normalized, raw_value)
        else:
            rarity_value = _parse_rarity(substat.rarity)
            if rarity_value is None:
                raise StatInputCompilerError(
                    f"Missing substat rarity for {substat.stat_name!r} in {entry.name!r}."
                )
            substat_value = _resolve_substat_value(slot_name, normalized, rarity_value)
        substats.append(
            ModuleSubstat(
                name=normalized,
                rarity=rarity_value,
                value=substat_value,
            )
        )
    return ModuleRecord(
        name=entry.name,
        slot=slot_name,
        rarity=rarity,
        level=entry.level,
        main_effect=main_effect,
        substats=substats,
    )


def _resolve_module(
    module_name: str,
    slot_name: str,
    inventory: Mapping[str, ModuleRecord],
) -> ModuleRecord:
    if module_name not in inventory:
        raise StatInputCompilerError(
            f"Unknown module {module_name!r} for slot {slot_name!r}."
        )
    return inventory[module_name]


def _resolve_substat_value(slot: str, substat_name: str, rarity: Rarity) -> float:
    if slot not in SUBSTAT_TABLES:
        raise StatInputCompilerError(f"Missing substat table for slot {slot!r}.")
    slot_table = SUBSTAT_TABLES[slot]
    if substat_name not in slot_table:
        raise StatInputCompilerError(
            f"Unknown substat {substat_name!r} for slot {slot!r}."
        )
    entry = slot_table[substat_name]
    if rarity not in entry.value:
        raise StatInputCompilerError(
            f"Missing substat rarity {rarity.value!r} for {substat_name!r}."
        )
    raw = entry.value[rarity]
    if entry.unit == "pct":
        return float(raw) / 100.0
    if entry.unit == "mult":
        return float(raw)
    if entry.unit == "flat":
        return float(raw)
    if entry.unit == "count":
        return float(raw)
    if entry.unit == "sec":
        return float(raw)
    raise StatInputCompilerError(
        f"Unsupported unit {entry.unit!r} for substat {substat_name!r}."
    )


def _parse_substat_display_number(value_display: str | None) -> Optional[float]:
    if value_display is None:
        return None
    match = re.search(r"[-+]?[0-9]+(?:\.[0-9]+)?", value_display)
    if match is None:
        return None
    return float(match.group(0))


def _coerce_substat_value_from_number(slot: str, substat_name: str, raw_value: float) -> float:
    if slot not in SUBSTAT_TABLES:
        raise StatInputCompilerError(f"Missing substat table for slot {slot!r}.")
    slot_table = SUBSTAT_TABLES[slot]
    if substat_name not in slot_table:
        raise StatInputCompilerError(
            f"Unknown substat {substat_name!r} for slot {slot!r}."
        )
    entry = slot_table[substat_name]
    if entry.unit == "pct":
        return float(raw_value) / 100.0
    if entry.unit in {"mult", "flat", "count", "sec"}:
        return float(raw_value)
    raise StatInputCompilerError(
        f"Unsupported unit {entry.unit!r} for substat {substat_name!r}."
    )


def _apply_module_effects(
    accumulator: "_StatAccumulator",
    *,
    primary: ModuleRecord | None,
    assist: ModuleRecord | None,
    assist_enabled: bool,
    assist_level: int,
    assist_cap: Optional[Rarity],
    ids_snapshot: AccountSnapshot,
    allow_provisional: bool,
    slot: str,
) -> List[str]:
    if primary is None and assist is None:
        return []
    layer_gaps: List[str] = []
    assist_eff = _resolve_assist_efficiencies(
        labs=ids_snapshot.labs,
        slot=primary.slot if primary else assist.slot,
        assist_level=assist_level,
    )
    substat_eff = assist_eff.substat_eff

    if primary is not None and primary.slot == "Armor":
        multiplier = _armor_module_multiplier(
            ids_snapshot.labs,
            primary,
            assist if assist_enabled else None,
            assist_level,
            allow_provisional=allow_provisional,
        )
        accumulator.multiply("tower_hp", multiplier, "modules:armor_main_effect")
        accumulator.record_module_contribution(slot=slot, placement="primary", module_name=primary.name, layer="primary", target="tower_hp", value=multiplier, kind="multiplier")

    if primary is not None:
        _apply_slot_main_effect(
            accumulator,
            slot=slot,
            placement="primary",
            module_name=primary.name,
            module_slot=primary.slot,
            main_effect=primary.main_effect,
        )
        layer_gaps.extend(
            _apply_module_substats(
                accumulator,
                primary,
                is_assist=False,
                efficiency=1.0,
                slot=slot,
                placement="primary",
            )
        )
        if not _apply_unique_effects(accumulator, primary, is_assist=False, assist_cap=assist_cap, slot=slot, placement="primary"):
            layer_gaps.append(f"module_unique_unmapped:{slot}:primary:{primary.name}")
    if assist is not None and assist_enabled:
        assist_main_effect = apply_bonus_eff_to_main_effect(
            assist.main_effect,
            assist_eff.bonus_eff,
        )
        _apply_slot_main_effect(
            accumulator,
            slot=slot,
            placement="assist",
            module_name=assist.name,
            module_slot=assist.slot,
            main_effect=assist_main_effect,
        )
        layer_gaps.extend(
            _apply_module_substats(
                accumulator,
                assist,
                is_assist=True,
                efficiency=substat_eff,
                slot=slot,
                placement="assist",
            )
        )
        if not _apply_unique_effects(accumulator, assist, is_assist=True, assist_cap=assist_cap, slot=slot, placement="assist"):
            layer_gaps.append(f"module_unique_unmapped:{slot}:assist:{assist.name}")
    return layer_gaps


def _apply_slot_main_effect(
    accumulator: "_StatAccumulator",
    *,
    slot: str,
    placement: str,
    module_name: str,
    module_slot: str,
    main_effect: float,
) -> None:
    if module_slot == "Armor":
        return
    targets: tuple[str, ...]
    if module_slot == "Cannon":
        targets = ("tower_damage",)
    elif module_slot == "Generator":
        accumulator.record_module_contribution(
            slot=slot,
            placement=placement,
            module_name=module_name,
            layer="primary",
            target="module_primary_effect:generator_main_effect",
            value=main_effect,
            kind="behavior_binding",
        )
        return
    elif module_slot == "Core":
        targets = (
            "chain_lightning_damage",
            "smart_missiles_damage",
            "death_wave_damage",
            "inner_land_mines_damage",
            "poison_swamp_damage",
        )
    else:
        return
    for target in targets:
        accumulator.multiply(target, main_effect, f"modules:{module_slot.lower()}_main_effect")
        accumulator.record_module_contribution(
            slot=slot,
            placement=placement,
            module_name=module_name,
            layer="primary",
            target=target,
            value=main_effect,
            kind="multiplier",
        )


def _apply_module_substats(
    accumulator: "_StatAccumulator",
    module: ModuleRecord,
    *,
    is_assist: bool,
    efficiency: float,
    slot: str,
    placement: str,
) -> List[str]:
    active_count = max_active_substats_for_module_level(module.level)
    if active_count <= 0:
        accumulator.record_module_contribution(
            slot=slot,
            placement=placement,
            module_name=module.name,
            layer="substat",
            target="substats:none_active",
            value=0.0,
            kind="noop",
        )
        return []
    unmapped: List[str] = []
    for substat in module.substats[:active_count]:
        value = substat.value * (efficiency if is_assist else 1.0)
        mapping = _SUBSTAT_MAPPINGS.get(substat.name)
        if mapping is None:
            unmapped.append(
                f"module_substat_unmapped:{slot}:{placement}:{module.name}:{substat.name}"
            )
            continue
        stat_id, kind = mapping
        if kind == "multiplier":
            resolved = 1.0 + value
            accumulator.multiply(stat_id, resolved, f"modules:{stat_id}")
            accumulator.record_module_contribution(
                slot=slot,
                placement=placement,
                module_name=module.name,
                layer="substat",
                target=stat_id,
                value=resolved,
                kind="multiplier",
            )
            continue
        accumulator.add(stat_id, value, f"modules:{stat_id}")
        accumulator.record_module_contribution(
            slot=slot,
            placement=placement,
            module_name=module.name,
            layer="substat",
            target=stat_id,
            value=value,
            kind="delta",
        )
    return unmapped


def _apply_unique_effects(
    accumulator: "_StatAccumulator",
    module: ModuleRecord,
    *,
    is_assist: bool,
    assist_cap: Optional[Rarity],
    slot: str,
    placement: str,
) -> bool:
    effect = UNIQUE_EFFECTS.get(module.name)
    if effect is None:
        return False
    rarity = module.rarity
    if is_assist and assist_cap is not None:
        rarity = _cap_rarity(rarity, assist_cap)

    if effect.effect_name == "bot_range_bonus_m":
        value = effect.value[rarity]
        accumulator.add("bot_range", value, "modules:unique:bot_range")
        accumulator.record_module_contribution(
            slot=slot,
            placement=placement,
            module_name=module.name,
            layer="unique",
            target="bot_range",
            value=value,
            kind="delta",
        )
        return True

    if effect.effect_name != "wall_health_regen_mult_x":
        accumulator.record_module_contribution(slot=slot, placement=placement, module_name=module.name, layer="unique", target=f"uw_behavior:{effect.effect_name}", value=effect.value[rarity], kind="behavior_binding")
        return True

    multiplier = effect.value[rarity]
    accumulator.multiply("wall_hp", multiplier, "modules:unique:wall_health")
    accumulator.multiply("wall_regen", multiplier, "modules:unique:wall_regen")
    accumulator.record_module_contribution(slot=slot, placement=placement, module_name=module.name, layer="unique", target="wall_hp", value=multiplier, kind="multiplier")
    accumulator.record_module_contribution(slot=slot, placement=placement, module_name=module.name, layer="unique", target="wall_regen", value=multiplier, kind="multiplier")
    return True


def _resolve_assist_efficiencies(
    labs: Mapping[str, Optional[int]], slot: str, assist_level: int
) -> AssistEfficiencies:
    bonus_lab_key = f"Assist Module Bonus - {slot}"
    substat_lab_key = f"Assist Module Substats - {slot}"
    bonus_level = labs.get(bonus_lab_key)
    substat_level = labs.get(substat_lab_key)
    if bonus_level is None or substat_level is None:
        raise StatInputCompilerError(
            f"Missing assist lab levels for {slot!r} in IDS."
        )
    labs = AssistLabLevels(
        bonus_level=bonus_level,
        substat_level=substat_level,
    )
    stone_pct = _assist_stone_percent(assist_level)
    inputs = AssistEfficiencyInputs(
        stone_bonus_percent=stone_pct,
        stone_substat_percent=stone_pct,
        labs=labs,
    )
    return compute_efficiencies(inputs)


def _armor_module_multiplier(
    labs: Mapping[str, Optional[int]],
    primary: ModuleRecord,
    assist: ModuleRecord | None,
    assist_level: int,
    *,
    allow_provisional: bool,
) -> float:
    if primary.slot != "Armor":
        return 1.0
    if not allow_provisional:
        raise StatInputCompilerError(
            "Armor main-effect formula is EP-derived without a table. "
            "Set allow_provisional=True to apply it."
        )
    prim_bonus = primary.main_effect
    if assist is None:
        return prim_bonus
    if assist.slot != "Armor":
        raise StatInputCompilerError(
            f"Assist module {assist.name!r} is not an Armor module."
        )
    stone_pct = _assist_stone_percent(assist_level)
    lab_level = labs.get("Assist Module Bonus - Armor")
    if lab_level is None:
        raise StatInputCompilerError(
            "Missing Assist Module Bonus - Armor lab level in IDS."
        )
    labs = AssistLabLevels(
        bonus_level=lab_level,
        substat_level=0,
    )
    lab_pct = labs.bonus_percent
    assist_bonus = assist.main_effect
    assist_multiplier = ((assist_bonus - 1.0) * (1.0 + stone_pct + lab_pct) * 0.01) + 1.0
    return prim_bonus * assist_multiplier


def _assist_stone_percent(level: int) -> float:
    table_path = resolve_table_path("assist_stone_levels")
    if not table_path.exists():
        raise StatInputCompilerError(
            f"Missing assist stone table: {table_path}"
        )
    with table_path.open("r", encoding="utf-8") as handle:
        header = handle.readline()
        if not header:
            raise StatInputCompilerError("Assist stone table is empty.")
        for line in handle:
            parts = [cell.strip() for cell in line.split(",")]
            if len(parts) < 2:
                continue
            if int(float(parts[0])) == level:
                return float(parts[1])
    raise StatInputCompilerError(
        f"Assist stone table missing level {level}."
    )


def _apply_card_effects(
    accumulator: "_StatAccumulator",
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str,
    selected_cards: Iterable[str] | None,
) -> None:
    from tower_sim.registry.naming_contract import resolve_named_entity
    equipped = list(
        selected_cards or _resolve_equipped_cards(ids_snapshot, module_context)
    )
    for card_name in equipped:
        effect = _resolve_card_effect(card_name, ids_snapshot)
        if effect.card == "Health":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Health card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_hp", effect.value, "cards:health")
        elif effect.card == "Health Regen":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Health Regen card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_regen", effect.value, "cards:health_regen")
        elif effect.card == "Damage":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Damage card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_damage", effect.value, "cards:damage")
        elif effect.card == "Berserker":
            # Simplified deterministic modeling per product direction: cap to x8 damage while equipped.
            accumulator.multiply("tower_damage", 8.0, "cards:berserker")
        elif effect.card == "Ultimate Crit":
            if effect.unit != "percent":
                raise StatInputCompilerError(
                    f"Ultimate Crit card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_damage", 1.0 + effect.value, "cards:ultimate_crit")
        elif effect.card == "Attack Speed":
            if effect.unit == "percent":
                multiplier = 1.0 + effect.value
            elif effect.unit == "mult":
                multiplier = effect.value
            else:
                raise StatInputCompilerError(
                    f"Attack Speed card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("tower_attack_speed", multiplier, "cards:attack_speed")
        elif effect.card == "Critical Chance":
            if effect.unit != "percent":
                raise StatInputCompilerError(
                    f"Critical Chance card has unsupported unit {effect.unit!r}."
                )
            accumulator.add("tower_crit_chance", effect.value, "cards:critical_chance")
        elif effect.card == "Range":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Range card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("workshop_range_meters", effect.value, "cards:range")
        elif effect.card == "Cash":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Cash card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("workshop_cash_bonus", effect.value, "cards:cash")
        elif effect.card == "Coins":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Coins card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply(
                "workshop_coins_per_kill_bonus", effect.value, "cards:coins"
            )
        elif effect.card == "Free Upgrades":
            if effect.unit != "percent":
                raise StatInputCompilerError(
                    f"Free Upgrades card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply(
                "workshop_free_upgrades", 1.0 + effect.value, "cards:free_upgrades"
            )
        elif effect.card == "Recovery Package Chance":
            if effect.unit != "percent":
                raise StatInputCompilerError(
                    f"Recovery Package Chance card has unsupported unit {effect.unit!r}."
                )
            accumulator.add(
                "workshop_package_chance", effect.value, "cards:recovery_package_chance"
            )
        elif effect.card == "Extra Defense":
            if effect.unit != "percent":
                raise StatInputCompilerError(
                    f"Extra Defense card has unsupported unit {effect.unit!r}."
                )
            accumulator.add("def_pct", effect.value, "cards:extra_defense")
        elif effect.card == "Fortress":
            if effect.unit != "mult":
                raise StatInputCompilerError(
                    f"Fortress card has unsupported unit {effect.unit!r}."
                )
            accumulator.multiply("defense_absolute", effect.value, "cards:fortress")
        else:
            try:
                card_canonical = resolve_named_entity("cards", effect.card)
            except KeyError as exc:
                raise StatInputCompilerError(
                    f"Unsupported card for survivability pipeline: {card_name!r}."
                ) from exc
            if card_canonical == "CARD_PLASMA_CANNON":
                if effect.unit != "percent":
                    raise StatInputCompilerError(
                        f"Plasma Cannon card has unsupported unit {effect.unit!r}."
                    )
                accumulator.add(
                    "plasma_cannon_damage_mult", effect.value, "cards:plasma_cannon"
                )
            elif card_canonical in _CARD_NOOP_CANONICALS:
                # These cards do not currently map to canonical survivability stat inputs.
                # Their mechanics are handled in other pipeline surfaces (spawn/wave pacing,
                # shield event handling, etc.) and are therefore a deterministic no-op here.
                continue
            else:
                raise StatInputCompilerError(
                    f"Unsupported card for survivability pipeline: {card_name!r}."
                )


def _resolve_equipped_cards(
    ids_snapshot: AccountSnapshot, module_context: str
) -> List[str]:
    if module_context not in ids_snapshot.card_presets:
        raise StatInputCompilerError(
            f"Missing card preset {module_context!r} in IDS snapshot."
        )
    return list(ids_snapshot.card_presets[module_context])


def _resolve_card_effect(
    card_name: str, ids_snapshot: AccountSnapshot
) -> CardEffect:
    from tower_sim.registry.naming_contract import resolve_named_entity
    entry = ids_snapshot.cards_inventory.get(card_name)
    if entry is None or entry.level is None:
        raise StatInputCompilerError(
            f"Missing card {card_name!r} or card level in IDS."
        )
    try:
        return get_card_effect(card_name, entry.level)
    except KeyError as exc:
        try:
            canonical = resolve_named_entity("cards", card_name)
        except KeyError:
            raise exc
        if canonical in _CARD_NOOP_CANONICALS:
            return CardEffect(
                card=card_name,
                rarity="Unknown",
                level=int(entry.level),
                value=0.0,
                value_raw="0",
                unit="flat",
            )
        raise exc


class _StatAccumulator:
    def __init__(self) -> None:
        self._stats: Dict[str, Dict[str, float]] = {}
        self._module_ledger: List[Dict[str, object]] = []

    def add(self, stat_id: str, delta: float, provenance: str) -> None:
        entry = self._stats.setdefault(stat_id, {"delta": 0.0, "mult": 1.0})
        entry["delta"] += float(delta)
        entry["provenance"] = provenance

    def multiply(self, stat_id: str, multiplier: float, provenance: str) -> None:
        entry = self._stats.setdefault(stat_id, {"delta": 0.0, "mult": 1.0})
        entry["mult"] *= float(multiplier)
        entry["provenance"] = provenance


    def record_module_contribution(
        self,
        *,
        slot: str,
        placement: str,
        module_name: str,
        layer: str,
        target: str,
        value: float,
        kind: str,
    ) -> None:
        self._module_ledger.append({
            "slot": slot,
            "placement": placement,
            "module": module_name,
            "layer": layer,
            "target": target,
            "kind": kind,
            "value": float(value),
        })

    def module_contribution_ledger(self) -> List[Dict[str, object]]:
        return list(self._module_ledger)

    def to_stat_inputs(self) -> List[StatInput]:
        inputs: List[StatInput] = []
        for stat_id, entry in self._stats.items():
            delta = entry["delta"]
            mult = entry["mult"]
            inputs.append(
                StatInput(
                    stat_id=stat_id,
                    phase=Phase.START_OF_RUN,
                    loadout_delta=delta if delta != 0.0 else None,
                    enhancement_multiplier=mult if mult != 1.0 else None,
                    provenance=entry.get("provenance"),
                )
            )
        return inputs


def _parse_optional_int(value: str) -> Optional[int]:
    candidate = value.strip()
    if candidate == "":
        return None
    return int(float(candidate))


def _parse_rarity(value: str) -> Optional[Rarity]:
    candidate = value.strip()
    if candidate == "":
        return None
    core = candidate.split()[0].replace("+", "")
    for rarity in Rarity:
        if rarity.value.lower() == core.lower():
            return rarity
    raise StatInputCompilerError(f"Unknown rarity {value!r} in IDS module data.")


def _cap_rarity(current: Rarity, cap: Rarity) -> Rarity:
    order = [Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHIC, Rarity.ANCESTRAL]
    if current not in order or cap not in order:
        return current
    return current if order.index(current) <= order.index(cap) else cap


def _normalize_substat_name(name: str) -> str:
    mapping = {
        "Critical Factor": "Crit Factor",
        "MultiShot Chance": "Multishot Chance",
        "MultiShot Targets": "Multishot Targets",
        "Defense %": "Defense",
        "Thorn Damage": "Thorns Damage",
        "Package Chance": "Recovery Package Chance",
    }
    return mapping.get(name, name)




def _uw_canonical_aliases() -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for track_specs in _UW_TRACK_SPECS.values():
        for spec in track_specs.values():
            source = spec.stat_id
            target = source[len("uw_") :] if source.startswith("uw_") else source
            aliases[source] = target
            aliases[f"{source}_next_cost"] = f"{target}_next_cost"
    return aliases


_UW_CANONICAL_ALIASES: Dict[str, str] = _uw_canonical_aliases()




def compile_baseline_loadout_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    module_context: str = "Testing",
    module_overrides: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
    selected_cards: Optional[Iterable[str]] = None,
    include_cards: bool = True,
    include_modules: bool = True,
    allow_provisional: bool = True,
) -> CompiledBaselineLoadout:
    """Compile canonical baseline_loadout stat inputs."""
    accumulator = _StatAccumulator()
    layer_gaps: List[str] = []

    if include_cards:
        _apply_card_effects(
            accumulator,
            ids_snapshot,
            module_context=module_context,
            selected_cards=selected_cards,
        )

    if include_modules:
        module_blocks = _parse_module_blocks(ids_snapshot)
        for block in module_blocks.values():
            if module_context not in block.loadout_by_context:
                continue
            loadout = block.loadout_by_context[module_context]
            overrides = (module_overrides or {}).get(loadout.slot, {})
            primary_name = overrides.get("primary", loadout.primary)
            assist_name = overrides.get("assist", loadout.assist)
            assist_enabled = loadout.assist_enabled
            assist_level = loadout.assist_stone_level
            assist_cap = loadout.assist_cap_rarity
            allocation = ids_snapshot.allocation_levels.get(loadout.slot)
            if allocation is not None:
                assist_level = allocation.assist_level

            primary = _resolve_module(primary_name, loadout.slot, block.inventory) if primary_name else None
            assist = _resolve_module(assist_name, loadout.slot, block.inventory) if assist_name else None

            layer_gaps.extend(
                _apply_module_effects(
                    accumulator,
                    primary=primary,
                    assist=assist,
                    assist_enabled=assist_enabled,
                    assist_level=assist_level,
                    assist_cap=assist_cap,
                    ids_snapshot=ids_snapshot,
                    allow_provisional=allow_provisional,
                    slot=loadout.slot,
                )
            )

    return CompiledBaselineLoadout(
        stat_inputs=accumulator.to_stat_inputs(),
        missing=[],
        module_contribution_ledger=accumulator.module_contribution_ledger(),
        layer_gaps=layer_gaps,
    )


def compile_baseline_account_stat_inputs(
    ids_snapshot: AccountSnapshot,
) -> CompiledStatInputs:
    """Compile canonical baseline_account stat inputs (workshop + UW + relics)."""
    return compile_full_stat_inputs(
        ids_snapshot,
        include_workshop=True,
        include_uw=True,
        include_bots=False,
    )


def compile_baseline_gem_respec_stat_inputs(
    ids_snapshot: AccountSnapshot,
) -> CompiledStatInputs:
    """Compile canonical baseline_gem_respec stat inputs (baseline_account + bots)."""
    baseline = compile_baseline_account_stat_inputs(ids_snapshot)
    bot_inputs, bot_missing = _compile_bot_stat_inputs(ids_snapshot)
    return CompiledStatInputs(
        stat_inputs=list(baseline.stat_inputs) + bot_inputs,
        missing=sorted(set(baseline.missing + bot_missing)),
    )


def compile_full_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    include_workshop: bool = True,
    include_uw: bool = True,
    include_bots: bool = True,
) -> CompiledStatInputs:
    stat_inputs: List[StatInput] = []
    missing: List[str] = []

    if include_workshop:
        workshop_inputs, workshop_missing = _compile_workshop_stat_inputs(ids_snapshot)
        stat_inputs.extend(workshop_inputs)
        missing.extend(workshop_missing)

    if include_uw:
        uw_inputs, uw_missing = _compile_uw_stat_inputs(ids_snapshot)
        stat_inputs.extend(uw_inputs)
        missing.extend(uw_missing)

    relic_inputs = _compile_relic_stat_inputs(ids_snapshot)
    stat_inputs.extend(relic_inputs)

    if include_bots:
        bot_inputs, bot_missing = _compile_bot_stat_inputs(ids_snapshot)
        stat_inputs.extend(bot_inputs)
        missing.extend(bot_missing)

    return CompiledStatInputs(
        stat_inputs=_with_required_start_of_run_defaults(stat_inputs),
        missing=sorted(set(missing)),
    )



def _required_start_of_run_defaults() -> List[StatInput]:
    return [
        StatInput(
            stat_id="orb_damage_mult",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="base:identity",
        ),
        StatInput(
            stat_id="death_ray_damage_mult",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="base:identity",
        ),
        StatInput(
            stat_id="plasma_cannon_damage_mult",
            phase=Phase.START_OF_RUN,
            base_value=0.0,
            provenance="base:cards:plasma_cannon",
        ),
        StatInput(
            stat_id="knockback_mult",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="base:identity",
        ),
    ]


def _with_required_start_of_run_defaults(stat_inputs: List[StatInput]) -> List[StatInput]:
    existing = {(item.stat_id, item.phase): item for item in stat_inputs}
    merged = list(stat_inputs)
    for default in _required_start_of_run_defaults():
        key = (default.stat_id, default.phase)
        item = existing.get(key)
        if item is None:
            merged.append(default)
            continue
        if item.base_value is None and item.derived_value is None:
            merged_item = StatInput(
                stat_id=item.stat_id,
                phase=item.phase,
                base_value=default.base_value,
                loadout_delta=item.loadout_delta,
                enhancement_multiplier=item.enhancement_multiplier,
                tier_rule_delta=item.tier_rule_delta,
                tier_rule_multiplier=item.tier_rule_multiplier,
                derived_value=item.derived_value,
                provenance=item.provenance or default.provenance,
            )
            for idx, current in enumerate(merged):
                if current.stat_id == item.stat_id and current.phase == item.phase:
                    merged[idx] = merged_item
                    break
    return merged



def _compile_relic_stat_inputs(ids_snapshot: AccountSnapshot) -> List[StatInput]:
    def _sum(keys: Tuple[str, ...]) -> float:
        total = 0.0
        for key in keys:
            raw = ids_snapshot.relics.get(key)
            if raw is None:
                continue
            value = float(raw)
            if value < 0.0:
                raise ValueError(f"Relic bonus must be non-negative for {key!r}, got {value}.")
            total += value
        return total

    specs = (
        (("Health",), "tower_hp", "mult", "relics:health"),
        (("Health Regen",), "tower_regen", "mult", "relics:health_regen"),
        (("Wall Health",), "wall_hp", "mult", "relics:wall_health"),
        (("Wall Regen",), "wall_regen", "mult", "relics:wall_regen"),
        (("Defense", "Defense %"), "def_pct", "delta", "relics:defense_percent"),
        (("Defense Absolute",), "defense_absolute", "mult", "relics:defense_absolute"),
        (("Enemy Attack Level Skip",), "eals_pct", "delta", "relics:eals"),
        (("Enemy Health Level Skip",), "ehls_pct", "delta", "relics:ehls"),
        (("Damage",), "tower_damage", "mult", "relics:damage"),
        (("Attack Speed",), "tower_attack_speed", "mult", "relics:attack_speed"),
        (("Crit Chance",), "tower_crit_chance", "delta", "relics:crit_chance"),
        (("Crit Factor",), "tower_crit_multiplier", "mult", "relics:crit_factor"),
        (("Damage / Meter",), "damage_per_meter", "mult", "relics:damage_per_meter"),
        (("Free Attack Upgrade",), "free_attack_upgrade", "delta", "relics:free_attack_upgrade"),
        (("Free Defense Upgrade",), "free_defense_upgrade", "delta", "relics:free_defense_upgrade"),
        (("Free Utility Upgrade",), "free_utility_upgrade", "delta", "relics:free_utility_upgrade"),
        (("Recovery Amount",), "recovery_amount", "mult", "relics:recovery_amount"),
        (("Super Critical Chance",), "super_crit_chance", "delta", "relics:super_crit_chance"),
        (("Super Critical Mult",), "super_crit_mult", "mult", "relics:super_crit_mult"),
        (("Thorns",), "thorns_damage_mult", "mult", "relics:thorns"),
        (("Orb Speed",), "orb_speed", "mult", "relics:orb_speed"),
        (("Wall Rebuild",), "wall_rebuild", "delta_negative", "relics:wall_rebuild"),
        (("Cash",), "cash_bonus", "mult", "relics:cash"),
        (("Coins",), "coins_bonus", "mult", "relics:coins"),
        (("Ultimate Damage",), "ultimate_damage", "mult", "relics:ultimate_damage"),
        (("Lab Speed",), "lab_speed", "mult", "relics:lab_speed"),
        (("Bot Range",), "bot_range", "mult", "relics:bot_range"),
    )

    inputs: List[StatInput] = []
    for keys, stat_id, mode, provenance in specs:
        total = _sum(keys)
        if total <= 0.0:
            continue
        if mode == "mult":
            inputs.append(
                StatInput(
                    stat_id=stat_id,
                    phase=Phase.START_OF_RUN,
                    enhancement_multiplier=1.0 + total,
                    provenance=provenance,
                )
            )
        elif mode == "delta_negative":
            inputs.append(
                StatInput(
                    stat_id=stat_id,
                    phase=Phase.START_OF_RUN,
                    loadout_delta=-total,
                    provenance=provenance,
                )
            )
        else:
            inputs.append(
                StatInput(
                    stat_id=stat_id,
                    phase=Phase.START_OF_RUN,
                    loadout_delta=total,
                    provenance=provenance,
                )
            )
    return inputs


_BOT_TRACK_SPECS: Dict[tuple[str, str], str] = {
    ("Flame Bot", "Damage"): "bot_flame_damage",
    ("Flame Bot", "Cooldown"): "bot_flame_cooldown",
    ("Flame Bot", "Damage R."): "bot_flame_damage_reduction",
    ("Flame Bot", "Range"): "bot_flame_range",
    ("Thunder Bot", "Cooldown"): "bot_thunder_cooldown",
    ("Thunder Bot", "Duration"): "bot_thunder_duration",
    ("Thunder Bot", "Linger"): "bot_thunder_linger",
    ("Thunder Bot", "Range"): "bot_thunder_range",
    ("Golden Bot", "Duration"): "bot_golden_duration",
    ("Golden Bot", "Cooldown"): "bot_golden_cooldown",
    ("Golden Bot", "Bonus"): "bot_golden_bonus",
    ("Golden Bot", "Range"): "bot_golden_range",
    ("Amplify Bot", "Duration"): "bot_amplify_duration",
    ("Amplify Bot", "Cooldown"): "bot_amplify_cooldown",
    ("Amplify Bot", "Bonus"): "bot_amplify_bonus",
    ("Amplify Bot", "Range"): "bot_amplify_range",
}


def _compile_bot_stat_inputs(ids_snapshot: AccountSnapshot) -> Tuple[List[StatInput], List[str]]:
    stat_inputs: List[StatInput] = []
    missing: List[str] = []

    for (bot_name, track_name), stat_id in _BOT_TRACK_SPECS.items():
        bot_tracks = ids_snapshot.bot_upgrades.get(bot_name)
        if bot_tracks is None:
            continue
        level = bot_tracks.get(track_name)
        if level is None:
            missing.append(f"bot_level_missing:{bot_name}:{track_name}")
            continue
        try:
            value, _, _ = get_bot_attribute(bot_name, track_name, int(level))
        except (KeyError, ValueError):
            missing.append(f"bot_level_invalid:{bot_name}:{track_name}:{level}")
            continue

        stat_inputs.append(
            StatInput(
                stat_id=stat_id,
                phase=Phase.START_OF_RUN,
                base_value=float(value),
                provenance=f"bot_table:{bot_name}:{track_name}",
            )
        )

    return stat_inputs, missing

def _compile_workshop_stat_inputs(
    ids_snapshot: AccountSnapshot,
) -> Tuple[List[StatInput], List[str]]:
    workshop_tables = load_workshop_tables()
    labs = load_labs_values()
    enhancement_map, enhancement_missing = _parse_workshop_enhancement_multipliers(ids_snapshot)
    stat_inputs: List[StatInput] = []
    missing: List[str] = list(enhancement_missing)
    missing.extend(_collect_unmapped_active_lab_levels(ids_snapshot, labs))

    for name, entry in ids_snapshot.workshop.items():
        if entry.coin_level is None:
            missing.append(f"workshop_level:{name}")
            continue
        if entry.max_level is None:
            missing.append(f"workshop_max_level:{name}")
            continue
        if entry.coin_level < 0:
            missing.append(f"workshop_level_bounds:{name}")
            continue
        if entry.coin_level > entry.max_level:
            missing.append(f"workshop_level_bounds:{name}")
            continue
        spec = _WORKSHOP_STAT_SPECS.get(name)
        if spec is None:
            missing.append(f"workshop_mapping:{name}")
            continue
        if not _has_authoritative_workshop_definition(name, spec, workshop_tables):
            missing.append(f"workshop_definition:{name}")
            continue
        formula = _WORKSHOP_FORMULAS.get(name)
        if name in _WORKSHOP_LAB_DELTA_STATS:
            lab_delta = _resolve_lab_delta(name, ids_snapshot, labs, missing)
            enhancement_multiplier = enhancement_map.get(spec.stat_id)
        else:
            lab_multiplier = _resolve_lab_multiplier(name, ids_snapshot, labs, missing)
            enhancement_multiplier = _combine_multipliers(
                enhancement_map.get(spec.stat_id),
                lab_multiplier,
            )
        if formula is not None:
            value = formula(entry.coin_level)
            if value is None:
                missing.append(f"workshop_unsupported:{name}")
                continue
            workshop_value_f = float(value)
            stat_inputs.append(
                StatInput(
                    stat_id=spec.stat_id,
                    phase=Phase.START_OF_RUN,
                    base_value=workshop_value_f,
                    enhancement_multiplier=enhancement_multiplier,
                    provenance="workshop_formula:DVT_WS_VALUE",
                )
            )
            canonical_stat_id = _WORKSHOP_CANONICAL_ALIASES.get(name)
            if canonical_stat_id is not None:
                canonical_value_f = workshop_value_f
                if name in _WORKSHOP_LAB_DELTA_STATS:
                    canonical_value_f = canonical_value_f + lab_delta
                    if name in {"Enemy Attack Level Skip", "Enemy Health Level Skip"}:
                        canonical_value_f = min(max(canonical_value_f, 0.0), 1.0)
                stat_inputs.append(
                    StatInput(
                        stat_id=canonical_stat_id,
                        phase=Phase.START_OF_RUN,
                        base_value=canonical_value_f,
                        enhancement_multiplier=enhancement_multiplier,
                        provenance=f"workshop_alias:{name}->{canonical_stat_id}",
                    )
                )
            continue
        try:
            value = _resolve_workshop_value(
                workshop_tables,
                spec,
                level=entry.coin_level,
            )
        except KeyError:
            missing.append(f"workshop_table:{name}")
            continue
        stat_inputs.append(
            StatInput(
                stat_id=spec.stat_id,
                phase=Phase.START_OF_RUN,
                base_value=value,
                enhancement_multiplier=enhancement_multiplier,
                provenance=_workshop_provenance(name),
            )
        )
        canonical_stat_id = _WORKSHOP_CANONICAL_ALIASES.get(name)
        if canonical_stat_id is not None:
            stat_inputs.append(
                StatInput(
                    stat_id=canonical_stat_id,
                    phase=Phase.START_OF_RUN,
                    base_value=value,
                    enhancement_multiplier=enhancement_multiplier,
                    provenance=f"workshop_alias:{name}->{canonical_stat_id}",
                )
            )

    wall_inputs, wall_missing = _compile_wall_survivability_aliases(
        ids_snapshot=ids_snapshot,
        labs=labs,
        stat_inputs=stat_inputs,
    )
    stat_inputs.extend(wall_inputs)
    missing.extend(wall_missing)
    return stat_inputs, missing


def _compile_wall_survivability_aliases(
    *,
    ids_snapshot: AccountSnapshot,
    labs,
    stat_inputs: List[StatInput],
) -> Tuple[List[StatInput], List[str]]:
    missing: List[str] = []
    by_id = {
        item.stat_id: item
        for item in stat_inputs
        if item.phase == Phase.START_OF_RUN and item.base_value is not None
    }
    tower_hp = by_id.get("tower_hp")
    tower_regen = by_id.get("tower_regen")
    wall_health_ratio_input = by_id.get("workshop_wall_health")
    if tower_hp is None:
        missing.append("workshop_alias_missing:tower_hp")
        return [], missing
    if tower_regen is None:
        missing.append("workshop_alias_missing:tower_regen")
        return [], missing
    if wall_health_ratio_input is None:
        missing.append("workshop_alias_missing:workshop_wall_health")
        return [], missing

    wall_health_ratio = _resolved_stat_input_value(wall_health_ratio_input)
    wall_health_lab = ids_snapshot.labs.get("Wall Health")
    if wall_health_lab is None:
        missing.append("lab_level:Wall Health")
        wall_health_lab = 0
    if wall_health_lab > 0:
        lab = labs.get("Wall Health")
        if lab is None:
            missing.append("lab_table:Wall Health")
            return [], missing
        if wall_health_lab not in lab.levels:
            missing.append(f"lab_table:Wall Health:{wall_health_lab}")
            return [], missing
        if lab.unit not in {"percent", "percent_points"}:
            missing.append(f"lab_unit:Wall Health:{lab.unit}")
            return [], missing
        wall_health_ratio += float(lab.levels[wall_health_lab]) / 100.0

    wall_regen_ratio_input = by_id.get("workshop_wall_regen")
    wall_regen_entry = ids_snapshot.workshop.get("Wall Regen")
    wall_regen_blocked = (
        wall_regen_entry is not None
        and wall_regen_entry.coin_level is not None
        and wall_regen_ratio_input is None
    )
    if wall_regen_blocked:
        missing.append("workshop_alias_missing:workshop_wall_regen")
    wall_regen_ratio = (
        _resolved_stat_input_value(wall_regen_ratio_input)
        if wall_regen_ratio_input is not None
        else 0.0
    )
    wall_regen_lab = ids_snapshot.labs.get("Wall Regen")
    if wall_regen_lab is None:
        missing.append("lab_level:Wall Regen")
        wall_regen_lab = 0
    if wall_regen_lab > 0:
        lab = labs.get("Wall Regen")
        if lab is None:
            missing.append("lab_table:Wall Regen")
            return [], missing
        if wall_regen_lab not in lab.levels:
            missing.append(f"lab_table:Wall Regen:{wall_regen_lab}")
            return [], missing
        if lab.unit not in {"percent", "percent_points"}:
            missing.append(f"lab_unit:Wall Regen:{lab.unit}")
            return [], missing
        wall_regen_ratio += float(lab.levels[wall_regen_lab]) / 100.0

    wall_hp = _resolved_stat_input_value(tower_hp) * wall_health_ratio
    outputs = [
        StatInput(
            stat_id="wall_hp",
            phase=Phase.START_OF_RUN,
            base_value=wall_hp,
            provenance="workshop_alias:Wall Health->wall_hp",
        )
    ]
    wall_regen = _resolved_stat_input_value(tower_regen) * wall_regen_ratio
    outputs.append(
        StatInput(
            stat_id="wall_regen",
            phase=Phase.START_OF_RUN,
            base_value=wall_regen,
            provenance="workshop_alias:Wall Regen->wall_regen",
        )
    )
    wall_thorns_entry = ids_snapshot.workshop.get("Wall Thorns")
    if wall_thorns_entry is not None and wall_thorns_entry.coin_level is not None:
        if wall_thorns_entry.coin_level < 0:
            missing.append("workshop_level_bounds:Wall Thorns")
        else:
            outputs.append(
                StatInput(
                    stat_id="wall_thorns_mult",
                    phase=Phase.START_OF_RUN,
                    base_value=float(wall_thorns_entry.coin_level) / 100.0,
                    provenance="workshop_alias:Wall Thorns->wall_thorns_mult",
                )
            )
    return outputs, missing


def _resolved_stat_input_value(stat_input: StatInput) -> float:
    base = float(stat_input.base_value or 0.0)
    loadout_delta = float(stat_input.loadout_delta or 0.0)
    enhancement_multiplier = float(stat_input.enhancement_multiplier or 1.0)
    tier_rule_delta = float(stat_input.tier_rule_delta or 0.0)
    tier_rule_multiplier = float(stat_input.tier_rule_multiplier or 1.0)
    return ((base + loadout_delta) * enhancement_multiplier + tier_rule_delta) * tier_rule_multiplier


def _combine_multipliers(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None and right is None:
        return None
    return float(left or 1.0) * float(right or 1.0)


_WORKSHOP_TO_LAB_NAME = {
    "Package Chance": "Recovery Package Chance",
}


_WORKSHOP_TO_LAB_CANONICAL_ID = {
    "Health": "LAB_HEALTH",
    "Health Regen": "LAB_HEALTH_REGEN",
    "Attack Speed": "LAB_ATTACK_SPEED",
    "Defense %": "LAB_DEFENSE_PERCENT",
    "Wall Health": "LAB_WALL_HEALTH",
    "Wall Regen": "LAB_WALL_REGEN",
    "Recovery Package Chance": "LAB_RECOVERY_PACKAGE_CHANCE",
    "Package Chance": "LAB_RECOVERY_PACKAGE_CHANCE",
    "Enemy Attack Level Skip": "LAB_ENEMY_ATTACK_LEVEL_SKIP",
    "Enemy Health Level Skip": "LAB_ENEMY_HEALTH_LEVEL_SKIP",
}


_LAB_NAME_ALIASES = {
    "Black Hole Coin Bonus": "Black Hole Coins Bonus",
    "Cash / Wave": "Cash Per Wave",
    "Coins / Kill Bonus": "Coins Per Kill Bonus",
    "Coins / Wave": "Coins Per Wave",
    "Damage / Meter": "Damage Per Meter",
    "Death Wave Cells Bonus": "Death Wave Cell Bonus",
    "Flame Bot - Cooldown": "Flame Bot Cooldown",
    "Improve Trade-off Perks": "Improve Trade-Off Perks",
    "Module Shards Cost": "Module Shard Costs",
    "Orbs Speed": "Orb Speed",
    "Reroll Daily Mission": "Reroll Daily Missions",
    "Wall Thorns": "Wall Thorn",
    "Workshop Enhancements": "Workshop Enhancement",
}


@lru_cache(maxsize=1)
def _load_labs_catalog_primary_names() -> Dict[str, str]:
    registry_dir = resolve_table_path("registry_dir", runtime_mode=False)
    catalog_path = registry_dir / "catalog.yaml"
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    categories = payload.get("categories") if isinstance(payload, dict) else None
    labs_entries = categories.get("labs") if isinstance(categories, dict) else None
    if not isinstance(labs_entries, list):
        raise ValueError("Lab catalog missing categories.labs list")

    mapping: Dict[str, str] = {}
    for entry in labs_entries:
        if not isinstance(entry, dict):
            continue
        primary_name = str(entry.get("primary_name", "")).strip()
        canonical_id = str(entry.get("canonical_id", "")).strip()
        if not primary_name or not canonical_id:
            continue
        mapping[primary_name] = canonical_id
    if not mapping:
        raise ValueError("Lab catalog has no primary_name/canonical_id mappings")
    return mapping


def _validate_lab_canonical_mapping(workshop_name: str, lab_name: str, lab, missing: List[str]) -> bool:
    expected_lab_id = _WORKSHOP_TO_LAB_CANONICAL_ID.get(workshop_name)
    if expected_lab_id is None:
        return True
    actual_lab_id = str(getattr(lab, "canonical_id", "")).strip()
    if actual_lab_id == expected_lab_id:
        return True
    missing.append(
        f"lab_mapping:{workshop_name}:{lab_name}:{actual_lab_id or 'missing'}:{expected_lab_id}"
    )
    return False


def _collect_unmapped_active_lab_levels(ids_snapshot: AccountSnapshot, labs) -> List[str]:
    missing: List[str] = []
    catalog = _load_labs_catalog_primary_names()
    for lab_name, level in ids_snapshot.labs.items():
        if level is None or level <= 0:
            continue
        normalized_name = _LAB_NAME_ALIASES.get(lab_name, lab_name)
        canonical_id = catalog.get(normalized_name)
        if canonical_id is None:
            missing.append(f"lab_catalog_missing:{lab_name}")
            continue
        if normalized_name in labs:
            continue
        missing.append(f"lab_table_unmapped:{lab_name}:{canonical_id}")
    return missing


def _resolve_lab_multiplier(
    workshop_name: str,
    ids_snapshot: AccountSnapshot,
    labs,
    missing: List[str],
) -> Optional[float]:
    lab_name = _WORKSHOP_TO_LAB_NAME.get(workshop_name, workshop_name)
    if lab_name not in labs:
        return None
    level = ids_snapshot.labs.get(lab_name)
    if level is None:
        missing.append(f"lab_level:{lab_name}")
        return None
    if level <= 0:
        return None
    lab = labs[lab_name]
    if not _validate_lab_canonical_mapping(workshop_name, lab_name, lab, missing):
        return None
    if level not in lab.levels:
        missing.append(f"lab_table:{lab_name}:{level}")
        return None
    value = float(lab.levels[level])
    if lab.unit == "raw_number":
        return value
    if lab.unit in {"percent", "percent_points"}:
        return 1.0 + (value / 100.0)
    missing.append(f"lab_unit:{lab_name}:{lab.unit}")
    return None




def _resolve_lab_delta(
    workshop_name: str,
    ids_snapshot: AccountSnapshot,
    labs,
    missing: List[str],
) -> float:
    lab_name = _WORKSHOP_TO_LAB_NAME.get(workshop_name, workshop_name)
    if lab_name not in labs:
        return 0.0
    level = ids_snapshot.labs.get(lab_name)
    if level is None:
        missing.append(f"lab_level:{lab_name}")
        return 0.0
    if level <= 0:
        return 0.0
    lab = labs[lab_name]
    if not _validate_lab_canonical_mapping(workshop_name, lab_name, lab, missing):
        return 0.0
    if level not in lab.levels:
        missing.append(f"lab_table:{lab_name}:{level}")
        return 0.0
    value = float(lab.levels[level])
    if lab.unit in {"percent", "percent_points"}:
        return value / 100.0
    if lab.unit == "raw_number":
        return value
    missing.append(f"lab_unit:{lab_name}:{lab.unit}")
    return 0.0


def _parse_workshop_enhancement_multipliers(
    ids_snapshot: AccountSnapshot,
) -> Tuple[Dict[str, float], List[str]]:
    rows = ids_snapshot.workshop_enhancements.rows
    if not rows:
        return {}, []
    multipliers: Dict[str, float] = {}
    missing: List[str] = []
    for row in rows:
        raw_name = row[0].strip() if row and row[0].strip() else ""
        if not raw_name.endswith("+"):
            continue
        base_name = raw_name[:-1].strip()
        target_stat_ids: List[str]
        if base_name == "Enemy Level Skips":
            target_stat_ids = [
                "workshop_enemy_attack_level_skip",
                "workshop_enemy_health_level_skip",
            ]
        else:
            spec = _WORKSHOP_STAT_SPECS.get(base_name)
            if spec is None:
                continue
            target_stat_ids = [spec.stat_id]
        raw_multiplier = row[1].strip() if len(row) > 1 else ""
        if not raw_multiplier:
            missing.append(f"workshop_enhancement_value:{base_name}")
            continue
        try:
            multiplier = float(raw_multiplier)
        except ValueError:
            missing.append(f"workshop_enhancement_value:{base_name}")
            continue
        if multiplier <= 0:
            missing.append(f"workshop_enhancement_value:{base_name}")
            continue
        for stat_id in target_stat_ids:
            multipliers[stat_id] = multiplier
    return multipliers, missing


def _resolve_workshop_value(
    workshop_tables: WorkshopTables,
    spec: WorkshopStatSpec,
    *,
    level: int,
) -> float:
    if spec.wsvalues_key and spec.wsvalues_key in workshop_tables.wsvalues:
        return float(workshop_value(spec.wsvalues_key, level, workshop_tables, section="WSValues"))
    for key in spec.dvt_keys:
        if key in workshop_tables.dvt_sections.get("Workshop", {}):
            return float(workshop_value(key, level, workshop_tables, section="Workshop"))
        if key in workshop_tables.dvt_sections.get("Workshop +", {}):
            return float(workshop_value(key, level, workshop_tables, section="Workshop +"))
    raise KeyError("Missing workshop table entry.")


def _has_authoritative_workshop_definition(
    stat_name: str,
    spec: WorkshopStatSpec,
    workshop_tables: WorkshopTables,
) -> bool:
    if spec.wsvalues_key and spec.wsvalues_key in workshop_tables.wsvalues:
        return True
    for key in spec.dvt_keys:
        if key in workshop_tables.dvt_sections.get("Workshop", {}):
            return True
        if key in workshop_tables.dvt_sections.get("Workshop +", {}):
            return True
    return stat_name in _WORKSHOP_FORMULAS


def _workshop_provenance(name: str) -> str:
    return f"workshop_table:{name}"




def _resolve_uw_lab_additive(
    *,
    stat_id: str,
    ids_snapshot: AccountSnapshot,
    labs,
    missing: List[str],
) -> float:
    lab_name = _UW_LAB_ADDITIVE_STATS.get(stat_id)
    if lab_name is None:
        return 0.0
    lab = labs.get(lab_name)
    if lab is None:
        missing.append(f"lab_table:{lab_name}")
        return 0.0
    expected = _UW_LAB_CANONICAL_ID.get(stat_id)
    actual = str(getattr(lab, "canonical_id", "")).strip()
    if expected is not None and actual != expected:
        missing.append(f"lab_mapping:{stat_id}:{lab_name}:{actual or 'missing'}:{expected}")
        return 0.0
    level = ids_snapshot.labs.get(lab_name)
    if level is None:
        missing.append(f"lab_level:{lab_name}")
        return 0.0
    if level <= 0:
        return 0.0
    if level not in lab.levels:
        missing.append(f"lab_table:{lab_name}:{level}")
        return 0.0
    if lab.unit != "raw_number":
        missing.append(f"lab_unit:{lab_name}:{lab.unit}")
        return 0.0
    return float(lab.levels[level])

def _compile_uw_stat_inputs(ids_snapshot: AccountSnapshot) -> Tuple[List[StatInput], List[str]]:
    stat_inputs: List[StatInput] = []
    missing: List[str] = []
    ladder_values, ladder_missing = _load_uw_track_values()
    missing.extend(ladder_missing)

    uw_tracks, uw_missing = _parse_uw_tracks(ids_snapshot.raw_sections.get("UWs", []))
    labs = load_labs_values()
    missing.extend(uw_missing)

    for uw_name, track_name, level_index, raw_value, next_cost in uw_tracks:
        mapping = _UW_TRACK_SPECS.get(uw_name)
        if mapping is None or track_name not in mapping:
            missing.append(f"uw_mapping:{uw_name}:{track_name}")
            continue
        spec = mapping[track_name]
        ladder_key = (uw_name, track_name, level_index)
        ladder_value = ladder_values.get(ladder_key)
        if raw_value is None:
            if level_index == 0:
                value = 0.0
            elif ladder_value is None:
                missing.append(f"uw_locked:{uw_name}:{track_name}")
                continue
            else:
                value = ladder_value
        else:
            value = raw_value

        value += _resolve_uw_lab_additive(
            stat_id=spec.stat_id,
            ids_snapshot=ids_snapshot,
            labs=labs,
            missing=missing,
        )

        source_stat_id = spec.stat_id
        canonical_stat_id = _UW_CANONICAL_ALIASES.get(source_stat_id)

        stat_inputs.append(
            StatInput(
                stat_id=source_stat_id,
                phase=Phase.START_OF_RUN,
                base_value=value,
                provenance=_uw_provenance(spec),
            )
        )
        if canonical_stat_id is not None:
            stat_inputs.append(
                StatInput(
                    stat_id=canonical_stat_id,
                    phase=Phase.START_OF_RUN,
                    base_value=value,
                    provenance=f"uw_alias:{source_stat_id}->{canonical_stat_id}",
                )
            )
        if next_cost is not None:
            source_cost_stat_id = f"{source_stat_id}_next_cost"
            stat_inputs.append(
                StatInput(
                    stat_id=source_cost_stat_id,
                    phase=Phase.START_OF_RUN,
                    base_value=next_cost,
                    provenance=_uw_provenance(spec),
                )
            )
            canonical_cost_stat_id = _UW_CANONICAL_ALIASES.get(source_cost_stat_id)
            if canonical_cost_stat_id is not None:
                stat_inputs.append(
                    StatInput(
                        stat_id=canonical_cost_stat_id,
                        phase=Phase.START_OF_RUN,
                        base_value=next_cost,
                        provenance=f"uw_alias:{source_cost_stat_id}->{canonical_cost_stat_id}",
                    )
                )
    return stat_inputs, missing


def _parse_uw_tracks(
    rows: Iterable[List[str]],
) -> Tuple[List[Tuple[str, str, int, Optional[float], Optional[float]]], List[str]]:
    tracks: List[Tuple[str, str, int, Optional[float], Optional[float]]] = []
    missing: List[str] = []
    current: Optional[str] = None
    for row in rows:
        name = row[0].strip() if row else ""
        if name in _UW_TRACK_SPECS:
            current = name
        elif name and name not in {"UW+", "true", "false"}:
            current = None
        if current is None:
            continue
        if len(row) < 5:
            continue
        track_name = row[2].strip()
        if not track_name:
            continue
        level_index = _parse_level_index(row[4])
        if level_index is None:
            missing.append(f"uw_level_missing:{current}:{track_name}")
            continue
        tracks.append(
            (current, track_name, level_index, _parse_uw_value(row[3]), _parse_next_cost(row[4]))
        )
    return tracks, missing


def _load_uw_track_values() -> Tuple[Dict[Tuple[str, str, int], float], List[str]]:
    values: Dict[Tuple[str, str, int], float] = {}
    missing: List[str] = []
    for table_name, track_column in (
        ("uw_track_ladders", "track_name"),
        ("uw_plus_ladders", "plus_track_name"),
    ):
        path = resolve_table_path(table_name)
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                uw_name = row.get("uw_name", "").strip()
                track_name = row.get(track_column, "").strip()
                level_raw = row.get("level_index", "").strip()
                value_raw = row.get("value", "").strip()
                if not uw_name or not track_name or not level_raw:
                    continue
                try:
                    level = int(level_raw)
                except ValueError:
                    missing.append(f"uw_table_level:{uw_name}:{track_name}:{level_raw}")
                    continue
                if not value_raw:
                    continue
                try:
                    value = float(value_raw)
                except ValueError:
                    missing.append(f"uw_table_value:{uw_name}:{track_name}:{level}")
                    continue
                values[(uw_name, track_name, level)] = value
    return values, missing


def _parse_level_index(value: str) -> Optional[int]:
    if not value:
        return None
    cleaned = value.strip()
    if "locked" in cleaned.lower():
        return 0
    match = _UW_LEVEL_RE.match(cleaned)
    if not match:
        return None
    return int(match.group(1))


def _parse_uw_value(value: str) -> Optional[float]:
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "locked":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_next_cost(descriptor: str) -> Optional[float]:
    match = _UW_NEXT_COST_RE.search(descriptor)
    if not match:
        return None
    return float(match.group(1))


def _uw_provenance(spec: UWTrackSpec) -> str:
    return "uw_section:_IDS.csv"


__all__ = ["CompiledBaselineLoadout", "CompiledStatInputs", "compile_baseline_account_stat_inputs", "compile_baseline_gem_respec_stat_inputs", "compile_baseline_loadout_stat_inputs", "compile_full_stat_inputs", "compile_workshop_values_at_wave"]


def compile_workshop_values_at_wave(
    ids_snapshot: AccountSnapshot,
    *,
    wave: int,
) -> Tuple[Dict[str, float], List[str]]:
    if wave <= 0:
        return {}, ["wave_limit"]

    workshop_tables = load_workshop_tables()
    enhancement_map, enhancement_missing = _parse_workshop_enhancement_multipliers(ids_snapshot)
    missing: List[str] = list(enhancement_missing)
    workshop_stats: List[WorkshopStat] = []
    by_name: Dict[str, Tuple[WorkshopStatSpec, WorkshopEntrySnapshot]] = {}

    for name, entry in ids_snapshot.workshop.items():
        if entry.coin_level is None:
            missing.append(f"workshop_level:{name}")
            continue
        if entry.max_level is None:
            missing.append(f"workshop_max_level:{name}")
            continue
        if entry.coin_level < 0 or entry.coin_level > entry.max_level:
            missing.append(f"workshop_level_bounds:{name}")
            continue
        spec = _WORKSHOP_STAT_SPECS.get(name)
        if spec is None:
            missing.append(f"workshop_mapping:{name}")
            continue
        if not _has_authoritative_workshop_definition(name, spec, workshop_tables):
            missing.append(f"workshop_definition:{name}")
            continue
        category = _workshop_category(entry.category)
        if category is None:
            continue
        target_level = entry.end_level if entry.end_level is not None else entry.max_level
        if target_level is None:
            continue
        if target_level < 0:
            missing.append(f"workshop_level_bounds:{name}")
            continue
        max_level = entry.max_level if entry.max_level is not None else target_level
        if target_level > max_level:
            missing.append(f"workshop_level_bounds:{name}")
            continue
        stat = WorkshopStat(
            name=name,
            category=category,
            start_level=int(entry.coin_level),
            end_level=int(target_level),
            max_level=int(max_level),
            unlocked=True,
        )
        workshop_stats.append(stat)
        by_name[name] = (spec, entry)

    chances, chance_missing = _free_upgrade_chances(ids_snapshot, enhancement_map)
    missing.extend(chance_missing)
    if chance_missing:
        return {}, sorted(set(missing))

    result = simulate_workshop_progression(
        workshop_stats,
        chances,
        max_waves=wave,
        allocation_policy=uniform_allocation,
        waves_skipped_per_wave=0.0,
    )

    values: Dict[str, float] = {}
    for stat in workshop_stats:
        spec, _entry = by_name[stat.name]
        track = result.levels.get(stat.name)
        if not track:
            continue
        idx = min(wave, len(track) - 1)
        level = int(track[idx])
        formula = _WORKSHOP_FORMULAS.get(stat.name)
        if formula is not None:
            resolved = formula(level)
            if resolved is None:
                missing.append(f"workshop_unsupported:{stat.name}")
                continue
            value = float(resolved)
        else:
            try:
                value = _resolve_workshop_value(workshop_tables, spec, level=level)
            except KeyError:
                missing.append(f"workshop_table:{stat.name}")
                continue
        mult = enhancement_map.get(spec.stat_id, 1.0)
        values[spec.stat_id] = float(value) * float(mult)

    canonical_values = _canonicalize_workshop_values(values)
    tower_hp = canonical_values.get("tower_hp")
    tower_regen = canonical_values.get("tower_regen")
    wall_health_ratio = canonical_values.get("workshop_wall_health")
    if (
        tower_hp is not None
        and tower_regen is not None
        and wall_health_ratio is not None
    ):
        wall_health_lab = ids_snapshot.labs.get("Wall Health") or 0
        if wall_health_lab > 0:
            labs = load_labs_values()
            wall_health_data = labs.get("Wall Health")
            if (
                wall_health_data is not None
                and wall_health_lab in wall_health_data.levels
                and wall_health_data.unit in {"percent", "percent_points"}
            ):
                wall_health_ratio += float(wall_health_data.levels[wall_health_lab]) / 100.0

        wall_regen_ratio = canonical_values.get("workshop_wall_regen")
        wall_regen_entry = ids_snapshot.workshop.get("Wall Regen")
        wall_regen_blocked = (
            wall_regen_entry is not None
            and wall_regen_entry.coin_level is not None
            and wall_regen_ratio is None
        )
        if wall_regen_blocked:
            missing.append("workshop_alias_missing:workshop_wall_regen")
            wall_regen_ratio = 0.0
        elif wall_regen_ratio is None:
            wall_regen_ratio = 0.0
        wall_regen_lab = ids_snapshot.labs.get("Wall Regen") or 0
        if wall_regen_lab > 0:
            labs = load_labs_values()
            wall_regen_data = labs.get("Wall Regen")
            if (
                wall_regen_data is not None
                and wall_regen_lab in wall_regen_data.levels
                and wall_regen_data.unit in {"percent", "percent_points"}
            ):
                wall_regen_ratio += float(wall_regen_data.levels[wall_regen_lab]) / 100.0

        canonical_values["wall_hp"] = float(tower_hp) * float(wall_health_ratio)
        canonical_values["wall_regen"] = float(tower_regen) * float(wall_regen_ratio)


    wall_thorns_entry = ids_snapshot.workshop.get("Wall Thorns")
    if wall_thorns_entry is not None and wall_thorns_entry.coin_level is not None:
        if wall_thorns_entry.coin_level < 0:
            missing.append("workshop_level_bounds:Wall Thorns")
        else:
            canonical_values["wall_thorns_mult"] = float(wall_thorns_entry.coin_level) / 100.0

    return canonical_values, sorted(set(missing))


def _workshop_category(raw: str | None) -> WSCategory | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized == "attack":
        return WSCategory.OFFENSE
    if normalized == "defense":
        return WSCategory.DEFENSE
    if normalized == "utility":
        return WSCategory.UTILITY
    return None


_compile_full = compile_full_stat_inputs


def _free_upgrade_chances(
    ids_snapshot: AccountSnapshot,
    enhancement_map: Dict[str, float],
) -> Tuple[FreeUpgradeChances, List[str]]:
    missing: List[str] = []

    compiled = _compile_full(ids_snapshot, include_workshop=True, include_uw=False)
    start_values = _workshop_start_values(compiled.stat_inputs)

    attack = start_values.get("workshop_free_attack_upgrade")
    defense = start_values.get("workshop_free_defense_upgrade")
    utility = start_values.get("workshop_free_utility_upgrade")
    if attack is None:
        missing.append("stat_input:workshop_free_attack_upgrade")
    if defense is None:
        missing.append("stat_input:workshop_free_defense_upgrade")
    if utility is None:
        missing.append("stat_input:workshop_free_utility_upgrade")
    if missing:
        return FreeUpgradeChances(attack=0.0, defense=0.0, utility=0.0), missing

    upgrade_mult = enhancement_map.get("workshop_free_upgrades", 1.0)
    return (
        FreeUpgradeChances(
            attack=float(attack) * upgrade_mult,
            defense=float(defense) * upgrade_mult,
            utility=float(utility) * upgrade_mult,
        ),
        [],
    )


def _workshop_start_values(stat_inputs: List[StatInput]) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for stat_input in stat_inputs:
        if stat_input.phase != Phase.START_OF_RUN:
            continue
        if not stat_input.stat_id.startswith("workshop_"):
            continue
        values[stat_input.stat_id] = _compose_stat_input_value(stat_input)
    return values


def _compose_stat_input_value(stat_input: StatInput) -> float:
    if stat_input.derived_value is not None:
        return float(stat_input.derived_value)
    base_value = stat_input.base_value or 0.0
    loadout_delta = stat_input.loadout_delta or 0.0
    enhancement = stat_input.enhancement_multiplier or 1.0
    tier_delta = stat_input.tier_rule_delta or 0.0
    value = (base_value + loadout_delta) * enhancement
    if stat_input.tier_rule_multiplier is not None:
        value *= stat_input.tier_rule_multiplier
    value += tier_delta
    return float(value)
