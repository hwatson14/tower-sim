"""
Perk gating: tournaments disable perks (fail-closed).

If run_context.perks_enabled is False, any attempt to apply perks must raise.
"""

from __future__ import annotations
from typing import Any, Dict


class PerksDisabledError(RuntimeError):
    pass


def assert_perks_enabled(run_context: Dict[str, Any]) -> None:
    enabled = run_context.get("perks_enabled")
    # fail-closed: missing field is an error
    if enabled is None:
        raise PerksDisabledError("run_context.perks_enabled missing (fail-closed)")
    if enabled is False:
        raise PerksDisabledError("Perks are disabled in tournament context")
