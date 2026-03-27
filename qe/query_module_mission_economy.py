from __future__ import annotations

from typing import Dict

from qe.models import StatRow

_BASE_DAILY_MISSION_SHARDS_BY_TIER = {
    1: 0.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 12.0, 6: 15.0, 7: 20.0, 8: 25.0, 9: 30.0,
    10: 34.0, 11: 38.0, 12: 42.0, 13: 48.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0,
    18: 75.0, 19: 80.0, 20: 85.0, 21: 90.0,
}

def _publish(rows: Dict[str, StatRow], surface_id: str, value: float, unit: str, value_type: str, notes: str, contributors: list[dict], schema: dict) -> None:
    if surface_id in rows:
        raise ValueError(f'collision for {surface_id}')
    rows[surface_id] = StatRow(
        stat_name=surface_id,
        final_value=float(value),
        value_type=value_type,
        source_count=len(contributors),
        status='resolved',
        notes=notes,
        contributors=contributors,
        schema=schema | {'unit': unit},
    )

def _require(rows: Dict[str, StatRow], surface_id: str) -> float:
    row = rows.get(surface_id)
    if row is None:
        raise ValueError(f'missing required upstream surface: {surface_id}')
    return float(row.final_value)

def publish_module_mission_economy_surfaces(rows: Dict[str, StatRow]) -> None:
    highest_tier = int(_require(rows, 'derived::module.runtime_profile.highest_tier_unlocked'))
    if highest_tier not in _BASE_DAILY_MISSION_SHARDS_BY_TIER:
        raise ValueError(f'unsupported highest tier unlocked for mission economy: {highest_tier}')

    mission_bonus_row = rows.get('derived::module.mission_policy.daily_mission_shards_bonus')
    mission_bonus = float(mission_bonus_row.final_value) if mission_bonus_row else 0.0
    base_shards = _BASE_DAILY_MISSION_SHARDS_BY_TIER[highest_tier]
    total_per_mission = base_shards + mission_bonus

    _publish(
        rows,
        'derived::module.mission_policy.base_daily_mission_shards',
        base_shards,
        'shards_per_mission',
        'scalar',
        'Wiki-backed base daily mission shard reward by highest tier unlocked.',
        [{'source_class': 'wiki_truth', 'value': base_shards, 'unit': 'shards_per_mission'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication', 'highest_tier_unlocked': highest_tier},
    )
    _publish(
        rows,
        'derived::module.mission_policy.total_daily_mission_shards',
        total_per_mission,
        'shards_per_mission',
        'scalar',
        'Total daily mission shard reward per mission: wiki-backed base plus QE-routed lab bonus.',
        [{'source_class': 'computed_from_wiki_and_qe', 'value': total_per_mission, 'unit': 'shards_per_mission'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication', 'highest_tier_unlocked': highest_tier},
    )
