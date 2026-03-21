from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from pathlib import Path

from compilers.account_state_compiler import compile_account_state
import engine.progression_recalc_bridge as progression_recalc_bridge
from engine.progression_recalc_bridge import ProgressionRecalcBridge, ProgressionRecalcRequest
from parsers.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def test_recalc_bridge_preserves_start_of_run_and_applies_specific_override():
    state = _build_state()
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
    wall_hp = result.statbook.rows['canonical_stat::wall_hp']
    assert wall_hp.status == 'resolved'


def test_recalc_bridge_rejects_invalid_workshop_level():
    state = _build_state()
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
    state = _build_state()
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
    state = _build_state()

    def _boom(_):
        raise AssertionError('resolve_stats should not be used for supported incremental_targeted_probe_guarded progression requests')

    monkeypatch.setattr(progression_recalc_bridge, 'resolve_stats', _boom)
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
    assert result.incremental_diagnostics['runtime_publication']['outputs']['attack_wave'] is not None
    assert 'canonical_stat::enemy_attack_level_skip_pct' in result.statbook.rows
