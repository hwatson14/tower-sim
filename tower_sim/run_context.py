from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RunType(str, Enum):
    FARMING = "farming"
    TOURNAMENT = "tournament"


@dataclass(frozen=True)
class RunContext:
    tier: str
    run_type: RunType
    perks_enabled: bool

    @classmethod
    def from_mode(cls, mode: str, tier: str | None = None) -> "RunContext":
        resolved_tier = tier or mode
        if mode == "tier":
            return cls.farming(resolved_tier)
        if mode == RunType.FARMING.value:
            return cls.farming(resolved_tier)
        if mode == RunType.TOURNAMENT.value:
            return cls.tournament(resolved_tier)
        raise ValueError(f"Unsupported run mode: {mode}")

    @classmethod
    def farming(cls, tier: str, perks_enabled: bool | None = None) -> "RunContext":
        resolved = True if perks_enabled is None else perks_enabled
        return cls(tier=tier, run_type=RunType.FARMING, perks_enabled=resolved)

    @classmethod
    def tournament(cls, tier: str, perks_enabled: bool | None = None) -> "RunContext":
        resolved = False if perks_enabled is None else perks_enabled
        return cls(tier=tier, run_type=RunType.TOURNAMENT, perks_enabled=resolved)


class PerksDisabledError(RuntimeError):
    pass


def assert_perks_enabled(context: RunContext) -> None:
    if context is None:
        raise PerksDisabledError("RunContext missing (fail-closed)")
    if not context.perks_enabled:
        raise PerksDisabledError(
            f"Perks are disabled for run_type={context.run_type.value} tier={context.tier}."
        )
