from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml

RUNTIME_INPUT_CONTRACT_PATH = Path(__file__).resolve().parents[1] / 'kb' / 'global-rules' / 'contracts' / 'scenario-runtime-inputs.yaml'


@lru_cache(maxsize=1)
def _load_runtime_input_contract() -> Dict[str, Dict[str, Any]]:
    raw = yaml.safe_load(RUNTIME_INPUT_CONTRACT_PATH.read_text()) or {}
    fields = raw.get('fields') or {}
    if not isinstance(fields, dict) or not fields:
        raise ValueError('Scenario runtime input contract must define non-empty fields.')
    out: Dict[str, Dict[str, Any]] = {}
    for field_name, spec in fields.items():
        if not isinstance(spec, dict):
            raise ValueError(f'Scenario runtime input field {field_name} must be a mapping.')
        aliases = spec.get('aliases') or []
        if not aliases:
            raise ValueError(f'Scenario runtime input field {field_name} must declare aliases.')
        out[field_name] = {
            'aliases': tuple(str(alias) for alias in aliases),
            'min': spec.get('min'),
            'min_exclusive': spec.get('min_exclusive'),
            'max': spec.get('max'),
            'max_exclusive': spec.get('max_exclusive'),
        }
    return out


@dataclass(frozen=True)
class ScenarioRuntimeInputs:
    orb_boss_hit_pct: Optional[float] = None
    orb_boss_hits_per_second: Optional[float] = None
    electron_hits_per_second: Optional[float] = None
    boss_contact_time_seconds: Optional[float] = None
    boss_hit_interval_seconds: Optional[float] = None
    effective_damage_reduction_pct: Optional[float] = None
    incoming_damage_multiplier: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> 'ScenarioRuntimeInputs':
        contract = _load_runtime_input_contract()
        values: Dict[str, Optional[float]] = {}
        for field_name, spec in contract.items():
            values[field_name] = _first_from_aliases(raw=raw, field_name=field_name, aliases=spec['aliases'], spec=spec)
        return cls(**values)

    def to_debug_dict(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for key in _load_runtime_input_contract().keys():
            value = getattr(self, key)
            if value is not None:
                out[key] = float(value)
        return out


def _first_from_aliases(*, raw: Mapping[str, Any], field_name: str, aliases: tuple[str, ...], spec: Mapping[str, Any]) -> Optional[float]:
    for key in aliases:
        if key in raw and raw[key] is not None:
            return _coerce_float(field_name=field_name, source_key=key, value=raw[key], spec=spec)
    return None


def _coerce_float(*, field_name: str, source_key: str, value: Any, spec: Mapping[str, Any]) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Scenario runtime input {source_key} must be numeric.') from exc
    if not isfinite(out):
        raise ValueError(f'Scenario runtime input {source_key} must be finite.')
    min_value = spec.get('min')
    if min_value is not None and out < float(min_value):
        raise ValueError(f'Scenario runtime input {source_key} must be >= {float(min_value)}.')
    min_exclusive = spec.get('min_exclusive')
    if min_exclusive is not None and out <= float(min_exclusive):
        raise ValueError(f'Scenario runtime input {source_key} must be > {float(min_exclusive)}.')
    max_value = spec.get('max')
    if max_value is not None and out > float(max_value):
        raise ValueError(f'Scenario runtime input {source_key} must be <= {float(max_value)}.')
    max_exclusive = spec.get('max_exclusive')
    if max_exclusive is not None and out >= float(max_exclusive):
        raise ValueError(f'Scenario runtime input {source_key} must be < {float(max_exclusive)}.')
    return out
