from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine.runtime_consumer_registry as runtime_consumer_registry
import engine.dependency_registry as dependency_registry
import engine.incremental_subset_executor as incremental_subset_executor
import engine.family_baseline_materializer as family_surface_registry
from engine.incremental_recalc_runtime import IncrementalRecalcRuntime
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.runtime_consumer_registry import resolve_consumer_bundle
from engine.dependency_registry import DependencyRegistry
from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from parsers.ids_parser import parse_ids


def test_consumer_bundle_registry_resolves_declared_bundle_with_optional_surfaces():
    resolved = resolve_consumer_bundle(
        'run_stats',
        'timing_wave_duration',
        family_id='timing_farm_with_perks',
        include_optional_surface_ids=('state::cards.wave_accelerator.spawn_rate_acceleration',),
        trace_mode='contributors',
    )

    assert resolved.family_id == 'timing_farm_with_perks'
    assert resolved.surface_ids == (
        'support_surface::timing.wave_duration_seconds_effective',
        'state::cards.wave_accelerator.spawn_rate_acceleration',
    )
    assert resolved.overlays_allowed is True


def test_consumer_bundle_registry_fails_closed_for_undeclared_consumer():
    with pytest.raises(ValueError, match='Undeclared consumer'):
        resolve_consumer_bundle('not_a_real_consumer', 'timing_wave_duration', family_id='timing_farm_with_perks')


def test_consumer_bundle_registry_fails_closed_for_family_mismatch():
    with pytest.raises(ValueError, match='not allowed for family_id'):
        resolve_consumer_bundle('run_stats', 'timing_wave_duration', family_id='progression_runtime_no_perks')


def test_consumer_bundle_registry_fails_closed_for_request_all_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract = copy.deepcopy(runtime_consumer_registry.load_consumer_bundle_contract())
    contract['consumers'][0]['bundles'][0]['required_surface_ids'].append('support_surface::free_upgrade_multiplier')
    contract_path = tmp_path / 'stat-query-consumer-bundles.yaml'
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    monkeypatch.setattr(runtime_consumer_registry, '_CONSUMER_BUNDLE_PATH', contract_path)
    runtime_consumer_registry.load_consumer_bundle_contract.cache_clear()
    runtime_consumer_registry.load_consumer_bundle_definitions.cache_clear()
    try:
        # explicit contract is allowed; the failure case is asking for undeclared optional surfaces after saturating the bundle
        with pytest.raises(ValueError, match='undeclared optional surfaces'):
            resolve_consumer_bundle(
                'run_stats',
                'progression_free_upgrades',
                family_id='progression_runtime_no_perks',
                include_optional_surface_ids=('state::tower.hp',),
            )
    finally:
        runtime_consumer_registry.load_consumer_bundle_contract.cache_clear()
        runtime_consumer_registry.load_consumer_bundle_definitions.cache_clear()


def test_dependency_registry_covers_bundle_reachable_surfaces_and_runtime_consumers():
    registry = DependencyRegistry.load_default()

    assert registry.node('support_surface::timing.wave_duration_seconds_effective') is not None
    assert 'runtime_consumer::wave_progression.attack_wave' in registry.closure_downstream({'state::tower.enemy_attack_level_skip_pct'})


def test_consumer_bundle_contract_covers_current_phase1_bounded_consumers():
    definitions = runtime_consumer_registry.load_consumer_bundle_definitions()
    declared_consumers = {consumer_id for consumer_id, _ in definitions}
    assert {
        'run_stats',
        'progression_runtime',
        'runtime_consumer::wave_progression.attack_wave',
        'runtime_consumer::wave_progression.health_wave',
        'optimizer_analysis',
        'advisor_reporting',
    }.issubset(declared_consumers)


def test_dependency_registry_fails_closed_for_missing_dependency_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ledger = copy.deepcopy(dependency_registry.load_dependency_ledger())
    ledger['nodes'] = [row for row in ledger['nodes'] if row['node_id'] != 'support_surface::timing.wave_duration_seconds_effective']
    ledger_path = tmp_path / 'stat-query-dependency-invalidation-ledger.yaml'
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    monkeypatch.setattr(dependency_registry, '_DEPENDENCY_LEDGER_PATH', ledger_path)
    dependency_registry.load_dependency_ledger.cache_clear()
    try:
        with pytest.raises(ValueError, match='undeclared node'):
            DependencyRegistry.load_default()
    finally:
        dependency_registry.load_dependency_ledger.cache_clear()


def test_dependency_registry_fails_closed_for_publishable_cycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ledger = copy.deepcopy(dependency_registry.load_dependency_ledger())
    ledger['edges'].append(
        {
            'upstream_node_id': 'state::wall.hp',
            'downstream_node_id': 'state::tower.hp',
            'invalidation_semantics': 'recompute_downstream',
            'mutation_classes': ['workshop_mutation'],
            'publication_relevance': 'publishable_path',
            'verification_status': 'verified',
            'notes': 'invalid cycle for test',
        }
    )
    ledger_path = tmp_path / 'stat-query-dependency-invalidation-ledger.yaml'
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    monkeypatch.setattr(dependency_registry, '_DEPENDENCY_LEDGER_PATH', ledger_path)
    dependency_registry.load_dependency_ledger.cache_clear()
    try:
        with pytest.raises(ValueError, match='Cycle or unresolved dependency ordering'):
            DependencyRegistry.load_default()
    finally:
        dependency_registry.load_dependency_ledger.cache_clear()


def test_dependency_registry_derives_required_mutation_classes_from_family_contracts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    raw_contract = yaml.safe_load((ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-scenario-families.yaml').read_text())
    raw_contract['family_groups']['progression']['families']['progression_runtime_no_perks']['allowed_overlay_types'].append('brand_new_overlay_type')
    contract_path = tmp_path / 'stat-query-scenario-families.yaml'
    contract_path.write_text(yaml.safe_dump(raw_contract, sort_keys=False))
    monkeypatch.setattr(family_surface_registry, '_FAMILY_CONTRACT_PATH', contract_path)
    dependency_registry.load_dependency_ledger.cache_clear()
    try:
        with pytest.raises(ValueError, match='Mutation classes missing invalidation mappings'):
            DependencyRegistry.load_default()
    finally:
        dependency_registry.load_dependency_ledger.cache_clear()


def test_planner_returns_minimal_closure_for_progression_bundle():
    plan = IncrementalRecalcRuntime().plan_consumer_bundle(
        consumer_id='run_stats',
        bundle_id='progression_free_upgrades',
        family_id='progression_runtime_with_perks',
        include_optional_surface_ids=('support_surface::free_upgrade_multiplier',),
        trace_mode='contributors',
    )

    assert plan.fallback_required is False
    assert plan.requested_surfaces == [
        'state::tower.free_attack_upgrade_chance_pct',
        'state::tower.free_defense_upgrade_chance_pct',
        'state::tower.free_utility_upgrade_chance_pct',
        'support_surface::free_upgrade_multiplier',
    ]
    assert sorted(plan.upstream_dependency_closure) == sorted(
        [
            'state::tower.free_attack_upgrade_chance_pct',
            'state::tower.free_defense_upgrade_chance_pct',
            'state::tower.free_utility_upgrade_chance_pct',
            'source_input::workshop:Free Attack Upgrade',
            'source_input::workshop:Free Defense Upgrade',
            'source_input::workshop:Free Utility Upgrade',
            'support_surface::free_upgrade_multiplier',
        ]
    )


def test_planner_returns_minimal_dirty_closure_for_mutation_and_runtime_consumers():
    plan = IncrementalRecalcRuntime().plan_overlay_mutation(
        family_id='progression_runtime_no_perks',
        mutation_class='workshop_mutation',
        trigger_keys=('Enemy Attack Level Skip',),
        consumer_id='progression_runtime',
        bundle_id='progression_wave_skips',
    )

    assert plan.fallback_required is False
    assert plan.mutated_source_nodes == ['source_input::workshop:Enemy Attack Level Skip']
    assert plan.runtime_consumer_ids == ['runtime_consumer::wave_progression.attack_wave']
    assert plan.publishable_closure == ['state::tower.enemy_attack_level_skip_pct']


def test_planner_populates_fallback_reason_for_invalid_surface_request():
    plan = IncrementalRecalcRuntime().plan_surface_request(
        family_id='timing_farm_with_perks',
        surface_ids=('state::tower.hp',),
    )

    assert plan.fallback_required is True
    assert 'outside family' in str(plan.fallback_reason)


def test_planned_progression_bundle_executes_natively_without_full_statbook(monkeypatch):
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    stat_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)
    plan = IncrementalRecalcRuntime().plan_consumer_bundle(
        consumer_id='progression_runtime',
        bundle_id='progression_wave_skips',
        family_id='progression_runtime_with_perks',
        trace_mode='contributors',
    )

    def _boom(_):
        raise AssertionError('resolve_stats should not be used by the bounded planned executor path')

    monkeypatch.setattr(incremental_subset_executor, 'resolve_stats', _boom, raising=False)
    candidate = IncrementalSubsetExecutor().execute(
        stat_inputs,
        plan.publishable_dirty_nodes,
        family_id=plan.family_id,
    )

    assert sorted(candidate) == sorted(plan.publishable_dirty_nodes)
    assert candidate['state::tower.enemy_attack_level_skip_pct'].status == 'resolved'
    assert candidate['state::tower.enemy_health_level_skip_pct'].status == 'resolved'
