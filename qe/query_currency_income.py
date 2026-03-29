from __future__ import annotations

from typing import Any, Dict

from qe.models import StatRow

DETERMINISTIC_CURRENCY_SURFACES = {
    'coins': ('derived::economy.income.coins', 'coins_income_proxy'),
    'shards': ('derived::economy.income.shards', 'shards_per_week'),
}

SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS = {
    'income.gems.per_week': ('derived::economy.income.gems', 'gems_per_week'),
    'income.power_stones.per_week': ('derived::economy.income.power_stones', 'power_stones_per_week'),
    'income.medals.per_week': ('derived::economy.income.medals', 'medals_per_week'),
    'income.keys.per_week': ('derived::economy.income.keys', 'keys_per_week'),
    'income.bits.per_week': ('derived::economy.income.bits', 'bits_per_week'),
}

UNSUPPORTED_CURRENCY_RESOURCES = {
    'cash': 'run_local_not_persistent',
    'cells': 'no_governed_query_income_model',
}

SUPPORTED_RESOURCE_RESOLUTION_MODES = {
    'coins': 'query_derived_deterministic',
    'gems': 'externalized_manual_input',
    'power_stones': 'externalized_manual_input',
    'medals': 'externalized_manual_input',
    'keys': 'externalized_manual_input',
    'shards': 'query_derived_deterministic',
    'bits': 'externalized_manual_input',
}


def deterministic_surface_ids() -> set[str]:
    return {surface_id for surface_id, _unit in DETERMINISTIC_CURRENCY_SURFACES.values()}


def supported_externalized_surface_ids() -> set[str]:
    return {surface_id for surface_id, _unit in SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS.values()}


def supported_resource_resolution_modes() -> Dict[str, str]:
    return dict(SUPPORTED_RESOURCE_RESOLUTION_MODES)


def supported_manual_input_ids() -> set[str]:
    return set(SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS)


def unsupported_manual_input_ids() -> set[str]:
    return {f'income.{name}.per_week' for name in UNSUPPORTED_CURRENCY_RESOURCES}


def forbidden_income_surface_ids() -> set[str]:
    return {f"derived::economy.income.{name}" for name in UNSUPPORTED_CURRENCY_RESOURCES}


def _manual_input_is_set(entry: Dict[str, Any]) -> bool:
    if bool(entry.get('is_set', False)):
        return True
    return isinstance(entry.get('value'), (int, float))


def _publish_surface(
    rows: Dict[str, StatRow],
    *,
    surface_id: str,
    value: float,
    unit: str,
    notes: str,
    contributors: list[dict],
    schema: dict,
) -> None:
    existing = rows.get(surface_id)
    if existing is not None:
        raise ValueError(f'Query publication collision for {surface_id}')
    rows[surface_id] = StatRow(
        stat_name=surface_id,
        final_value=value,
        value_type='per_week',
        source_count=len(contributors),
        status='resolved',
        notes=notes,
        contributors=contributors,
        schema=schema | {'unit': unit},
    )


def _require_float(rows: Dict[str, StatRow], surface_id: str) -> float | None:
    row = rows.get(surface_id)
    if row is None:
        return None
    try:
        return float(row.final_value)
    except (TypeError, ValueError):
        return None


def _module_draw_shards_per_week(rows: Dict[str, StatRow]) -> tuple[float, list[dict], str] | None:
    gems_per_week = _require_float(rows, 'derived::module.resource_policy.gems_allocated_to_modules_per_week')
    gem_cost_per_draw = _require_float(rows, 'derived::module.draw_policy.gem_cost_per_draw')
    common_rate_pct = _require_float(rows, 'derived::module.draw_policy.common_rate_pct')
    rare_rate_pct = _require_float(rows, 'derived::module.draw_policy.rare_rate_pct')
    epic_rate_pct = _require_float(rows, 'derived::module.draw_policy.epic_rate_pct')
    common_shards = _require_float(rows, 'derived::module.shatter_policy.common_module_shards')
    rare_shards = _require_float(rows, 'derived::module.shatter_policy.rare_module_shards')
    epic_immediate_shards = _require_float(rows, 'derived::module.draw_policy.epic_draw_immediate_shard_value')
    ten_pull_ev_multiplier = _require_float(rows, 'derived::module.draw_policy.ten_pull_ev_multiplier')
    required = (
        gems_per_week,
        gem_cost_per_draw,
        common_rate_pct,
        rare_rate_pct,
        epic_rate_pct,
        common_shards,
        rare_shards,
        epic_immediate_shards,
        ten_pull_ev_multiplier,
    )
    if any(value is None for value in required):
        return None

    expected_shards_per_draw = (
        (common_rate_pct / 100.0) * common_shards
        + (rare_rate_pct / 100.0) * rare_shards
        + (epic_rate_pct / 100.0) * epic_immediate_shards
    ) * ten_pull_ev_multiplier
    draws_per_week = gems_per_week / gem_cost_per_draw if gem_cost_per_draw > 0.0 else 0.0
    value = draws_per_week * expected_shards_per_draw
    contributors = [
        {'surface_id': 'derived::module.resource_policy.gems_allocated_to_modules_per_week', 'value': gems_per_week, 'unit': 'gems_per_week'},
        {'surface_id': 'derived::module.draw_policy.gem_cost_per_draw', 'value': gem_cost_per_draw, 'unit': 'gems'},
        {'surface_id': 'derived::module.draw_policy.common_rate_pct', 'value': common_rate_pct, 'unit': 'pct'},
        {'surface_id': 'derived::module.draw_policy.rare_rate_pct', 'value': rare_rate_pct, 'unit': 'pct'},
        {'surface_id': 'derived::module.draw_policy.epic_rate_pct', 'value': epic_rate_pct, 'unit': 'pct'},
        {'surface_id': 'derived::module.shatter_policy.common_module_shards', 'value': common_shards, 'unit': 'shards'},
        {'surface_id': 'derived::module.shatter_policy.rare_module_shards', 'value': rare_shards, 'unit': 'shards'},
        {'surface_id': 'derived::module.draw_policy.epic_draw_immediate_shard_value', 'value': epic_immediate_shards, 'unit': 'shards'},
        {'surface_id': 'derived::module.draw_policy.ten_pull_ev_multiplier', 'value': ten_pull_ev_multiplier, 'unit': 'multiplier'},
    ]
    notes = 'Module draw shard lane uses the KB package-rule EV: epics are retained for zero immediate shards and 10-pulls are treated as ten independent singles.'
    return value, contributors, notes


def _publish_deterministic_shards(rows: Dict[str, StatRow]) -> None:
    bosses_per_day = _require_float(rows, 'support_surface::scenario.bosses_per_day_effective')
    expected_shards_per_boss = _require_float(rows, 'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss')
    if bosses_per_day is None or expected_shards_per_boss is None:
        return

    boss_drop_shards_per_week = bosses_per_day * 7.0 * expected_shards_per_boss
    contributors = [
        {
            'surface_id': 'support_surface::scenario.bosses_per_day_effective',
            'source_class': 'published_surface',
            'value': bosses_per_day,
            'unit': 'bosses_per_day',
            'source_alignment': 'Simulator+QE',
        },
        {
            'surface_id': 'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss',
            'source_class': 'published_surface',
            'value': expected_shards_per_boss,
            'unit': 'shards_per_boss',
            'source_alignment': 'WikiDerived+QE',
        },
    ]
    total = boss_drop_shards_per_week
    notes_parts = ['Weekly module shard income surface derived from farming throughput, module boss-drop EV, and any available mission/draw lanes.']

    missions_per_week = _require_float(rows, 'planner.manual_policy.module.missions_per_week')
    shards_per_mission = _require_float(rows, 'derived::module.mission_policy.total_daily_mission_shards')
    if missions_per_week is not None and shards_per_mission is not None:
        mission_shards_per_week = missions_per_week * shards_per_mission
        total += mission_shards_per_week
        contributors.extend([
            {
                'surface_id': 'planner.manual_policy.module.missions_per_week',
                'source_class': 'published_surface',
                'value': missions_per_week,
                'unit': 'missions_per_week',
                'source_alignment': 'Inputs',
            },
            {
                'surface_id': 'derived::module.mission_policy.total_daily_mission_shards',
                'source_class': 'published_surface',
                'value': shards_per_mission,
                'unit': 'shards_per_mission',
                'source_alignment': 'Wiki+QE',
            },
        ])

    draw_lane = _module_draw_shards_per_week(rows)
    if draw_lane is not None:
        draw_shards_per_week, draw_contributors, draw_notes = draw_lane
        total += draw_shards_per_week
        contributors.extend(draw_contributors)
        notes_parts.append(draw_notes)

    _publish_surface(
        rows,
        surface_id='derived::economy.income.shards',
        value=total,
        unit='shards_per_week',
        notes=' '.join(notes_parts),
        contributors=contributors,
        schema={'source_alignment': 'Simulator+QE', 'externalized': False, 'publisher': 'query_surface_publication'},
    )


def publish_currency_income_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    eecon_base = rows.get('derived::eecon.base_coin_income')
    if eecon_base is not None:
        _publish_surface(
            rows,
            surface_id='derived::economy.income.coins',
            value=float(eecon_base.final_value),
            unit='coins_income_proxy',
            notes='Coin-first persistent income proxy surface derived from published eEcon base.',
            contributors=[{
                'surface_id': 'derived::economy.income.coins',
                'source_class': 'published_surface',
                'source_name': 'derived::eecon.base_coin_income',
                'value': eecon_base.final_value,
                'unit': 'coins_income_proxy',
                'trust_label': 'accepted_model',
                'source_alignment': 'EP',
            }],
            schema={'source_alignment': 'EP', 'externalized': False, 'publisher': 'query_surface_publication'},
        )

    _publish_deterministic_shards(rows)

    manual_inputs = manual_advisory_inputs or {}
    for input_id, (surface_id, unit) in SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS.items():
        entry = manual_inputs.get(input_id)
        if entry is None or not _manual_input_is_set(entry):
            continue
        try:
            value = float(entry.get('value'))
        except (TypeError, ValueError):
            continue
        _publish_surface(
            rows,
            surface_id=surface_id,
            value=value,
            unit=unit,
            notes='Derived from the input-owned manual_advisory_inputs surface.',
            contributors=[{
                'surface_id': surface_id,
                'source_class': 'manual_input',
                'input_id': input_id,
                'value': value,
                'unit': unit,
                'trust_label': entry.get('trust_label', 'externally_observed'),
                'consumer_scope': entry.get('consumer_scope', []),
                'source_alignment': 'Inputs',
            }],
            schema={'source_alignment': 'Inputs', 'input_id': input_id, 'externalized': True, 'publisher': 'query_surface_publication', 'is_set': True},
        )


def manual_income_input_contract_snapshot() -> Dict[str, Any]:
    """Expose the user-editable manual persistent-income lane for tests and audits."""
    return {
        'editable_manual_input_ids': sorted(supported_manual_input_ids()),
        'supported_manual_input_ids': sorted(supported_manual_input_ids()),
        'unsupported_manual_input_ids': sorted(unsupported_manual_input_ids()),
        'forbidden_income_surface_ids': sorted(forbidden_income_surface_ids()),
        'default_file_contains_only_supported_inputs': True,
    }


def currency_income_surface_contract_snapshot() -> Dict[str, Any]:
    """Expose the implementation-side support boundary for tests and audits."""
    return {
        'deterministic': {k: {'surface_id': v[0], 'unit': v[1], 'resolution_mode': SUPPORTED_RESOURCE_RESOLUTION_MODES[k]} for k, v in DETERMINISTIC_CURRENCY_SURFACES.items()},
        'externalized_manual': {
            k: {
                'surface_id': v[0],
                'unit': v[1],
                'manual_input_id': f'income.{k}.per_week',
                'resolution_mode': SUPPORTED_RESOURCE_RESOLUTION_MODES[k],
            }
            for k, v in {
                'gems': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.gems.per_week'],
                'power_stones': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.power_stones.per_week'],
                'medals': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.medals.per_week'],
                'keys': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.keys.per_week'],
                'bits': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.bits.per_week'],
            }.items()
        },
        'unsupported': dict(UNSUPPORTED_CURRENCY_RESOURCES),
    }


def income_resolution_audit_snapshot() -> Dict[str, Any]:
    """Expose the complete current income-resolution boundary for audits."""
    supported_resources = set(DETERMINISTIC_CURRENCY_SURFACES) | {
        input_id.split('.')[1] for input_id in SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS
    }
    resolution_modes = supported_resource_resolution_modes()
    return {
        'supported_resources': sorted(supported_resources),
        'deterministic_resources': sorted(DETERMINISTIC_CURRENCY_SURFACES),
        'externalized_manual_resources': sorted({input_id.split('.')[1] for input_id in SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS}),
        'unsupported_resources': sorted(UNSUPPORTED_CURRENCY_RESOURCES),
        'resolution_modes': dict(sorted(resolution_modes.items())),
        'supported_surface_ids': sorted(deterministic_surface_ids() | supported_externalized_surface_ids()),
        'forbidden_surface_ids': sorted(forbidden_income_surface_ids()),
        'complete_partition': sorted(supported_resources | set(UNSUPPORTED_CURRENCY_RESOURCES)),
    }


def resolve_currency_income_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, StatRow]:
    tmp = dict(rows)
    publish_currency_income_surfaces(tmp, manual_advisory_inputs=manual_advisory_inputs)
    return {k: v for k, v in tmp.items() if k.startswith('derived::economy.income.')}
