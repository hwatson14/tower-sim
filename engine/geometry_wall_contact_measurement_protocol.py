from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

PROTOCOL_VERSION = "wall_contact_measurement_protocol_v1"


@dataclass(frozen=True)
class MeasurementRule:
    rule_id: str
    description: str
    required: bool = True


def build_wall_contact_measurement_protocol() -> Dict[str, Any]:
    rules: List[MeasurementRule] = [
        MeasurementRule(
            rule_id="contact_event_definition",
            description=(
                "Define boss-to-wall contact as the first frame where wall HP first decreases. "
                "Use visual fallback only when HP change is unreadable."
            ),
        ),
        MeasurementRule(
            rule_id="timestamping",
            description="Record both frame index and seconds when possible; frame is preferred when available.",
        ),
        MeasurementRule(
            rule_id="runtime_capture",
            description=(
                "Capture tower_range_theoretical_m, tower_range_displayed_m, wall_radius_displayed_m, "
                "and boss_speed_runtime_surface for each observation."
            ),
        ),
        MeasurementRule(
            rule_id="version_scope",
            description="Record game/build version or date band for every observation.",
        ),
    ]
    return {
        "protocol_id": PROTOCOL_VERSION,
        "status": "measurement_ready",
        "rules": [asdict(r) for r in rules],
        "sample_row_template": {
            "sample_id": "",
            "measurement_version_scope": "",
            "tower_range_theoretical_m": None,
            "tower_range_displayed_m": None,
            "wall_radius_displayed_m": None,
            "boss_speed_runtime_surface": None,
            "boss_contact_event_frame": None,
            "boss_contact_event_seconds": None,
            "contact_event_definition": "wall_hp_first_decrease",
            "tier": None,
            "boss_type": None,
            "heat_profile": None,
            "video_frame_rate_fps": None,
            "notes": "",
        },
        "minimum_dataset_gate": {
            "min_distinct_tower_ranges": 6,
            "must_include_post_80_display_compression": True,
            "must_include_contact_definition": True,
            "must_include_version_scope": True,
        },
    }
