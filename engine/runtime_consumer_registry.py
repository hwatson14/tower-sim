from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
_OWNERSHIP_LEDGER_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-surface-ownership-ledger.yaml'


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


@lru_cache(maxsize=1)
def load_surface_ownership_ledger() -> dict[str, Any]:
    return yaml.safe_load(_OWNERSHIP_LEDGER_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def ownership_rows_by_node() -> Mapping[str, dict[str, Any]]:
    ledger = load_surface_ownership_ledger()
    rows = [
        *(ledger.get('surface_nodes') or []),
        *(ledger.get('runtime_consumers') or []),
        *(ledger.get('runtime_domains') or []),
        *(ledger.get('analysis_nodes') or []),
        *(ledger.get('out_of_scope_nodes') or []),
    ]
    return {str(row.get('node_id')): row for row in rows}


def assert_runtime_consumer_ownership_contract() -> None:
    ownership_rows = ownership_rows_by_node()
    for rule in _RUNTIME_CONSUMER_RULES:
        consumer_row = ownership_rows.get(rule.consumer_id)
        if consumer_row is None:
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} is missing from the ownership ledger.')
        if consumer_row.get('ownership_status') != 'simulator_owned' or consumer_row.get('governed_by') != 'runtime_simulation':
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must be simulator_owned and governed_by runtime_simulation.')
        if consumer_row.get('downstream_policy') != 'consume_query_owned_surfaces_only':
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must consume query-owned surfaces only.')
        consumed = tuple(consumer_row.get('consumes') or ())
        if consumed != rule.source_node_ids:
            raise ValueError(
                f'Runtime consumer {rule.consumer_id!r} ownership ledger consumes {consumed!r}, expected {rule.source_node_ids!r}.'
            )
        for source_node_id in rule.source_node_ids:
            source_row = ownership_rows.get(source_node_id)
            if source_row is None:
                raise ValueError(f'Runtime consumer source {source_node_id!r} is missing from the ownership ledger.')
            if source_row.get('ownership_status') != 'query_owned' or source_row.get('governed_by') != 'canonical_query_engine':
                raise ValueError(
                    f'Runtime consumer source {source_node_id!r} must be query_owned and governed_by canonical_query_engine.'
                )
            if source_row.get('downstream_policy') != 'consume_only_no_rederivation':
                raise ValueError(
                    f'Runtime consumer source {source_node_id!r} must forbid downstream re-derivation in the ownership ledger.'
                )


def list_runtime_consumer_rules() -> tuple[RuntimeConsumerRule, ...]:
    assert_runtime_consumer_ownership_contract()
    return _RUNTIME_CONSUMER_RULES



def impacted_runtime_consumers(dirty_node_ids: Iterable[str]) -> tuple[RuntimeConsumerRule, ...]:
    assert_runtime_consumer_ownership_contract()
    dirty = {str(node_id) for node_id in dirty_node_ids}
    return tuple(
        rule
        for rule in _RUNTIME_CONSUMER_RULES
        if dirty.intersection(rule.source_node_ids)
    )
