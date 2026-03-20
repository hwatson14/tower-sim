from __future__ import annotations

from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from tower_sim.util.account_snapshot import AccountSnapshot

import yaml


class StaticV2ContractError(RuntimeError):
    pass


_REGISTRY_ROOT = Path("tables/meta/registry/v2")
_CANONICAL_TARGET_STATS_PATH = _REGISTRY_ROOT / "canonical_target_stats.yaml"
_MECHANIC_PARAMETERS_PATH = _REGISTRY_ROOT / "mechanic_parameters.yaml"
_ENVIRONMENT_PARAMETERS_PATH = _REGISTRY_ROOT / "environment_parameters.yaml"
_CAPABILITIES_PATH = _REGISTRY_ROOT / "capabilities.yaml"
_CONTRIBUTORS_PATH = _REGISTRY_ROOT / "contributors.yaml"
_ALIASES_PATH = _REGISTRY_ROOT / "aliases.yaml"
_STAGES_PATH = _REGISTRY_ROOT / "stages.yaml"
_RUNTIME_DOMAINS_PATH = _REGISTRY_ROOT / "runtime_domains.yaml"
_SOURCE_STATE_SCHEMA_PATH = _REGISTRY_ROOT / "source_state_schema.yaml"
_CONTRIBUTOR_OPERATIONS_PATH = _REGISTRY_ROOT / "contributor_operations.yaml"
_COMPOSITE_DEPENDENCIES_PATH = _REGISTRY_ROOT / "composite_dependencies.yaml"
_QUARANTINE_REGISTRY_PATH = _REGISTRY_ROOT / "quarantine_registry.yaml"
_IDS_SECTION_ROUTING_PATH = Path("kb/global-rules/contracts/ids-section-routing.yaml")

_PHASE_B_SOURCE_COVERAGE_PATH = Path("audit/static_pipeline_v2_phase_b_source_state_coverage.yaml")
_PHASE_B_TARGET_CROSSWALK_PATH = Path("audit/static_pipeline_v2_phase_b_target_stat_crosswalk.yaml")
_PHASE_B_CONTRIBUTOR_CROSSWALK_PATH = Path("audit/static_pipeline_v2_phase_b_contributor_crosswalk.yaml")

_FORBIDDEN_CANONICAL_CONTRIBUTOR_PREFIXES = (
    "legacy_stage__",
    "resolved__",
    "helper__",
)

_REQUIRED_CONTRIBUTOR_FIELDS = (
    "contributor_id",
    "contributor_family",
    "owned_target_stat",
    "destination_object_class",
    "operation_class",
    "stage_applicability",
    "ownership_role",
    "canonical_status",
    "migration_status",
)

_CONTRIBUTOR_ID_SECTION_SEPARATOR = "__"


@dataclass(frozen=True)
class StaticV2Contract:
    canonical_target_stats: frozenset[str]
    runtime_mechanic_parameters: frozenset[str]
    environment_parameters: frozenset[str]
    capabilities: frozenset[str]
    canonical_object_ids: frozenset[str]
    canonical_contributor_ids: frozenset[str]
    legacy_to_canonical_aliases: Mapping[str, str]
    required_static_stage_order: tuple[str, ...]
    static_runtime_deny_list: frozenset[str]
    composite_targets: frozenset[str]
    quarantined_contributor_ids: frozenset[str]
    bridge_contributor_families: frozenset[str]
    stage_bridge_by_family: Mapping[str, Mapping[str, object]]
    required_runtime_overlay_order: tuple[str, ...]

    def resolve_legacy_alias(self, candidate: str) -> str:
        value = candidate.strip()
        return self.legacy_to_canonical_aliases.get(value, value)

    def resolve_target_stat(self, candidate: str) -> str:
        resolved = self.resolve_legacy_alias(candidate)
        if resolved in self.static_runtime_deny_list:
            raise StaticV2ContractError(f"runtime_field_not_allowed_in_static_core:{resolved}")
        if resolved not in self.canonical_target_stats:
            raise StaticV2ContractError(f"unknown_target_stat:{candidate}")
        return resolved

    def validate_canonical_contributor_id(self, contributor_id: str) -> None:
        value = contributor_id.strip()
        for prefix in _FORBIDDEN_CANONICAL_CONTRIBUTOR_PREFIXES:
            if value.startswith(prefix):
                raise StaticV2ContractError(
                    f"fabricated_canonical_contributor_id_forbidden:{contributor_id}"
                )
        if value not in self.canonical_contributor_ids:
            raise StaticV2ContractError(f"unknown_canonical_contributor_id:{contributor_id}")


@lru_cache(maxsize=1)
def load_static_v2_contract() -> StaticV2Contract:
    canonical_targets_doc = _load_yaml(_CANONICAL_TARGET_STATS_PATH)
    mechanics_doc = _load_yaml(_MECHANIC_PARAMETERS_PATH)
    environment_doc = _load_yaml(_ENVIRONMENT_PARAMETERS_PATH)
    capabilities_doc = _load_yaml(_CAPABILITIES_PATH)
    contributors_doc = _load_yaml(_CONTRIBUTORS_PATH)
    aliases_doc = _load_yaml(_ALIASES_PATH)
    stages_doc = _load_yaml(_STAGES_PATH)
    runtime_doc = _load_yaml(_RUNTIME_DOMAINS_PATH)
    source_schema_doc = _load_yaml(_SOURCE_STATE_SCHEMA_PATH)
    operations_doc = _load_yaml(_CONTRIBUTOR_OPERATIONS_PATH)
    composite_doc = _load_yaml(_COMPOSITE_DEPENDENCIES_PATH)
    quarantine_doc = _load_yaml(_QUARANTINE_REGISTRY_PATH)

    _validate_source_schema(source_schema_doc)
    allowed_operations = _validate_operations_registry(operations_doc)

    canonical_targets = _load_named_registry_list(
        canonical_targets_doc,
        key="v2_canonical_target_stats",
        error_code="registry_invalid:v2_canonical_target_stats",
    )
    mechanic_parameters = _load_named_registry_list(
        mechanics_doc,
        key="v2_mechanic_parameters",
        error_code="registry_invalid:v2_mechanic_parameters",
    )
    environment_parameters = _load_named_registry_list(
        environment_doc,
        key="v2_environment_parameters",
        error_code="registry_invalid:v2_environment_parameters",
    )
    capabilities = _load_named_registry_list(
        capabilities_doc,
        key="v2_capabilities",
        error_code="registry_invalid:v2_capabilities",
    )

    _ensure_disjoint_registry_classes(
        canonical_targets=canonical_targets,
        mechanic_parameters=mechanic_parameters,
        environment_parameters=environment_parameters,
        capabilities=capabilities,
    )
    canonical_object_ids = (
        canonical_targets
        | mechanic_parameters
        | environment_parameters
        | capabilities
    )

    contributor_rows = contributors_doc.get("v2_contributor_ids")
    if not isinstance(contributor_rows, list):
        raise StaticV2ContractError("registry_invalid:v2_contributor_ids")
    contributor_ids: list[str] = []
    for row in contributor_rows:
        if not isinstance(row, dict):
            raise StaticV2ContractError("registry_invalid:contributor_row_not_mapping")
        _validate_contributor_row(
            row,
            canonical_targets=canonical_object_ids,
            canonical_target_stats=canonical_targets,
            mechanic_parameters=mechanic_parameters,
            environment_parameters=environment_parameters,
            capabilities=capabilities,
            allowed_operations=allowed_operations,
        )
        contributor_ids.append(str(row["contributor_id"]).strip())

    alias_map = aliases_doc.get("v2_alias_map")
    if not isinstance(alias_map, dict):
        raise StaticV2ContractError("registry_invalid:v2_alias_map")
    direction = str(aliases_doc.get("direction", "")).strip()
    if direction != "legacy_to_canonical_only":
        raise StaticV2ContractError("alias_direction_must_be_legacy_to_canonical_only")
    for legacy, canonical in alias_map.items():
        legacy_name = str(legacy).strip()
        canonical_name = str(canonical).strip()
        if legacy_name in canonical_targets:
            raise StaticV2ContractError(
                f"alias_direction_violation_canonical_key:{legacy_name}"
            )
        if canonical_name not in canonical_object_ids:
            raise StaticV2ContractError(
                f"alias_points_to_unknown_canonical_target:{canonical_name}"
            )

    stage_root = stages_doc.get("v2_stage_applicability")
    if not isinstance(stage_root, dict):
        raise StaticV2ContractError("registry_invalid:v2_stage_applicability")
    required_stage_order = stage_root.get("required_static_stage_order")
    if not isinstance(required_stage_order, list):
        raise StaticV2ContractError("registry_invalid:required_static_stage_order")
    static_stages = stage_root.get("static_stages")
    if not isinstance(static_stages, list):
        raise StaticV2ContractError("registry_invalid:static_stages")
    runtime_overlay_stage = str(stage_root.get("runtime_overlay_stage", "")).strip()
    if runtime_overlay_stage != "runtime_overlay":
        raise StaticV2ContractError("registry_invalid:runtime_overlay_stage")

    runtime_overlay_families = stage_root.get("runtime_overlay_families")
    if not isinstance(runtime_overlay_families, list):
        raise StaticV2ContractError("registry_invalid:runtime_overlay_families")
    required_runtime_overlay_order = stage_root.get("required_runtime_overlay_order")
    if not isinstance(required_runtime_overlay_order, list):
        raise StaticV2ContractError("registry_invalid:required_runtime_overlay_order")

    runtime_root = runtime_doc.get("v2_runtime_field_registry")
    if not isinstance(runtime_root, dict):
        raise StaticV2ContractError("registry_invalid:v2_runtime_field_registry")
    deny_list = runtime_root.get("static_reject_if_seen")
    if not isinstance(deny_list, list):
        raise StaticV2ContractError("registry_invalid:static_reject_if_seen")

    composite_entries = composite_doc.get("v2_composite_dependencies")
    if not isinstance(composite_entries, list):
        raise StaticV2ContractError("registry_invalid:v2_composite_dependencies")
    composite_targets = _validate_composite_entries(
        composite_entries,
            canonical_targets=canonical_object_ids,
        )

    quarantine_root = quarantine_doc.get("v2_quarantine_registry")
    if not isinstance(quarantine_root, dict):
        raise StaticV2ContractError("registry_invalid:v2_quarantine_registry")
    quarantined_contributor_ids = _validate_quarantine_registry(quarantine_root)

    contributor_families = frozenset(
        str(row["contributor_family"]).strip() for row in contributor_rows
    )
    bridge_families, stage_bridge_by_family = _validate_stage_applicability_bridge(
        stage_root,
        contributor_families=contributor_families,
        static_stage_order=tuple(str(stage).strip() for stage in required_stage_order),
        contributor_rows=contributor_rows,
    )

    declared_overlay_families: list[str] = []
    for row in runtime_overlay_families:
        if not isinstance(row, dict):
            raise StaticV2ContractError("registry_invalid:runtime_overlay_family_row")
        family = str(row.get("family", "")).strip()
        if not family:
            raise StaticV2ContractError("registry_invalid:runtime_overlay_family_name")
        declared_overlay_families.append(family)
    normalized_required_overlay = [str(value).strip() for value in required_runtime_overlay_order]
    if tuple(declared_overlay_families) != tuple(normalized_required_overlay):
        raise StaticV2ContractError("registry_invalid:runtime_overlay_order_mismatch")

    return StaticV2Contract(
        canonical_target_stats=canonical_targets,
        runtime_mechanic_parameters=mechanic_parameters,
        environment_parameters=environment_parameters,
        capabilities=capabilities,
        canonical_object_ids=canonical_object_ids,
        canonical_contributor_ids=frozenset(contributor_ids),
        legacy_to_canonical_aliases={
            str(key).strip(): str(value).strip() for key, value in alias_map.items()
        },
        required_static_stage_order=tuple(str(stage).strip() for stage in required_stage_order),
        static_runtime_deny_list=frozenset(str(item).strip() for item in deny_list),
        composite_targets=composite_targets,
        quarantined_contributor_ids=quarantined_contributor_ids,
        bridge_contributor_families=bridge_families,
        stage_bridge_by_family=stage_bridge_by_family,
        required_runtime_overlay_order=tuple(str(value).strip() for value in required_runtime_overlay_order),
    )


def validate_phase_b_stat_coverage() -> dict:
    contract = load_static_v2_contract()
    source_cov_doc = _load_yaml(_PHASE_B_SOURCE_COVERAGE_PATH)
    target_cross_doc = _load_yaml(_PHASE_B_TARGET_CROSSWALK_PATH)
    contributor_cross_doc = _load_yaml(_PHASE_B_CONTRIBUTOR_CROSSWALK_PATH)
    quarantine_doc = _load_yaml(_QUARANTINE_REGISTRY_PATH)

    source_cov = source_cov_doc.get("phase_b_source_state_coverage")
    if not isinstance(source_cov, dict):
        raise StaticV2ContractError("phase_b_invalid:source_state_coverage")
    families = source_cov.get("families")
    if not isinstance(families, list):
        raise StaticV2ContractError("phase_b_invalid:source_state_families")

    family_rows: dict[str, dict] = {}
    for row in families:
        if not isinstance(row, dict):
            raise StaticV2ContractError("phase_b_invalid:source_state_family_row")
        family = str(row.get("family", "")).strip()
        if not family:
            raise StaticV2ContractError("phase_b_invalid:source_state_family_name")
        family_rows[family] = row

    target_rows = target_cross_doc.get("phase_b_target_stat_crosswalk")
    contributor_rows = contributor_cross_doc.get("phase_b_contributor_crosswalk")
    if not isinstance(target_rows, list):
        raise StaticV2ContractError("phase_b_invalid:target_crosswalk")
    if not isinstance(contributor_rows, list):
        raise StaticV2ContractError("phase_b_invalid:contributor_crosswalk")

    contributor_ids_seen: set[str] = set()
    for row in contributor_rows:
        if not isinstance(row, dict):
            raise StaticV2ContractError("phase_b_invalid:contributor_crosswalk_row")
        contributor_id = str(row.get("contributor_id", "")).strip()
        if contributor_id not in contract.canonical_contributor_ids:
            raise StaticV2ContractError(
                f"phase_b_invalid:unknown_canonical_contributor_in_crosswalk:{contributor_id}"
            )
        contributor_ids_seen.add(contributor_id)
        verdict = str(row.get("coverage_verdict", "")).strip()
        if verdict not in {"fully_source_backed", "explicitly_blocked", "incomplete"}:
            raise StaticV2ContractError(f"phase_b_invalid:contributor_verdict:{verdict}")
        if verdict == "incomplete":
            raise StaticV2ContractError("phase_b_incomplete:contributor_incomplete_present")
        source_family = str(row.get("source_state_family", "")).strip()
        if source_family not in family_rows:
            raise StaticV2ContractError(
                f"phase_b_invalid:source_state_family_missing_from_coverage:{source_family}"
            )

    missing_contributors = contract.canonical_contributor_ids - contributor_ids_seen
    if missing_contributors:
        raise StaticV2ContractError(
            "phase_b_incomplete:canonical_contributors_missing_crosswalk_rows"
        )

    target_ids_seen: set[str] = set()
    for row in target_rows:
        if not isinstance(row, dict):
            raise StaticV2ContractError("phase_b_invalid:target_crosswalk_row")
        target = str(row.get("target_stat", "")).strip()
        if target not in contract.canonical_object_ids:
            raise StaticV2ContractError(
                f"phase_b_invalid:unknown_canonical_target_in_crosswalk:{target}"
            )
        target_ids_seen.add(target)
        verdict = str(row.get("final_coverage_verdict", "")).strip()
        if verdict not in {
            "fully_source_covered",
            "partially_blocked_but_explicit",
            "incomplete",
        }:
            raise StaticV2ContractError(f"phase_b_invalid:target_verdict:{verdict}")
        if verdict == "incomplete":
            raise StaticV2ContractError("phase_b_incomplete:target_incomplete_present")
        composite_status = str(row.get("composite_dependency_status", "")).strip()
        if composite_status not in {
            "dependency_rule_defined",
            "dependency_rule_deferred_blocked",
            "not_composite",
        }:
            raise StaticV2ContractError(
                f"phase_b_invalid:target_composite_status:{composite_status}"
            )

    missing_targets = contract.canonical_object_ids - target_ids_seen
    if missing_targets:
        raise StaticV2ContractError("phase_b_incomplete:canonical_targets_missing_crosswalk_rows")

    contributors_by_source_family: dict[str, int] = {}
    for row in contributor_rows:
        fam = str(row.get("source_state_family", "")).strip()
        contributors_by_source_family[fam] = contributors_by_source_family.get(fam, 0) + 1

    for family, row in family_rows.items():
        implemented = bool(row.get("adapter_implemented"))
        in_scope = bool(row.get("in_scope"))
        expected = bool(row.get("expected_canonical_contributors", True))
        mapped = contributors_by_source_family.get(family, 0)
        if in_scope and implemented and expected and mapped == 0:
            raise StaticV2ContractError(
                f"phase_b_incomplete:implemented_family_without_mapped_contributors:{family}"
            )


    quarantine_root = quarantine_doc.get("v2_quarantine_registry")
    if not isinstance(quarantine_root, dict):
        raise StaticV2ContractError("phase_b_invalid:quarantine_registry")
    blocked_or_unresolved_targets = quarantine_root.get("blocked_or_unresolved_targets")
    if not isinstance(blocked_or_unresolved_targets, list):
        raise StaticV2ContractError("phase_b_invalid:blocked_or_unresolved_targets")
    blocked_target_names = {str(row.get("target_name", "")).strip() for row in blocked_or_unresolved_targets if isinstance(row, dict)}
    canonical_blocked_overlap = blocked_target_names.intersection(contract.canonical_target_stats)
    if canonical_blocked_overlap:
        raise StaticV2ContractError("phase_b_invalid:canonical_targets_present_in_blocked_or_unresolved_targets")

    readiness = source_cov.get("readiness")
    if not isinstance(readiness, dict):
        raise StaticV2ContractError("phase_b_invalid:missing_readiness")

    declared_phase_c_gate_open = bool(readiness.get("phase_c_gate_open"))
    if blocked_target_names and declared_phase_c_gate_open:
        raise StaticV2ContractError("phase_b_invalid:phase_c_gate_open_with_blocked_or_unresolved_target_names")

    targets_incomplete_total = int(readiness.get("targets_incomplete_total", -1))
    contributors_incomplete_total = int(readiness.get("contributors_incomplete_total", -1))
    computed_accounting_complete = (
        targets_incomplete_total == 0 and contributors_incomplete_total == 0
    )
    declared_accounting_complete = bool(readiness.get("coverage_accounting_complete"))
    if declared_accounting_complete != computed_accounting_complete:
        raise StaticV2ContractError("phase_b_invalid:coverage_accounting_complete_mismatch")

    return {
        "targets": len(target_rows),
        "contributors": len(contributor_rows),
        "family_rows": len(family_rows),
        "coverage_accounting_complete": computed_accounting_complete,
    }




def summarize_v2_registry_status() -> dict[str, object]:
    contract = load_static_v2_contract()
    phase_b = validate_phase_b_stat_coverage()
    quarantine_doc = _load_yaml(_QUARANTINE_REGISTRY_PATH)
    quarantine_root = quarantine_doc.get("v2_quarantine_registry", {})
    blocked_targets = quarantine_root.get("blocked_or_unresolved_targets", [])
    blocked_legacy_names = quarantine_root.get("blocked_or_unresolved_legacy_names", [])

    return {
        "summary_status": {
            "canonical_target_stats": len(contract.canonical_target_stats),
            "runtime_mechanic_parameters": len(contract.runtime_mechanic_parameters),
            "environment_parameters": len(contract.environment_parameters),
            "capabilities": len(contract.capabilities),
            "canonical_object_ids": len(contract.canonical_object_ids),
            "canonical_contributor_ids": len(contract.canonical_contributor_ids),
            "composite_targets": len(contract.composite_targets),
            "blocked_or_unresolved_targets": len(blocked_targets),
            "blocked_or_unresolved_legacy_names": len(blocked_legacy_names),
            "phase_b_coverage_accounting_complete": bool(
                phase_b.get("coverage_accounting_complete", False)
            ),
        },
        "next": [
            "curate split registry membership semantics for edge IDs (object-class review)",
            "complete migration of all parity/audit artifacts to split object-class IDs (remove legacy wording)",
            "wire summary status into user-facing reporting so counts/blocked items are visible by default",
        ],
    }


def _load_named_registry_list(doc: dict, *, key: str, error_code: str) -> tuple[frozenset[str], Mapping[str, Mapping[str, object]]]:
    values = doc.get(key)
    if not isinstance(values, list):
        raise StaticV2ContractError(error_code)
    return frozenset(str(value).strip() for value in values)


def _ensure_disjoint_registry_classes(
    *,
    canonical_targets: frozenset[str],
    mechanic_parameters: frozenset[str],
    environment_parameters: frozenset[str],
    capabilities: frozenset[str],
) -> None:
    classes = {
        "v2_canonical_target_stats": canonical_targets,
        "v2_mechanic_parameters": mechanic_parameters,
        "v2_environment_parameters": environment_parameters,
        "v2_capabilities": capabilities,
    }
    names = tuple(classes.keys())
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            if classes[left_name].intersection(classes[right_name]):
                raise StaticV2ContractError(
                    f"registry_invalid:object_class_overlap:{left_name}:{right_name}"
                )

def _validate_source_schema(source_schema_doc: dict) -> None:
    root = source_schema_doc.get("v2_source_state_schema")
    if not isinstance(root, dict):
        raise StaticV2ContractError("registry_invalid:v2_source_state_schema")
    required_fields = root.get("required_row_fields")
    families = root.get("families")
    if not isinstance(required_fields, list) or not isinstance(families, list):
        raise StaticV2ContractError("registry_invalid:v2_source_state_schema_structure")

    stat_contract = root.get("stat_target_contract_schema")
    if not isinstance(stat_contract, dict):
        raise StaticV2ContractError("registry_invalid:stat_target_contract_schema")

    contributor_id_section_contract = stat_contract.get("contributor_id_section_contract")
    if not isinstance(contributor_id_section_contract, dict):
        raise StaticV2ContractError("registry_invalid:contributor_id_section_contract")

    source_family_separator = str(
        contributor_id_section_contract.get("source_family_separator", "")
    ).strip()
    if source_family_separator != _CONTRIBUTOR_ID_SECTION_SEPARATOR:
        raise StaticV2ContractError("registry_invalid:contributor_id_section_separator")

    semantic_separator = str(contributor_id_section_contract.get("semantic_separator", "")).strip()
    if semantic_separator != ".":
        raise StaticV2ContractError("registry_invalid:contributor_id_semantic_separator")

    required_sections = contributor_id_section_contract.get("required_sections")
    if required_sections != ["source_family"]:
        raise StaticV2ContractError("registry_invalid:contributor_id_required_sections")

    optional_sections = contributor_id_section_contract.get("optional_sections")
    if optional_sections != ["entity", "attribute", "metric"]:
        raise StaticV2ContractError("registry_invalid:contributor_id_optional_sections")

    semantic_sections_optional = contributor_id_section_contract.get("semantic_sections_optional")
    if semantic_sections_optional is not True:
        raise StaticV2ContractError("registry_invalid:contributor_id_semantic_sections_optional")


def _validate_operations_registry(operations_doc: dict) -> frozenset[str]:
    root = operations_doc.get("v2_contributor_operations")
    if not isinstance(root, dict):
        raise StaticV2ContractError("registry_invalid:v2_contributor_operations")
    operation_classes = root.get("allowed_operation_classes")
    if not isinstance(operation_classes, list):
        raise StaticV2ContractError("registry_invalid:allowed_operation_classes")
    return frozenset(str(value).strip() for value in operation_classes)


def _validate_contributor_row(
    row: dict,
    *,
    canonical_targets: frozenset[str],
    canonical_target_stats: frozenset[str],
    mechanic_parameters: frozenset[str],
    environment_parameters: frozenset[str],
    capabilities: frozenset[str],
    allowed_operations: frozenset[str],
) -> None:
    for field in _REQUIRED_CONTRIBUTOR_FIELDS:
        if field not in row:
            raise StaticV2ContractError(f"registry_invalid:contributor_missing_field:{field}")

    contributor_id = str(row.get("contributor_id", "")).strip()
    if not contributor_id:
        raise StaticV2ContractError("registry_invalid:empty_contributor_id")
    for prefix in _FORBIDDEN_CANONICAL_CONTRIBUTOR_PREFIXES:
        if contributor_id.startswith(prefix):
            raise StaticV2ContractError(
                f"fabricated_canonical_contributor_id_forbidden:{contributor_id}"
            )

    if " " in contributor_id:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_id_contains_space:{contributor_id}"
        )

    if _CONTRIBUTOR_ID_SECTION_SEPARATOR not in contributor_id:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_id_missing_source_family_separator:{contributor_id}"
        )

    contributor_family = str(row.get("contributor_family", "")).strip()
    family_prefix, remainder = contributor_id.split(_CONTRIBUTOR_ID_SECTION_SEPARATOR, 1)
    if not family_prefix or not remainder:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_id_empty_section:{contributor_id}"
        )
    if family_prefix != contributor_family:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_id_source_family_mismatch:{contributor_id}"
        )

    target = str(row.get("owned_target_stat", "")).strip()
    if target not in canonical_targets:
        raise StaticV2ContractError(f"registry_invalid:contributor_unknown_target:{target}")

    destination_object_class = str(row.get("destination_object_class", "")).strip()
    allowed_classes = {
        "canonical_target_stat",
        "runtime_mechanic_parameter",
        "environment_parameter",
        "capability",
    }
    if destination_object_class not in allowed_classes:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_unknown_destination_object_class:{destination_object_class}"
        )

    expected_class = "canonical_target_stat"
    if target in mechanic_parameters:
        expected_class = "runtime_mechanic_parameter"
    elif target in environment_parameters:
        expected_class = "environment_parameter"
    elif target in capabilities:
        expected_class = "capability"
    elif target in canonical_target_stats:
        expected_class = "canonical_target_stat"

    if destination_object_class != expected_class:
        raise StaticV2ContractError(
            "registry_invalid:contributor_destination_object_class_mismatch:"
            f"{contributor_id}:{destination_object_class}:{expected_class}"
        )

    operation_class = str(row.get("operation_class", "")).strip()
    if operation_class not in allowed_operations:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_unknown_operation:{operation_class}"
        )

    stages = row.get("stage_applicability")
    if not isinstance(stages, list) or not stages:
        raise StaticV2ContractError("registry_invalid:contributor_missing_stage_applicability")


def _validate_stage_applicability_bridge(
    stage_root: dict,
    *,
    contributor_families: frozenset[str],
    static_stage_order: tuple[str, ...],
    contributor_rows: list,
) -> tuple[frozenset[str], Mapping[str, Mapping[str, object]]]:
    static_stage_names: list[str] = []
    for row in stage_root.get("static_stages", []):
        if not isinstance(row, dict):
            raise StaticV2ContractError("registry_invalid:static_stage_row")
        name = str(row.get("stage", "")).strip()
        if not name:
            raise StaticV2ContractError("registry_invalid:static_stage_name")
        static_stage_names.append(name)

    if tuple(static_stage_names) != static_stage_order:
        raise StaticV2ContractError("registry_invalid:static_stage_order_mismatch")

    bridge_rows = stage_root.get("source_family_stage_bridge")
    if not isinstance(bridge_rows, list) or not bridge_rows:
        raise StaticV2ContractError("registry_invalid:source_family_stage_bridge")

    routing_doc = _load_yaml(_IDS_SECTION_ROUTING_PATH)
    routing_sections = routing_doc.get("sections")
    if not isinstance(routing_sections, dict):
        raise StaticV2ContractError("registry_invalid:ids_section_routing")
    ids_source_families = {
        str(payload.get("source_family", "")).strip()
        for payload in routing_sections.values()
        if isinstance(payload, dict)
    }

    snapshot_fields = {field.name for field in fields(AccountSnapshot)}
    static_stage_set = set(static_stage_order)
    rows_by_family: dict[str, dict] = {}

    for row in bridge_rows:
        if not isinstance(row, dict):
            raise StaticV2ContractError("registry_invalid:source_family_stage_bridge_row")
        contributor_family = str(row.get("contributor_family", "")).strip()
        if not contributor_family:
            raise StaticV2ContractError("registry_invalid:bridge_missing_contributor_family")
        if contributor_family in rows_by_family:
            raise StaticV2ContractError(f"registry_invalid:bridge_duplicate_contributor_family:{contributor_family}")
        if contributor_family not in contributor_families:
            raise StaticV2ContractError(f"registry_invalid:bridge_unknown_contributor_family:{contributor_family}")

        kb_source_family = str(row.get("kb_source_family", "")).strip()
        if not kb_source_family:
            raise StaticV2ContractError(f"registry_invalid:bridge_missing_kb_source_family:{contributor_family}")

        source_origin = str(row.get("source_origin", "")).strip()
        if source_origin not in {"ids_section", "table_surface"}:
            raise StaticV2ContractError(f"registry_invalid:bridge_invalid_source_origin:{contributor_family}")
        if source_origin == "ids_section" and kb_source_family not in ids_source_families:
            raise StaticV2ContractError(f"registry_invalid:bridge_ids_source_family_drift:{contributor_family}:{kb_source_family}")

        account_snapshot_field = row.get("account_snapshot_field")
        if source_origin == "ids_section":
            field_name = str(account_snapshot_field or "").strip()
            if not field_name:
                raise StaticV2ContractError(f"registry_invalid:bridge_missing_account_snapshot_field:{contributor_family}")
            if field_name not in snapshot_fields:
                raise StaticV2ContractError(f"registry_invalid:bridge_unknown_account_snapshot_field:{contributor_family}:{field_name}")
        elif account_snapshot_field is not None:
            field_name = str(account_snapshot_field).strip()
            if field_name:
                raise StaticV2ContractError(f"registry_invalid:bridge_table_surface_must_not_set_account_snapshot_field:{contributor_family}")

        loadout_selection_field = str(row.get("loadout_selection_field", "")).strip()
        stages = row.get("stage_applicability")
        if not isinstance(stages, list) or not stages:
            raise StaticV2ContractError(f"registry_invalid:bridge_missing_stage_applicability:{contributor_family}")
        stage_set = {str(stage).strip() for stage in stages}
        if not stage_set.issubset(static_stage_set):
            raise StaticV2ContractError(f"registry_invalid:bridge_unknown_stage_reference:{contributor_family}")

        if loadout_selection_field:
            if "baseline_loadout" not in stage_set:
                raise StaticV2ContractError(f"registry_invalid:bridge_loadout_selector_without_baseline_loadout_stage:{contributor_family}")
            if loadout_selection_field not in {"card_presets", "module_presets"}:
                raise StaticV2ContractError(f"registry_invalid:bridge_unknown_loadout_selection_field:{contributor_family}:{loadout_selection_field}")
        elif "baseline_loadout" in stage_set and contributor_family in {"card", "module_main", "module_sub", "module_unique"}:
            raise StaticV2ContractError(f"registry_invalid:bridge_missing_loadout_selector:{contributor_family}")

        rows_by_family[contributor_family] = row

    if set(rows_by_family.keys()) != set(contributor_families):
        raise StaticV2ContractError("registry_invalid:bridge_contributor_family_coverage_mismatch")

    allowed_stages_by_family = {
        family: {str(item).strip() for item in row.get("stage_applicability", [])}
        for family, row in rows_by_family.items()
    }
    for row in contributor_rows:
        family = str(row.get("contributor_family", "")).strip()
        contributor_id = str(row.get("contributor_id", "")).strip()
        stages = row.get("stage_applicability")
        contributor_stage_set = {str(item).strip() for item in stages} if isinstance(stages, list) else set()
        allowed = allowed_stages_by_family.get(family)
        if not allowed or not contributor_stage_set.issubset(allowed):
            raise StaticV2ContractError(
                f"registry_invalid:contributor_stage_not_allowed_by_bridge:{contributor_id}"
            )

    return frozenset(rows_by_family.keys()), {
        family: dict(row) for family, row in rows_by_family.items()
    }


def _validate_composite_entries(
    entries: list,
    *,
    canonical_targets: frozenset[str],
) -> frozenset[str]:
    composite_targets: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise StaticV2ContractError("registry_invalid:composite_entry_not_mapping")
        target = str(item.get("target_stat", "")).strip()
        if target not in canonical_targets:
            raise StaticV2ContractError(
                f"registry_invalid:composite_unknown_target:{target}"
            )
        status = str(item.get("composite_status", "")).strip()
        if status not in {"dependency_rule_defined", "dependency_rule_deferred_blocked"}:
            raise StaticV2ContractError(f"registry_invalid:composite_status:{status}")
        composite_targets.add(target)
    return frozenset(composite_targets)


def _validate_quarantine_registry(root: dict) -> frozenset[str]:
    quarantined = root.get("quarantined_contributors")
    coverage = root.get("coverage_accounting")
    if not isinstance(quarantined, list):
        raise StaticV2ContractError("registry_invalid:quarantined_contributors")
    if not isinstance(coverage, dict):
        raise StaticV2ContractError("registry_invalid:coverage_accounting")

    target_coverage = coverage.get("targets")
    contributor_coverage = coverage.get("contributors")
    if not isinstance(target_coverage, dict) or not isinstance(contributor_coverage, dict):
        raise StaticV2ContractError("registry_invalid:coverage_sections")

    target_uncovered = target_coverage.get("uncovered_items")
    contributor_uncovered = contributor_coverage.get("uncovered_items")
    if target_uncovered != []:
        raise StaticV2ContractError("phase_a_incomplete:uncovered_targets_present")
    if contributor_uncovered != []:
        raise StaticV2ContractError("phase_a_incomplete:uncovered_contributors_present")

    ids: set[str] = set()
    for item in quarantined:
        if not isinstance(item, dict):
            raise StaticV2ContractError("registry_invalid:quarantined_entry_not_mapping")
        cid = str(item.get("contributor_id", "")).strip()
        if not cid:
            raise StaticV2ContractError("registry_invalid:quarantined_missing_contributor_id")
        ids.add(cid)
    return frozenset(ids)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise StaticV2ContractError(f"missing_v2_registry:{path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StaticV2ContractError(f"invalid_v2_registry_payload:{path}")
    return payload
