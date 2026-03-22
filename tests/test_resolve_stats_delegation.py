from __future__ import annotations

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
from helpers import build_family_baseline, build_state


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

    monkeypatch.setattr('engine.stat_engine._fallback_resolve_stats', _fake_fallback)
    monkeypatch.setattr('engine.stat_engine._resolve_manifest_approved_family', _fake_delegate)

    resolved = resolve_stats(list(timing_rows))

    assert seen['fallback_calls'] == 1
    assert seen['delegated_rows'] is not None
    assert resolved.rows['mechanic_param::uw.black_hole.cooldown_seconds'].final_value == 12.5
    assert resolved.rows['raw::untouched'].final_value == 'fallback'
    assert resolved.diagnostics['resolve_stats_delegation']['delegated_family_id'] == 'timing_tournament_no_perks'
    assert resolved.diagnostics['resolve_stats_delegation']['bounded_only'] is True


def test_resolve_stats_preserves_explicit_fallback_for_undelegated_progression_rows(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    progression_rows = compile_stat_inputs(
        state,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )

    def _boom(*args, **kwargs):
        raise AssertionError('undelegated progression rows must stay on the explicit fallback path')

    monkeypatch.setattr('engine.stat_engine._resolve_manifest_approved_family', _boom)

    resolved = resolve_stats(progression_rows)

    assert 'resolve_stats_delegation' not in resolved.diagnostics
    assert resolved.rows


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


def test_resolve_stats_does_not_imply_full_timing_family_coverage_when_family_is_ambiguous(monkeypatch: pytest.MonkeyPatch):
    state = build_state()
    _, timing_rows = compile_timing_family_rows(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=ScenarioConfig(mode_id='farming', tier=14),
        perks_enabled=True,
    )

    def _boom(*args, **kwargs):
        raise AssertionError('ambiguous timing families must not be delegated through resolve_stats yet')

    monkeypatch.setattr('engine.stat_engine._resolve_manifest_approved_family', _boom)

    resolved = resolve_stats(list(timing_rows))

    assert 'resolve_stats_delegation' not in resolved.diagnostics
    assert 'support_surface::timing.wave_duration_seconds_effective' in resolved.rows
