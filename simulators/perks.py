from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

from simulators.contracts import PerkState
from simulators.perk_timeline_state import PerkTimelineEvent


@dataclass(frozen=True)
class PerkCursor:
    next_index: int = 0
    counts: Dict[str, int] = field(default_factory=dict)


def advance_perk_state(
    events: Iterable[PerkTimelineEvent],
    *,
    wave: int,
    cursor: Optional[PerkCursor] = None,
) -> Tuple[PerkState, PerkCursor]:
    """Advance perk state to the requested wave using a prefix cursor."""
    ordered = tuple(events)
    next_index = 0 if cursor is None else int(cursor.next_index)
    counts = dict({} if cursor is None else cursor.counts)
    dirty = False
    while next_index < len(ordered) and int(ordered[next_index].wave) <= int(wave):
        event = ordered[next_index]
        counts[str(event.perk_id)] = counts.get(str(event.perk_id), 0) + int(event.quantity or 1)
        next_index += 1
        dirty = True
    state = PerkState(wave=int(wave), counts=counts, dirty=dirty)
    return state, PerkCursor(next_index=next_index, counts=counts)
