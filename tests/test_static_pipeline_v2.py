from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.stat_input_compiler import (
    CompiledBaselineLoadout,
    CompiledStatInputs,
    compile_baseline_account_stat_inputs,
    compile_baseline_gem_respec_stat_inputs,
    compile_baseline_loadout_stat_inputs,
)
from tower_sim.engines.static_pipeline_v2 import (
    RuntimeOverlayMaterialization,
    StageMaterialization,
    materialize_runtime_overlays,
    materialize_runtime_state,
    materialize_static_stages,
    required_runtime_overlay_families,
    required_static_stages,
    validate_required_runtime_overlay_families_present,
    validate_required_stages_present,
)
from tower_sim.registry import static_v2_contract as contract_module
from tower_sim.registry.stat_registry import Phase
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.registry.static_v2_contract import (
    StaticV2ContractError,
    load_static_v2_contract,
    summarize_v2_registry_status,
    validate_phase_b_stat_coverage,
)


def test_registry_completeness_contract_loads() -> None:
    contract = load_static_v2_contract()
    assert contract.canonical_target_stats
    assert contract.canonical_contributor_ids
    assert contract.composite_targets




def test_object_class_registries_are_disjoint_and_cover_object_universe() -> None:
    contract = load_static_v2_contract()

    assert contract.canonical_target_stats
    assert contract.runtime_mechanic_parameters
    assert contract.environment_parameters
    assert contract.capabilities

    assert contract.canonical_target_stats.isdisjoint(contract.runtime_mechanic_parameters)
    assert contract.canonical_target_stats.isdisjoint(contract.environment_parameters)
    assert contract.canonical_target_stats.isdisjoint(contract.capabilities)
    assert contract.runtime_mechanic_parameters.isdisjoint(contract.environment_parameters)
    assert contract.runtime_mechanic_parameters.isdisjoint(contract.capabilities)
    assert contract.environment_parameters.isdisjoint(contract.capabilities)

    assert contract.canonical_object_ids == (
        contract.canonical_target_stats
        | contract.runtime_mechanic_parameters
        | contract.environment_parameters
        | contract.capabilities
    )



def test_registry_status_summary_includes_next_steps() -> None:
    status = summarize_v2_registry_status()
    summary = status["summary_status"]
    next_steps = status["next"]

    assert summary["canonical_object_ids"] == (
        summary["canonical_target_stats"]
        + summary["runtime_mechanic_parameters"]
        + summary["environment_parameters"]
        + summary["capabilities"]
    )
    assert summary["phase_b_coverage_accounting_complete"] is True
    assert isinstance(summary["blocked_or_unresolved_targets"], int)
    assert isinstance(summary["blocked_or_unresolved_legacy_names"], int)
    assert isinstance(next_steps, list)
    assert len(next_steps) >= 3

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
        "destination_object_class": "canonical_target_stat",
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
            canonical_target_stats=frozenset({"health"}),
            mechanic_parameters=frozenset(),
            environment_parameters=frozenset(),
            capabilities=frozenset(),
            allowed_operations=frozenset({"set_base"}),
        )




def test_contributor_destination_object_class_mismatch_fails_validation() -> None:
    row = {
        "contributor_id": "uw__black_hole.cooldown_seconds",
        "contributor_family": "uw",
        "owned_target_stat": "black_hole_cooldown_seconds",
        "destination_object_class": "canonical_target_stat",
        "operation_class": "set_base",
        "stage_applicability": ["baseline_gem_respec"],
        "ownership_role": "direct",
        "canonical_status": "canonical",
        "migration_status": "ledger_seed_phase_a",
    }
    with pytest.raises(
        StaticV2ContractError,
        match="contributor_destination_object_class_mismatch",
    ):
        contract_module._validate_contributor_row(
            row,
            canonical_targets=frozenset({"black_hole_cooldown_seconds"}),
            canonical_target_stats=frozenset(),
            mechanic_parameters=frozenset({"black_hole_cooldown_seconds"}),
            environment_parameters=frozenset(),
            capabilities=frozenset(),
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
    contract = load_static_v2_contract()

    unresolved = {row["name"] for row in quarantine_doc["v2_quarantine_registry"]["blocked_or_unresolved_legacy_names"]}
    alias_keys = set(alias_doc["v2_alias_map"].keys())

    assert unresolved.isdisjoint(alias_keys)
    assert unresolved.isdisjoint(contract.canonical_object_ids)


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
    allowed_destination_classes = {
        "canonical_target_stat",
        "runtime_mechanic_parameter",
        "environment_parameter",
        "capability",
    }
    for row in rows:
        contributor_id = row["contributor_id"]
        assert " " not in contributor_id
        assert "__" in contributor_id
        family_prefix, remainder = contributor_id.split("__", 1)
        assert family_prefix == row["contributor_family"]
        assert remainder.strip()
        assert row["destination_object_class"] in allowed_destination_classes


def test_stage_bridge_covers_all_contributor_families() -> None:
    contract = load_static_v2_contract()
    assert contract.bridge_contributor_families == {
        "workshop",
        "lab",
        "relic",
        "enhancement",
        "uw",
        "uw_plus",
        "bot",
        "guardian",
        "card",
        "module_main",
        "module_sub",
        "module_unique",
        "perk",
        "battle_condition",
    }


def test_stage_bridge_rejects_unknown_account_snapshot_field() -> None:
    stages_doc = contract_module._load_yaml(contract_module._STAGES_PATH)
    bad_stages_doc = deepcopy(stages_doc)
    row = bad_stages_doc["v2_stage_applicability"]["source_family_stage_bridge"][0]
    row["account_snapshot_field"] = "not_a_snapshot_field"

    with patch(
        "tower_sim.registry.static_v2_contract._load_yaml",
        side_effect=[
            contract_module._load_yaml(contract_module._CANONICAL_TARGET_STATS_PATH),
            contract_module._load_yaml(contract_module._MECHANIC_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._ENVIRONMENT_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._CAPABILITIES_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTORS_PATH),
            contract_module._load_yaml(contract_module._ALIASES_PATH),
            bad_stages_doc,
            contract_module._load_yaml(contract_module._RUNTIME_DOMAINS_PATH),
            contract_module._load_yaml(contract_module._SOURCE_STATE_SCHEMA_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTOR_OPERATIONS_PATH),
            contract_module._load_yaml(contract_module._COMPOSITE_DEPENDENCIES_PATH),
            contract_module._load_yaml(contract_module._QUARANTINE_REGISTRY_PATH),
            contract_module._load_yaml(contract_module._IDS_SECTION_ROUTING_PATH),
        ],
    ):
        with pytest.raises(StaticV2ContractError, match="bridge_unknown_account_snapshot_field"):
            contract_module.load_static_v2_contract.__wrapped__()


def test_stage_bridge_rejects_ids_source_family_drift() -> None:
    stages_doc = contract_module._load_yaml(contract_module._STAGES_PATH)
    bad_stages_doc = deepcopy(stages_doc)
    row = bad_stages_doc["v2_stage_applicability"]["source_family_stage_bridge"][0]
    row["kb_source_family"] = "workshop_drift"

    with patch(
        "tower_sim.registry.static_v2_contract._load_yaml",
        side_effect=[
            contract_module._load_yaml(contract_module._CANONICAL_TARGET_STATS_PATH),
            contract_module._load_yaml(contract_module._MECHANIC_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._ENVIRONMENT_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._CAPABILITIES_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTORS_PATH),
            contract_module._load_yaml(contract_module._ALIASES_PATH),
            bad_stages_doc,
            contract_module._load_yaml(contract_module._RUNTIME_DOMAINS_PATH),
            contract_module._load_yaml(contract_module._SOURCE_STATE_SCHEMA_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTOR_OPERATIONS_PATH),
            contract_module._load_yaml(contract_module._COMPOSITE_DEPENDENCIES_PATH),
            contract_module._load_yaml(contract_module._QUARANTINE_REGISTRY_PATH),
            contract_module._load_yaml(contract_module._IDS_SECTION_ROUTING_PATH),
        ],
    ):
        with pytest.raises(StaticV2ContractError, match="bridge_ids_source_family_drift"):
            contract_module.load_static_v2_contract.__wrapped__()


def test_stage_bridge_rejects_loadout_family_without_selector() -> None:
    stages_doc = contract_module._load_yaml(contract_module._STAGES_PATH)
    bad_stages_doc = deepcopy(stages_doc)
    for row in bad_stages_doc["v2_stage_applicability"]["source_family_stage_bridge"]:
        if row.get("contributor_family") == "card":
            row.pop("loadout_selection_field", None)
            break

    with patch(
        "tower_sim.registry.static_v2_contract._load_yaml",
        side_effect=[
            contract_module._load_yaml(contract_module._CANONICAL_TARGET_STATS_PATH),
            contract_module._load_yaml(contract_module._MECHANIC_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._ENVIRONMENT_PARAMETERS_PATH),
            contract_module._load_yaml(contract_module._CAPABILITIES_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTORS_PATH),
            contract_module._load_yaml(contract_module._ALIASES_PATH),
            bad_stages_doc,
            contract_module._load_yaml(contract_module._RUNTIME_DOMAINS_PATH),
            contract_module._load_yaml(contract_module._SOURCE_STATE_SCHEMA_PATH),
            contract_module._load_yaml(contract_module._CONTRIBUTOR_OPERATIONS_PATH),
            contract_module._load_yaml(contract_module._COMPOSITE_DEPENDENCIES_PATH),
            contract_module._load_yaml(contract_module._QUARANTINE_REGISTRY_PATH),
            contract_module._load_yaml(contract_module._IDS_SECTION_ROUTING_PATH),
        ],
    ):
        with pytest.raises(StaticV2ContractError, match="bridge_missing_loadout_selector"):
            contract_module.load_static_v2_contract.__wrapped__()



def _fixture_snapshot():
    return compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))


def test_materialize_static_stages_emits_stage_family_metadata() -> None:
    materialized = materialize_static_stages(_fixture_snapshot())
    assert tuple(materialized.by_stage.keys()) == required_static_stages()
    assert tuple(materialized.families_by_stage.keys()) == required_static_stages()
    assert materialized.by_stage["baseline_account"]
    assert materialized.by_stage["baseline_gem_respec"]


def test_stage_materialization_keeps_families_in_compatible_stages() -> None:
    materialized = materialize_static_stages(_fixture_snapshot())

    baseline_account_families = set(materialized.families_by_stage["baseline_account"])
    baseline_gem_respec_families = set(materialized.families_by_stage["baseline_gem_respec"])
    baseline_loadout_families = set(materialized.families_by_stage["baseline_loadout"])

    assert "card" not in baseline_account_families
    assert "module_main" not in baseline_account_families
    assert "card" not in baseline_gem_respec_families
    assert "module_main" not in baseline_gem_respec_families
    assert baseline_loadout_families <= {"card", "module_main"}


def test_inventory_only_families_do_not_appear_in_loadout_stage() -> None:
    materialized = materialize_static_stages(_fixture_snapshot())
    loadout_families = set(materialized.families_by_stage["baseline_loadout"])
    assert loadout_families.isdisjoint({"workshop", "relic", "uw", "bot", "enhancement"})


def test_loadout_family_requires_selector_presence() -> None:
    snapshot = _fixture_snapshot()
    broken_bridge = deepcopy(contract_module.load_static_v2_contract().stage_bridge_by_family)
    broken_bridge["module_main"] = {
        **broken_bridge["module_main"],
        "loadout_selection_field": "missing_selector_field",
    }

    with pytest.raises(StaticV2ContractError, match="stage_materialization_missing_loadout_selector"):
        contract_module.load_static_v2_contract.cache_clear()
        try:
            with patch(
                "tower_sim.engines.static_pipeline_v2.load_static_v2_contract",
                side_effect=lambda: type("C", (), {
                    "required_static_stage_order": ("baseline_account", "baseline_gem_respec", "baseline_loadout"),
                    "stage_bridge_by_family": broken_bridge,
                })(),
            ):
                materialize_static_stages(snapshot)
        finally:
            contract_module.load_static_v2_contract.cache_clear()


def test_materialized_stage_inputs_emit_explicit_contributor_family_metadata() -> None:
    materialized = materialize_static_stages(_fixture_snapshot())
    account_inputs = materialized.by_stage["baseline_account"]
    assert any(item.contributor_family == "workshop" for item in account_inputs)
    assert any(item.contributor_family == "uw" for item in account_inputs)


def test_stage_validation_fails_for_incompatible_explicit_family_metadata() -> None:
    contract = load_static_v2_contract()
    snapshot = _fixture_snapshot()
    bad = [
        StatInput(
            stat_id="tower_damage",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="synthetic:test",
            contributor_family="card",
        )
    ]
    with pytest.raises(StaticV2ContractError, match="stage_materialization_family_not_allowed"):
        from tower_sim.engines.static_pipeline_v2 import _validate_stage_inputs_against_bridge

        _validate_stage_inputs_against_bridge(
            contract.stage_bridge_by_family,
            snapshot=snapshot,
            stage="baseline_account",
            stat_inputs=bad,
        )


def test_stage_materialization_outputs_remain_stable_against_compiler_surfaces() -> None:
    snapshot = _fixture_snapshot()
    materialized = materialize_static_stages(snapshot)

    account = compile_baseline_account_stat_inputs(snapshot)
    gem = compile_baseline_gem_respec_stat_inputs(snapshot)
    loadout = compile_baseline_loadout_stat_inputs(snapshot)

    assert len(materialized.by_stage["baseline_account"]) == len(account.stat_inputs)
    assert len(materialized.by_stage["baseline_gem_respec"]) == len(gem.stat_inputs)
    assert len(materialized.by_stage["baseline_loadout"]) == len(loadout.stat_inputs)
    assert {item.stat_id for item in materialized.by_stage["baseline_account"]} == {
        item.stat_id for item in account.stat_inputs
    }



def test_required_runtime_overlay_order_is_declared_and_valid() -> None:
    assert required_runtime_overlay_families() == (
        "perks",
        "battle_conditions",
        "cash_workshop_purchases",
        "free_upgrades",
        "eals_realized_effect",
        "ehls_realized_effect",
    )
    validate_required_runtime_overlay_families_present()


def test_runtime_overlays_materialize_separately_from_static_stages() -> None:
    snapshot = _fixture_snapshot()
    static_before = materialize_static_stages(snapshot)
    baseline_account_ids = {item.stat_id for item in static_before.by_stage["baseline_account"]}

    overlays = materialize_runtime_overlays(snapshot, stage_materialization=static_before)

    assert overlays.order == required_runtime_overlay_families()
    assert set(overlays.by_family.keys()) == set(required_runtime_overlay_families())
    assert all(row.stage == "runtime_overlay" for rows in overlays.by_family.values() for row in rows)

    static_after = materialize_static_stages(snapshot)
    assert {item.stat_id for item in static_after.by_stage["baseline_account"]} == baseline_account_ids


def test_runtime_overlay_families_are_all_materialized_with_rows() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    assert overlays.order == required_runtime_overlay_families()
    assert all(len(overlays.by_family[family]) > 0 for family in overlays.order)


def test_runtime_overlay_order_is_explicit_and_stable() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    assert overlays.order == (
        "perks",
        "battle_conditions",
        "cash_workshop_purchases",
        "free_upgrades",
        "eals_realized_effect",
        "ehls_realized_effect",
    )


def test_runtime_overlay_fails_closed_when_required_stat_missing() -> None:
    snapshot = _fixture_snapshot()
    static = materialize_static_stages(snapshot)
    stripped = [row for row in static.by_stage["baseline_gem_respec"] if row.stat_id != "eals_pct"]
    broken = StageMaterialization(
        by_stage={
            **static.by_stage,
            "baseline_gem_respec": stripped,
        },
        missing=static.missing,
        families_by_stage=static.families_by_stage,
    )
    with pytest.raises(StaticV2ContractError, match="runtime_overlay_missing_required_stat:eals_pct"):
        materialize_runtime_overlays(snapshot, stage_materialization=broken)




def test_runtime_state_materialization_includes_static_and_overlay_orders() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    assert runtime_state.static_stage_order == required_static_stages()
    assert tuple(runtime_state.stage_stat_inputs_by_stage.keys()) == required_static_stages()
    assert runtime_state.start_of_run_stat_inputs == runtime_state.stage_stat_inputs_by_stage["baseline_loadout"]
    assert tuple(runtime_state.stage_stat_values_by_stage.keys()) == required_static_stages()
    assert runtime_state.start_of_run_stat_values == runtime_state.stage_stat_values_by_stage["baseline_loadout"]
    assert runtime_state.stage_stat_inputs_by_stage["baseline_account"]
    assert "tower_hp" in runtime_state.stage_stat_values_by_stage["baseline_account"]
    assert any(row.stat_id == "eals_pct" for row in runtime_state.stage_stat_inputs_by_stage["baseline_gem_respec"])
    assert "eals_pct" in runtime_state.stage_stat_values_by_stage["baseline_gem_respec"]
    assert runtime_state.overlay_order == required_runtime_overlay_families()
    assert len(runtime_state.overlay_rows) == sum(runtime_state.overlay_counts.values())






def test_runtime_state_stage_stat_values_preserve_duplicate_contributors() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    tower_hp_values = runtime_state.stage_stat_values_by_stage["baseline_account"].get("tower_hp")
    assert tower_hp_values is not None
    assert len(tower_hp_values) >= 2





def test_runtime_state_fails_closed_when_stage_value_is_non_finite() -> None:
    snapshot = _fixture_snapshot()
    static = materialize_static_stages(snapshot)
    bad_input = StatInput(
        stat_id="tower_damage",
        phase=Phase.START_OF_RUN,
        base_value=float("nan"),
        provenance="synthetic:test",
        contributor_family="workshop",
    )
    broken = StageMaterialization(
        by_stage={
            **static.by_stage,
            "baseline_account": [*static.by_stage["baseline_account"], bad_input],
        },
        missing=static.missing,
        families_by_stage=static.families_by_stage,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_state_non_finite_value:baseline_account:tower_damage",
    ):
        materialize_runtime_state(snapshot, stage_materialization=broken)

def test_runtime_state_fails_closed_when_stage_input_phase_is_not_start_of_run() -> None:
    snapshot = _fixture_snapshot()
    static = materialize_static_stages(snapshot)
    bad_input = StatInput(
        stat_id="tower_damage",
        phase=Phase.END_OF_RUN,
        base_value=1.0,
        provenance="synthetic:test",
        contributor_family="workshop",
    )
    broken = StageMaterialization(
        by_stage={
            **static.by_stage,
            "baseline_account": [*static.by_stage["baseline_account"], bad_input],
        },
        missing=static.missing,
        families_by_stage=static.families_by_stage,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_state_unexpected_phase:baseline_account:tower_damage:end_of_run",
    ):
        materialize_runtime_state(snapshot, stage_materialization=broken)



def test_runtime_state_fails_closed_when_unexpected_overlay_family_present() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    broken = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            **overlays.by_family,
            "boss_state": [
                overlays.by_family["perks"][0].__class__(
                    family="boss_state",
                    stage="runtime_overlay",
                    payload={"note": "unexpected"},
                    provenance="synthetic:test",
                )
            ],
        },
    )
    with pytest.raises(
        StaticV2ContractError,
        match="runtime_state_unexpected_overlay_families:boss_state",
    ):
        materialize_runtime_state(_fixture_snapshot(), overlays=broken)

def test_runtime_state_fails_closed_when_overlay_family_missing() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    broken = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={k: v for k, v in overlays.by_family.items() if k != "perks"},
    )
    with pytest.raises(StaticV2ContractError, match="runtime_state_missing_overlay_family:perks"):
        materialize_runtime_state(_fixture_snapshot(), overlays=broken)


def test_runtime_state_fails_closed_when_overlay_family_empty() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    broken = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={**overlays.by_family, "perks": []},
    )
    with pytest.raises(StaticV2ContractError, match="runtime_state_empty_overlay_family:perks"):
        materialize_runtime_state(_fixture_snapshot(), overlays=broken)



def test_runtime_state_fails_closed_when_overlay_row_family_mismatches_bucket() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    perks_rows = overlays.by_family["perks"]
    broken = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            **overlays.by_family,
            "perks": [
                perks_rows[0].__class__(
                    family="battle_conditions",
                    stage=perks_rows[0].stage,
                    payload=perks_rows[0].payload,
                    provenance=perks_rows[0].provenance,
                )
            ],
        },
    )
    with pytest.raises(StaticV2ContractError, match="runtime_state_overlay_family_row_mismatch:perks:battle_conditions"):
        materialize_runtime_state(_fixture_snapshot(), overlays=broken)


def test_runtime_state_fails_closed_when_overlay_row_stage_unexpected() -> None:
    overlays = materialize_runtime_overlays(_fixture_snapshot())
    perks_rows = overlays.by_family["perks"]
    broken = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            **overlays.by_family,
            "perks": [
                perks_rows[0].__class__(
                    family=perks_rows[0].family,
                    stage="baseline_gem_respec",
                    payload=perks_rows[0].payload,
                    provenance=perks_rows[0].provenance,
                )
            ],
        },
    )
    with pytest.raises(StaticV2ContractError, match="runtime_state_overlay_stage_unexpected:perks:baseline_gem_respec"):
        materialize_runtime_state(_fixture_snapshot(), overlays=broken)

def test_runtime_overlay_fails_closed_when_overlay_table_missing() -> None:
    snapshot = _fixture_snapshot()
    with patch("tower_sim.engines.static_pipeline_v2._PERKS_TABLE_PATH", Path("tables/inputs/perks/not_real.csv")):
        with pytest.raises(StaticV2ContractError, match="runtime_overlay_missing_table"):
            materialize_runtime_overlays(snapshot)
