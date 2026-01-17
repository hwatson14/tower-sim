from __future__ import annotations

from collections.abc import Iterable

from tower_sim.stat_engine import StatEngine, StatInput
from tower_sim.stat_registry import Phase, StatRegistry
from tower_sim.statbook import StatBook


PHASE_START = Phase.START_OF_RUN
PHASE_END = Phase.END_OF_RUN


def build_statbook(inputs: Iterable[StatInput], registry: StatRegistry) -> StatBook:
    engine = StatEngine(registry=registry)
    return engine.build(inputs).statbook
