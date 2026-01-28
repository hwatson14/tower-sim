from __future__ import annotations

from dataclasses import dataclass

from tower_sim.perks_gate import assert_perks_enabled


@dataclass(frozen=True)
class RunContext:
    mode: str
    perks_enabled: bool

    @classmethod
    def from_mode(cls, mode: str) -> "RunContext":
        normalized = mode.strip().lower()
        if normalized in {"tourney", "tournament"}:
            return cls(mode="tournament", perks_enabled=False)
        if normalized in {"tier", "farming", "milestone"}:
            return cls(mode=normalized, perks_enabled=True)
        raise ValueError(f"Unknown run mode: {mode!r}")

    def require_perks_enabled(self) -> None:
        assert_perks_enabled({"perks_enabled": self.perks_enabled})
