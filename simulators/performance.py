from __future__ import annotations

from time import perf_counter

from input.state_types import AccountState
from simulators.contracts import SimulatorCheckpointState
from simulators.snapshot_resolver import SimulatorSnapshotResolver


def measure_checkpoint_resolution(
    *,
    account_state: AccountState,
    checkpoint_state: SimulatorCheckpointState,
    preset_name: str,
    requested_surface_ids: tuple[str, ...] | list[str],
    family_id: str | None = None,
) -> dict[str, float]:
    resolver = SimulatorSnapshotResolver()
    start = perf_counter()
    result = resolver.resolve_checkpoint(
        account_state=account_state,
        checkpoint_state=checkpoint_state,
        preset_name=preset_name,
        requested_surface_ids=requested_surface_ids,
        family_id=family_id,
    )
    return {
        'total_wall_ms': round((perf_counter() - start) * 1000.0, 3),
        'resolved_surface_count': float(len(result.resolved_values)),
        **{
            f'phase_{name}_ms': float(value)
            for name, value in result.diagnostics['phase_timing_ms'].items()
        },
    }
