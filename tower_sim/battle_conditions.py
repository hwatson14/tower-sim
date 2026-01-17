
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class BCRow:
    tier: str
    context: str  # "farm" or "tourney"
    name: str
    target: str
    op: str       # "override" | "add" | "mult"
    value: float
    units: str    # "mult" | "pp" | "pct" | "sec" | "abs"
    priority: int = 100

class BattleConditions:
    """
    Deterministic, unit-aware BC application at stat-key granularity.
    Apply order (per target):
      1) override (ascending priority)
      2) add (ascending priority)
      3) mult (ascending priority)
    """
    def __init__(self, rows: List[BCRow], strict_unknown: bool = True):
        self.rows = rows
        self.strict_unknown = strict_unknown

    def for_target(self, target: str) -> List[BCRow]:
        return [r for r in self.rows if r.target == target]

    def apply(self, target: str, base: float) -> float:
        rows = sorted(self.for_target(target), key=lambda r: (r.priority, r.op))
        overrides = [r for r in rows if r.op == "override"]
        adds = [r for r in rows if r.op == "add"]
        mults = [r for r in rows if r.op == "mult"]

        v = base
        for r in sorted(overrides, key=lambda x: x.priority):
            v = r.value
        for r in sorted(adds, key=lambda x: x.priority):
            v = v + r.value
        for r in sorted(mults, key=lambda x: x.priority):
            v = v * r.value
        return v

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def apply_skip_bc(p: float, mult: float = 1.0, sub: float = 0.0) -> float:
    """
    Skip BC convention in this codebase:
      p' = clamp(p * mult - sub, 0, 1)
    where p is fraction 0..1 and sub is also fraction 0..1.
    """
    return clamp(p * mult - sub, 0.0, 1.0)
