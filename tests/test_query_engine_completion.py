from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from engine.family_baseline_materializer import FamilyBaselineMaterializer
from engine.family_baseline_materializer import load_family_surface_ids
from engine.runtime_consumer_registry import (
    assert_runtime_consumer_bundle_contract,
    assert_runtime_consumer_ownership_contract,
    list_runtime_consumer_rules,
    load_consumer_bundle_definitions,
)
from engine.scenario_engine import ScenarioConfig
from engine.state_identity import compile_stat_inputs_with_identity
from engine.stat_query_kernel import StatQueryKernel
from engine.timing_engine import materialize_timing_family_baseline
from parsers.ids_parser import parse_ids


def _state() -> object:
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def _timing_state_for_family(family_id: str):
    state = _state()
    if family_id == 'timing_tournament_no_perks':
        return replace(
            state,
            default_preset='Tourney',
            active_card_preset='Tourney',
            active_module_preset='Tourney',
            active_perk_preset='Tourney',
        )
    return state


def _timing_config_for_family(family_id: str) -> tuple[ScenarioConfig, bool, str]:
    if family_id == 'timing_tournament_no_perks':
        return ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150), False, 'Tourney'
    if family_id == 'timing_farm_with_perks':
        return ScenarioConfig(mode_id='farming', tier=14), True, 'Farming'
    if family_id == 'timing_scenario_probe':
        return ScenarioConfig(mode_id='scenario_probe', tier=14), False, 'Farming'
    raise ValueError(f'Unsupported timing family {family_id!r}.')


def _baseline_for_family(family_id: str):
    if family_id.startswith('timing_'):
        scenario_config, perks_enabled, preset_name = _timing_config_for_family(family_id)
        return materialize_timing_family_baseline(
            account_state=_timing_state_for_family(family_id),
            family_id=family_id,
            preset_name=preset_name,
            scenario_config=scenario_config,
            perks_enabled=perks_enabled,
        )

    if family_id.startswith('progression_'):
        state = _state()
        perks_enabled = family_id.endswith('with_perks')
        materializer = FamilyBaselineMaterializer()
        materializer.assert_family_compatibility(
            family_id=family_id,
            state_mode='start_of_run',
            perks_enabled=perks_enabled,
            scenario_mode_id='progression',
        )
        bound = compile_stat_inputs_with_identity(
            state,
            preset_name='Farming',
            state_mode='start_of_run',
            runtime_branch_id='branch_base',
            perks_enabled=perks_enabled,
            scenario_context={'mode_id': 'progression'},
        )
        return materializer.materialize(bound, family_id)

    raise ValueError(f'Unsupported family {family_id!r}.')


@pytest.mark.parametrize(
    ('consumer_id', 'bundle_id'),
    sorted(
        key
        for key, definition in load_consumer_bundle_definitions().items()
        if definition.publish_default
    ),
)
def test_publish_default_consumer_bundles_resolve_through_bounded_query_stack(consumer_id: str, bundle_id: str):
    definitions = load_consumer_bundle_definitions()
    definition = definitions[(consumer_id, bundle_id)]
    family_id = definition.allowed_family_ids[0]
    baseline = _baseline_for_family(family_id)
    kernel = StatQueryKernel()
    response = kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=definition.required_surface_ids,
        trace_mode=definition.minimum_trace_mode,
    )

    assert response.family_id == family_id
    assert tuple(row.surface_id for row in response.resolved_surface_rows) == definition.required_surface_ids
    assert all(row.status in {'resolved', 'gated_off'} for row in response.resolved_surface_rows)
    if definition.minimum_trace_mode == 'none':
        assert response.contributor_rows == ()
    else:
        assert response.contributor_rows


def test_query_engine_completion_contracts_are_internally_consistent():
    assert_runtime_consumer_ownership_contract()
    assert_runtime_consumer_bundle_contract()
    definitions = load_consumer_bundle_definitions()
    assert definitions
    for definition in definitions.values():
        baseline = _baseline_for_family(definition.allowed_family_ids[0])
        available_surface_ids = set(baseline.contributor_rows_by_surface)
        assert set(definition.required_surface_ids).issubset(available_surface_ids)


def test_runtime_consumer_query_ownership_scope_is_complete_for_declared_phase1_consumers():
    assert_runtime_consumer_ownership_contract()
    assert_runtime_consumer_bundle_contract()
    definitions = load_consumer_bundle_definitions()
    runtime_rules = list_runtime_consumer_rules()

    runtime_bundle_keys = {
        key
        for key, definition in definitions.items()
        if definition.consumer_id.startswith('runtime_consumer::') and definition.publish_default
    }
    assert runtime_bundle_keys == {
        (rule.consumer_id, 'progression_wave_skips')
        for rule in runtime_rules
    }
    assert len(runtime_bundle_keys) == len(runtime_rules) == 2

    progression_runtime_bundle = definitions[('progression_runtime', 'progression_wave_skips')]
    assert progression_runtime_bundle.publish_default is True
    assert set(progression_runtime_bundle.required_surface_ids) == {
        source_node_id
        for rule in runtime_rules
        for source_node_id in rule.source_node_ids
    }


@pytest.mark.parametrize('family_id', sorted(load_family_surface_ids()))
def test_every_declared_family_surface_is_query_covered_and_resolvable(family_id: str):
    baseline = _baseline_for_family(family_id)
    declared_surface_ids = load_family_surface_ids()[family_id]

    assert declared_surface_ids.issubset(set(baseline.contributor_rows_by_surface))

    response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=tuple(sorted(declared_surface_ids)),
        trace_mode='contributors',
    )

    assert {row.surface_id for row in response.resolved_surface_rows} == set(declared_surface_ids)
    assert all(row.status in {'resolved', 'gated_off'} for row in response.resolved_surface_rows)
