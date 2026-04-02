from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from math import prod
from pathlib import Path
from types import MappingProxyType
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import yaml

from qe.dependency_registry import DependencyRegistry
from qe.materializer import (
    BaselineContributorRow,
    FamilyBaselineContributorMap,
    FamilyBaselineMaterializer,
    contributor_row_sort_key,
    load_surface_metadata_by_id,
)
from qe.contracts import to_legacy_surface_id, to_v2_surface_id
from qe.models import BoundStatInputs, StatInput

ROOT = Path(__file__).resolve().parents[1]
_OVERLAY_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'overlay-delta-schema.yaml'
_QUERY_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-api-contract.yaml'
_FAMILY_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-scenario-families.yaml'

_MUTATING_STAGES = {'additive_pre_cap', 'scenario_adjustment'}
_ALLOWED_TRACE_MODES = frozenset({'none', 'contributors', 'full_trace'})

# Hard caps applied after additive×multiplicative composition, matching legacy pct_capped_scalar_stat resolver.
# Keys are the surface IDs as they appear in FamilyBaselineContributorMap (after naming-contract remap).
_QE_PCT_CAPS: dict[str, float] = {
    'state::tower.defense_pct': 98.0,
}
_ALLOWED_CONTRIBUTOR_OPS = frozenset({'add', 'remove', 'multiply', 'replace'})
_MUTATION_METADATA_FIELDS = frozenset(
    {
        'surface_id',
        'surface_class',
        'domain',
        'source_class',
        'composition_stage',
        'value_type',
        'active',
        'gate_reason',
        'provenance_ref',
    }
)
_REMOVE_FORBIDDEN_FIELDS = _MUTATION_METADATA_FIELDS | frozenset({'new_value', 'factor'})


@lru_cache(maxsize=1)
def _load_overlay_contract() -> Mapping[str, Any]:
    return MappingProxyType(yaml.safe_load(_OVERLAY_CONTRACT_PATH.read_text()) or {})


@lru_cache(maxsize=1)
def _load_query_contract() -> Mapping[str, Any]:
    return MappingProxyType(yaml.safe_load(_QUERY_CONTRACT_PATH.read_text()) or {})


@lru_cache(maxsize=1)
def _load_family_contract() -> Mapping[str, Any]:
    return MappingProxyType(yaml.safe_load(_FAMILY_CONTRACT_PATH.read_text()) or {})


@dataclass(frozen=True)
class OverlayAppliedContributorMap:
    account_snapshot_id: str
    loadout_id: str
    scenario_id: str
    runtime_branch_id: str
    family_id: str
    contributor_rows: tuple[BaselineContributorRow, ...]
    delta_id: str
    delta_type: str

    @property
    def contributor_rows_by_surface(self) -> Mapping[str, tuple[BaselineContributorRow, ...]]:
        grouped: dict[str, list[BaselineContributorRow]] = {}
        for row in self.contributor_rows:
            grouped.setdefault(row.surface_id, []).append(row)
        return MappingProxyType({surface_id: tuple(rows) for surface_id, rows in grouped.items()})


@dataclass(frozen=True)
class ResolvedSurfaceRow:
    surface_id: str
    final_value: Any
    value_type: str
    status: str


@dataclass(frozen=True)
class QueryResponse:
    family_id: str
    resolved_surface_rows: tuple[ResolvedSurfaceRow, ...]
    contributor_rows: tuple[BaselineContributorRow, ...]
    dependency_trace: Mapping[str, Mapping[str, Any]]


class OverlayApplicator:
    def __init__(self) -> None:
        overlay_contract = _load_overlay_contract()
        family_contract = _load_family_contract()
        self._required_fields = tuple(overlay_contract.get('required_fields') or ())
        self._allowed_delta_types = frozenset(overlay_contract.get('allowed_delta_types') or ())
        self._target_scope_allowed_keys = frozenset(((overlay_contract.get('target_scope_schema') or {}).get('allowed_keys') or ()))
        changed_schema = overlay_contract.get('changed_contributors_schema') or {}
        self._op_required_fields = {
            str(operation): tuple(payload.get('required_fields') or ())
            for operation, payload in (changed_schema.get('per_operation_requirements') or {}).items()
        }
        self._family_allowed_delta_types = _family_allowed_delta_types(family_contract)
        self._surface_metadata_by_id = load_surface_metadata_by_id()

    def apply_overlay_delta(
        self,
        family_baseline_contributor_map: FamilyBaselineContributorMap,
        immutable_overlay_delta: Mapping[str, Any],
    ) -> OverlayAppliedContributorMap:
        self._validate_delta(family_baseline_contributor_map, immutable_overlay_delta)
        rows_by_id = {row.contributor_id: row for row in family_baseline_contributor_map.contributor_rows}
        new_rows = list(family_baseline_contributor_map.contributor_rows)
        index_by_id = {row.contributor_id: idx for idx, row in enumerate(new_rows)}

        for change in immutable_overlay_delta.get('changed_contributors', ()):
            operation = str(change.get('operation') or 'replace').strip()
            if operation not in _ALLOWED_CONTRIBUTOR_OPS:
                raise ValueError(f'Unsupported overlay contributor operation {operation!r}.')
            contributor_id = _required(change, 'contributor_id')
            target_row = rows_by_id.get(contributor_id)
            if operation == 'add':
                if target_row is not None:
                    raise ValueError(f'Overlay add operation refuses to overwrite existing contributor {contributor_id!r}.')
                created = _row_from_overlay_add(change, self._surface_metadata_by_id)
                new_rows.append(created)
                rows_by_id[contributor_id] = created
                index_by_id[contributor_id] = len(new_rows) - 1
                continue
            if target_row is None:
                raise ValueError(f'Overlay contributor {contributor_id!r} is missing from the baseline map.')
            _validate_surface_metadata(
                surface_metadata_by_id=self._surface_metadata_by_id,
                surface_id=target_row.surface_id,
                surface_class=target_row.surface_class,
                domain=target_row.domain,
            )
            if operation == 'remove':
                del new_rows[index_by_id[contributor_id]]
                rows_by_id.pop(contributor_id, None)
                index_by_id = {row.contributor_id: idx for idx, row in enumerate(new_rows)}
                continue
            if operation == 'multiply':
                new_value = _coerce_numeric(target_row.value) * _coerce_numeric(_required(change, 'factor'))
            else:
                new_value = _required(change, 'new_value')
            replacement = BaselineContributorRow(
                surface_id=target_row.surface_id,
                surface_class=target_row.surface_class,
                domain=target_row.domain,
                source_class=target_row.source_class,
                source_family=target_row.source_family,
                source_name=target_row.source_name,
                composition_stage=target_row.composition_stage,
                contributor_id=target_row.contributor_id,
                value=new_value,
                value_type=target_row.value_type,
                input_value=target_row.input_value,
                input_value_type=target_row.input_value_type,
                input_notes=target_row.input_notes,
                active=target_row.active,
                gate_reason=target_row.gate_reason,
                provenance_ref=target_row.provenance_ref,
            )
            new_rows[index_by_id[contributor_id]] = replacement
            rows_by_id[contributor_id] = replacement

        return OverlayAppliedContributorMap(
            account_snapshot_id=family_baseline_contributor_map.account_snapshot_id,
            loadout_id=family_baseline_contributor_map.loadout_id,
            scenario_id=family_baseline_contributor_map.scenario_id,
            runtime_branch_id=str(immutable_overlay_delta['runtime_branch_id']),
            family_id=family_baseline_contributor_map.family_id,
            contributor_rows=tuple(sorted(new_rows, key=contributor_row_sort_key)),
            delta_id=str(immutable_overlay_delta['delta_id']),
            delta_type=str(immutable_overlay_delta['delta_type']),
        )

    def _validate_delta(self, baseline: FamilyBaselineContributorMap, delta: Mapping[str, Any]) -> None:
        missing = [field for field in self._required_fields if field not in delta]
        if missing:
            raise ValueError(f'Overlay delta is missing required fields: {missing}.')
        baseline_runtime_branch_id = str(delta['baseline_runtime_branch_id'])
        runtime_branch_id = str(delta['runtime_branch_id'])
        if baseline_runtime_branch_id != baseline.runtime_branch_id:
            raise ValueError('Overlay baseline_runtime_branch_id does not match the supplied baseline runtime_branch_id.')
        if runtime_branch_id == baseline_runtime_branch_id:
            raise ValueError('Overlay runtime_branch_id must identify a new immutable branch, not reuse the baseline runtime_branch_id.')
        delta_type = str(delta['delta_type'])
        if delta_type not in self._allowed_delta_types:
            raise ValueError(f'Overlay delta_type {delta_type!r} is not declared by the KB schema.')
        if str(delta['affected_family_id']) != baseline.family_id:
            raise ValueError('Overlay affected_family_id does not match the baseline family_id.')
        allowed_delta_types = self._family_allowed_delta_types.get(baseline.family_id)
        if allowed_delta_types is None or delta_type not in allowed_delta_types:
            raise ValueError(f'Family {baseline.family_id!r} forbids overlay delta_type {delta_type!r}.')
        target_scope = delta.get('target_scope') or {}
        unknown_scope_keys = sorted(set(target_scope) - self._target_scope_allowed_keys)
        if unknown_scope_keys:
            raise ValueError(f'Overlay target_scope contains unsupported keys: {unknown_scope_keys}.')
        allowed_surfaces = {row.surface_id for row in baseline.contributor_rows}
        allowed_contributor_ids = {row.contributor_id for row in baseline.contributor_rows}
        supplied_surfaces = set(target_scope.get('surface_ids') or ())
        supplied_contributor_ids = set(target_scope.get('contributor_ids') or ())
        if not supplied_surfaces.issubset(allowed_surfaces):
            raise ValueError('Overlay target_scope surface_ids include surfaces absent from the supplied baseline family map.')
        if not supplied_contributor_ids.issubset(allowed_contributor_ids):
            raise ValueError('Overlay target_scope contributor_ids include contributors absent from the supplied baseline family map.')
        if not isinstance(delta.get('changed_masks'), Sequence) or not isinstance(delta.get('changed_assertions'), Sequence):
            raise ValueError('Overlay changed_masks and changed_assertions must be sequences, even when empty.')
        for change in delta.get('changed_contributors', ()):
            if 'contributor_id' not in change:
                raise ValueError('Every overlay changed_contributors row must include contributor_id.')
            self._validate_change(change, supplied_surfaces=supplied_surfaces, supplied_contributor_ids=supplied_contributor_ids)

    def _validate_change(
        self,
        change: Mapping[str, Any],
        *,
        supplied_surfaces: set[str],
        supplied_contributor_ids: set[str],
    ) -> None:
        operation = str(change.get('operation') or 'replace').strip()
        if operation not in _ALLOWED_CONTRIBUTOR_OPS:
            raise ValueError(f'Unsupported overlay contributor operation {operation!r}.')
        missing = [field for field in self._op_required_fields.get(operation, ()) if field not in change]
        if missing:
            raise ValueError(f'Overlay {operation} operation is missing required fields: {missing}.')

        contributor_id = str(change['contributor_id'])
        if supplied_contributor_ids and operation in {'replace', 'multiply', 'remove'} and contributor_id not in supplied_contributor_ids:
            raise ValueError(f'Overlay {operation} operation targets contributor_id {contributor_id!r} outside target_scope contributor_ids.')

        if operation == 'add':
            surface_id = str(change['surface_id'])
            if supplied_surfaces and surface_id not in supplied_surfaces:
                raise ValueError(f'Overlay add operation targets surface_id {surface_id!r} outside target_scope surface_ids.')
            return

        illegal_mutation_fields = sorted(set(change) & _MUTATION_METADATA_FIELDS)
        if illegal_mutation_fields:
            raise ValueError(
                f'Overlay {operation} operation cannot mutate contributor metadata fields: {illegal_mutation_fields}.'
            )
        if operation == 'remove':
            illegal_remove_fields = sorted(set(change) & _REMOVE_FORBIDDEN_FIELDS)
            if illegal_remove_fields:
                raise ValueError(
                    f'Overlay remove operation cannot carry value or metadata mutation fields: {illegal_remove_fields}.'
                )


class StatQueryKernel:
    def __init__(self, *, registry: DependencyRegistry | None = None) -> None:
        query_contract = _load_query_contract()
        self.materializer = FamilyBaselineMaterializer()
        self.overlay_applicator = OverlayApplicator()
        self.registry = DependencyRegistry.load_default() if registry is None else registry
        self._allowed_trace_modes = frozenset(query_contract.get('trace_modes') or _ALLOWED_TRACE_MODES)

    def materialise_family_baseline(self, bound_inputs: BoundStatInputs, family_id: str) -> FamilyBaselineContributorMap:
        return self.materializer.materialize(bound_inputs, family_id)

    def apply_overlay_delta(
        self,
        family_baseline_contributor_map: FamilyBaselineContributorMap,
        immutable_overlay_delta: Mapping[str, Any],
    ) -> OverlayAppliedContributorMap:
        return self.overlay_applicator.apply_overlay_delta(family_baseline_contributor_map, immutable_overlay_delta)

    def resolve_surfaces(
        self,
        overlay_applied_contributor_map: FamilyBaselineContributorMap | OverlayAppliedContributorMap,
        requested_surface_ids: Iterable[str],
        trace_mode: str = 'contributors',
    ) -> QueryResponse:
        """Resolve requested surfaces from an overlay-applied map or a baseline-only branch_base map."""
        trace_mode = str(trace_mode)
        if trace_mode not in self._allowed_trace_modes:
            raise ValueError(f'Unsupported trace_mode {trace_mode!r}.')
        requested = tuple(str(surface_id) for surface_id in requested_surface_ids)
        available = overlay_applied_contributor_map.contributor_rows_by_surface

        def _resolve_available_surface_id(surface_id: str) -> str | None:
            candidates = (
                surface_id,
                to_v2_surface_id(surface_id),
                to_legacy_surface_id(surface_id),
                'canonical_stat::free_upgrade_multiplier' if str(surface_id) == 'support_surface::free_upgrade_multiplier' else None,
            )
            for candidate in candidates:
                if candidate is not None and candidate in available:
                    return candidate
            return None

        def _publish_surface_id(surface_id: str) -> str:
            return publish_lookup.get(surface_id, to_v2_surface_id(surface_id))

        def _surface_step(
            surface_id: str,
            *,
            step_index: int,
            step_kind: str,
            status: str,
            note: str = '',
            **details: Any,
        ) -> dict[str, Any]:
            payload: dict[str, Any] = {
                'step_index': int(step_index),
                'step_kind': str(step_kind),
                'node_id': _publish_surface_id(surface_id),
                'status': str(status),
            }
            if note:
                payload['note'] = str(note)
            for key, value in details.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    payload[key] = [
                        _publish_surface_id(item) if 'surface' in key or 'node' in key else item
                        for item in value
                    ]
                else:
                    payload[key] = _publish_surface_id(value) if ('surface' in key or 'node' in key) and isinstance(value, str) else value
            return payload

        available_requested = tuple(_resolve_available_surface_id(surface_id) for surface_id in requested)
        missing = sorted(surface_id for surface_id, available_surface_id in zip(requested, available_requested) if available_surface_id is None)
        if missing:
            raise ValueError(f'Requested surfaces are not covered by family {overlay_applied_contributor_map.family_id!r}: {missing}.')

        published_requested = requested
        publish_lookup = {
            available_surface_id: requested_surface_id
            for requested_surface_id, available_surface_id in zip(requested, available_requested)
            if available_surface_id is not None
        }
        dependency_seeds = tuple(available_surface_id for available_surface_id in available_requested if available_surface_id is not None)
        resolution_closure = self.registry.closure_upstream(dependency_seeds)
        resolution_closure.update(dependency_seeds)
        ordered_resolution_candidates = list(self.registry.topo_publishable_subset(resolution_closure))
        for surface_id in sorted(resolution_closure):
            if surface_id not in ordered_resolution_candidates:
                ordered_resolution_candidates.append(surface_id)
        resolution_surface_ids: list[str] = []
        for surface_id in ordered_resolution_candidates:
            available_surface_id = _resolve_available_surface_id(surface_id)
            if available_surface_id is None or available_surface_id in resolution_surface_ids:
                continue
            resolution_surface_ids.append(available_surface_id)

        trace_steps_by_surface: dict[str, list[dict[str, Any]]] = {}
        resolution_attempts: dict[str, int] = {}
        resolution_order_index_by_surface: dict[str, int] = {}
        if trace_mode == 'full_trace':
            for available_surface_id in dependency_seeds:
                published_surface_id = _publish_surface_id(available_surface_id)
                direct_upstream = tuple(_publish_surface_id(node_id) for node_id in self.registry.upstream.get(available_surface_id, []))
                direct_downstream = tuple(_publish_surface_id(node_id) for node_id in self.registry.downstream.get(available_surface_id, []))
                trace_steps_by_surface[published_surface_id] = [
                    _surface_step(
                        available_surface_id,
                        step_index=1,
                        step_kind='surface_requested',
                        status='ready',
                        note='Surface selected for QE resolution trace.',
                        requested_surface_ids=published_requested,
                    ),
                    _surface_step(
                        available_surface_id,
                        step_index=2,
                        step_kind='dependency_lineage_loaded',
                        status='ready',
                        note='Declared dependency lineage loaded from registry.',
                        direct_upstream_node_ids=direct_upstream,
                        direct_downstream_node_ids=direct_downstream,
                    ),
                ]

        resolved_rows_by_surface: dict[str, object] = {}
        resolved_by_available_surface: dict[str, ResolvedSurfaceRow] = {}
        pending = {surface_id for surface_id in resolution_surface_ids if surface_id in available}
        ordered_resolution = [surface_id for surface_id in resolution_surface_ids if surface_id in pending]
        resolution_order_counter = 0
        while pending:
            progress = False
            for available_surface_id in ordered_resolution:
                if available_surface_id not in pending:
                    continue
                resolution_attempts[available_surface_id] = resolution_attempts.get(available_surface_id, 0) + 1
                if trace_mode == 'full_trace' and available_surface_id in publish_lookup:
                    published_surface_id = _publish_surface_id(available_surface_id)
                    upstream_nodes = self.registry.upstream.get(available_surface_id, [])
                    resolved_upstream = [node_id for node_id in upstream_nodes if node_id in resolved_rows_by_surface]
                    unresolved_upstream = [node_id for node_id in upstream_nodes if node_id not in resolved_rows_by_surface]
                    trace_steps_by_surface.setdefault(published_surface_id, []).append(
                        _surface_step(
                            available_surface_id,
                            step_index=len(trace_steps_by_surface.get(published_surface_id, [])) + 1,
                            step_kind='resolve_attempt',
                            status='running',
                            note='QE attempting to resolve surface against current upstream availability.',
                            attempt_index=resolution_attempts[available_surface_id],
                            resolved_upstream_node_ids=resolved_upstream,
                            unresolved_upstream_node_ids=unresolved_upstream,
                        )
                    )
                surface_trace_steps = trace_steps_by_surface.get(_publish_surface_id(available_surface_id)) if trace_mode == 'full_trace' else None
                resolved = self._resolve_surface(
                    available_surface_id,
                    available[available_surface_id],
                    resolved_rows=resolved_rows_by_surface,
                    trace_steps=surface_trace_steps,
                )
                if resolved.status == 'mapped_not_resolved':
                    if trace_mode == 'full_trace' and available_surface_id in publish_lookup:
                        trace_steps_by_surface[_publish_surface_id(available_surface_id)].append(
                            _surface_step(
                                available_surface_id,
                                step_index=len(trace_steps_by_surface[_publish_surface_id(available_surface_id)]) + 1,
                                step_kind='resolve_deferred',
                                status='waiting',
                                note='Resolution deferred because required upstream data is not yet resolved.',
                            )
                        )
                    continue
                resolved_by_available_surface[available_surface_id] = resolved
                resolved_rows_by_surface[available_surface_id] = SimpleNamespace(
                    final_value=resolved.final_value,
                    status=resolved.status,
                )
                resolution_order_counter += 1
                resolution_order_index_by_surface[available_surface_id] = resolution_order_counter
                if trace_mode == 'full_trace' and available_surface_id in publish_lookup:
                    trace_steps_by_surface[_publish_surface_id(available_surface_id)].append(
                        _surface_step(
                            available_surface_id,
                            step_index=len(trace_steps_by_surface[_publish_surface_id(available_surface_id)]) + 1,
                            step_kind='surface_resolved',
                            status=resolved.status,
                            note='QE published a final row for this surface.',
                            resolution_order_index=resolution_order_counter,
                            value_type=resolved.value_type,
                            final_value=resolved.final_value,
                        )
                    )
                pending.remove(available_surface_id)
                progress = True
            if progress:
                continue
            for available_surface_id in list(pending):
                resolution_attempts[available_surface_id] = resolution_attempts.get(available_surface_id, 0) + 1
                surface_trace_steps = trace_steps_by_surface.get(_publish_surface_id(available_surface_id)) if trace_mode == 'full_trace' else None
                resolved = self._resolve_surface(
                    available_surface_id,
                    available[available_surface_id],
                    resolved_rows=resolved_rows_by_surface,
                    trace_steps=surface_trace_steps,
                )
                resolved_by_available_surface[available_surface_id] = resolved
                resolved_rows_by_surface[available_surface_id] = SimpleNamespace(
                    final_value=resolved.final_value,
                    status=resolved.status,
                )
                resolution_order_counter += 1
                resolution_order_index_by_surface[available_surface_id] = resolution_order_counter
                if trace_mode == 'full_trace' and available_surface_id in publish_lookup:
                    trace_steps_by_surface.setdefault(_publish_surface_id(available_surface_id), []).append(
                        _surface_step(
                            available_surface_id,
                            step_index=len(trace_steps_by_surface.get(_publish_surface_id(available_surface_id), [])) + 1,
                            step_kind='forced_resolution_finalize',
                            status=resolved.status,
                            note='QE finalized the remaining pending surface after dependency progress stalled.',
                            attempt_index=resolution_attempts[available_surface_id],
                            resolution_order_index=resolution_order_counter,
                            value_type=resolved.value_type,
                            final_value=resolved.final_value,
                        )
                    )
                pending.remove(available_surface_id)
        resolved_rows = tuple(
            replace(
                resolved_by_available_surface[available_surface_id],
                surface_id=publish_lookup[available_surface_id],
            )
            for available_surface_id in available_requested
            if available_surface_id is not None
        )
        contributor_rows = () if trace_mode == 'none' else tuple(
            replace(row, surface_id=publish_lookup.get(row.surface_id, row.surface_id))
            for available_surface_id in available_requested
            if available_surface_id is not None
            for row in available[available_surface_id]
        )
        dependency_trace: dict[str, dict[str, Any]] = {}
        for available_surface_id in dependency_seeds:
            published_surface_id = _publish_surface_id(available_surface_id)
            direct_upstream = tuple(_publish_surface_id(node_id) for node_id in self.registry.upstream.get(available_surface_id, []))
            direct_downstream = tuple(_publish_surface_id(node_id) for node_id in self.registry.downstream.get(available_surface_id, []))
            upstream_closure = tuple(_publish_surface_id(node_id) for node_id in sorted(self.registry.closure_upstream((available_surface_id,)) - {available_surface_id}))
            downstream_closure = tuple(_publish_surface_id(node_id) for node_id in sorted(self.registry.closure_downstream((available_surface_id,)) - {available_surface_id}))
            resolved_upstream = tuple(node_id for node_id in direct_upstream if node_id in {_publish_surface_id(key) for key in resolved_rows_by_surface})
            unresolved_upstream = tuple(node_id for node_id in direct_upstream if node_id not in resolved_upstream)
            trace_steps = trace_steps_by_surface.get(published_surface_id, ()) if trace_mode == 'full_trace' else ()
            dependency_trace[published_surface_id] = {
                'trace_contract_id': 'qe_dependency_trace_v1',
                'surface_id': published_surface_id,
                'trace_mode': trace_mode,
                'requested_surface_ids': list(published_requested),
                'resolution_order_index': resolution_order_index_by_surface.get(available_surface_id),
                'direct_upstream_node_ids': list(direct_upstream),
                'direct_downstream_node_ids': list(direct_downstream),
                'upstream_closure_node_ids': list(upstream_closure),
                'downstream_closure_node_ids': list(downstream_closure),
                'resolved_upstream_node_ids': list(resolved_upstream),
                'unresolved_upstream_node_ids': list(unresolved_upstream),
                'has_runtime_trace_steps': bool(trace_steps),
                'trace_steps': list(trace_steps),
            }
        return QueryResponse(
            family_id=overlay_applied_contributor_map.family_id,
            resolved_surface_rows=resolved_rows,
            contributor_rows=contributor_rows,
            dependency_trace=dependency_trace,
        )

    def _resolve_surface(
        self,
        surface_id: str,
        rows: Sequence[BaselineContributorRow],
        *,
        resolved_rows: Mapping[str, object] | None = None,
        trace_steps: list[dict[str, Any]] | None = None,
    ) -> ResolvedSurfaceRow:
        legacy_surface_id = to_legacy_surface_id(surface_id)
        destination_object_type, separator, destination_id = legacy_surface_id.partition('::')
        if (
            separator
            and destination_object_type in {
                'canonical_stat',
                'mechanic_param',
                'runtime_mechanic_param',
                'environment_param',
                'account_flag',
                'account_context',
                'meta_progression_param',
                'cosmetic_bonus',
                'capability',
            }
            and all(row.source_family is not None for row in rows)
        ):
            stat_inputs = [
                StatInput(
                    stat_name=legacy_surface_id,
                    source_family=str(row.source_family),
                    source_name=str(row.source_name or row.contributor_id),
                    value=row.input_value,
                    value_type=str(row.input_value_type or row.value_type),
                    stage='qe_native_family_query',
                    active=row.active,
                    provenance=row.provenance_ref,
                    notes=row.input_notes,
                    contributor_id=row.contributor_id,
                    destination_object_type=destination_object_type,
                    destination_id=destination_id,
                )
                for row in rows
            ]
            if trace_steps is not None:
                trace_steps.append({
                    'step_index': len(trace_steps) + 1,
                    'step_kind': 'resolution_backend_selected',
                    'node_id': to_v2_surface_id(surface_id),
                    'status': 'running',
                    'note': 'QE selected the native bucket resolver path for this surface.',
                    'backend': 'qe_native_bucket',
                    'destination_object_type': destination_object_type,
                    'destination_id': destination_id,
                    'contributor_count': len(stat_inputs),
                    'active_contributor_count': sum(1 for row in stat_inputs if row.active),
                })
            from qe.routing import load_bounded_resolution_metadata, resolve_bounded_bucket

            bounded_meta = dict(
                load_bounded_resolution_metadata().get(
                    destination_id,
                    {'unit': 'unknown', 'resolver': stat_inputs[0].resolver_id or 'unknown'},
                )
            )
            bounded_meta['_resolved_rows'] = {
                str(key): value
                for key, value in (resolved_rows or {}).items()
            }
            final_value, status, notes, _schema = resolve_bounded_bucket(
                destination_object_type,
                destination_id,
                stat_inputs,
                bounded_meta,
            )
            meta = {'unit': str(bounded_meta.get('unit') or ''), 'resolver': str(bounded_meta.get('resolver') or '')}
            if trace_steps is not None:
                trace_steps.append({
                    'step_index': len(trace_steps) + 1,
                    'step_kind': 'resolution_backend_result',
                    'node_id': to_v2_surface_id(surface_id),
                    'status': status,
                    'note': notes,
                    'backend': 'qe_native_bucket',
                    'resolver_id': str(meta.get('resolver') or ''),
                    'value_type': str(meta.get('unit') or next(iter({row.value_type for row in rows}))),
                    'final_value': final_value,
                })
            return ResolvedSurfaceRow(
                surface_id=surface_id,
                final_value=final_value,
                value_type=str(meta.get('unit') or next(iter({row.value_type for row in rows}))),
                status=status,
            )

        value_types = {row.value_type for row in rows}
        if len(value_types) != 1:
            raise ValueError(f'Surface {surface_id!r} mixes multiple contributor value types: {sorted(value_types)}.')
        active_rows = [row for row in rows if row.active]
        if trace_steps is not None:
            trace_steps.append({
                'step_index': len(trace_steps) + 1,
                'step_kind': 'resolution_backend_selected',
                'node_id': to_v2_surface_id(surface_id),
                'status': 'running',
                'note': 'QE selected direct composition for this surface.',
                'backend': 'kernel_direct_composition',
                'contributor_count': len(rows),
                'active_contributor_count': len(active_rows),
                'composition_stages': sorted({row.composition_stage for row in rows}),
            })
        if not active_rows:
            if trace_steps is not None:
                trace_steps.append({
                    'step_index': len(trace_steps) + 1,
                    'step_kind': 'resolution_backend_result',
                    'node_id': to_v2_surface_id(surface_id),
                    'status': 'gated_off',
                    'note': 'All contributors are inactive, so QE gated this surface off.',
                    'backend': 'kernel_direct_composition',
                    'value_type': next(iter(value_types)),
                })
            return ResolvedSurfaceRow(surface_id=surface_id, final_value=None, value_type=next(iter(value_types)), status='gated_off')

        supported_stages = _MUTATING_STAGES | {'multiplicative', 'gate_enable_disable'}
        unsupported_stages = sorted({row.composition_stage for row in active_rows if row.composition_stage not in supported_stages})
        if unsupported_stages:
            raise ValueError(f"Surface {surface_id!r} includes unsupported phase-1 composition stages: {unsupported_stages}.")

        additive_rows = [row for row in active_rows if row.composition_stage in _MUTATING_STAGES]
        multiplicative_rows = [row for row in active_rows if row.composition_stage == 'multiplicative']
        gate_rows = [row for row in active_rows if row.composition_stage == 'gate_enable_disable']

        if gate_rows and not additive_rows and not multiplicative_rows:
            if trace_steps is not None:
                trace_steps.append({
                    'step_index': len(trace_steps) + 1,
                    'step_kind': 'resolution_backend_result',
                    'node_id': to_v2_surface_id(surface_id),
                    'status': 'resolved',
                    'note': 'Gate-only surface resolved true from active gate contributors.',
                    'backend': 'kernel_direct_composition',
                    'value_type': next(iter(value_types)),
                    'final_value': True,
                })
            return ResolvedSurfaceRow(surface_id=surface_id, final_value=True, value_type=next(iter(value_types)), status='resolved')

        additive_total = sum(_coerce_numeric(row.value) for row in additive_rows)
        multiplicative_total = prod(_coerce_numeric(row.value) for row in multiplicative_rows) if multiplicative_rows else 1
        if additive_rows:
            final_value: Any = additive_total * multiplicative_total
        elif multiplicative_rows:
            final_value = multiplicative_total
        else:
            raise ValueError(f'Surface {surface_id!r} has active contributors but no supported composition stages.')
        final_value = _normalize_number(final_value)
        if surface_id in _QE_PCT_CAPS and isinstance(final_value, (int, float)):
            final_value = max(0.0, min(_QE_PCT_CAPS[surface_id], float(final_value)))
        if trace_steps is not None:
            trace_steps.append({
                'step_index': len(trace_steps) + 1,
                'step_kind': 'resolution_backend_result',
                'node_id': to_v2_surface_id(surface_id),
                'status': 'resolved',
                'note': 'Direct kernel composition completed for this surface.',
                'backend': 'kernel_direct_composition',
                'value_type': next(iter(value_types)),
                'final_value': final_value,
            })
        return ResolvedSurfaceRow(surface_id=surface_id, final_value=final_value, value_type=next(iter(value_types)), status='resolved')

    def _dependency_closure(self, requested: Sequence[str], trace_mode: str) -> tuple[str, ...]:
        if trace_mode != 'full_trace':
            return tuple(requested)
        closure = self.registry.closure_upstream(requested)
        closure.update(requested)
        return tuple(sorted(closure))


@lru_cache(maxsize=1)
def get_default_query_kernel() -> StatQueryKernel:
    return StatQueryKernel()


def _required(mapping: Mapping[str, Any], field: str) -> Any:
    if field not in mapping:
        raise ValueError(f'Missing required overlay field {field!r}.')
    return mapping[field]


def _row_from_overlay_add(
    change: Mapping[str, Any],
    surface_metadata_by_id: Mapping[str, Mapping[str, Any]],
) -> BaselineContributorRow:
    required = (
        'surface_id',
        'surface_class',
        'domain',
        'source_class',
        'composition_stage',
        'contributor_id',
        'new_value',
        'value_type',
        'provenance_ref',
    )
    missing = [field for field in required if field not in change]
    if missing:
        raise ValueError(f'Overlay add operation is missing contributor row fields: {missing}.')
    _validate_surface_metadata(
        surface_metadata_by_id=surface_metadata_by_id,
        surface_id=str(change['surface_id']),
        surface_class=str(change['surface_class']),
        domain=str(change['domain']),
    )
    return BaselineContributorRow(
        surface_id=str(change['surface_id']),
        surface_class=str(change['surface_class']),
        domain=str(change['domain']),
        source_class=str(change['source_class']),
        source_family=str(change.get('source_family') or '') or None,
        source_name=str(change.get('source_name') or '') or None,
        composition_stage=str(change['composition_stage']),
        contributor_id=str(change['contributor_id']),
        value=change['new_value'],
        value_type=str(change['value_type']),
        input_value=change.get('new_value'),
        input_value_type=str(change.get('value_type') or ''),
        input_notes=str(change.get('input_notes') or '') or None,
        active=bool(change.get('active', True)),
        gate_reason=change.get('gate_reason'),
        provenance_ref=str(change['provenance_ref']),
    )


def _validate_surface_metadata(
    *,
    surface_metadata_by_id: Mapping[str, Mapping[str, Any]],
    surface_id: str,
    surface_class: str,
    domain: str,
) -> None:
    metadata = surface_metadata_by_id.get(surface_id)
    if metadata is None:
        raise ValueError(f'Overlay references undeclared surface_id {surface_id!r}.')
    expected_surface_class = str(metadata['surface_class'])
    expected_domain = str(metadata['domain'])
    if surface_class != expected_surface_class:
        raise ValueError(
            f'Overlay surface_class mismatch for {surface_id!r}: expected {expected_surface_class!r}, got {surface_class!r}.'
        )
    if domain != expected_domain:
        raise ValueError(f'Overlay domain mismatch for {surface_id!r}: expected {expected_domain!r}, got {domain!r}.')


def _coerce_numeric(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f'Expected numeric overlay/query value, got {value!r}.')


def _normalize_number(value: float) -> Any:
    rounded = round(value)
    if abs(value - rounded) < 1e-12:
        return int(rounded)
    return value


def _family_allowed_delta_types(family_contract: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    allowed: dict[str, frozenset[str]] = {}
    for group_payload in (family_contract.get('family_groups') or {}).values():
        for family_id, family_data in (group_payload.get('families') or {}).items():
            allowed[family_id] = frozenset(family_data.get('allowed_overlay_types') or ())
    return allowed
