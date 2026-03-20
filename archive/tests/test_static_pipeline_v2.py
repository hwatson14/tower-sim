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
    audit_static_stage_baselines,
    build_runtime_execution_plan,
    execute_runtime_state_pass,
    materialize_and_execute_runtime_state,
    materialize_pre_combat_transition_artifact,
    materialize_runtime_execution_snapshot,
    materialize_runtime_state_transition_artifact,
    materialize_runtime_execution_phase_bundle,
    materialize_runtime_pre_combat_balance_sheet,
    materialize_runtime_transition_checkpoint,
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



def test_runtime_execution_pass_returns_deterministic_artifact() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())

    artifact = execute_runtime_state_pass(runtime_state)

    assert artifact.executed_overlay_order == required_runtime_overlay_families()
    assert artifact.applied_overlay_counts == runtime_state.overlay_counts
    assert len(artifact.execution_trace) == len(required_runtime_overlay_families())
    assert all(step.startswith("apply_overlay_family:") for step in artifact.execution_trace)
    assert len(artifact.start_of_run_stat_totals) > 0


def test_runtime_execution_pass_fails_closed_when_overlay_count_missing() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts={
            k: v for k, v in runtime_state.overlay_counts.items() if k != "perks"
        },
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_missing_overlay_count:perks",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_start_values_empty() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken_values = dict(runtime_state.start_of_run_stat_values)
    first_key = next(iter(broken_values.keys()))
    broken_values[first_key] = ()
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=broken_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_empty_start_values",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_overlay_count_mismatches_rows() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken_counts = dict(runtime_state.overlay_counts)
    broken_counts["perks"] = broken_counts["perks"] + 1
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=broken_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_overlay_count_mismatch:perks",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_overlay_row_stage_is_unexpected() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_row = runtime_state.overlay_rows[0]
    broken_rows = (
        first_row.__class__(
            family=first_row.family,
            stage="baseline_loadout",
            payload=first_row.payload,
            provenance=first_row.provenance,
        ),
        *runtime_state.overlay_rows[1:],
    )
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_plan_overlay_row_stage_unexpected",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_materialization_builds_state_and_execution_artifact() -> None:
    materialized = materialize_and_execute_runtime_state(_fixture_snapshot())

    assert materialized.runtime_state.overlay_order == required_runtime_overlay_families()
    assert materialized.execution_pass.executed_overlay_order == required_runtime_overlay_families()
    assert materialized.execution_pass.applied_overlay_counts == materialized.runtime_state.overlay_counts


def test_runtime_execution_pass_fails_closed_when_start_value_count_mismatches_inputs() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_key = next(iter(runtime_state.start_of_run_stat_values.keys()))
    broken_values = dict(runtime_state.start_of_run_stat_values)
    broken_values[first_key] = (*broken_values[first_key], 1.0)
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=broken_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_start_value_count_mismatch",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_start_values_missing() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values={},
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_missing_start_of_run_values",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_start_value_stat_unexpected() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken_values = dict(runtime_state.start_of_run_stat_values)
    broken_values["synthetic_unknown_stat"] = (1.0,)
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=broken_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_unexpected_start_value_stats:synthetic_unknown_stat",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_overlay_payload_missing_key() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_row = runtime_state.overlay_rows[0]
    broken_rows = (
        first_row.__class__(
            family=first_row.family,
            stage=first_row.stage,
            payload={},
            provenance=first_row.provenance,
        ),
        *runtime_state.overlay_rows[1:],
    )
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_overlay_payload_missing_key",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_overlay_payload_non_finite() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_row = runtime_state.overlay_rows[0]
    broken_rows = (
        first_row.__class__(
            family=first_row.family,
            stage=first_row.stage,
            payload={"reference_rows": float("nan")},
            provenance=first_row.provenance,
        ),
        *runtime_state.overlay_rows[1:],
    )
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_overlay_payload_non_finite",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_pass_fails_closed_when_overlay_row_provenance_missing() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_row = runtime_state.overlay_rows[0]
    broken_rows = (
        first_row.__class__(
            family=first_row.family,
            stage=first_row.stage,
            payload=first_row.payload,
            provenance="   ",
        ),
        *runtime_state.overlay_rows[1:],
    )
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_overlay_row_missing_provenance",
    ):
        execute_runtime_state_pass(broken)


def test_runtime_execution_plan_builds_ordered_steps_from_overlay_order() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())

    plan = build_runtime_execution_plan(runtime_state)

    assert len(plan.ordered_steps) == sum(runtime_state.overlay_counts.values())
    families = [step.family for step in plan.ordered_steps]
    assert families == list(required_runtime_overlay_families())
    assert plan.per_family_step_counts == runtime_state.overlay_counts


def test_runtime_execution_plan_fails_closed_when_overlay_order_unexpected() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=("perks",),
        overlay_rows=runtime_state.overlay_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_plan_overlay_order_unexpected",
    ):
        build_runtime_execution_plan(broken)


def test_runtime_execution_plan_fails_closed_when_overlay_rows_missing_for_family() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    broken_rows = tuple(row for row in runtime_state.overlay_rows if row.family != "perks")
    broken = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="runtime_execution_plan_missing_overlay_rows:perks",
    ):
        build_runtime_execution_plan(broken)


def test_runtime_execution_snapshot_builds_with_trace_and_totals() -> None:
    snapshot = materialize_runtime_execution_snapshot(_fixture_snapshot())

    assert snapshot.plan.per_family_step_counts == snapshot.execution_pass.applied_overlay_counts
    assert len(snapshot.execution_pass.execution_trace) == len(required_runtime_overlay_families())
    assert snapshot.start_of_run_grand_total > 0.0
    assert set(snapshot.overlay_numeric_totals_by_family.keys()) == set(required_runtime_overlay_families())


def test_runtime_execution_snapshot_fails_closed_when_trace_mismatch() -> None:
    runtime_snapshot = materialize_runtime_state(_fixture_snapshot())

    class _BrokenPass:
        executed_overlay_order = required_runtime_overlay_families()
        start_of_run_stat_totals = {"tower_hp": 1.0}
        applied_overlay_counts = runtime_snapshot.overlay_counts
        execution_trace = ("apply_overlay_family:perks:rows=999",)

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_and_execute_runtime_state",
        return_value=type("_M", (), {"runtime_state": runtime_snapshot, "execution_pass": _BrokenPass()})(),
    ):
        with pytest.raises(StaticV2ContractError, match="runtime_execution_snapshot_trace_mismatch"):
            materialize_runtime_execution_snapshot(_fixture_snapshot())


def test_runtime_execution_snapshot_fails_closed_when_overlay_payload_has_non_finite_number() -> None:
    runtime_state = materialize_runtime_state(_fixture_snapshot())
    first_row = runtime_state.overlay_rows[0]
    broken_rows = (
        first_row.__class__(
            family=first_row.family,
            stage=first_row.stage,
            payload={"reference_rows": float("nan")},
            provenance=first_row.provenance,
        ),
        *runtime_state.overlay_rows[1:],
    )
    broken_state = runtime_state.__class__(
        static_stage_order=runtime_state.static_stage_order,
        stage_stat_inputs_by_stage=runtime_state.stage_stat_inputs_by_stage,
        stage_stat_values_by_stage=runtime_state.stage_stat_values_by_stage,
        start_of_run_stat_inputs=runtime_state.start_of_run_stat_inputs,
        start_of_run_stat_values=runtime_state.start_of_run_stat_values,
        overlay_order=runtime_state.overlay_order,
        overlay_rows=broken_rows,
        overlay_counts=runtime_state.overlay_counts,
    )

    materialized = materialize_and_execute_runtime_state(_fixture_snapshot())
    broken_materialized = type(
        "_M",
        (),
        {"runtime_state": broken_state, "execution_pass": materialized.execution_pass},
    )()

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_and_execute_runtime_state",
        return_value=broken_materialized,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_execution_overlay_payload_non_finite",
        ):
            materialize_runtime_execution_snapshot(_fixture_snapshot())


def test_pre_combat_transition_artifact_builds_and_matches_snapshot_totals() -> None:
    artifact = materialize_pre_combat_transition_artifact(_fixture_snapshot())

    assert artifact.start_of_run_grand_total > 0.0
    assert len(artifact.ordered_transition_steps) > 0
    assert set(artifact.transition_totals_by_family.keys()) == set(required_runtime_overlay_families())


def test_pre_combat_transition_artifact_supports_multi_row_families_and_mixed_payload_shapes() -> None:
    snapshot = _fixture_snapshot()
    overlays = materialize_runtime_overlays(snapshot)
    row_cls = overlays.by_family["perks"][0].__class__

    custom = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            "perks": [
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 3, "bonus": 2.5, "note": "alpha", "flag": True},
                    provenance="table:custom_perks_a",
                ),
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 4, "bonus": 1.0, "note": "beta"},
                    provenance="table:custom_perks_b",
                ),
            ],
            "battle_conditions": [
                row_cls(
                    family="battle_conditions",
                    stage="runtime_overlay",
                    payload={"reference_rows": 5, "meta": "ok"},
                    provenance="table:custom_bc",
                )
            ],
            "cash_workshop_purchases": [
                row_cls(
                    family="cash_workshop_purchases",
                    stage="runtime_overlay",
                    payload={
                        "tracked_stats": 2,
                        "total_start_coin_level": 10,
                        "total_end_level": 14,
                        "total_expected_purchases": 4,
                        "note": "mixed",
                    },
                    provenance="ids:WS",
                )
            ],
            "free_upgrades": [
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.1, "defense": 0.2, "utility": 0.3, "bonus": 1, "flag": False},
                    provenance="static_stage:baseline_gem_respec",
                ),
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.4, "defense": 0.0, "utility": 0.6, "label": "row2"},
                    provenance="static_stage:baseline_gem_respec",
                ),
            ],
            "eals_realized_effect": [
                row_cls(
                    family="eals_realized_effect",
                    stage="runtime_overlay",
                    payload={"configured_skip_pct": 5.0, "workshop_level": 10, "extra": 1.5},
                    provenance="static_stage:baseline_gem_respec",
                )
            ],
            "ehls_realized_effect": [
                row_cls(
                    family="ehls_realized_effect",
                    stage="runtime_overlay",
                    payload={"configured_skip_pct": 6.0, "workshop_level": 11, "extra": 2.5},
                    provenance="static_stage:baseline_gem_respec",
                )
            ],
        },
    )

    artifact = materialize_pre_combat_transition_artifact(snapshot, overlays=custom)

    assert len(artifact.ordered_transition_steps) == 8
    assert artifact.transition_totals_by_family["perks"] == pytest.approx(10.5)
    assert artifact.transition_totals_by_family["free_upgrades"] == pytest.approx(2.6)


def test_pre_combat_transition_artifact_fails_closed_when_family_totals_mismatch_snapshot() -> None:
    snapshot = _fixture_snapshot()
    execution_snapshot = materialize_runtime_execution_snapshot(snapshot)
    broken_totals = dict(execution_snapshot.overlay_numeric_totals_by_family)
    broken_totals["perks"] = broken_totals["perks"] + 1.0
    broken_snapshot = execution_snapshot.__class__(
        plan=execution_snapshot.plan,
        execution_pass=execution_snapshot.execution_pass,
        overlay_numeric_totals_by_family=broken_totals,
        start_of_run_grand_total=execution_snapshot.start_of_run_grand_total,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_runtime_execution_snapshot",
        return_value=broken_snapshot,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_pre_combat_transition_family_total_mismatch:perks",
        ):
            materialize_pre_combat_transition_artifact(snapshot)


def test_runtime_state_transition_artifact_builds_from_pre_combat_artifact() -> None:
    artifact = materialize_runtime_state_transition_artifact(_fixture_snapshot())

    assert artifact.start_of_run_grand_total > 0.0
    assert artifact.final_pre_combat_total >= artifact.start_of_run_grand_total
    assert len(artifact.ordered_steps) > 0
    assert set(artifact.applied_totals_by_family.keys()) == set(required_runtime_overlay_families())


def test_runtime_state_transition_artifact_fails_closed_on_family_order_mismatch_with_multi_row_families() -> None:
    pre = materialize_pre_combat_transition_artifact(_fixture_snapshot())
    steps = list(pre.ordered_transition_steps)
    perks_steps = [s for s in steps if s.family == "perks"]
    free_steps = [s for s in steps if s.family == "free_upgrades"]
    others = [s for s in steps if s.family not in {"perks", "free_upgrades"}]
    if not free_steps:
        free_steps = [
            pre.ordered_transition_steps[0].__class__(
                family="free_upgrades",
                row_index=1,
                numeric_payload_total=1.0,
            )
        ]
        steps = [
            pre.ordered_transition_steps[0].__class__(
                family="perks",
                row_index=1,
                numeric_payload_total=1.0,
            ),
            *free_steps,
            *others,
        ]
        pre = pre.__class__(
            start_of_run_grand_total=pre.start_of_run_grand_total,
            transition_totals_by_family={
                **pre.transition_totals_by_family,
                "perks": 1.0,
                "free_upgrades": 1.0,
            },
            ordered_transition_steps=tuple(steps),
        )

    broken_steps = tuple([free_steps[0], *perks_steps, *others])
    broken = pre.__class__(
        start_of_run_grand_total=pre.start_of_run_grand_total,
        transition_totals_by_family=pre.transition_totals_by_family,
        ordered_transition_steps=broken_steps,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_pre_combat_transition_artifact",
        return_value=broken,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_state_transition_family_order_mismatch",
        ):
            materialize_runtime_state_transition_artifact(_fixture_snapshot())


def test_runtime_state_transition_artifact_fails_closed_on_row_index_mismatch_with_multi_rows() -> None:
    snapshot = _fixture_snapshot()
    overlays = materialize_runtime_overlays(snapshot)
    row_cls = overlays.by_family["perks"][0].__class__
    custom = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            **overlays.by_family,
            "perks": [
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 3},
                    provenance="table:custom_a",
                ),
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 4},
                    provenance="table:custom_b",
                ),
            ],
            "free_upgrades": [
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.1, "defense": 0.2, "utility": 0.3},
                    provenance="static_stage:baseline_gem_respec",
                ),
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.4, "defense": 0.5, "utility": 0.6},
                    provenance="static_stage:baseline_gem_respec",
                ),
            ],
        },
    )
    pre = materialize_pre_combat_transition_artifact(snapshot, overlays=custom)

    broken_steps = list(pre.ordered_transition_steps)
    perks_positions = [i for i, s in enumerate(broken_steps) if s.family == "perks"]
    if len(perks_positions) >= 2:
        second = broken_steps[perks_positions[1]]
        broken_steps[perks_positions[1]] = second.__class__(
            family=second.family,
            row_index=3,
            numeric_payload_total=second.numeric_payload_total,
        )
    broken = pre.__class__(
        start_of_run_grand_total=pre.start_of_run_grand_total,
        transition_totals_by_family=pre.transition_totals_by_family,
        ordered_transition_steps=tuple(broken_steps),
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_pre_combat_transition_artifact",
        return_value=broken,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_state_transition_row_index_mismatch:perks",
        ):
            materialize_runtime_state_transition_artifact(snapshot)


def test_runtime_transition_checkpoint_builds_and_balances_final_total() -> None:
    checkpoint = materialize_runtime_transition_checkpoint(_fixture_snapshot())

    assert checkpoint.total_delta_from_start >= 0.0
    assert checkpoint.expected_final_pre_combat_total == pytest.approx(
        checkpoint.transition.final_pre_combat_total
    )


def test_runtime_state_transition_artifact_fails_closed_on_interleaved_family_order_with_multi_rows() -> None:
    snapshot = _fixture_snapshot()
    overlays = materialize_runtime_overlays(snapshot)
    row_cls = overlays.by_family["perks"][0].__class__
    custom = RuntimeOverlayMaterialization(
        order=overlays.order,
        by_family={
            **overlays.by_family,
            "perks": [
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 3},
                    provenance="table:custom_perks_a",
                ),
                row_cls(
                    family="perks",
                    stage="runtime_overlay",
                    payload={"reference_rows": 4},
                    provenance="table:custom_perks_b",
                ),
            ],
            "free_upgrades": [
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.1, "defense": 0.2, "utility": 0.3},
                    provenance="static_stage:baseline_gem_respec",
                ),
                row_cls(
                    family="free_upgrades",
                    stage="runtime_overlay",
                    payload={"attack": 0.4, "defense": 0.5, "utility": 0.6},
                    provenance="static_stage:baseline_gem_respec",
                ),
            ],
        },
    )
    pre = materialize_pre_combat_transition_artifact(snapshot, overlays=custom)
    steps = list(pre.ordered_transition_steps)
    perks = [s for s in steps if s.family == "perks"]
    free = [s for s in steps if s.family == "free_upgrades"]
    others = [s for s in steps if s.family not in {"perks", "free_upgrades"}]
    assert len(perks) >= 2 and len(free) >= 1

    interleaved = (perks[0], free[0], perks[1], *others, *free[1:])
    broken = pre.__class__(
        start_of_run_grand_total=pre.start_of_run_grand_total,
        transition_totals_by_family=pre.transition_totals_by_family,
        ordered_transition_steps=interleaved,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_pre_combat_transition_artifact",
        return_value=broken,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_state_transition_family_order_mismatch:perks",
        ):
            materialize_runtime_state_transition_artifact(snapshot)


def test_runtime_transition_checkpoint_fails_closed_when_final_total_mismatch() -> None:
    transition = materialize_runtime_state_transition_artifact(_fixture_snapshot())
    broken = transition.__class__(
        start_of_run_grand_total=transition.start_of_run_grand_total,
        final_pre_combat_total=transition.final_pre_combat_total + 5.0,
        ordered_steps=transition.ordered_steps,
        applied_totals_by_family=transition.applied_totals_by_family,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_runtime_state_transition_artifact",
        return_value=broken,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_transition_checkpoint_final_total_mismatch",
        ):
            materialize_runtime_transition_checkpoint(_fixture_snapshot())


def test_runtime_pre_combat_balance_sheet_builds_in_required_family_order() -> None:
    sheet = materialize_runtime_pre_combat_balance_sheet(_fixture_snapshot())

    assert sheet.total_delta >= 0.0
    assert sheet.final_total == pytest.approx(sheet.start_total + sheet.total_delta)
    assert [family for family, _ in sheet.family_deltas_in_order] == list(required_runtime_overlay_families())


def test_runtime_pre_combat_balance_sheet_fails_closed_when_family_delta_missing() -> None:
    checkpoint = materialize_runtime_transition_checkpoint(_fixture_snapshot())
    broken_applied = {
        k: v for k, v in checkpoint.transition.applied_totals_by_family.items() if k != "perks"
    }
    broken_transition = checkpoint.transition.__class__(
        start_of_run_grand_total=checkpoint.transition.start_of_run_grand_total,
        final_pre_combat_total=checkpoint.transition.final_pre_combat_total,
        ordered_steps=checkpoint.transition.ordered_steps,
        applied_totals_by_family=broken_applied,
    )
    broken_checkpoint = checkpoint.__class__(
        transition=broken_transition,
        expected_final_pre_combat_total=checkpoint.expected_final_pre_combat_total,
        total_delta_from_start=checkpoint.total_delta_from_start,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_runtime_transition_checkpoint",
        return_value=broken_checkpoint,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_pre_combat_balance_sheet_missing_family_delta:perks",
        ):
            materialize_runtime_pre_combat_balance_sheet(_fixture_snapshot())


def test_runtime_transition_checkpoint_fails_closed_when_cumulative_total_is_non_monotonic() -> None:
    transition = materialize_runtime_state_transition_artifact(_fixture_snapshot())
    steps = list(transition.ordered_steps)
    first = steps[0]
    steps[0] = first.__class__(
        family=first.family,
        row_index=first.row_index,
        input_total=first.input_total,
        cumulative_total=transition.start_of_run_grand_total - 1.0,
    )
    broken_transition = transition.__class__(
        start_of_run_grand_total=transition.start_of_run_grand_total,
        final_pre_combat_total=transition.final_pre_combat_total,
        ordered_steps=tuple(steps),
        applied_totals_by_family=transition.applied_totals_by_family,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_runtime_state_transition_artifact",
        return_value=broken_transition,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_transition_checkpoint_non_monotonic_cumulative_total",
        ):
            materialize_runtime_transition_checkpoint(_fixture_snapshot())


def test_static_stage_baseline_audit_builds_deterministic_summary() -> None:
    audit = audit_static_stage_baselines(_fixture_snapshot())

    assert audit.stage_order == required_static_stages()
    for stage in required_static_stages():
        assert audit.stat_input_counts_by_stage[stage] > 0
        assert audit.unique_stat_counts_by_stage[stage] > 0
        assert audit.stage_total_values[stage] > 0.0


def test_static_stage_baseline_audit_fails_closed_when_stage_order_unexpected() -> None:
    snapshot = _fixture_snapshot()
    static = materialize_static_stages(snapshot)
    broken = StageMaterialization(
        by_stage={
            "baseline_gem_respec": static.by_stage["baseline_gem_respec"],
            "baseline_account": static.by_stage["baseline_account"],
            "baseline_loadout": static.by_stage["baseline_loadout"],
        },
        missing=static.missing,
        families_by_stage=static.families_by_stage,
    )

    with pytest.raises(
        StaticV2ContractError,
        match="static_stage_audit_stage_order_unexpected",
    ):
        audit_static_stage_baselines(snapshot, stage_materialization=broken)


def test_runtime_execution_phase_bundle_materializes_consistent_artifacts() -> None:
    bundle = materialize_runtime_execution_phase_bundle(_fixture_snapshot())

    assert bundle.static_stage_audit.stage_order == required_static_stages()
    assert bundle.execution_plan.per_family_step_counts == bundle.runtime_state.overlay_counts
    assert bundle.execution_pass.applied_overlay_counts == bundle.runtime_state.overlay_counts
    assert bundle.execution_snapshot.execution_pass == bundle.execution_pass
    assert bundle.transition_checkpoint.transition == bundle.runtime_state_transition
    assert bundle.pre_combat_balance_sheet.final_total == pytest.approx(
        bundle.transition_checkpoint.expected_final_pre_combat_total
    )


def test_runtime_execution_phase_bundle_fails_closed_when_balance_final_mismatches_checkpoint() -> None:
    sheet = materialize_runtime_pre_combat_balance_sheet(_fixture_snapshot())
    broken_sheet = sheet.__class__(
        start_total=sheet.start_total,
        final_total=sheet.final_total + 1.0,
        total_delta=sheet.total_delta,
        family_deltas_in_order=sheet.family_deltas_in_order,
    )

    with patch(
        "tower_sim.engines.static_pipeline_v2.materialize_runtime_pre_combat_balance_sheet",
        return_value=broken_sheet,
    ):
        with pytest.raises(
            StaticV2ContractError,
            match="runtime_phase_bundle_final_total_mismatch",
        ):
            materialize_runtime_execution_phase_bundle(_fixture_snapshot())
