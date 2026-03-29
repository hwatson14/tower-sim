"""Bounded QE owner for module policy and module-economy publication surfaces.

This module intentionally consolidates the module publication/policy surface area
so QE does not fragment into several tiny module-only publisher files.
"""

from __future__ import annotations

from typing import Any, Dict

from qe.models import StatRow

SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS = {
    'module.farming.hours_per_day': {
        'surface_id': 'derived::module.runtime_profile.farming_hours_per_day',
        'unit': 'hours_per_day',
        'value_type': 'scalar',
    },
    'module.resource.gems_allocated_to_modules.per_week': {
        'surface_id': 'derived::module.resource_policy.gems_allocated_to_modules_per_week',
        'unit': 'gems_per_week',
        'value_type': 'per_week',
    },
    'module.missions.per_week': {
        'surface_id': 'planner.manual_policy.module.missions_per_week',
        'unit': 'missions_per_week',
        'value_type': 'per_week',
    },
}
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
MODULE_DROP_ECONOMY_INPUT_MAP = {
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
REROLL_SHARDS_BY_TIER = {
    1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 6.0, 6: 8.0, 7: 12.0, 8: 18.0, 9: 25.0,
    10: 32.0, 11: 40.0, 12: 45.0, 13: 50.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0, 18: 75.0,
}
BASE_DAILY_MISSION_SHARDS_BY_TIER = {
    1: 0.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 12.0, 6: 15.0, 7: 20.0, 8: 25.0, 9: 30.0,
    10: 34.0, 11: 38.0, 12: 42.0, 13: 48.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0,
    18: 75.0, 19: 80.0, 20: 85.0, 21: 90.0,
}
MODULE_DRAW_POLICY_ROWS = (
    ('derived::module.draw_policy.common_rate_pct', 68.5, 'pct', 'scalar', 'Wiki-backed common module draw rate.'),
    ('derived::module.draw_policy.rare_rate_pct', 29.0, 'pct', 'scalar', 'Wiki-backed rare module draw rate.'),
    ('derived::module.draw_policy.epic_rate_pct', 2.5, 'pct', 'scalar', 'Wiki-backed epic module draw rate.'),
    ('derived::module.draw_policy.epic_pity_draws', 150.0, 'draws', 'scalar', 'Wiki-backed epic pity threshold for module draws.'),
    ('derived::module.draw_policy.ten_pull_minimum_rare', 1.0, 'rare_per_ten_pull', 'scalar', 'Wiki-backed minimum of one rare in every 10-pull.'),
    ('derived::module.draw_policy.gem_cost_per_draw', 20.0, 'gems', 'scalar', 'Wiki-backed module gem cost per single draw.'),
    ('derived::module.draw_policy.epic_draw_immediate_shard_value', 0.0, 'shards', 'scalar', 'KB package-rule epic draw immediate shard value: retained epics contribute zero immediate shards.'),
    ('derived::module.draw_policy.ten_pull_ev_multiplier', 1.0, 'multiplier', 'scalar', 'KB package-rule ten-pull EV multiplier: a 10-pull is modeled as ten independent singles for EV.'),
)


def supported_module_runtime_policy_input_ids() -> set[str]:
    return set(SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS)


def published_module_runtime_policy_surface_ids() -> set[str]:
    return {row['surface_id'] for row in SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.values()}


def _manual_input_is_set(entry: Dict[str, Any]) -> bool:
    if bool(entry.get('is_set', False)):
        return True
    return isinstance(entry.get('value'), (int, float))


def _publish_surface(rows: Dict[str, StatRow], *, surface_id: str, value: float, value_type: str, unit: str, notes: str, contributors: list[dict], schema: dict) -> None:
    existing = rows.get(surface_id)
    if existing is not None:
        raise ValueError(f'Module runtime/policy publication collision for {surface_id}')
    rows[surface_id] = StatRow(
        stat_name=surface_id,
        final_value=value,
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


def _prepopulate_drop_economy_upstream_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    manual_inputs = manual_advisory_inputs or {}
    for input_id, spec in MODULE_DROP_ECONOMY_INPUT_MAP.items():
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
            notes=f'Pre-populated from the input-owned manual_advisory_inputs surface for {input_id}.',
            contributors=[{'source_class': 'manual_input', 'input_id': input_id, 'value': value, 'unit': spec['unit']}],
            schema={'source_alignment': 'Inputs', 'unit': spec['unit'], 'publisher': 'query_module_policy'},
        )


def publish_module_runtime_policy_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    manual_inputs = manual_advisory_inputs or {}
    for input_id, spec in SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.items():
        entry = manual_inputs.get(input_id)
        if entry is None or not _manual_input_is_set(entry):
            continue
        try:
            value = float(entry.get('value'))
        except (TypeError, ValueError):
            continue
        _publish_surface(
            rows,
            surface_id=spec['surface_id'],
            value=value,
            value_type=spec['value_type'],
            unit=spec['unit'],
            notes='Derived from the input-owned manual_advisory_inputs surface.',
            contributors=[{
                'surface_id': spec['surface_id'],
                'source_class': 'manual_input',
                'input_id': input_id,
                'value': value,
                'unit': spec['unit'],
                'trust_label': entry.get('trust_label', 'accepted_model'),
                'consumer_scope': entry.get('consumer_scope', []),
                'source_alignment': 'Inputs',
            }],
            schema={
                'source_alignment': 'Inputs',
                'input_id': input_id,
                'externalized': True,
                'publisher': 'query_module_policy',
                'is_set': True,
            },
        )


def publish_module_draw_policy_surfaces(rows: Dict[str, StatRow]) -> None:
    for surface_id, value, unit, value_type, notes in MODULE_DRAW_POLICY_ROWS:
        _publish_surface(
            rows,
            surface_id=surface_id,
            value=value,
            value_type=value_type,
            unit=unit,
            notes=notes,
            contributors=[{'source_class': 'wiki_truth', 'value': value, 'unit': unit}],
            schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy'},
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
        _publish_surface(
            rows,
            surface_id=spec['surface_id'],
            value=value,
            value_type=spec['value_type'],
            unit=spec['unit'],
            notes='QE-routed module lab value derived from account_state.labs using wiki-backed level semantics.',
            contributors=[{
                'source_class': 'account_state_lab',
                'lab_name': lab_name,
                'level': level,
                'value': value,
                'unit': spec['unit'],
                'source_alignment': 'AccountState+Wiki',
            }],
            schema={'source_alignment': 'AccountState+Wiki', 'publisher': 'query_module_policy', 'lab_name': lab_name, 'level': level},
        )


def publish_module_drop_economy_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    _prepopulate_drop_economy_upstream_surfaces(rows, manual_advisory_inputs)
    farming_tier = int(_require(rows, 'derived::module.runtime_profile.farming_tier'))
    if farming_tier not in REROLL_SHARDS_BY_TIER:
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

    _publish_surface(
        rows, surface_id='derived::module.drop_policy.reroll_shard_drop_chance_pct',
        value=15.0, unit='pct', value_type='scalar',
        notes='Wiki-backed base boss reroll shard drop chance.',
        contributors=[{'source_class': 'wiki_truth', 'value': 15.0, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.reroll_shards_per_boss',
        value=REROLL_SHARDS_BY_TIER[farming_tier] + reroll_bonus, unit='shards', value_type='scalar',
        notes='Wiki-backed tier reroll shard amount per successful boss drop plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': REROLL_SHARDS_BY_TIER[farming_tier], 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy', 'tier': farming_tier},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.common_module_drop_chance_pct',
        value=2.0 + common_bonus, unit='pct', value_type='scalar',
        notes='Wiki-backed base common module boss drop chance plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': 2.0, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.rare_module_drop_chance_pct',
        value=0.5 + rare_bonus, unit='pct', value_type='scalar',
        notes='Wiki-backed base rare module boss drop chance plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': 0.5, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.shatter_policy.common_module_shards',
        value=5.0 * shatter_mult, unit='shards', value_type='scalar',
        notes='Wiki-backed common module shatter shards with QE-routed shatter-shards lab applied.',
        contributors=[{'source_class': 'wiki_truth', 'value': 5.0, 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.shatter_policy.rare_module_shards',
        value=10.0 * shatter_mult, unit='shards', value_type='scalar',
        notes='Wiki-backed rare module shatter shards with QE-routed shatter-shards lab applied.',
        contributors=[{'source_class': 'wiki_truth', 'value': 10.0, 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.mission_policy.daily_mission_shards_bonus',
        value=mission_bonus, unit='shards_per_mission', value_type='scalar',
        notes='QE-routed daily mission shard bonus lab value. Base mission shard reward remains unresolved.',
        contributors=[{'source_class': 'account_state_lab', 'value': mission_bonus, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'QE', 'publisher': 'query_module_policy', 'base_mission_shards_unresolved': True},
    )

    expected_shatter_equiv = (
        (2.0 + common_bonus) / 100.0 * (5.0 * shatter_mult)
        + (0.5 + rare_bonus) / 100.0 * (10.0 * shatter_mult)
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss',
        value=expected_shatter_equiv, unit='shards_per_boss', value_type='scalar',
        notes='Computed shatter-equivalent expected shard value of boss module drops assuming all dropped common/rare modules are shattered.',
        contributors=[{'source_class': 'computed_from_wiki_truth', 'value': expected_shatter_equiv, 'unit': 'shards_per_boss'}],
        schema={'source_alignment': 'WikiDerived+QE', 'publisher': 'query_module_policy', 'assumption': 'all_dropped_common_and_rare_modules_shattered'},
    )


def publish_module_mission_economy_surfaces(rows: Dict[str, StatRow]) -> None:
    highest_tier = int(_require(rows, 'derived::module.runtime_profile.highest_tier_unlocked'))
    if highest_tier not in BASE_DAILY_MISSION_SHARDS_BY_TIER:
        raise ValueError(f'unsupported highest tier unlocked for mission economy: {highest_tier}')

    mission_bonus_row = rows.get('derived::module.mission_policy.daily_mission_shards_bonus')
    mission_bonus = float(mission_bonus_row.final_value) if mission_bonus_row else 0.0
    base_shards = BASE_DAILY_MISSION_SHARDS_BY_TIER[highest_tier]
    total_per_mission = base_shards + mission_bonus

    _publish_surface(
        rows, surface_id='derived::module.mission_policy.base_daily_mission_shards',
        value=base_shards, unit='shards_per_mission', value_type='scalar',
        notes='Wiki-backed base daily mission shard reward by highest tier unlocked.',
        contributors=[{'source_class': 'wiki_truth', 'value': base_shards, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy', 'highest_tier_unlocked': highest_tier},
    )
    _publish_surface(
        rows, surface_id='derived::module.mission_policy.total_daily_mission_shards',
        value=total_per_mission, unit='shards_per_mission', value_type='scalar',
        notes='Total daily mission shard reward per mission: wiki-backed base plus QE-routed lab bonus.',
        contributors=[{'source_class': 'computed_from_wiki_and_qe', 'value': total_per_mission, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy', 'highest_tier_unlocked': highest_tier},
    )


def module_runtime_policy_surface_contract_snapshot() -> Dict[str, Any]:
    return {
        'supported_manual_input_ids': sorted(supported_module_runtime_policy_input_ids()),
        'published_surface_ids': sorted(published_module_runtime_policy_surface_ids()),
        'supported_inputs': {
            input_id: {
                'surface_id': spec['surface_id'],
                'unit': spec['unit'],
                'value_type': spec['value_type'],
            }
            for input_id, spec in sorted(SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.items())
        },
        'planner_manual_inputs_retained': ['module.planner.horizon_days', 'module.missions.per_week'],
    }
