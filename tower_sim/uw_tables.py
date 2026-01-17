
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class UWLevels:
    a: int
    b: int
    c: int
    plus: int = 0

class UWTableError(RuntimeError):
    pass

class UWRegistry:
    """
    Stores per-UW per-track lookup tables (loaded from your snapshot CSVs).
    No hardcoded numeric values allowed here.
    """
    def __init__(self):
        self.tables: Dict[str, Any] = {}

    def register(self, uw_name: str, table: Any) -> None:
        self.tables[uw_name] = table

    def get(self, uw_name: str) -> Any:
        if uw_name not in self.tables:
            raise UWTableError(f"UW table not registered for: {uw_name}")
        return self.tables[uw_name]
