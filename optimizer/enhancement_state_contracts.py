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
_OBSERVED_RUN_ELS_INPUT_PATH = ROOT / 'input' / 'observed_run_els_scenarios.json'

_ALLOWED_LABEL_STRENGTHS = frozenset({'strong_model', 'accepted_model'})
_REQUIRED_PREP_CONTRACT_KEYS = frozenset({'change_classification', 'enhancement_surfaces', 'output_labels', 'future_query_bundle'})
_REQUIRED_SURFACE_KEYS = frozenset({'surface_id', 'cost_table', 'value_table', 'formula_registry_key', 'current_value_owner', 'current_cost_owner'})
_REQUIRED_QUERY_BUNDLE_KEYS = frozenset({'consumer_id', 'bundle_id', 'family_bundle_id', 'surface_ids'})


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
    for surface_name, payload in surfaces.items():
        if not isinstance(payload, dict):
            raise ValueError(f'Enhancement surface {surface_name!r} must be a mapping.')
        missing_surface_keys = sorted(_REQUIRED_SURFACE_KEYS - set(payload))
        if missing_surface_keys:
            raise ValueError(f'Enhancement surface {surface_name!r} missing required keys: {missing_surface_keys}.')
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
        strength = str(payload.get('strength') or '').strip()
        if strength not in _ALLOWED_LABEL_STRENGTHS:
            raise ValueError(f'Output label {label_name!r} must declare strength in {_ALLOWED_LABEL_STRENGTHS}.')
        surface_ids = tuple(str(surface_id) for surface_id in (payload.get('surface_ids') or ()))
        if not surface_ids:
            raise ValueError(f'Output label {label_name!r} must declare at least one surface_id.')

    bundle = raw.get('future_query_bundle') or {}
    missing_bundle_keys = sorted(_REQUIRED_QUERY_BUNDLE_KEYS - set(bundle))
    if missing_bundle_keys:
        raise ValueError(f'Enhancement prep contract future_query_bundle missing keys: {missing_bundle_keys}.')
    if not tuple(str(surface_id) for surface_id in (bundle.get('surface_ids') or ())):
        raise ValueError('Enhancement prep contract future_query_bundle must declare surface_ids.')

    return raw


@lru_cache(maxsize=1)
def load_observed_run_els_contract() -> dict[str, Any]:
    raw = yaml.safe_load(_OBSERVED_RUN_ELS_CONTRACT_PATH.read_text()) or {}
    required_fields = tuple(str(field_name) for field_name in (raw.get('required_fields') or ()))
    if not required_fields:
        raise ValueError('Observed-run ELS contract must declare required_fields.')
    required_scenarios = tuple(str(scenario_id) for scenario_id in (raw.get('required_scenarios') or ()))
    if not required_scenarios:
        raise ValueError('Observed-run ELS contract must declare required_scenarios.')
    return raw


@lru_cache(maxsize=1)
def load_observed_run_els_scenarios() -> tuple[ObservedRunElsScenario, ...]:
    contract = load_observed_run_els_contract()
    raw = json.loads(_OBSERVED_RUN_ELS_INPUT_PATH.read_text())
    scenarios = raw.get('scenarios')
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('Observed-run ELS input must declare a non-empty scenarios list.')

    required_fields = tuple(str(field_name) for field_name in (contract.get('required_fields') or ()))
    expected_ids = tuple(str(scenario_id) for scenario_id in (contract.get('required_scenarios') or ()))
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
        by_id[scenario.scenario_id] = scenario

    missing_scenarios = sorted(set(expected_ids) - set(by_id))
    if missing_scenarios:
        raise ValueError(f'Observed-run ELS input missing required scenarios: {missing_scenarios}.')
    return tuple(by_id[scenario_id] for scenario_id in expected_ids)
