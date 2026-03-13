from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import yaml


class StaticV2ContractError(RuntimeError):
    pass


_REGISTRY_ROOT = Path("tables/meta/registry/v2")
_TARGET_STATS_PATH = _REGISTRY_ROOT / "target_stats.yaml"
_CONTRIBUTORS_PATH = _REGISTRY_ROOT / "contributors.yaml"
_ALIASES_PATH = _REGISTRY_ROOT / "aliases.yaml"
_STAGES_PATH = _REGISTRY_ROOT / "stages.yaml"
_RUNTIME_DOMAINS_PATH = _REGISTRY_ROOT / "runtime_domains.yaml"
_SOURCE_STATE_SCHEMA_PATH = _REGISTRY_ROOT / "source_state_schema.yaml"
_CONTRIBUTOR_OPERATIONS_PATH = _REGISTRY_ROOT / "contributor_operations.yaml"
_COMPOSITE_DEPENDENCIES_PATH = _REGISTRY_ROOT / "composite_dependencies.yaml"
_QUARANTINE_REGISTRY_PATH = _REGISTRY_ROOT / "quarantine_registry.yaml"

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
    canonical_contributor_ids: frozenset[str]
    legacy_to_canonical_aliases: Mapping[str, str]
    required_static_stage_order: tuple[str, ...]
    static_runtime_deny_list: frozenset[str]
    composite_targets: frozenset[str]
    quarantined_contributor_ids: frozenset[str]

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
    target_stats_doc = _load_yaml(_TARGET_STATS_PATH)
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

    target_stats = target_stats_doc.get("v2_target_stats")
    if not isinstance(target_stats, list):
        raise StaticV2ContractError("registry_invalid:v2_target_stats")
    canonical_targets = frozenset(str(item).strip() for item in target_stats)

    contributor_rows = contributors_doc.get("v2_contributor_ids")
    if not isinstance(contributor_rows, list):
        raise StaticV2ContractError("registry_invalid:v2_contributor_ids")
    contributor_ids: list[str] = []
    for row in contributor_rows:
        if not isinstance(row, dict):
            raise StaticV2ContractError("registry_invalid:contributor_row_not_mapping")
        _validate_contributor_row(
            row,
            canonical_targets=canonical_targets,
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
        if canonical_name not in canonical_targets:
            raise StaticV2ContractError(
                f"alias_points_to_unknown_canonical_target:{canonical_name}"
            )

    stage_root = stages_doc.get("v2_stage_applicability")
    if not isinstance(stage_root, dict):
        raise StaticV2ContractError("registry_invalid:v2_stage_applicability")
    required_stage_order = stage_root.get("required_static_stage_order")
    if not isinstance(required_stage_order, list):
        raise StaticV2ContractError("registry_invalid:required_static_stage_order")

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
        canonical_targets=canonical_targets,
    )

    quarantine_root = quarantine_doc.get("v2_quarantine_registry")
    if not isinstance(quarantine_root, dict):
        raise StaticV2ContractError("registry_invalid:v2_quarantine_registry")
    quarantined_contributor_ids = _validate_quarantine_registry(quarantine_root)

    return StaticV2Contract(
        canonical_target_stats=canonical_targets,
        canonical_contributor_ids=frozenset(contributor_ids),
        legacy_to_canonical_aliases={
            str(key).strip(): str(value).strip() for key, value in alias_map.items()
        },
        required_static_stage_order=tuple(str(stage).strip() for stage in required_stage_order),
        static_runtime_deny_list=frozenset(str(item).strip() for item in deny_list),
        composite_targets=composite_targets,
        quarantined_contributor_ids=quarantined_contributor_ids,
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
        if target not in contract.canonical_target_stats:
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

    missing_targets = contract.canonical_target_stats - target_ids_seen
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

    operation_class = str(row.get("operation_class", "")).strip()
    if operation_class not in allowed_operations:
        raise StaticV2ContractError(
            f"registry_invalid:contributor_unknown_operation:{operation_class}"
        )

    stages = row.get("stage_applicability")
    if not isinstance(stages, list) or not stages:
        raise StaticV2ContractError("registry_invalid:contributor_missing_stage_applicability")


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
