from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.runtime_consumer_registry import impacted_runtime_consumers, list_runtime_consumer_rules
from engine.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState


def test_runtime_consumer_registry_exposes_skip_consumers():
    rules = {rule.consumer_id: rule for rule in list_runtime_consumer_rules()}
    assert 'runtime_consumer::wave_progression.attack_wave' in rules
    assert 'runtime_consumer::wave_progression.health_wave' in rules
    assert rules['runtime_consumer::wave_progression.attack_wave'].source_node_ids == ('canonical_stat::enemy_attack_level_skip_pct',)
    assert rules['runtime_consumer::wave_progression.health_wave'].source_node_ids == ('canonical_stat::enemy_health_level_skip_pct',)


def test_impacted_runtime_consumers_filters_by_dirty_nodes():
    impacted = {rule.consumer_id for rule in impacted_runtime_consumers({'canonical_stat::enemy_attack_level_skip_pct'})}
    assert impacted == {'runtime_consumer::wave_progression.attack_wave'}


def test_wave_progression_policy_attack_wave_is_monotonic_with_attack_skip_pct():
    policy = WaveProgressionPolicy()
    low = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.10, health_skip_pct=0.0)
    high = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.40, health_skip_pct=0.0)
    assert high.attack_wave < low.attack_wave
    assert high.health_wave == low.health_wave == 1000


def test_wave_progression_policy_health_wave_is_monotonic_with_health_skip_pct():
    policy = WaveProgressionPolicy()
    low = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.0, health_skip_pct=0.10)
    high = policy.advance_to_wave(state=WaveProgressionState(), target_display_wave=1000, attack_skip_pct=0.0, health_skip_pct=0.40)
    assert high.health_wave < low.health_wave
    assert high.attack_wave == low.attack_wave == 1000
