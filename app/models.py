"""
app/models.py -- Pipeline data models.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace


@dataclass(frozen=True)
class PipelineRunRequest:
    ids: Path
    out: Path
    preset: str = 'Farming'
    state_mode: str = 'max_progression'
    manual_inputs: Path | None = None
    runtime_state_overlay: str | None = None
    perk_mode: str = 'max_progression_policy'
    include_slow_audits: bool = False
    perk_state: str = 'auto'
    perk_policy_preset: str | None = None
    tier: int | None = None
    dissonance_run_category: str | None = None
    include_boss_wave_milestone_matrix: bool = False


def _run_stats_args_from_payload(payload: dict[str, object]):
    return SimpleNamespace(
        ids=Path(str(payload['ids'])),
        out=Path(str(payload['out'])),
        manual_inputs=Path(str(payload['manual_inputs'])) if payload.get('manual_inputs') else None,
        runtime_state_overlay=(
            str(payload['runtime_state_overlay'])
            if payload.get('runtime_state_overlay') not in {None, '', 'None', 'none'}
            else None
        ),
        perk_mode=str(payload.get('perk_mode', 'max_progression_policy')),
        perk_state=str(payload.get('perk_state', 'auto')),
        perk_policy_preset=str(payload['perk_policy_preset']) if payload.get('perk_policy_preset') else None,
        tier=int(payload['tier']) if payload.get('tier') is not None else None,
        dissonance_run_category=(
            str(payload['dissonance_run_category'])
            if payload.get('dissonance_run_category') is not None
            else None
        ),
        include_boss_wave_milestone_matrix=bool(payload.get('include_boss_wave_milestone_matrix', False)),
    )


def _normalize_perk_state(perk_state: str) -> str:
    value = str(perk_state or 'auto').strip().lower()
    if value not in {'auto', 'on', 'off'}:
        raise ValueError(f'Unsupported perk state: {perk_state}')
    return value


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
    runtime_state_overlay: str | None = None
    perk_mode: str = 'max_progression_policy'
    perk_state: str = 'auto'
    perk_policy_preset: str | None = None
    requested_surface_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FastCheckpointResult:
    request: FastCheckpointRequest
    statbook: dict[str, object]
    diagnostics: dict[str, object]
