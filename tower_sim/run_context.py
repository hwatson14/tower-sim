from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RunType(str, Enum):
    TIER = "tier"
    TOURNAMENT = "tournament"


@dataclass(frozen=True)
class RunContext:
    tier: str
    run_type: RunType
    perks_enabled: bool | None = None

    def __post_init__(self) -> None:
        if self.perks_enabled is None:
            default = self.run_type == RunType.TIER
            object.__setattr__(self, "perks_enabled", default)

    @classmethod
    def for_tier(cls, tier: str, perks_enabled: bool | None = None) -> "RunContext":
        return cls(tier=tier, run_type=RunType.TIER, perks_enabled=perks_enabled)

    @classmethod
    def tournament(cls, tier: str, perks_enabled: bool | None = None) -> "RunContext":
        return cls(tier=tier, run_type=RunType.TOURNAMENT, perks_enabled=perks_enabled)


def assert_perks_enabled(context: RunContext) -> None:
    if not context.perks_enabled:
        raise ValueError(
            f"Perks are disabled for run_type={context.run_type.value} tier={context.tier}."
        )
