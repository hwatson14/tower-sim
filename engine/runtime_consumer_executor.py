from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from engine.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState
from models.statbook import StatBook


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
        attack_skip_pct = self._row_float(statbook, 'canonical_stat::enemy_attack_level_skip_pct')
        health_skip_pct = self._row_float(statbook, 'canonical_stat::enemy_health_level_skip_pct')
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
        row = statbook.rows.get(stat_name)
        if row is None or row.final_value is None:
            return None
        return float(row.final_value)
