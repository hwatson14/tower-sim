from __future__ import annotations

import csv
from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.libs.workshop_lib import WorkshopTables, load_workshop_tables, workshop_value
from tower_sim.loaders.table_paths import resolve_table_path
from tower_sim.registry.stat_registry import Phase
from tower_sim.util.account_snapshot import AccountSnapshot, WorkshopEntrySnapshot
from tower_sim.engines.free_upgrades import FreeUpgradeChances
from tower_sim.engines.workshop_progression import WSCategory, WorkshopStat, simulate_workshop_progression, uniform_allocation
from tower_sim.libs.labs_lib import load_labs_values
from tower_sim.loaders.wiki.enemy_level_skip import workshop_level_to_chance

@dataclass(frozen=True)
class CompiledStatInputs:
    stat_inputs: List[StatInput]
    missing: List[str]


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
    "Health": "tower_hp",
    "Health Regen": "tower_regen",
    "Defense %": "def_pct",
    "Thorn Damage": "thorns_damage_mult",
    "Enemy Attack Level Skip": "eals_pct",
    "Enemy Health Level Skip": "ehls_pct",
    "Critical Chance": "tower_crit_chance",
    "Critical Factor": "tower_crit_multiplier",
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
    "Rend Armor Chance": lambda level: _pct(0.5 + 0.1 * level),
    "Rend Armor Mult": lambda level: 0.001 + 0.001 * level,
    "Knockback Chance": lambda level: _pct(1.0 * level),
    "Knockback Force": lambda level: 0.4 + 0.15 * level,
    "Shockwave Size": lambda level: 0.6 + 0.05 * level,
    "Shockwave Frequency": lambda level: 17 - 0.15 * level,
    "Land Mine Chance": lambda level: _pct(12 + 6 * level),
    "Land Mine Radius": lambda level: 0.5 + 0.02 * level,
    "Orbs": lambda level: level,
    "Orb Speed": lambda level: 0.4 + 0.15 * level,
    "Recovery Amount": lambda level: 0.1 + 0.01 * level,
    "Package Chance": lambda level: _pct(6 + 0.4 * level),
    "Wall Rebuild": lambda level: 0.01 + 0.01 * level,
    "Coins per Kill": lambda level: 1 + _pct(0.01 * level),
    "Coin / Kill Bonus": lambda level: 1 + _pct(0.01 * level),
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


def compile_full_stat_inputs(
    ids_snapshot: AccountSnapshot,
    *,
    include_workshop: bool = True,
    include_uw: bool = True,
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

    return CompiledStatInputs(
        stat_inputs=stat_inputs,
        missing=sorted(set(missing)),
    )




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
        (("Defense", "Defense %"), "def_pct", "delta", "relics:defense"),
        (("Enemy Attack Level Skip",), "eals_pct", "delta", "relics:eals"),
        (("Enemy Health Level Skip",), "ehls_pct", "delta", "relics:ehls"),
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

def _compile_workshop_stat_inputs(
    ids_snapshot: AccountSnapshot,
) -> Tuple[List[StatInput], List[str]]:
    workshop_tables = load_workshop_tables()
    labs = load_labs_values()
    enhancement_map, enhancement_missing = _parse_workshop_enhancement_multipliers(ids_snapshot)
    stat_inputs: List[StatInput] = []
    missing: List[str] = list(enhancement_missing)

    for name, entry in ids_snapshot.workshop.items():
        if entry.coin_level is None:
            missing.append(f"workshop_level:{name}")
            continue
        spec = _WORKSHOP_STAT_SPECS.get(name)
        if spec is None:
            missing.append(f"workshop_mapping:{name}")
            continue
        formula = _WORKSHOP_FORMULAS.get(name)
        if name in {"Enemy Attack Level Skip", "Enemy Health Level Skip"}:
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
            value_f = float(value)
            if name in {"Enemy Attack Level Skip", "Enemy Health Level Skip"}:
                value_f = min(max(value_f + lab_delta, 0.0), 1.0)
            stat_inputs.append(
                StatInput(
                    stat_id=spec.stat_id,
                    phase=Phase.START_OF_RUN,
                    base_value=value_f,
                    enhancement_multiplier=enhancement_multiplier,
                    provenance="workshop_formula:DVT_WS_VALUE",
                )
            )
            canonical_stat_id = _WORKSHOP_CANONICAL_ALIASES.get(name)
            if canonical_stat_id is not None:
                stat_inputs.append(
                    StatInput(
                        stat_id=canonical_stat_id,
                        phase=Phase.START_OF_RUN,
                        base_value=value_f,
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
    wall_regen = _resolved_stat_input_value(tower_regen) * wall_regen_ratio
    return [
        StatInput(
            stat_id="wall_hp",
            phase=Phase.START_OF_RUN,
            base_value=wall_hp,
            provenance="workshop_alias:Wall Health->wall_hp",
        ),
        StatInput(
            stat_id="wall_regen",
            phase=Phase.START_OF_RUN,
            base_value=wall_regen,
            provenance="workshop_alias:Wall Regen->wall_regen",
        ),
    ], missing


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


def _workshop_provenance(name: str) -> str:
    return f"workshop_table:{name}"


def _compile_uw_stat_inputs(ids_snapshot: AccountSnapshot) -> Tuple[List[StatInput], List[str]]:
    stat_inputs: List[StatInput] = []
    missing: List[str] = []
    ladder_values, ladder_missing = _load_uw_track_values()
    missing.extend(ladder_missing)

    uw_tracks, uw_missing = _parse_uw_tracks(ids_snapshot.raw_sections.get("UWs", []))
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

        stat_inputs.append(
            StatInput(
                stat_id=spec.stat_id,
                phase=Phase.START_OF_RUN,
                base_value=value,
                provenance=_uw_provenance(spec),
            )
        )
        if next_cost is not None:
            stat_inputs.append(
                StatInput(
                    stat_id=f"{spec.stat_id}_next_cost",
                    phase=Phase.START_OF_RUN,
                    base_value=next_cost,
                    provenance=_uw_provenance(spec),
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


__all__ = ["CompiledStatInputs", "compile_full_stat_inputs", "compile_workshop_values_at_wave"]


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
            continue
        spec = _WORKSHOP_STAT_SPECS.get(name)
        if spec is None:
            continue
        category = _workshop_category(entry.category)
        if category is None:
            continue
        target_level = entry.end_level if entry.end_level is not None else entry.max_level
        if target_level is None:
            continue
        max_level = entry.max_level if entry.max_level is not None else target_level
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

        wall_regen_ratio = canonical_values.get("workshop_wall_regen", 0.0)
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
