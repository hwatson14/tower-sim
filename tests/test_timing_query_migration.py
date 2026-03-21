from __future__ import annotations

import copy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.scenario_engine import ScenarioConfig
from engine.stat_query_kernel import StatQueryKernel
from engine.timing_engine import (
    materialize_timing_family_baseline,
    resolve_timing_consumer_bundle,
    resolve_timing_family_query,
)
from tests.helpers import build_state


def _tourney_query_state():
    state = build_state()
    return replace(
        state,
        active_card_preset='Tourney',
        active_module_preset='Tourney',
        active_perk_preset='Tourney',
        default_preset='Tourney',
    )


def test_timing_query_rejects_tournament_perks_enabled():
    with pytest.raises(ValueError, match='tournament implies perks disabled'):
        materialize_timing_family_baseline(
            account_state=_tourney_query_state(),
            family_id='timing_tournament_no_perks',
            preset_name='Tourney',
            scenario_config=ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150),
            perks_enabled=True,
        )


def test_timing_query_package_card_assertions_hold():
    state_with_cards = _tourney_query_state()
    state_without_cards = copy.deepcopy(state_with_cards)
    state_without_cards.card_presets['Tourney'] = [
        card
        for card in state_without_cards.card_presets['Tourney']
        if card not in {'Recovery Package Chance', 'Wave Accelerator'}
    ]

    config = ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150)

    with_cards = resolve_timing_family_query(
        account_state=state_with_cards,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=config,
        perks_enabled=False,
        requested_surface_ids=('canonical_stat::package_chance_pct',),
        trace_mode='contributors',
    )
    without_cards = resolve_timing_family_query(
        account_state=state_without_cards,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=config,
        perks_enabled=False,
        requested_surface_ids=('canonical_stat::package_chance_pct',),
        trace_mode='contributors',
    )

    with_rows = {row.surface_id: row.final_value for row in with_cards.resolved_surface_rows}
    without_rows = {row.surface_id: row.final_value for row in without_cards.resolved_surface_rows}

    assert with_rows['canonical_stat::package_chance_pct'] > without_rows['canonical_stat::package_chance_pct']
    assert any(
        row.source_class == 'cards' and 'recovery_package_chance' in row.contributor_id
        for row in with_cards.contributor_rows
    )
    assert all(row.source_class != 'cards' for row in without_cards.contributor_rows)


def test_timing_query_wave_accelerator_assertions_hold():
    state_with_card = build_state()
    state_without_card = copy.deepcopy(state_with_card)
    state_without_card.card_presets['Farming'] = [
        card for card in state_without_card.card_presets['Farming'] if card != 'Wave Accelerator'
    ]
    config = ScenarioConfig(mode_id='farming', tier=14)

    with_card = resolve_timing_family_query(
        account_state=state_with_card,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
        requested_surface_ids=(
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'support_surface::timing.wave_duration_seconds_effective',
        ),
        trace_mode='contributors',
    )
    without_card_baseline = materialize_timing_family_baseline(
        account_state=state_without_card,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
    )

    resolved = {row.surface_id: row.final_value for row in with_card.resolved_surface_rows}
    assert resolved['runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration'] > 0
    assert resolved['support_surface::timing.wave_duration_seconds_effective'] < 35.0
    assert any('wave_accelerator' in row.contributor_id for row in with_card.contributor_rows)
    without_wave_accel = without_card_baseline.contributor_rows_by_surface['runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration'][0]
    assert without_wave_accel.active is False
    assert without_wave_accel.gate_reason == 'surface_absent_from_bound_inputs'
    assert resolved['support_surface::timing.wave_duration_seconds_effective'] == pytest.approx(16.1)


def test_timing_query_assist_slot_owns_and_traces_gcomp_surface():
    with_gcomp = _tourney_query_state()
    without_gcomp = copy.deepcopy(with_gcomp)
    without_gcomp.module_presets['Tourney']['generator'] = replace(
        without_gcomp.module_presets['Tourney']['generator'],
        assist=None,
    )

    config = ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=250)

    with_response = resolve_timing_family_query(
        account_state=with_gcomp,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=config,
        perks_enabled=False,
        requested_surface_ids=('support_surface::timing.gcomp_cooldown_reduction_seconds',),
        trace_mode='full_trace',
    )
    without_baseline = materialize_timing_family_baseline(
        account_state=without_gcomp,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=config,
        perks_enabled=False,
    )

    assert with_response.resolved_surface_rows[0].final_value > 0
    assert any(
        row.contributor_id == 'module__generator__galaxy_compressor__uw_cooldown_reduction_seconds@@galaxy compressor@@assist@@unique'
        for row in with_response.contributor_rows
    )
    assert 'support_surface::timing.gcomp_cooldown_reduction_seconds' in with_response.dependency_trace['dependency_closure']
    without_gcomp_row = without_baseline.contributor_rows_by_surface['support_surface::timing.gcomp_cooldown_reduction_seconds'][0]
    assert without_gcomp_row.active is False
    assert without_gcomp_row.gate_reason == 'surface_absent_from_bound_inputs'


def test_timing_query_replaces_base_uw_duration_rows_with_scenario_effective_values():
    state = _tourney_query_state()
    config = ScenarioConfig(
        mode_id='tournament',
        league='champion',
        tournament_wave=1000,
        bh_base_duration_s=30.0,
        gt_base_duration_s=40.0,
    )

    response = resolve_timing_family_query(
        account_state=state,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=config,
        perks_enabled=False,
        requested_surface_ids=(
            'mechanic_param::uw.black_hole.duration_seconds',
            'mechanic_param::uw.golden_tower.duration_seconds',
        ),
        trace_mode='contributors',
    )

    resolved = {row.surface_id: row.final_value for row in response.resolved_surface_rows}
    assert resolved['mechanic_param::uw.black_hole.duration_seconds'] < 30.0
    assert resolved['mechanic_param::uw.golden_tower.duration_seconds'] < 40.0
    assert all(
        row.provenance_ref == 'engine.timing_engine.compute_timing_surfaces'
        for row in response.contributor_rows
    )
    assert all(row.source_class == 'scenario_rules' for row in response.contributor_rows)


def test_timing_query_helper_matches_direct_kernel_resolution():
    state = build_state()
    config = ScenarioConfig(mode_id='farming', tier=14)
    requested_surface_ids = (
        'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
        'support_surface::timing.wave_duration_seconds_effective',
    )

    helper_response = resolve_timing_family_query(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
        requested_surface_ids=requested_surface_ids,
        trace_mode='full_trace',
    )
    baseline = materialize_timing_family_baseline(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
    )
    direct_response = StatQueryKernel().resolve_surfaces(
        baseline,
        requested_surface_ids=requested_surface_ids,
        trace_mode='full_trace',
    )

    assert helper_response.family_id == direct_response.family_id
    assert helper_response.resolved_surface_rows == direct_response.resolved_surface_rows
    assert helper_response.contributor_rows == direct_response.contributor_rows
    assert helper_response.dependency_trace == direct_response.dependency_trace


def test_timing_consumer_bundle_helper_matches_family_query_for_declared_bundle():
    state = build_state()
    config = ScenarioConfig(mode_id='farming', tier=14)

    bundle_response = resolve_timing_consumer_bundle(
        account_state=state,
        consumer_id='run_stats',
        bundle_id='timing_wave_duration',
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
        include_optional_surface_ids=(
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'canonical_stat::package_chance_pct',
        ),
        trace_mode='contributors',
    )
    family_response = resolve_timing_family_query(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=config,
        perks_enabled=True,
        requested_surface_ids=(
            'support_surface::timing.wave_duration_seconds_effective',
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'canonical_stat::package_chance_pct',
        ),
        trace_mode='contributors',
    )

    assert bundle_response.family_id == family_response.family_id
    assert bundle_response.resolved_surface_rows == family_response.resolved_surface_rows
    assert bundle_response.contributor_rows == family_response.contributor_rows
    assert bundle_response.dependency_trace == family_response.dependency_trace
