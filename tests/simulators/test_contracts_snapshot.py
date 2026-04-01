from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_simulator_contracts_construct__expected_defaults_present():
    from simulators.contracts import (
        DirtyLedger,
        NormalizedCheckpointState,
        PerkState,
        ProjectedRunState,
        RunResult,
        WaveCheckpoint,
    )

    checkpoint = WaveCheckpoint(display_wave=10)
    perk_state = PerkState(wave=10, counts={'perk.alpha': 2}, dirty=True)
    projected = ProjectedRunState(
        checkpoint=checkpoint,
        workshop_levels_current={'Health': 6000},
        perk_state=perk_state,
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True),
    )
    normalized = NormalizedCheckpointState(
        checkpoint=checkpoint,
        account_state=object(),
        preset_name='Farming',
        projected_run_state=projected,
    )
    result = RunResult(max_wave=100, row_count=10, terminal_checkpoint=checkpoint)

    assert normalized.projected_run_state.perk_state.counts['perk.alpha'] == 2
    assert result.max_wave == 100


def test_snapshot_resolver__uses_contract_owned_bundle_and_preserves_provenance():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from qe.consumer_registry import load_consumer_bundle_definitions
    from simulators.contracts import DirtyLedger, NormalizedCheckpointState, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.snapshot_resolver import resolve_wave_row_snapshot

    bundle_defs = load_consumer_bundle_definitions()
    boss_bundle = bundle_defs[('simulator_boss_wave', 'boss_wave_hot_surfaces')]
    core_bundle = bundle_defs[('run_stats', 'progression_core_stats')]
    assert set(boss_bundle.surface_ids) <= set(core_bundle.surface_ids)
    assert 'state::tower.regen' in boss_bundle.surface_ids
    assert 'state::wall.regen' in boss_bundle.surface_ids

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=0),
        workshop_levels_current={
            name: int((entry.preset_levels.get('Farming') or 0))
            for name, entry in state.workshop.items()
            if entry.max_level is not None
        },
        perk_state=PerkState(wave=0, counts={}, dirty=False),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
    )
    normalized = NormalizedCheckpointState(
        checkpoint=projected.checkpoint,
        account_state=state,
        preset_name='Farming',
        projected_run_state=projected,
        state_mode='start_of_run',
        perks_enabled=False,
        mode_id='farming',
    )

    snapshot = resolve_wave_row_snapshot(normalized)
    rows = snapshot.resolved_statbook.rows
    diagnostics = snapshot.resolved_statbook.diagnostics

    assert diagnostics['qe_consumer_id'] == 'simulator_boss_wave'
    assert diagnostics['qe_bundle_id'] == 'boss_wave_hot_surfaces'
    assert diagnostics['family_id'] == 'progression_start_of_run'
    assert 'state::tower.regen' in rows
    assert 'state::wall.regen' in rows
    assert rows['state::tower.regen'].contributors
    assert rows['state::wall.regen'].contributors


def test_snapshot_resolver_source__does_not_keep_local_checkpoint_surface_authority():
    import simulators.snapshot_resolver as snapshot_resolver

    source = inspect.getsource(snapshot_resolver)
    assert '_CHECKPOINT_SURFACE_IDS' not in source
    assert 'boss_wave_hot_surfaces' in source


def test_snapshot_resolver_generic_checkpoint_seam__honors_requested_surface_ids():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import SimulatorCheckpointState
    from simulators.snapshot_resolver import SimulatorSnapshotResolver

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    resolution = SimulatorSnapshotResolver().resolve_checkpoint(
        account_state=state,
        checkpoint_state=SimulatorCheckpointState(workshop_levels_current={}),
        preset_name='Farming',
        requested_surface_ids=('state::economy.cash_per_wave',),
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )

    assert resolution.diagnostics['resolver_kind'] == 'simulator_checkpoint_qe_light'
    assert tuple(resolution.resolved_values) == ('state::economy.cash_per_wave',)
    assert 'state::tower.hp' not in resolution.resolved_values
