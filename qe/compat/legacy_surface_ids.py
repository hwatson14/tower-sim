"""Legacy surface-id compatibility bridges quarantined from runtime owners."""

from __future__ import annotations

from qe.contracts import normalize_surface_id_to_contract, to_legacy_surface_id


def _surface_id(object_type: str, destination_id: str) -> str:
    return f'{object_type}::{destination_id}'


def legacy_canonical_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('canonical_stat', destination_id))


def legacy_mechanic_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('mechanic_param', destination_id))


def legacy_runtime_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('runtime_mechanic_param', destination_id))


def legacy_flag_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('account_flag', destination_id))


def legacy_context_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('account_context', destination_id))


def legacy_capability_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('capability', destination_id))


def legacy_cosmetic_surface_id(destination_id: str) -> str:
    return normalize_surface_id_to_contract(_surface_id('cosmetic_bonus', destination_id))


def legacy_surface_id(surface_id: str) -> str:
    return to_legacy_surface_id(surface_id)


def surface_id_candidates(surface_id: str) -> tuple[str, ...]:
    normalized = normalize_surface_id_to_contract(surface_id)
    legacy = legacy_surface_id(normalized)
    ordered: list[str] = []
    for candidate in (normalized, legacy, surface_id):
        if candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)
