from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.perk_timeline_state import PerkTimelineEvent, load_perk_timeline

from models.account_state import AccountState

MODE_IDS = {
    "Farming": "farming",
    "Tourney": "tournament",
    "Milestone": "milestone",
    "Preset 4": "preset_4",
    "Preset 5": "preset_5",
}


@dataclass(frozen=True)
class WorkshopTrackState:
    track_name: str
    current_level: int
    max_level: int
    category: Optional[str] = None
    unlocked: Optional[str] = None

    @property
    def remaining_levels(self) -> int:
        return max(0, self.max_level - self.current_level)


@dataclass(frozen=True)
class ProgressionInitState:
    preset_name: str
    mode_id: str
    workshop_tracks: Dict[str, WorkshopTrackState]
    perk_timeline: List[PerkTimelineEvent] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def workshop_levels_current(self) -> Dict[str, int]:
        return {name: track.current_level for name, track in self.workshop_tracks.items()}

    @property
    def workshop_levels_max(self) -> Dict[str, int]:
        return {name: track.max_level for name, track in self.workshop_tracks.items()}


def infer_mode_id_from_preset(preset_name: str) -> str:
    if preset_name not in MODE_IDS:
        raise ValueError(
            f"Unsupported preset for progression engine: {preset_name!r}. "
            f"Expected one of {sorted(MODE_IDS)}."
        )
    return MODE_IDS[preset_name]


def build_workshop_track_states(account_state: AccountState, preset_name: str) -> Dict[str, WorkshopTrackState]:
    tracks: Dict[str, WorkshopTrackState] = {}
    for name, entry in account_state.workshop.items():
        if entry.max_level is None:
            continue
        current = entry.preset_levels.get(preset_name)
        if current is None:
            current = 0
        tracks[name] = WorkshopTrackState(
            track_name=name,
            current_level=int(current),
            max_level=int(entry.max_level),
            category=entry.category,
            unlocked=entry.unlocked,
        )
    return tracks


def build_progression_init_state(
    account_state: AccountState,
    *,
    preset_name: str,
    mode_id: Optional[str] = None,
    perk_timeline: Optional[List[Dict[str, Any]]] = None,
    perk_timeline_path: Optional[Path] = None,
) -> ProgressionInitState:
    resolved_mode_id = mode_id or infer_mode_id_from_preset(preset_name)
    resolved_timeline = list(perk_timeline or [])
    if perk_timeline_path is not None:
        resolved_timeline = load_perk_timeline(Path(perk_timeline_path))
    notes = [
        "Initialized from IDS-backed start-of-run workshop preset levels.",
        "Progression engine owns mutable in-run workshop state; stat formulas remain owned by stat engine.",
    ]
    if perk_timeline:
        notes.append("Perk timeline supplied as fixed run timeline; progression consumes timeline but does not own PWR timing logic.")
    return ProgressionInitState(
        preset_name=preset_name,
        mode_id=resolved_mode_id,
        workshop_tracks=build_workshop_track_states(account_state, preset_name),
        perk_timeline=resolved_timeline,
        notes=notes,
    )
