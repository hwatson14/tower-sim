from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from engine.dependency_registry import DependencyRegistry
from engine.runtime_consumer_registry import resolve_consumer_bundle


@dataclass(frozen=True)
class IncrementalPlan:
    consumer_id: str | None
    bundle_id: str | None
    family_id: str
    baseline_required: bool
    overlays_to_apply: List[str]
    requested_surfaces: List[str]
    upstream_dependency_closure: List[str]
    publishable_closure: List[str]
    runtime_consumer_ids: List[str]
    mutated_source_nodes: List[str]
    dirty_nodes: List[str]
    fallback_required: bool
    fallback_reason: str | None


    @property
    def publishable_dirty_nodes(self) -> List[str]:
        return list(self.publishable_closure)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'consumer_id': self.consumer_id,
            'bundle_id': self.bundle_id,
            'family_id': self.family_id,
            'baseline_required': self.baseline_required,
            'overlays_to_apply': list(self.overlays_to_apply),
            'requested_surfaces': list(self.requested_surfaces),
            'upstream_dependency_closure': list(self.upstream_dependency_closure),
            'publishable_closure': list(self.publishable_closure),
            'runtime_consumer_ids': list(self.runtime_consumer_ids),
            'mutated_source_nodes': list(self.mutated_source_nodes),
            'dirty_nodes': list(self.dirty_nodes),
            'fallback_required': self.fallback_required,
            'fallback_reason': self.fallback_reason,
        }


class IncrementalRecalcRuntime:
    def __init__(self, registry: DependencyRegistry | None = None):
        self.registry = DependencyRegistry.load_default() if registry is None else registry

    def plan_consumer_bundle(
        self,
        *,
        consumer_id: str,
        bundle_id: str,
        family_id: str,
        include_optional_surface_ids: Sequence[str] = (),
        overlay_delta_types: Sequence[str] = (),
        trace_mode: str | None = None,
    ) -> IncrementalPlan:
        try:
            resolved_bundle = resolve_consumer_bundle(
                consumer_id,
                bundle_id,
                family_id=family_id,
                include_optional_surface_ids=include_optional_surface_ids,
                trace_mode=trace_mode,
            )
        except ValueError as exc:
            return self._fallback_plan(family_id=family_id, consumer_id=consumer_id, bundle_id=bundle_id, reason=str(exc))

        closure = sorted(self.registry.closure_upstream(resolved_bundle.surface_ids))
        publishable = self.registry.topo_publishable_subset(closure)
        runtime_consumers = self.registry.impacted_runtime_consumer_ids(self.registry.closure_downstream(resolved_bundle.surface_ids))
        return IncrementalPlan(
            consumer_id=consumer_id,
            bundle_id=bundle_id,
            family_id=family_id,
            baseline_required=True,
            overlays_to_apply=list(overlay_delta_types),
            requested_surfaces=list(resolved_bundle.surface_ids),
            upstream_dependency_closure=closure,
            publishable_closure=publishable,
            runtime_consumer_ids=runtime_consumers,
            mutated_source_nodes=[],
            dirty_nodes=list(resolved_bundle.surface_ids),
            fallback_required=False,
            fallback_reason=None,
        )

    def plan_surface_request(
        self,
        *,
        family_id: str,
        surface_ids: Iterable[str],
        overlay_delta_types: Sequence[str] = (),
    ) -> IncrementalPlan:
        requested = [str(surface_id) for surface_id in surface_ids]
        unknown = [surface_id for surface_id in requested if self.registry.node(surface_id) is None]
        if unknown:
            return self._fallback_plan(family_id=family_id, reason=f'Unknown surface request for family {family_id!r}: {sorted(unknown)}')
        illegal = [
            surface_id
            for surface_id in requested
            if family_id not in self.registry.node(surface_id).family_ids
        ]
        if illegal:
            return self._fallback_plan(family_id=family_id, reason=f'Surfaces outside family {family_id!r}: {sorted(illegal)}')
        closure = sorted(self.registry.closure_upstream(requested))
        publishable = self.registry.topo_publishable_subset(closure)
        runtime_consumers = self.registry.impacted_runtime_consumer_ids(self.registry.closure_downstream(requested))
        return IncrementalPlan(
            consumer_id=None,
            bundle_id=None,
            family_id=family_id,
            baseline_required=True,
            overlays_to_apply=list(overlay_delta_types),
            requested_surfaces=requested,
            upstream_dependency_closure=closure,
            publishable_closure=publishable,
            runtime_consumer_ids=runtime_consumers,
            mutated_source_nodes=[],
            dirty_nodes=requested,
            fallback_required=False,
            fallback_reason=None,
        )

    def plan_overlay_mutation(
        self,
        *,
        family_id: str,
        mutation_class: str,
        trigger_keys: Iterable[str],
        consumer_id: str | None = None,
        bundle_id: str | None = None,
    ) -> IncrementalPlan:
        mutated: list[str] = []
        missing: list[str] = []
        for trigger_key in trigger_keys:
            mapping = self.registry.mutation_mapping(mutation_class, str(trigger_key))
            if mapping is None:
                missing.append(str(trigger_key))
                continue
            mutated.append(mapping.source_node_id)
        if missing:
            return self._fallback_plan(
                family_id=family_id,
                consumer_id=consumer_id,
                bundle_id=bundle_id,
                reason=f'Unsupported mutation keys for {mutation_class}: {sorted(missing)}',
            )
        dirty = sorted(self.registry.closure_downstream(mutated))
        publishable = self.registry.topo_publishable_subset(dirty)
        runtime_consumers = self.registry.impacted_runtime_consumer_ids(dirty)
        return IncrementalPlan(
            consumer_id=consumer_id,
            bundle_id=bundle_id,
            family_id=family_id,
            baseline_required=True,
            overlays_to_apply=[mutation_class],
            requested_surfaces=[],
            upstream_dependency_closure=sorted(self.registry.closure_upstream(dirty)),
            publishable_closure=publishable,
            runtime_consumer_ids=runtime_consumers,
            mutated_source_nodes=mutated,
            dirty_nodes=dirty,
            fallback_required=False,
            fallback_reason=None,
        )

    def plan_from_workshop_overrides(self, workshop_levels_current: Mapping[str, int]) -> IncrementalPlan:
        return self.plan_overlay_mutation(
            family_id='progression_runtime_no_perks',
            mutation_class='workshop_mutation',
            trigger_keys=workshop_levels_current,
        )

    @staticmethod
    def _fallback_plan(*, family_id: str, reason: str, consumer_id: str | None = None, bundle_id: str | None = None) -> IncrementalPlan:
        return IncrementalPlan(
            consumer_id=consumer_id,
            bundle_id=bundle_id,
            family_id=family_id,
            baseline_required=True,
            overlays_to_apply=[],
            requested_surfaces=[],
            upstream_dependency_closure=[],
            publishable_closure=[],
            runtime_consumer_ids=[],
            mutated_source_nodes=[],
            dirty_nodes=[],
            fallback_required=True,
            fallback_reason=reason,
        )
