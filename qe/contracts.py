"""
qe/contracts.py — Preset, section layout, and surface-ID contracts. AUTHORITY.

Extracted from: models/preset_contract.py (T3), engine/query_routing.py surface-ID
functions (T3B).
Owns: load_preset_contract, load_section_layout_contract, CANONICAL_PRESET_NAMES,
PRESET_ALIASES, normalize_preset_name, require_canonical_preset_name,
sanitize_preset_name_for_canonical_output, sanitize_perk_presets_for_canonical_output,
to_v2_surface_id, to_legacy_surface_id, pack_v2_naming_remap_rows.
"""
from __future__ import annotations

import csv
import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
_PRESET_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'preset_contract.yaml'
_SECTION_LAYOUT_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'section_layout_contract.yaml'
_YAML_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


@lru_cache(maxsize=None)
def load_yaml_contract(path: str) -> dict[str, Any]:
    contract_path = Path(path)
    with contract_path.open('r', encoding='utf-8') as handle:
        raw = yaml.load(handle, Loader=_YAML_LOADER) or {}
    if not isinstance(raw, dict):
        raise ValueError(f'Expected YAML contract mapping at {contract_path}, got {type(raw).__name__}.')
    return raw


@lru_cache(maxsize=1)
def load_preset_contract() -> dict[str, Any]:
    raw = load_yaml_contract(str(_PRESET_CONTRACT_PATH))
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
    raw = load_yaml_contract(str(_SECTION_LAYOUT_CONTRACT_PATH))
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


# ---------------------------------------------------------------------------
# Surface-ID translation — extracted from engine/query_routing.py (T3B)
# Authority: qe.contracts. engine/query_routing.py retains its own copy for
# compiler callers (routing-table scope); qe/ internals use this module only.
# ---------------------------------------------------------------------------

_KB_CONTRACTS = ROOT / 'kb' / 'global-rules' / 'contracts'
NAMING_CONTRACT_PACK_V2_REMAP_PATH = _KB_CONTRACTS / 'naming-contract-pack-v2-remap.csv'

_PLACEHOLDER_RE = re.compile(r'<[^>]+>')
_SURFACE_ID_TOKEN_RE = re.compile(
    r'(?P<surface>(?:canonical_stat|mechanic_param|runtime_mechanic_param|environment_param|account_flag|account_context|meta_progression_param|cosmetic_bonus|capability|raw)::[A-Za-z0-9_.*<>-]+(?:\.[A-Za-z0-9_.*<>-]+)*)'
)
_LEGACY_SURFACE_TOKEN_MARKERS: tuple[str, ...] = (
    'canonical_stat::',
    'mechanic_param::',
    'runtime_mechanic_param::',
    'environment_param::',
    'account_flag::',
    'account_context::',
    'meta_progression_param::',
    'cosmetic_bonus::',
    'capability::',
    'raw::',
)


def _surface_id(object_type: str, destination_id: str) -> str:
    return f'{object_type}::{destination_id}'


def compat_surface_from_legacy_canonical(destination_id: str) -> str:
    """Compatibility-only bridge from legacy canonical_stat ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('canonical_stat', destination_id))


def compat_surface_from_legacy_mechanic(destination_id: str) -> str:
    """Compatibility-only bridge from legacy mechanic_param ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('mechanic_param', destination_id))


def compat_surface_from_legacy_runtime(destination_id: str) -> str:
    """Compatibility-only bridge from legacy runtime_mechanic_param ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('runtime_mechanic_param', destination_id))


def compat_surface_from_legacy_flag(destination_id: str) -> str:
    """Compatibility-only bridge from legacy account_flag ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('account_flag', destination_id))


def compat_surface_from_legacy_context(destination_id: str) -> str:
    """Compatibility-only bridge from legacy account_context ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('account_context', destination_id))


def compat_surface_from_legacy_capability(destination_id: str) -> str:
    """Compatibility-only bridge from legacy capability ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('capability', destination_id))


def compat_surface_from_legacy_cosmetic(destination_id: str) -> str:
    """Compatibility-only bridge from legacy cosmetic_bonus ids into the active contract."""
    return normalize_surface_id_to_contract(_surface_id('cosmetic_bonus', destination_id))


def _pattern_to_regex(surface_id_pattern: str) -> re.Pattern[str]:
    escaped = re.escape(surface_id_pattern)
    return re.compile('^' + _PLACEHOLDER_RE.sub(r'([^:]+)', escaped) + '$')


def _pattern_to_template(surface_id_pattern: str) -> str:
    return _PLACEHOLDER_RE.sub('{}', surface_id_pattern)


@lru_cache(maxsize=1)
def pack_v2_naming_remap_rows() -> tuple[dict[str, str], ...]:
    payload = NAMING_CONTRACT_PACK_V2_REMAP_PATH.read_text(encoding='utf-8')
    return tuple(csv.DictReader(io.StringIO(payload)))


@lru_cache(maxsize=1)
def pack_v2_naming_remap_surface_maps() -> tuple[dict[str, str], dict[str, str], tuple[tuple[re.Pattern[str], str], ...], tuple[tuple[re.Pattern[str], str], ...]]:
    legacy_to_v2: dict[str, str] = {}
    v2_to_legacy: dict[str, str] = {}
    legacy_patterns: list[tuple[re.Pattern[str], str]] = []
    v2_patterns: list[tuple[re.Pattern[str], str]] = []
    for row in pack_v2_naming_remap_rows():
        row_type = str(row.get('row_type') or '').strip()
        new_bucket = str(row.get('new_bucket') or '').strip()
        new_id = str(row.get('new_id') or '').strip()
        if not new_id or new_bucket in {'hold', 'state/context', 'state/context/derived'}:
            continue
        old_surface_id = _surface_id(str(row['old_bucket']).strip(), str(row['old_id']).strip())
        new_surface_id = new_id
        if row_type in {'concrete', 'gap'}:
            legacy_to_v2[old_surface_id] = new_surface_id
            if row_type == 'concrete':
                v2_to_legacy.setdefault(new_surface_id, old_surface_id)
            continue
        if row_type == 'pattern':
            legacy_patterns.append((_pattern_to_regex(old_surface_id), _pattern_to_template(new_surface_id)))
            v2_patterns.append((_pattern_to_regex(new_surface_id), _pattern_to_template(old_surface_id)))
    return legacy_to_v2, v2_to_legacy, tuple(legacy_patterns), tuple(v2_patterns)


@lru_cache(maxsize=8192)
def to_v2_surface_id(surface_id: str) -> str:
    legacy_to_v2, _, legacy_patterns, _ = pack_v2_naming_remap_surface_maps()
    exact = legacy_to_v2.get(surface_id)
    if exact is not None:
        return exact
    for pattern, template in legacy_patterns:
        match = pattern.match(surface_id)
        if match is not None:
            return template.format(*match.groups())
    return surface_id


@lru_cache(maxsize=8192)
def to_legacy_surface_id(surface_id: str) -> str:
    _, v2_to_legacy, _, v2_patterns = pack_v2_naming_remap_surface_maps()
    exact = v2_to_legacy.get(surface_id)
    if exact is not None:
        return exact
    for pattern, template in v2_patterns:
        match = pattern.match(surface_id)
        if match is not None:
            return template.format(*match.groups())
    return surface_id


def to_v2_destination(destination_object_type: str, destination_id: str) -> tuple[str, str]:
    published = to_v2_surface_id(_surface_id(destination_object_type, destination_id))
    if '::' not in published:
        return destination_object_type, destination_id
    return tuple(published.split('::', 1))  # type: ignore[return-value]


def to_legacy_destination(destination_object_type: str, destination_id: str) -> tuple[str, str]:
    legacy = to_legacy_surface_id(_surface_id(destination_object_type, destination_id))
    if '::' not in legacy:
        return destination_object_type, destination_id
    return tuple(legacy.split('::', 1))  # type: ignore[return-value]


_COMPATIBILITY_LEGACY_SURFACE_FALLBACKS: dict[str, str] = {
    'canonical_stat::free_upgrade_shared_add_pct': 'state::tower.free_upgrade_shared_add_pct',
}

COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES: tuple[str, ...] = (
    'mechanic_param::',
    'runtime_mechanic_param::',
    'account_flag::',
    'capability::',
    'raw::',
)


@lru_cache(maxsize=8192)
def normalize_surface_id_to_contract(surface_id: str) -> str:
    """Normalize a possibly-legacy surface id to the active naming contract."""
    normalized = to_v2_surface_id(surface_id)
    if normalized != surface_id:
        return normalized
    if '::' not in surface_id:
        return surface_id

    bucket, destination_id = surface_id.split('::', 1)
    explicit = _COMPATIBILITY_LEGACY_SURFACE_FALLBACKS.get(surface_id)
    if explicit is not None:
        return explicit

    if bucket == 'environment_param':
        return f'context::{destination_id}'
    if bucket == 'account_flag':
        return f'state::{destination_id}'
    if bucket == 'account_context':
        return f'state::meta.{destination_id}'
    if bucket == 'cosmetic_bonus':
        return f'state::meta.{destination_id}'
    if bucket == 'meta_progression_param':
        return f'state::{destination_id}'
    if bucket == 'capability':
        if destination_id.startswith('capability.'):
            return f'state::{destination_id}'
        return f'state::capability.{destination_id}'
    if bucket in {'mechanic_param', 'runtime_mechanic_param'}:
        if destination_id.startswith(('enemy.', 'boss.', 'bc.', 'tier.', 'heat.', 'tournament.')):
            return f'context::{destination_id}'
        return f'state::{destination_id}'
    if bucket == 'canonical_stat':
        if destination_id.startswith(('tower_', 'wall_', 'economy.', 'meta.', 'uw.', 'bot.', 'guardian.', 'module.', 'cards.', 'perk.')):
            return f'state::{destination_id.replace("_", ".")}'
        return f'state::{destination_id}'
    return surface_id


@lru_cache(maxsize=8192)
def normalize_surface_token_text(value: str) -> str:
    """Rewrite embedded legacy surface-id tokens to the active naming contract."""

    def _replace(match: re.Match[str]) -> str:
        return normalize_surface_id_to_contract(match.group('surface'))

    return _SURFACE_ID_TOKEN_RE.sub(_replace, value)


@lru_cache(maxsize=16384)
def _normalize_contract_string(value: str) -> str:
    if '::' not in value:
        return value
    if not any(marker in value for marker in _LEGACY_SURFACE_TOKEN_MARKERS):
        return value
    return normalize_surface_token_text(value)


def _normalize_contract_payload_inner(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        normalized = _normalize_contract_string(value)
        return normalized, normalized != value
    if not isinstance(value, (dict, list, tuple)):
        return value, False
    if isinstance(value, dict):
        normalized: dict[Any, Any] | None = None
        for index, (key, item) in enumerate(value.items()):
            normalized_key = _normalize_contract_string(key) if isinstance(key, str) else key
            normalized_item, item_changed = _normalize_contract_payload_inner(item)
            if normalized is None and (item_changed or normalized_key != key):
                normalized = dict(list(value.items())[:index])
            if normalized is not None:
                normalized[normalized_key] = normalized_item
        return (value, False) if normalized is None else (normalized, True)
    if isinstance(value, list):
        normalized_items: list[Any] | None = None
        for index, item in enumerate(value):
            normalized_item, item_changed = _normalize_contract_payload_inner(item)
            if normalized_items is None and item_changed:
                normalized_items = list(value[:index])
            if normalized_items is not None:
                normalized_items.append(normalized_item)
        return (value, False) if normalized_items is None else (normalized_items, True)
    if isinstance(value, tuple):
        return [_normalize_contract_payload_inner(item)[0] for item in value], True
    return value, False


def normalize_contract_payload(value: Any) -> Any:
    """Recursively normalize generated payloads to the active naming contract."""
    return _normalize_contract_payload_inner(value)[0]


def relpath_str(path_like) -> str:
    p = Path(path_like)
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        try:
            return str(p.relative_to(ROOT))
        except Exception:
            return str(p)


def json_sanitize(obj):
    if isinstance(obj, Path):
        return relpath_str(obj)
    if isinstance(obj, dict):
        return {k: json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, str) and (obj.startswith('/') or obj.startswith('\\')):
        try:
            return relpath_str(obj)
        except Exception:
            return obj
    return obj


def contract_json_payload(obj):
    return normalize_contract_payload(json_sanitize(obj))
