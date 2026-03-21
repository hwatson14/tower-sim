from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import optimizer.enhancement_state_contracts as enhancement_state_contracts
from optimizer.enhancement_state_contracts import (
    load_enhancement_state_prep_contract,
    load_observed_run_els_contract,
    load_observed_run_els_scenarios,
)


def test_enhancement_state_prep_contract_loads_and_pins_expected_bundle():
    contract = load_enhancement_state_prep_contract()

    assert contract['change_classification'] == ['Routing correction', 'Output correction']
    assert contract['future_query_bundle']['bundle_id'] == 'optimizer_enhancement_state'
    assert contract['output_labels']['strong_model_coin_bonus']['strength'] == 'strong_model'
    assert contract['output_labels']['accepted_model_els_helpers']['strength'] == 'accepted_model'


def test_observed_run_els_contract_and_inputs_load_in_declared_order():
    contract = load_observed_run_els_contract()
    scenarios = load_observed_run_els_scenarios()

    assert tuple(contract['required_scenarios']) == (
        'observed_run_enemy_attack_skip',
        'observed_run_enemy_health_skip',
    )
    assert tuple(scenario.scenario_id for scenario in scenarios) == tuple(contract['required_scenarios'])
    assert {scenario.skip_track for scenario in scenarios} == {
        'enemy_attack_level_skip',
        'enemy_health_level_skip',
    }


def test_observed_run_els_inputs_fail_closed_for_missing_required_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    payload = json.loads((ROOT / 'input' / 'observed_run_els_scenarios.json').read_text())
    del payload['scenarios'][0]['enemy_level_skip_reduction_pp']
    input_path = tmp_path / 'observed_run_els_scenarios.json'
    input_path.write_text(json.dumps(payload, indent=2))
    monkeypatch.setattr(enhancement_state_contracts, '_OBSERVED_RUN_ELS_INPUT_PATH', input_path)
    enhancement_state_contracts.load_observed_run_els_scenarios.cache_clear()
    try:
        with pytest.raises(ValueError, match='missing required fields'):
            load_observed_run_els_scenarios()
    finally:
        enhancement_state_contracts.load_observed_run_els_scenarios.cache_clear()


def test_observed_run_els_inputs_fail_closed_for_missing_required_scenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    payload = json.loads((ROOT / 'input' / 'observed_run_els_scenarios.json').read_text())
    payload['scenarios'] = payload['scenarios'][:1]
    input_path = tmp_path / 'observed_run_els_scenarios.json'
    input_path.write_text(json.dumps(payload, indent=2))
    monkeypatch.setattr(enhancement_state_contracts, '_OBSERVED_RUN_ELS_INPUT_PATH', input_path)
    enhancement_state_contracts.load_observed_run_els_scenarios.cache_clear()
    try:
        with pytest.raises(ValueError, match='missing required scenarios'):
            load_observed_run_els_scenarios()
    finally:
        enhancement_state_contracts.load_observed_run_els_scenarios.cache_clear()


def test_enhancement_state_prep_contract_fails_closed_for_missing_value_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract = copy.deepcopy(load_enhancement_state_prep_contract())
    contract['enhancement_surfaces']['coin_bonus']['value_table'] = 'kb/workshop/derived/materialized/does-not-exist.csv'
    contract_path = tmp_path / 'enhancement-state-prep.yaml'
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    monkeypatch.setattr(enhancement_state_contracts, '_WORKSHOP_PREP_CONTRACT_PATH', contract_path)
    enhancement_state_contracts.load_enhancement_state_prep_contract.cache_clear()
    try:
        with pytest.raises(ValueError, match='references missing value_table'):
            load_enhancement_state_prep_contract()
    finally:
        enhancement_state_contracts.load_enhancement_state_prep_contract.cache_clear()

