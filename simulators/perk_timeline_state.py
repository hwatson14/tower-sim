from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from qe.account_state import AccountState, PerkSelection

ROOT = Path(__file__).resolve().parents[1]
PERK_ENTITY_REGISTRY = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
PROGRESSION_TIMELINE_PRESET = 'ProgressionTimeline_CurrentWave'


@dataclass(frozen=True)
class PerkTimelineEvent:
    wave: int
    perk_id: str
    perk_name: str
    quantity: int = 1
    retroactive_burst: bool = False


def load_perk_name_to_id_map(path: Path = PERK_ENTITY_REGISTRY) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            perk_id = (row.get('perk_id') or '').strip()
            perk_name = (row.get('perk_name') or '').strip()
            if perk_id and perk_name:
                mapping[perk_name] = perk_id
    return mapping


def load_perk_timeline(path: Path, *, perk_name_to_id: Optional[Dict[str, str]] = None) -> List[PerkTimelineEvent]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, list):
        raise ValueError(f'Expected perk timeline JSON array, got {type(raw).__name__}.')
    name_map = perk_name_to_id or load_perk_name_to_id_map()
    events: List[PerkTimelineEvent] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f'Timeline row {idx} is not an object.')
        perk_id = str(row.get('perk_id') or '').strip()
        perk_name = str(row.get('perk_taken') or row.get('perk_name') or '').strip()
        if not perk_id:
            if not perk_name:
                raise ValueError(f'Timeline row {idx} missing both perk_id and perk name.')
            perk_id = name_map.get(perk_name, '')
        if not perk_id:
            raise ValueError(f'Timeline row {idx} could not map perk name to perk_id: {perk_name!r}')
        wave = int(row.get('wave'))
        quantity = int(row.get('quantity') or 1)
        events.append(PerkTimelineEvent(
            wave=wave,
            perk_id=perk_id,
            perk_name=perk_name or perk_id,
            quantity=quantity,
            retroactive_burst=bool(row.get('retroactive_burst', False)),
        ))
    events.sort(key=lambda e: (e.wave, e.perk_id))
    return events


def perk_counts_at_wave(events: Iterable[PerkTimelineEvent], wave: int) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        if event.wave > wave:
            break
        counts[event.perk_id] = counts.get(event.perk_id, 0) + int(event.quantity)
    return counts


def apply_perk_counts_to_account_state(
    account_state: AccountState,
    *,
    perk_counts: Dict[str, int],
    preset_name: str = PROGRESSION_TIMELINE_PRESET,
) -> AccountState:
    patched_perk_presets = dict(account_state.perk_presets)
    patched_perk_presets[preset_name] = [
        PerkSelection(perk_id=perk_id, picks=int(picks))
        for perk_id, picks in sorted(perk_counts.items())
        if int(picks) > 0
    ]
    return replace(
        account_state,
        perk_presets=patched_perk_presets,
        perk_preset_namespace_class='transient',
        active_perk_preset=preset_name,
    )
