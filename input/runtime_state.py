"""
input/runtime_state.py — Runtime state types and assembly. AUTHORITY.

Owns: IdsRaw, AccountState, ScenarioRuntimeInputs (canonical re-export point),
and build_runtime_state() which is the SANCTIONED entry point for assembling
an AccountState from parsed inputs.

Transitional notes:
  - IdsRaw: defined in models/ids_raw.py until T3 moves it to qe/models.py.
  - AccountState snapshots: defined in models/account_state.py until T3.
  - ScenarioRuntimeInputs: defined in engine/scenario_runtime_inputs.py until T4.
  - compile_account_state(): transitional alias for build_runtime_state() so that
    test files importing from compilers.account_state_compiler (via that module's
    own shim path) still work. Remove alias in T8.
  - Assembly implementation: compilers/account_state_compiler.py is an internal
    implementation detail. Do not import from it in new active code.

Active code MUST import from here (input.runtime_state), not from models.*,
engine.scenario_runtime_inputs, or compilers.account_state_compiler.
"""
from __future__ import annotations

from typing import Optional

# ── Canonical type re-exports ─────────────────────────────────────────────────
# Transitional: these types will consolidate into qe/models.py in T3.

from input.ids_raw import IdsRaw  # noqa: F401
from qe.account_state import (  # noqa: F401
    AccountState,
    BotUpgradeSnapshot,
    CardSnapshot,
    GuardianTrackSnapshot,
    ModulePresetSelection,
    ModuleSnapshot,
    ModuleSubstat,
    ModuleSystemState,
    PerkSelection,
    PRESET_NAMES,
    SLOT_TYPES,
    TableSnapshot,
    UltimateWeaponSnapshot,
    UwPlusTrackSnapshot,
    UwTrackSnapshot,
    WorkshopEnhancementSnapshot,
    WorkshopEntrySnapshot,
)
from input.scenario_runtime_inputs import ScenarioRuntimeInputs  # noqa: F401

__all__ = [
    # types
    "IdsRaw",
    "AccountState",
    "ScenarioRuntimeInputs",
    "BotUpgradeSnapshot",
    "CardSnapshot",
    "GuardianTrackSnapshot",
    "ModulePresetSelection",
    "ModuleSnapshot",
    "ModuleSubstat",
    "ModuleSystemState",
    "PerkSelection",
    "PRESET_NAMES",
    "SLOT_TYPES",
    "TableSnapshot",
    "UltimateWeaponSnapshot",
    "UwPlusTrackSnapshot",
    "UwTrackSnapshot",
    "WorkshopEnhancementSnapshot",
    "WorkshopEntrySnapshot",
    # entry points
    "build_runtime_state",
    "compile_account_state",  # transitional alias; remove in T8
]


def build_runtime_state(
    ids_raw: IdsRaw,
    *,
    default_preset: str = "Farming",
    loadout_config: Optional[dict] = None,
    perk_config: Optional[dict] = None,
) -> AccountState:
    """
    SANCTIONED ENTRY POINT for runtime-state assembly.

    Assembles an AccountState from a parsed IdsRaw plus optional config overrides.
    Implementation delegates to compilers.account_state_compiler (internal detail).
    """
    from input.account_state_compiler import compile_account_state as _compile
    return _compile(
        ids_raw,
        default_preset=default_preset,
        loadout_config=loadout_config,
        perk_config=perk_config,
    )


# Transitional alias so active callers can migrate incrementally.
# Remove in T8 once all callers use build_runtime_state directly.
compile_account_state = build_runtime_state
