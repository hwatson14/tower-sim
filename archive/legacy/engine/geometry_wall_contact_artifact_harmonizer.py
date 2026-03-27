from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE, LEGACY_TARGET_ALIASES

FIT_PATH_ARTIFACT_ORDER = ["ingestion", "fit_harness"]


def _canonicalize_surface_name(value: Any) -> Tuple[Any, bool]:
    if not isinstance(value, str):
        return value, False
    if value == CANONICAL_TARGET_SURFACE:
        return value, False
    if value in LEGACY_TARGET_ALIASES:
        return CANONICAL_TARGET_SURFACE, True
    return value, False


def _normalize_dict(obj: Dict[str, Any], touched: List[str], path: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in obj.items():
        cur_path = f"{path}.{key}" if path else key
        new_key = CANONICAL_TARGET_SURFACE if key in LEGACY_TARGET_ALIASES else key
        if new_key != key:
            touched.append(cur_path)
        if isinstance(value, dict):
            out[new_key] = _normalize_dict(value, touched, cur_path)
        elif isinstance(value, list):
            out[new_key] = _normalize_list(value, touched, cur_path)
        else:
            new_value, changed = _canonicalize_surface_name(value)
            if changed:
                touched.append(cur_path)
            out[new_key] = new_value
    return out


def _normalize_list(items: List[Any], touched: List[str], path: str) -> List[Any]:
    out: List[Any] = []
    for idx, item in enumerate(items):
        cur_path = f"{path}[{idx}]"
        if isinstance(item, dict):
            out.append(_normalize_dict(item, touched, cur_path))
        elif isinstance(item, list):
            out.append(_normalize_list(item, touched, cur_path))
        else:
            new_value, changed = _canonicalize_surface_name(item)
            if changed:
                touched.append(cur_path)
            out.append(new_value)
    return out


def harmonize_wall_contact_fit_path_artifacts(artifacts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    harmonized: Dict[str, Dict[str, Any]] = {}
    touched: List[str] = []
    warnings: List[str] = []
    for stage_name, payload in artifacts.items():
        harmonized[stage_name] = _normalize_dict(payload, touched, stage_name) if isinstance(payload, dict) else {"value": payload}
    missing_stages = [s for s in FIT_PATH_ARTIFACT_ORDER if s not in harmonized]
    if missing_stages:
        warnings.append("Missing fit-path stages: " + ", ".join(missing_stages))
    return {
        "status": "fit_path_artifacts_harmonized__promotion_blocked",
        "canonical_target_surface": CANONICAL_TARGET_SURFACE,
        "artifact_order": FIT_PATH_ARTIFACT_ORDER,
        "touched_paths": sorted(set(touched)),
        "warnings": warnings,
        "harmonized_artifacts": harmonized,
    }
