from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qe.materializer as family_surface_registry
from engine.family_baseline_materializer import FamilyBaselineMaterializer
from engine.runtime_consumer_registry import list_runtime_consumer_rules
from engine.state_identity import StateIdentity
from models.stat_input import StatInput


REQUIRED_SURFACE_FIELDS = {
    'surface_id',
    'surface_kind',
    'surface_class',
    'domain',
    'owning_families',
    'query_resolvable_phase_1',
    'queryable_directly',
    'consumer_only',
    'support_only',
    'publish_default',
    'debug_only',
    'scenario_scoped',
    'semantics',
}
EXPECTED_SURFACE_KINDS = {'canonical_surface', 'support_surface', 'runtime_mechanic_surface', 'published_derived_surface'}
EXPECTED_SURFACE_CLASSES = {'surface', 'capability', 'environment', 'context_resource'}
REVIEWED_PROMOTION_DOMAINS = {'ultimate_weapons', 'modules', 'bots', 'guardians'}


def _registry_contract() -> dict:
    return family_surface_registry.load_surface_registry_contract()


def _ownership_ledger() -> dict:
    return family_surface_registry.load_surface_ownership_ledger()


def _all_surface_entries() -> list[tuple[str, dict]]:
    contract = _registry_contract()
    return [
        (group_id, entry)
        for group_id, group in (contract.get('families') or {}).items()
        for entry in (group.get('surfaces') or [])
    ]


def test_phase_1_surface_registry_entries_define_required_metadata_and_designations():
    entries = _all_surface_entries()

    assert entries
    for _, entry in entries:
        assert REQUIRED_SURFACE_FIELDS.issubset(entry)
        assert entry['surface_kind'] in EXPECTED_SURFACE_KINDS
        assert entry['surface_class'] in EXPECTED_SURFACE_CLASSES
        assert isinstance(entry['query_resolvable_phase_1'], bool)
        assert isinstance(entry['queryable_directly'], bool)
        assert isinstance(entry['consumer_only'], bool)
        assert isinstance(entry['support_only'], bool)
        assert isinstance(entry['publish_default'], bool)
        assert isinstance(entry['debug_only'], bool)
        assert isinstance(entry['scenario_scoped'], bool)
        is_published_derived = entry['surface_kind'] == 'published_derived_surface'
        if not is_published_derived:
            assert entry['query_resolvable_phase_1'] is True
        assert entry['queryable_directly'] is True
        if entry['surface_kind'] == 'support_surface':
            assert entry['support_only'] is True
            assert entry['surface_class'] == 'surface'
            assert entry.get('query_value_type') in {'scalar', 'count'}
        elif not is_published_derived:
            assert entry['support_only'] is False
        assert entry['consumer_only'] is False
        assert not (entry['debug_only'] and entry['publish_default'])
        assert str(entry['domain']).strip()
        assert str(entry['semantics']).strip()


def test_phase_1_surface_registry_has_no_duplicate_surface_ids():
    surface_ids = [entry['surface_id'] for _, entry in _all_surface_entries()]

    assert len(surface_ids) == len(set(surface_ids))


def test_every_family_owned_surface_is_declared_in_exactly_one_registry_location():
    family_surface_ids = family_surface_registry.load_family_surface_ids()
    family_contracts = family_surface_registry.load_family_contracts()
    declared_surface_ids = {entry['surface_id'] for _, entry in _all_surface_entries()}

    assert family_surface_ids
    assert set().union(*family_surface_ids.values()) == declared_surface_ids
    assert set(family_contracts) <= set(family_surface_ids)
    for family_id, surface_ids in family_surface_ids.items():
        assert surface_ids, family_id


def test_family_contracts_define_baseline_semantics_and_supported_compatibility_shape():
    family_contracts = family_surface_registry.load_family_contracts()

    assert family_contracts
    for family_id, contract in family_contracts.items():
        assert contract['family_group'] in {'timing', 'progression'}
        assert contract['state_mode'] == 'start_of_run'
        assert contract['mode_id']
        assert contract['scenario_kind'] in {'run', 'scenario_probe'}
        assert set(contract['baseline_semantics']) == {
            'deterministic',
            'immutable',
            'overlay_free',
            'bounded_to_declared_surface_set',
        }, family_id
        assert all(contract['baseline_semantics'].values()), family_id

def test_every_phase_1_surface_has_matching_query_ownership_ledger_coverage():
    ownership_rows = {row['node_id']: row for row in (_ownership_ledger().get('surface_nodes') or [])}

    for _, entry in _all_surface_entries():
        row = ownership_rows.get(entry['surface_id'])
        assert row is not None, entry['surface_id']
        assert row['ownership_status'] == 'query_owned'
        assert row['governed_by'] == 'canonical_query_engine'
        assert row['ownership_class'] == entry['surface_class']
        assert row['downstream_policy'] == 'consume_only_no_rederivation'


def test_every_bundle_referenced_surface_is_declared_within_its_family_group():
    contract = _registry_contract()

    for group_id, group in (contract.get('families') or {}).items():
        declared_surface_ids = {entry['surface_id'] for entry in (group.get('surfaces') or [])}
        for bundle in group.get('query_bundles') or []:
            assert set(bundle.get('surface_ids') or ()).issubset(declared_surface_ids), (group_id, bundle['bundle_id'])


def test_every_declared_runtime_consumer_is_backed_by_registry_rules():
    contract = _registry_contract()
    declared_consumers = {
        consumer_id
        for group in (contract.get('families') or {}).values()
        for consumer_id in (group.get('runtime_consumers') or [])
    }
    runtime_rules = {rule.consumer_id for rule in list_runtime_consumer_rules()}

    assert declared_consumers == runtime_rules


def test_promotion_review_covers_uw_bot_guardian_and_module_mechanic_style_nodes():
    reviewed_nodes = _registry_contract().get('promotion_review', {}).get('reviewed_nodes') or []

    assert reviewed_nodes
    reviewed_domains = {row['domain'] for row in reviewed_nodes}
    assert REVIEWED_PROMOTION_DOMAINS.issubset(reviewed_domains)
    assert {
        row['promotion_decision']
        for row in reviewed_nodes
    } == {'first_class_surface_entry', 'helper_debug_only_node'}


def test_module_contributors_are_split_into_main_unique_and_substat_source_classes():
    identity = StateIdentity('acct_demo_v1', 'loadout_demo', 'scenario_demo', 'branch_base')
    baseline = FamilyBaselineMaterializer().materialize_from_rows(
        identity,
        'timing_tournament_no_perks',
        (
            StatInput(
                stat_name='Galaxy Compressor',
                source_family='module',
                source_name='Galaxy Compressor',
                value=1.25,
                value_type='multiplier',
                stage='loadout_resolved',
                contributor_id='module.galaxy_compressor.main',
                provenance='test.module.main',
                destination_object_type='canonical_stat',
                destination_id='package_chance_pct',
                kb_mapped=True,
                notes='module_generator_main_effect',
            ),
            StatInput(
                stat_name='Galaxy Compressor::unique',
                source_family='module',
                source_name='Galaxy Compressor',
                value=13,
                value_type='seconds',
                stage='loadout_resolved',
                contributor_id='module.galaxy_compressor.unique',
                provenance='test.module.unique',
                destination_object_type='support_surface',
                destination_id='timing.gcomp_cooldown_reduction_seconds',
                kb_mapped=True,
                notes='module_generator_unique_effect:kb_module_unique_routed',
            ),
            StatInput(
                stat_name='Recovery Package Chance',
                source_family='module_substat',
                source_name='Galaxy Compressor',
                value=5,
                value_type='integer_pct',
                stage='loadout_resolved',
                contributor_id='module.galaxy_compressor.substat',
                provenance='test.module.substat',
                destination_object_type='canonical_stat',
                destination_id='package_chance_pct',
                kb_mapped=True,
                notes='module_generator_substat',
            ),
        ),
    )

    assert {row.contributor_id: row.source_class for row in baseline.contributor_rows if row.active} == {
        'module.galaxy_compressor.main': 'module_main',
        'module.galaxy_compressor.substat': 'module_substat',
        'module.galaxy_compressor.unique': 'module_unique',
    }


@pytest.mark.parametrize(
    ('mutation', 'match'),
    [
        (
            lambda contract: contract['families']['timing_v1']['surfaces'].append(
                copy.deepcopy(contract['families']['timing_v1']['surfaces'][0])
            ),
            'Duplicate surface_id',
        ),
        (
            lambda contract: contract['families']['timing_v1']['surfaces'][0]['owning_families'].append('missing_family'),
            'undeclared owning_families',
        ),
        (
            lambda contract: contract['families']['timing_v1']['query_bundles'][0]['surface_ids'].append('canonical_stat::missing_surface'),
            'undeclared surface_ids',
        ),
        (
            lambda contract: contract['families']['timing_v1']['surfaces'][0].pop('surface_class'),
            'missing required fields',
        ),
        (
            lambda contract: contract['families']['timing_v1']['surfaces'][0].__setitem__('surface_class', 'internal_only'),
            'unsupported surface_class',
        ),
        (
            lambda contract: None,
            'missing from the ownership ledger',
        ),
    ],
)
def test_surface_registry_loader_fails_closed_for_invalid_registry_references(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation, match: str):
    contract = copy.deepcopy(_registry_contract())
    mutation(contract)
    registry_path = tmp_path / 'stat-query-initial-surface-set.yaml'
    registry_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    monkeypatch.setattr(family_surface_registry, '_INITIAL_SURFACE_SET_PATH', registry_path)
    if match == 'missing from the ownership ledger':
        ledger = copy.deepcopy(_ownership_ledger())
        ledger['surface_nodes'] = [
            row for row in (ledger.get('surface_nodes') or [])
            if row.get('node_id') != contract['families']['timing_v1']['surfaces'][0]['surface_id']
        ]
        ledger_path = tmp_path / 'stat-query-surface-ownership-ledger.yaml'
        ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
        monkeypatch.setattr(family_surface_registry, '_OWNERSHIP_LEDGER_PATH', ledger_path)

    with pytest.raises(ValueError, match=match):
        family_surface_registry.load_family_surface_ids()
