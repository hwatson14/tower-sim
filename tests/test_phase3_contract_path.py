
import json
import re
import yaml
from pathlib import Path

from engine.query_currency_income import supported_manual_input_ids, unsupported_manual_input_ids

ROOT = Path(__file__).resolve().parents[1]

def test_phase3_contracts_registered_for_all_published_query_surfaces():
    initial = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-initial-surface-set.yaml').read_text())
    ledger = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-surface-ownership-ledger.yaml').read_text())
    code = (ROOT / 'engine/query_derived_composites.py').read_text()
    published = set(re.findall(r"_publish\(rows,\s*'([^']+)'", code))
    derived_surfaces = {s['surface_id'] for s in initial['families']['derived_v1']['surfaces']}
    ledger_nodes = {n['node_id'] for n in ledger['surface_nodes']}
    assert published
    assert published <= derived_surfaces
    assert published <= ledger_nodes
    for sid in ['derived::ehp','derived::ehp_ep','derived::edamage','derived::edamage_ep','derived::eecon','derived::eecon_ep','derived::economy.income.coins','derived::economy.income.gems','derived::economy.income.stones']:
        assert sid in derived_surfaces


def test_phase3_optimizer_bundle_required_surfaces_are_published_and_owned():
    initial = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-initial-surface-set.yaml').read_text())
    ledger = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-surface-ownership-ledger.yaml').read_text())
    bundles = yaml.safe_load((ROOT / 'kb/global-rules/contracts/stat-query-consumer-bundles.yaml').read_text())
    composites = (ROOT / 'engine/query_derived_composites.py').read_text()
    currency = (ROOT / 'engine/query_currency_income.py').read_text()

    published_composites = set(re.findall(r"_publish\(rows,\s*'([^']+)'", composites))
    published_income = set(re.findall(r"surface_id='([^']+)'", currency))
    published = published_composites | published_income

    bundle = next(c for c in bundles['consumers'] if c['consumer_id'] == 'optimizer_analysis')['bundles'][0]
    required = set(bundle['required_surface_ids'])
    optional = set(bundle['optional_surface_ids'])
    derived_surfaces = {s['surface_id'] for s in initial['families']['derived_v1']['surfaces']}
    ledger_nodes = {n['node_id'] for n in ledger['surface_nodes']}

    assert required <= published
    assert required <= derived_surfaces
    assert required <= ledger_nodes
    assert optional <= derived_surfaces
    assert optional <= ledger_nodes


def test_currency_income_contract_alignment_with_implementation_boundaries():
    contract = yaml.safe_load((ROOT / 'kb/economy/contracts/currency-income-surfaces-contract.yaml').read_text())
    implementation = (ROOT / 'engine/query_currency_income.py').read_text()
    manual_inputs = (yaml.safe_load((ROOT / 'input/assumptions.yaml').read_text(encoding='utf-8')) or {}).get('manual_advisory_inputs') or {}

    contract_currencies = contract['currencies']
    contract_surface_ids = {row['surface_id'] for row in contract_currencies}
    contract_manual_ids = {row['manual_input_id'] for row in contract_currencies if row.get('resolution_mode') == 'externalized_manual_input'}
    contract_deterministic_ids = {row['resource_id'] for row in contract_currencies if row.get('resolution_mode') == 'query_derived_deterministic'}
    contract_unsupported = {row['resource_id'] for row in contract['unsupported_resources']}

    implementation_manual_ids = set(re.findall(r"'([^']+)': \('derived::economy\.income\.[^']+', '[^']+'\)", implementation)) - {'coins'}
    implementation_supported_surfaces = set(re.findall(r"derived::economy\.income\.[a-z_]+", implementation))

    input_ids = {row['input_id'] for row in manual_inputs['inputs']}

    assert contract_deterministic_ids == {'coins'}
    assert contract_manual_ids == implementation_manual_ids
    assert contract_manual_ids <= input_ids
    assert contract_surface_ids <= implementation_supported_surfaces
    assert {'cash', 'cells', 'modules'} <= contract_unsupported
    assert 'derived::economy.income.cash' not in contract_surface_ids


def test_supported_and_unsupported_manual_input_ids_are_explicit():
    assert supported_manual_input_ids() == {
        'income.gems.per_week',
        'income.stones.per_week',
        'income.medals.per_week',
        'income.keys.per_week',
        'income.shards.per_week',
        'income.bits.per_week',
    }
    assert unsupported_manual_input_ids() == {
        'income.cash.per_week',
        'income.cells.per_week',
        'income.modules.per_week',
    }
