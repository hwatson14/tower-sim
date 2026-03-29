from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SimulatorCheckpointState:
    workshop_levels_current: dict[str, int] = field(default_factory=dict)
    perk_counts_override: dict[str, int] | None = None
    runtime_target_display_wave: int | None = None


@dataclass(frozen=True)
class SimulatorCheckpointResolution:
    requested_surface_ids: tuple[str, ...]
    resolved_values: dict[str, Any]
    diagnostics: Mapping[str, Any]
