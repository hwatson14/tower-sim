"""Simulator smoke tests for progression/timing public APIs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_progression_public_api_is_importable__query_callables_exposed():
    from simulators.progression import resolve_progression_consumer_bundle, resolve_progression_family_query

    assert callable(resolve_progression_family_query)
    assert callable(resolve_progression_consumer_bundle)


def test_timing_public_api_is_importable__query_callables_exposed():
    from simulators.timing import compute_timing_surfaces, resolve_timing_consumer_bundle, resolve_timing_family_query

    assert callable(compute_timing_surfaces)
    assert callable(resolve_timing_family_query)
    assert callable(resolve_timing_consumer_bundle)


def test_simulator_modules_reference_qe_imports__expected_qe_strings_present():
    import simulators.progression as progression_module
    import simulators.timing as timing_module

    for mod, name in [(progression_module, "simulators.progression"), (timing_module, "simulators.timing")]:
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "qe." in src or "from qe" in src, f"{name} must import from qe.*"


def test_qe_checkpoint_surface_resolution__resolves_only_requested_progression_surfaces():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from qe.routing import resolve_checkpoint_surfaces

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    response = resolve_checkpoint_surfaces(
        state,
        requested_surface_ids=(
            'state::tower.hp',
            'state::wall.hp',
        ),
        preset_name='Farming',
        family_id='progression_runtime_with_perks',
        perks_enabled=True,
    )

    surface_ids = tuple(row.surface_id for row in response.resolved_surface_rows)
    assert surface_ids == ('state::tower.hp', 'state::wall.hp')


def test_simulator_snapshot_resolver__avoids_progression_recalc_bridge(monkeypatch):
    import simulators.progression as progression_module
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import DirtyLedger, NormalizedCheckpointState, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.snapshot_resolver import resolve_wave_row_snapshot

    def _no_bridge(*args, **kwargs):
        raise AssertionError('snapshot resolver must not call ProgressionRecalcBridge.recompute')

    monkeypatch.setattr(progression_module.ProgressionRecalcBridge, 'recompute', _no_bridge)

    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    checkpoint = WaveCheckpoint(display_wave=1)
    projected = ProjectedRunState(
        checkpoint=checkpoint,
        workshop_levels_current={'Health': 1},
        perk_state=PerkState(wave=1, counts={}),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True),
    )
    snapshot = resolve_wave_row_snapshot(
        NormalizedCheckpointState(
            checkpoint=checkpoint,
            account_state=state,
            preset_name='Farming',
            projected_run_state=projected,
        )
    )
    assert snapshot.metrics is not None
    assert snapshot.metrics.qe_resolution_count == 1
