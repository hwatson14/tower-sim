from __future__ import annotations

from dataclasses import dataclass
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


REQUIRED_STATIC_STAGES = (
    "baseline_account",
    "baseline_gem_respec",
    "baseline_loadout",
)


# Phase A note:
# This module is intentionally limited to static stage materialization and registry guardrails.
# It is provisional and non-authoritative for full contributor emission or resolution semantics
# until Phase C/Phase D implementation lands under the V2 master spec.

def required_static_stages() -> tuple[str, ...]:
    return REQUIRED_STATIC_STAGES


def validate_required_stages_present() -> None:
    contract = load_static_v2_contract()
    observed = tuple(contract.required_static_stage_order)
    if observed != REQUIRED_STATIC_STAGES:
        raise StaticV2ContractError(
            f"required_stage_order_mismatch:expected={REQUIRED_STATIC_STAGES}:observed={observed}"
        )


def materialize_static_stages(snapshot: AccountSnapshot) -> StageMaterialization:
    validate_required_stages_present()

    baseline_account = compile_baseline_account_stat_inputs(snapshot)
    baseline_gem_respec = compile_baseline_gem_respec_stat_inputs(snapshot)
    baseline_loadout = compile_baseline_loadout_stat_inputs(snapshot)

    return StageMaterialization(
        by_stage={
            "baseline_account": list(baseline_account.stat_inputs),
            "baseline_gem_respec": list(baseline_gem_respec.stat_inputs),
            "baseline_loadout": list(baseline_loadout.stat_inputs),
        },
        missing={
            "baseline_account": list(baseline_account.missing),
            "baseline_gem_respec": list(baseline_gem_respec.missing),
            "baseline_loadout": list(baseline_loadout.missing),
        },
    )
