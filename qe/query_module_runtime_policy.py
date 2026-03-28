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
                'publisher': 'query_surface_publication',
                'is_set': True,
            },
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
