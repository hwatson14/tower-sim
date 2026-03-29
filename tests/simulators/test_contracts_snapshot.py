from __future__ import annotations

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
    perk_state = PerkState(wave=10, counts={"perk.alpha": 2}, dirty=True)
    projected = ProjectedRunState(
        checkpoint=checkpoint,
        workshop_levels_current={"Health": 6000},
        perk_state=perk_state,
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True),
    )
    normalized = NormalizedCheckpointState(
        checkpoint=checkpoint,
        account_state=object(),
        preset_name="Farming",
        projected_run_state=projected,
    )
    result = RunResult(max_wave=100, row_count=10, terminal_checkpoint=checkpoint)

    assert normalized.projected_run_state.perk_state.counts["perk.alpha"] == 2
    assert result.max_wave == 100


def test_perk_state_cursor_advances_incrementally__without_recounting_prefix():
    from simulators.perk_timeline_state import PerkTimelineEvent
    from simulators.perks import advance_perk_state

    events = [
        PerkTimelineEvent(wave=10, perk_id="a", perk_name="A"),
        PerkTimelineEvent(wave=20, perk_id="b", perk_name="B"),
        PerkTimelineEvent(wave=20, perk_id="a", perk_name="A"),
    ]

    state10, cursor10 = advance_perk_state(events, wave=10)
    state20, cursor20 = advance_perk_state(events, wave=20, cursor=cursor10)

    assert state10.counts == {"a": 1}
    assert state20.counts == {"a": 2, "b": 1}
    assert cursor20.next_index == 3


@pytest.mark.expensive
def test_row_resolution_benchmark_harness_returns_shape():
    from simulators.performance import bench_row_resolution

    result = bench_row_resolution(wave=1)
    assert result.name == "row_resolution"
    assert result.rows == 1
    assert result.qe_resolution_count == 1
    assert result.elapsed_ms >= 0.0
