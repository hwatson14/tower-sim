from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Dict, List, Mapping

from engine.progression_state import WorkshopTrackState
from engine.workshop_progression_policy import TRACK_CATEGORY_BY_NAME, WorkshopUpgradeEvent

FREE_UPGRADE_SURFACE_BY_CATEGORY: Dict[str, str] = {
    'attack': 'canonical_stat::free_attack_upgrade_chance_pct',
    'defense': 'canonical_stat::free_defense_upgrade_chance_pct',
    'utility': 'canonical_stat::free_utility_upgrade_chance_pct',
}

FREE_UPGRADE_SOURCE_BY_CATEGORY: Dict[str, str] = {
    'attack': 'free_attack_upgrade',
    'defense': 'free_defense_upgrade',
    'utility': 'free_utility_upgrade',
}

DYNAMICALLY_EXCLUDED_FREE_UPGRADE_TRACKS = {'Range'}


@dataclass(frozen=True)
class FreeUpgradeGenerationConfig:
    exclude_tracks: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FreeUpgradeGenerationState:
    carry_by_category: Dict[str, float] = field(default_factory=lambda: {'attack': 0.0, 'defense': 0.0, 'utility': 0.0})
    next_index_by_category: Dict[str, int] = field(default_factory=lambda: {'attack': 0, 'defense': 0, 'utility': 0})


@dataclass(frozen=True)
class GeneratedFreeUpgradeResult:
    state: FreeUpgradeGenerationState
    generated_events: List[WorkshopUpgradeEvent]
    notes: List[str] = field(default_factory=list)


class FreeUpgradeGenerationPolicy:
    """Deterministic expected free-upgrade generator.

    Current policy is an accepted deterministic model:
    - expected upgrades per wave = chance_pct / 100
    - fractional expectation carries forward by category
    - guaranteed upgrades are distributed in stable workshop-track order
      within category, skipping maxed tracks
    - Range exclusion is conditional on Black Hole Disable Ranged capability
    - no wave-skip-derived extra upgrades are modeled here
    """

    def __init__(self, config: FreeUpgradeGenerationConfig | None = None) -> None:
        self.config = config or FreeUpgradeGenerationConfig()

    def generate_for_wave(
        self,
        *,
        wave: int,
        workshop_tracks: Mapping[str, WorkshopTrackState],
        workshop_levels_current: Dict[str, int],
        stat_values: Mapping[str, float | None],
        state: FreeUpgradeGenerationState,
        black_hole_disable_ranged: bool = False,
    ) -> GeneratedFreeUpgradeResult:
        carry = dict(state.carry_by_category)
        next_index = dict(state.next_index_by_category)
        events: List[WorkshopUpgradeEvent] = []
        notes: List[str] = []
        dynamic_exclude_tracks = set(self.config.exclude_tracks)
        if black_hole_disable_ranged:
            dynamic_exclude_tracks.update(DYNAMICALLY_EXCLUDED_FREE_UPGRADE_TRACKS)
            notes.append('Range excluded from free-upgrade generation because Black Hole disable-ranged capability is active.')
        for category in ('attack', 'defense', 'utility'):
            if not self._candidate_tracks(workshop_tracks=workshop_tracks, workshop_levels_current=workshop_levels_current, category=category, exclude_tracks=dynamic_exclude_tracks):
                continue
            surface = FREE_UPGRADE_SURFACE_BY_CATEGORY[category]
            pct = stat_values.get(surface)
            if pct is None:
                notes.append(f'Missing {surface}; generated free upgrades skipped for {category} at wave {wave}.')
                continue
            carry[category] = carry.get(category, 0.0) + max(0.0, float(pct)) / 100.0
            guaranteed = int(floor(carry[category] + 1e-12))
            if guaranteed <= 0:
                continue
            carry[category] -= guaranteed
            idx = next_index.get(category, 0)
            for _ in range(guaranteed):
                candidates = self._candidate_tracks(
                    workshop_tracks=workshop_tracks,
                    workshop_levels_current=workshop_levels_current,
                    category=category,
                    exclude_tracks=dynamic_exclude_tracks,
                )
                if not candidates:
                    notes.append(f'Category {category} exhausted at wave {wave}; remaining generated free upgrades were not assignable.')
                    break
                chosen_index = idx % len(candidates)
                track_name = candidates[chosen_index]
                current = int(workshop_levels_current[track_name])
                max_level = int(workshop_tracks[track_name].max_level)
                if current >= max_level:
                    idx += 1
                    continue
                workshop_levels_current[track_name] = min(max_level, current + 1)
                events.append(
                    WorkshopUpgradeEvent(
                        wave=int(wave),
                        track_name=track_name,
                        delta_levels=1,
                        source=FREE_UPGRADE_SOURCE_BY_CATEGORY[category],
                        note=f'generated_from_{surface}',
                    )
                )
                idx = chosen_index + 1
            next_index[category] = idx
        return GeneratedFreeUpgradeResult(
            state=FreeUpgradeGenerationState(carry_by_category=carry, next_index_by_category=next_index),
            generated_events=events,
            notes=notes,
        )

    def _candidate_tracks(
        self,
        *,
        workshop_tracks: Mapping[str, WorkshopTrackState],
        workshop_levels_current: Mapping[str, int],
        category: str,
        exclude_tracks: set[str],
    ) -> List[str]:
        out: List[str] = []
        for name, track in workshop_tracks.items():
            mapped_category = TRACK_CATEGORY_BY_NAME.get(name)
            if mapped_category != category:
                continue
            if name in exclude_tracks:
                continue
            current = int(workshop_levels_current[name])
            if current >= int(track.max_level):
                continue
            out.append(name)
        return out
