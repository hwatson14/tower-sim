from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RuntimeConsumerRule:
    consumer_id: str
    source_node_ids: tuple[str, ...]
    evidence: str
    notes: str = ""


_RUNTIME_CONSUMER_RULES: tuple[RuntimeConsumerRule, ...] = (
    RuntimeConsumerRule(
        consumer_id='runtime_consumer::wave_progression.attack_wave',
        source_node_ids=('canonical_stat::enemy_attack_level_skip_pct',),
        evidence='engine/wave_progression_policy.py; engine/boss_wave_engine.py',
        notes='Attack-wave advancement is deterministically suppressed by effective enemy attack level skip pct.',
    ),
    RuntimeConsumerRule(
        consumer_id='runtime_consumer::wave_progression.health_wave',
        source_node_ids=('canonical_stat::enemy_health_level_skip_pct',),
        evidence='engine/wave_progression_policy.py; engine/boss_wave_engine.py',
        notes='Health-wave advancement is deterministically suppressed by effective enemy health level skip pct.',
    ),
)


def list_runtime_consumer_rules() -> tuple[RuntimeConsumerRule, ...]:
    return _RUNTIME_CONSUMER_RULES



def impacted_runtime_consumers(dirty_node_ids: Iterable[str]) -> tuple[RuntimeConsumerRule, ...]:
    dirty = {str(node_id) for node_id in dirty_node_ids}
    return tuple(
        rule
        for rule in _RUNTIME_CONSUMER_RULES
        if dirty.intersection(rule.source_node_ids)
    )
