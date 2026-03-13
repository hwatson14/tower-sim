from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from tower_sim.engines.stat_input_compiler import CompiledBaselineLoadout, CompiledStatInputs
from tower_sim.engines.static_pipeline_v2 import (
    materialize_static_stages,
    required_static_stages,
    validate_required_stages_present,
)
from tower_sim.registry import static_v2_contract as contract_module
from tower_sim.registry.static_v2_contract import (
    StaticV2ContractError,
    load_static_v2_contract,
    validate_phase_b_stat_coverage,
)


def test_registry_completeness_contract_loads() -> None:
    contract = load_static_v2_contract()
    assert contract.canonical_target_stats
    assert contract.canonical_contributor_ids
    assert contract.composite_targets


def test_alias_direction_is_legacy_to_canonical_only() -> None:
    contract = load_static_v2_contract()
    assert contract.resolve_target_stat("tower_hp") == "health"
    with pytest.raises(StaticV2ContractError, match="unknown_target_stat"):
        contract.resolve_target_stat("health_legacy")


def test_runtime_fields_rejected_from_static_targets() -> None:
    contract = load_static_v2_contract()
    with pytest.raises(StaticV2ContractError, match="runtime_field_not_allowed_in_static_core"):
        contract.resolve_target_stat("wave_attack_index")


def test_required_stages_include_baseline_gem_respec() -> None:
    assert required_static_stages() == (
        "baseline_account",
        "baseline_gem_respec",
        "baseline_loadout",
    )
    validate_required_stages_present()


def test_fabricated_canonical_contributor_ids_forbidden() -> None:
    contract = load_static_v2_contract()
    with pytest.raises(StaticV2ContractError, match="fabricated_canonical_contributor_id_forbidden"):
        contract.validate_canonical_contributor_id("legacy_stage__baseline_account__tower_hp")


def test_composite_dependency_registry_loads() -> None:
    contract = load_static_v2_contract()
    assert "health" in contract.composite_targets


def test_quarantined_items_are_explicit_and_enumerable() -> None:
    contract = load_static_v2_contract()
    assert isinstance(contract.quarantined_contributor_ids, frozenset)
    assert len(contract.quarantined_contributor_ids) == 0


def test_contributor_missing_required_field_fails_validation() -> None:
    row = {
        "contributor_id": "workshop__health__base",
        "contributor_family": "workshop",
        "owned_target_stat": "health",
        "operation_class": "set_base",
        # stage_applicability intentionally omitted
        "ownership_role": "direct",
        "canonical_status": "canonical",
        "migration_status": "ledger_seed_phase_a",
    }
    with pytest.raises(StaticV2ContractError, match="contributor_missing_field:stage_applicability"):
        contract_module._validate_contributor_row(
            row,
            canonical_targets=frozenset({"health"}),
            allowed_operations=frozenset({"set_base"}),
        )


def test_phase_b_target_and_contributor_crosswalk_validation_passes_structure() -> None:
    summary = validate_phase_b_stat_coverage()
    assert summary["targets"] > 0
    assert summary["contributors"] > 0
    assert summary["coverage_accounting_complete"] is True


def test_phase_b_readiness_marks_accounting_complete_and_opens_phase_c_gate() -> None:
    import yaml
    doc = yaml.safe_load(Path("audit/static_pipeline_v2_phase_b_source_state_coverage.yaml").read_text(encoding="utf-8"))
    readiness = doc["phase_b_source_state_coverage"]["readiness"]
    assert readiness["verdict"] == "Phase B source normalization and naming reconciliation complete"
    assert readiness["coverage_accounting_complete"] is True
    assert readiness["phase_c_gate_open"] is True


def test_phase_b_blocks_declaring_complete_for_family_only_coverage() -> None:
    _ = load_static_v2_contract()
    source_doc = contract_module._load_yaml(contract_module._PHASE_B_SOURCE_COVERAGE_PATH)
    target_doc = contract_module._load_yaml(contract_module._PHASE_B_TARGET_CROSSWALK_PATH)
    contributor_doc = contract_module._load_yaml(contract_module._PHASE_B_CONTRIBUTOR_CROSSWALK_PATH)

    bad_source = deepcopy(source_doc)
    bad_contrib = deepcopy(contributor_doc)

    for row in bad_source["phase_b_source_state_coverage"]["families"]:
        if row.get("family") == "workshop":
            row["adapter_implemented"] = True
            row["blocked_or_deferred"] = False
            row["reason"] = None
    for row in bad_contrib["phase_b_contributor_crosswalk"]:
        if row.get("source_state_family") == "workshop":
            row["source_state_family"] = "labs"

    with patch(
        "tower_sim.registry.static_v2_contract._load_yaml",
        side_effect=[bad_source, target_doc, bad_contrib, contract_module._load_yaml(contract_module._QUARANTINE_REGISTRY_PATH)],
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="implemented_family_without_mapped_contributors:workshop",
        ):
            validate_phase_b_stat_coverage()


def test_phase_b_target_crosswalk_has_no_partially_blocked_rows_after_mapping_closure() -> None:
    import yaml
    target_doc = yaml.safe_load(Path("audit/static_pipeline_v2_phase_b_target_stat_crosswalk.yaml").read_text(encoding="utf-8"))
    rows = target_doc["phase_b_target_stat_crosswalk"]
    assert not any(row["final_coverage_verdict"] == "partially_blocked_but_explicit" for row in rows)


def test_materialize_static_stages_uses_required_stage_names() -> None:
    with (
        patch(
            "tower_sim.engines.static_pipeline_v2.compile_baseline_account_stat_inputs",
            return_value=CompiledStatInputs(stat_inputs=[], missing=[]),
        ),
        patch(
            "tower_sim.engines.static_pipeline_v2.compile_baseline_gem_respec_stat_inputs",
            return_value=CompiledStatInputs(stat_inputs=[], missing=[]),
        ),
        patch(
            "tower_sim.engines.static_pipeline_v2.compile_baseline_loadout_stat_inputs",
            return_value=CompiledBaselineLoadout(
                stat_inputs=[],
                missing=[],
                module_contribution_ledger=[],
                layer_gaps=[],
            ),
        ),
    ):
        materialized = materialize_static_stages(snapshot=None)  # type: ignore[arg-type]

    assert tuple(materialized.by_stage.keys()) == required_static_stages()


def test_phase_b_mapping_backlog_metrics_are_explicit() -> None:
    import yaml
    doc = yaml.safe_load(Path("audit/static_pipeline_v2_phase_b_source_state_coverage.yaml").read_text(encoding="utf-8"))
    backlog = doc["phase_b_source_state_coverage"]["mapping_backlog"]
    assert backlog["quarantined_contributors_total"] == 0
    assert backlog["partially_blocked_targets_total"] == 0
    assert backlog["blocked_or_unresolved_target_names_total"] == 0


def test_phase_b_gate_open_when_blocked_or_unresolved_target_names_are_zero() -> None:
    import yaml
    doc = yaml.safe_load(Path("audit/static_pipeline_v2_phase_b_source_state_coverage.yaml").read_text(encoding="utf-8"))
    readiness = doc["phase_b_source_state_coverage"]["readiness"]
    assert readiness["phase_c_gate_open"] is True


def test_next_cost_fields_remain_out_of_canonical_target_aliasing() -> None:
    import yaml
    alias_doc = yaml.safe_load(Path("tables/meta/registry/v2/aliases.yaml").read_text(encoding="utf-8"))
    alias_keys = set(alias_doc["v2_alias_map"].keys())
    assert "black_hole_cooldown_next_cost" not in alias_keys



def test_legacy_backlog_uses_explicit_domain_taxonomy() -> None:
    import yaml
    doc = yaml.safe_load(Path("tables/meta/registry/v2/quarantine_registry.yaml").read_text(encoding="utf-8"))
    rows = doc["v2_quarantine_registry"]["blocked_or_unresolved_legacy_names"]
    domains = {row["domain"] for row in rows}
    assert domains <= {
        "canonical_target_legacy_name",
        "canonical_target_legacy_excluded_name",
        "economy_cost_legacy_name",
        "runtime_derived_legacy_name",
    }


def test_legacy_backlog_contains_only_unresolved_names() -> None:
    import yaml
    quarantine_doc = yaml.safe_load(Path("tables/meta/registry/v2/quarantine_registry.yaml").read_text(encoding="utf-8"))
    alias_doc = yaml.safe_load(Path("tables/meta/registry/v2/aliases.yaml").read_text(encoding="utf-8"))
    target_doc = yaml.safe_load(Path("tables/meta/registry/v2/target_stats.yaml").read_text(encoding="utf-8"))

    unresolved = {row["name"] for row in quarantine_doc["v2_quarantine_registry"]["blocked_or_unresolved_legacy_names"]}
    alias_keys = set(alias_doc["v2_alias_map"].keys())
    canonical_targets = set(target_doc["v2_target_stats"])

    assert unresolved.isdisjoint(alias_keys)
    assert unresolved.isdisjoint(canonical_targets)


def test_canonical_target_legacy_review_set_resolved_with_mapping_or_exclusion() -> None:
    import yaml
    alias_doc = yaml.safe_load(Path("tables/meta/registry/v2/aliases.yaml").read_text(encoding="utf-8"))
    quarantine_doc = yaml.safe_load(Path("tables/meta/registry/v2/quarantine_registry.yaml").read_text(encoding="utf-8"))

    reviewed = {
        "death_ray_damage_mult",
        "knockback_mult",
        "orb_damage_mult",
        "plasma_cannon_damage_mult",
        "thorns_damage_mult",
        "wall_thorns_mult",
        "workshop_interest",
        "workshop_knockback",
        "workshop_max_recovery",
        "workshop_recovery_packages",
    }

    alias_keys = set(alias_doc["v2_alias_map"].keys())
    legacy_rows = quarantine_doc["v2_quarantine_registry"]["blocked_or_unresolved_legacy_names"]
    excluded = {row["name"] for row in legacy_rows if row["domain"] == "canonical_target_legacy_excluded_name"}
    runtime_derived = {row["name"] for row in legacy_rows if row["domain"] == "runtime_derived_legacy_name"}

    mapped = reviewed.intersection(alias_keys)
    explicitly_excluded = reviewed.intersection(excluded)

    assert mapped == {
        "death_ray_damage_mult",
        "plasma_cannon_damage_mult",
        "thorns_damage_mult",
        "wall_thorns_mult",
        "workshop_knockback",
        "workshop_interest",
        "workshop_max_recovery",
        "workshop_recovery_packages",
    }
    assert explicitly_excluded == set()
    assert "orb_damage_mult" in runtime_derived
    assert "knockback_mult" in runtime_derived


def test_removed_workshop_legacy_names_do_not_exist_anywhere() -> None:
    import yaml
    alias_doc = yaml.safe_load(Path("tables/meta/registry/v2/aliases.yaml").read_text(encoding="utf-8"))
    quarantine_doc = yaml.safe_load(Path("tables/meta/registry/v2/quarantine_registry.yaml").read_text(encoding="utf-8"))

    removed = {"workshop_enemy_level_skip", "workshop_free_upgrades", "workshop_land_mine"}
    alias_keys = set(alias_doc["v2_alias_map"].keys())
    legacy_names = {row["name"] for row in quarantine_doc["v2_quarantine_registry"]["blocked_or_unresolved_legacy_names"]}

    assert removed.isdisjoint(alias_keys)
    assert removed.isdisjoint(legacy_names)


def test_removed_workshop_names_absent_from_phase_a_coverage_audit() -> None:
    text = Path("audit/static_pipeline_v2_phase_a_coverage_audit.md").read_text(encoding="utf-8")
    assert "`workshop_enemy_level_skip`" not in text
    assert "`workshop_free_upgrades`" not in text
    assert "`workshop_land_mine`" not in text


def test_stat_target_contract_schema_declares_required_and_derivation_fields() -> None:
    import yaml
    doc = yaml.safe_load(Path("tables/meta/registry/v2/source_state_schema.yaml").read_text(encoding="utf-8"))
    schema = doc["v2_source_state_schema"]["stat_target_contract_schema"]

    assert schema["required_fields"] == ["stat_target_id", "source_family", "derivation_kind"]
    assert set(schema["derivation_kind_allowed"]) == {"direct_input", "computed_component", "final_resolved"}
    assert schema["contributor_id_section_contract"] == {
        "source_family_separator": "__",
        "semantic_separator": ".",
        "required_sections": ["source_family"],
        "optional_sections": ["entity", "attribute", "metric"],
        "semantic_sections_optional": True,
        "policy": "contributor_id_must_be_prefixed_by_source_family_and_semantic_sections_use_dot_when_present",
    }


def test_stat_target_contract_schema_health_example_matches_final_formula_contract() -> None:
    import yaml
    doc = yaml.safe_load(Path("tables/meta/registry/v2/source_state_schema.yaml").read_text(encoding="utf-8"))
    example = doc["v2_source_state_schema"]["stat_target_contract_schema"]["example_health_final_row"]

    assert example["stat_target_id"] == "tower_hp"
    assert example["derivation_kind"] == "final_resolved"
    assert example["formula_contract"] == "final=((base+loadout_delta)*enhancement)+tier_delta"


def test_all_contributor_ids_follow_section_contract() -> None:
    import yaml

    rows = yaml.safe_load(Path("tables/meta/registry/v2/contributors.yaml").read_text(encoding="utf-8"))["v2_contributor_ids"]
    for row in rows:
        contributor_id = row["contributor_id"]
        assert " " not in contributor_id
        assert "__" in contributor_id
        family_prefix, remainder = contributor_id.split("__", 1)
        assert family_prefix == row["contributor_family"]
        assert remainder.strip()
