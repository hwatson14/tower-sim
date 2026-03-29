"""
qe/shared_runtime_context.py -- Shared QE runtime context.

Owns: one-process shared runtime context for immutable QE/compiler runtime state:
  - compiler routing indexes
  - consumer bundle definitions
  - materializer family metadata
  - dependency registry
  - shared query kernel

This is a shared-runtime owner only. It must not own query execution logic,
simulation logic, or app orchestration.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from qe.consumer_registry import load_consumer_bundle_definitions
from qe.dependency_registry import DependencyRegistry
from qe.kernel import StatQueryKernel, get_default_query_kernel
from qe.materializer import (
    load_family_contracts,
    load_family_surface_ids,
    load_surface_metadata_by_id,
)
from qe.query_routing import compiler_routing_indexes


@dataclass(frozen=True)
class QESharedRuntimeContext:
    """Shared immutable QE runtime context for one-process warm starts."""

    query_kernel: StatQueryKernel
    dependency_registry: DependencyRegistry
    consumer_bundle_count: int
    family_surface_count: int
    family_contract_count: int
    surface_metadata_count: int
    compiler_mapping_count: int
    compiler_alias_count: int
    compiler_relic_count: int
    compiler_family_slug_count: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            'context_kind': 'qe_shared_runtime_context',
            'consumer_bundle_count': self.consumer_bundle_count,
            'family_surface_count': self.family_surface_count,
            'family_contract_count': self.family_contract_count,
            'surface_metadata_count': self.surface_metadata_count,
            'compiler_mapping_count': self.compiler_mapping_count,
            'compiler_alias_count': self.compiler_alias_count,
            'compiler_relic_count': self.compiler_relic_count,
            'compiler_family_slug_count': self.compiler_family_slug_count,
        }


@lru_cache(maxsize=1)
def get_default_qe_shared_runtime_context() -> QESharedRuntimeContext:
    """
    Build and cache the shared QE runtime context for the current process.

    This intentionally prewarms the high-cost immutable caches that bounded
    query consumers reuse across requests.
    """
    mapping_index, _canonical_stats, alias_index, relic_index, family_slug_index = compiler_routing_indexes()
    consumer_bundles = load_consumer_bundle_definitions()
    family_surface_ids = load_family_surface_ids()
    family_contracts = load_family_contracts()
    surface_metadata = load_surface_metadata_by_id()
    dependency_registry = DependencyRegistry.load_default()
    query_kernel = get_default_query_kernel()
    return QESharedRuntimeContext(
        query_kernel=query_kernel,
        dependency_registry=dependency_registry,
        consumer_bundle_count=len(consumer_bundles),
        family_surface_count=sum(len(surface_ids) for surface_ids in family_surface_ids.values()),
        family_contract_count=len(family_contracts),
        surface_metadata_count=len(surface_metadata),
        compiler_mapping_count=len(mapping_index),
        compiler_alias_count=len(alias_index),
        compiler_relic_count=len(relic_index),
        compiler_family_slug_count=len(family_slug_index),
    )
