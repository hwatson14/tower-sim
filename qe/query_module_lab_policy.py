from __future__ import annotations

from typing import Any, Dict

from qe.models import StatRow

MODULE_LAB_VALUE_MODELS = {
    'Reroll Shards': {
        'surface_id': 'derived::module.lab.reroll_shards_bonus',
        'unit': 'shards',
        'value_type': 'scalar',
        'formula': lambda level: float(level),
    },
    'Common Drop Chance': {
        'surface_id': 'derived::module.lab.common_drop_chance_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 0.1,
    },
    'Rare Drop Chance': {
        'surface_id': 'derived::module.lab.rare_drop_chance_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 0.1,
    },
    'Daily Mission Shards': {
        'surface_id': 'derived::module.lab.daily_mission_shards_bonus',
        'unit': 'shards_per_mission',
        'value_type': 'scalar',
        'formula': lambda level: float(level),
    },
    'Shatter Shards': {
        'surface_id': 'derived::module.lab.shatter_shards_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 20.0,
    },
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

def publish_module_lab_policy_surfaces(rows: Dict[str, StatRow], account_state_labs: Dict[str, Any]) -> None:
    if not isinstance(account_state_labs, dict):
        raise ValueError('account_state_labs dict required')

    for lab_name, spec in MODULE_LAB_VALUE_MODELS.items():
        raw_level = account_state_labs.get(lab_name, 0)
        if raw_level in (None, ''):
            continue
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            raise ValueError(f'invalid level for lab {lab_name}: {raw_level}')
        value = spec['formula'](level)
        _publish(
            rows,
            spec['surface_id'],
            value,
            spec['unit'],
            spec['value_type'],
            'QE-routed module lab value derived from account_state.labs using wiki-backed level semantics.',
            [{
                'source_class': 'account_state_lab',
                'lab_name': lab_name,
                'level': level,
                'value': value,
                'unit': spec['unit'],
                'source_alignment': 'AccountState+Wiki',
            }],
            {'source_alignment': 'AccountState+Wiki', 'publisher': 'query_surface_publication', 'lab_name': lab_name, 'level': level},
        )
