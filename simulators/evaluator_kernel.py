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
    PERK_CONTRIBUTION_EFFECT_IDS,
    SurvivabilityContributorBundle,
    WaveProgressionRecurrence,
    advance_wave_progression,
)


ROOT = Path(__file__).resolve().parents[1]
ENEMY_DAMAGE_TABLE = ROOT / "kb" / "enemies" / "tables" / "enemy-damage-table.csv"
ENEMY_HEALTH_TABLE = ROOT / "kb" / "enemies" / "tables" / "enemy-health-table.csv"
KILL_HP_THRESHOLD_FRACTION = 1e-9
LANE_ORDER: tuple[str, str, str] = ("avg", "min", "max")
SUMMARY_LANE_ID = "avg"


TABLE2_COLUMN_REGISTRY: tuple[ColumnFormulaSpec, ...] = (
    ColumnFormulaSpec("row_key", "simulators", "str", ("source_row_key", "scenario_key"), "identity", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("effective_attack_wave", "simulators", "int", ("table1.wave_progression", "scenario.attack_skip"), "scenario_overlay", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("effective_health_wave", "simulators", "int", ("table1.wave_progression", "scenario.health_skip"), "scenario_overlay", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("enemy_attack", "simulators", "float", ("effective_attack_wave", "enemy_damage_table"), "table_lookup", "per_overlay_row", "kb_cached"),
    ColumnFormulaSpec("enemy_health", "simulators", "float", ("effective_health_wave", "enemy_health_table", "boss_multiplier"), "table_lookup", "per_overlay_row", "kb_cached"),
    ColumnFormulaSpec("active_perk_contributions", "simulators", "mapping[str,float]", ("table1.compiled_perk_state", "scenario.removed_perk_ids"), "scenario_perk_mask", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("final_wall_hp", "simulators", "float", ("table1.survivability_contributors", "active_perk_contributions", "scenario.wall_hp_multiplier"), "staged_contributor_formula", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("final_wall_regen", "simulators", "float", ("table1.survivability_contributors", "active_perk_contributions", "scenario.wall_regen_multiplier"), "staged_contributor_formula", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("lane_evaluations", "simulators", "tuple[CombatLaneEvaluation]", ("final_wall_hp", "final_wall_regen", "v21_ttk"), "lane_evaluation", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("summary_lane_id", "simulators", "str", ("summary_lane_policy",), "explicit_policy", "per_overlay_row", "plan_static"),
    ColumnFormulaSpec("summary_combat", "simulators", "CombatLaneEvaluation", ("lane_evaluations", "summary_lane_id"), "explicit_policy_lookup", "per_overlay_row", "row_static"),
    ColumnFormulaSpec("operator_handle", "simulators", "OperatorLookupHandle", ("row_key", "summary_lane_id"), "identity", "per_overlay_row", "row_static"),
)
TABLE2_REQUIRED_COLUMN_IDS: frozenset[str] = frozenset(spec.column_id for spec in TABLE2_COLUMN_REGISTRY)
TABLE2_KEY_CONTRACTS: Mapping[str, tuple[tuple[str, ...], str]] = {
    "active_perk_contributions": (("table1.compiled_perk_state", "scenario.removed_perk_ids"), "scenario_perk_mask"),
    "final_wall_hp": (("table1.survivability_contributors", "active_perk_contributions", "scenario.wall_hp_multiplier"), "staged_contributor_formula"),
    "final_wall_regen": (("table1.survivability_contributors", "active_perk_contributions", "scenario.wall_regen_multiplier"), "staged_contributor_formula"),
    "lane_evaluations": (("final_wall_hp", "final_wall_regen", "v21_ttk"), "lane_evaluation"),
    "summary_combat": (("lane_evaluations", "summary_lane_id"), "explicit_policy_lookup"),
}


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
    orb_boss_total_damage_pct: float | None = None
    orb_boss_hit_count: float | None = None
    electron_total_damage_pct: float | None = None
    electron_hit_count: float | None = None
    orb_boss_hits_per_second: float | None = None
    electron_hits_per_second: float | None = None
    boss_time_to_contact_seconds: float | None = None
    boss_hit_interval_seconds: float = 2.0
    max_ttk_seconds: float = 120.0
    plasma_cannon_resistance_multiplier: float = 1.0
    orb_resistance_multiplier: float = 1.0
    thorns_resistance_multiplier: float = 1.0
    wall_thorns_damage_increase_per_hit: float = 0.0


@dataclass(frozen=True)
class BossDamageBreakdown:
    plasma_cannon_damage: float = 0.0
    orb_damage: float = 0.0
    electron_damage: float = 0.0
    thorns_damage: float = 0.0
    plasma_cannon_damage_pct: float = 0.0
    orb_damage_pct: float = 0.0
    electron_damage_pct: float = 0.0
    thorns_damage_pct: float = 0.0
    thorns_expected_damage_pct_from_hits: float = 0.0
    thorns_hits: int = 0


@dataclass(frozen=True)
class BossPreContactKillState:
    ttk_seconds: float | None
    remaining_hp: float
    starting_hp: float
    kill_threshold: float
    damage_breakdown: BossDamageBreakdown
    pre_contact_event_seconds: float | None


@dataclass(frozen=True)
class BossContactThornsResult:
    kill_seconds: float | None
    thorns_damage: float
    thorns_damage_pct: float
    thorns_expected_damage_pct_from_hits: float
    thorns_hits: int


@dataclass(frozen=True)
class BossCombatTimeline:
    ttk_seconds: float
    damage_breakdown: BossDamageBreakdown
    wall_thorns_kill_seconds: float | None
    boss_hits_to_player: int


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
    ttk_seconds: float | None
    contact_thorns_kill_seconds: float | None
    boss_hits_taken: int
    total_damage_taken: float
    survival_margin_hp: float
    wall_hp: float
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
    active_perk_contributions: Mapping[str, float]
    removed_perk_ids: tuple[str, ...]
    effective_attack_skip_chance: float
    effective_health_skip_chance: float
    effective_attack_wave: int
    effective_health_wave: int
    enemy_attack: float
    enemy_health: float
    final_wall_hp: float
    final_wall_regen: float
    boss_damage_breakdown: BossDamageBreakdown
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
            "active_perk_contributions": dict(self.active_perk_contributions),
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
    )
    active_perk_counts, active_perk_contributions = _active_perk_state(row, scenario)
    final_wall_hp = _derive_wall_hp(row.survivability_contributors, transforms, active_perk_contributions)
    final_wall_regen = _derive_wall_regen(row.survivability_contributors, transforms, active_perk_contributions)
    lane_drs = _derive_lane_damage_reduction(row.survivability_contributors, transforms, active_perk_contributions)
    boss_timeline = _simulate_boss_combat_timeline(enemy_health=enemy_health, combat=combat)
    ttk_seconds = boss_timeline.ttk_seconds
    contact_thorns_kill_seconds = boss_timeline.wall_thorns_kill_seconds
    boss_damage_breakdown = boss_timeline.damage_breakdown
    lane_evaluations = tuple(
        _evaluate_boss_ttd_lane(
            lane_id=lane_id,
            enemy_attack=enemy_attack,
            pre_fort_wall_hp=final_wall_hp,
            wall_regen=final_wall_regen,
            wall_fortification_multiplier=row.survivability_contributors.wall_fortification_multiplier * max(0.0, float(transforms.wall_fortification_multiplier)),
            damage_reduction_fraction=lane_drs[lane_id],
            incoming_damage_multiplier=max(0.0, float(transforms.incoming_damage_multiplier)),
            ttk_seconds=ttk_seconds,
            contact_thorns_kill_seconds=contact_thorns_kill_seconds,
            boss_hits_to_player=boss_timeline.boss_hits_to_player,
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
        active_perk_counts=active_perk_counts,
        active_perk_contributions=active_perk_contributions,
        removed_perk_ids=tuple(scenario.removed_perk_ids),
        effective_attack_skip_chance=effective_attack_skip,
        effective_health_skip_chance=effective_health_skip,
        effective_attack_wave=effective_progression.attack_wave,
        effective_health_wave=effective_progression.health_wave,
        enemy_attack=enemy_attack,
        enemy_health=enemy_health,
        final_wall_hp=final_wall_hp,
        final_wall_regen=final_wall_regen,
        boss_damage_breakdown=boss_damage_breakdown,
        lane_evaluations=lane_evaluations,
        summary_lane_id=SUMMARY_LANE_ID,
        summary_combat=summary,
        operator_handle=handle,
    )


def validate_table2_registry(table: ScenarioOverlayTable) -> None:
    registry = _registry_by_id(table.column_registry)
    missing_required = sorted(TABLE2_REQUIRED_COLUMN_IDS - frozenset(registry))
    if missing_required:
        raise ValueError(f"Table 2 registry missing required columns: {missing_required!r}")
    _validate_registry_contracts(registry, TABLE2_KEY_CONTRACTS, "Table 2")
    registry_ids = frozenset(registry)
    for row in table.rows:
        missing = [column_id for column_id in registry_ids if not hasattr(row, column_id)]
        if missing:
            raise ValueError(f"Table 2 row missing registered columns: {missing!r}")
        _validate_table2_row_contract(row)


def _derive_wall_hp(
    contributors: SurvivabilityContributorBundle,
    transforms: ScenarioSurvivabilityTransforms,
    perk_contributions: Mapping[str, float],
) -> float:
    _validate_survivability_contributors(contributors)
    flat, multiplier = _perk_contribution_pair(perk_contributions, flat_effect_id="wall_hp_flat", multiplier_effect_id="wall_hp_multiplier")
    base = sum(contributors.wall_hp_primitives.values()) + flat
    return base * max(0.0, float(contributors.wall_hp_multiplier)) * multiplier * max(0.0, float(transforms.wall_hp_multiplier))


def _derive_wall_regen(
    contributors: SurvivabilityContributorBundle,
    transforms: ScenarioSurvivabilityTransforms,
    perk_contributions: Mapping[str, float],
) -> float:
    _validate_survivability_contributors(contributors)
    flat, multiplier = _perk_contribution_pair(perk_contributions, flat_effect_id="wall_regen_flat", multiplier_effect_id="wall_regen_multiplier")
    base = sum(contributors.wall_regen_primitives.values()) + flat
    return base * max(0.0, float(contributors.wall_regen_multiplier)) * multiplier * max(0.0, float(transforms.wall_regen_multiplier))


def _derive_lane_damage_reduction(
    contributors: SurvivabilityContributorBundle,
    transforms: ScenarioSurvivabilityTransforms,
    perk_contributions: Mapping[str, float],
) -> dict[str, float]:
    defense = _bounded_percent(contributors.tower_defense_pct) / 100.0
    black_hole_dr = _timed_dr_fraction(
        damage_reduction_pct=contributors.black_hole_damage_reduction_pct,
        duration_seconds=contributors.black_hole_duration_seconds + _perk_contribution_sum(perk_contributions, "black_hole_duration_seconds_add"),
        cooldown_seconds=contributors.black_hole_cooldown_seconds,
    )
    chrono_field_dr = _timed_dr_fraction(
        damage_reduction_pct=contributors.chrono_field_damage_reduction_pct,
        duration_seconds=contributors.chrono_field_duration_seconds + _perk_contribution_sum(perk_contributions, "chrono_field_duration_seconds_add"),
        cooldown_seconds=contributors.chrono_field_cooldown_seconds,
    )
    out: dict[str, float] = {}
    for lane_id in LANE_ORDER:
        timed = _bounded_fraction(contributors.timed_dr_by_lane.get(lane_id, 0.0))
        scenario_bonus = _bounded_fraction(transforms.dr_bonus_by_lane.get(lane_id, 0.0))
        out[lane_id] = _bounded_fraction(
            1.0
            - (
                (1.0 - defense)
                * (1.0 - timed)
                * (1.0 - black_hole_dr)
                * (1.0 - chrono_field_dr)
                * (1.0 - scenario_bonus)
            )
        )
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


def _active_perk_state(row: CommonTrajectoryRow, scenario: ScenarioOverlayInputs) -> tuple[dict[str, int], dict[str, float]]:
    counts = {str(k): int(v) for k, v in row.compiled_perk_state.counts.items()}
    contributions = {str(k): float(v) for k, v in row.compiled_perk_state.contributions.items()}
    _validate_perk_contributions(contributions)
    if scenario.tournament_perks_enabled:
        return counts, contributions
    removed = set(str(perk_id) for perk_id in scenario.removed_perk_ids)
    if not removed:
        raise KernelAmbiguityError("tournament perk removal requested without removed_perk_ids")
    missing = sorted(perk_id for perk_id in removed if perk_id not in counts)
    if missing:
        raise KernelAmbiguityError(f"tournament perk removal references unknown compiled perk ids: {missing!r}")
    active_counts = {perk_id: count for perk_id, count in counts.items() if perk_id not in removed}
    active_contributions = {
        contribution_id: value
        for contribution_id, value in contributions.items()
        if _perk_contribution_owner(contribution_id) not in removed
    }
    return active_counts, active_contributions


def _perk_contribution_pair(
    contributions: Mapping[str, float],
    *,
    flat_effect_id: str,
    multiplier_effect_id: str,
) -> tuple[float, float]:
    _validate_perk_contributions(contributions)
    flat = 0.0
    multiplier = 1.0
    for contribution_id, value in contributions.items():
        effect_id = _perk_contribution_effect_id(contribution_id)
        if effect_id == flat_effect_id:
            flat += float(value)
        elif effect_id == multiplier_effect_id:
            multiplier *= max(0.0, float(value))
    return flat, multiplier


def _perk_contribution_sum(contributions: Mapping[str, float], effect_id: str) -> float:
    _validate_perk_contributions(contributions)
    total = 0.0
    for contribution_id, value in contributions.items():
        if _perk_contribution_effect_id(contribution_id) == effect_id:
            total += float(value)
    return total


def _validate_perk_contributions(contributions: Mapping[str, float]) -> None:
    for contribution_id, value in contributions.items():
        effect_id = _perk_contribution_effect_id(contribution_id)
        if effect_id not in PERK_CONTRIBUTION_EFFECT_IDS:
            raise KernelAmbiguityError(f"unsupported perk contribution effect {effect_id!r}")
        if effect_id.endswith("_multiplier") and float(value) < 0.0:
            raise KernelAmbiguityError(f"perk contribution {contribution_id!r} multiplier cannot be negative")


def _perk_contribution_owner(contribution_id: str) -> str | None:
    return str(contribution_id).split(":", 1)[0] if ":" in str(contribution_id) else None


def _perk_contribution_effect_id(contribution_id: str) -> str:
    return str(contribution_id).split(":", 1)[1] if ":" in str(contribution_id) else str(contribution_id)


def _summary_lane(lanes: tuple[CombatLaneEvaluation, ...]) -> CombatLaneEvaluation:
    for lane in lanes:
        if lane.lane_id == SUMMARY_LANE_ID:
            return lane
    raise KernelAmbiguityError(f"summary lane {SUMMARY_LANE_ID!r} was not evaluated")


def _evaluate_boss_ttd_lane(
    *,
    lane_id: str,
    enemy_attack: float,
    pre_fort_wall_hp: float,
    wall_regen: float,
    wall_fortification_multiplier: float,
    damage_reduction_fraction: float,
    incoming_damage_multiplier: float,
    ttk_seconds: float | None,
    contact_thorns_kill_seconds: float | None,
    boss_hits_to_player: int,
    combat: CombatInputs,
) -> CombatLaneEvaluation:
    if ttk_seconds is None:
        raise KernelAmbiguityError("boss TTD requires finite boss_ttk_seconds")
    ttd_window_seconds = float(ttk_seconds)
    wall_hp = pre_fort_wall_hp * max(0.0, float(wall_fortification_multiplier))
    wall_regen_gained = max(0.0, wall_regen * ttd_window_seconds)
    hits = _bounded_whole_hit_count(boss_hits_to_player, "boss_hits_to_player")
    total_damage = 0.0
    for hit_index in range(hits):
        heat_multiplier = 1.0 + BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT * hit_index
        total_damage += float(enemy_attack) * incoming_damage_multiplier * heat_multiplier * max(0.0, 1.0 - damage_reduction_fraction)
    margin = wall_hp + wall_regen_gained - total_damage
    return CombatLaneEvaluation(lane_id, margin >= 0.0, None if margin >= 0.0 else "boss_wall_damage_exceeds_hp", ttk_seconds, contact_thorns_kill_seconds, hits, total_damage, margin, wall_hp, wall_regen_gained, damage_reduction_fraction)


def _simulate_boss_ttk(*, enemy_health: float, combat: CombatInputs) -> float:
    return _simulate_boss_combat_timeline(enemy_health=enemy_health, combat=combat).ttk_seconds


def _simulate_boss_combat_timeline(*, enemy_health: float, combat: CombatInputs) -> BossCombatTimeline:
    pre_contact_kill = _simulate_boss_pre_contact_kill_state(enemy_health=enemy_health, combat=combat)
    if pre_contact_kill.ttk_seconds is not None:
        return BossCombatTimeline(
            ttk_seconds=_finite_ttk_seconds(pre_contact_kill.ttk_seconds, "pre_contact_ttk_seconds"),
            damage_breakdown=pre_contact_kill.damage_breakdown,
            wall_thorns_kill_seconds=None,
            boss_hits_to_player=0,
        )
    contact_thorns_result = _simulate_boss_contact_thorns_result(
        remaining_hp=pre_contact_kill.remaining_hp,
        starting_hp=pre_contact_kill.starting_hp,
        kill_threshold=pre_contact_kill.kill_threshold,
        combat=combat,
    )
    ttk_seconds = _boss_total_ttk_seconds(
        pre_contact_ttk_seconds=pre_contact_kill.ttk_seconds,
        contact_thorns_kill_seconds=contact_thorns_result.kill_seconds,
        combat=combat,
    )
    return BossCombatTimeline(
        ttk_seconds=ttk_seconds,
        damage_breakdown=BossDamageBreakdown(
            plasma_cannon_damage=pre_contact_kill.damage_breakdown.plasma_cannon_damage,
            orb_damage=pre_contact_kill.damage_breakdown.orb_damage,
            electron_damage=pre_contact_kill.damage_breakdown.electron_damage,
            thorns_damage=contact_thorns_result.thorns_damage,
            plasma_cannon_damage_pct=pre_contact_kill.damage_breakdown.plasma_cannon_damage_pct,
            orb_damage_pct=pre_contact_kill.damage_breakdown.orb_damage_pct,
            electron_damage_pct=pre_contact_kill.damage_breakdown.electron_damage_pct,
            thorns_damage_pct=contact_thorns_result.thorns_damage_pct,
            thorns_expected_damage_pct_from_hits=contact_thorns_result.thorns_expected_damage_pct_from_hits,
            thorns_hits=contact_thorns_result.thorns_hits,
        ),
        wall_thorns_kill_seconds=contact_thorns_result.kill_seconds,
        boss_hits_to_player=contact_thorns_result.thorns_hits,
    )


def _finite_ttk_seconds(value: float, field_name: str) -> float:
    seconds = float(value)
    if not isfinite(seconds) or seconds < 0.0:
        raise KernelAmbiguityError(f"{field_name} must be finite and non-negative")
    return seconds


def _pre_contact_event_seconds(combat: CombatInputs) -> float:
    if combat.boss_time_to_contact_seconds is None:
        raise KernelAmbiguityError("boss_time_to_contact_seconds is required to time orb/electron pre-contact kills")
    seconds = float(combat.boss_time_to_contact_seconds)
    if not isfinite(seconds) or seconds < 0.0:
        raise KernelAmbiguityError("boss_time_to_contact_seconds must be finite and non-negative")
    return seconds


def _simulate_boss_pre_contact_kill_state(*, enemy_health: float, combat: CombatInputs) -> BossPreContactKillState:
    if combat.orb_boss_total_damage_pct is None and (combat.orb_boss_hit_pct is None or combat.orb_boss_hit_count is None):
        raise KernelAmbiguityError("total orb boss damage or explicit total orb hit count is required for boss TTK")
    if combat.electron_total_damage_pct is None and combat.electron_hit_count is None:
        raise KernelAmbiguityError("total electron boss damage or explicit total electron hit count is required for boss TTK")
    starting_hp = float(enemy_health)
    if not isfinite(starting_hp) or starting_hp < 0.0:
        raise KernelAmbiguityError("enemy_health must be finite and non-negative")
    kill_threshold = starting_hp * KILL_HP_THRESHOLD_FRACTION
    pc_pct = _bounded_percent(combat.plasma_cannon_effect_pct) / 100.0
    pc_pct *= max(0.0, float(combat.plasma_cannon_resistance_multiplier))
    plasma_cannon_damage = 0.0
    orb_damage = 0.0
    electron_damage = 0.0
    plasma_cannon_damage_pct = pc_pct * 100.0
    orb_damage_pct = 0.0
    electron_damage_pct = 0.0
    before = remaining_hp = starting_hp
    remaining_hp = starting_hp * max(0.0, 1.0 - pc_pct)
    plasma_cannon_damage += max(0.0, before - remaining_hp)
    if remaining_hp <= kill_threshold:
        return BossPreContactKillState(
            0.0,
            remaining_hp,
            starting_hp,
            kill_threshold,
            BossDamageBreakdown(
                plasma_cannon_damage=plasma_cannon_damage,
                plasma_cannon_damage_pct=plasma_cannon_damage_pct,
            ),
            0.0,
        )
    if combat.orb_boss_total_damage_pct is not None:
        orb_pct = (_bounded_percent(float(combat.orb_boss_total_damage_pct)) / 100.0) * max(0.0, float(combat.orb_resistance_multiplier))
        orb_damage_pct = orb_pct * 100.0
        before = remaining_hp
        remaining_hp *= max(0.0, 1.0 - orb_pct)
        orb_damage += max(0.0, before - remaining_hp)
    else:
        orb_pct = (_bounded_percent(float(combat.orb_boss_hit_pct)) / 100.0) * max(0.0, float(combat.orb_resistance_multiplier))
        orb_hits = _bounded_whole_hit_count(combat.orb_boss_hit_count, "orb_boss_hit_count")
        orb_damage_pct = (1.0 - (max(0.0, 1.0 - orb_pct) ** orb_hits)) * 100.0
        for _ in range(orb_hits):
            before = remaining_hp
            remaining_hp *= max(0.0, 1.0 - orb_pct)
            orb_damage += max(0.0, before - remaining_hp)
    if remaining_hp <= kill_threshold:
        event_seconds = _pre_contact_event_seconds(combat)
        return BossPreContactKillState(
            event_seconds,
            remaining_hp,
            starting_hp,
            kill_threshold,
            BossDamageBreakdown(
                plasma_cannon_damage=plasma_cannon_damage,
                orb_damage=orb_damage,
                plasma_cannon_damage_pct=plasma_cannon_damage_pct,
                orb_damage_pct=orb_damage_pct,
            ),
            event_seconds,
        )
    if combat.electron_total_damage_pct is not None:
        electron_pct = _bounded_percent(float(combat.electron_total_damage_pct)) / 100.0
        electron_damage_pct = electron_pct * 100.0
        before = remaining_hp
        remaining_hp *= max(0.0, 1.0 - electron_pct)
        electron_damage += max(0.0, before - remaining_hp)
    else:
        electron_pct = ELECTRON_BOSS_REMAINING_HP_PCT
        electron_hits = _bounded_whole_hit_count(combat.electron_hit_count, "electron_hit_count")
        electron_damage_pct = (1.0 - (max(0.0, 1.0 - electron_pct) ** electron_hits)) * 100.0
        for _ in range(electron_hits):
            before = remaining_hp
            remaining_hp *= max(0.0, 1.0 - electron_pct)
            electron_damage += max(0.0, before - remaining_hp)
    if remaining_hp <= kill_threshold:
        event_seconds = _pre_contact_event_seconds(combat)
        return BossPreContactKillState(
            event_seconds,
            remaining_hp,
            starting_hp,
            kill_threshold,
            BossDamageBreakdown(
                plasma_cannon_damage=plasma_cannon_damage,
                orb_damage=orb_damage,
                electron_damage=electron_damage,
                plasma_cannon_damage_pct=plasma_cannon_damage_pct,
                orb_damage_pct=orb_damage_pct,
                electron_damage_pct=electron_damage_pct,
            ),
            event_seconds,
        )
    pre_contact_event_seconds = None
    if (orb_damage > 0.0 or electron_damage > 0.0) and combat.boss_time_to_contact_seconds is not None:
        pre_contact_event_seconds = _pre_contact_event_seconds(combat)
    return BossPreContactKillState(
        None,
        remaining_hp,
        starting_hp,
        kill_threshold,
        BossDamageBreakdown(
            plasma_cannon_damage=plasma_cannon_damage,
            orb_damage=orb_damage,
            electron_damage=electron_damage,
            plasma_cannon_damage_pct=plasma_cannon_damage_pct,
            orb_damage_pct=orb_damage_pct,
            electron_damage_pct=electron_damage_pct,
        ),
        pre_contact_event_seconds,
    )


def _simulate_boss_contact_thorns_kill_seconds(
    *,
    remaining_hp: float,
    starting_hp: float,
    kill_threshold: float,
    combat: CombatInputs,
) -> float | None:
    return _simulate_boss_contact_thorns_result(
        remaining_hp=remaining_hp,
        starting_hp=starting_hp,
        kill_threshold=kill_threshold,
        combat=combat,
    ).kill_seconds


def _simulate_boss_contact_thorns_result(
    *,
    remaining_hp: float,
    starting_hp: float,
    kill_threshold: float,
    combat: CombatInputs,
) -> BossContactThornsResult:
    if remaining_hp <= kill_threshold:
        return BossContactThornsResult(None, 0.0, 0.0, 0.0, 0)
    next_contact = inf if combat.boss_time_to_contact_seconds is None else float(combat.boss_time_to_contact_seconds)
    thorns_pct = max(0.0, float(combat.tower_thorns_damage_pct) / 100.0) * THORNS_BOSS_EFFECTIVENESS * max(0.0, float(combat.thorns_resistance_multiplier))
    thorns_increase_per_hit = max(0.0, float(combat.wall_thorns_damage_increase_per_hit))
    contact_hit_index = 0
    thorns_damage = 0.0
    thorns_expected_damage_pct_from_hits = 0.0
    thorns_hits = 0
    max_ttk = float(combat.max_ttk_seconds)
    while remaining_hp > kill_threshold:
        t = next_contact
        if not isfinite(t) or t > max_ttk:
            if thorns_pct <= 0.0:
                thorns_damage_pct = 0.0 if starting_hp <= 0.0 else (thorns_damage / starting_hp) * 100.0
                return BossContactThornsResult(None, thorns_damage, thorns_damage_pct, thorns_expected_damage_pct_from_hits, thorns_hits)
            raise KernelAmbiguityError("boss contact thorns resolution exceeded event horizon without kill")
        if abs(next_contact - t) <= 1e-12:
            before = remaining_hp
            thorns_fraction = thorns_pct + (thorns_increase_per_hit * contact_hit_index)
            raw_thorns_damage = starting_hp * max(0.0, thorns_fraction)
            applied_thorns_damage = min(before, raw_thorns_damage)
            thorns_expected_damage_pct_from_hits += 0.0 if starting_hp <= 0.0 else (applied_thorns_damage / starting_hp) * 100.0
            remaining_hp = max(0.0, remaining_hp - applied_thorns_damage)
            thorns_damage += applied_thorns_damage
            contact_hit_index += 1
            thorns_hits += 1
            if combat.boss_hit_interval_seconds <= 0:
                raise KernelAmbiguityError("boss_hit_interval_seconds must be positive")
            next_contact += float(combat.boss_hit_interval_seconds)
    thorns_damage_pct = 0.0 if starting_hp <= 0.0 else (thorns_damage / starting_hp) * 100.0
    return BossContactThornsResult(float(t), thorns_damage, thorns_damage_pct, thorns_expected_damage_pct_from_hits, thorns_hits)


def _boss_total_ttk_seconds(
    *,
    pre_contact_ttk_seconds: float | None,
    contact_thorns_kill_seconds: float | None,
    combat: CombatInputs,
) -> float:
    candidates = [
        float(value)
        for value in (pre_contact_ttk_seconds, contact_thorns_kill_seconds)
        if value is not None and isfinite(float(value))
    ]
    if candidates:
        return max(0.0, min(candidates))
    if combat.boss_time_to_contact_seconds is None:
        raise KernelAmbiguityError("boss cannot be killed by pre-contact events and contact timing is unavailable")
    raise KernelAmbiguityError("boss cannot be killed by pre-contact TTK events or contact thorns within the modeled horizon")


def _timed_dr_fraction(*, damage_reduction_pct: float, duration_seconds: float, cooldown_seconds: float) -> float:
    dr = _bounded_percent(damage_reduction_pct) / 100.0
    duration = max(0.0, float(duration_seconds))
    cooldown = max(0.0, float(cooldown_seconds))
    if dr <= 0.0 or duration <= 0.0 or cooldown <= 0.0:
        return 0.0
    return _bounded_fraction(dr * min(1.0, duration / cooldown))


def _validate_survivability_contributors(contributors: SurvivabilityContributorBundle) -> None:
    if contributors.source_policy != "explicit_staged_contributors_v1":
        raise KernelAmbiguityError("survivability contributors source_policy must be explicit_staged_contributors_v1")
    for name in (
        "base_wall_hp", "workshop_wall_hp", "lab_wall_hp", "enhancement_wall_hp", "module_flat_wall_hp", "wall_hp_multiplier",
        "base_wall_regen", "workshop_wall_regen", "lab_wall_regen", "enhancement_wall_regen", "module_flat_wall_regen", "wall_regen_multiplier",
        "wall_fortification_multiplier", "black_hole_damage_reduction_pct", "black_hole_duration_seconds", "black_hole_cooldown_seconds",
        "chrono_field_damage_reduction_pct", "chrono_field_duration_seconds", "chrono_field_cooldown_seconds",
    ):
        if float(getattr(contributors, name)) < 0.0:
            raise KernelAmbiguityError(f"survivability contributor {name} cannot be negative")


def _registry_by_id(registry: tuple[ColumnFormulaSpec, ...]) -> dict[str, ColumnFormulaSpec]:
    out: dict[str, ColumnFormulaSpec] = {}
    for spec in registry:
        if spec.column_id in out:
            raise ValueError(f"duplicate registry column {spec.column_id!r}")
        for field_name in ("column_id", "owner_layer", "dtype", "recurrence_type", "evaluation_policy", "cache_policy"):
            if not str(getattr(spec, field_name)):
                raise ValueError(f"registry column {spec.column_id!r} has empty {field_name}")
        out[spec.column_id] = spec
    return out


def _validate_registry_contracts(
    registry: Mapping[str, ColumnFormulaSpec],
    contracts: Mapping[str, tuple[tuple[str, ...], str]],
    label: str,
) -> None:
    for column_id, (dependencies, recurrence_type) in contracts.items():
        spec = registry.get(column_id)
        if spec is None:
            raise ValueError(f"{label} registry missing key contract column {column_id!r}")
        if tuple(spec.dependencies) != tuple(dependencies):
            raise ValueError(f"{label} registry column {column_id!r} dependencies changed from {dependencies!r}")
        if spec.recurrence_type != recurrence_type:
            raise ValueError(f"{label} registry column {column_id!r} recurrence_type must be {recurrence_type!r}")


def _validate_table2_row_contract(row: ScenarioOverlayRow) -> None:
    if not isinstance(row.row_key, str) or not row.row_key:
        raise ValueError("Table 2 row_key must be a non-empty string")
    if not isinstance(row.final_wall_hp, (int, float)) or float(row.final_wall_hp) < 0.0:
        raise ValueError("Table 2 final_wall_hp must be non-negative")
    if not isinstance(row.final_wall_regen, (int, float)) or float(row.final_wall_regen) < 0.0:
        raise ValueError("Table 2 final_wall_regen must be non-negative")
    if tuple(lane.lane_id for lane in row.lane_evaluations) != LANE_ORDER:
        raise ValueError("Table 2 lane_evaluations must follow canonical lane order")
    if row.summary_lane_id != SUMMARY_LANE_ID or row.summary_combat.lane_id != SUMMARY_LANE_ID:
        raise ValueError("Table 2 summary lane must use explicit avg policy")
    _validate_perk_contributions(row.active_perk_contributions)


def _validate_combat(combat: CombatInputs) -> None:
    if float(combat.max_ttk_seconds) <= 0.0:
        raise KernelAmbiguityError("max_ttk_seconds must be positive")
    if not isfinite(float(combat.wall_thorns_damage_increase_per_hit)) or float(combat.wall_thorns_damage_increase_per_hit) < 0.0:
        raise KernelAmbiguityError("wall_thorns_damage_increase_per_hit must be finite and non-negative")


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
    target = int(wave)
    if target in table and column in table[target]:
        return table[target][column]
    ordered = sorted(table)
    lower_keys = [key for key in ordered if key <= target]
    upper_keys = [key for key in ordered if key >= target]
    if not lower_keys:
        raise KernelAmbiguityError(f"no enemy table row for wave {wave}")
    lower = max(lower_keys)
    upper = min(upper_keys) if upper_keys else lower
    lower_value = table[lower].get(column)
    upper_value = table[upper].get(column)
    if lower_value is None or upper_value is None:
        raise KernelAmbiguityError(f"enemy table column {column!r} is missing")
    if lower == upper:
        return lower_value
    fraction = (target - lower) / float(upper - lower)
    return lower_value + (upper_value - lower_value) * fraction


def _bounded_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bounded_percent(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _bounded_whole_hit_count(value: float | None, field_name: str) -> int:
    if value is None:
        raise KernelAmbiguityError(f"{field_name} is required")
    count = float(value)
    if not isfinite(count) or count < 0.0:
        raise KernelAmbiguityError(f"{field_name} must be finite and non-negative")
    rounded = int(count)
    if abs(count - rounded) > 1e-9:
        raise KernelAmbiguityError(f"{field_name} must be a whole-event count")
    return rounded
