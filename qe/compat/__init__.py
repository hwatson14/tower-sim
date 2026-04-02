"""Compatibility quarantine surface for legacy surface-id translation helpers."""

from .legacy_surface_ids import (
    legacy_capability_surface_id,
    legacy_canonical_surface_id,
    legacy_context_surface_id,
    legacy_cosmetic_surface_id,
    legacy_flag_surface_id,
    legacy_mechanic_surface_id,
    legacy_runtime_surface_id,
    legacy_surface_id,
    surface_id_candidates,
)

__all__ = [
    'legacy_capability_surface_id',
    'legacy_canonical_surface_id',
    'legacy_context_surface_id',
    'legacy_cosmetic_surface_id',
    'legacy_flag_surface_id',
    'legacy_mechanic_surface_id',
    'legacy_runtime_surface_id',
    'legacy_surface_id',
    'surface_id_candidates',
]
