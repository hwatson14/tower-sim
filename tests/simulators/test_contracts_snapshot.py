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
