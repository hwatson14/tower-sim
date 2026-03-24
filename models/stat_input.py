from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class StatInput:
    stat_name: str
    source_family: str
    source_name: str
    value: Any
    value_type: str
    stage: str
    active: bool = True
    preset_name: Optional[str] = None
    provenance: Optional[str] = None
    notes: Optional[str] = None
    contributor_id: Optional[str] = None
    destination_object_type: Optional[str] = None
    destination_id: Optional[str] = None
    resolver_id: Optional[str] = None
    kb_mapped: bool = False
    raw_level: Optional[int] = None
    resolved_value: Optional[float] = None
    resolved_unit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
