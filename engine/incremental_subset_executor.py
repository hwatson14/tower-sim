from __future__ import annotations

from collections import defaultdict
from typing import ClassVar, Dict, Iterable, List, Set

from engine.dependency_registry import DependencyRegistry
from engine.stat_engine import _apply_phase3_postprocessing, _load_canonical_stats, _resolve_bucket
from models.stat_input import StatInput
from models.statbook import StatRow


class IncrementalSubsetExecutor:
    _canonical_stats_cache: ClassVar[dict | None] = None

    def __init__(self, registry: DependencyRegistry | None = None):
        self.registry = DependencyRegistry.load_default() if registry is None else registry

    @classmethod
    def _canonical_stats(cls) -> dict:
        if cls._canonical_stats_cache is None:
            cls._canonical_stats_cache = _load_canonical_stats()
        return cls._canonical_stats_cache

    def _closure_upstream(self, target_nodes: Iterable[str]) -> Set[str]:
        todo = list(target_nodes)
        seen: Set[str] = set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(self.registry.upstream.get(node, []))
        return seen

    def _serialized_contributors(self, contributors: List[StatInput], node: str):
        return [
            {
                'stat_name': contributor.stat_name,
                'source_family': contributor.source_family,
                'source_name': contributor.source_name,
                'value': contributor.value,
                'value_type': contributor.value_type,
                'stage': contributor.stage,
                'preset_name': contributor.preset_name,
                'provenance': contributor.provenance,
                'destination_object_type': contributor.destination_object_type,
                'destination_id': contributor.destination_id,
                'resolver_id': contributor.resolver_id,
                'kb_mapped': contributor.kb_mapped,
                'notes': contributor.notes,
            }
            for contributor in contributors
        ]

    def execute(self, stat_inputs: List[StatInput], target_nodes: Iterable[str]) -> Dict[str, StatRow]:
        selected = self._closure_upstream(target_nodes)
        order = self.registry.topo_publishable_subset(selected)
        selected_nodes = set(order)
        mapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)
        for row in stat_inputs:
            if not row.kb_mapped or not row.destination_id:
                continue
            node = f'{row.destination_object_type}::{row.destination_id}'
            if node in selected_nodes:
                mapped_buckets[node].append(row)

        canonical_stats = self._canonical_stats()
        rows: Dict[str, StatRow] = {}
        for node in order:
            contributors = mapped_buckets.get(node)
            if not contributors:
                continue
            destination_object_type, destination_id = node.split('::', 1)
            meta = dict(canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}))
            meta['_resolved_rows'] = rows
            final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
            rows[node] = StatRow(
                stat_name=node,
                final_value=final_value,
                value_type=meta['unit'],
                source_count=len(contributors),
                status=status,
                notes=notes,
                contributors=self._serialized_contributors(contributors, node),
                schema=schema,
            )
        _apply_phase3_postprocessing(rows)
        return {node: row for node, row in rows.items() if node in selected_nodes}
