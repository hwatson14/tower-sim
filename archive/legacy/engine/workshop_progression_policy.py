from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Literal, Optional

from engine.progression_state import WorkshopTrackState

UpgradeSource = Literal[
    'manual_buy',
    'free_attack_upgrade',
    'free_defense_upgrade',
    'free_utility_upgrade',
]

TRACK_CATEGORY_BY_NAME: Dict[str, str] = {
    # Attack
    'Damage': 'attack',
    'Attack Speed': 'attack',
    'Critical Chance': 'attack',
    'Critical Factor': 'attack',
    'Range': 'attack',
    'Damage / Meter': 'attack',
    'Multishot Chance': 'attack',
    'Multishot Targets': 'attack',
    'Rapid Fire Chance': 'attack',
    'Rapid Fire Duration': 'attack',
    'Bounce Shot Chance': 'attack',
    'Bounce Shot Targets': 'attack',
    'Bounce Shot Range': 'attack',
    'Super Critical Chance': 'attack',
    'Super Critical Mult': 'attack',
    'Rend Armor Chance': 'attack',
    'Rend Armor Mult': 'attack',
    # Defense
    'Health': 'defense',
    'Health Regen': 'defense',
    'Defense %': 'defense',
    'Defense Absolute': 'defense',
    'Thorn Damage': 'defense',
    'Lifesteal': 'defense',
    'Knockback Chance': 'defense',
    'Knockback Force': 'defense',
    'Orb Speed': 'defense',
    'Orb Boss Hit': 'defense',
    'Orbs': 'defense',
    'Death Defy': 'defense',
    'Shockwave Size': 'defense',
    'Shockwave Frequency': 'defense',
    'Land Mine Chance': 'defense',
    'Land Mine Damage': 'defense',
    'Land Mine Radius': 'defense',
    'Wall Health': 'defense',
    'Wall Rebuild': 'defense',
    'Wall Regen': 'defense',
    'Wall Thorns': 'defense',
    'Wall Invincibility': 'defense',
    'Wall Fortification': 'defense',
    # Utility
    'Cash Bonus': 'utility',
    'Cash / Wave': 'utility',
    'Coins / Kill Bonus': 'utility',
    'Coins / Wave': 'utility',
    'Enemy Balance': 'utility',
    'Health Package Chance': 'utility',
    'Health Package Amount': 'utility',
    'Health Package Max': 'utility',
    'Free Attack Upgrade': 'utility',
    'Free Defense Upgrade': 'utility',
    'Free Utility Upgrade': 'utility',
    'Recovery Package Chance': 'utility',
    'Recovery Package Amount': 'utility',
    'Recovery Package Max': 'utility',
    'EALS': 'utility',
    'EHLS': 'utility',
}

_SOURCE_TO_CATEGORY = {
    'free_attack_upgrade': 'attack',
    'free_defense_upgrade': 'defense',
    'free_utility_upgrade': 'utility',
}


@dataclass(frozen=True)
class WorkshopUpgradeEvent:
    wave: int
    track_name: str
    delta_levels: int
    source: UpgradeSource
    note: Optional[str] = None


@dataclass(frozen=True)
class AppliedWorkshopUpgrade:
    wave: int
    track_name: str
    requested_delta: int
    applied_delta: int
    resulting_level: int
    source: UpgradeSource
    category: str
    note: Optional[str] = None


@dataclass(frozen=True)
class WorkshopProgressionSnapshot:
    wave: int
    workshop_levels_current: Dict[str, int]
    applied_upgrades: List[AppliedWorkshopUpgrade] = field(default_factory=list)


class WorkshopProgressionPolicy:
    """Owns progression-time workshop state mutation only.

    This module intentionally does not invent expected free-upgrade counts from chance percentages.
    It consumes explicit upgrade events by wave and validates them against track categories.
    Stat formulas remain owned by the stat engine via full recompute after mutation.
    """

    def snapshot_at_wave(
        self,
        *,
        workshop_tracks: Dict[str, WorkshopTrackState],
        events: Iterable[WorkshopUpgradeEvent],
        wave: int,
    ) -> WorkshopProgressionSnapshot:
        levels = {name: track.current_level for name, track in workshop_tracks.items()}
        max_levels = {name: track.max_level for name, track in workshop_tracks.items()}
        applied: List[AppliedWorkshopUpgrade] = []
        for event in sorted(events, key=lambda e: (e.wave, e.track_name, e.source)):
            if event.wave > wave:
                break
            if event.track_name not in levels:
                raise KeyError(f'Unknown workshop track in progression event: {event.track_name}')
            if int(event.delta_levels) < 0:
                raise ValueError(f'Negative workshop delta is not allowed: {event}')
            category = self._track_category(event.track_name)
            self._validate_source_category(event.source, event.track_name, category)
            before = levels[event.track_name]
            max_level = max_levels[event.track_name]
            requested = int(event.delta_levels)
            after = min(max_level, before + requested)
            applied_delta = after - before
            levels[event.track_name] = after
            applied.append(
                AppliedWorkshopUpgrade(
                    wave=int(event.wave),
                    track_name=event.track_name,
                    requested_delta=requested,
                    applied_delta=applied_delta,
                    resulting_level=after,
                    source=event.source,
                    category=category,
                    note=event.note,
                )
            )
        return WorkshopProgressionSnapshot(wave=wave, workshop_levels_current=levels, applied_upgrades=applied)

    def _track_category(self, track_name: str) -> str:
        if track_name not in TRACK_CATEGORY_BY_NAME:
            raise KeyError(
                f'Workshop track category not registered for progression policy: {track_name!r}. '
                'Add an explicit mapping before using free-upgrade category validation.'
            )
        return TRACK_CATEGORY_BY_NAME[track_name]

    def _validate_source_category(self, source: UpgradeSource, track_name: str, category: str) -> None:
        required_category = _SOURCE_TO_CATEGORY.get(source)
        if required_category is None:
            return
        if category != required_category:
            raise ValueError(
                f'Invalid workshop event source/category mismatch: source={source!r} track={track_name!r} '
                f'category={category!r} required_category={required_category!r}'
            )
