from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from simulators.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState
from qe.contracts import to_legacy_surface_id
from models.statbook import StatBook


_WAVE_SKIP_SURFACE_IDS = (
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
)


@dataclass(frozen=True)
class RuntimeConsumerOutputs:
    target_display_wave: int
    attack_wave: int | None
    health_wave: int | None
    attack_skip_pct: float | None
    health_skip_pct: float | None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RuntimeConsumerExecutor:
    """Executes explicitly-registered runtime consumers from canonical stat rows.

    Current closed runtime publication scope is limited to the two skip-driven wave
    progression consumers because their dependency chain is explicit in-package.
    """

    def __init__(self, policy: WaveProgressionPolicy | None = None) -> None:
        self._policy = policy or WaveProgressionPolicy()

    def execute_skip_wave_outputs(self, *, statbook: StatBook, target_display_wave: int) -> RuntimeConsumerOutputs:
        self._assert_required_wave_skip_rows_present(statbook)
        attack_skip_pct = self._row_float(statbook, 'state::tower.enemy_attack_level_skip_pct')
        health_skip_pct = self._row_float(statbook, 'state::tower.enemy_health_level_skip_pct')
        state = self._policy.advance_to_wave(
            state=WaveProgressionState(),
            target_display_wave=int(target_display_wave),
            attack_skip_pct=0.0 if attack_skip_pct is None else attack_skip_pct,
            health_skip_pct=0.0 if health_skip_pct is None else health_skip_pct,
        )
        return RuntimeConsumerOutputs(
            target_display_wave=int(target_display_wave),
            attack_wave=state.attack_wave,
            health_wave=state.health_wave,
            attack_skip_pct=attack_skip_pct,
            health_skip_pct=health_skip_pct,
        )

    @staticmethod
    def _row_float(statbook: StatBook, stat_name: str) -> float | None:
        row = RuntimeConsumerExecutor._lookup_surface_row(statbook, stat_name)
        if row is None or row.final_value is None:
            return None
        return float(row.final_value)

    @staticmethod
    def _lookup_surface_row(statbook: StatBook, surface_id: str):
        row = statbook.rows.get(surface_id)
        if row is not None:
            return row
        legacy_surface_id = to_legacy_surface_id(surface_id)
        if legacy_surface_id != surface_id:
            row = statbook.rows.get(legacy_surface_id)
            if row is not None:
                return row
        return None

    @staticmethod
    def _assert_required_wave_skip_rows_present(statbook: StatBook) -> None:
        for surface_id in _WAVE_SKIP_SURFACE_IDS:
            row = RuntimeConsumerExecutor._lookup_surface_row(statbook, surface_id)
            if row is None:
                raise ValueError(
                    f'Runtime skip-wave execution requires wave skip surface {surface_id!r}; row is missing.'
                )
