from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState


def test_wave_progression_policy_identity_when_no_skip():
    policy = WaveProgressionPolicy()
    state = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=100, attack_skip_pct=0.0, health_skip_pct=0.0)
    assert state.attack_wave == 100
    assert state.health_wave == 100


def test_wave_progression_policy_separates_attack_and_health():
    policy = WaveProgressionPolicy()
    state = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.50, health_skip_pct=0.25)
    assert state.attack_wave < state.health_wave < 1000


def test_wave_progression_policy_is_monotonic_across_segments():
    policy = WaveProgressionPolicy()
    state = WaveProgressionState()
    state = policy.advance_to_wave(state=state, target_display_wave=500, attack_skip_pct=0.50, health_skip_pct=0.50)
    first_attack = state.attack_wave
    state = policy.advance_to_wave(state=state, target_display_wave=1000, attack_skip_pct=0.50, health_skip_pct=0.50)
    assert state.attack_wave > first_attack
    assert state.attack_wave < 1000


def test_wave_progression_policy_uses_exact_current_wave_skip_without_warmup():
    policy = WaveProgressionPolicy()
    state = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=100, attack_skip_pct=0.50, health_skip_pct=0.25)
    assert state.attack_wave == 50
    assert state.health_wave == 75
