from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
_PRESET_CONTRACT_PATH = ROOT / 'registry' / 'preset_contract.yaml'
_SECTION_LAYOUT_CONTRACT_PATH = ROOT / 'registry' / 'section_layout_contract.yaml'


@lru_cache(maxsize=1)
def load_preset_contract() -> dict[str, Any]:
    with _PRESET_CONTRACT_PATH.open('r', encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}
    canonical_presets = tuple(str(name) for name in raw.get('canonical_presets') or ())
    aliases = {str(key): str(value) for key, value in (raw.get('aliases') or {}).items()}
    if not canonical_presets:
        raise ValueError('Preset contract missing canonical_presets.')
    for alias_target in aliases.values():
        if alias_target not in canonical_presets:
            raise ValueError(f'Preset contract alias targets unknown canonical preset {alias_target!r}.')
    return {
        'canonical_presets': canonical_presets,
        'aliases': aliases,
        'alias_normalization_policy': str(raw.get('alias_normalization_policy') or ''),
        'post_ingestion_policy': dict(raw.get('post_ingestion_policy') or {}),
    }


@lru_cache(maxsize=1)
def load_section_layout_contract() -> dict[str, Any]:
    with _SECTION_LAYOUT_CONTRACT_PATH.open('r', encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}
    sections = raw.get('sections') or {}
    if not sections:
        raise ValueError('Section layout contract missing sections.')
    return sections


CANONICAL_PRESET_NAMES: tuple[str, ...] = load_preset_contract()['canonical_presets']
PRESET_ALIASES: dict[str, str] = load_preset_contract()['aliases']


def is_canonical_preset_name(value: str | None) -> bool:
    return isinstance(value, str) and value in CANONICAL_PRESET_NAMES


def normalize_preset_name(value: str | None, *, allow_aliases: bool) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw in CANONICAL_PRESET_NAMES:
        return raw
    if allow_aliases:
        return PRESET_ALIASES.get(raw)
    return None


def require_canonical_preset_name(value: str | None, *, field_name: str) -> str:
    normalized = normalize_preset_name(value, allow_aliases=False)
    if normalized is None:
        raise ValueError(f'{field_name} must use a canonical preset name, got {value!r}.')
    return normalized



def is_transient_preset_namespace(value: str | None, *, namespace_class: str | None = None) -> bool:
    normalized_class = str(namespace_class or '').strip().lower()
    if normalized_class == 'transient':
        return True
    return value is not None and not is_canonical_preset_name(value)


def sanitize_preset_name_for_canonical_output(
    value: str | None,
    *,
    namespace_class: str | None = None,
    fallback_preset_name: str | None = None,
) -> str | None:
    if value is None:
        return None
    if is_transient_preset_namespace(value, namespace_class=namespace_class):
        fallback = normalize_preset_name(fallback_preset_name, allow_aliases=False)
        if fallback is not None:
            return fallback
    return normalize_preset_name(value, allow_aliases=False) or value


def sanitize_perk_presets_for_canonical_output(
    perk_presets: dict[str, Any],
    *,
    namespace_class: str | None = None,
    fallback_preset_name: str | None = None,
    active_preset_name: str | None = None,
) -> dict[str, Any]:
    if not isinstance(perk_presets, dict):
        return {}
    out: dict[str, Any] = {}
    for preset_name, payload in perk_presets.items():
        sanitized_name = sanitize_preset_name_for_canonical_output(
            str(preset_name),
            namespace_class=namespace_class,
            fallback_preset_name=fallback_preset_name,
        )
        if sanitized_name is None:
            continue
        if sanitized_name in out and sanitized_name != preset_name and preset_name != active_preset_name:
            continue
        out[sanitized_name] = payload
    return out
