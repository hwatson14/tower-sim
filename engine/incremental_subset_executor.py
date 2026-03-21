from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, Sequence

from engine.dependency_registry import DependencyRegistry
from engine.stat_engine import _apply_phase3_postprocessing, _load_canonical_stats, _resolve_bucket
from models.stat_input import StatInput
from models.statbook import StatRow

_NODE_TO_BUCKET = {
    'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier',
    'support_surface::timing.gcomp_cooldown_reduction_seconds': 'mechanic_param::module.galaxy_compressor.uw_cooldown_reduction_seconds',
}

_ALIAS_OUTPUTS = {
    'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier',
}


class IncrementalSubsetExecutor:
    def __init__(self, registry: DependencyRegistry | None = None) -> None:
        self._registry = DependencyRegistry.load_default() if registry is None else registry
        self._canonical_stats = _load_canonical_stats()

    def execute(
        self,
        stat_inputs: List[StatInput],
        target_nodes: Iterable[str],
        *,
        family_id: str | None = None,
        scenario_mode_id: str | None = None,
    ) -> Dict[str, StatRow]:
        requested_nodes = [self._normalize_target(node) for node in target_nodes]
        if not requested_nodes:
            return {}
        self._assert_supported_targets(requested_nodes, family_id=family_id)

        closure_nodes = self._publishable_closure(requested_nodes, family_id=family_id)
        bucket_rows = self._resolve_bucket_rows(
            stat_inputs,
            closure_nodes,
            family_id=family_id,
            scenario_mode_id=scenario_mode_id,
        )

        resolved: Dict[str, StatRow] = {}
        for node in closure_nodes:
            bucket_key = self._bucket_key_for_node(node)
            row = bucket_rows.get(bucket_key) or bucket_rows.get(node)
            if row is None:
                raise ValueError(f'Unsupported bounded query target nodes: {node!r}')
            resolved[node] = row
            alias_output = _ALIAS_OUTPUTS.get(node)
            if alias_output is not None:
                resolved[alias_output] = row
        return resolved

    @staticmethod
    def _normalize_target(node: str) -> str:
        return str(node)

    def _assert_supported_targets(self, requested_nodes: Sequence[str], *, family_id: str | None) -> None:
        unknown = [node for node in requested_nodes if self._registry.node(node) is None]
        if unknown:
            raise ValueError(f'Unsupported bounded query target nodes: {sorted(unknown)!r}')
        if family_id is None:
            return
        outside_family = [node for node in requested_nodes if family_id not in self._registry.node(node).family_ids]
        if outside_family:
            raise ValueError(f'Bounded executor family {family_id!r} does not own requested nodes {sorted(outside_family)!r}.')

    def _publishable_closure(self, requested_nodes: Sequence[str], *, family_id: str | None) -> list[str]:
        closure = self._registry.closure_upstream(requested_nodes)
        publishable = self._registry.topo_publishable_subset(closure)
        ordered = list(publishable)
        for node in requested_nodes:
            if node not in ordered:
                ordered.append(node)
        if family_id is None:
            return ordered
        illegal = [node for node in ordered if family_id not in self._registry.node(node).family_ids]
        if illegal:
            raise ValueError(f'Bounded executor family {family_id!r} closure crossed into undeclared nodes {sorted(illegal)!r}.')
        return ordered

    def _resolve_bucket_rows(
        self,
        stat_inputs: Sequence[StatInput],
        closure_nodes: Sequence[str],
        *,
        family_id: str | None,
        scenario_mode_id: str | None,
    ) -> Dict[str, StatRow]:
        mapped_buckets: Dict[str, List[StatInput]] = defaultdict(list)
        required_bucket_keys = {self._bucket_key_for_node(node) for node in closure_nodes}
        for row in self._augment_stat_inputs(stat_inputs, closure_nodes, family_id=family_id, scenario_mode_id=scenario_mode_id):
            if not row.kb_mapped or not row.destination_id:
                continue
            bucket_key = f'{row.destination_object_type}::{row.destination_id}'
            if bucket_key in required_bucket_keys:
                mapped_buckets[bucket_key].append(row)

        rows: Dict[str, StatRow] = {}
        for bucket_key in self._bucket_resolution_order(closure_nodes):
            contributors = mapped_buckets.get(bucket_key)
            if not contributors:
                continue
            if bucket_key == 'support_surface::timing.wave_duration_seconds_effective':
                contributor = contributors[0]
                rows[bucket_key] = StatRow(
                    stat_name=bucket_key,
                    final_value=float(contributor.value),
                    value_type='seconds',
                    source_count=len(contributors),
                    status='resolved',
                    notes='Derived timing wave-duration support surface from family-governed baseline and bounded wave-acceleration input.',
                    contributors=[c.to_dict() for c in contributors],
                    schema={'unit': 'seconds', 'resolver': 'bounded_timing_wave_duration_support'},
                )
                continue
            destination_object_type, destination_id = bucket_key.split('::', 1)
            meta = self._canonical_stats.get(destination_id, {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'})
            if destination_object_type != 'canonical_stat' and meta.get('unit') == 'unknown':
                meta = {'unit': 'unknown', 'resolver': contributors[0].resolver_id or 'unknown'}
            meta = dict(meta)
            meta['_resolved_rows'] = rows
            final_value, status, notes, schema = _resolve_bucket(destination_object_type, destination_id, contributors, meta)
            rows[bucket_key] = StatRow(
                stat_name=bucket_key,
                final_value=final_value,
                value_type=meta['unit'],
                source_count=len(contributors),
                status=status,
                notes=notes,
                contributors=[c.to_dict() for c in contributors],
                schema=schema,
            )

        _apply_phase3_postprocessing(rows)

        missing = sorted(
            node
            for node in closure_nodes
            if self._bucket_key_for_node(node) not in rows and node not in rows
        )
        if missing:
            raise ValueError(f'No native bounded resolver path is available for {missing}.')
        return rows

    def _bucket_resolution_order(self, closure_nodes: Sequence[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for node in closure_nodes:
            bucket_key = self._bucket_key_for_node(node)
            if bucket_key in seen:
                continue
            seen.add(bucket_key)
            ordered.append(bucket_key)
        return ordered

    def _augment_stat_inputs(
        self,
        stat_inputs: Sequence[StatInput],
        closure_nodes: Sequence[str],
        *,
        family_id: str | None,
        scenario_mode_id: str | None,
    ) -> list[StatInput]:
        rows = list(stat_inputs)
        if 'support_surface::timing.wave_duration_seconds_effective' in closure_nodes:
            rows.append(
                self._derive_wave_duration_input(
                    stat_inputs,
                    family_id=family_id,
                    scenario_mode_id=scenario_mode_id,
                )
            )
        return rows

    def _derive_wave_duration_input(
        self,
        stat_inputs: Sequence[StatInput],
        *,
        family_id: str | None,
        scenario_mode_id: str | None,
    ) -> StatInput:
        from engine.timing_engine import _load_wave_timing_baselines

        inferred_mode_id = scenario_mode_id
        if inferred_mode_id is None:
            inferred_mode_id = {
                'timing_tournament_no_perks': 'tournament',
                'timing_farm_with_perks': 'farming',
            }.get(str(family_id))
        if inferred_mode_id not in {'tournament', 'farming'}:
            raise ValueError(
                'support_surface::timing.wave_duration_seconds_effective requires scenario_mode_id '
                'for native bounded resolution when family_id does not imply tournament/farming.'
            )
        base_wave_duration_seconds = _load_wave_timing_baselines()[str(inferred_mode_id)]
        wave_acceleration_pct = 0.0
        for row in stat_inputs:
            if row.destination_object_type == 'runtime_mechanic_param' and row.destination_id == 'cards.wave_accelerator.spawn_rate_acceleration' and row.active:
                try:
                    wave_acceleration_pct = float(row.value)
                except (TypeError, ValueError):
                    wave_acceleration_pct = 0.0
                break
        effective_wave_duration_seconds = max(0.0, base_wave_duration_seconds * (1.0 - (max(0.0, wave_acceleration_pct) / 100.0)))
        return StatInput(
            stat_name='Wave Duration Effective',
            source_family='scenario_rules',
            source_name='Wave Accelerator',
            value=effective_wave_duration_seconds,
            value_type='seconds',
            stage='scenario_runtime',
            active=True,
            contributor_id='timing.wave_duration_seconds_effective',
            provenance='engine.incremental_subset_executor.derive_wave_duration',
            destination_object_type='support_surface',
            destination_id='timing.wave_duration_seconds_effective',
            kb_mapped=True,
        )

    @staticmethod
    def _bucket_key_for_node(node: str) -> str:
        return _NODE_TO_BUCKET.get(node, node)
