from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live




def _safe_bump(workshop, state, track_name, delta):
    current = int(workshop.get(track_name, 0))
    entry = state.workshop[track_name]
    max_level = int(entry.max_level) if entry.max_level is not None else current
    candidate = current + int(delta)
    if candidate > max_level:
        candidate = max(0, current - 1)
    if candidate < 0:
        candidate = 0
    workshop[track_name] = candidate

def _build_patched_state_and_family(*, workshop_bumps: dict[str, int], perks_enabled: bool = False, state_mode: str = 'start_of_run'):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import SimulatorCheckpointState
    from simulators.progression import run_stats_progression_family_id
    from simulators.snapshot_resolver import SimulatorSnapshotResolver

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    resolver = SimulatorSnapshotResolver()
    workshop = {
        name: int((entry.preset_levels.get('Farming') or 0))
        for name, entry in state.workshop.items()
        if entry.max_level is not None
    }
    for track_name, bump in workshop_bumps.items():
        _safe_bump(workshop, state, track_name, bump)
    patched = resolver.patched_account_state(
        account_state=state,
        checkpoint_state=SimulatorCheckpointState(
            workshop_levels_current=workshop,
            perk_counts_override={},
            runtime_target_display_wave=0,
        ),
        preset_name='Farming',
    )
    family_id = run_stats_progression_family_id(state_mode=state_mode, perks_enabled=perks_enabled)
    return patched, family_id


def test_simulator_boss_wave_bundle__valid_and_subset_of_progression_core_stats():
    from qe.consumer_registry import load_consumer_bundle_definitions

    definitions = load_consumer_bundle_definitions()
    boss_bundle = definitions[('simulator_boss_wave', 'boss_wave_hot_surfaces')]
    core_bundle = definitions[('run_stats', 'progression_core_stats')]

    assert set(boss_bundle.surface_ids) <= set(core_bundle.surface_ids)
    assert 'state::tower.hp' in boss_bundle.surface_ids
    assert 'state::tower.regen' in boss_bundle.surface_ids
    assert 'state::wall.hp' in boss_bundle.surface_ids
    assert 'state::wall.regen' in boss_bundle.surface_ids
    assert 'state::tower.defense_pct' in boss_bundle.surface_ids


def test_checkpoint_consumer_bundle_delta__parity_and_fallback():
    from qe.routing import (
        query_response_to_statbook,
        resolve_checkpoint_consumer_bundle,
        resolve_checkpoint_consumer_bundle_delta,
    )

    baseline_state, family_id = _build_patched_state_and_family(workshop_bumps={})
    baseline_response = resolve_checkpoint_consumer_bundle(
        baseline_state,
        consumer_id='simulator_boss_wave',
        bundle_id='boss_wave_hot_surfaces',
        family_id=family_id,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )
    baseline_statbook = query_response_to_statbook(
        baseline_response,
        notes='baseline',
        diagnostics={'consumer_id': 'simulator_boss_wave', 'bundle_id': 'boss_wave_hot_surfaces'},
    )

    target_state, _ = _build_patched_state_and_family(
        workshop_bumps={'Health': 1, 'Health Regen': 1, 'Defense %': 1, 'Thorn Damage': 1}
    )
    full_target_response = resolve_checkpoint_consumer_bundle(
        target_state,
        consumer_id='simulator_boss_wave',
        bundle_id='boss_wave_hot_surfaces',
        family_id=family_id,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
    )
    full_target_statbook = query_response_to_statbook(full_target_response, notes='full target', diagnostics={})
    delta_statbook = resolve_checkpoint_consumer_bundle_delta(
        base_statbook=baseline_statbook,
        account_state=target_state,
        consumer_id='simulator_boss_wave',
        bundle_id='boss_wave_hot_surfaces',
        family_id=family_id,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
        trigger_keys=('Health', 'Health Regen', 'Defense %', 'Thorn Damage'),
    )

    assert delta_statbook.diagnostics['delta_fallback_used'] is False
    for surface_id in (
        'state::wall.hp',
        'state::wall.regen',
        'state::tower.defense_pct',
        'state::tower.thorns_damage_pct',
    ):
        assert delta_statbook.rows[surface_id].final_value == full_target_statbook.rows[surface_id].final_value
        assert delta_statbook.rows[surface_id].contributors

    fallback_state, _ = _build_patched_state_and_family(workshop_bumps={'Wall Health': 1})
    fallback_statbook = resolve_checkpoint_consumer_bundle_delta(
        base_statbook=baseline_statbook,
        account_state=fallback_state,
        consumer_id='simulator_boss_wave',
        bundle_id='boss_wave_hot_surfaces',
        family_id=family_id,
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=False,
        trigger_keys=('Wall Health',),
    )
    assert fallback_statbook.diagnostics['delta_fallback_used'] is True
    assert 'Unsupported mutation keys' in fallback_statbook.diagnostics['delta_fallback_reason']
