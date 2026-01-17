from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Set


class UnknownStatError(KeyError):
    pass


class Unit(str, Enum):
    COUNT = "count"
    PERCENT = "percent"
    PERCENT_POINTS = "percent_points"
    MULTIPLIER = "multiplier"
    HP = "hp"
    HP_PER_S = "hp_per_s"
    SECONDS = "seconds"
    WAVES = "waves"
    NONE = "none"


class StatKind(str, Enum):
    BASE = "base"
    DELTA_ADD = "delta_add"
    DELTA_MULT = "delta_mult"
    CAP = "cap"
    DERIVED = "derived"


class StatScope(str, Enum):
    TOWER = "tower"
    WALL = "wall"
    ENEMY = "enemy"
    BOSS = "boss"
    RUN = "run"


class Phase(str, Enum):
    START_OF_RUN = "start_of_run"
    END_OF_RUN = "end_of_run"
    AT_WAVE = "at_wave"


@dataclass(frozen=True)
class StatDef:
    stat_id: str
    display_name: str
    unit: Unit
    kind: StatKind
    scope: StatScope
    allowed_phases: Set[Phase]
    description: Optional[str] = None


class StatRegistry:
    def __init__(self, definitions: Iterable[StatDef]):
        self._defs: Dict[str, StatDef] = {}
        for definition in definitions:
            if definition.stat_id in self._defs:
                raise ValueError(f"Duplicate stat_id in registry: {definition.stat_id}")
            self._defs[definition.stat_id] = definition

    def get(self, stat_id: str) -> StatDef:
        if stat_id not in self._defs:
            raise UnknownStatError(f"Unknown stat_id: {stat_id}")
        return self._defs[stat_id]

    def validate_stat_id(self, stat_id: str) -> None:
        if stat_id not in self._defs:
            raise UnknownStatError(f"Unknown stat_id: {stat_id}")

    def all_defs(self) -> List[StatDef]:
        return sorted(self._defs.values(), key=lambda item: item.stat_id)


def default_registry() -> StatRegistry:
    defs: Sequence[StatDef] = [
        StatDef(
            stat_id="tower_hp",
            display_name="Health",
            unit=Unit.HP,
            kind=StatKind.BASE,
            scope=StatScope.TOWER,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Tower health (base value).",
        ),
        StatDef(
            stat_id="tower_regen",
            display_name="Health Regen",
            unit=Unit.HP_PER_S,
            kind=StatKind.BASE,
            scope=StatScope.TOWER,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Tower regen rate (base value).",
        ),
        StatDef(
            stat_id="def_pct",
            display_name="Defense %",
            unit=Unit.PERCENT,
            kind=StatKind.BASE,
            scope=StatScope.TOWER,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Defense percent (base value).",
        ),
        StatDef(
            stat_id="wall_hp",
            display_name="Wall Health",
            unit=Unit.HP,
            kind=StatKind.BASE,
            scope=StatScope.WALL,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Wall health (base value).",
        ),
        StatDef(
            stat_id="wall_regen",
            display_name="Wall Regen",
            unit=Unit.HP_PER_S,
            kind=StatKind.BASE,
            scope=StatScope.WALL,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Wall regen rate (base value).",
        ),
        StatDef(
            stat_id="eals_pct",
            display_name="Enemy Attack Level Skip",
            unit=Unit.PERCENT,
            kind=StatKind.DERIVED,
            scope=StatScope.RUN,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Enemy attack level skip percent (placeholder).",
        ),
        StatDef(
            stat_id="ehls_pct",
            display_name="Enemy Health Level Skip",
            unit=Unit.PERCENT,
            kind=StatKind.DERIVED,
            scope=StatScope.RUN,
            allowed_phases={Phase.START_OF_RUN, Phase.END_OF_RUN},
            description="Enemy health level skip percent (placeholder).",
        ),
        StatDef(
            stat_id="wave_attack_index",
            display_name="Wave Attack Index",
            unit=Unit.WAVES,
            kind=StatKind.DERIVED,
            scope=StatScope.RUN,
            allowed_phases={Phase.AT_WAVE},
            description="Derived attack wave index (placeholder).",
        ),
        StatDef(
            stat_id="wave_health_index",
            display_name="Wave Health Index",
            unit=Unit.WAVES,
            kind=StatKind.DERIVED,
            scope=StatScope.RUN,
            allowed_phases={Phase.AT_WAVE},
            description="Derived health wave index (placeholder).",
        ),
    ]
    return StatRegistry(defs)
