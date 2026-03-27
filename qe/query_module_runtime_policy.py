from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import yaml as _yaml

from qe.models import StatRow

_DEFAULT_MANUAL_INPUT_PATH = Path(__file__).resolve().parents[1] / 'input' / 'manual_inputs.yaml'  # T10: canonical path (assumptions.yaml archived)

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


def _load_manual_inputs(manual_input_path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
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

    module_missions = payload.get('module', {}).get('missions', {}).get('per_week')
    if 'module.missions.per_week' not in out and isinstance(module_missions, (int, float)):
        out['module.missions.per_week'] = {
            'input_id': 'module.missions.per_week',
            'value': float(module_missions),
            'is_set': True,
            'trust_label': 'policy_heuristic',
            'consumer_scope': ['optimizer', 'advisor'],
            'input_kind': 'accepted_model_override',
        }
    return out


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


def publish_module_runtime_policy_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> None:
    manual_inputs = _load_manual_inputs(manual_input_path)
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
            notes='Derived from input/assumptions.yaml manual_advisory_inputs explicit module runtime/policy planning input.',
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
        'default_manual_input_path': str(_DEFAULT_MANUAL_INPUT_PATH),
        'supported_manual_input_file': 'input/assumptions.yaml',
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
