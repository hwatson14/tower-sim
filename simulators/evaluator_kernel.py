from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from math import inf, isfinite
from pathlib import Path
from typing import Any, Mapping

from qe.kb_surfaces import (
    BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT,
    BOSS_HP_MULTIPLIER,
    ELECTRON_BOSS_REMAINING_HP_PCT,
    THORNS_BOSS_EFFECTIVENESS,
)
from qe.run_plan import (
    ColumnFormulaSpec,
    CommonTrajectoryRow,
    CommonTrajectoryTable,
    SurvivabilityContributorBundle,
    WaveProgressionRecurrence,
    advance_wave_progression,
)


ROOT = Path(__file__).resolve().parents[1]
ENEMY_DAMAGE_TABLE = ROOT / "kb" / "enemies" / "tables" / "enemy-damage-table.csv"
ENEMY_HEALTH_TABLE = ROOT / "kb" / "enemies" / "tables" / "enemy-health-table.csv"
KILL_HP_THRESHOLD = 1e-9
LANE_ORDER: tuple[str, str, str] = ("avg", "min", "max")
SUMMARY_LANE_ID = "avg"


TABLE2_COLUMN_REGISTRY: tuple[ColumnFormulaSpec, ...] = (
    ColumnFormulaSpec("row_key", "simulators", "str", ("source_row_key", "scenario_key"), "identity", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("effective_attack_wave", "simulators", "int", ("table1.wave_progression", "scenario.attack_skip"), "scenario_overlay", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("effective_health_wave", "simulators", "int", ("table1.wave_progression", "scenario.health_skip"), "scenario_overlay", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("enemy_attack", "simulators", "float", ("effective_attack_wave", "enemy_damage_table"), "table_lookup", "per_overlay_row", "kb_cached"),
    ColumnFormulaSpec("enemy_health", "simulators", "float", ("effective_health_wave", "enemy_health_table", "boss_multiplier"), "table_lookup", "per_overlay_row", "kb_cached"),
    ColumnFormulaSpec("final_wall_hp", "simulators", "float", ("table1.survivability_contributors", "scenario.wall_hp_multiplier"), "staged_contributor_formula", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("final_wall_regen", "simulators", "float", ("table1.survivability_contributors", "scenario.wall_regen_multiplier"), "staged_contributor_formula", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("lane_evaluations", "simulators", "tuple[CombatLaneEvaluation]", ("final_wall_hp", "final_wall_regen", "v21_ttk"), "lane_evaluation", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("summary_lane_id", "simulators", "str", ("summary_lane_policy",), "explicit_policy", "per_overlay_row", "plan_static"),
    ColumnFormulaSpec("summary_combat", "simulators", "CombatLaneEvaluation", ("lane_evaluations", "summary_lane_id"), "explicit_policy_lookup", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("operator_handle", "simulators", "OperatorLookupHandle", ("row_key", "summary_lane_id"), "identity", "per_overlay_row", "row_static"),
)


class KernelAmbiguityError(ValueError):
    """Raised when a staged-kernel input would require guessed mechanics."""


@dataclass(frozen=True)
class ScenarioSurvivabilityTransforms:
    wall_hp_multiplier: float = 1.0
    wall_regen_multiplier: float = 1.0
    wall_fortification_multiplier: float = 1.0
    incoming_damage_multiplier: float = 1.0
    enemy_attack_multiplier: float = 1.0
    enemy_health_multiplier: float = 1.0
    dr_bonus_by_lane: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioOverlayInputs:
    scenario_key: str
    tier_column: str
    battle_conditions: tuple[str, ...] = ()
    heat: Mapping[str, float] = field(default_factory=dict)
    tournament_perks_enabled: bool = True
    removed_perk_ids: tuple[str, ...] = ()
    attack_skip_chance_delta: float = 0.0
    health_skip_chance_delta: float = 0.0
    survivability_transforms: ScenarioSurvivabilityTransforms = field(default_factory=ScenarioSurvivabilityTransforms)


@dataclass(frozen=True)
class CombatInputs:
    plasma_cannon_effect_pct: float = 0.0
    tower_thorns_damage_pct: float = 0.0
    orb_boss_hit_pct: float | None = None
    orb_boss_hits_per_second: float | None = None
    electron_hits_per_second: float | None = None
    boss_contact_time_seconds: float | None = None
    boss_hit_interval_seconds: float = 2.0
    max_ttk_seconds: float = 120.0
    plasma_cannon_resistance_multiplier: float = 1.0
    orb_resistance_multiplier: float = 1.0
    thorns_resistance_multiplier: float = 1.0


@dataclass(frozen=True)
class OperatorLookupHandle:
    handle_id: str
    table1_row_key: str
    table2_row_key: str
    display_wave: int
    scenario_key: str
    summary_lane_id: str
    lane_handle_ids: Mapping[str, str]


@dataclass(frozen=True)
class CombatLaneEvaluation:
    lane_id: str
    survives: bool
    fail_reason: str | None
    ttk_seconds: float
    boss_hits_taken: int
    total_damage_taken: float
    survival_margin_hp: float
    wall_pool_hp: float
    wall_regen_gained_hp: float
    damage_reduction_fraction: float


@dataclass(frozen=True)
class ScenarioOverlayRow:
    row_key: str
    source_row_key: str
    display_wave: int
    scenario_key: str
    battle_conditions: tuple[str, ...]
    heat: Mapping[str, float]
    tournament_perks_enabled: bool
    active_perk_counts: Mapping[str, int]
    removed_perk_ids: tuple[str, ...]
    effective_attack_skip_chance: float
    effective_health_skip_chance: float
    effective_attack_wave: int
    effective_health_wave: int
    enemy_attack: float
    enemy_health: float
    final_wall_hp: float
    final_wall_regen: float
    lane_evaluations: tuple[CombatLaneEvaluation, ...]
    summary_lane_id: str
    summary_combat: CombatLaneEvaluation
    operator_handle: OperatorLookupHandle

    @property
    def damage_reduction_pct(self) -> float:
        return self.summary_combat.damage_reduction_fraction * 100.0

    @property
    def combat(self) -> CombatLaneEvaluation:
        return self.summary_combat

    def to_operator_row(self) -> dict[str, Any]:
        return {
            "handle_id": self.operator_handle.handle_id,
            "display_wave": self.display_wave,
            "scenario_key": self.scenario_key,
            "summary_lane_id": self.summary_lane_id,
            "enemy_attack": self.enemy_attack,
            "enemy_health": self.enemy_health,
            "wall_hp": self.final_wall_hp,
            "wall_regen": self.final_wall_regen,
            "damage_reduction_pct": self.damage_reduction_pct,
            "survival_margin_hp": self.summary_combat.survival_margin_hp,
            "survives": self.summary_combat.survives,
            "fail_reason": self.summary_combat.fail_reason,
            "lane_handle_ids": dict(self.operator_handle.lane_handle_ids),
        }


@dataclass(frozen=True)
class ScenarioOverlayTable:
    table_id: str
    rows: tuple[ScenarioOverlayRow, ...]
    column_registry: tuple[ColumnFormulaSpec, ...]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


def build_scenario_overlay_table(
    table1: CommonTrajectoryTable,
    *,
    scenario: ScenarioOverlayInputs,
    combat: CombatInputs,
) -> ScenarioOverlayTable:
    rows = tuple(evaluate_overlay_row(row, scenario=scenario, combat=combat) for row in table1.rows)
    table = ScenarioOverlayTable(
        table_id="boss_waves.scenario_overlay.v1",
        rows=rows,
        column_registry=TABLE2_COLUMN_REGISTRY,
        diagnostics={
            "row_count": len(rows),
            "source_table_id": table1.table_id,
            "scenario_key": scenario.scenario_key,
            "summary_lane_id": SUMMARY_LANE_ID,
            "lane_order": LANE_ORDER,
        },
    )
    validate_table2_registry(table)
    return table


def evaluate_overlay_row(
    row: CommonTrajectoryRow,
    *,
    scenario: ScenarioOverlayInputs,
    combat: CombatInputs,
) -> ScenarioOverlayRow:
    _validate_combat(combat)
    transforms = scenario.survivability_transforms
    effective_attack_skip = _bounded_fraction(float(row.common_inputs.get("attack_skip_chance", 0.0)) + float(scenario.attack_skip_chance_delta))
    effective_health_skip = _bounded_fraction(float(row.common_inputs.get("health_skip_chance", 0.0)) + float(scenario.health_skip_chance_delta))
    effective_progression = _effective_progression_for_row(
        row.wave_progression,
        start_progression_wave=int(row.common_inputs.get("start_progression_wave", 0)),
        attack_skip_chance=effective_attack_skip,
        health_skip_chance=effective_health_skip,
    )
    enemy_attack = _required_enemy_value(ENEMY_DAMAGE_TABLE, effective_progression.attack_wave, scenario.tier_column) * max(0.0, float(transforms.enemy_attack_multiplier))
    enemy_health = (
        _required_enemy_value(ENEMY_HEALTH_TABLE, effective_progression.health_wave, scenario.tier_column)
        * float(BOSS_HP_MULTIPLIER)
        * max(0.0, float(transforms.enemy_health_multiplier))
        * max(0.0, float(row.death_wave_health_multiplier))
    )
    final_wall_hp = _derive_wall_hp(row.survivability_contributors, transforms)
    final_wall_regen = _derive_wall_regen(row.survivability_contributors, transforms)
    lane_drs = _derive_lane_damage_reduction(row.survivability_contributors, transforms)
    ttk_seconds = _simulate_boss_ttk(enemy_health=enemy_health, combat=combat)
    lane_evaluations = tuple(
        _evaluate_boss_ttd_lane(
            lane_id=lane_id,
            enemy_attack=enemy_attack,
            wall_hp=final_wall_hp,
            wall_regen=final_wall_regen,
            wall_fortification_multiplier=row.survivability_contributors.wall_fortification_multiplier * max(0.0, float(transforms.wall_fortification_multiplier)),
            damage_reduction_fraction=lane_drs[lane_id],
            incoming_damage_multiplier=max(0.0, float(transforms.incoming_damage_multiplier)),
            ttk_seconds=ttk_seconds,
            combat=combat,
        )
        for lane_id in LANE_ORDER
    )
    summary = _summary_lane(lane_evaluations)
    table2_key = f"table2:{scenario.scenario_key}:{row.checkpoint_index}:{row.display_wave}"
    lane_handle_ids = {lane.lane_id: f"boss:{scenario.scenario_key}:{row.display_wave}:{lane.lane_id}" for lane in lane_evaluations}
    handle = OperatorLookupHandle(
        handle_id=f"boss:{scenario.scenario_key}:{row.display_wave}:{SUMMARY_LANE_ID}",
        table1_row_key=row.row_key,
        table2_row_key=table2_key,
        display_wave=row.display_wave,
        scenario_key=scenario.scenario_key,
        summary_lane_id=SUMMARY_LANE_ID,
        lane_handle_ids=lane_handle_ids,
    )
    return ScenarioOverlayRow(
        row_key=table2_key,
        source_row_key=row.row_key,
        display_wave=row.display_wave,
        scenario_key=scenario.scenario_key,
        battle_conditions=tuple(scenario.battle_conditions),
        heat=dict(scenario.heat),
        tournament_perks_enabled=bool(scenario.tournament_perks_enabled),
        active_perk_counts=_active_perk_counts(row, scenario),
        removed_perk_ids=tuple(scenario.removed_perk_ids),
        effective_attack_skip_chance=effective_attack_skip,
        effective_health_skip_chance=effective_health_skip,
        effective_attack_wave=effective_progression.attack_wave,
        effective_health_wave=effective_progression.health_wave,
        enemy_attack=enemy_attack,
        enemy_health=enemy_health,
        final_wall_hp=final_wall_hp,
        final_wall_regen=final_wall_regen,
        lane_evaluations=lane_evaluations,
        summary_lane_id=SUMMARY_LANE_ID,
        summary_combat=summary,
        operator_handle=handle,
    )


def validate_table2_registry(table: ScenarioOverlayTable) -> None:
    registry_ids = frozenset(spec.column_id for spec in table.column_registry)
    for row in table.rows:
        missing = [column_id for column_id in registry_ids if not hasattr(row, column_id)]
        if missing:
            raise ValueError(f"Table 2 row missing registered columns: {missing!r}")


def _derive_wall_hp(contributors: SurvivabilityContributorBundle, transforms: ScenarioSurvivabilityTransforms) -> float:
    _validate_survivability_contributors(contributors)
    base = contributors.base_wall_hp + contributors.workshop_wall_hp + contributors.lab_wall_hp + contributors.enhancement_wall_hp + contributors.module_flat_wall_hp
    return base * max(0.0, float(contributors.wall_hp_multiplier)) * max(0.0, float(transforms.wall_hp_multiplier))


def _derive_wall_regen(contributors: SurvivabilityContributorBundle, transforms: ScenarioSurvivabilityTransforms) -> float:
    _validate_survivability_contributors(contributors)
    base = contributors.base_wall_regen + contributors.workshop_wall_regen + contributors.lab_wall_regen + contributors.enhancement_wall_regen + contributors.module_flat_wall_regen
    return base * max(0.0, float(contributors.wall_regen_multiplier)) * max(0.0, float(transforms.wall_regen_multiplier))


def _derive_lane_damage_reduction(contributors: SurvivabilityContributorBundle, transforms: ScenarioSurvivabilityTransforms) -> dict[str, float]:
    defense = _bounded_percent(contributors.tower_defense_pct) / 100.0
    out: dict[str, float] = {}
    for lane_id in LANE_ORDER:
        timed = _bounded_fraction(contributors.timed_dr_by_lane.get(lane_id, 0.0))
        scenario_bonus = _bounded_fraction(transforms.dr_bonus_by_lane.get(lane_id, 0.0))
        out[lane_id] = _bounded_fraction(1.0 - ((1.0 - defense) * (1.0 - timed) * (1.0 - scenario_bonus)))
    if not 0.0 <= out["min"] <= out["avg"] <= out["max"] <= 1.0:
        raise KernelAmbiguityError("lane DR invariant failed: expected 0 <= min <= avg <= max <= 1")
    return out


def _effective_progression_for_row(progression: WaveProgressionRecurrence, *, start_progression_wave: int, attack_skip_chance: float, health_skip_chance: float) -> WaveProgressionRecurrence:
    start_wave = max(0, int(start_progression_wave))
    return advance_wave_progression(
        WaveProgressionRecurrence(display_wave=start_wave, attack_wave=start_wave, health_wave=start_wave),
        target_display_wave=int(progression.display_wave),
        attack_skip_chance=attack_skip_chance,
        health_skip_chance=health_skip_chance,
    )


def _active_perk_counts(row: CommonTrajectoryRow, scenario: ScenarioOverlayInputs) -> dict[str, int]:
    counts = {str(k): int(v) for k, v in row.compiled_perk_state.counts.items()}
    if scenario.tournament_perks_enabled:
        return counts
    removed = set(str(perk_id) for perk_id in scenario.removed_perk_ids)
    if not removed:
        raise KernelAmbiguityError("tournament perk removal requested without removed_perk_ids")
    missing = sorted(perk_id for perk_id in removed if perk_id not in counts)
    if missing:
        raise KernelAmbiguityError(f"tournament perk removal references unknown compiled perk ids: {missing!r}")
    return {perk_id: count for perk_id, count in counts.items() if perk_id not in removed}


def _summary_lane(lanes: tuple[CombatLaneEvaluation, ...]) -> CombatLaneEvaluation:
    for lane in lanes:
        if lane.lane_id == SUMMARY_LANE_ID:
            return lane
    raise KernelAmbiguityError(f"summary lane {SUMMARY_LANE_ID!r} was not evaluated")


def _evaluate_boss_ttd_lane(
    *,
    lane_id: str,
    enemy_attack: float,
    wall_hp: float,
    wall_regen: float,
    wall_fortification_multiplier: float,
    damage_reduction_fraction: float,
    incoming_damage_multiplier: float,
    ttk_seconds: float,
    combat: CombatInputs,
) -> CombatLaneEvaluation:
    wall_pool = wall_hp * max(0.0, float(wall_fortification_multiplier))
    wall_regen_gained = max(0.0, wall_regen * ttk_seconds)
    if combat.boss_contact_time_seconds is None:
        return CombatLaneEvaluation(lane_id, True, None, ttk_seconds, 0, 0.0, wall_pool + wall_regen_gained, wall_pool, wall_regen_gained, damage_reduction_fraction)
    interval = float(combat.boss_hit_interval_seconds)
    if interval <= 0:
        raise KernelAmbiguityError("boss_hit_interval_seconds must be positive")
    hit_t = float(combat.boss_contact_time_seconds)
    total_damage = 0.0
    hits = 0
    while hit_t <= ttk_seconds + 1e-12:
        heat_multiplier = 1.0 + BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT * hits
        total_damage += float(enemy_attack) * incoming_damage_multiplier * heat_multiplier * max(0.0, 1.0 - damage_reduction_fraction)
        hits += 1
        hit_t += interval
    margin = wall_pool + wall_regen_gained - total_damage
    return CombatLaneEvaluation(lane_id, margin >= 0.0, None if margin >= 0.0 else "boss_wall_damage_exceeds_pool", ttk_seconds, hits, total_damage, margin, wall_pool, wall_regen_gained, damage_reduction_fraction)


def _simulate_boss_ttk(*, enemy_health: float, combat: CombatInputs) -> float:
    if combat.orb_boss_hit_pct is None or combat.orb_boss_hits_per_second is None:
        raise KernelAmbiguityError("orb boss hit cadence is required for boss TTK")
    if combat.electron_hits_per_second is None:
        raise KernelAmbiguityError("electron hit cadence is required for boss TTK")
    pc_pct = _bounded_percent(combat.plasma_cannon_effect_pct) / 100.0
    pc_pct *= max(0.0, float(combat.plasma_cannon_resistance_multiplier))
    remaining_hp = float(enemy_health) * max(0.0, 1.0 - pc_pct)
    if remaining_hp <= KILL_HP_THRESHOLD:
        return 0.0
    orb_pct = (_bounded_percent(float(combat.orb_boss_hit_pct)) / 100.0) * max(0.0, float(combat.orb_resistance_multiplier))
    electron_pct = ELECTRON_BOSS_REMAINING_HP_PCT
    orb_rate = float(combat.orb_boss_hits_per_second)
    electron_rate = float(combat.electron_hits_per_second)
    if orb_rate <= 0.0 or electron_rate <= 0.0:
        raise KernelAmbiguityError("orb and electron hit rates must be positive")
    next_orb = 1.0 / orb_rate
    next_electron = 1.0 / electron_rate
    next_contact = inf if combat.boss_contact_time_seconds is None else float(combat.boss_contact_time_seconds)
    thorns_pct = (_bounded_percent(combat.tower_thorns_damage_pct) / 100.0) * THORNS_BOSS_EFFECTIVENESS * max(0.0, float(combat.thorns_resistance_multiplier))
    max_ttk = float(combat.max_ttk_seconds)
    while remaining_hp > KILL_HP_THRESHOLD:
        t = min(next_orb, next_electron, next_contact)
        if not isfinite(t) or t > max_ttk:
            raise KernelAmbiguityError("boss TTK exceeded v21 event horizon without kill")
        if abs(next_orb - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - orb_pct)
            next_orb += 1.0 / orb_rate
        if remaining_hp <= KILL_HP_THRESHOLD:
            return t
        if abs(next_electron - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - electron_pct)
            next_electron += 1.0 / electron_rate
        if remaining_hp <= KILL_HP_THRESHOLD:
            return t
        if abs(next_contact - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - thorns_pct)
            if combat.boss_hit_interval_seconds <= 0:
                raise KernelAmbiguityError("boss_hit_interval_seconds must be positive")
            next_contact += float(combat.boss_hit_interval_seconds)
    return 0.0


def _validate_survivability_contributors(contributors: SurvivabilityContributorBundle) -> None:
    for name in ("base_wall_hp", "workshop_wall_hp", "lab_wall_hp", "enhancement_wall_hp", "module_flat_wall_hp", "wall_hp_multiplier", "base_wall_regen", "workshop_wall_regen", "lab_wall_regen", "enhancement_wall_regen", "module_flat_wall_regen", "wall_regen_multiplier", "wall_fortification_multiplier"):
        if float(getattr(contributors, name)) < 0.0:
            raise KernelAmbiguityError(f"survivability contributor {name} cannot be negative")


def _validate_combat(combat: CombatInputs) -> None:
    if float(combat.max_ttk_seconds) <= 0.0:
        raise KernelAmbiguityError("max_ttk_seconds must be positive")


@lru_cache(maxsize=2)
def _load_wave_table(path: Path) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                wave = int(float(row["wave_actual"]))
            except (TypeError, ValueError, KeyError):
                continue
            out[wave] = {}
            for key, value in row.items():
                if key == "wave_actual":
                    continue
                try:
                    out[wave][key] = float(value)
                except (TypeError, ValueError):
                    continue
    return out


def _required_enemy_value(path: Path, wave: int, column: str) -> float:
    table = _load_wave_table(path)
    if int(wave) in table and column in table[int(wave)]:
        return table[int(wave)][column]
    eligible = [key for key in table if key <= int(wave)]
    if not eligible:
        raise KernelAmbiguityError(f"no enemy table row for wave {wave}")
    value = table[max(eligible)].get(column)
    if value is None:
        raise KernelAmbiguityError(f"enemy table column {column!r} is missing")
    return value


def _bounded_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bounded_percent(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
