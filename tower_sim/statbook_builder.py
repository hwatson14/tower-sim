from __future__ import annotations

from tower_sim.ids_state import IdsState
from tower_sim.stat_registry import Phase, StatRegistry, default_registry
from tower_sim.statbook import StatBook, StatRow


PHASE_START = Phase.START_OF_RUN
PHASE_END = Phase.END_OF_RUN


STAT_SOURCES = {
    "tower_hp": ("workshop", "Health"),
    "tower_regen": ("workshop", "Health Regen"),
    "def_pct": ("workshop", "Defense %"),
    "wall_hp": ("workshop", "Wall Health"),
    "wall_regen": ("labs", "Wall Regen"),
    "eals_pct": ("labs", "Enemy Attack Level Skip"),
    "ehls_pct": ("labs", "Enemy Health Level Skip"),
}


def build_statbook(ids_state: IdsState, registry: StatRegistry | None = None) -> StatBook:
    rows: list[StatRow] = []
    active_registry = registry or default_registry()
    for stat_id, (source, key) in STAT_SOURCES.items():
        if source == "workshop":
            if key not in ids_state.workshop.entries:
                raise KeyError(f"Missing workshop entry for {stat_id}: {key}")
            entry = ids_state.workshop.entries[key]
            rows.append(
                StatRow(
                    stat_id=stat_id,
                    phase=PHASE_START,
                    value=entry.coin_level,
                    source="workshop",
                )
            )
            rows.append(
                StatRow(
                    stat_id=stat_id,
                    phase=PHASE_END,
                    value=entry.max_level or entry.coin_level,
                    source="workshop",
                    notes="Uses raw max level when present; otherwise coin level.",
                )
            )
            continue
        if source == "labs":
            if key not in ids_state.labs.labs:
                raise KeyError(f"Missing lab entry for {stat_id}: {key}")
            value = ids_state.labs.labs[key]
            rows.append(
                StatRow(
                    stat_id=stat_id,
                    phase=PHASE_START,
                    value=value,
                    source="labs",
                )
            )
            rows.append(
                StatRow(
                    stat_id=stat_id,
                    phase=PHASE_END,
                    value=value,
                    source="labs",
                    notes="Raw lab level duplicated for end-of-run placeholder.",
                )
            )
            continue
        raise KeyError(f"Unknown stat source: {source}")
    return StatBook(rows=rows, registry=active_registry)
