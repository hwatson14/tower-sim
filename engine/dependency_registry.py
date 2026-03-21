from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Set

import yaml

from engine.runtime_consumer_registry import load_consumer_bundle_definitions
from engine.family_baseline_materializer import load_family_contracts, load_family_surface_ids

ROOT = Path(__file__).resolve().parents[1]
_DEPENDENCY_LEDGER_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-dependency-invalidation-ledger.yaml'


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    node_kind: str
    family_ids: tuple[str, ...]
    is_publishable: bool
    publication_relevance: str
    verification_status: str
    blocker_reason: str
    notes: str


@dataclass(frozen=True)
class DependencyEdge:
    upstream_node_id: str
    downstream_node_id: str
    invalidation_semantics: str
    mutation_classes: tuple[str, ...]
    publication_relevance: str
    verification_status: str
    notes: str


@dataclass(frozen=True)
class MutationMapping:
    mutation_class: str
    trigger_key: str
    source_node_id: str
    invalidation_semantics: str
    publication_relevance: str
    verification_status: str
    notes: str


@lru_cache(maxsize=1)
def load_dependency_ledger() -> dict[str, Any]:
    return yaml.safe_load(_DEPENDENCY_LEDGER_PATH.read_text()) or {}


class DependencyRegistry:
    def __init__(self, nodes: Dict[str, DependencyNode], edges: List[DependencyEdge], mutation_mappings: Dict[tuple[str, str], MutationMapping]):
        self.nodes = nodes
        self.edges = edges
        self.mutation_mappings = mutation_mappings
        self.downstream: Dict[str, List[str]] = {}
        self.upstream: Dict[str, List[str]] = {}
        for edge in edges:
            self.downstream.setdefault(edge.upstream_node_id, []).append(edge.downstream_node_id)
            self.upstream.setdefault(edge.downstream_node_id, []).append(edge.upstream_node_id)

    @classmethod
    def load_default(cls, root: Path | None = None) -> 'DependencyRegistry':
        _ = root
        ledger = load_dependency_ledger()
        nodes = {
            str(row['node_id']): DependencyNode(
                node_id=str(row['node_id']),
                node_kind=str(row['node_kind']),
                family_ids=tuple(str(family_id) for family_id in (row.get('family_ids') or ())),
                is_publishable=bool(row['is_publishable']),
                publication_relevance=str(row['publication_relevance']),
                verification_status=str(row['verification_status']),
                blocker_reason=str(row.get('blocker_reason') or ''),
                notes=str(row.get('notes') or ''),
            )
            for row in (ledger.get('nodes') or [])
        }
        edges = [
            DependencyEdge(
                upstream_node_id=str(row['upstream_node_id']),
                downstream_node_id=str(row['downstream_node_id']),
                invalidation_semantics=str(row['invalidation_semantics']),
                mutation_classes=tuple(str(item) for item in (row.get('mutation_classes') or ())),
                publication_relevance=str(row['publication_relevance']),
                verification_status=str(row['verification_status']),
                notes=str(row.get('notes') or ''),
            )
            for row in (ledger.get('edges') or [])
        ]
        mutation_mappings = {
            (str(row['mutation_class']), str(row['trigger_key'])): MutationMapping(
                mutation_class=str(row['mutation_class']),
                trigger_key=str(row['trigger_key']),
                source_node_id=str(row['source_node_id']),
                invalidation_semantics=str(row['invalidation_semantics']),
                publication_relevance=str(row['publication_relevance']),
                verification_status=str(row['verification_status']),
                notes=str(row.get('notes') or ''),
            )
            for row in (ledger.get('mutation_triggers') or [])
        }
        registry = cls(nodes=nodes, edges=edges, mutation_mappings=mutation_mappings)
        registry.assert_contract_integrity()
        return registry

    def assert_contract_integrity(self) -> None:
        family_surface_ids = load_family_surface_ids()
        family_contracts = load_family_contracts()
        bundle_definitions = load_consumer_bundle_definitions()
        for node_id, node in self.nodes.items():
            if not node.family_ids:
                raise ValueError(f'Dependency node {node_id!r} must declare family_ids.')
        for edge in self.edges:
            if edge.upstream_node_id not in self.nodes or edge.downstream_node_id not in self.nodes:
                raise ValueError(f'Dependency edge references undeclared node: {edge!r}.')
        for mapping in self.mutation_mappings.values():
            if mapping.source_node_id not in self.nodes:
                raise ValueError(f'Mutation mapping {mapping!r} references undeclared node.')
        bundle_surface_ids = {
            surface_id
            for definition in bundle_definitions.values()
            for surface_id in definition.surface_ids
        }
        uncovered = sorted(
            surface_id
            for surface_id in bundle_surface_ids
            if surface_id not in self.nodes
        )
        if uncovered:
            raise ValueError(f'Bundle-reachable surfaces missing dependency nodes: {uncovered}.')
        for surface_id in bundle_surface_ids:
            if not self.upstream.get(surface_id) and not self.downstream.get(surface_id):
                raise ValueError(f'Bundle-reachable surface {surface_id!r} has no dependency coverage.')
        declared_mutation_classes = {mapping.mutation_class for mapping in self.mutation_mappings.values()}
        required_mutation_classes = {
            str(overlay_type)
            for contract in family_contracts.values()
            for overlay_type in contract['allowed_overlay_types']
        }
        missing_mutation_classes = sorted(required_mutation_classes - declared_mutation_classes)
        if missing_mutation_classes:
            raise ValueError(f'Mutation classes missing invalidation mappings: {missing_mutation_classes}.')
        publishable_nodes = [node_id for node_id, node in self.nodes.items() if node.is_publishable]
        self.topo_publishable_subset(publishable_nodes)

    def node(self, node_id: str) -> DependencyNode | None:
        return self.nodes.get(node_id)

    def mutation_mapping(self, mutation_class: str, trigger_key: str) -> MutationMapping | None:
        return self.mutation_mappings.get((mutation_class, trigger_key))

    def closure_downstream(self, seeds: Iterable[str]) -> Set[str]:
        todo = list(seeds)
        seen: Set[str] = set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(self.downstream.get(node, []))
        return seen

    def closure_upstream(self, seeds: Iterable[str]) -> Set[str]:
        todo = list(seeds)
        seen: Set[str] = set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(self.upstream.get(node, []))
        return seen

    def impacted_runtime_consumer_ids(self, dirty_nodes: Iterable[str]) -> List[str]:
        dirty = set(dirty_nodes)
        return sorted(
            node_id for node_id in dirty
            if (node := self.nodes.get(node_id)) is not None and node.node_kind == 'runtime_consumer'
        )

    def topo_publishable_subset(self, nodes: Iterable[str]) -> List[str]:
        selected = {node for node in nodes if self.nodes.get(node) and self.nodes[node].is_publishable}
        indegree = {node: 0 for node in selected}
        for node in selected:
            for upstream in self.upstream.get(node, []):
                if upstream in selected:
                    indegree[node] += 1
        ready = sorted(node for node, degree in indegree.items() if degree == 0)
        order: List[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for downstream in self.downstream.get(node, []):
                if downstream in indegree:
                    indegree[downstream] -= 1
                    if indegree[downstream] == 0:
                        ready.append(downstream)
                        ready.sort()
        remaining = [node for node in selected if node not in order]
        if remaining:
            raise ValueError(f'Cycle or unresolved dependency ordering in selected nodes: {remaining}')
        return order
