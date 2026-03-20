from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import (
    compile_baseline_account_stat_inputs,
    compile_baseline_gem_respec_stat_inputs,
    compile_baseline_loadout_stat_inputs,
)
from tower_sim.registry.stat_registry import Phase
from tower_sim.registry.static_v2_contract import StaticV2ContractError, load_static_v2_contract
from tower_sim.util.account_snapshot import AccountSnapshot


@dataclass(frozen=True)
class StageMaterialization:
    by_stage: Mapping[str, list[StatInput]]
    missing: Mapping[str, list[str]]
    families_by_stage: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class RuntimeOverlayRow:
    family: str
    stage: str
    payload: Mapping[str, object]
    provenance: str


@dataclass(frozen=True)
class RuntimeOverlayMaterialization:
    order: tuple[str, ...]
    by_family: Mapping[str, list[RuntimeOverlayRow]]


@dataclass(frozen=True)
class RuntimeStateMaterialization:
    static_stage_order: tuple[str, ...]
    stage_stat_inputs_by_stage: Mapping[str, tuple[StatInput, ...]]
    stage_stat_values_by_stage: Mapping[str, Mapping[str, tuple[float, ...]]]
    start_of_run_stat_inputs: tuple[StatInput, ...]
    start_of_run_stat_values: Mapping[str, tuple[float, ...]]
    overlay_order: tuple[str, ...]
    overlay_rows: tuple[RuntimeOverlayRow, ...]
    overlay_counts: Mapping[str, int]


@dataclass(frozen=True)
class RuntimeExecutionPassArtifact:
    executed_overlay_order: tuple[str, ...]
    start_of_run_stat_totals: Mapping[str, float]
    applied_overlay_counts: Mapping[str, int]
    execution_trace: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeExecutionMaterialization:
    runtime_state: RuntimeStateMaterialization
    execution_pass: RuntimeExecutionPassArtifact


@dataclass(frozen=True)
class RuntimeExecutionStep:
    family: str
    row_index: int
    stage: str
    payload: Mapping[str, object]
    provenance: str


@dataclass(frozen=True)
class RuntimeExecutionPlan:
    ordered_steps: tuple[RuntimeExecutionStep, ...]
    per_family_step_counts: Mapping[str, int]


@dataclass(frozen=True)
class RuntimeExecutionSnapshot:
    plan: RuntimeExecutionPlan
    execution_pass: RuntimeExecutionPassArtifact
    overlay_numeric_totals_by_family: Mapping[str, float]
    start_of_run_grand_total: float


@dataclass(frozen=True)
class RuntimePreCombatTransitionStep:
    family: str
    row_index: int
    numeric_payload_total: float


@dataclass(frozen=True)
class RuntimePreCombatTransitionArtifact:
    start_of_run_grand_total: float
    transition_totals_by_family: Mapping[str, float]
    ordered_transition_steps: tuple[RuntimePreCombatTransitionStep, ...]


@dataclass(frozen=True)
class RuntimeStateTransitionStep:
    family: str
    row_index: int
    input_total: float
    cumulative_total: float


@dataclass(frozen=True)
class RuntimeStateTransitionArtifact:
    start_of_run_grand_total: float
    final_pre_combat_total: float
    ordered_steps: tuple[RuntimeStateTransitionStep, ...]
    applied_totals_by_family: Mapping[str, float]


@dataclass(frozen=True)
class RuntimeTransitionCheckpoint:
    transition: RuntimeStateTransitionArtifact
    expected_final_pre_combat_total: float
    total_delta_from_start: float


@dataclass(frozen=True)
class RuntimePreCombatBalanceSheet:
    start_total: float
    final_total: float
    total_delta: float
    family_deltas_in_order: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class StaticStageBaselineAudit:
    stage_order: tuple[str, ...]
    stat_input_counts_by_stage: Mapping[str, int]
    unique_stat_counts_by_stage: Mapping[str, int]
    stage_total_values: Mapping[str, float]


@dataclass(frozen=True)
class RuntimeExecutionPhaseBundle:
    static_stage_audit: StaticStageBaselineAudit
    runtime_state: RuntimeStateMaterialization
    execution_plan: RuntimeExecutionPlan
    execution_pass: RuntimeExecutionPassArtifact
    execution_snapshot: RuntimeExecutionSnapshot
    pre_combat_transition: RuntimePreCombatTransitionArtifact
    runtime_state_transition: RuntimeStateTransitionArtifact
    transition_checkpoint: RuntimeTransitionCheckpoint
    pre_combat_balance_sheet: RuntimePreCombatBalanceSheet


REQUIRED_STATIC_STAGES = (
    "baseline_account",
    "baseline_gem_respec",
    "baseline_loadout",
)

REQUIRED_RUNTIME_OVERLAY_FAMILIES = (
    "perks",
    "battle_conditions",
    "cash_workshop_purchases",
    "free_upgrades",
    "eals_realized_effect",
    "ehls_realized_effect",
)


_PROVENANCE_PREFIX_TO_FAMILY = {
    "workshop_formula": "workshop",
    "workshop_alias": "workshop",
    "workshop_table": "workshop",
    "relics": "relic",
    "uw_section": "uw",
    "uw_alias": "uw",
    "bot_table": "bot",
    "cards": "card",
    "modules": "module_main",
}

_DEFAULT_PROVENANCE_PREFIXES = {"base"}

_PERKS_TABLE_PATH = Path("tables/inputs/perks/perks_v1.csv")
_BATTLE_CONDITIONS_TABLE_PATH = Path("tables/inputs/combat/tier_battle_conditions.csv")


def required_static_stages() -> tuple[str, ...]:
    return REQUIRED_STATIC_STAGES


def required_runtime_overlay_families() -> tuple[str, ...]:
    return REQUIRED_RUNTIME_OVERLAY_FAMILIES


def validate_required_stages_present() -> None:
    contract = load_static_v2_contract()
    observed = tuple(contract.required_static_stage_order)
    if observed != REQUIRED_STATIC_STAGES:
        raise StaticV2ContractError(
            f"required_stage_order_mismatch:expected={REQUIRED_STATIC_STAGES}:observed={observed}"
        )


def validate_required_runtime_overlay_families_present() -> None:
    contract = load_static_v2_contract()
    observed = tuple(contract.required_runtime_overlay_order)
    if observed != REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        raise StaticV2ContractError(
            "required_runtime_overlay_order_mismatch:"
            f"expected={REQUIRED_RUNTIME_OVERLAY_FAMILIES}:observed={observed}"
        )


def materialize_static_stages(snapshot: AccountSnapshot) -> StageMaterialization:
    validate_required_stages_present()
    contract = load_static_v2_contract()

    baseline_account = compile_baseline_account_stat_inputs(snapshot)
    baseline_gem_respec = compile_baseline_gem_respec_stat_inputs(snapshot)
    baseline_loadout = compile_baseline_loadout_stat_inputs(snapshot)

    by_stage = {
        "baseline_account": _with_explicit_contributor_families(
            list(baseline_account.stat_inputs), stage="baseline_account"
        ),
        "baseline_gem_respec": _with_explicit_contributor_families(
            list(baseline_gem_respec.stat_inputs), stage="baseline_gem_respec"
        ),
        "baseline_loadout": _with_explicit_contributor_families(
            list(baseline_loadout.stat_inputs), stage="baseline_loadout"
        ),
    }

    families_by_stage = {
        stage: _validate_stage_inputs_against_bridge(
            contract.stage_bridge_by_family,
            snapshot=snapshot,
            stage=stage,
            stat_inputs=inputs,
        )
        for stage, inputs in by_stage.items()
    }

    return StageMaterialization(
        by_stage=by_stage,
        missing={
            "baseline_account": list(baseline_account.missing),
            "baseline_gem_respec": list(baseline_gem_respec.missing),
            "baseline_loadout": list(baseline_loadout.missing),
        },
        families_by_stage=families_by_stage,
    )


def audit_static_stage_baselines(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
) -> StaticStageBaselineAudit:
    materialized = stage_materialization or materialize_static_stages(snapshot)

    observed_stage_order = tuple(materialized.by_stage.keys())
    if observed_stage_order != REQUIRED_STATIC_STAGES:
        raise StaticV2ContractError(
            f"static_stage_audit_stage_order_unexpected:expected={REQUIRED_STATIC_STAGES}:observed={observed_stage_order}"
        )

    stat_input_counts_by_stage: dict[str, int] = {}
    unique_stat_counts_by_stage: dict[str, int] = {}
    stage_total_values: dict[str, float] = {}

    for stage in REQUIRED_STATIC_STAGES:
        inputs = materialized.by_stage.get(stage)
        if inputs is None:
            raise StaticV2ContractError(f"static_stage_audit_missing_stage:{stage}")
        if len(inputs) == 0:
            raise StaticV2ContractError(f"static_stage_audit_empty_stage:{stage}")

        values_by_stat = _group_stage_stat_values(inputs, stage=stage)
        stage_total = 0.0
        for values in values_by_stat.values():
            subtotal = float(sum(values))
            if not math.isfinite(subtotal):
                raise StaticV2ContractError(
                    f"static_stage_audit_non_finite_stage_total:{stage}"
                )
            stage_total += subtotal
        if not math.isfinite(stage_total):
            raise StaticV2ContractError(
                f"static_stage_audit_non_finite_stage_total:{stage}"
            )

        stat_input_counts_by_stage[stage] = len(inputs)
        unique_stat_counts_by_stage[stage] = len(values_by_stat)
        stage_total_values[stage] = stage_total

    return StaticStageBaselineAudit(
        stage_order=REQUIRED_STATIC_STAGES,
        stat_input_counts_by_stage=stat_input_counts_by_stage,
        unique_stat_counts_by_stage=unique_stat_counts_by_stage,
        stage_total_values=stage_total_values,
    )


def materialize_runtime_overlays(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
) -> RuntimeOverlayMaterialization:
    validate_required_runtime_overlay_families_present()
    contract = load_static_v2_contract()

    materialized = stage_materialization or materialize_static_stages(snapshot)
    overlay_order = tuple(contract.required_runtime_overlay_order)

    if overlay_order != REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        raise StaticV2ContractError("runtime_overlay_order_unexpected")

    gem_inputs = materialized.by_stage.get("baseline_gem_respec")
    if gem_inputs is None:
        raise StaticV2ContractError("runtime_overlay_missing_stage:baseline_gem_respec")

    rows_by_family: dict[str, list[RuntimeOverlayRow]] = {
        family: [] for family in overlay_order
    }

    rows_by_family["perks"].append(
        RuntimeOverlayRow(
            family="perks",
            stage="runtime_overlay",
            payload={"reference_rows": _count_data_rows(_PERKS_TABLE_PATH)},
            provenance=f"table:{_PERKS_TABLE_PATH}",
        )
    )
    rows_by_family["battle_conditions"].append(
        RuntimeOverlayRow(
            family="battle_conditions",
            stage="runtime_overlay",
            payload={"reference_rows": _count_data_rows(_BATTLE_CONDITIONS_TABLE_PATH)},
            provenance=f"table:{_BATTLE_CONDITIONS_TABLE_PATH}",
        )
    )

    start_total = 0
    end_total = 0
    tracked = 0
    for entry in snapshot.workshop.values():
        if entry.coin_level is None or entry.end_level is None:
            continue
        if entry.end_level < entry.coin_level:
            raise StaticV2ContractError("runtime_overlay_invalid_workshop_progression:end_below_start")
        tracked += 1
        start_total += int(entry.coin_level)
        end_total += int(entry.end_level)
    if tracked == 0:
        raise StaticV2ContractError("runtime_overlay_missing_workshop_progression_data")
    rows_by_family["cash_workshop_purchases"].append(
        RuntimeOverlayRow(
            family="cash_workshop_purchases",
            stage="runtime_overlay",
            payload={
                "tracked_stats": tracked,
                "total_start_coin_level": start_total,
                "total_end_level": end_total,
                "total_expected_purchases": end_total - start_total,
            },
            provenance="ids:WS",
        )
    )

    free_attack = _required_resolved_value(gem_inputs, "free_attack_upgrade")
    free_defense = _required_resolved_value(gem_inputs, "free_defense_upgrade")
    free_utility = _required_resolved_value(gem_inputs, "free_utility_upgrade")
    if free_attack < 0.0 or free_defense < 0.0 or free_utility < 0.0:
        raise StaticV2ContractError("runtime_overlay_invalid_free_upgrade_chance")
    rows_by_family["free_upgrades"].append(
        RuntimeOverlayRow(
            family="free_upgrades",
            stage="runtime_overlay",
            payload={
                "attack": free_attack,
                "defense": free_defense,
                "utility": free_utility,
            },
            provenance="static_stage:baseline_gem_respec",
        )
    )

    rows_by_family["eals_realized_effect"].append(
        RuntimeOverlayRow(
            family="eals_realized_effect",
            stage="runtime_overlay",
            payload={
                "configured_skip_pct": _required_resolved_value(gem_inputs, "eals_pct"),
                "workshop_level": _required_workshop_level(snapshot, "Enemy Attack Level Skip"),
            },
            provenance="static_stage:baseline_gem_respec",
        )
    )
    rows_by_family["ehls_realized_effect"].append(
        RuntimeOverlayRow(
            family="ehls_realized_effect",
            stage="runtime_overlay",
            payload={
                "configured_skip_pct": _required_resolved_value(gem_inputs, "ehls_pct"),
                "workshop_level": _required_workshop_level(snapshot, "Enemy Health Level Skip"),
            },
            provenance="static_stage:baseline_gem_respec",
        )
    )

    return RuntimeOverlayMaterialization(order=overlay_order, by_family=rows_by_family)


def materialize_runtime_state(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeStateMaterialization:
    materialized = stage_materialization or materialize_static_stages(snapshot)
    overlay_materialized = overlays or materialize_runtime_overlays(
        snapshot,
        stage_materialization=materialized,
    )

    observed_stage_order = tuple(materialized.by_stage.keys())
    if observed_stage_order != REQUIRED_STATIC_STAGES:
        raise StaticV2ContractError(
            f"runtime_state_static_stage_order_unexpected:expected={REQUIRED_STATIC_STAGES}:observed={observed_stage_order}"
        )

    if overlay_materialized.order != REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        raise StaticV2ContractError("runtime_state_overlay_order_unexpected")

    unexpected_overlay_families = sorted(
        set(overlay_materialized.by_family.keys()) - set(REQUIRED_RUNTIME_OVERLAY_FAMILIES)
    )
    if unexpected_overlay_families:
        joined = ",".join(unexpected_overlay_families)
        raise StaticV2ContractError(f"runtime_state_unexpected_overlay_families:{joined}")

    flattened_rows: list[RuntimeOverlayRow] = []
    overlay_counts: dict[str, int] = {}
    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        rows = overlay_materialized.by_family.get(family)
        if rows is None:
            raise StaticV2ContractError(f"runtime_state_missing_overlay_family:{family}")
        if len(rows) == 0:
            raise StaticV2ContractError(f"runtime_state_empty_overlay_family:{family}")
        for row in rows:
            if row.family != family:
                raise StaticV2ContractError(
                    f"runtime_state_overlay_family_row_mismatch:{family}:{row.family}"
                )
            if row.stage != "runtime_overlay":
                raise StaticV2ContractError(
                    f"runtime_state_overlay_stage_unexpected:{family}:{row.stage}"
                )
        overlay_counts[family] = len(rows)
        flattened_rows.extend(rows)

    stage_stat_inputs_by_stage = {
        stage: tuple(inputs)
        for stage, inputs in materialized.by_stage.items()
    }

    stage_stat_values_by_stage = {
        stage: _group_stage_stat_values(inputs, stage=stage)
        for stage, inputs in materialized.by_stage.items()
    }

    return RuntimeStateMaterialization(
        static_stage_order=REQUIRED_STATIC_STAGES,
        stage_stat_inputs_by_stage=stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=stage_stat_values_by_stage,
        start_of_run_stat_inputs=stage_stat_inputs_by_stage["baseline_loadout"],
        start_of_run_stat_values=stage_stat_values_by_stage["baseline_loadout"],
        overlay_order=REQUIRED_RUNTIME_OVERLAY_FAMILIES,
        overlay_rows=tuple(flattened_rows),
        overlay_counts=overlay_counts,
    )


def build_runtime_execution_plan(
    runtime_state: RuntimeStateMaterialization,
) -> RuntimeExecutionPlan:
    if runtime_state.overlay_order != REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        raise StaticV2ContractError("runtime_execution_plan_overlay_order_unexpected")

    steps: list[RuntimeExecutionStep] = []
    counts: dict[str, int] = {family: 0 for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES}

    grouped_rows: dict[str, list[RuntimeOverlayRow]] = {
        family: [] for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES
    }
    for row in runtime_state.overlay_rows:
        if row.family not in grouped_rows:
            raise StaticV2ContractError(
                f"runtime_execution_plan_unexpected_overlay_row_family:{row.family}"
            )
        grouped_rows[row.family].append(row)

    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        rows = grouped_rows[family]
        if len(rows) == 0:
            raise StaticV2ContractError(
                f"runtime_execution_plan_missing_overlay_rows:{family}"
            )
        for idx, row in enumerate(rows, start=1):
            if row.stage != "runtime_overlay":
                raise StaticV2ContractError(
                    f"runtime_execution_plan_overlay_row_stage_unexpected:{family}:{row.stage}"
                )
            _validate_runtime_execution_overlay_row_payload(row)
            steps.append(
                RuntimeExecutionStep(
                    family=family,
                    row_index=idx,
                    stage=row.stage,
                    payload=row.payload,
                    provenance=row.provenance,
                )
            )
            counts[family] += 1

    return RuntimeExecutionPlan(
        ordered_steps=tuple(steps),
        per_family_step_counts=counts,
    )


def execute_runtime_state_pass(
    runtime_state: RuntimeStateMaterialization,
) -> RuntimeExecutionPassArtifact:
    if runtime_state.static_stage_order != REQUIRED_STATIC_STAGES:
        raise StaticV2ContractError(
            "runtime_execution_static_stage_order_unexpected"
        )

    if runtime_state.overlay_order != REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        raise StaticV2ContractError(
            "runtime_execution_overlay_order_unexpected"
        )

    observed_overlay_families = {row.family for row in runtime_state.overlay_rows}
    missing_overlay_families = [
        family
        for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES
        if family not in observed_overlay_families
    ]
    if missing_overlay_families:
        raise StaticV2ContractError(
            "runtime_execution_missing_overlay_families:"
            + ",".join(missing_overlay_families)
        )

    plan = build_runtime_execution_plan(runtime_state)
    row_counts = dict(plan.per_family_step_counts)

    if len(runtime_state.start_of_run_stat_inputs) == 0:
        raise StaticV2ContractError("runtime_execution_missing_start_of_run_inputs")

    if len(runtime_state.start_of_run_stat_values) == 0:
        raise StaticV2ContractError("runtime_execution_missing_start_of_run_values")

    input_counts_by_stat: dict[str, int] = {}
    for item in runtime_state.start_of_run_stat_inputs:
        input_counts_by_stat[item.stat_id] = input_counts_by_stat.get(item.stat_id, 0) + 1

    unexpected_start_value_stats = sorted(
        set(runtime_state.start_of_run_stat_values.keys()) - set(input_counts_by_stat.keys())
    )
    if unexpected_start_value_stats:
        raise StaticV2ContractError(
            "runtime_execution_unexpected_start_value_stats:"
            + ",".join(unexpected_start_value_stats)
        )

    totals: dict[str, float] = {}
    for stat_id, values in runtime_state.start_of_run_stat_values.items():
        if len(values) == 0:
            raise StaticV2ContractError(
                f"runtime_execution_empty_start_values:{stat_id}"
            )
        expected_count = input_counts_by_stat[stat_id]
        observed_count = len(values)
        if observed_count != expected_count:
            raise StaticV2ContractError(
                f"runtime_execution_start_value_count_mismatch:{stat_id}:inputs={expected_count}:values={observed_count}"
            )
        total = float(sum(values))
        if not math.isfinite(total):
            raise StaticV2ContractError(
                f"runtime_execution_non_finite_start_value:{stat_id}"
            )
        totals[stat_id] = total

    trace: list[str] = []
    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        count = runtime_state.overlay_counts.get(family)
        if count is None:
            raise StaticV2ContractError(
                f"runtime_execution_missing_overlay_count:{family}"
            )
        if count <= 0:
            raise StaticV2ContractError(
                f"runtime_execution_invalid_overlay_count:{family}:{count}"
            )
        observed_count = row_counts[family]
        if observed_count != count:
            raise StaticV2ContractError(
                f"runtime_execution_overlay_count_mismatch:{family}:counts={count}:rows={observed_count}"
            )
        trace.append(f"apply_overlay_family:{family}:rows={count}")

    if len(plan.ordered_steps) != sum(runtime_state.overlay_counts.values()):
        raise StaticV2ContractError("runtime_execution_plan_step_total_mismatch")

    return RuntimeExecutionPassArtifact(
        executed_overlay_order=REQUIRED_RUNTIME_OVERLAY_FAMILIES,
        start_of_run_stat_totals=totals,
        applied_overlay_counts={
            family: runtime_state.overlay_counts[family]
            for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES
        },
        execution_trace=tuple(trace),
    )


def _validate_runtime_execution_overlay_row_payload(row: RuntimeOverlayRow) -> None:
    if row.provenance.strip() == "":
        raise StaticV2ContractError(
            f"runtime_execution_overlay_row_missing_provenance:{row.family}"
        )

    payload = row.payload
    if row.family in {"perks", "battle_conditions"}:
        _validate_required_payload_number(
            payload,
            key="reference_rows",
            family=row.family,
            allow_zero=False,
        )
        return

    if row.family == "cash_workshop_purchases":
        _validate_required_payload_number(payload, key="tracked_stats", family=row.family, allow_zero=False)
        _validate_required_payload_number(payload, key="total_start_coin_level", family=row.family, allow_zero=True)
        _validate_required_payload_number(payload, key="total_end_level", family=row.family, allow_zero=True)
        purchases = _validate_required_payload_number(
            payload,
            key="total_expected_purchases",
            family=row.family,
            allow_zero=True,
        )
        if purchases < 0:
            raise StaticV2ContractError(
                f"runtime_execution_overlay_payload_negative_value:{row.family}:total_expected_purchases"
            )
        return

    if row.family == "free_upgrades":
        for key in ("attack", "defense", "utility"):
            _validate_required_payload_number(payload, key=key, family=row.family, allow_zero=True)
        return

    if row.family in {"eals_realized_effect", "ehls_realized_effect"}:
        _validate_required_payload_number(payload, key="configured_skip_pct", family=row.family, allow_zero=True)
        _validate_required_payload_number(payload, key="workshop_level", family=row.family, allow_zero=True)
        return

    raise StaticV2ContractError(f"runtime_execution_overlay_payload_unknown_family:{row.family}")


def _validate_required_payload_number(
    payload: Mapping[str, object],
    *,
    key: str,
    family: str,
    allow_zero: bool,
) -> float:
    value = payload.get(key)
    if value is None:
        raise StaticV2ContractError(
            f"runtime_execution_overlay_payload_missing_key:{family}:{key}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise StaticV2ContractError(
            f"runtime_execution_overlay_payload_non_finite:{family}:{key}"
        )
    if allow_zero:
        if number < 0:
            raise StaticV2ContractError(
                f"runtime_execution_overlay_payload_negative_value:{family}:{key}"
            )
    else:
        if number <= 0:
            raise StaticV2ContractError(
                f"runtime_execution_overlay_payload_non_positive:{family}:{key}"
            )
    return number


def materialize_and_execute_runtime_state(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeExecutionMaterialization:
    runtime_state = materialize_runtime_state(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    execution_pass = execute_runtime_state_pass(runtime_state)

    if execution_pass.executed_overlay_order != runtime_state.overlay_order:
        raise StaticV2ContractError("runtime_execution_materialization_overlay_order_mismatch")

    if execution_pass.applied_overlay_counts != runtime_state.overlay_counts:
        raise StaticV2ContractError("runtime_execution_materialization_overlay_count_mismatch")

    return RuntimeExecutionMaterialization(
        runtime_state=runtime_state,
        execution_pass=execution_pass,
    )


def materialize_runtime_execution_snapshot(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeExecutionSnapshot:
    execution_materialization = materialize_and_execute_runtime_state(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    runtime_state = execution_materialization.runtime_state
    execution_pass = execution_materialization.execution_pass
    plan = build_runtime_execution_plan(runtime_state)

    trace_from_plan = tuple(
        f"apply_overlay_family:{family}:rows={plan.per_family_step_counts[family]}"
        for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES
    )
    if execution_pass.execution_trace != trace_from_plan:
        raise StaticV2ContractError("runtime_execution_snapshot_trace_mismatch")

    overlay_numeric_totals_by_family = _sum_overlay_numeric_payload_values(plan)

    start_of_run_grand_total = float(sum(execution_pass.start_of_run_stat_totals.values()))
    if not math.isfinite(start_of_run_grand_total):
        raise StaticV2ContractError("runtime_execution_snapshot_non_finite_start_grand_total")

    return RuntimeExecutionSnapshot(
        plan=plan,
        execution_pass=execution_pass,
        overlay_numeric_totals_by_family=overlay_numeric_totals_by_family,
        start_of_run_grand_total=start_of_run_grand_total,
    )


def materialize_pre_combat_transition_artifact(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimePreCombatTransitionArtifact:
    execution_snapshot = materialize_runtime_execution_snapshot(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )

    plan = execution_snapshot.plan
    ordered_steps: list[RuntimePreCombatTransitionStep] = []
    transition_totals_by_family: dict[str, float] = {
        family: 0.0 for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES
    }

    for step in plan.ordered_steps:
        subtotal = _sum_numeric_values_from_payload(step.payload, family=step.family)
        if not math.isfinite(subtotal):
            raise StaticV2ContractError(
                f"runtime_pre_combat_transition_non_finite_step_total:{step.family}:{step.row_index}"
            )
        ordered_steps.append(
            RuntimePreCombatTransitionStep(
                family=step.family,
                row_index=step.row_index,
                numeric_payload_total=subtotal,
            )
        )
        transition_totals_by_family[step.family] += subtotal

    if len(ordered_steps) != len(plan.ordered_steps):
        raise StaticV2ContractError("runtime_pre_combat_transition_step_count_mismatch")

    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        expected = execution_snapshot.overlay_numeric_totals_by_family[family]
        observed = transition_totals_by_family[family]
        if not math.isclose(expected, observed, rel_tol=0.0, abs_tol=1e-9):
            raise StaticV2ContractError(
                f"runtime_pre_combat_transition_family_total_mismatch:{family}:expected={expected}:observed={observed}"
            )

    return RuntimePreCombatTransitionArtifact(
        start_of_run_grand_total=execution_snapshot.start_of_run_grand_total,
        transition_totals_by_family=transition_totals_by_family,
        ordered_transition_steps=tuple(ordered_steps),
    )


def materialize_runtime_state_transition_artifact(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeStateTransitionArtifact:
    pre_combat = materialize_pre_combat_transition_artifact(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )

    ordered_steps = pre_combat.ordered_transition_steps
    expected_family_idx = {family: idx for idx, family in enumerate(REQUIRED_RUNTIME_OVERLAY_FAMILIES)}

    last_family_order = -1
    row_index_by_family: dict[str, int] = {family: 0 for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES}
    applied_totals_by_family: dict[str, float] = {family: 0.0 for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES}

    cumulative_total = float(pre_combat.start_of_run_grand_total)
    if not math.isfinite(cumulative_total):
        raise StaticV2ContractError("runtime_state_transition_non_finite_start_total")

    out_steps: list[RuntimeStateTransitionStep] = []
    for step in ordered_steps:
        family_order = expected_family_idx.get(step.family)
        if family_order is None:
            raise StaticV2ContractError(
                f"runtime_state_transition_unknown_family:{step.family}"
            )
        if family_order < last_family_order:
            raise StaticV2ContractError(
                f"runtime_state_transition_family_order_mismatch:{step.family}"
            )
        last_family_order = family_order

        expected_row_index = row_index_by_family[step.family] + 1
        if step.row_index != expected_row_index:
            raise StaticV2ContractError(
                f"runtime_state_transition_row_index_mismatch:{step.family}:expected={expected_row_index}:observed={step.row_index}"
            )
        row_index_by_family[step.family] = step.row_index

        input_total = float(step.numeric_payload_total)
        if not math.isfinite(input_total):
            raise StaticV2ContractError(
                f"runtime_state_transition_non_finite_step_total:{step.family}:{step.row_index}"
            )

        cumulative_total += input_total
        if not math.isfinite(cumulative_total):
            raise StaticV2ContractError("runtime_state_transition_non_finite_cumulative_total")

        applied_totals_by_family[step.family] += input_total
        out_steps.append(
            RuntimeStateTransitionStep(
                family=step.family,
                row_index=step.row_index,
                input_total=input_total,
                cumulative_total=cumulative_total,
            )
        )

    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        expected = float(pre_combat.transition_totals_by_family[family])
        observed = applied_totals_by_family[family]
        if not math.isclose(expected, observed, rel_tol=0.0, abs_tol=1e-9):
            raise StaticV2ContractError(
                f"runtime_state_transition_family_total_mismatch:{family}:expected={expected}:observed={observed}"
            )

    return RuntimeStateTransitionArtifact(
        start_of_run_grand_total=float(pre_combat.start_of_run_grand_total),
        final_pre_combat_total=cumulative_total,
        ordered_steps=tuple(out_steps),
        applied_totals_by_family=applied_totals_by_family,
    )


def materialize_runtime_transition_checkpoint(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeTransitionCheckpoint:
    transition = materialize_runtime_state_transition_artifact(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )

    total_delta = float(sum(transition.applied_totals_by_family.values()))
    if not math.isfinite(total_delta):
        raise StaticV2ContractError("runtime_transition_checkpoint_non_finite_total_delta")

    expected_final = transition.start_of_run_grand_total + total_delta
    if not math.isfinite(expected_final):
        raise StaticV2ContractError("runtime_transition_checkpoint_non_finite_expected_final")

    if not math.isclose(
        expected_final,
        transition.final_pre_combat_total,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise StaticV2ContractError(
            "runtime_transition_checkpoint_final_total_mismatch:"
            f"expected={expected_final}:observed={transition.final_pre_combat_total}"
        )

    last_total = transition.start_of_run_grand_total
    for step in transition.ordered_steps:
        if step.cumulative_total < last_total:
            raise StaticV2ContractError(
                f"runtime_transition_checkpoint_non_monotonic_cumulative_total:{step.family}:{step.row_index}"
            )
        last_total = step.cumulative_total

    return RuntimeTransitionCheckpoint(
        transition=transition,
        expected_final_pre_combat_total=expected_final,
        total_delta_from_start=total_delta,
    )


def materialize_runtime_pre_combat_balance_sheet(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimePreCombatBalanceSheet:
    checkpoint = materialize_runtime_transition_checkpoint(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )

    transition = checkpoint.transition
    ordered_pairs: list[tuple[str, float]] = []
    for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES:
        value = transition.applied_totals_by_family.get(family)
        if value is None:
            raise StaticV2ContractError(
                f"runtime_pre_combat_balance_sheet_missing_family_delta:{family}"
            )
        number = float(value)
        if not math.isfinite(number):
            raise StaticV2ContractError(
                f"runtime_pre_combat_balance_sheet_non_finite_family_delta:{family}"
            )
        ordered_pairs.append((family, number))

    recomputed_delta = float(sum(value for _, value in ordered_pairs))
    if not math.isclose(recomputed_delta, checkpoint.total_delta_from_start, rel_tol=0.0, abs_tol=1e-9):
        raise StaticV2ContractError(
            "runtime_pre_combat_balance_sheet_delta_mismatch:"
            f"expected={checkpoint.total_delta_from_start}:observed={recomputed_delta}"
        )

    final_total = transition.start_of_run_grand_total + recomputed_delta
    if not math.isclose(final_total, transition.final_pre_combat_total, rel_tol=0.0, abs_tol=1e-9):
        raise StaticV2ContractError(
            "runtime_pre_combat_balance_sheet_final_total_mismatch:"
            f"expected={transition.final_pre_combat_total}:observed={final_total}"
        )

    return RuntimePreCombatBalanceSheet(
        start_total=transition.start_of_run_grand_total,
        final_total=final_total,
        total_delta=recomputed_delta,
        family_deltas_in_order=tuple(ordered_pairs),
    )


def materialize_runtime_execution_phase_bundle(
    snapshot: AccountSnapshot,
    *,
    stage_materialization: StageMaterialization | None = None,
    overlays: RuntimeOverlayMaterialization | None = None,
) -> RuntimeExecutionPhaseBundle:
    static_stage_audit = audit_static_stage_baselines(
        snapshot,
        stage_materialization=stage_materialization,
    )
    runtime_state = materialize_runtime_state(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    execution_plan = build_runtime_execution_plan(runtime_state)
    execution_pass = execute_runtime_state_pass(runtime_state)
    execution_snapshot = materialize_runtime_execution_snapshot(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    pre_combat_transition = materialize_pre_combat_transition_artifact(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    runtime_state_transition = materialize_runtime_state_transition_artifact(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    transition_checkpoint = materialize_runtime_transition_checkpoint(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )
    pre_combat_balance_sheet = materialize_runtime_pre_combat_balance_sheet(
        snapshot,
        stage_materialization=stage_materialization,
        overlays=overlays,
    )

    if execution_plan.per_family_step_counts != runtime_state.overlay_counts:
        raise StaticV2ContractError("runtime_phase_bundle_plan_count_mismatch")

    if execution_pass.applied_overlay_counts != runtime_state.overlay_counts:
        raise StaticV2ContractError("runtime_phase_bundle_pass_count_mismatch")

    if execution_snapshot.execution_pass != execution_pass:
        raise StaticV2ContractError("runtime_phase_bundle_snapshot_pass_mismatch")

    if transition_checkpoint.transition != runtime_state_transition:
        raise StaticV2ContractError("runtime_phase_bundle_checkpoint_transition_mismatch")

    if not math.isclose(
        pre_combat_balance_sheet.final_total,
        transition_checkpoint.expected_final_pre_combat_total,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise StaticV2ContractError("runtime_phase_bundle_final_total_mismatch")

    return RuntimeExecutionPhaseBundle(
        static_stage_audit=static_stage_audit,
        runtime_state=runtime_state,
        execution_plan=execution_plan,
        execution_pass=execution_pass,
        execution_snapshot=execution_snapshot,
        pre_combat_transition=pre_combat_transition,
        runtime_state_transition=runtime_state_transition,
        transition_checkpoint=transition_checkpoint,
        pre_combat_balance_sheet=pre_combat_balance_sheet,
    )


def _sum_overlay_numeric_payload_values(
    plan: RuntimeExecutionPlan,
) -> Mapping[str, float]:
    totals: dict[str, float] = {family: 0.0 for family in REQUIRED_RUNTIME_OVERLAY_FAMILIES}
    for step in plan.ordered_steps:
        family_total = totals.get(step.family)
        if family_total is None:
            raise StaticV2ContractError(
                f"runtime_execution_snapshot_unknown_plan_family:{step.family}"
            )
        subtotal = _sum_numeric_values_from_payload(step.payload, family=step.family)
        totals[step.family] = family_total + subtotal
    return totals


def _sum_numeric_values_from_payload(
    payload: Mapping[str, object],
    *,
    family: str,
) -> float:
    subtotal = 0.0
    for value in payload.values():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            number = float(value)
            if not math.isfinite(number):
                raise StaticV2ContractError(
                f"runtime_execution_snapshot_non_finite_overlay_payload:{family}"
            )
            subtotal += number
    return subtotal


def _group_stage_stat_values(
    inputs: list[StatInput],
    *,
    stage: str,
) -> Mapping[str, tuple[float, ...]]:
    grouped: dict[str, list[float]] = {}
    for item in inputs:
        if item.phase != Phase.START_OF_RUN:
            raise StaticV2ContractError(
                f"runtime_state_unexpected_phase:{stage}:{item.stat_id}:{item.phase.value}"
            )
        base = float(item.base_value or 0.0)
        delta = float(item.loadout_delta or 0.0)
        mult = float(item.enhancement_multiplier or 1.0)
        value = (base + delta) * mult
        if not math.isfinite(value):
            raise StaticV2ContractError(
                f"runtime_state_non_finite_value:{stage}:{item.stat_id}"
            )
        grouped.setdefault(item.stat_id, []).append(value)
    return {stat_id: tuple(values) for stat_id, values in grouped.items()}


def _with_explicit_contributor_families(
    stat_inputs: list[StatInput],
    *,
    stage: str,
) -> list[StatInput]:
    out: list[StatInput] = []
    for item in stat_inputs:
        if item.contributor_family is not None:
            out.append(item)
            continue
        provenance = (item.provenance or "").strip()
        if provenance == "":
            raise StaticV2ContractError(f"stage_materialization_missing_provenance:{stage}:{item.stat_id}")

        prefix = provenance.split(":", 1)[0]
        if prefix in _DEFAULT_PROVENANCE_PREFIXES:
            out.append(item)
            continue

        family = _PROVENANCE_PREFIX_TO_FAMILY.get(prefix)
        if family is None:
            raise StaticV2ContractError(
                f"stage_materialization_unknown_provenance_prefix:{stage}:{prefix}"
            )
        out.append(replace(item, contributor_family=family))
    return out


def _validate_stage_inputs_against_bridge(
    stage_bridge_by_family: Mapping[str, Mapping[str, object]],
    *,
    snapshot: AccountSnapshot,
    stage: str,
    stat_inputs: list[StatInput],
) -> tuple[str, ...]:
    families_seen: set[str] = set()

    for item in stat_inputs:
        family = item.contributor_family
        if family is None:
            continue

        bridge_row = stage_bridge_by_family.get(family)
        if bridge_row is None:
            raise StaticV2ContractError(f"stage_materialization_missing_bridge_family:{family}")

        stage_applicability = bridge_row.get("stage_applicability")
        allowed = [str(value).strip() for value in stage_applicability] if isinstance(stage_applicability, list) else []
        if not _is_family_allowed_for_stage(stage, allowed):
            raise StaticV2ContractError(
                f"stage_materialization_family_not_allowed:{stage}:{family}:{item.stat_id}"
            )

        selector = str(bridge_row.get("loadout_selection_field", "")).strip()
        if selector:
            if not hasattr(snapshot, selector):
                raise StaticV2ContractError(
                    f"stage_materialization_missing_loadout_selector:{stage}:{family}:{selector}"
                )
            if stage != "baseline_loadout":
                raise StaticV2ContractError(
                    f"stage_materialization_loadout_family_in_non_loadout_stage:{stage}:{family}"
                )
        families_seen.add(family)

    return tuple(sorted(families_seen))


def _is_family_allowed_for_stage(stage: str, family_stages: list[str]) -> bool:
    if stage not in REQUIRED_STATIC_STAGES:
        return False
    stage_index = REQUIRED_STATIC_STAGES.index(stage)
    for candidate in family_stages:
        if candidate not in REQUIRED_STATIC_STAGES:
            continue
        if REQUIRED_STATIC_STAGES.index(candidate) <= stage_index:
            return True
    return False


def _count_data_rows(path: Path) -> int:
    if not path.exists():
        raise StaticV2ContractError(f"runtime_overlay_missing_table:{path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    return max(0, len(rows) - 1)


def _required_resolved_value(inputs: list[StatInput], stat_id: str) -> float:
    for item in inputs:
        if item.stat_id != stat_id:
            continue
        base = float(item.base_value or 0.0)
        delta = float(item.loadout_delta or 0.0)
        mult = float(item.enhancement_multiplier or 1.0)
        return (base + delta) * mult
    raise StaticV2ContractError(f"runtime_overlay_missing_required_stat:{stat_id}")


def _required_workshop_level(snapshot: AccountSnapshot, name: str) -> int:
    entry = snapshot.workshop.get(name)
    if entry is None or entry.coin_level is None:
        raise StaticV2ContractError(f"runtime_overlay_missing_workshop_level:{name}")
    return int(entry.coin_level)
