from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.perk_timeline_state import load_perk_timeline, perk_counts_at_wave


def test_load_perk_timeline_maps_names_to_ids(tmp_path: Path):
    registry = tmp_path / 'perk-entity-registry.csv'
    registry.write_text('perk_id,perk_name\nPERK_ORBS_1,Orbs +1\nPERK_X1_20_MAX_HEALTH,x1.20 Max Health\n', encoding='utf-8')
    timeline = tmp_path / 'timeline.json'
    timeline.write_text(json.dumps([
        {'wave': 187, 'perk_taken': 'Orbs +1', 'quantity': 1},
        {'wave': 374, 'perk_taken': 'x1.20 Max Health', 'quantity': 1},
    ]), encoding='utf-8')
    events = load_perk_timeline(timeline, perk_name_to_id={'Orbs +1': 'PERK_ORBS_1', 'x1.20 Max Health': 'PERK_X1_20_MAX_HEALTH'})
    assert [e.perk_id for e in events] == ['PERK_ORBS_1', 'PERK_X1_20_MAX_HEALTH']


def test_perk_counts_at_wave_is_cumulative():
    from engine.perk_timeline_state import PerkTimelineEvent
    events = [
        PerkTimelineEvent(wave=100, perk_id='PERK_A', perk_name='A'),
        PerkTimelineEvent(wave=200, perk_id='PERK_A', perk_name='A'),
        PerkTimelineEvent(wave=250, perk_id='PERK_B', perk_name='B', quantity=2),
    ]
    assert perk_counts_at_wave(events, 199) == {'PERK_A': 1}
    assert perk_counts_at_wave(events, 250) == {'PERK_A': 2, 'PERK_B': 2}
