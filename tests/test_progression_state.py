from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from pathlib import Path

from input.runtime_state import compile_account_state
from engine.progression_state import build_progression_init_state, infer_mode_id_from_preset
from input.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def test_infer_mode_id_from_preset():
    assert infer_mode_id_from_preset('Farming') == 'farming'
    assert infer_mode_id_from_preset('Tourney') == 'tournament'
    assert infer_mode_id_from_preset('Milestone') == 'milestone'
    assert infer_mode_id_from_preset('Preset 4') == 'preset_4'
    assert infer_mode_id_from_preset('Preset 5') == 'preset_5'


def test_progression_init_uses_ids_backed_workshop_levels():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming')
    damage = init.workshop_tracks['Damage']
    assert damage.current_level == 5750
    assert damage.max_level == 6000
    assert damage.remaining_levels == 250
    assert init.mode_id == 'farming'


def test_progression_init_accepts_all_five_canonical_presets():
    state = _build_state()
    for preset_name in ('Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5'):
        init = build_progression_init_state(state, preset_name=preset_name)
        assert init.preset_name == preset_name
        assert init.mode_id == infer_mode_id_from_preset(preset_name)
        assert 'Damage' in init.workshop_tracks
        assert init.workshop_tracks['Damage'].current_level is not None
