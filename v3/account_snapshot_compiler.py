"""v3 Phase-1 account snapshot compiler surface.

This module intentionally re-exports the validated compiler from the existing
TowerSim core so v3 can consume the same deterministic, fail-closed behavior
without forking compiler logic during bootstrap.
"""

from tower_sim.loaders.account_snapshot_compiler import (  # noqa: F401
    compile_account_snapshot,
    resolve_loadout,
    snapshot_as_dict,
)
