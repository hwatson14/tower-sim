from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import yaml as _yaml

from models.statbook import StatRow

_DEFAULT_MANUAL_INPUT_PATH = Path(__file__).resolve().parents[1] / 'input' / 'manual_inputs.yaml'  # T10: canonical path (assumptions.yaml archived)

_DROP_ECONOMY_INPUT_MAP = {
    'module.runtime.tier_for_drop_tables': {
        'surface_id': 'derived::module.runtime_profile.farming_tier',
        'unit': 'tier',
    },
    'module.labs.reroll_shards_bonus': {
        'surface_id': 'derived::module.lab.reroll_shards_bonus',
        'unit': 'shards',
    },
    'module.labs.common_drop_chance_bonus_pct': {
        'surface_id': 'derived::module.lab.common_drop_chance_bonus_pct',
        'unit': 'pct',
    },
    'module.labs.rare_drop_chance_bonus_pct': {
        'surface_id': 'derived::module.lab.rare_drop_chance_bonus_pct',
        'unit': 'pct',
    },
    'module.labs.daily_mission_shards_bonus': {
        'surface_id': 'derived::module.lab.daily_mission_shards_bonus',
        'unit': 'shards_per_mission',
    },
}


def _load_drop_economy_manual_inputs(manual_input_path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    path = Path(manual_input_path) if manual_input_path is not None else _DEFAULT_MANUAL_INPUT_PATH
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding='utf-8')
        if path.suffix in ('.yaml', '.yml'):
            payload = (_yaml.safe_load(text) or {}).get('manual_advisory_inputs') or {}
        else:
            payload = json.loads(text)
    except Exception:
        return {}
    rows = payload.get('inputs', [])
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get('input_id'), str):
                out[row['input_id']] = row
    return out


def _prepopulate_upstream_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> None:
    manual_inputs = _load_drop_economy_manual_inputs(manual_input_path)
    for input_id, spec in _DROP_ECONOMY_INPUT_MAP.items():
        surface_id = spec['surface_id']
        if surface_id in rows:
            continue
        entry = manual_inputs.get(input_id)
        if entry is None or not entry.get('is_set', False):
            continue
        try:
            value = float(entry['value'])
        except (TypeError, ValueError, KeyError):
            continue
        rows[surface_id] = StatRow(
            stat_name=surface_id,
            final_value=value,
            value_type='scalar',
            source_count=1,
            status='resolved',
            notes=f'Pre-populated from manual_advisory_inputs.json input {input_id}.',
            contributors=[{'source_class': 'manual_input', 'input_id': input_id, 'value': value, 'unit': spec['unit']}],
            schema={'source_alignment': 'Inputs', 'unit': spec['unit'], 'publisher': 'query_module_drop_economy'},
        )

_REROLL_SHARDS_BY_TIER = {
    1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 6.0, 6: 8.0, 7: 12.0, 8: 18.0, 9: 25.0,
    10: 32.0, 11: 40.0, 12: 45.0, 13: 50.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0, 18: 75.0,
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

def publish_module_drop_economy_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> None:
    _prepopulate_upstream_surfaces(rows, manual_input_path)
    farming_tier = int(_require(rows, 'derived::module.runtime_profile.farming_tier'))
    if farming_tier not in _REROLL_SHARDS_BY_TIER:
        raise ValueError(f'unsupported farming tier for module drop tables: {farming_tier}')

    reroll_lab_bonus = rows.get('derived::module.lab.reroll_shards_bonus')
    common_lab_bonus = rows.get('derived::module.lab.common_drop_chance_bonus_pct')
    rare_lab_bonus = rows.get('derived::module.lab.rare_drop_chance_bonus_pct')
    mission_lab_bonus = rows.get('derived::module.lab.daily_mission_shards_bonus')
    shatter_bonus = rows.get('derived::module.lab.shatter_shards_bonus_pct')

    reroll_bonus = float(reroll_lab_bonus.final_value) if reroll_lab_bonus else 0.0
    common_bonus = float(common_lab_bonus.final_value) if common_lab_bonus else 0.0
    rare_bonus = float(rare_lab_bonus.final_value) if rare_lab_bonus else 0.0
    mission_bonus = float(mission_lab_bonus.final_value) if mission_lab_bonus else 0.0
    shatter_mult = 1.0 + ((float(shatter_bonus.final_value) if shatter_bonus else 0.0) / 100.0)

    _publish(
        rows, 'derived::module.drop_policy.reroll_shard_drop_chance_pct',
        15.0, 'pct', 'scalar',
        'Wiki-backed base boss reroll shard drop chance.',
        [{'source_class': 'wiki_truth', 'value': 15.0, 'unit': 'pct'}],
        {'source_alignment': 'Wiki', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.drop_policy.reroll_shards_per_boss',
        _REROLL_SHARDS_BY_TIER[farming_tier] + reroll_bonus, 'shards', 'scalar',
        'Wiki-backed tier reroll shard amount per successful boss drop plus QE-routed lab bonus.',
        [{'source_class': 'wiki_truth', 'value': _REROLL_SHARDS_BY_TIER[farming_tier], 'unit': 'shards'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication', 'tier': farming_tier},
    )
    _publish(
        rows, 'derived::module.drop_policy.common_module_drop_chance_pct',
        2.0 + common_bonus, 'pct', 'scalar',
        'Wiki-backed base common module boss drop chance plus QE-routed lab bonus.',
        [{'source_class': 'wiki_truth', 'value': 2.0, 'unit': 'pct'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.drop_policy.rare_module_drop_chance_pct',
        0.5 + rare_bonus, 'pct', 'scalar',
        'Wiki-backed base rare module boss drop chance plus QE-routed lab bonus.',
        [{'source_class': 'wiki_truth', 'value': 0.5, 'unit': 'pct'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.shatter_policy.common_module_shards',
        5.0 * shatter_mult, 'shards', 'scalar',
        'Wiki-backed common module shatter shards with QE-routed shatter-shards lab applied.',
        [{'source_class': 'wiki_truth', 'value': 5.0, 'unit': 'shards'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.shatter_policy.rare_module_shards',
        10.0 * shatter_mult, 'shards', 'scalar',
        'Wiki-backed rare module shatter shards with QE-routed shatter-shards lab applied.',
        [{'source_class': 'wiki_truth', 'value': 10.0, 'unit': 'shards'}],
        {'source_alignment': 'Wiki+QE', 'publisher': 'query_surface_publication'},
    )
    _publish(
        rows, 'derived::module.mission_policy.daily_mission_shards_bonus',
        mission_bonus, 'shards_per_mission', 'scalar',
        'QE-routed daily mission shard bonus lab value. Base mission shard reward remains unresolved.',
        [{'source_class': 'account_state_lab', 'value': mission_bonus, 'unit': 'shards_per_mission'}],
        {'source_alignment': 'QE', 'publisher': 'query_surface_publication', 'base_mission_shards_unresolved': True},
    )

    expected_shatter_equiv = (
        (2.0 + common_bonus) / 100.0 * (5.0 * shatter_mult)
        + (0.5 + rare_bonus) / 100.0 * (10.0 * shatter_mult)
    )
    _publish(
        rows, 'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss',
        expected_shatter_equiv, 'shards_per_boss', 'scalar',
        'Computed shatter-equivalent expected shard value of boss module drops assuming all dropped common/rare modules are shattered.',
        [{'source_class': 'computed_from_wiki_truth', 'value': expected_shatter_equiv, 'unit': 'shards_per_boss'}],
        {'source_alignment': 'WikiDerived+QE', 'publisher': 'query_surface_publication', 'assumption': 'all_dropped_common_and_rare_modules_shattered'},
    )
