from __future__ import annotations

from typing import Any, Dict, Iterable, List

CANONICAL_TARGET_SURFACE = "wall_contact_observed_contact_proxy_seconds"
LEGACY_TARGET_ALIASES = {
    "measured_effective_wall_contact_radius_m": CANONICAL_TARGET_SURFACE,
    "boss_contact_event_seconds_normalized": CANONICAL_TARGET_SURFACE,
    "wall_contact_observed_contact_seconds": CANONICAL_TARGET_SURFACE,
}


def _copy_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return dict(row) if isinstance(row, dict) else {"value": row}


def unify_wall_contact_target_surface(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_rows: List[Dict[str, Any]] = []
    aliases_consumed: List[str] = []
    warnings: List[str] = []
    missing_count = 0
    for row in rows:
        out = _copy_row(row)
        if CANONICAL_TARGET_SURFACE not in out:
            matched = None
            for old, new in LEGACY_TARGET_ALIASES.items():
                if old in out:
                    out[new] = out[old]
                    matched = old
                    aliases_consumed.append(old)
                    warnings.append(f"Mapped legacy target surface '{old}' to canonical '{new}'.")
                    break
            if matched is None:
                missing_count += 1
                warnings.append("Row missing canonical target surface and no known legacy alias was found.")
        normalized_rows.append(out)
    return {
        "status": "target_surface_unified__promotion_blocked",
        "canonical_target_surface": CANONICAL_TARGET_SURFACE,
        "legacy_aliases": LEGACY_TARGET_ALIASES,
        "aliases_consumed": sorted(set(aliases_consumed)),
        "warnings": warnings,
        "missing_target_rows": missing_count,
        "rows": normalized_rows,
    }
