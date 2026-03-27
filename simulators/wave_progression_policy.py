from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class WaveProgressionPolicyConfig:
    warmup_waves: int = 0


@dataclass(frozen=True)
class WaveProgressionState:
    display_wave: int = 0
    attack_wave: int = 0
    health_wave: int = 0
    attack_skip_counter: float = 0.0
    health_skip_counter: float = 0.0


class WaveProgressionPolicy:
    """Deterministic current-wave progression policy for attack and health wave.

    Package rule:
    - Enemy level skip is deterministic/non-random.
    - Progression engine tracks attack and health wave separately.
    - The current effective skip pct applies immediately at each displayed wave.
    - Deterministic accumulation uses an integer carry counter; every full 1.0 of
      accumulated skip chance suppresses one enemy level advance.

    Compatibility note:
    - ``warmup_waves`` remains in the config only to avoid breaking callers on the
      refactored runtime branch. It is intentionally ignored by the accepted
      progression-truth model implemented here.
    """

    def __init__(self, config: WaveProgressionPolicyConfig | None = None) -> None:
        self._config = config or WaveProgressionPolicyConfig()

    def advance_to_wave(
        self,
        *,
        state: WaveProgressionState,
        target_display_wave: int,
        attack_skip_pct: float,
        health_skip_pct: float,
    ) -> WaveProgressionState:
        if target_display_wave < state.display_wave:
            raise ValueError(
                f'target_display_wave {target_display_wave} cannot move backwards from {state.display_wave}'
            )
        attack_wave = state.attack_wave
        health_wave = state.health_wave
        attack_counter = state.attack_skip_counter
        health_counter = state.health_skip_counter
        attack_skip = self._effective_skip_pct(attack_skip_pct)
        health_skip = self._effective_skip_pct(health_skip_pct)
        for _display_wave in range(state.display_wave + 1, target_display_wave + 1):
            attack_counter += attack_skip
            attack_suppressed = floor(attack_counter)
            attack_counter -= attack_suppressed
            attack_wave += max(0, 1 - attack_suppressed)

            health_counter += health_skip
            health_suppressed = floor(health_counter)
            health_counter -= health_suppressed
            health_wave += max(0, 1 - health_suppressed)
        return WaveProgressionState(
            display_wave=target_display_wave,
            attack_wave=attack_wave,
            health_wave=health_wave,
            attack_skip_counter=attack_counter,
            health_skip_counter=health_counter,
        )

    @staticmethod
    def _effective_skip_pct(skip_pct: float) -> float:
        return max(0.0, min(1.0, float(skip_pct)))
