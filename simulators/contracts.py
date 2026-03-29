from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WaveCheckpoint:
    display_wave: int


@dataclass(frozen=True)
class PerkState:
    wave: int
    counts: Dict[str, int] = field(default_factory=dict)
    dirty: bool = False


@dataclass(frozen=True)
class DirtyLedger:
    progression_dirty: bool = False
    qe_dirty: bool = False
    timing_dirty: bool = False
    geometry_dirty: bool = False


@dataclass(frozen=True)
class ProjectedRunState:
    checkpoint: WaveCheckpoint
    workshop_levels_current: Dict[str, int]
    perk_state: PerkState
    wave_progression_state: Dict[str, Any] = field(default_factory=dict)
    free_upgrade_state: Dict[str, Any] = field(default_factory=dict)
    counters: Dict[str, Any] = field(default_factory=dict)
    dirty_ledger: DirtyLedger = field(default_factory=DirtyLedger)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedCheckpointState:
    checkpoint: WaveCheckpoint
    account_state: Any
    preset_name: str
    projected_run_state: ProjectedRunState
    state_mode: str = "start_of_run"
    perks_enabled: bool = True
    card_preset_name: Optional[str] = None
    module_preset_name: Optional[str] = None
    perk_preset_name: Optional[str] = None
    mode_id: str = "farming"
    tier: int = 14
    league: Optional[str] = None
    tournament_wave: int = 0
    scenario_runtime_inputs: Any = None


@dataclass(frozen=True)
class PerformanceMetrics:
    row_resolution_ms: float
    qe_resolution_count: int = 0
    timing_recompute_count: int = 0
    geometry_recompute_count: int = 0


@dataclass(frozen=True)
class WaveRowSnapshot:
    checkpoint: WaveCheckpoint
    projected_run_state: ProjectedRunState
    resolved_statbook: Any
    scenario_context: Any
    timing_context: Any
    geometry_context: Dict[str, Any] = field(default_factory=dict)
    combat_runtime: Any = None
    metrics: Optional[PerformanceMetrics] = None


@dataclass(frozen=True)
class RunResult:
    max_wave: int
    row_count: int
    terminal_checkpoint: Optional[WaveCheckpoint] = None
    terminal_snapshot: Optional[WaveRowSnapshot] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)
