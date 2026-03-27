from __future__ import annotations

from dataclasses import replace as dc_replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.stat_input_compiler import compile_stat_inputs
from engine.scenario_engine import ScenarioConfig
from engine.stat_engine import resolve_stats
from engine.stat_query_kernel import StatQueryKernel
from engine.timing_engine import compile_timing_family_rows
from models.statbook import StatBook, StatRow
try:
    from helpers import build_family_baseline, build_state
except (ImportError, AttributeError) as _skip_reason:
    pytest.skip(f'missing test helper: {_skip_reason}', allow_module_level=True)


_PROGRESSSION_ASSERTED_SURFACE_IDS = (
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'support_surface::free_upgrade_multiplier',
)


def test_resolve_stats_delegates_only_unambiguous_manifest_approved_tournament_timing_family(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150),
        perks_enabled=False,
    )
    seen = {'fallback_calls': 0, 'delegated_rows': None}

    def _fake_fallback(rows):
        seen['fallback_calls'] += 1
        return StatBook(
            rows={
                'mechanic_param::uw.black_hole.cooldown_seconds': StatRow(
                    stat_name='mechanic_param::uw.black_hole.cooldown_seconds',
                    final_value=999.0,
                    value_type='seconds',
                    source_count=1,
                    status='resolved',
                ),
                'raw::untouched': StatRow(
                    stat_name='untouched',
                    final_value='fallback',
                    value_type='raw',
                    source_count=1,
                    status='unmapped',
                ),
            },
            diagnostics={'source': 'fallback'},
        )

    def _fake_delegate(*, family_id, stat_inputs):
        seen['delegated_rows'] = list(stat_inputs)

        class _Response:
            resolved_surface_rows = (
                type('Row', (), {
                    'surface_id': 'mechanic_param::uw.black_hole.cooldown_seconds',
                    'final_value': 12.5,
                    'value_type': 'seconds',
                    'status': 'resolved',
                })(),
            )
            contributor_rows = (
                type('Contributor', (), {
                    'surface_id': 'mechanic_param::uw.black_hole.cooldown_seconds',
                    'surface_class': 'surface',
                    'domain': 'ultimate_weapons',
                    'source_class': 'scenario_rules',
                    'composition_stage': 'scenario_runtime',
                    'contributor_id': 'timing.black_hole.effective_cooldown',
                    'value': 12.5,
                    'value_type': 'seconds',
                    'active': True,
                    'gate_reason': '',
                    'provenance_ref': 'test',
                })(),
            )

        assert family_id == 'timing_tournament_no_perks'
        return _Response()

    monkeypatch.setattr('qe.routing._fallback_resolve_stats', _fake_fallback)
    monkeypatch.setattr('qe.routing._resolve_manifest_approved_family', _fake_delegate)

    resolved = resolve_stats(list(timing_rows))

    assert seen['fallback_calls'] == 1
    assert seen['delegated_rows'] is not None
    assert resolved.rows['mechanic_param::uw.black_hole.cooldown_seconds'].final_value == 12.5
    assert resolved.rows['raw::untouched'].final_value == 'fallback'
    assert resolved.diagnostics['resolve_stats_delegation']['delegated_family_id'] == 'timing_tournament_no_perks'
    assert resolved.diagnostics['resolve_stats_delegation']['bounded_only'] is True


def test_resolve_stats_delegates_progression_surface_contract_when_identifiable(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    progression_rows = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )
    seen = {'fallback_calls': 0, 'delegated_family_id': None}

    def _fake_fallback(rows):
        seen['fallback_calls'] += 1
        return StatBook(
            rows={
                'state::tower.enemy_attack_level_skip_pct': StatRow(
                    stat_name='state::tower.enemy_attack_level_skip_pct',
                    final_value=1.0,
                    value_type='percent',
                    source_count=1,
                    status='resolved',
                ),
                'raw::untouched': StatRow(
                    stat_name='raw::untouched',
                    final_value='fallback',
                    value_type='raw',
                    source_count=1,
                    status='unmapped',
                ),
            },
            diagnostics={'source': 'fallback'},
        )

    def _fake_delegate(*, family_id, stat_inputs):
        seen['delegated_family_id'] = family_id

        class _Response:
            resolved_surface_rows = (
                type('Row', (), {
                    'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                    'final_value': 35.0,
                    'value_type': 'percent_display',
                    'status': 'resolved',
                })(),
            )
            contributor_rows = (
                type('Contributor', (), {
                    'surface_id': 'state::tower.enemy_attack_level_skip_pct',
                    'surface_class': 'surface',
                    'domain': 'base',
                    'source_class': 'workshop',
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'workshop__enemy_attack_level_skip_pct',
                    'value': 35.0,
                    'value_type': 'percent_display',
                    'active': True,
                    'gate_reason': '',
                    'provenance_ref': 'test',
                })(),
            )

        return _Response()

    monkeypatch.setattr('qe.routing._fallback_resolve_stats', _fake_fallback)
    monkeypatch.setattr('qe.routing._resolve_manifest_approved_family', _fake_delegate)

    resolved = resolve_stats(progression_rows)

    assert seen['fallback_calls'] == 1
    assert seen['delegated_family_id'] == 'progression_start_of_run'
    assert resolved.rows['state::tower.enemy_attack_level_skip_pct'].final_value == 35.0
    assert resolved.rows['raw::untouched'].final_value == 'fallback'
    assert resolved.diagnostics['resolve_stats_delegation']['compat_equivalent_declared_families'] == [
        'progression_start_of_run',
        'progression_runtime_no_perks',
    ]


def test_resolve_stats_preserves_explicit_fallback_for_mixed_preset_rows(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    progression_rows = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )
    mixed_rows = list(progression_rows)
    mixed_rows[0] = dc_replace(mixed_rows[0], preset_name='Tourney')

    def _boom(*args, **kwargs):
        raise AssertionError('mixed-preset rows must stay on the explicit fallback path')

    monkeypatch.setattr('qe.routing._resolve_manifest_approved_family', _boom)

    resolved = resolve_stats(mixed_rows)

    assert 'resolve_stats_delegation' not in resolved.diagnostics
    assert resolved.rows


@pytest.mark.expensive
def test_resolve_stats_delegated_tournament_surfaces_match_direct_query_kernel_resolution():
    state = build_state()
    scenario_config = ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150)
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_tournament_no_perks',
        preset_name='Tourney',
        scenario_config=scenario_config,
        perks_enabled=False,
    )

    resolved = resolve_stats(list(timing_rows))
    direct = StatQueryKernel().resolve_surfaces(
        build_family_baseline('timing_tournament_no_perks'),
        requested_surface_ids=(
            'mechanic_param::uw.black_hole.cooldown_seconds',
            'mechanic_param::uw.black_hole.duration_seconds',
            'mechanic_param::uw.golden_tower.cooldown_seconds',
            'mechanic_param::uw.golden_tower.duration_seconds',
            'support_surface::timing.gcomp_cooldown_reduction_seconds',
            'support_surface::timing.wave_duration_seconds_effective',
        ),
        trace_mode='contributors',
    )

    direct_rows = {row.surface_id: row for row in direct.resolved_surface_rows}
    assert resolved.diagnostics['resolve_stats_delegation']['delegated_family_id'] == 'timing_tournament_no_perks'
    for surface_id, direct_row in direct_rows.items():
        if surface_id not in resolved.rows:
            continue
        resolved_row = resolved.rows[surface_id]
        assert resolved_row.status == direct_row.status
        assert resolved_row.final_value == pytest.approx(direct_row.final_value, rel=1e-9, abs=1e-9)
        assert resolved_row.schema['delegated_family_id'] == 'timing_tournament_no_perks'


@pytest.mark.expensive
def test_resolve_stats_delegated_progression_surfaces_match_direct_query_kernel_resolution():
    state = build_state()
    progression_rows = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )

    resolved = resolve_stats(progression_rows)
    direct = StatQueryKernel().resolve_surfaces(
        build_family_baseline('progression_start_of_run'),
        requested_surface_ids=_PROGRESSSION_ASSERTED_SURFACE_IDS,
        trace_mode='contributors',
    )

    direct_rows = {row.surface_id: row for row in direct.resolved_surface_rows}
    assert resolved.diagnostics['resolve_stats_delegation']['delegated_family_id'] == 'progression_start_of_run'
    for surface_id, direct_row in direct_rows.items():
        assert surface_id in resolved.rows
        resolved_row = resolved.rows[surface_id]
        assert resolved_row.status == direct_row.status
        assert resolved_row.final_value == pytest.approx(direct_row.final_value, rel=1e-9, abs=1e-9)
        assert resolved_row.schema['delegated_family_id'] == 'progression_start_of_run'


def test_resolve_stats_delegates_farming_timing_family_when_unambiguous(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    scenario_config = ScenarioConfig(mode_id='farming', tier=14)
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=scenario_config,
        perks_enabled=True,
    )
    seen = {'delegated_family_id': None}

    def _fake_delegate(*, family_id, stat_inputs):
        seen['delegated_family_id'] = family_id

        class _Response:
            resolved_surface_rows = (
                type('Row', (), {
                    'surface_id': 'mechanic_param::uw.black_hole.cooldown_seconds',
                    'final_value': 10.0,
                    'value_type': 'seconds',
                    'status': 'resolved',
                })(),
            )
            contributor_rows = (
                type('Contributor', (), {
                    'surface_id': 'mechanic_param::uw.black_hole.cooldown_seconds',
                    'surface_class': 'surface',
                    'domain': 'ultimate_weapons',
                    'source_class': 'scenario_rules',
                    'composition_stage': 'scenario_runtime',
                    'contributor_id': 'timing.black_hole.effective_cooldown',
                    'value': 10.0,
                    'value_type': 'seconds',
                    'active': True,
                    'gate_reason': '',
                    'provenance_ref': 'test',
                })(),
            )

        return _Response()

    monkeypatch.setattr('qe.routing._resolve_manifest_approved_family', _fake_delegate)

    resolve_stats(list(timing_rows))

    assert seen['delegated_family_id'] == 'timing_farm_with_perks'


def test_resolve_stats_does_not_delegate_timing_rows_with_unrecognized_preset(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=ScenarioConfig(mode_id='farming', tier=14),
        perks_enabled=True,
    )
    unrecognized_rows = [dc_replace(row, preset_name='UnrecognizedPreset') for row in timing_rows]

    def _boom(*args, **kwargs):
        raise AssertionError('timing rows with an unrecognized preset must stay on the fallback path')

    monkeypatch.setattr('qe.routing._resolve_manifest_approved_family', _boom)

    resolved = resolve_stats(unrecognized_rows)

    assert 'resolve_stats_delegation' not in resolved.diagnostics
    assert resolved.rows


@pytest.mark.expensive
def test_resolve_stats_delegated_farming_surfaces_match_direct_query_kernel_resolution():
    state = build_state()
    scenario_config = ScenarioConfig(mode_id='farming', tier=14)
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=scenario_config,
        perks_enabled=True,
    )

    resolved = resolve_stats(list(timing_rows))
    direct = StatQueryKernel().resolve_surfaces(
        build_family_baseline('timing_farm_with_perks'),
        requested_surface_ids=(
            'mechanic_param::uw.black_hole.cooldown_seconds',
            'mechanic_param::uw.black_hole.duration_seconds',
            'mechanic_param::uw.golden_tower.cooldown_seconds',
            'mechanic_param::uw.golden_tower.duration_seconds',
            'support_surface::timing.gcomp_cooldown_reduction_seconds',
            'support_surface::timing.wave_duration_seconds_effective',
        ),
        trace_mode='contributors',
    )

    direct_rows = {row.surface_id: row for row in direct.resolved_surface_rows}
    assert resolved.diagnostics['resolve_stats_delegation']['delegated_family_id'] == 'timing_farm_with_perks'
    for surface_id, direct_row in direct_rows.items():
        if surface_id not in resolved.rows:
            continue
        resolved_row = resolved.rows[surface_id]
        assert resolved_row.status == direct_row.status
        assert resolved_row.final_value == pytest.approx(direct_row.final_value, rel=1e-9, abs=1e-9)
        assert resolved_row.schema['delegated_family_id'] == 'timing_farm_with_perks'
