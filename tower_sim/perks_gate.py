"""
Perk gating: tournaments disable perks (fail-closed).

If run_context.perks_enabled is False, any attempt to apply perks must raise.
"""

from __future__ import annotations

from tower_sim.run_context import PerksDisabledError, RunContext, assert_perks_enabled as _assert_perks_enabled


def assert_perks_enabled(run_context: RunContext) -> None:
    _assert_perks_enabled(run_context)
