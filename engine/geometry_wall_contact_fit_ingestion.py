from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from engine.geometry_wall_contact_measurement_protocol import build_wall_contact_measurement_protocol
from engine.geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE, unify_wall_contact_target_surface

FIT_INGESTION_VERSION = "wall_contact_fit_ingestion_scaffold_v2"
REQUIRED_FIELDS = [
    "measurement_version_scope",
    "tower_range_theoretical_m",
    "tower_range_displayed_m",
    "wall_radius_displayed_m",
    "boss_speed_runtime_surface",
    "contact_event_definition",
]
ALLOWED_CONTACT_DEFINITIONS = {"wall_hp_first_decrease", "visual_wall_contact_fallback"}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    row_index: Optional[int] = None
    sample_id: Optional[str] = None


def load_wall_contact_measurement_rows(path: str | Path) -> List[Dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        payload = json.loads(p.read_text())
        rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("JSON measurement payload must be a list or {'rows': [...]}.")
        return [dict(r) for r in rows]
    if p.suffix.lower() == ".csv":
        with p.open(newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    raise ValueError("Unsupported measurement file type. Use .json or .csv")


def _coerce_float(v: Any) -> Optional[float]:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_int(v: Any) -> Optional[int]:
    if v in (None, "", "None"):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def validate_wall_contact_measurement_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    protocol = build_wall_contact_measurement_protocol()
    unified = unify_wall_contact_target_surface(rows)
    issues: List[ValidationIssue] = []
    valid_rows: List[Dict[str, Any]] = []

    for idx, raw in enumerate(unified["rows"]):
        row = dict(raw)
        sample_id = row.get("sample_id") or f"row_{idx}"

        for field in REQUIRED_FIELDS:
            if row.get(field) in (None, "", "None"):
                issues.append(ValidationIssue("error", "missing_required_field", f"Missing required field: {field}", idx, sample_id))

        frame = _coerce_int(row.get("boss_contact_event_frame"))
        secs = _coerce_float(row.get("boss_contact_event_seconds"))
        if frame is None and secs is None and _coerce_float(row.get(CANONICAL_TARGET_SURFACE)) is None:
            issues.append(ValidationIssue("error", "missing_contact_timestamp", "At least one timestamp or canonical target surface is required.", idx, sample_id))

        definition = row.get("contact_event_definition")
        if definition not in ALLOWED_CONTACT_DEFINITIONS:
            issues.append(ValidationIssue("warning", "unknown_contact_definition", f"Unexpected contact_event_definition: {definition}", idx, sample_id))

        for numeric_field in ["tower_range_theoretical_m", "tower_range_displayed_m", "wall_radius_displayed_m", "boss_speed_runtime_surface"]:
            value = _coerce_float(row.get(numeric_field))
            if value is None or value <= 0:
                issues.append(ValidationIssue("error", "invalid_numeric_surface", f"Field {numeric_field} must be positive numeric.", idx, sample_id))

        fps = _coerce_float(row.get("video_frame_rate_fps"))
        if fps is not None and fps <= 0:
            issues.append(ValidationIssue("warning", "invalid_fps", "video_frame_rate_fps should be positive when provided.", idx, sample_id))

        target_secs = _coerce_float(row.get(CANONICAL_TARGET_SURFACE))
        if target_secs is None:
            if secs is not None:
                target_secs = secs
            elif frame is not None and fps and fps > 0:
                target_secs = frame / fps

        row[CANONICAL_TARGET_SURFACE] = target_secs
        row["boss_contact_event_seconds_normalized"] = target_secs
        row["boss_contact_event_frame_normalized"] = frame

        row_errors = [i for i in issues if i.row_index == idx and i.severity == "error"]
        if not row_errors:
            valid_rows.append(row)

    distinct_theoretical = sorted({float(r["tower_range_theoretical_m"]) for r in valid_rows})
    has_post_80 = any(v > 80.0 for v in distinct_theoretical)
    gate = protocol["minimum_dataset_gate"]

    if not valid_rows:
        readiness = "insufficient"
    elif len(distinct_theoretical) < gate["min_distinct_tower_ranges"] or not has_post_80:
        readiness = "measurement_ready"
    else:
        readiness = "fit_ready"

    issue_counts = Counter((i.severity, i.code) for i in issues)
    return {
        "status": "measurement_rows_validated__promotion_blocked",
        "protocol_id": protocol["protocol_id"],
        "canonical_target_surface": CANONICAL_TARGET_SURFACE,
        "valid_rows": valid_rows,
        "issues": [asdict(i) for i in issues],
        "issue_counts": {f"{sev}:{code}": n for (sev, code), n in sorted(issue_counts.items())},
        "readiness": {
            "status": readiness,
            "distinct_tower_ranges": len(distinct_theoretical),
            "has_post_80_theoretical_range": has_post_80,
        },
        "target_surface_unification": {
            "aliases_consumed": unified["aliases_consumed"],
            "missing_target_rows": unified["missing_target_rows"],
            "warnings": unified["warnings"],
        },
    }


def build_wall_contact_fit_ingestion_scaffold(path: str | Path) -> Dict[str, Any]:
    rows = load_wall_contact_measurement_rows(path)
    validation = validate_wall_contact_measurement_rows(rows)
    return {
        "status": "fit_ingestion_built__promotion_blocked",
        "version": FIT_INGESTION_VERSION,
        "input_path": str(path),
        **validation,
    }
