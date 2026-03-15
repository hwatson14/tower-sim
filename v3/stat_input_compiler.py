"""v3 Phase-2 stat input compiler with KB naming-contract validation.

This module composes the existing deterministic stat-input compiler surfaces and
adds fail-closed validation against canonical KB contracts loaded through a
single KB accessor.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import Iterable, Literal

import yaml

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import (
    CompiledBaselineLoadout,
    CompiledStatInputs,
    compile_baseline_account_stat_inputs,
    compile_baseline_gem_respec_stat_inputs,
    compile_baseline_loadout_stat_inputs,
    compile_full_stat_inputs,
)
from tower_sim.registry.stat_registry import default_registry
from tower_sim.util.account_snapshot import AccountSnapshot
from v3.kb_access import content_sha256, load_yaml

_NAMING_CONTRACT_IN_KB = "kb/global-rules/contracts/naming-contract.yaml"
_LOCK_PATH = Path("v3/kb_contract_lock.yaml")
_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Provenance-prefix -> KB naming-contract contributor source_section
_PROVENANCE_SOURCE_MAP = {
    "workshop_table": "workshop",
    "workshop_formula": "workshop",
    "workshop_alias": "workshop",
    "uw_section": "uw_upgrade",
    "uw_alias": "uw_upgrade",
    "relics": "relic",
    "bot_table": "bot_upgrade",
    "base": "unlock",  # identity/default seed rows
    "modules": "module",
    "cards": "card",
}


class V3StatInputCompilerError(RuntimeError):
    pass


@dataclass(frozen=True)
class V3CompiledStatInputs:
    stat_inputs: list[StatInput]
    missing: list[str]


@dataclass(frozen=True)
class V3CompiledBaselineLoadout:
    stat_inputs: list[StatInput]
    missing: list[str]
    module_contribution_ledger: list[dict[str, object]]
    layer_gaps: list[str]


def _load_kb_naming_contract() -> dict:
    data = load_yaml(_NAMING_CONTRACT_IN_KB)
    if data.get("kind") != "naming_contract":
        raise V3StatInputCompilerError("KB naming contract kind mismatch.")
    return data


def _load_contract_lock() -> dict[str, str]:
    payload = yaml.safe_load(_LOCK_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise V3StatInputCompilerError("KB contract lock is not a mapping.")
    contracts = payload.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise V3StatInputCompilerError("KB contract lock missing contracts mapping.")
    return {str(k): str(v) for k, v in contracts.items()}


def _validate_contract_hash_lock() -> None:
    expected = _load_contract_lock()
    drift: list[str] = []
    for rel_path, expected_hash in expected.items():
        observed = content_sha256(rel_path)
        if observed != expected_hash:
            drift.append(f"{rel_path}:expected={expected_hash}:observed={observed}")
    if drift:
        raise V3StatInputCompilerError("KB contract hash drift detected: " + ", ".join(drift))


def _allowed_source_sections_from_kb(contract: dict) -> set[str]:
    section_def = (
        contract.get("sections", {})
        .get("contributor_id", {})
        .get("section_definitions", {})
        .get("source_section", "")
    )
    if not isinstance(section_def, str) or section_def.strip() == "":
        raise V3StatInputCompilerError("KB naming contract missing contributor source_section definition.")

    section_csv = section_def
    if "such as" in section_def:
        section_csv = section_def.split("such as", 1)[1]
    allowed = {
        token.strip().replace(" ", "_")
        for token in section_csv.split(",")
        if token.strip()
    }
    if not allowed:
        raise V3StatInputCompilerError("KB naming contract yielded no contributor source sections.")
    return allowed


def _infer_contributor_family(item: StatInput) -> str:
    if item.contributor_family and item.contributor_family.strip():
        return item.contributor_family.strip()
    prefix = (item.provenance or "").split(":", 1)[0].strip()
    mapped = _PROVENANCE_SOURCE_MAP.get(prefix)
    if mapped:
        return mapped
    raise V3StatInputCompilerError(
        f"Unable to infer contributor_family for stat input {item.stat_id!r} provenance={item.provenance!r}."
    )


def _enrich_contributor_families(stat_inputs: Iterable[StatInput]) -> list[StatInput]:
    enriched: list[StatInput] = []
    for item in stat_inputs:
        family = _infer_contributor_family(item)
        enriched.append(replace(item, contributor_family=family))
    return enriched


def validate_compiled_stat_inputs(
    stat_inputs: Iterable[StatInput],
) -> None:
    _validate_contract_hash_lock()
    contract = _load_kb_naming_contract()
    allowed_sources = _allowed_source_sections_from_kb(contract)
    registry = default_registry()

    errors: list[str] = []
    for item in stat_inputs:
        if not _SNAKE_CASE_RE.fullmatch(item.stat_id):
            errors.append(f"stat_id_not_snake_case:{item.stat_id}")
            continue

        try:
            registry.get(item.stat_id)
        except KeyError:
            errors.append(f"unknown_stat_id:{item.stat_id}")

        if not item.provenance or item.provenance.strip() == "":
            errors.append(f"missing_provenance:{item.stat_id}")

        source = (item.contributor_family or "").strip()
        if source == "":
            errors.append(f"missing_contributor_family:{item.stat_id}")
        elif source not in allowed_sources:
            errors.append(f"unknown_contributor_source_section:{item.stat_id}:{source}")

    if errors:
        unique = sorted(set(errors))
        raise V3StatInputCompilerError(
            "KB naming-contract validation failed for compiled stat inputs: "
            + ", ".join(unique[:20])
            + (" ..." if len(unique) > 20 else "")
        )


def _wrap_and_validate(compiled: CompiledStatInputs) -> V3CompiledStatInputs:
    enriched = _enrich_contributor_families(compiled.stat_inputs)
    validate_compiled_stat_inputs(enriched)
    return V3CompiledStatInputs(
        stat_inputs=enriched,
        missing=list(compiled.missing),
    )


def compile_v3_stat_inputs(
    snapshot: AccountSnapshot,
    *,
    stage: Literal["baseline_account", "baseline_gem_respec", "full"] = "baseline_gem_respec",
) -> V3CompiledStatInputs:
    if stage == "baseline_account":
        compiled = compile_baseline_account_stat_inputs(snapshot)
    elif stage == "baseline_gem_respec":
        compiled = compile_baseline_gem_respec_stat_inputs(snapshot)
    elif stage == "full":
        compiled = compile_full_stat_inputs(snapshot)
    else:
        raise V3StatInputCompilerError(f"Unsupported stage: {stage}")

    return _wrap_and_validate(compiled)


def compile_v3_baseline_loadout_stat_inputs(
    snapshot: AccountSnapshot,
    *,
    module_context: str = "Farming",
    selected_cards: Iterable[str] | None = None,
) -> V3CompiledBaselineLoadout:
    compiled: CompiledBaselineLoadout = compile_baseline_loadout_stat_inputs(
        snapshot,
        module_context=module_context,
        selected_cards=selected_cards,
    )
    enriched = _enrich_contributor_families(compiled.stat_inputs)
    validate_compiled_stat_inputs(enriched)
    return V3CompiledBaselineLoadout(
        stat_inputs=enriched,
        missing=list(compiled.missing),
        module_contribution_ledger=list(compiled.module_contribution_ledger),
        layer_gaps=list(compiled.layer_gaps),
    )
