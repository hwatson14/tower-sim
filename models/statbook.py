from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class StatRow:
    stat_name: str
    final_value: Any
    value_type: str
    source_count: int
    status: str = 'unresolved'
    notes: Optional[str] = None
    contributors: List[Dict[str, Any]] = field(default_factory=list)
    schema: Dict[str, Any] | None = None


@dataclass
class StatBook:
    rows: Dict[str, StatRow]
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rows': {k: asdict(v) for k, v in self.rows.items()},
            'diagnostics': self.diagnostics,
        }
