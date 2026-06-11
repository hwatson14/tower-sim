from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.loader import load_inputs
from input.runtime_state import build_runtime_state

pytestmark = pytest.mark.live


def _track_by_name(state, bot_name: str, track_name: str):
    tracks = {
        track.track_name: track
        for track in state.bot_upgrade_tracks.get(bot_name, [])
    }
    return tracks[track_name]


def _overlay_manual_inputs() -> dict:
    return {
        'runtime_state_overlays': {
            'disco_respec_test': {
                'lab_levels': {
                    'Second Wind Mastery': 3,
                },
                'dissonance_pbs_by_tier': {
                    'Tier 16': {
                        'uw': 780,
                    },
                    '17': {
                        'Attack': 1545,
                        'ultimate_weapons': 230,
                    },
                },
                'bots': {
                    'Flame Bot': {
                        'unlocked': True,
                        'tracks': {
                            'Damage R.': {'value': 95.0, 'unit': '%'},
                            'Cooldown': {'value': 5.0, 'unit': 's'},
                            'Range': {'value': 91.0, 'unit': 'm', 'value_kind': 'effective_range_m'},
                        },
                    },
                    'Bot Bot': {
                        'unlocked': True,
                        'tracks': {
                            'Bonus': {'value': 1.5, 'unit': 'x'},
                        },
                    },
                },
            },
        },
    }


def test_runtime_state_overlays_do_not_apply_without_explicit_selector() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
        manual_inputs=_overlay_manual_inputs(),
    )

    assert state.manual_override_sources == {}
    assert _track_by_name(state, 'Flame Bot', 'Damage R.').resolved_value != pytest.approx(95.0)


def test_manual_runtime_state_overlay_applies_lab_and_exact_bot_values_when_selected() -> None:
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
        manual_inputs=_overlay_manual_inputs(),
        runtime_state_overlay='disco_respec_test',
    )

    assert state.labs['Second Wind Mastery'] == 3
    assert state.cards_inventory['Second Wind'].mastery_lab_level == 3
    assert state.bot_unlocks['Flame Bot'] is True
    assert state.bot_unlocks['Bot Bot'] is True
    assert state.dissonance_pbs_by_tier['Tier 16']['ultimate_weapons'] == 780
    assert state.dissonance_pbs_by_tier['Tier 17']['attack'] == 1545
    assert state.dissonance_pbs_by_tier['Tier 17']['ultimate_weapons'] == 230

    flame_dr = _track_by_name(state, 'Flame Bot', 'Damage R.')
    flame_cooldown = _track_by_name(state, 'Flame Bot', 'Cooldown')
    flame_range = _track_by_name(state, 'Flame Bot', 'Range')
    bot_bot_bonus = _track_by_name(state, 'Bot Bot', 'Bonus')

    assert flame_dr.level is None
    assert flame_dr.resolved_value == pytest.approx(95.0)
    assert flame_dr.resolved_unit == '%'
    assert flame_dr.source == 'manual_inputs.runtime_state_overlays.disco_respec_test.bots.Flame Bot.tracks.Damage R.'
    assert flame_cooldown.resolved_value == pytest.approx(5.0)
    assert flame_range.resolved_value == pytest.approx(91.0)
    assert flame_range.value_kind == 'effective_range_m'
    assert bot_bot_bonus.resolved_value == pytest.approx(1.5)
    assert (
        state.manual_override_sources['runtime_state_overlay']['selected']
        == 'manual_inputs.runtime_state_overlays.disco_respec_test'
    )
    assert (
        state.manual_override_sources['labs']['Second Wind Mastery']
        == 'manual_inputs.runtime_state_overlays.disco_respec_test.lab_levels'
    )
    assert (
        state.manual_override_sources['bot_tracks']['Flame Bot::Damage R.']
        == 'manual_inputs.runtime_state_overlays.disco_respec_test.bots.Flame Bot.tracks.Damage R.'
    )
    assert (
        state.manual_override_sources['dissonance_pbs_by_tier']['Tier 17::attack']
        == 'manual_inputs.runtime_state_overlays.disco_respec_test.dissonance_pbs_by_tier.Tier 17.attack'
    )
