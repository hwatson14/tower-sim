from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

from qe.contracts import (
    load_yaml_contract,
    to_legacy_destination,
    to_legacy_surface_id,
    to_v2_destination,
    to_v2_surface_id,
)
from qe.models import StatInput  # T3B: authority transferred to qe.models

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
KB_CONTRACTS = KB / 'global-rules' / 'contracts'
KB_TABLES = KB / 'global-rules' / 'tables'
KB_MAPPINGS_PATH = KB_CONTRACTS / 'contributor-mappings-full.yaml'
KB_CANONICAL_STATS_PATH = KB_CONTRACTS / 'canonical-stats.yaml'
KB_ALIASES_PATH = KB_CONTRACTS / 'name-aliases.yaml'
RELIC_REGISTRY_PATH = KB_TABLES / 'relic-input-registry.csv'

CARD_EFFECT_REGISTRY_PATH = KB / 'cards' / 'tables' / 'card-effect-registry.csv'
THEME_SONG_REGISTRY_PATH = KB_TABLES / 'theme-song-input-registry.csv'
LAB_APPLICATION_REGISTRY_PATH = KB / 'labs' / 'tables' / 'lab-application-registry.csv'

COMPILER_ROUTING_POLICY_PATH = KB_CONTRACTS / 'compiler-routing-policy.yaml'
QUERY_ROUTING_MAPPINGS_PATH = KB_CONTRACTS / 'query-routing-mappings.yaml'


def _load_yaml(path: Path) -> dict:
    return load_yaml_contract(str(path))


@lru_cache(maxsize=1)
def _load_compiler_routing_policy() -> dict:
    raw = _load_yaml(COMPILER_ROUTING_POLICY_PATH)

    def _nested_tuple_map(section: str) -> dict:
        out = {}
        for outer_key, inner in (raw.get(section) or {}).items():
            inner = inner or {}
            for inner_key, destination in inner.items():
                out[(outer_key, inner_key)] = tuple(destination)
        return out

    return {
        'parser_drop_rows': set(raw.get('parser_drop_rows') or []),
        'account_metadata_rows': set(raw.get('account_metadata_rows') or []),
        'capability_policy_rows': set(raw.get('capability_policy_rows') or []),
        'governed_numeric_rows': set(raw.get('governed_numeric_rows') or []),
        'uw_mechanic_destination_overrides': _nested_tuple_map('uw_mechanic_destination_overrides'),
        'uw_contributor_overrides': {
            (outer_key, inner_key): value
            for outer_key, inner in (raw.get('uw_contributor_overrides') or {}).items()
            for inner_key, value in (inner or {}).items()
        },
        'guardian_destination_overrides': _nested_tuple_map('guardian_destination_overrides'),
        'vault_boolean_flags': {k: tuple(v) for k, v in (raw.get('vault_boolean_flags') or {}).items()},
        'relic_alias_overrides': {k: tuple(v) for k, v in (raw.get('relic_alias_overrides') or {}).items()},
        'vault_numeric_overrides': {k: tuple(v) for k, v in (raw.get('vault_numeric_overrides') or {}).items()},
    }


def compiler_routing_policy() -> dict:
    return _load_compiler_routing_policy()


def _to_destination_tuple_map(raw: dict | None) -> Dict[str, Tuple[str, str]]:
    return {key: tuple(value) for key, value in (raw or {}).items()}


def _to_nested_destination_tuple_map(rows: list[dict] | None) -> Dict[Tuple[str, str], Tuple[str, str]]:
    out: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for row in rows or []:
        key = (str(row['destination_namespace']).strip(), str(row['destination_field']).strip())
        out[key] = (str(row['destination_object_type']).strip(), str(row['destination_id']).strip())
    return out


def _to_nested_contributor_key_map(rows: list[dict] | None) -> Dict[Tuple[str, str], str]:
    out: Dict[Tuple[str, str], str] = {}
    for row in rows or []:
        key = (str(row['uw_name']).strip(), str(row['track_name']).strip())
        out[key] = str(row['contributor_id']).strip()
    return out


@lru_cache(maxsize=1)
def _load_query_routing_mappings() -> dict:
    raw = _load_yaml(QUERY_ROUTING_MAPPINGS_PATH)
    return {
        'uw_lab_direct_destination': _to_destination_tuple_map(raw.get('uw_lab_direct_destination')),
        'workshop_ids_to_contributor': dict(raw.get('workshop_ids_to_contributor') or {}),
        'lab_ids_to_contributor': dict(raw.get('lab_ids_to_contributor') or {}),
        'direct_workshop_table_columns': dict(raw.get('direct_workshop_table_columns') or {}),
        'card_target_surface_to_canonical': dict(raw.get('card_target_surface_to_canonical') or {}),
        'card_target_surface_to_destination': _to_destination_tuple_map(raw.get('card_target_surface_to_destination')),
        'lab_application_target_to_destination': _to_nested_destination_tuple_map(raw.get('lab_application_target_to_destination')),
        'card_name_fallback_destination': _to_destination_tuple_map(raw.get('card_name_fallback_destination')),
        'module_substat_name_to_destination': _to_destination_tuple_map(raw.get('module_substat_name_to_destination')),
        'enhancement_alias_overrides': dict(raw.get('enhancement_alias_overrides') or {}),
        'relic_contributor_overrides': dict(raw.get('relic_contributor_overrides') or {}),
        'perk_target_destination_overrides': _to_destination_tuple_map(raw.get('perk_target_destination_overrides')),
        'uw_contributor_map': _to_nested_contributor_key_map(raw.get('uw_contributor_map')),
    }


def query_routing_mappings() -> dict:
    return _load_query_routing_mappings()


def routing_class_for_lab_name(name: str) -> str | None:
    policy = compiler_routing_policy()
    if name in policy['parser_drop_rows']:
        return 'parser_drop'
    if name in policy['account_metadata_rows']:
        return 'account_metadata'
    if name in policy['capability_policy_rows']:
        return 'capability_policy'
    if name in policy['governed_numeric_rows']:
        return 'governed_numeric'
    return None


@lru_cache(maxsize=1)
def load_card_effect_targets() -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    with CARD_EFFECT_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            if row.get('layer') != 'base_card':
                continue
            target = row.get('target_surface', '').strip()
            destination = CARD_TARGET_SURFACE_TO_DESTINATION.get(target)
            if destination:
                out[row['card_id']] = destination
    return out


@lru_cache(maxsize=1)
def load_lab_application_registry() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    with LAB_APPLICATION_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            name = str(row['lab_primary_name']).strip()
            out[name] = row
            out[slug_text(name)] = row
    return out


@lru_cache(maxsize=1)
def load_theme_song_registry() -> Dict[str, Tuple[str, str, str]]:
    out: Dict[str, Tuple[str, str, str]] = {}
    if not THEME_SONG_REGISTRY_PATH.exists():
        return out
    with THEME_SONG_REGISTRY_PATH.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = (row.get('contributor_id') or '').strip()
            if cid:
                out[cid] = (
                    (row.get('destination_object_type') or '').strip(),
                    (row.get('destination_id') or '').strip(),
                    (row.get('resolver_id') or '').strip(),
                )
    return out

# Source-backed workshop and lab formula callables: loaded from KB table.
# Source: kb/global-rules/tables/workshop-formula-params-canonical.csv
from qe.kb_surfaces import WORKSHOP_FORMULA_VALUES, LAB_FORMULA_VALUES  # noqa: E402

PARSER_DROP_ROWS = compiler_routing_policy()['parser_drop_rows']
ACCOUNT_METADATA_ROWS = compiler_routing_policy()['account_metadata_rows']
CAPABILITY_POLICY_ROWS = compiler_routing_policy()['capability_policy_rows']
GOVERNED_NUMERIC_ROWS = compiler_routing_policy()['governed_numeric_rows']
UW_MECHANIC_DESTINATION_OVERRIDES = compiler_routing_policy()['uw_mechanic_destination_overrides']
UW_CONTRIBUTOR_OVERRIDES = compiler_routing_policy()['uw_contributor_overrides']
GUARDIAN_DESTINATION_OVERRIDES = compiler_routing_policy()['guardian_destination_overrides']
VAULT_BOOLEAN_FLAGS = compiler_routing_policy()['vault_boolean_flags']
RELIC_ALIAS_OVERRIDES = compiler_routing_policy()['relic_alias_overrides']
VAULT_NUMERIC_OVERRIDES = compiler_routing_policy()['vault_numeric_overrides']

_QUERY_ROUTING_MAPPINGS = query_routing_mappings()

# UW lab destinations for labs not yet in LAB_APPLICATION_TARGET_TO_DESTINATION
_UW_LAB_DIRECT_DESTINATION: Dict[str, Tuple[str, str]] = _QUERY_ROUTING_MAPPINGS['uw_lab_direct_destination']
WORKSHOP_IDS_TO_CONTRIBUTOR = _QUERY_ROUTING_MAPPINGS['workshop_ids_to_contributor']
LAB_IDS_TO_CONTRIBUTOR = _QUERY_ROUTING_MAPPINGS['lab_ids_to_contributor']
DIRECT_WORKSHOP_TABLE_COLUMNS = _QUERY_ROUTING_MAPPINGS['direct_workshop_table_columns']
CARD_TARGET_SURFACE_TO_CANONICAL = _QUERY_ROUTING_MAPPINGS['card_target_surface_to_canonical']
CARD_TARGET_SURFACE_TO_DESTINATION = _QUERY_ROUTING_MAPPINGS['card_target_surface_to_destination']
LAB_APPLICATION_TARGET_TO_DESTINATION = _QUERY_ROUTING_MAPPINGS['lab_application_target_to_destination']
CARD_NAME_FALLBACK_DESTINATION = _QUERY_ROUTING_MAPPINGS['card_name_fallback_destination']
MODULE_SUBSTAT_NAME_TO_DESTINATION = _QUERY_ROUTING_MAPPINGS['module_substat_name_to_destination']
ENHANCEMENT_ALIAS_OVERRIDES = _QUERY_ROUTING_MAPPINGS['enhancement_alias_overrides']
RELIC_CONTRIBUTOR_OVERRIDES = _QUERY_ROUTING_MAPPINGS['relic_contributor_overrides']
PERK_TARGET_DESTINATION_OVERRIDES = _QUERY_ROUTING_MAPPINGS['perk_target_destination_overrides']

@lru_cache(maxsize=8192)
def slug_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace('&', ' and ')
    text = text.replace('%', ' pct ')
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(' / ', ' ')
    text = text.replace('/', ' ')
    text = text.replace('-', ' ')
    text = text.replace('_', ' ')
    text = text.replace('+', ' ')
    text = re.sub(r'[^a-z0-9 ]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


@lru_cache(maxsize=1)
def compiler_routing_indexes() -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Tuple[str, str]], Dict[str, str], Dict[Tuple[str, str], str]]:
    mapping_data = _load_yaml(KB_MAPPINGS_PATH)
    mapping_index: Dict[str, Dict[str, str]] = {}
    family_slug_index: Dict[Tuple[str, str], str] = {}
    for family, rows in mapping_data['source_families'].items():
        for row in rows:
            mapping_index[row['contributor_id']] = {
                'source_family': family,
                'destination_object_type': row['destination_object_type'],
                'destination_id': row['destination_id'],
                'resolver_id': row['resolver'],
            }
            parts = row['contributor_id'].split('__')
            if len(parts) >= 4:
                family_slug_index[(family, slug_text(parts[2].replace('_', ' ')))] = row['contributor_id']
                if family == 'module' and len(parts) >= 4:
                    family_slug_index[(family, slug_text(parts[1].replace('_', ' ') + ' ' + parts[2].replace('_', ' ')))] = row['contributor_id']

    stats = _load_yaml(KB_CANONICAL_STATS_PATH)
    canonical_stats: Dict[str, Dict[str, str]] = {}
    for domain, entries in stats['domains'].items():
        for entry in entries:
            canonical_stats[entry['id']] = {
                'domain': domain,
                'unit': entry['unit'],
                'resolver': entry['resolver'],
            }

    alias_data = _load_yaml(KB_ALIASES_PATH)
    alias_index: Dict[str, Tuple[str, str]] = {}
    for row in alias_data['alias_groups'].get('object_aliases', []):
        alias_index[slug_text(row['alias'])] = (row['resolves_to_type'], row['resolves_to_id'])

    relic_index: Dict[str, str] = {}
    with RELIC_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            contributor_id = row['contributor_id']
            parts = contributor_id.split('__')
            if len(parts) >= 4:
                key = slug_text(parts[2].replace('_', ' '))
                relic_index[key] = contributor_id
    return mapping_index, canonical_stats, alias_index, relic_index, family_slug_index


def uw_contributor_id(uw_name: str, track_name: str) -> str | None:
    mapping = query_routing_mappings()['uw_contributor_map']
    return mapping.get((uw_name, track_name))

def mapping_lookup_for_family_name(family_slug_index: Dict[Tuple[str, str], str], family: str, name: str) -> Optional[str]:
    slug = slug_text(name)
    return family_slug_index.get((family, slug))



def _set_row_field(row: StatInput, field_name: str, value) -> None:
    object.__setattr__(row, field_name, value)


def bind_kb_fields(row: StatInput, contributor_id: str, mapping_index: Dict[str, Dict[str, str]], canonical_stats: Dict[str, Dict[str, str]]) -> None:
    if contributor_id not in mapping_index:
        raise KeyError(f'Contributor id {contributor_id!r} not found in KB mapping index.')
    info = mapping_index[contributor_id]
    destination_id = info['destination_id']
    if info['destination_object_type'] == 'canonical_stat' and destination_id not in canonical_stats:
        raise KeyError(f'Destination id {destination_id!r} missing from canonical stats registry.')
    _set_row_field(row, 'contributor_id', contributor_id)
    _set_row_field(row, 'destination_object_type', info['destination_object_type'])
    _set_row_field(row, 'destination_id', destination_id)
    _set_row_field(row, 'resolver_id', info['resolver_id'])
    _set_row_field(row, 'kb_mapped', True)


def bind_alias_destination(row: StatInput, alias_text: str, alias_index: Dict[str, Tuple[str, str]], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
    slug = slug_text(alias_text)
    if slug in ENHANCEMENT_ALIAS_OVERRIDES:
        _set_row_field(row, 'destination_object_type', 'canonical_stat')
        _set_row_field(row, 'destination_id', ENHANCEMENT_ALIAS_OVERRIDES[slug])
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
        _set_row_field(row, 'notes', note)
        return
    match = alias_index.get(slug)
    if match is None:
        _set_row_field(row, 'notes', note + '_alias_missing')
        return
    _set_row_field(row, 'destination_object_type', match[0])
    _set_row_field(row, 'destination_id', match[1])
    if row.destination_object_type == 'canonical_stat':
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
    _set_row_field(row, 'notes', note)


def bind_destination(row: StatInput, destination: Tuple[str, str], canonical_stats: Dict[str, Dict[str, str]], *, note: str) -> None:
    _set_row_field(row, 'destination_object_type', destination[0])
    _set_row_field(row, 'destination_id', destination[1])
    if row.destination_object_type == 'canonical_stat':
        _set_row_field(row, 'resolver_id', canonical_stats.get(row.destination_id, {}).get('resolver'))
        _set_row_field(row, 'kb_mapped', row.destination_id in canonical_stats)
    elif row.destination_object_type in {'runtime_mechanic_param', 'mechanic_param', 'meta_progression_param', 'environment_param'}:
        _set_row_field(row, 'resolver_id', 'standard_scalar_param')
        _set_row_field(row, 'kb_mapped', True)
    elif row.destination_object_type in {'capability', 'account_flag'}:
        _set_row_field(row, 'resolver_id', 'capability_passthrough')
        _set_row_field(row, 'kb_mapped', True)
    _set_row_field(row, 'notes', note)



def bind_perk_effect_destination(row: StatInput, target_stat_id: str, canonical_stats: Dict[str, Dict[str, str]], alias_index: Dict[str, Tuple[str, str]]) -> None:
    destination = PERK_TARGET_DESTINATION_OVERRIDES.get(target_stat_id)
    if destination is not None:
        bind_destination(row, destination, canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    if target_stat_id in canonical_stats:
        bind_destination(row, ('canonical_stat', target_stat_id), canonical_stats, note=f'kb_perk_effect_routed:{target_stat_id}')
        return
    bind_alias_destination(row, target_stat_id.replace('_', ' '), alias_index, canonical_stats, note='kb_alias_routed_perk_target')


__all__ = [
    'compiler_routing_policy',
    'compiler_routing_indexes',
    'slug_text',
    'mapping_lookup_for_family_name',
    'bind_kb_fields',
    'bind_alias_destination',
    'bind_destination',
    'bind_perk_effect_destination',
    'uw_contributor_id',
    'routing_class_for_lab_name',
    'PARSER_DROP_ROWS',
    'ACCOUNT_METADATA_ROWS',
    'CAPABILITY_POLICY_ROWS',
    'GOVERNED_NUMERIC_ROWS',
    'UW_MECHANIC_DESTINATION_OVERRIDES',
    'UW_CONTRIBUTOR_OVERRIDES',
    'GUARDIAN_DESTINATION_OVERRIDES',
    'VAULT_BOOLEAN_FLAGS',
    'RELIC_ALIAS_OVERRIDES',
    'VAULT_NUMERIC_OVERRIDES',
    '_UW_LAB_DIRECT_DESTINATION',
    'WORKSHOP_IDS_TO_CONTRIBUTOR',
    'LAB_IDS_TO_CONTRIBUTOR',
    'CARD_TARGET_SURFACE_TO_DESTINATION',
    'LAB_APPLICATION_TARGET_TO_DESTINATION',
    'CARD_NAME_FALLBACK_DESTINATION',
    'MODULE_SUBSTAT_NAME_TO_DESTINATION',
    'ENHANCEMENT_ALIAS_OVERRIDES',
    'RELIC_CONTRIBUTOR_OVERRIDES',
    'PERK_TARGET_DESTINATION_OVERRIDES',
    'to_v2_surface_id',
    'to_legacy_surface_id',
    'to_v2_destination',
    'to_legacy_destination',
]
