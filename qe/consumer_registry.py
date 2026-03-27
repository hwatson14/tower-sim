from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from qe.contracts import to_legacy_surface_id, to_v2_surface_id

ROOT = Path(__file__).resolve().parents[1]
_OWNERSHIP_LEDGER_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-surface-ownership-ledger.yaml'
_INITIAL_SURFACE_SET_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-initial-surface-set.yaml'
_CONSUMER_BUNDLE_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-consumer-bundles.yaml'
_TRACE_MODE_RANK = {'none': 0, 'contributors': 1, 'full_trace': 2}


@dataclass(frozen=True)
class RuntimeConsumerRule:
    consumer_id: str
    source_node_ids: tuple[str, ...]
    evidence: str
    notes: str = ""


@dataclass(frozen=True)
class ConsumerBundleDefinition:
    consumer_id: str
    bundle_id: str
    family_bundle_id: str
    allowed_family_ids: tuple[str, ...]
    required_surface_ids: tuple[str, ...]
    optional_surface_ids: tuple[str, ...]
    minimum_trace_mode: str
    overlays_allowed: bool
    publish_default: bool
    debug_only: bool

    @property
    def surface_ids(self) -> tuple[str, ...]:
        return self.required_surface_ids + self.optional_surface_ids


@dataclass(frozen=True)
class ResolvedConsumerBundle:
    consumer_id: str
    bundle_id: str
    family_id: str
    surface_ids: tuple[str, ...]
    required_surface_ids: tuple[str, ...]
    optional_surface_ids: tuple[str, ...]
    minimum_trace_mode: str
    overlays_allowed: bool
    publish_default: bool
    debug_only: bool


_RUNTIME_CONSUMER_RULES: tuple[RuntimeConsumerRule, ...] = (
    RuntimeConsumerRule(
        consumer_id='runtime_consumer::wave_progression.attack_wave',
        source_node_ids=('state::tower.enemy_attack_level_skip_pct',),
        evidence='engine/wave_progression_policy.py; engine/boss_wave_engine.py',
        notes='Attack-wave advancement is deterministically suppressed by effective enemy attack level skip pct.',
    ),
    RuntimeConsumerRule(
        consumer_id='runtime_consumer::wave_progression.health_wave',
        source_node_ids=('state::tower.enemy_health_level_skip_pct',),
        evidence='engine/wave_progression_policy.py; engine/boss_wave_engine.py',
        notes='Health-wave advancement is deterministically suppressed by effective enemy health level skip pct.',
    ),
)


@lru_cache(maxsize=1)
def load_surface_ownership_ledger() -> dict[str, Any]:
    return yaml.safe_load(_OWNERSHIP_LEDGER_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def load_initial_surface_contract() -> dict[str, Any]:
    return yaml.safe_load(_INITIAL_SURFACE_SET_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def load_consumer_bundle_contract() -> dict[str, Any]:
    return yaml.safe_load(_CONSUMER_BUNDLE_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def ownership_rows_by_node() -> Mapping[str, dict[str, Any]]:
    ledger = load_surface_ownership_ledger()
    rows = [
        *(ledger.get('surface_nodes') or []),
        *(ledger.get('runtime_consumers') or []),
        *(ledger.get('runtime_domains') or []),
        *(ledger.get('analysis_nodes') or []),
        *(ledger.get('out_of_scope_nodes') or []),
    ]
    return {str(row.get('node_id')): row for row in rows}


@lru_cache(maxsize=1)
def declared_query_bundles() -> Mapping[str, frozenset[str]]:
    contract = load_initial_surface_contract()
    bundles: dict[str, frozenset[str]] = {}
    for family_data in (contract.get('families') or {}).values():
        for bundle in family_data.get('query_bundles') or ():
            bundle_id = str(bundle.get('bundle_id') or '').strip()
            if not bundle_id:
                raise ValueError('Initial surface contract contains a query bundle without bundle_id.')
            surface_ids = tuple(str(surface_id) for surface_id in (bundle.get('surface_ids') or ()))
            if bundle_id in bundles:
                raise ValueError(f'Duplicate query bundle {bundle_id!r} in initial surface contract.')
            bundles[bundle_id] = frozenset(surface_ids)
        for bundle in family_data.get('family_bundles') or ():
            bundle_id = str(bundle.get('bundle_id') or '').strip()
            if not bundle_id:
                raise ValueError('Initial surface contract contains a family bundle without bundle_id.')
            surface_ids = frozenset(
                str(s) for s in (bundle.get('required_surface_ids') or ()) + (bundle.get('optional_surface_ids') or ())
            )
            if bundle_id in bundles:
                raise ValueError(f'Duplicate family bundle {bundle_id!r} in initial surface contract.')
            bundles[bundle_id] = surface_ids
    return bundles


@lru_cache(maxsize=1)
def declared_family_surface_ids() -> Mapping[str, frozenset[str]]:
    contract = load_initial_surface_contract()
    surfaces_by_family: dict[str, set[str]] = {}
    for family_data in (contract.get('families') or {}).values():
        for entry in family_data.get('surfaces') or ():
            surface_id = str(entry.get('surface_id') or '').strip()
            for family_id in entry.get('owning_families') or ():
                surfaces_by_family.setdefault(str(family_id), set()).add(surface_id)
    return {family_id: frozenset(surface_ids) for family_id, surface_ids in surfaces_by_family.items()}


def assert_runtime_consumer_ownership_contract() -> None:
    ownership_rows = ownership_rows_by_node()
    for rule in _RUNTIME_CONSUMER_RULES:
        consumer_row = ownership_rows.get(rule.consumer_id)
        if consumer_row is None:
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} is missing from the ownership ledger.')
        if consumer_row.get('ownership_status') != 'simulator_owned' or consumer_row.get('governed_by') != 'runtime_simulation':
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must be simulator_owned and governed_by runtime_simulation.')
        if consumer_row.get('downstream_policy') != 'consume_query_owned_surfaces_only':
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must consume query-owned surfaces only.')
        consumed = tuple(consumer_row.get('consumes') or ())
        if consumed != rule.source_node_ids:
            raise ValueError(
                f'Runtime consumer {rule.consumer_id!r} ownership ledger consumes {consumed!r}, expected {rule.source_node_ids!r}.'
            )
        for source_node_id in rule.source_node_ids:
            source_row = ownership_rows.get(source_node_id)
            if source_row is None:
                raise ValueError(f'Runtime consumer source {source_node_id!r} is missing from the ownership ledger.')
            if source_row.get('ownership_status') != 'query_owned' or source_row.get('governed_by') != 'canonical_query_engine':
                raise ValueError(
                    f'Runtime consumer source {source_node_id!r} must be query_owned and governed_by canonical_query_engine.'
                )
            if source_row.get('downstream_policy') != 'consume_only_no_rederivation':
                raise ValueError(
                    f'Runtime consumer source {source_node_id!r} must forbid downstream re-derivation in the ownership ledger.'
                )


def assert_runtime_consumer_bundle_contract() -> None:
    definitions = load_consumer_bundle_definitions()
    covered_consumers = {
        definition.consumer_id
        for definition in definitions.values()
        if definition.consumer_id.startswith('runtime_consumer::') and definition.publish_default
    }
    uncovered = sorted(
        rule.consumer_id
        for rule in _RUNTIME_CONSUMER_RULES
        if rule.consumer_id not in covered_consumers
    )
    if uncovered:
        raise ValueError(
            'Runtime consumers missing publish-default query bundle coverage: '
            f'{uncovered}.'
        )
    for rule in _RUNTIME_CONSUMER_RULES:
        matching = [
            definition
            for definition in definitions.values()
            if definition.consumer_id == rule.consumer_id and definition.publish_default
        ]
        if not matching:
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} is missing a publish-default bundle contract.')
        if len(matching) != 1:
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must map to exactly one publish-default bundle contract.')
        definition = matching[0]
        if definition.required_surface_ids != rule.source_node_ids:
            raise ValueError(
                f'Runtime consumer {rule.consumer_id!r} bundle surfaces {definition.required_surface_ids!r} '
                f'do not match owned source nodes {rule.source_node_ids!r}.'
            )
        if definition.optional_surface_ids:
            raise ValueError(f'Runtime consumer {rule.consumer_id!r} must not declare optional surfaces in its publish-default bundle.')
        if definition.minimum_trace_mode != 'none':
            raise ValueError(
                f'Runtime consumer {rule.consumer_id!r} publish-default bundle must require minimum_trace_mode \"none\".'
            )


def _bundle_definition_from_payload(consumer_id: str, payload: Mapping[str, Any]) -> ConsumerBundleDefinition:
    required_surface_ids = tuple(str(surface_id) for surface_id in (payload.get('required_surface_ids') or ()))
    optional_surface_ids = tuple(str(surface_id) for surface_id in (payload.get('optional_surface_ids') or ()))
    minimum_trace_mode = str(payload.get('minimum_trace_mode') or '').strip()
    if minimum_trace_mode not in _TRACE_MODE_RANK:
        raise ValueError(f'Consumer bundle {(consumer_id, payload.get("bundle_id"))!r} declares unsupported minimum_trace_mode {minimum_trace_mode!r}.')
    definition = ConsumerBundleDefinition(
        consumer_id=consumer_id,
        bundle_id=str(payload.get('bundle_id') or '').strip(),
        family_bundle_id=str(payload.get('family_bundle_id') or '').strip(),
        allowed_family_ids=tuple(str(family_id) for family_id in (payload.get('allowed_family_ids') or ())),
        required_surface_ids=required_surface_ids,
        optional_surface_ids=optional_surface_ids,
        minimum_trace_mode=minimum_trace_mode,
        overlays_allowed=bool(payload.get('overlays_allowed')),
        publish_default=bool(payload.get('publish_default')),
        debug_only=bool(payload.get('debug_only')),
    )
    if not definition.bundle_id:
        raise ValueError(f'Consumer {consumer_id!r} declares a bundle without bundle_id.')
    if not definition.family_bundle_id:
        raise ValueError(f'Consumer bundle {definition.bundle_id!r} must declare family_bundle_id.')
    if not definition.allowed_family_ids:
        raise ValueError(f'Consumer bundle {definition.bundle_id!r} must declare allowed_family_ids.')
    if not definition.required_surface_ids:
        raise ValueError(f'Consumer bundle {definition.bundle_id!r} must declare required_surface_ids.')
    if definition.publish_default and definition.debug_only:
        raise ValueError(f'Consumer bundle {definition.bundle_id!r} cannot be publish_default and debug_only simultaneously.')
    return definition


@lru_cache(maxsize=1)
def load_consumer_bundle_definitions() -> Mapping[tuple[str, str], ConsumerBundleDefinition]:
    ownership = ownership_rows_by_node()
    query_bundles = declared_query_bundles()
    family_surfaces = declared_family_surface_ids()
    definitions: dict[tuple[str, str], ConsumerBundleDefinition] = {}
    for consumer_payload in load_consumer_bundle_contract().get('consumers') or ():
        consumer_id = str(consumer_payload.get('consumer_id') or '').strip()
        if not consumer_id:
            raise ValueError('Consumer bundle contract declares a consumer without consumer_id.')
        if consumer_id.startswith('runtime_consumer::') and consumer_id not in ownership:
            raise ValueError(f'Runtime consumer bundle declaration references undeclared consumer {consumer_id!r}.')
        for bundle_payload in consumer_payload.get('bundles') or ():
            definition = _bundle_definition_from_payload(consumer_id, bundle_payload)
            key = (definition.consumer_id, definition.bundle_id)
            if key in definitions:
                raise ValueError(f'Duplicate consumer bundle declaration for {key!r}.')
            if definition.family_bundle_id not in query_bundles:
                raise ValueError(
                    f'Consumer bundle {key!r} references undeclared family_bundle_id {definition.family_bundle_id!r}.'
                )
            declared_surfaces = query_bundles[definition.family_bundle_id]
            requested_surfaces = set(definition.surface_ids)
            missing_surfaces = sorted(requested_surfaces - declared_surfaces)
            if missing_surfaces:
                raise ValueError(f'Consumer bundle {key!r} references undeclared bundle surfaces: {missing_surfaces}.')
            for family_id in definition.allowed_family_ids:
                allowed_family_surfaces = family_surfaces.get(family_id)
                if allowed_family_surfaces is None:
                    raise ValueError(f'Consumer bundle {key!r} references undeclared family_id {family_id!r}.')
                if not requested_surfaces.issubset(allowed_family_surfaces):
                    raise ValueError(
                        f'Consumer bundle {key!r} requests surfaces outside allowed family {family_id!r}. '
                        f'Got {sorted(requested_surfaces - allowed_family_surfaces)}.'
                    )
            definitions[key] = definition
    return definitions


def resolve_consumer_bundle(
    consumer_id: str,
    bundle_id: str,
    *,
    family_id: str,
    include_optional_surface_ids: Sequence[str] = (),
    trace_mode: str | None = None,
) -> ResolvedConsumerBundle:
    definitions = load_consumer_bundle_definitions()
    key = (str(consumer_id), str(bundle_id))
    definition = definitions.get(key)
    if definition is None:
        if consumer_id not in {consumer for consumer, _ in definitions}:
            raise ValueError(f'Undeclared consumer {consumer_id!r} cannot request query bundles.')
        raise ValueError(f'Consumer {consumer_id!r} is not allowed to request bundle {bundle_id!r}.')
    if family_id not in definition.allowed_family_ids:
        raise ValueError(f'Consumer bundle {key!r} is not allowed for family_id {family_id!r}.')
    resolved_optional: list[str] = []
    unknown_optional: list[str] = []
    declared_optional = set(definition.optional_surface_ids)
    for surface_id in (str(surface_id) for surface_id in include_optional_surface_ids):
        candidates = (surface_id, to_v2_surface_id(surface_id), to_legacy_surface_id(surface_id))
        matched = next((candidate for candidate in candidates if candidate in declared_optional), None)
        if matched is None:
            unknown_optional.append(surface_id)
            continue
        resolved_optional.append(surface_id)
    optional_requested = tuple(resolved_optional)
    if unknown_optional:
        raise ValueError(f'Consumer bundle {key!r} cannot request undeclared optional surfaces {unknown_optional}.')
    if trace_mode is not None and _TRACE_MODE_RANK[str(trace_mode)] < _TRACE_MODE_RANK[definition.minimum_trace_mode]:
        raise ValueError(
            f'Consumer bundle {key!r} requires minimum trace_mode {definition.minimum_trace_mode!r}, got {trace_mode!r}.'
        )
    surface_ids = definition.required_surface_ids + optional_requested
    return ResolvedConsumerBundle(
        consumer_id=definition.consumer_id,
        bundle_id=definition.bundle_id,
        family_id=family_id,
        surface_ids=surface_ids,
        required_surface_ids=definition.required_surface_ids,
        optional_surface_ids=optional_requested,
        minimum_trace_mode=definition.minimum_trace_mode,
        overlays_allowed=definition.overlays_allowed,
        publish_default=definition.publish_default,
        debug_only=definition.debug_only,
    )


def list_runtime_consumer_rules() -> tuple[RuntimeConsumerRule, ...]:
    assert_runtime_consumer_ownership_contract()
    return _RUNTIME_CONSUMER_RULES



def impacted_runtime_consumers(dirty_node_ids: Iterable[str]) -> tuple[RuntimeConsumerRule, ...]:
    assert_runtime_consumer_ownership_contract()
    dirty = {str(node_id) for node_id in dirty_node_ids}
    return tuple(
        rule
        for rule in _RUNTIME_CONSUMER_RULES
        if dirty.intersection(rule.source_node_ids)
    )
