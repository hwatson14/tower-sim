from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from models.statbook import StatRow

_DEFAULT_MANUAL_INPUT_PATH = Path(__file__).resolve().parents[1] / 'input' / 'manual_advisory_inputs.json'
# Users may edit input/manual_advisory_inputs.json directly to provide weekly persistent-income observations for supported externalized resources.

DETERMINISTIC_CURRENCY_SURFACES = {
    'coins': ('derived::economy.income.coins', 'coins_income_proxy'),
}

SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS = {
    'income.gems.per_week': ('derived::economy.income.gems', 'gems_per_week'),
    'income.stones.per_week': ('derived::economy.income.stones', 'stones_per_week'),
    'income.medals.per_week': ('derived::economy.income.medals', 'medals_per_week'),
    'income.keys.per_week': ('derived::economy.income.keys', 'keys_per_week'),
    'income.shards.per_week': ('derived::economy.income.shards', 'shards_per_week'),
    'income.bits.per_week': ('derived::economy.income.bits', 'bits_per_week'),
}

UNSUPPORTED_CURRENCY_RESOURCES = {
    'cash': 'run_local_not_persistent',
    'cells': 'no_governed_phase3_income_model',
    'modules': 'no_governed_phase3_income_model',
}

SUPPORTED_RESOURCE_RESOLUTION_MODES = {
    'coins': 'query_derived_deterministic',
    'gems': 'externalized_manual_input',
    'stones': 'externalized_manual_input',
    'medals': 'externalized_manual_input',
    'keys': 'externalized_manual_input',
    'shards': 'externalized_manual_input',
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


def _load_manual_inputs(manual_input_path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    path = Path(manual_input_path) if manual_input_path is not None else _DEFAULT_MANUAL_INPUT_PATH
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get('inputs', [])
    if not isinstance(rows, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get('input_id'), str):
            out[row['input_id']] = row
    return out


def _manual_input_is_set(entry: Dict[str, Any]) -> bool:
    if bool(entry.get('is_set', False)):
        return True
    return isinstance(entry.get('value'), (int, float))


def _publish_surface(rows: Dict[str, StatRow], *, surface_id: str, value: float, unit: str, notes: str, contributors: list[dict], schema: dict) -> None:
    existing = rows.get(surface_id)
    if existing is not None:
        raise ValueError(f'Phase 3 publication collision for {surface_id}')
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


def publish_currency_income_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> None:
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

    manual_inputs = _load_manual_inputs(manual_input_path)
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
            notes='Derived from input/manual_advisory_inputs.json user input surface.',
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
        'default_manual_input_path': str(_DEFAULT_MANUAL_INPUT_PATH),
        'supported_manual_input_file': 'input/manual_advisory_inputs.json',
        'editable_manual_input_ids': sorted(supported_manual_input_ids()),
        'supported_manual_input_ids': sorted(supported_manual_input_ids()),
        'unsupported_manual_input_ids': sorted(unsupported_manual_input_ids()),
        'forbidden_income_surface_ids': sorted(forbidden_income_surface_ids()),
        'default_file_contains_only_supported_inputs': True,
    }


def currency_income_surface_contract_snapshot() -> Dict[str, Any]:
    """Expose the Phase 3 implementation-side support boundary for tests and audits."""
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
                'stones': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.stones.per_week'],
                'medals': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.medals.per_week'],
                'keys': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.keys.per_week'],
                'shards': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.shards.per_week'],
                'bits': SUPPORTED_EXTERNALIZED_CURRENCY_INPUTS['income.bits.per_week'],
            }.items()
        },
        'unsupported': dict(UNSUPPORTED_CURRENCY_RESOURCES),
    }



def phase3_income_resolution_audit_snapshot() -> Dict[str, Any]:
    """Expose the complete current Phase 3 income-resolution boundary for audits."""
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

def resolve_currency_income_surfaces(rows: Dict[str, StatRow], manual_input_path: str | Path | None = None) -> Dict[str, StatRow]:
    tmp = dict(rows)
    publish_currency_income_surfaces(tmp, manual_input_path=manual_input_path)
    return {k: v for k, v in tmp.items() if k.startswith('derived::economy.income.')}
