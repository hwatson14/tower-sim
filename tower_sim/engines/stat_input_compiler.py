from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Optional, Tuple

from tower_sim.engines.stat_engine import StatInput
from tower_sim.libs.workshop_lib import WorkshopTables, load_workshop_tables, workshop_value
from tower_sim.libs.uw_lib import load_uw_table
from tower_sim.registry.stat_registry import Phase
from tower_sim.util.account_snapshot import AccountSnapshot


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
    csv_file: str


_UW_LEVEL_RE = re.compile(r"^(\d+)")


_WORKSHOP_STAT_SPECS: Dict[str, WorkshopStatSpec] = {
    "Damage": WorkshopStatSpec(stat_id="workshop_damage_mult", wsvalues_key="Damage"),
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
    "Attack Speed": WorkshopStatSpec(stat_id="workshop_attack_speed", dvt_keys=("Attack Speed",)),
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
    "Wall Health": WorkshopStatSpec(stat_id="workshop_wall_health", dvt_keys=("Wall Health",)),
    "Orb Size": WorkshopStatSpec(stat_id="workshop_orb_size", dvt_keys=("Orb Size",)),
    "Cash Bonus": WorkshopStatSpec(stat_id="workshop_cash_bonus", dvt_keys=("Cash Bonus",)),
    "Coin Bonus": WorkshopStatSpec(
        stat_id="workshop_coins_per_kill_bonus", dvt_keys=("Coin Bonus",)
    ),
    "Cells / Kill Bonus": WorkshopStatSpec(
        stat_id="workshop_cells_per_kill_bonus", dvt_keys=("Cells / Kill Bonus",)
    ),
    "Free Upgrades": WorkshopStatSpec(stat_id="workshop_free_upgrades", dvt_keys=("Free Upgrades",)),
    "Recovery Package": WorkshopStatSpec(
        stat_id="workshop_recovery_packages", dvt_keys=("Recovery Package",)
    ),
    "Enemy Level Skip": WorkshopStatSpec(
        stat_id="workshop_enemy_level_skip", dvt_keys=("Enemy Level Skip",)
    ),
    "Rend Armor": WorkshopStatSpec(stat_id="workshop_rend_armor", dvt_keys=("Rend Armor",)),
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

    return CompiledStatInputs(
        stat_inputs=stat_inputs,
        missing=sorted(set(missing)),
    )


def _compile_workshop_stat_inputs(
    ids_snapshot: AccountSnapshot,
) -> Tuple[List[StatInput], List[str]]:
    workshop_tables = load_workshop_tables()
    stat_inputs: List[StatInput] = []
    missing: List[str] = []

    for name, entry in ids_snapshot.workshop.items():
        if entry.coin_level is None:
            missing.append(f"workshop_level:{name}")
            continue
        spec = _WORKSHOP_STAT_SPECS.get(name)
        if spec is None:
            missing.append(f"workshop_mapping:{name}")
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
                provenance=_workshop_provenance(name),
            )
        )
    return stat_inputs, missing


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

    uw_tracks, uw_missing = _parse_uw_tracks(ids_snapshot.raw_sections.get("UWs", []))
    missing.extend(uw_missing)
    tables: Dict[str, List[Dict[str, str]]] = {}

    for uw_name, track_name, level_index in uw_tracks:
        mapping = _UW_TRACK_SPECS.get(uw_name)
        if mapping is None or track_name not in mapping:
            missing.append(f"uw_mapping:{uw_name}:{track_name}")
            continue
        spec = mapping[track_name]
        rows = tables.get(spec.csv_file)
        if rows is None:
            rows = _load_uw_rows(spec.csv_file)
            tables[spec.csv_file] = rows
        try:
            value, next_cost = _resolve_uw_values(rows, level_index)
        except (IndexError, ValueError):
            missing.append(f"uw_level:{uw_name}:{track_name}")
            continue

        stat_inputs.append(
            StatInput(
                stat_id=spec.stat_id,
                phase=Phase.START_OF_RUN,
                base_value=value,
                provenance=_uw_provenance(spec.csv_file),
            )
        )
        if next_cost is not None:
            stat_inputs.append(
                StatInput(
                    stat_id=f"{spec.stat_id}_next_cost",
                    phase=Phase.START_OF_RUN,
                    base_value=next_cost,
                    provenance=_uw_provenance(spec.csv_file),
                )
            )
    return stat_inputs, missing


def _parse_uw_tracks(
    rows: Iterable[List[str]],
) -> Tuple[List[Tuple[str, str, int]], List[str]]:
    tracks: List[Tuple[str, str, int]] = []
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
        tracks.append((current, track_name, level_index))
    return tracks, missing


def _parse_level_index(value: str) -> Optional[int]:
    if not value:
        return None
    match = _UW_LEVEL_RE.match(value.strip())
    if not match:
        return None
    return int(match.group(1))


def _load_uw_rows(filename: str) -> List[Dict[str, str]]:
    table = load_uw_table(filename)
    rows: List[Dict[str, str]] = []
    indices = table.columns.get("level_index")
    values = table.columns.get("value")
    costs = table.columns.get("cost")
    if indices is None or values is None or costs is None:
        raise ValueError(f"UW table {filename} missing required columns.")
    for idx, value, cost in zip(indices, values, costs):
        rows.append({"level_index": idx, "value": value, "cost": cost})
    return rows


def _resolve_uw_values(rows: List[Dict[str, str]], level_index: int) -> Tuple[float, Optional[float]]:
    if level_index < 0 or level_index >= len(rows):
        raise IndexError("UW level index out of range.")
    row = rows[level_index]
    value = float(row["value"])
    next_cost = _uw_next_cost(rows, level_index)
    return value, next_cost


def _uw_next_cost(rows: List[Dict[str, str]], level_index: int) -> Optional[float]:
    current_cost = rows[level_index]["cost"].strip()
    if current_cost.lower() == "max":
        return None
    next_index = level_index + 1
    if next_index >= len(rows):
        return None
    next_cost = rows[next_index]["cost"]
    if next_cost.strip().lower() == "max":
        return None
    return float(next_cost)


def _uw_provenance(csv_file: str) -> str:
    return f"reference/uw_tables_v2_1_2.zip:{csv_file}"


__all__ = ["CompiledStatInputs", "compile_full_stat_inputs"]
