from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import (
    compile_baseline_account_stat_inputs,
    compile_baseline_gem_respec_stat_inputs,
    compile_baseline_loadout_stat_inputs,
)
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
