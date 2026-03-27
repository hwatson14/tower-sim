from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import simulators.progression as progression_recalc_bridge
from engine.incremental_recalc_runtime import IncrementalPlan
from engine.progression_recalc_bridge import ProgressionRecalcBridge, ProgressionRecalcRequest
from helpers import build_state

ROOT = Path(__file__).resolve().parents[1]


def test_recalc_bridge_preserves_start_of_run_and_applies_specific_override():
    state = build_state()
    original = state.workshop['Wall Health'].preset_levels['Farming']
    bridge = ProgressionRecalcBridge()
    result = bridge.recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={
                'Wall Health': original + 1,
            },
        )
    )
    assert state.workshop['Wall Health'].preset_levels['Farming'] == original
    assert result.patched_account_state.workshop['Wall Health'].preset_levels['Farming'] == original + 1
    wall_hp = result.statbook.rows['state::wall.hp']
    assert wall_hp.status == 'resolved'


def test_recalc_bridge_rejects_invalid_workshop_level():
    state = build_state()
    bridge = ProgressionRecalcBridge()
    try:
        bridge.recompute(
            ProgressionRecalcRequest(
                account_state=state,
                preset_name='Farming',
                workshop_levels_current={'Damage': 6001},
            )
        )
    except ValueError as exc:
        assert 'Invalid workshop level' in str(exc)
    else:
        raise AssertionError('Expected invalid workshop level to raise ValueError')

def test_recalc_bridge_uses_structural_overlay_without_mutating_original_nested_state():
    state = build_state()
    original_workshop_entry = state.workshop['Wall Health']
    original_preset_levels = state.workshop['Wall Health'].preset_levels
    bridge = ProgressionRecalcBridge()
    result = bridge.recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Wall Health': int(original_preset_levels['Farming']) + 1},
            perk_counts_override={'perk_wave_requirement': 2},
        )
    )
    assert result.patched_account_state is not state
    assert result.patched_account_state.workshop is not state.workshop
    assert result.patched_account_state.workshop['Wall Health'] is not original_workshop_entry
    assert result.patched_account_state.workshop['Wall Health'].preset_levels is not original_preset_levels
    assert state.active_perk_preset != 'ProgressionTimeline_CurrentWave'
    assert 'ProgressionTimeline_CurrentWave' not in state.perk_presets
    assert result.patched_account_state.active_perk_preset == 'ProgressionTimeline_CurrentWave'
    assert result.patched_account_state.perk_presets['ProgressionTimeline_CurrentWave'][0].perk_id == 'perk_wave_requirement'


def test_recalc_bridge_uses_bounded_native_subset_for_supported_progression_probe(monkeypatch):
    state = build_state()

    def _boom(_):
        raise AssertionError('resolve_stats should not be used for supported incremental_targeted_probe_guarded progression requests')

    monkeypatch.setattr(progression_recalc_bridge, 'resolve_stats', _boom, raising=False)
    result = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': state.workshop['Enemy Attack Level Skip'].preset_levels['Farming'] + 1},
            recompute_mode='incremental_targeted_probe_guarded',
            runtime_target_display_wave=120,
        )
    )

    assert result.incremental_diagnostics['status'] == 'published_targeted_probe_subset'
    assert result.incremental_diagnostics['ownership_boundary'] == 'bounded_query_owned_publishable_subset'
    assert result.incremental_diagnostics['runtime_publication']['status'] == 'published_from_bounded_progression_bundle'
    assert result.incremental_diagnostics['runtime_publication']['outputs']['attack_wave'] is not None
    assert 'state::tower.enemy_attack_level_skip_pct' in result.statbook.rows


def test_recalc_bridge_full_safe_uses_bounded_family_reference(monkeypatch):
    state = build_state()

    def _boom(_):
        raise AssertionError('resolve_stats should not be used for full_safe progression requests once bounded family reference is available')

    monkeypatch.setattr(progression_recalc_bridge, 'resolve_stats', _boom, raising=False)
    result = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Wall Health': state.workshop['Wall Health'].preset_levels['Farming']},
            recompute_mode='full_safe',
        )
    )

    assert result.incremental_diagnostics['mode'] == 'full_safe'
    assert result.incremental_diagnostics['ownership_boundary'] == 'bounded_query_owned_declared_family_reference'


def test_recalc_bridge_full_safe_runtime_publication_uses_bounded_progression_bundle(monkeypatch):
    state = build_state()
    seen_calls = []
    original = progression_recalc_bridge.resolve_progression_consumer_bundle

    def _wrapped(*args, **kwargs):
        seen_calls.append((kwargs['consumer_id'], kwargs['bundle_id'], kwargs['family_id']))
        return original(*args, **kwargs)

    monkeypatch.setattr(progression_recalc_bridge, 'resolve_progression_consumer_bundle', _wrapped)

    result = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Enemy Attack Level Skip': state.workshop['Enemy Attack Level Skip'].preset_levels['Farming'] + 1},
            recompute_mode='full_safe',
            runtime_target_display_wave=120,
            perks_enabled=False,
        )
    )

    assert seen_calls == [('progression_runtime', 'progression_wave_skips', 'progression_runtime_no_perks')]
    assert result.incremental_diagnostics['runtime_publication']['status'] == 'published_from_bounded_progression_bundle'
    assert result.incremental_diagnostics['runtime_publication']['outputs']['attack_wave'] is not None


def test_recalc_bridge_fallback_plans_use_bounded_family_reference(monkeypatch):
    state = build_state()

    def _fallback_plan(self, workshop_levels_current):
        return IncrementalPlan(
            consumer_id=None,
            bundle_id=None,
            family_id='progression_runtime_no_perks',
            baseline_required=True,
            overlays_to_apply=[],
            requested_surfaces=[],
            upstream_dependency_closure=[],
            publishable_closure=[],
            runtime_consumer_ids=[],
            mutated_source_nodes=[],
            dirty_nodes=[],
            fallback_required=True,
            fallback_reason='forced_fallback_for_test',
        )

    monkeypatch.setattr(
        progression_recalc_bridge.IncrementalRecalcRuntime,
        'plan_from_workshop_overrides',
        _fallback_plan,
    )

    result = ProgressionRecalcBridge().recompute(
        ProgressionRecalcRequest(
            account_state=state,
            preset_name='Farming',
            workshop_levels_current={'Wall Health': state.workshop['Wall Health'].preset_levels['Farming']},
            recompute_mode='incremental_targeted_probe_guarded',
        )
    )

    assert result.incremental_diagnostics['status'] == 'fallback_bounded_family_reference'
    assert result.incremental_diagnostics['ownership_boundary'] == 'bounded_query_owned_declared_family_reference'
