from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase


@dataclass(frozen=True)
class SkipRampSpec:
    start: float
    end: float
    ramp_waves: int = 1000


@dataclass(frozen=True)
class StatInputSpec:
    stat_id: str
    phase: Phase
    base_value: Optional[float] = None
    loadout_delta: Optional[float] = None
    enhancement_multiplier: Optional[float] = None
    tier_rule_delta: Optional[float] = None
    tier_rule_multiplier: Optional[float] = None
    derived_value: Optional[float] = None
    provenance: Optional[str] = None

    def to_stat_input(self) -> StatInput:
        return StatInput(
            stat_id=self.stat_id,
            phase=self.phase,
            base_value=self.base_value,
            loadout_delta=self.loadout_delta,
            enhancement_multiplier=self.enhancement_multiplier,
            tier_rule_delta=self.tier_rule_delta,
            tier_rule_multiplier=self.tier_rule_multiplier,
            derived_value=self.derived_value,
            provenance=self.provenance,
        )


@dataclass(frozen=True)
class BossStatsSpec:
    hp: float
    attack: float
    attack_interval: float
    enrage_mult: float


@dataclass(frozen=True)
class TowerDefenseSpec:
    dr_frac: float
    regen_per_sec: float
    shields: float


@dataclass(frozen=True)
class BossSurvivabilitySpec:
    boss: BossStatsSpec
    tower: TowerDefenseSpec
    combat_params: Dict[str, Any]
    bc_params: Dict[str, Any]


@dataclass(frozen=True)
class ScenarioSpec:
    mode: str
    tier: int
    league: Optional[str] = None
    wave: int = 1
    wave_damage_tier: Optional[str] = None
    eals_ramp: Optional[SkipRampSpec] = None
    ehls_ramp: Optional[SkipRampSpec] = None
    boss_survivability: Optional[BossSurvivabilitySpec] = None
    perk_timeline_path: Optional[str] = None
    allow_core_stat_overrides: bool = False



@dataclass(frozen=True)
class ProblemSpec:
    scenario: ScenarioSpec
    stat_inputs: List[StatInputSpec]
    evaluator: str = "max_wave"
