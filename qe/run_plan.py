from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from math import floor
from typing import Any, Mapping


CATEGORY_IDS: tuple[str, str, str] = ("attack", "defense", "utility")
RUN_PLAN_VERSION = "boss_waves.run_plan.v1"


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
    ColumnFormulaSpec("survivability_contributors", "qe", "SurvivabilityContributorBundle", ("survivability_policy",), "contributor_bundle", "compile_once", "plan_static"),
    ColumnFormulaSpec("death_wave_health_multiplier", "qe", "float", ("survivability_policy",), "pass_through", "compile_once", "plan_static"),
)


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
    free_upgrade_chance_by_category: Mapping[str, float] = field(default_factory=dict)
    category_track_order: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    track_max_levels: Mapping[str, int] = field(default_factory=dict)
    workshop_levels: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PerkPolicyConfig:
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
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
    timed_dr_by_lane: Mapping[str, float] = field(default_factory=dict)
    source_policy: str = "explicit_staged_contributors_v1"


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
    free_upgrade_chance_by_category: Mapping[str, float] = field(default_factory=dict)
    category_track_order: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    track_max_levels: Mapping[str, int] = field(default_factory=dict)
    workshop_levels: Mapping[str, int] = field(default_factory=dict)
    perk_counts: Mapping[str, int] = field(default_factory=dict)
    perk_contributions: Mapping[str, float] = field(default_factory=dict)
    survivability_contributors: SurvivabilityContributorBundle | None = None
    death_wave_health_multiplier: float = 1.0


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
    scope = RunScopeConfig(int(inputs.start_wave), int(inputs.end_wave), str(inputs.tier_column))
    checkpoint_policy = CheckpointPolicyConfig(max(1, int(inputs.boss_interval_waves)), max(1, int(inputs.checkpoint_every_bosses)))
    recurrence_policy = RecurrencePolicyConfig(
        attack_skip_chance=_bounded_fraction(inputs.attack_skip_chance),
        health_skip_chance=_bounded_fraction(inputs.health_skip_chance),
        free_upgrade_chance_by_category=_category_fraction_map(inputs.free_upgrade_chance_by_category),
        category_track_order={str(k): tuple(v) for k, v in inputs.category_track_order.items()},
        track_max_levels={str(k): int(v) for k, v in inputs.track_max_levels.items()},
        workshop_levels={str(k): int(v) for k, v in inputs.workshop_levels.items()},
    )
    perk_policy = PerkPolicyConfig(
        perk_counts={str(k): int(v) for k, v in inputs.perk_counts.items()},
        perk_contributions={str(k): float(v) for k, v in inputs.perk_contributions.items()},
    )
    dependency_policy = DependencyPolicyConfig()
    payload = {
        "plan_version": RUN_PLAN_VERSION,
        "scope": scope,
        "checkpoint_policy": checkpoint_policy,
        "recurrence_policy": recurrence_policy,
        "perk_policy": perk_policy,
        "dependency_policy": dependency_policy,
        "survivability_contributors": contributors,
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
    for _ in range(max(0, int(wave_count))):
        for category in CATEGORY_IDS:
            carry[category] += _bounded_fraction(free_upgrade_chance_by_category.get(category, 0.0))
            guaranteed = int(floor(carry[category] + 1e-12))
            if guaranteed > 0:
                generated_last[category] += guaranteed
                carry[category] -= guaranteed
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
        for _ in range(generated):
            candidates = [track for track in order if int(levels.get(track, 0)) < int(track_max_levels.get(track, 0))]
            if not candidates:
                unallocated_last[category] += 1
                continue
            track = candidates[next_index[category] % len(candidates)]
            levels[track] = int(levels.get(track, 0)) + 1
            allocated_last[category] += 1
            next_index[category] += 1
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
    compiled_perk_state = _compile_perk_state(plan.perk_policy)
    rows: list[CommonTrajectoryRow] = []
    previous_wave = progression.display_wave
    for index, wave in enumerate(checkpoint_waves):
        progression = advance_wave_progression(
            progression,
            target_display_wave=wave,
            attack_skip_chance=plan.recurrence_policy.attack_skip_chance,
            health_skip_chance=plan.recurrence_policy.health_skip_chance,
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
            survivability_contributors=plan.survivability_contributors,
            death_wave_health_multiplier=1.0,
            common_inputs={
                "plan_id": plan.plan_id,
                "start_progression_wave": max(0, plan.scope.start_wave - 1),
                "attack_skip_chance": float(plan.recurrence_policy.attack_skip_chance),
                "health_skip_chance": float(plan.recurrence_policy.health_skip_chance),
                "boss_interval_waves": int(plan.checkpoint_policy.boss_interval_waves),
                "checkpoint_every_bosses": int(plan.checkpoint_policy.checkpoint_every_bosses),
                "tier_column": plan.scope.tier_column,
            },
        ))
        previous_wave = int(wave)
    table = CommonTrajectoryTable("boss_waves.common_trajectory.v1", plan, tuple(rows), TABLE1_COLUMN_REGISTRY, {"row_count": len(rows), "plan_id": plan.plan_id})
    validate_table1_registry(table)
    return table


def validate_table1_registry(table: CommonTrajectoryTable) -> None:
    registry_ids = frozenset(spec.column_id for spec in table.column_registry)
    for row in table.rows:
        missing = [column_id for column_id in registry_ids if not hasattr(row, column_id)]
        if missing:
            raise ValueError(f"Table 1 row missing registered columns: {missing!r}")


def _compile_perk_state(perk_policy: PerkPolicyConfig) -> CompiledPerkState:
    payload = {
        "counts": dict(sorted((str(k), int(v)) for k, v in perk_policy.perk_counts.items())),
        "contributions": dict(sorted((str(k), float(v)) for k, v in perk_policy.perk_contributions.items())),
        "source_policy": perk_policy.perk_source,
    }
    identity = "perk:" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return CompiledPerkState(payload["counts"], payload["contributions"], perk_policy.perk_source, identity)


def _validate_survivability_contributors(contributors: SurvivabilityContributorBundle) -> None:
    for key, value in _stable_json_value(contributors).items():
        if key in {"timed_dr_by_lane", "source_policy"}:
            continue
        if float(value) < 0.0:
            raise ValueError(f"survivability contributor {key} cannot be negative")
    for lane, value in contributors.timed_dr_by_lane.items():
        if str(lane) not in {"avg", "min", "max"}:
            raise ValueError(f"unknown timed DR lane {lane!r}")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"timed DR lane {lane!r} must be a fraction")


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
