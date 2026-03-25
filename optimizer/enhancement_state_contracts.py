from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
from typing import Any, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
_WORKSHOP_PREP_CONTRACT_PATH = ROOT / 'kb' / 'workshop' / 'contracts' / 'enhancement-state-prep.yaml'
_OBSERVED_RUN_ELS_CONTRACT_PATH = ROOT / 'input' / 'observed_run_els_scenarios.contract.yaml'
_OBSERVED_RUN_ELS_INPUT_PATH = ROOT / 'input' / 'assumptions.yaml'

_ALLOWED_LABEL_STRENGTHS = frozenset({'strong_model', 'accepted_model'})
_ALLOWED_TRUST_LEVELS = frozenset({'strong_model', 'accepted_model'})
_ALLOWED_RUNTIME_STATUS = frozenset({'prep_only', 'runtime_pending'})
_REQUIRED_PREP_CONTRACT_KEYS = frozenset(
    {'change_classification', 'enhancement_surfaces', 'output_labels', 'future_query_bundle'}
)
_REQUIRED_SURFACE_KEYS = frozenset(
    {'surface_id', 'cost_table', 'value_table', 'formula_registry_key', 'current_value_owner', 'current_cost_owner'}
)
_REQUIRED_OUTPUT_LABEL_KEYS = frozenset({'strength', 'surface_ids', 'trust_payload', 'provenance_payload'})
_REQUIRED_TRUST_PAYLOAD_KEYS = frozenset(
    {
        'trust_level',
        'runtime_status',
        'truth_surface_ids',
        'cost_truth_table',
        'value_truth_table',
        'formula_owner',
        'owner_notes',
    }
)
_REQUIRED_PROVENANCE_PAYLOAD_KEYS = frozenset(
    {'kb_surface_paths', 'materialized_table_paths', 'accepted_inputs', 'contract_paths', 'notes'}
)
_REQUIRED_QUERY_BUNDLE_KEYS = frozenset(
    {'consumer_id', 'bundle_id', 'family_bundle_id', 'surface_ids', 'requirements'}
)
_REQUIRED_QUERY_BUNDLE_REQUIREMENT_KEYS = frozenset(
    {'family_scope', 'overlay_policy', 'runtime_owner_status', 'resolver_expectation', 'failure_mode'}
)
_REQUIRED_OBSERVED_RUN_CONTRACT_KEYS = frozenset(
    {'contract_id', 'required_fields', 'required_scenarios', 'allowed_scenario_kinds', 'allowed_skip_tracks', 'scenario_contracts'}
)
_REQUIRED_SCENARIO_CONTRACT_KEYS = frozenset(
    {'scenario_kind', 'skip_track', 'observed_run_label', 'notes_must_include'}
)


@dataclass(frozen=True)
class ObservedRunElsScenario:
    scenario_id: str
    scenario_kind: str
    skip_track: str
    observed_run_label: str
    enemy_level_skip_reduction_pp: float
    notes: str


@lru_cache(maxsize=1)
def load_enhancement_state_prep_contract() -> dict[str, Any]:
    raw = yaml.safe_load(_WORKSHOP_PREP_CONTRACT_PATH.read_text()) or {}
    missing = sorted(_REQUIRED_PREP_CONTRACT_KEYS - set(raw))
    if missing:
        raise ValueError(f'Enhancement prep contract missing required keys: {missing}.')

    surfaces = raw.get('enhancement_surfaces') or {}
    if not isinstance(surfaces, dict) or not surfaces:
        raise ValueError('Enhancement prep contract must declare enhancement_surfaces.')
    declared_surface_ids: set[str] = set()
    for surface_name, payload in surfaces.items():
        if not isinstance(payload, dict):
            raise ValueError(f'Enhancement surface {surface_name!r} must be a mapping.')
        missing_surface_keys = sorted(_REQUIRED_SURFACE_KEYS - set(payload))
        if missing_surface_keys:
            raise ValueError(f'Enhancement surface {surface_name!r} missing required keys: {missing_surface_keys}.')
        surface_id = str(payload['surface_id'])
        if surface_id in declared_surface_ids:
            raise ValueError(f'Duplicate enhancement surface_id {surface_id!r}.')
        declared_surface_ids.add(surface_id)
        for path_key in ('cost_table', 'value_table'):
            table_path = ROOT / str(payload[path_key])
            if not table_path.exists():
                raise ValueError(f'Enhancement surface {surface_name!r} references missing {path_key} {payload[path_key]!r}.')

    labels = raw.get('output_labels') or {}
    if not isinstance(labels, dict) or not labels:
        raise ValueError('Enhancement prep contract must declare output_labels.')
    for label_name, payload in labels.items():
        if not isinstance(payload, dict):
            raise ValueError(f'Output label {label_name!r} must be a mapping.')
        missing_label_keys = sorted(_REQUIRED_OUTPUT_LABEL_KEYS - set(payload))
        if missing_label_keys:
            raise ValueError(f'Output label {label_name!r} missing required keys: {missing_label_keys}.')
        strength = str(payload.get('strength') or '').strip()
        if strength not in _ALLOWED_LABEL_STRENGTHS:
            raise ValueError(f'Output label {label_name!r} must declare strength in {_ALLOWED_LABEL_STRENGTHS}.')
        surface_ids = tuple(str(surface_id) for surface_id in (payload.get('surface_ids') or ()))
        if not surface_ids:
            raise ValueError(f'Output label {label_name!r} must declare at least one surface_id.')
        undeclared_label_surface_ids = sorted(set(surface_ids) - declared_surface_ids)
        if undeclared_label_surface_ids:
            raise ValueError(
                f'Output label {label_name!r} references undeclared surface_ids: {undeclared_label_surface_ids}.'
            )

        trust_payload = payload.get('trust_payload') or {}
        missing_trust_payload_keys = sorted(_REQUIRED_TRUST_PAYLOAD_KEYS - set(trust_payload))
        if missing_trust_payload_keys:
            raise ValueError(f'Output label {label_name!r} trust_payload missing keys: {missing_trust_payload_keys}.')
        trust_level = str(trust_payload.get('trust_level') or '').strip()
        if trust_level not in _ALLOWED_TRUST_LEVELS:
            raise ValueError(f'Output label {label_name!r} trust_payload trust_level must be in {_ALLOWED_TRUST_LEVELS}.')
        runtime_status = str(trust_payload.get('runtime_status') or '').strip()
        if runtime_status not in _ALLOWED_RUNTIME_STATUS:
            raise ValueError(
                f'Output label {label_name!r} trust_payload runtime_status must be in {_ALLOWED_RUNTIME_STATUS}.'
            )
        truth_surface_ids = tuple(str(surface_id) for surface_id in (trust_payload.get('truth_surface_ids') or ()))
        if not truth_surface_ids:
            raise ValueError(f'Output label {label_name!r} trust_payload must declare truth_surface_ids.')
        undeclared_truth_surface_ids = sorted(set(truth_surface_ids) - declared_surface_ids)
        if undeclared_truth_surface_ids:
            raise ValueError(
                f'Output label {label_name!r} trust_payload references undeclared truth_surface_ids: '
                f'{undeclared_truth_surface_ids}.'
            )
        for path_key in ('cost_truth_table', 'value_truth_table', 'formula_owner'):
            path = ROOT / str(trust_payload[path_key])
            if not path.exists():
                raise ValueError(f'Output label {label_name!r} trust_payload references missing {path_key} {trust_payload[path_key]!r}.')

        provenance_payload = payload.get('provenance_payload') or {}
        missing_provenance_payload_keys = sorted(_REQUIRED_PROVENANCE_PAYLOAD_KEYS - set(provenance_payload))
        if missing_provenance_payload_keys:
            raise ValueError(
                f'Output label {label_name!r} provenance_payload missing keys: {missing_provenance_payload_keys}.'
            )
        for path_list_key in ('kb_surface_paths', 'materialized_table_paths', 'accepted_inputs', 'contract_paths'):
            values = tuple(str(path_value) for path_value in (provenance_payload.get(path_list_key) or ()))
            if not values:
                raise ValueError(f'Output label {label_name!r} provenance_payload must declare {path_list_key}.')
            for value in values:
                path = ROOT / value
                if not path.exists():
                    raise ValueError(
                        f'Output label {label_name!r} provenance_payload references missing {path_list_key} path {value!r}.'
                    )
        notes = tuple(str(note) for note in (provenance_payload.get('notes') or ()))
        if not notes:
            raise ValueError(f'Output label {label_name!r} provenance_payload must declare notes.')

    bundle = raw.get('future_query_bundle') or {}
    missing_bundle_keys = sorted(_REQUIRED_QUERY_BUNDLE_KEYS - set(bundle))
    if missing_bundle_keys:
        raise ValueError(f'Enhancement prep contract future_query_bundle missing keys: {missing_bundle_keys}.')
    bundle_surface_ids = tuple(str(surface_id) for surface_id in (bundle.get('surface_ids') or ()))
    if not bundle_surface_ids:
        raise ValueError('Enhancement prep contract future_query_bundle must declare surface_ids.')
    undeclared_bundle_surface_ids = sorted(set(bundle_surface_ids) - declared_surface_ids)
    if undeclared_bundle_surface_ids:
        raise ValueError(
            f'Enhancement prep contract future_query_bundle references undeclared surface_ids: {undeclared_bundle_surface_ids}.'
        )
    requirements = bundle.get('requirements') or {}
    missing_requirement_keys = sorted(_REQUIRED_QUERY_BUNDLE_REQUIREMENT_KEYS - set(requirements))
    if missing_requirement_keys:
        raise ValueError(
            'Enhancement prep contract future_query_bundle requirements missing keys: '
            f'{missing_requirement_keys}.'
        )

    return raw


@lru_cache(maxsize=1)
def load_observed_run_els_contract() -> dict[str, Any]:
    raw = yaml.safe_load(_OBSERVED_RUN_ELS_CONTRACT_PATH.read_text()) or {}
    missing = sorted(_REQUIRED_OBSERVED_RUN_CONTRACT_KEYS - set(raw))
    if missing:
        raise ValueError(f'Observed-run ELS contract missing required keys: {missing}.')

    required_fields = tuple(str(field_name) for field_name in (raw.get('required_fields') or ()))
    if not required_fields:
        raise ValueError('Observed-run ELS contract must declare required_fields.')
    required_scenarios = tuple(str(scenario_id) for scenario_id in (raw.get('required_scenarios') or ()))
    if not required_scenarios:
        raise ValueError('Observed-run ELS contract must declare required_scenarios.')
    allowed_scenario_kinds = tuple(str(value) for value in (raw.get('allowed_scenario_kinds') or ()))
    if not allowed_scenario_kinds:
        raise ValueError('Observed-run ELS contract must declare allowed_scenario_kinds.')
    allowed_skip_tracks = tuple(str(value) for value in (raw.get('allowed_skip_tracks') or ()))
    if not allowed_skip_tracks:
        raise ValueError('Observed-run ELS contract must declare allowed_skip_tracks.')

    scenario_contracts = raw.get('scenario_contracts') or {}
    if not isinstance(scenario_contracts, dict) or not scenario_contracts:
        raise ValueError('Observed-run ELS contract must declare scenario_contracts.')
    missing_scenario_contracts = sorted(set(required_scenarios) - set(scenario_contracts))
    if missing_scenario_contracts:
        raise ValueError(
            f'Observed-run ELS contract missing scenario_contracts for required_scenarios: {missing_scenario_contracts}.'
        )
    for scenario_id in required_scenarios:
        payload = scenario_contracts.get(scenario_id)
        if not isinstance(payload, dict):
            raise ValueError(f'Observed-run ELS contract scenario_contract {scenario_id!r} must be a mapping.')
        missing_scenario_keys = sorted(_REQUIRED_SCENARIO_CONTRACT_KEYS - set(payload))
        if missing_scenario_keys:
            raise ValueError(
                f'Observed-run ELS contract scenario_contract {scenario_id!r} missing required keys: {missing_scenario_keys}.'
            )
    return raw


@lru_cache(maxsize=1)
def load_observed_run_els_scenarios() -> tuple[ObservedRunElsScenario, ...]:
    contract = load_observed_run_els_contract()
    _text = _OBSERVED_RUN_ELS_INPUT_PATH.read_text()
    if _OBSERVED_RUN_ELS_INPUT_PATH.suffix in ('.yaml', '.yml'):
        raw = (yaml.safe_load(_text) or {}).get('observed_run_els_scenarios') or {}
    else:
        raw = json.loads(_text)
    scenarios = raw.get('scenarios')
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('Observed-run ELS input must declare a non-empty scenarios list.')

    required_fields = tuple(str(field_name) for field_name in (contract.get('required_fields') or ()))
    expected_ids = tuple(str(scenario_id) for scenario_id in (contract.get('required_scenarios') or ()))
    allowed_scenario_kinds = set(str(value) for value in (contract.get('allowed_scenario_kinds') or ()))
    allowed_skip_tracks = set(str(value) for value in (contract.get('allowed_skip_tracks') or ()))
    scenario_contracts = contract.get('scenario_contracts') or {}
    by_id: dict[str, ObservedRunElsScenario] = {}
    for index, payload in enumerate(scenarios):
        if not isinstance(payload, Mapping):
            raise ValueError(f'Observed-run ELS scenario index {index} must be a mapping.')
        missing = [field_name for field_name in required_fields if field_name not in payload]
        if missing:
            raise ValueError(f'Observed-run ELS scenario index {index} missing required fields: {missing}.')
        scenario = ObservedRunElsScenario(
            scenario_id=str(payload['scenario_id']),
            scenario_kind=str(payload['scenario_kind']),
            skip_track=str(payload['skip_track']),
            observed_run_label=str(payload['observed_run_label']),
            enemy_level_skip_reduction_pp=float(payload['enemy_level_skip_reduction_pp']),
            notes=str(payload['notes']),
        )
        if scenario.scenario_id in by_id:
            raise ValueError(f'Duplicate observed-run ELS scenario_id {scenario.scenario_id!r}.')
        if scenario.scenario_kind not in allowed_scenario_kinds:
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} has disallowed scenario_kind {scenario.scenario_kind!r}.'
            )
        if scenario.skip_track not in allowed_skip_tracks:
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} has disallowed skip_track {scenario.skip_track!r}.'
            )
        scenario_contract = scenario_contracts.get(scenario.scenario_id)
        if scenario_contract is None:
            raise ValueError(f'Observed-run ELS scenario {scenario.scenario_id!r} has no declared scenario_contract.')
        if scenario.scenario_kind != str(scenario_contract['scenario_kind']):
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} mismatches scenario_kind contract '
                f'{scenario_contract["scenario_kind"]!r}.'
            )
        if scenario.skip_track != str(scenario_contract['skip_track']):
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} mismatches skip_track contract '
                f'{scenario_contract["skip_track"]!r}.'
            )
        if scenario.observed_run_label != str(scenario_contract['observed_run_label']):
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} mismatches observed_run_label contract '
                f'{scenario_contract["observed_run_label"]!r}.'
            )
        notes_required_substring = str(scenario_contract['notes_must_include'])
        if notes_required_substring not in scenario.notes:
            raise ValueError(
                f'Observed-run ELS scenario {scenario.scenario_id!r} notes must include {notes_required_substring!r}.'
            )
        by_id[scenario.scenario_id] = scenario

    missing_scenarios = sorted(set(expected_ids) - set(by_id))
    if missing_scenarios:
        raise ValueError(f'Observed-run ELS input missing required scenarios: {missing_scenarios}.')
    return tuple(by_id[scenario_id] for scenario_id in expected_ids)
