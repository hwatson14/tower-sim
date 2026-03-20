from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    node_kind: str
    is_publishable: bool
    verification_status: str
    blocker_reason: str
    notes: str


@dataclass(frozen=True)
class DependencyEdge:
    upstream_node_id: str
    downstream_node_id: str
    verification_status: str
    notes: str


@dataclass(frozen=True)
class MutationMapping:
    mutation_class: str
    trigger_key: str
    source_node_id: str
    verification_status: str
    notes: str


class DependencyRegistry:
    def __init__(self, nodes: Dict[str, DependencyNode], edges: List[DependencyEdge], mutation_mappings: Dict[str, MutationMapping]):
        self.nodes = nodes
        self.edges = edges
        self.mutation_mappings = mutation_mappings
        self.downstream: Dict[str, List[str]] = {}
        self.upstream: Dict[str, List[str]] = {}
        for edge in edges:
            self.downstream.setdefault(edge.upstream_node_id, []).append(edge.downstream_node_id)
            self.upstream.setdefault(edge.downstream_node_id, []).append(edge.upstream_node_id)

    @classmethod
    def load_default(cls, root: Path | None = None) -> "DependencyRegistry":
        root = Path(__file__).resolve().parents[1] if root is None else Path(root)
        nodes = {}
        with (root / 'config' / 'progression_hot_dependency_nodes.csv').open(newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                nodes[row['node_id']] = DependencyNode(
                    node_id=row['node_id'],
                    node_kind=row['node_kind'],
                    is_publishable=row['is_publishable'].strip().lower() == 'true',
                    verification_status=row['verification_status'],
                    blocker_reason=row['blocker_reason'],
                    notes=row['notes'],
                )
        edges = []
        with (root / 'config' / 'progression_hot_dependency_edges.csv').open(newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                edges.append(DependencyEdge(**row))
        mutation_mappings = {}
        with (root / 'config' / 'progression_hot_mutation_classes.csv').open(newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                mapping = MutationMapping(**row)
                mutation_mappings[mapping.trigger_key] = mapping
        return cls(nodes=nodes, edges=edges, mutation_mappings=mutation_mappings)

    def node(self, node_id: str) -> DependencyNode | None:
        return self.nodes.get(node_id)

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
