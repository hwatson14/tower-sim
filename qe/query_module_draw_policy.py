from __future__ import annotations

from typing import Dict
from qe.models import StatRow

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

def publish_module_draw_policy_surfaces(rows: Dict[str, StatRow]) -> None:
    _publish(
        rows, 'derived::module.draw_policy.common_rate_pct',
        68.5, 'pct', 'scalar',
        'Wiki-backed common module draw rate.',
        [{'source_class': 'wiki_truth', 'value': 68.5, 'unit': 'pct'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.draw_policy.rare_rate_pct',
        29.0, 'pct', 'scalar',
        'Wiki-backed rare module draw rate.',
        [{'source_class': 'wiki_truth', 'value': 29.0, 'unit': 'pct'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.draw_policy.epic_rate_pct',
        2.5, 'pct', 'scalar',
        'Wiki-backed epic module draw rate.',
        [{'source_class': 'wiki_truth', 'value': 2.5, 'unit': 'pct'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.draw_policy.epic_pity_draws',
        150.0, 'draws', 'scalar',
        'Wiki-backed epic pity threshold for module draws.',
        [{'source_class': 'wiki_truth', 'value': 150.0, 'unit': 'draws'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.draw_policy.ten_pull_minimum_rare',
        1.0, 'rare_per_ten_pull', 'scalar',
        'Wiki-backed minimum of one rare in every 10-pull.',
        [{'source_class': 'wiki_truth', 'value': 1.0, 'unit': 'rare_per_ten_pull'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.draw_policy.gem_cost_per_draw',
        20.0, 'gems', 'scalar',
        'Wiki-backed module gem cost per single draw.',
        [{'source_class': 'wiki_truth', 'value': 20.0, 'unit': 'gems'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
