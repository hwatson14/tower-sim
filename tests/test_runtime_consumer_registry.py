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
from engine.runtime_consumer_registry import (
    assert_runtime_consumer_bundle_contract,
    assert_runtime_consumer_ownership_contract,
    impacted_runtime_consumers,
    list_runtime_consumer_rules,
)
from engine.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState


def test_runtime_consumer_registry_exposes_skip_consumers():
    rules = {rule.consumer_id: rule for rule in list_runtime_consumer_rules()}
    assert 'runtime_consumer::wave_progression.attack_wave' in rules
    assert 'runtime_consumer::wave_progression.health_wave' in rules
    assert rules['runtime_consumer::wave_progression.attack_wave'].source_node_ids == ('canonical_stat::enemy_attack_level_skip_pct',)
    assert rules['runtime_consumer::wave_progression.health_wave'].source_node_ids == ('canonical_stat::enemy_health_level_skip_pct',)


def test_impacted_runtime_consumers_filters_by_dirty_nodes():
    impacted = {rule.consumer_id for rule in impacted_runtime_consumers({'canonical_stat::enemy_attack_level_skip_pct'})}
    assert impacted == {'runtime_consumer::wave_progression.attack_wave'}


def test_runtime_consumers_consume_query_owned_surfaces_without_rederiving_them():
    ledger_rows = runtime_consumer_registry.ownership_rows_by_node()

    assert_runtime_consumer_ownership_contract()
    assert_runtime_consumer_bundle_contract()
    for rule in list_runtime_consumer_rules():
        consumer_row = ledger_rows[rule.consumer_id]
        assert consumer_row['ownership_status'] == 'simulator_owned'
        assert consumer_row['governed_by'] == 'runtime_simulation'
        assert tuple(consumer_row['consumes']) == rule.source_node_ids
        assert consumer_row['downstream_policy'] == 'consume_query_owned_surfaces_only'
        for source_node_id in rule.source_node_ids:
            source_row = ledger_rows[source_node_id]
            assert source_row['ownership_status'] == 'query_owned'
            assert source_row['governed_by'] == 'canonical_query_engine'
            assert source_row['downstream_policy'] == 'consume_only_no_rederivation'

@pytest.mark.parametrize(
    ('mutator', 'match'),
    [
        (
            lambda ledger: ledger['runtime_consumers'][0].__setitem__('governed_by', 'analysis_reporting'),
            'must be simulator_owned and governed_by runtime_simulation',
        ),
        (
            lambda ledger: ledger['runtime_consumers'][0].__setitem__('consumes', ['canonical_stat::tower_hp']),
            'ownership ledger consumes',
        ),
        (
            lambda ledger: next(
                row for row in ledger['surface_nodes'] if row['node_id'] == 'canonical_stat::enemy_attack_level_skip_pct'
            ).__setitem__('downstream_policy', 'rederive_allowed'),
            'must forbid downstream re-derivation',
        ),
    ],
)
def test_runtime_consumer_ownership_contract_fails_closed_for_invalid_ledgers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutator, match: str):
    ledger = copy.deepcopy(runtime_consumer_registry.load_surface_ownership_ledger())
    mutator(ledger)
    ledger_path = tmp_path / 'stat-query-surface-ownership-ledger.yaml'
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    monkeypatch.setattr(runtime_consumer_registry, '_OWNERSHIP_LEDGER_PATH', ledger_path)
    runtime_consumer_registry.load_surface_ownership_ledger.cache_clear()
    runtime_consumer_registry.ownership_rows_by_node.cache_clear()
    try:
        with pytest.raises(ValueError, match=match):
            assert_runtime_consumer_ownership_contract()
    finally:
        runtime_consumer_registry.load_surface_ownership_ledger.cache_clear()
        runtime_consumer_registry.ownership_rows_by_node.cache_clear()


def test_runtime_consumer_bundle_contract_fails_closed_for_mismatched_bundle_surfaces(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract = copy.deepcopy(runtime_consumer_registry.load_consumer_bundle_contract())
    contract['consumers'][1]['bundles'][0]['required_surface_ids'] = ['canonical_stat::enemy_health_level_skip_pct']
    contract_path = tmp_path / 'stat-query-consumer-bundles.yaml'
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    monkeypatch.setattr(runtime_consumer_registry, '_CONSUMER_BUNDLE_PATH', contract_path)
    runtime_consumer_registry.load_consumer_bundle_contract.cache_clear()
    runtime_consumer_registry.load_consumer_bundle_definitions.cache_clear()
    try:
        with pytest.raises(ValueError, match='do not match owned source nodes'):
            assert_runtime_consumer_bundle_contract()
    finally:
        runtime_consumer_registry.load_consumer_bundle_contract.cache_clear()
        runtime_consumer_registry.load_consumer_bundle_definitions.cache_clear()


def test_wave_progression_policy_attack_wave_is_monotonic_with_attack_skip_pct():
    policy = WaveProgressionPolicy()
    low = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.10, health_skip_pct=0.0)
    high = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.40, health_skip_pct=0.0)
    assert high.attack_wave < low.attack_wave
    assert high.health_wave == low.health_wave == 1000


def test_wave_progression_policy_health_wave_is_monotonic_with_health_skip_pct():
    policy = WaveProgressionPolicy()
    low = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.0, health_skip_pct=0.10)
    high = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.0, health_skip_pct=0.40)
    assert high.health_wave < low.health_wave
    assert high.attack_wave == low.attack_wave == 1000
