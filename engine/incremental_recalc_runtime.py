from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from engine.dependency_registry import DependencyRegistry
from engine.runtime_consumer_registry import impacted_runtime_consumers


@dataclass(frozen=True)
class IncrementalPlan:
    mutated_source_nodes: List[str]
    dirty_nodes: List[str]
    publishable_dirty_nodes: List[str]
    runtime_consumer_ids: List[str]
    fallback_required: bool
    fallback_reason: str | None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mutated_source_nodes': list(self.mutated_source_nodes),
            'dirty_nodes': list(self.dirty_nodes),
            'publishable_dirty_nodes': list(self.publishable_dirty_nodes),
            'runtime_consumer_ids': list(self.runtime_consumer_ids),
            'fallback_required': self.fallback_required,
            'fallback_reason': self.fallback_reason,
        }


class IncrementalRecalcRuntime:
    def __init__(self, registry: DependencyRegistry | None = None):
        self.registry = DependencyRegistry.load_default() if registry is None else registry

    def plan_from_workshop_overrides(self, workshop_levels_current: Dict[str, int]) -> IncrementalPlan:
        mutated = []
        unknown = []
        for key in workshop_levels_current:
            mapping = self.registry.mutation_mappings.get(key)
            if mapping is None:
                unknown.append(key)
                continue
            mutated.append(mapping.source_node_id)
        if unknown:
            return IncrementalPlan([], [], [], [], True, f'Unsupported mutation keys for incremental planning: {sorted(unknown)}')
        dirty = sorted(self.registry.closure_downstream(mutated))
        publishable_dirty = sorted(
            node for node in dirty
            if (self.registry.node(node) is not None and self.registry.node(node).is_publishable)
        )
        runtime_consumer_ids = sorted(rule.consumer_id for rule in impacted_runtime_consumers(dirty))
        return IncrementalPlan(mutated, dirty, publishable_dirty, runtime_consumer_ids, False, None)
