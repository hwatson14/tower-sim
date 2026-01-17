from __future__ import annotations

from tower_sim.ids_state import IdsState
from tower_sim.statbook import StatBook, StatRow


PHASE_START = "start_of_run"
PHASE_END = "end_of_run"


def build_statbook(ids_state: IdsState) -> StatBook:
    rows: list[StatRow] = []
    for name, level in ids_state.labs.labs.items():
        rows.append(
            StatRow(
                stat_name=name,
                phase=PHASE_START,
                value=level,
                source="labs",
            )
        )
        rows.append(
            StatRow(
                stat_name=name,
                phase=PHASE_END,
                value=level,
                source="labs",
                notes="Raw lab level duplicated for end-of-run placeholder.",
            )
        )
    for entry in ids_state.workshop.entries.values():
        rows.append(
            StatRow(
                stat_name=entry.name,
                phase=PHASE_START,
                value=entry.coin_level,
                source="workshop",
            )
        )
        rows.append(
            StatRow(
                stat_name=entry.name,
                phase=PHASE_END,
                value=entry.max_level or entry.coin_level,
                source="workshop",
                notes="Uses raw max level when present; otherwise coin level.",
            )
        )
    return StatBook(rows=rows)
