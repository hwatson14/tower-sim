from __future__ import annotations

import hashlib
import csv
import json
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from functools import lru_cache
from math import floor, isfinite
from pathlib import Path
from typing import Any, Mapping


CATEGORY_IDS: tuple[str, str, str] = ("attack", "defense", "utility")
RUN_PLAN_VERSION = "boss_waves.run_plan.v1"
ROOT = Path(__file__).resolve().parents[1]
WORKSHOP_VALUES_PATH = ROOT / "kb" / "workshop" / "tables" / "workshop-values.csv"
DEFAULT_WORKSHOP_CATEGORY_BY_TRACK: Mapping[str, str] = {
    "Damage": "attack",
    "Attack Speed": "attack",
    "Critical Chance": "attack",
    "Critical Factor": "attack",
    "Range": "attack",
    "Damage / Meter": "attack",
    "Super Crit Chance": "attack",
    "Super Crit Multi": "attack",
    "Rend Armor Chance": "attack",
    "Rend Armor Mult": "attack",
    "Health": "defense",
    "Health Regen": "defense",
    "Defense %": "defense",
    "Defense Absolute": "defense",
    "Thorn Damage": "defense",
    "Lifesteal": "defense",
    "Knockback Chance": "defense",
    "Knockback Force": "defense",
    "Orb Speed": "defense",
    "Orbs": "defense",
    "Shockwave Size": "defense",
    "Shockwave Frequency": "defense",
    "Land Mine Chance": "defense",
    "Land Mine Damage": "defense",
    "Land Mine Radius": "defense",
    "Death Defy": "defense",
    "Wall Health": "defense",
    "Wall Rebuild": "defense",
    "Wall Regen": "defense",
    "Wall Thorns": "defense",
    "Wall Invincibility": "defense",
    "Wall Fortification": "defense",
    "Cash Bonus": "utility",
    "Cash / Wave": "utility",
    "Coins / Kill Bonus": "utility",
    "Coins / Wave": "utility",
    "Free Attack Upgrade": "utility",
    "Free Defense Upgrade": "utility",
    "Free Utility Upgrade": "utility",
    "Interest / Wave": "utility",
    "Recovery Amount": "utility",
    "Max Recovery": "utility",
    "Package Chance": "utility",
    "Enemy Level Skip": "utility",
    "Enemy Attack Level Skip": "utility",
    "Enemy Health Level Skip": "utility",
}
PERK_CONTRIBUTION_EFFECT_IDS: frozenset[str] = frozenset(
    {
        "wall_hp_flat",
        "wall_hp_multiplier",
        "wall_regen_flat",
        "wall_regen_multiplier",
        "tower_defense_pct_points_add",
        "tower_defense_absolute_multiplier",
        "black_hole_duration_seconds_add",
        "chrono_field_duration_seconds_add",
    }
)

@dataclass(frozen=True)
class ColumnFormulaSpec:
    column_id: str
    owner_layer: str
    dtype: str
    dependencies: tuple[str, ...]
    recurrence_type: str
    evaluation_policy: str
    cache_policy: str


TABLE1_COLUMN_REGISTRY: tuple[ColumnFormulaSpec, ...] = (
    ColumnFormulaSpec("row_key", "qe", "str", (), "identity", "compile_once", "plan_static"),
    ColumnFormulaSpec("display_wave", "qe", "int", ("checkpoint_policy",), "checkpoint_grid", "compile_once", "plan_static"),
    ColumnFormulaSpec("wave_progression", "qe", "WaveProgressionRecurrence", ("recurrence_policy",), "stateful_recurrence", "per_checkpoint", "carry_forward"),
    ColumnFormulaSpec("free_upgrade_state", "qe", "FreeUpgradeRecurrence", ("recurrence_policy",), "stateful_recurrence", "per_checkpoint", "carry_forward"),
    ColumnFormulaSpec("workshop_levels", "qe", "mapping[str,int]", ("free_upgrade_state",), "allocation_recurrence", "per_checkpoint", "carry_forward"),
    ColumnFormulaSpec("compiled_perk_state", "qe", "CompiledPerkState", ("perk_policy",), "checkpoint_lookup", "per_checkpoint", "plan_static"),
    ColumnFormulaSpec("survivability_contributors", "qe", "SurvivabilityContributorBundle", ("survivability_policy", "workshop_levels"), "row_rederived_contributor_bundle", "per_checkpoint", "row_static"),
    ColumnFormulaSpec("death_wave_health_multiplier", "qe", "float", ("display_wave", "death_wave_policy"), "linear_recurrence", "per_checkpoint", "row_static"),
)
TABLE1_REQUIRED_COLUMN_IDS: frozenset[str] = frozenset(spec.column_id for spec in TABLE1_COLUMN_REGISTRY)
TABLE1_KEY_CONTRACTS: Mapping[str, tuple[tuple[str, ...], str]] = {
    "wave_progression": (("recurrence_policy",), "stateful_recurrence"),
    "free_upgrade_state": (("recurrence_policy",), "stateful_recurrence"),
    "compiled_perk_state": (("perk_policy",), "checkpoint_lookup"),
    "survivability_contributors": (("survivability_policy", "workshop_levels"), "row_rederived_contributor_bundle"),
    "death_wave_health_multiplier": (("display_wave", "death_wave_policy"), "linear_recurrence"),
}


@dataclass(frozen=True)
class RunScopeConfig:
    start_wave: int
    end_wave: int
    tier_column: str = "Tier 14"


@dataclass(frozen=True)
class CheckpointPolicyConfig:
    boss_interval_waves: int = 10
    checkpoint_every_bosses: int = 1


@dataclass(frozen=True)
class RecurrencePolicyConfig:
    attack_skip_chance: float = 0.0
    health_skip_chance: float = 0.0
    attack_skip_chance_delta: float = 0.0
    health_skip_chance_delta: float = 0.0
    enemy_skip_decay_start_wave: int = 0
    enemy_skip_decay_fraction_per_step: float = 0.0
    enemy_skip_decay_interval_waves: int = 0
    enemy_skip_decay_schedule: Mapping[int, float] = field(default_factory=dict)
    attack_skip_static_percent_points: float = 0.0
    attack_skip_multiplier: float = 1.0
    attack_skip_workshop_track: str = ""
    attack_skip_workshop_baseline_level: int = 0
    health_skip_static_percent_points: float = 0.0
    health_skip_multiplier: float = 1.0
    health_skip_workshop_track: str = ""
    health_skip_workshop_baseline_level: int = 0
    free_upgrade_chance_by_category: Mapping[str, float] = field(default_factory=dict)
    category_track_order: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    track_max_levels: Mapping[str, int] = field(default_factory=dict)
    workshop_levels: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PerkPolicyConfig:
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
    perk_counts_by_wave: Mapping[int, Mapping[str, int]] = field(default_factory=dict)
    perk_contributions_by_wave: Mapping[int, Mapping[str, float]] = field(default_factory=dict)
    perk_source: str = "explicit_staged_perk_policy"


@dataclass(frozen=True)
class DependencyPolicyConfig:
    dependency_order: tuple[str, ...] = (
        "checkpoint_grid",
        "wave_progression",
        "free_upgrade_generation",
        "free_upgrade_allocation",
        "workshop_levels",
        "compiled_perk_state",
        "survivability_contributors",
    )


def derive_wall_regen_hp_per_second(
    *,
    tower_regen_hp_per_second: float,
    wall_regen_percent_points: float,
) -> float:
    tower_regen = float(tower_regen_hp_per_second)
    wall_regen_pct = float(wall_regen_percent_points)
    if not isfinite(tower_regen) or tower_regen < 0.0:
        raise ValueError("tower_regen_hp_per_second must be a finite non-negative value")
    if not isfinite(wall_regen_pct) or wall_regen_pct < 0.0:
        raise ValueError("wall_regen_percent_points must be a finite non-negative value")
    return tower_regen * (wall_regen_pct / 100.0)


def derive_wall_thorns_contact_damage_pct(
    *,
    tower_thorns_damage_pct: float,
    wall_thorns_level: int,
) -> float:
    tower_thorns = float(tower_thorns_damage_pct)
    wall_level = int(wall_thorns_level)
    if not isfinite(tower_thorns) or tower_thorns < 0.0:
        raise ValueError("tower_thorns_damage_pct must be finite and non-negative")
    if wall_level < 0:
        raise ValueError("wall_thorns_level cannot be negative")
    return tower_thorns * (wall_level / 100.0)


def derive_chrono_field_damage_reduction_pct(*, reduction_lab_level: int, damage_reduction_unlocked: bool = True) -> float:
    """KB canonical Chrono Field DR lab formula: 10.5% at level 1, +0.5% per level, max 25%."""
    level = int(reduction_lab_level)
    if level <= 0 or not bool(damage_reduction_unlocked):
        return 0.0
    if level > 30:
        raise ValueError("Chrono Field Reduction % lab level cannot exceed 30")
    return 10.5 + ((level - 1) * 0.5)


@lru_cache(maxsize=1)
def _workshop_value_table() -> dict[tuple[str, int], float]:
    if not WORKSHOP_VALUES_PATH.exists():
        return {}
    out: dict[tuple[str, int], float] = {}
    with WORKSHOP_VALUES_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return out
        pairs: list[tuple[int, int, str]] = []
        for index in range(0, max(0, len(header) - 1), 2):
            level_name = str(header[index] or "").strip()
            value_name = str(header[index + 1] or "").strip()
            if level_name == "Level" and value_name:
                pairs.append((index, index + 1, value_name))
        for raw in reader:
            for level_index, value_index, track_name in pairs:
                if level_index >= len(raw) or value_index >= len(raw):
                    continue
                try:
                    level = int(float(str(raw[level_index]).strip()))
                    value = float(str(raw[value_index]).strip())
                except (TypeError, ValueError):
                    continue
                out[(track_name, level)] = value
    return out


def workshop_value_for_level(track_name: str, level: int) -> float:
    try:
        from qe.kb_surfaces import WORKSHOP_FORMULA_VALUES

        formula = WORKSHOP_FORMULA_VALUES.get(str(track_name))
        if formula is not None:
            return float(formula(int(level)))
    except Exception:
        pass
    values = _workshop_value_table()
    key = (str(track_name), int(level))
    if key not in values:
        raise ValueError(f"missing workshop value for {track_name!r} level {int(level)}")
    return float(values[key])


def derive_wall_hp_from_qe_primitives(
    *,
    tower_hp: float,
    wall_hp_contributors: tuple[Mapping[str, Any], ...],
) -> Mapping[str, float]:
    resolved_tower_hp = float(tower_hp)
    if not isfinite(resolved_tower_hp) or resolved_tower_hp < 0.0:
        raise ValueError("tower_hp must be a finite non-negative value")
    ratio_percent_points = 0.0
    multiplier = 1.0
    saw_ratio = False
    for contributor in wall_hp_contributors:
        if not bool(contributor.get("active", True)):
            continue
        value = float(contributor.get("value") or 0.0)
        if not isfinite(value):
            raise ValueError("wall HP contributor values must be finite")
        contributor_id = str(contributor.get("contributor_id") or "")
        stage = str(contributor.get("composition_stage") or "")
        input_value_type = str(contributor.get("input_value_type") or "")
        if contributor_id == "lab__wall__fortification__multiplier":
            continue
        if "wall_health_regen_mult" in contributor_id or (
            "wall_health__pct" in contributor_id and "@@unique" in contributor_id
        ):
            multiplier *= value
            continue
        if stage == "additive_pre_cap":
            ratio_percent_points += value
            saw_ratio = True
            continue
        if stage == "multiplicative":
            multiplier *= value
            continue
        if input_value_type in {"percent_display", "resolved_value"}:
            ratio_percent_points += value
            saw_ratio = True
            continue
        raise ValueError(f"unsupported wall HP contributor semantics for {contributor_id!r}")
    if not saw_ratio:
        raise ValueError("wall HP derivation requires at least one ratio contributor")
    ratio = ratio_percent_points / 100.0
    return {
        "wall_hp_pre_fort": resolved_tower_hp * ratio * multiplier,
        "wall_hp_ratio": ratio,
        "wall_hp_percent_points": ratio_percent_points,
        "wall_hp_multiplier": multiplier,
        "wall_hp_per_workshop_level_pre_fort": resolved_tower_hp * 0.001 * multiplier,
    }


@dataclass(frozen=True)
class SurvivabilityContributorBundle:
    base_wall_hp: float
    workshop_wall_hp: float = 0.0
    lab_wall_hp: float = 0.0
    enhancement_wall_hp: float = 0.0
    module_flat_wall_hp: float = 0.0
    wall_hp_multiplier: float = 1.0
    base_wall_regen: float = 0.0
    workshop_wall_regen: float = 0.0
    lab_wall_regen: float = 0.0
    enhancement_wall_regen: float = 0.0
    module_flat_wall_regen: float = 0.0
    wall_regen_multiplier: float = 1.0
    wall_fortification_multiplier: float = 1.0
    tower_defense_pct: float = 0.0
    tower_defense_absolute: float = 0.0
    timed_dr_by_lane: Mapping[str, float] = field(default_factory=dict)
    black_hole_damage_reduction_pct: float = 0.0
    black_hole_duration_seconds: float = 0.0
    black_hole_cooldown_seconds: float = 0.0
    black_hole_explicit_uptime_fraction: float | None = None
    chrono_field_damage_reduction_pct: float = 0.0
    chrono_field_duration_seconds: float = 0.0
    chrono_field_cooldown_seconds: float = 0.0
    wall_hp_workshop_track: str | None = None
    wall_hp_workshop_baseline_level: int | None = None
    wall_hp_workshop_value_per_level: float = 0.0
    wall_hp_static_ratio_percent_points: float = 0.0
    wall_hp_effect_multiplier: float = 1.0
    tower_hp_workshop_track: str | None = None
    tower_hp_workshop_baseline_level: int | None = None
    tower_hp_workshop_multiplier: float = 1.0
    wall_regen_workshop_track: str | None = None
    wall_regen_workshop_baseline_level: int | None = None
    wall_regen_workshop_value_per_level: float = 0.0
    source_policy: str = "explicit_staged_contributors_v1"

    @property
    def wall_hp_primitives(self) -> Mapping[str, float]:
        return {
            "base_wall_hp": float(self.base_wall_hp),
            "workshop_wall_hp": float(self.workshop_wall_hp),
            "lab_wall_hp": float(self.lab_wall_hp),
            "enhancement_wall_hp": float(self.enhancement_wall_hp),
            "module_flat_wall_hp": float(self.module_flat_wall_hp),
        }

    @property
    def wall_regen_primitives(self) -> Mapping[str, float]:
        return {
            "base_wall_regen": float(self.base_wall_regen),
            "workshop_wall_regen": float(self.workshop_wall_regen),
            "lab_wall_regen": float(self.lab_wall_regen),
            "enhancement_wall_regen": float(self.enhancement_wall_regen),
            "module_flat_wall_regen": float(self.module_flat_wall_regen),
        }

    def rederive_for_workshop_levels(
        self,
        workshop_levels: Mapping[str, int],
        *,
        tower_hp_multiplier: float = 1.0,
    ) -> "SurvivabilityContributorBundle":
        values: dict[str, float | int | str | None | Mapping[str, float]] = {}
        row_tower_hp_multiplier = float(tower_hp_multiplier)
        if not isfinite(row_tower_hp_multiplier) or row_tower_hp_multiplier < 0.0:
            raise ValueError("tower_hp_multiplier must be finite and non-negative")
        if self.wall_hp_workshop_track and self.tower_hp_workshop_track:
            if self.tower_hp_workshop_baseline_level is None:
                raise ValueError("wall HP row derivation requires tower_hp_workshop_baseline_level")
            if self.wall_hp_workshop_baseline_level is None:
                raise ValueError("wall HP row derivation requires wall_hp_workshop_baseline_level")
            tower_level = int(workshop_levels.get(self.tower_hp_workshop_track, self.tower_hp_workshop_baseline_level))
            wall_level = int(workshop_levels.get(self.wall_hp_workshop_track, self.wall_hp_workshop_baseline_level))
            tower_hp = (
                workshop_value_for_level(self.tower_hp_workshop_track, tower_level)
                * float(self.tower_hp_workshop_multiplier)
                * row_tower_hp_multiplier
            )
            wall_ratio_percent_points = float(self.wall_hp_static_ratio_percent_points) + workshop_value_for_level(
                self.wall_hp_workshop_track,
                wall_level,
            )
            values["base_wall_hp"] = 0.0
            values["workshop_wall_hp"] = max(
                0.0,
                tower_hp * (wall_ratio_percent_points / 100.0) * float(self.wall_hp_effect_multiplier),
            )
            values["lab_wall_hp"] = 0.0
            values["enhancement_wall_hp"] = 0.0
            values["module_flat_wall_hp"] = 0.0
            values["wall_hp_multiplier"] = 1.0
        elif self.wall_hp_workshop_track:
            if self.wall_hp_workshop_baseline_level is None:
                raise ValueError("wall HP row derivation requires wall_hp_workshop_baseline_level")
            level = int(workshop_levels.get(self.wall_hp_workshop_track, self.wall_hp_workshop_baseline_level))
            values["workshop_wall_hp"] = max(
                0.0,
                float(self.workshop_wall_hp)
                + (level - int(self.wall_hp_workshop_baseline_level)) * float(self.wall_hp_workshop_value_per_level),
            )
        if self.wall_regen_workshop_track:
            if self.wall_regen_workshop_baseline_level is None:
                raise ValueError("wall regen row derivation requires wall_regen_workshop_baseline_level")
            level = int(workshop_levels.get(self.wall_regen_workshop_track, self.wall_regen_workshop_baseline_level))
            values["workshop_wall_regen"] = max(
                0.0,
                float(self.workshop_wall_regen)
                + (level - int(self.wall_regen_workshop_baseline_level)) * float(self.wall_regen_workshop_value_per_level),
            )
        return replace(self, **values)


@dataclass(frozen=True)
class CompiledPerkState:
    counts: Mapping[str, int]
    contributions: Mapping[str, float]
    source_policy: str
    dependency_identity: str


@dataclass(frozen=True)
class RunPlan:
    plan_id: str
    plan_version: str
    scope: RunScopeConfig
    checkpoint_policy: CheckpointPolicyConfig
    recurrence_policy: RecurrencePolicyConfig
    perk_policy: PerkPolicyConfig
    dependency_policy: DependencyPolicyConfig
    survivability_contributors: SurvivabilityContributorBundle
    death_wave_health_max_multiplier: float
    death_wave_health_max_wave: int
    dependency_order: tuple[str, ...]
    table1_registry: tuple[ColumnFormulaSpec, ...]


@dataclass(frozen=True)
class WaveProgressionRecurrence:
    display_wave: int = 0
    attack_wave: int = 0
    health_wave: int = 0
    attack_skip_counter: float = 0.0
    health_skip_counter: float = 0.0


@dataclass(frozen=True)
class FreeUpgradeRecurrence:
    carry_by_category: Mapping[str, float] = field(default_factory=dict)
    next_index_by_category: Mapping[str, int] = field(default_factory=dict)
    generated_total_by_category: Mapping[str, int] = field(default_factory=dict)
    allocated_total_by_category: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CommonTrajectoryInputs:
    start_wave: int
    end_wave: int
    boss_interval_waves: int = 10
    checkpoint_every_bosses: int = 1
    tier_column: str = "Tier 14"
    attack_skip_chance: float = 0.0
    health_skip_chance: float = 0.0
    attack_skip_chance_delta: float = 0.0
    health_skip_chance_delta: float = 0.0
    enemy_skip_decay_start_wave: int = 0
    enemy_skip_decay_fraction_per_step: float = 0.0
    enemy_skip_decay_interval_waves: int = 0
    enemy_skip_decay_schedule: Mapping[int, float] = field(default_factory=dict)
    attack_skip_static_percent_points: float = 0.0
    attack_skip_multiplier: float = 1.0
    attack_skip_workshop_track: str = ""
    attack_skip_workshop_baseline_level: int = 0
    health_skip_static_percent_points: float = 0.0
    health_skip_multiplier: float = 1.0
    health_skip_workshop_track: str = ""
    health_skip_workshop_baseline_level: int = 0
    free_upgrade_chance_by_category: Mapping[str, float] = field(default_factory=dict)
    category_track_order: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    track_max_levels: Mapping[str, int] = field(default_factory=dict)
    workshop_levels: Mapping[str, int] = field(default_factory=dict)
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
    perk_counts_by_wave: Mapping[int, Mapping[str, int]] = field(default_factory=dict)
    perk_contributions_by_wave: Mapping[int, Mapping[str, float]] = field(default_factory=dict)
    survivability_contributors: SurvivabilityContributorBundle | None = None
    death_wave_health_multiplier: float = 1.0
    death_wave_health_max_multiplier: float | None = None
    death_wave_health_max_wave: int = 1000


@dataclass(frozen=True)
class CommonTrajectoryRow:
    row_key: str
    display_wave: int
    checkpoint_index: int
    wave_progression: WaveProgressionRecurrence
    free_upgrade_state: FreeUpgradeRecurrence
    generated_free_upgrades_last_step: Mapping[str, int]
    allocated_free_upgrades_last_step: Mapping[str, int]
    unallocated_free_upgrades_last_step: Mapping[str, int]
    workshop_levels: Mapping[str, int]
    compiled_perk_state: CompiledPerkState
    survivability_contributors: SurvivabilityContributorBundle
    death_wave_health_multiplier: float
    common_inputs: Mapping[str, Any] = field(default_factory=dict)

    @property
    def perk_counts(self) -> Mapping[str, int]:
        return self.compiled_perk_state.counts

    @property
    def perk_contributions(self) -> Mapping[str, float]:
        return self.compiled_perk_state.contributions


@dataclass(frozen=True)
class CommonTrajectoryTable:
    table_id: str
    run_plan: RunPlan
    rows: tuple[CommonTrajectoryRow, ...]
    column_registry: tuple[ColumnFormulaSpec, ...]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


def compile_run_plan(inputs: CommonTrajectoryInputs) -> RunPlan:
    contributors = inputs.survivability_contributors or SurvivabilityContributorBundle(base_wall_hp=0.0)
    _validate_survivability_contributors(contributors)
    death_wave_health_max_multiplier = float(
        inputs.death_wave_health_max_multiplier
        if inputs.death_wave_health_max_multiplier is not None
        else inputs.death_wave_health_multiplier
    )
    death_wave_health_max_wave = int(inputs.death_wave_health_max_wave)
    if death_wave_health_max_multiplier < 0.0:
        raise ValueError("death_wave_health_max_multiplier cannot be negative")
    if death_wave_health_max_wave <= 0:
        raise ValueError("death_wave_health_max_wave must be positive")
    scope = RunScopeConfig(int(inputs.start_wave), int(inputs.end_wave), str(inputs.tier_column))
    checkpoint_policy = CheckpointPolicyConfig(max(1, int(inputs.boss_interval_waves)), max(1, int(inputs.checkpoint_every_bosses)))
    recurrence_policy = RecurrencePolicyConfig(
        attack_skip_chance=_bounded_fraction(inputs.attack_skip_chance),
        health_skip_chance=_bounded_fraction(inputs.health_skip_chance),
        attack_skip_chance_delta=float(inputs.attack_skip_chance_delta),
        health_skip_chance_delta=float(inputs.health_skip_chance_delta),
        enemy_skip_decay_start_wave=max(0, int(inputs.enemy_skip_decay_start_wave)),
        enemy_skip_decay_fraction_per_step=_bounded_fraction(inputs.enemy_skip_decay_fraction_per_step),
        enemy_skip_decay_interval_waves=max(0, int(inputs.enemy_skip_decay_interval_waves)),
        enemy_skip_decay_schedule={
            max(0, int(wave)): _bounded_fraction(value)
            for wave, value in dict(inputs.enemy_skip_decay_schedule or {}).items()
        },
        attack_skip_static_percent_points=float(inputs.attack_skip_static_percent_points),
        attack_skip_multiplier=float(inputs.attack_skip_multiplier),
        attack_skip_workshop_track=str(inputs.attack_skip_workshop_track or ""),
        attack_skip_workshop_baseline_level=int(inputs.attack_skip_workshop_baseline_level),
        health_skip_static_percent_points=float(inputs.health_skip_static_percent_points),
        health_skip_multiplier=float(inputs.health_skip_multiplier),
        health_skip_workshop_track=str(inputs.health_skip_workshop_track or ""),
        health_skip_workshop_baseline_level=int(inputs.health_skip_workshop_baseline_level),
        free_upgrade_chance_by_category=_category_fraction_map(inputs.free_upgrade_chance_by_category),
        category_track_order={str(k): tuple(v) for k, v in inputs.category_track_order.items()},
        track_max_levels={str(k): int(v) for k, v in inputs.track_max_levels.items()},
        workshop_levels={str(k): int(v) for k, v in inputs.workshop_levels.items()},
    )
    perk_policy = PerkPolicyConfig(
        perk_counts={str(k): int(v) for k, v in inputs.perk_counts.items()},
        perk_contributions={str(k): float(v) for k, v in inputs.perk_contributions.items()},
        perk_counts_by_wave=_normalize_perk_count_schedule(inputs.perk_counts_by_wave),
        perk_contributions_by_wave=_normalize_perk_contribution_schedule(inputs.perk_contributions_by_wave),
    )
    _validate_perk_policy(perk_policy)
    dependency_policy = DependencyPolicyConfig()
    payload = {
        "plan_version": RUN_PLAN_VERSION,
        "scope": scope,
        "checkpoint_policy": checkpoint_policy,
        "recurrence_policy": recurrence_policy,
        "perk_policy": perk_policy,
        "dependency_policy": dependency_policy,
        "survivability_contributors": contributors,
        "death_wave_health_max_multiplier": death_wave_health_max_multiplier,
        "death_wave_health_max_wave": death_wave_health_max_wave,
        "table1_registry": TABLE1_COLUMN_REGISTRY,
    }
    plan_id = "runplan:" + hashlib.sha256(
        json.dumps(_stable_json_value(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return RunPlan(
        plan_id=plan_id,
        plan_version=RUN_PLAN_VERSION,
        scope=scope,
        checkpoint_policy=checkpoint_policy,
        recurrence_policy=recurrence_policy,
        perk_policy=perk_policy,
        dependency_policy=dependency_policy,
        survivability_contributors=contributors,
        death_wave_health_max_multiplier=death_wave_health_max_multiplier,
        death_wave_health_max_wave=death_wave_health_max_wave,
        dependency_order=dependency_policy.dependency_order,
        table1_registry=TABLE1_COLUMN_REGISTRY,
    )


def build_checkpoint_wave_grid(*, start_wave: int, end_wave: int, boss_interval_waves: int = 10, checkpoint_every_bosses: int = 1) -> tuple[int, ...]:
    if end_wave < start_wave:
        raise ValueError("end_wave cannot be before start_wave")
    interval = max(1, int(boss_interval_waves))
    stride = max(1, int(checkpoint_every_bosses)) * interval
    first_wave = _first_boss_wave_at_or_after(start_wave, interval)
    if first_wave > end_wave:
        return ()
    return tuple(range(first_wave, int(end_wave) + 1, stride))


def _row_skip_chance(
    *,
    fallback_fraction: float,
    static_percent_points: float,
    multiplier: float,
    workshop_track: str,
    workshop_baseline_level: int,
    workshop_levels: Mapping[str, int],
    absolute_delta_fraction: float = 0.0,
) -> float:
    bounded_fallback = _bounded_fraction(fallback_fraction)
    track = str(workshop_track or "").strip()
    if not track:
        return _bounded_fraction(bounded_fallback + float(absolute_delta_fraction))
    baseline_level = int(workshop_baseline_level)
    if baseline_level < 0:
        raise ValueError("skip workshop baseline level cannot be negative")
    level = int(workshop_levels.get(track, baseline_level))
    resolved = (float(static_percent_points) + workshop_value_for_level(track, level)) * float(multiplier)
    return _bounded_fraction(resolved / 100.0 + float(absolute_delta_fraction))


def _enemy_skip_decay_delta_for_wave(
    *,
    display_wave: int,
    start_wave: int,
    fraction_per_step: float,
    interval_waves: int,
    schedule: Mapping[int, float] | None = None,
) -> tuple[int, float]:
    start = int(start_wave)
    if start > 0 and int(display_wave) >= start and schedule:
        elapsed = max(0, int(display_wave) - start)
        normalized = {
            max(0, int(threshold)): _bounded_fraction(value)
            for threshold, value in dict(schedule).items()
        }
        active_thresholds = [threshold for threshold in normalized if threshold <= elapsed]
        if active_thresholds:
            threshold = max(active_thresholds)
            amount = normalized[threshold]
            if amount > 0.0:
                return int(threshold), -amount
    interval = int(interval_waves)
    amount = _bounded_fraction(float(fraction_per_step))
    if start <= 0 or interval <= 0 or amount <= 0.0 or int(display_wave) < start:
        return 0, 0.0
    steps = max(0, (int(display_wave) - start) // interval)
    return steps, -amount * steps


def advance_wave_progression(state: WaveProgressionRecurrence, *, target_display_wave: int, attack_skip_chance: float, health_skip_chance: float) -> WaveProgressionRecurrence:
    if int(target_display_wave) < int(state.display_wave):
        raise ValueError("target_display_wave cannot move backwards")
    attack_wave = int(state.attack_wave)
    health_wave = int(state.health_wave)
    attack_counter = float(state.attack_skip_counter)
    health_counter = float(state.health_skip_counter)
    attack_skip = _bounded_fraction(attack_skip_chance)
    health_skip = _bounded_fraction(health_skip_chance)
    for _display_wave in range(int(state.display_wave) + 1, int(target_display_wave) + 1):
        attack_counter += attack_skip
        attack_suppressed = floor(attack_counter)
        attack_counter -= attack_suppressed
        attack_wave += max(0, 1 - attack_suppressed)
        health_counter += health_skip
        health_suppressed = floor(health_counter)
        health_counter -= health_suppressed
        health_wave += max(0, 1 - health_suppressed)
    return WaveProgressionRecurrence(int(target_display_wave), attack_wave, health_wave, attack_counter, health_counter)


def advance_free_upgrade_generation(state: FreeUpgradeRecurrence, *, wave_count: int, free_upgrade_chance_by_category: Mapping[str, float]) -> tuple[FreeUpgradeRecurrence, dict[str, int]]:
    carry = _category_float_map(state.carry_by_category)
    generated_last = {category: 0 for category in CATEGORY_IDS}
    waves = max(0, int(wave_count))
    for category in CATEGORY_IDS:
        total = carry[category] + (_bounded_fraction(free_upgrade_chance_by_category.get(category, 0.0)) * waves)
        guaranteed = int(floor(total + 1e-12))
        generated_last[category] = guaranteed
        carry[category] = total - guaranteed
    generated_total = _category_int_map(state.generated_total_by_category)
    for category in CATEGORY_IDS:
        generated_total[category] += int(generated_last[category])
    return (
        FreeUpgradeRecurrence(carry, _category_int_map(state.next_index_by_category), generated_total, _category_int_map(state.allocated_total_by_category)),
        generated_last,
    )


def allocate_free_upgrades(state: FreeUpgradeRecurrence, *, workshop_levels: Mapping[str, int], generated_last_step: Mapping[str, int], category_track_order: Mapping[str, tuple[str, ...]], track_max_levels: Mapping[str, int]) -> tuple[FreeUpgradeRecurrence, dict[str, int], dict[str, int], dict[str, int]]:
    levels = {str(track): int(level) for track, level in workshop_levels.items()}
    next_index = _category_int_map(state.next_index_by_category)
    allocated_last = {category: 0 for category in CATEGORY_IDS}
    unallocated_last = {category: 0 for category in CATEGORY_IDS}
    for category in CATEGORY_IDS:
        order = tuple(category_track_order.get(category, ()))
        generated = int(generated_last_step.get(category, 0) or 0)
        candidates = [
            str(track)
            for track in order
            if int(levels.get(str(track), 0)) < int(track_max_levels.get(str(track), 0))
        ]
        for _ in range(generated):
            if not candidates:
                unallocated_last[category] += 1
                continue
            candidate_index = next_index[category] % len(candidates)
            track = candidates[candidate_index]
            next_level = int(levels.get(track, 0)) + 1
            levels[track] = next_level
            allocated_last[category] += 1
            next_index[category] += 1
            if next_level >= int(track_max_levels.get(track, 0)):
                candidates.pop(candidate_index)
        if len(order) > 1:
            next_index[category] %= len(order)
    allocated_total = _category_int_map(state.allocated_total_by_category)
    for category in CATEGORY_IDS:
        allocated_total[category] += int(allocated_last[category])
    return (
        FreeUpgradeRecurrence(_category_float_map(state.carry_by_category), next_index, _category_int_map(state.generated_total_by_category), allocated_total),
        levels,
        allocated_last,
        unallocated_last,
    )


def default_category_track_order(workshop_levels: Mapping[str, int], track_max_levels: Mapping[str, int]) -> dict[str, tuple[str, ...]]:
    order: dict[str, list[str]] = {category: [] for category in CATEGORY_IDS}
    for track in workshop_levels:
        category = DEFAULT_WORKSHOP_CATEGORY_BY_TRACK.get(str(track))
        if category in order and str(track) in track_max_levels:
            order[category].append(str(track))
    return {category: tuple(tracks) for category, tracks in order.items()}


def build_common_trajectory(inputs: CommonTrajectoryInputs | RunPlan) -> CommonTrajectoryTable:
    plan = inputs if isinstance(inputs, RunPlan) else compile_run_plan(inputs)
    checkpoint_waves = build_checkpoint_wave_grid(
        start_wave=plan.scope.start_wave,
        end_wave=plan.scope.end_wave,
        boss_interval_waves=plan.checkpoint_policy.boss_interval_waves,
        checkpoint_every_bosses=plan.checkpoint_policy.checkpoint_every_bosses,
    )
    progression = WaveProgressionRecurrence(max(0, plan.scope.start_wave - 1), max(0, plan.scope.start_wave - 1), max(0, plan.scope.start_wave - 1))
    free_state = FreeUpgradeRecurrence()
    workshop_levels: Mapping[str, int] = dict(plan.recurrence_policy.workshop_levels)
    rows: list[CommonTrajectoryRow] = []
    previous_wave = progression.display_wave
    for index, wave in enumerate(checkpoint_waves):
        enemy_skip_decay_steps, enemy_skip_decay_delta = _enemy_skip_decay_delta_for_wave(
            display_wave=int(wave),
            start_wave=plan.recurrence_policy.enemy_skip_decay_start_wave,
            fraction_per_step=plan.recurrence_policy.enemy_skip_decay_fraction_per_step,
            interval_waves=plan.recurrence_policy.enemy_skip_decay_interval_waves,
            schedule=plan.recurrence_policy.enemy_skip_decay_schedule,
        )
        row_attack_skip_chance = _row_skip_chance(
            fallback_fraction=plan.recurrence_policy.attack_skip_chance,
            absolute_delta_fraction=plan.recurrence_policy.attack_skip_chance_delta + enemy_skip_decay_delta,
            static_percent_points=plan.recurrence_policy.attack_skip_static_percent_points,
            multiplier=plan.recurrence_policy.attack_skip_multiplier,
            workshop_track=plan.recurrence_policy.attack_skip_workshop_track,
            workshop_baseline_level=plan.recurrence_policy.attack_skip_workshop_baseline_level,
            workshop_levels=workshop_levels,
        )
        row_health_skip_chance = _row_skip_chance(
            fallback_fraction=plan.recurrence_policy.health_skip_chance,
            absolute_delta_fraction=plan.recurrence_policy.health_skip_chance_delta + enemy_skip_decay_delta,
            static_percent_points=plan.recurrence_policy.health_skip_static_percent_points,
            multiplier=plan.recurrence_policy.health_skip_multiplier,
            workshop_track=plan.recurrence_policy.health_skip_workshop_track,
            workshop_baseline_level=plan.recurrence_policy.health_skip_workshop_baseline_level,
            workshop_levels=workshop_levels,
        )
        progression = advance_wave_progression(
            progression,
            target_display_wave=wave,
            attack_skip_chance=row_attack_skip_chance,
            health_skip_chance=row_health_skip_chance,
        )
        free_state, generated_last = advance_free_upgrade_generation(
            free_state,
            wave_count=int(wave) - int(previous_wave),
            free_upgrade_chance_by_category=plan.recurrence_policy.free_upgrade_chance_by_category,
        )
        free_state, workshop_levels, allocated_last, unallocated_last = allocate_free_upgrades(
            free_state,
            workshop_levels=workshop_levels,
            generated_last_step=generated_last,
            category_track_order=plan.recurrence_policy.category_track_order,
            track_max_levels=plan.recurrence_policy.track_max_levels,
        )
        compiled_perk_state = _compile_perk_state(plan.perk_policy, display_wave=int(wave))
        row_death_wave_health_multiplier = death_wave_health_multiplier_for_wave(
            display_wave=int(wave),
            max_multiplier=plan.death_wave_health_max_multiplier,
            max_wave=plan.death_wave_health_max_wave,
        )
        row_survivability = plan.survivability_contributors.rederive_for_workshop_levels(
            workshop_levels,
            tower_hp_multiplier=row_death_wave_health_multiplier,
        )
        rows.append(CommonTrajectoryRow(
            row_key=f"{plan.plan_id}:table1:{index}:{wave}",
            display_wave=int(wave),
            checkpoint_index=index,
            wave_progression=progression,
            free_upgrade_state=free_state,
            generated_free_upgrades_last_step=generated_last,
            allocated_free_upgrades_last_step=allocated_last,
            unallocated_free_upgrades_last_step=unallocated_last,
            workshop_levels=dict(workshop_levels),
            compiled_perk_state=compiled_perk_state,
            survivability_contributors=row_survivability,
            death_wave_health_multiplier=row_death_wave_health_multiplier,
            common_inputs={
                "plan_id": plan.plan_id,
                "start_progression_wave": max(0, plan.scope.start_wave - 1),
                "attack_skip_chance": float(row_attack_skip_chance),
                "health_skip_chance": float(row_health_skip_chance),
                "attack_skip_chance_delta": float(plan.recurrence_policy.attack_skip_chance_delta),
                "health_skip_chance_delta": float(plan.recurrence_policy.health_skip_chance_delta),
                "enemy_skip_decay_start_wave": int(plan.recurrence_policy.enemy_skip_decay_start_wave),
                "enemy_skip_decay_fraction_per_step": float(plan.recurrence_policy.enemy_skip_decay_fraction_per_step),
                "enemy_skip_decay_interval_waves": int(plan.recurrence_policy.enemy_skip_decay_interval_waves),
                "enemy_skip_decay_schedule": dict(plan.recurrence_policy.enemy_skip_decay_schedule),
                "enemy_skip_decay_steps": int(enemy_skip_decay_steps),
                "enemy_skip_decay_delta": float(enemy_skip_decay_delta),
                "boss_interval_waves": int(plan.checkpoint_policy.boss_interval_waves),
                "checkpoint_every_bosses": int(plan.checkpoint_policy.checkpoint_every_bosses),
                "tier_column": plan.scope.tier_column,
            },
        ))
        previous_wave = int(wave)
    table = CommonTrajectoryTable(
        "boss_waves.common_trajectory.v1",
        plan,
        tuple(rows),
        TABLE1_COLUMN_REGISTRY,
        {
            "row_count": len(rows),
            "plan_id": plan.plan_id,
            "death_wave_health_max_multiplier": float(plan.death_wave_health_max_multiplier),
            "death_wave_health_max_wave": int(plan.death_wave_health_max_wave),
        },
    )
    validate_table1_registry(table)
    return table


def death_wave_health_multiplier_for_wave(*, display_wave: int, max_multiplier: float, max_wave: int) -> float:
    maximum = float(max_multiplier)
    wave = max(0, int(display_wave))
    maxed_wave = int(max_wave)
    if not isfinite(maximum) or maximum < 0.0:
        raise ValueError("death_wave_health max multiplier must be finite and non-negative")
    if maxed_wave <= 0:
        raise ValueError("death_wave_health max wave must be positive")
    if maximum <= 1.0:
        return maximum
    progress = min(1.0, wave / float(maxed_wave))
    return 1.0 + ((maximum - 1.0) * progress)


def validate_table1_registry(table: CommonTrajectoryTable) -> None:
    registry = _registry_by_id(table.column_registry)
    missing_required = sorted(TABLE1_REQUIRED_COLUMN_IDS - frozenset(registry))
    if missing_required:
        raise ValueError(f"Table 1 registry missing required columns: {missing_required!r}")
    _validate_registry_contracts(registry, TABLE1_KEY_CONTRACTS, "Table 1")
    registry_ids = frozenset(registry)
    for row in table.rows:
        missing = [column_id for column_id in registry_ids if not hasattr(row, column_id)]
        if missing:
            raise ValueError(f"Table 1 row missing registered columns: {missing!r}")
        _validate_table1_row_contract(row)


def _compile_perk_state(perk_policy: PerkPolicyConfig, *, display_wave: int | None = None) -> CompiledPerkState:
    _validate_perk_policy(perk_policy)
    counts = dict(perk_policy.perk_counts)
    contributions = dict(perk_policy.perk_contributions)
    if display_wave is not None:
        counts.update(_scheduled_mapping_at_wave(perk_policy.perk_counts_by_wave, int(display_wave)))
        contributions.update(_scheduled_mapping_at_wave(perk_policy.perk_contributions_by_wave, int(display_wave)))
    payload = {
        "counts": dict(sorted((str(k), int(v)) for k, v in counts.items())),
        "contributions": dict(sorted((str(k), float(v)) for k, v in contributions.items())),
        "source_policy": perk_policy.perk_source,
        "display_wave": display_wave,
    }
    identity = "perk:" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return CompiledPerkState(payload["counts"], payload["contributions"], perk_policy.perk_source, identity)


def _validate_perk_policy(perk_policy: PerkPolicyConfig) -> None:
    if str(perk_policy.perk_source) != "explicit_staged_perk_policy":
        raise ValueError("perk policy source must be explicit_staged_perk_policy")
    for perk_id, count in perk_policy.perk_counts.items():
        if int(count) < 0:
            raise ValueError(f"perk count for {perk_id!r} cannot be negative")
    for contribution_id, value in perk_policy.perk_contributions.items():
        effect_id = _perk_contribution_effect_id(str(contribution_id))
        if effect_id not in PERK_CONTRIBUTION_EFFECT_IDS:
            raise ValueError(f"unsupported perk contribution effect {effect_id!r}")
        if effect_id.endswith("_multiplier") and float(value) < 0.0:
            raise ValueError(f"perk contribution {contribution_id!r} multiplier cannot be negative")
    for wave, counts in perk_policy.perk_counts_by_wave.items():
        if int(wave) < 0:
            raise ValueError("perk_counts_by_wave cannot use negative waves")
        for perk_id, count in counts.items():
            if int(count) < 0:
                raise ValueError(f"perk count for {perk_id!r} cannot be negative")
    for wave, contributions in perk_policy.perk_contributions_by_wave.items():
        if int(wave) < 0:
            raise ValueError("perk_contributions_by_wave cannot use negative waves")
        for contribution_id, value in contributions.items():
            effect_id = _perk_contribution_effect_id(str(contribution_id))
            if effect_id not in PERK_CONTRIBUTION_EFFECT_IDS:
                raise ValueError(f"unsupported perk contribution effect {effect_id!r}")
            if effect_id.endswith("_multiplier") and float(value) < 0.0:
                raise ValueError(f"perk contribution {contribution_id!r} multiplier cannot be negative")


def _scheduled_mapping_at_wave(schedule: Mapping[int, Mapping[str, Any]], display_wave: int) -> dict[str, Any]:
    active: dict[str, Any] = {}
    for wave, values in sorted(schedule.items(), key=lambda item: int(item[0])):
        if int(wave) <= int(display_wave):
            active = dict(values)
        else:
            break
    return active


def _normalize_perk_count_schedule(schedule: Mapping[int, Mapping[str, int]]) -> dict[int, dict[str, int]]:
    return {int(wave): {str(k): int(v) for k, v in values.items()} for wave, values in schedule.items()}


def _normalize_perk_contribution_schedule(schedule: Mapping[int, Mapping[str, float]]) -> dict[int, dict[str, float]]:
    return {int(wave): {str(k): float(v) for k, v in values.items()} for wave, values in schedule.items()}


def _perk_contribution_effect_id(contribution_id: str) -> str:
    return str(contribution_id).split(":", 1)[1] if ":" in str(contribution_id) else str(contribution_id)


def _validate_survivability_contributors(contributors: SurvivabilityContributorBundle) -> None:
    if contributors.source_policy != "explicit_staged_contributors_v1":
        raise ValueError("survivability contributors source_policy must be explicit_staged_contributors_v1")
    for key, value in _stable_json_value(contributors).items():
        if key in {"timed_dr_by_lane", "source_policy"} or value is None:
            continue
        if key.endswith("_track"):
            if not str(value):
                raise ValueError(f"survivability contributor {key} cannot be empty")
            continue
        if float(value) < 0.0:
            raise ValueError(f"survivability contributor {key} cannot be negative")
    if contributors.wall_hp_workshop_track and contributors.wall_hp_workshop_baseline_level is None:
        raise ValueError("wall HP workshop derivation requires a baseline level")
    if contributors.wall_regen_workshop_track and contributors.wall_regen_workshop_baseline_level is None:
        raise ValueError("wall regen workshop derivation requires a baseline level")
    for lane, value in contributors.timed_dr_by_lane.items():
        if str(lane) not in {"avg", "min", "max"}:
            raise ValueError(f"unknown timed DR lane {lane!r}")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"timed DR lane {lane!r} must be a fraction")


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


def _validate_table1_row_contract(row: CommonTrajectoryRow) -> None:
    if not isinstance(row.row_key, str) or not row.row_key:
        raise ValueError("Table 1 row_key must be a non-empty string")
    if not isinstance(row.display_wave, int):
        raise ValueError("Table 1 display_wave must be int")
    if not isinstance(row.wave_progression, WaveProgressionRecurrence):
        raise ValueError("Table 1 wave_progression must be WaveProgressionRecurrence")
    if not isinstance(row.free_upgrade_state, FreeUpgradeRecurrence):
        raise ValueError("Table 1 free_upgrade_state must be FreeUpgradeRecurrence")
    if not isinstance(row.compiled_perk_state, CompiledPerkState):
        raise ValueError("Table 1 compiled_perk_state must be CompiledPerkState")
    if not isinstance(row.survivability_contributors, SurvivabilityContributorBundle):
        raise ValueError("Table 1 survivability_contributors must be SurvivabilityContributorBundle")
    if float(row.death_wave_health_multiplier) < 0.0:
        raise ValueError("Table 1 death_wave_health_multiplier cannot be negative")


def _first_boss_wave_at_or_after(start_wave: int, boss_interval_waves: int) -> int:
    interval = max(1, int(boss_interval_waves))
    if int(start_wave) <= interval:
        return interval
    remainder = int(start_wave) % interval
    return int(start_wave) if remainder == 0 else int(start_wave) + (interval - remainder)


def _bounded_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _category_float_map(values: Mapping[str, float]) -> dict[str, float]:
    return {category: float(values.get(category, 0.0) or 0.0) for category in CATEGORY_IDS}


def _category_fraction_map(values: Mapping[str, float]) -> dict[str, float]:
    return {category: _bounded_fraction(values.get(category, 0.0)) for category in CATEGORY_IDS}


def _category_int_map(values: Mapping[str, int]) -> dict[str, int]:
    return {category: int(values.get(category, 0) or 0) for category in CATEGORY_IDS}


def _stable_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _stable_json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _stable_json_value(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple):
        return [_stable_json_value(v) for v in value]
    if isinstance(value, list):
        return [_stable_json_value(v) for v in value]
    return value
