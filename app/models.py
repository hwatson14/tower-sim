"""
app/models.py -- Pipeline data models.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PipelineRunRequest:
    ids: Path
    out: Path
    preset: str = 'Farming'
    state_mode: str = 'max_progression'
    manual_inputs: Path | None = None
    perk_mode: str = 'max_progression_policy'
    include_slow_audits: bool = False
    perk_state: str = 'auto'


@dataclass(frozen=True)
class PipelineStageRecord:
    stage_id: str
    title: str
    owner_module: str
    entry_function: str
    status: str
    elapsed_ms: float
    outputs_summary: dict[str, object] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PipelineTrace:
    request: dict[str, object]
    execution_path: dict[str, object]
    stages: list[PipelineStageRecord]
    artifacts_written: list[str]

    def to_dict(self) -> dict[str, object]:
        payload = dataclasses.asdict(self)
        payload['stages'] = [stage.to_dict() for stage in self.stages]
        return payload


@dataclass(frozen=True)
class PipelineRunResult:
    exit_code: int
    request: PipelineRunRequest
    out_dir: Path
    diagnostics: dict[str, object]
    generated_files: tuple[Path, ...]
    pipeline_trace: PipelineTrace


@dataclass(frozen=True)
class VerificationSnapshotSpec:
    preset: str
    state_mode: str
    perk_state: str = 'auto'
    out_subdir: str | None = None


@dataclass(frozen=True)
class FastCheckpointRequest:
    ids: Path
    preset: str = 'Farming'
    state_mode: str = 'start_of_run'
    manual_inputs: Path | None = None
    perk_mode: str = 'max_progression_policy'
    perk_state: str = 'auto'
    requested_surface_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FastCheckpointResult:
    request: FastCheckpointRequest
    statbook: dict[str, object]
    diagnostics: dict[str, object]
