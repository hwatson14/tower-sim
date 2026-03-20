from engine.free_upgrade_generation_policy import FreeUpgradeGenerationPolicy, FreeUpgradeGenerationState
from engine.progression_state import WorkshopTrackState


def _tracks():
    return {
        'Damage': WorkshopTrackState(track_name='Damage', current_level=0, max_level=2),
        'Attack Speed': WorkshopTrackState(track_name='Attack Speed', current_level=0, max_level=2),
        'Health': WorkshopTrackState(track_name='Health', current_level=0, max_level=2),
        'Free Utility Upgrade': WorkshopTrackState(track_name='Free Utility Upgrade', current_level=0, max_level=2),
        'Range': WorkshopTrackState(track_name='Range', current_level=0, max_level=2),
    }


def test_generate_for_wave_uses_expected_carry_and_round_robin():
    policy = FreeUpgradeGenerationPolicy()
    levels = {name: track.current_level for name, track in _tracks().items()}
    state = FreeUpgradeGenerationState()
    wave1 = policy.generate_for_wave(
        wave=1,
        workshop_tracks=_tracks(),
        workshop_levels_current=levels,
        stat_values={
            'canonical_stat::free_attack_upgrade_chance_pct': 150.0,
            'canonical_stat::free_defense_upgrade_chance_pct': 0.0,
            'canonical_stat::free_utility_upgrade_chance_pct': 0.0,
        },
        state=state,
    )
    assert len(wave1.generated_events) == 1
    assert wave1.generated_events[0].track_name == 'Damage'
    assert levels['Damage'] == 1
    wave2 = policy.generate_for_wave(
        wave=2,
        workshop_tracks=_tracks(),
        workshop_levels_current=levels,
        stat_values={
            'canonical_stat::free_attack_upgrade_chance_pct': 150.0,
            'canonical_stat::free_defense_upgrade_chance_pct': 0.0,
            'canonical_stat::free_utility_upgrade_chance_pct': 0.0,
        },
        state=wave1.state,
    )
    assert len(wave2.generated_events) == 2
    assert [e.track_name for e in wave2.generated_events] == ['Attack Speed', 'Range']
    assert levels['Damage'] == 1
    assert levels['Attack Speed'] == 1
    assert levels['Range'] == 1


def test_generate_for_wave_excludes_range_only_when_bhd_active():
    policy = FreeUpgradeGenerationPolicy()
    levels = {name: track.current_level for name, track in _tracks().items()}
    state = FreeUpgradeGenerationState()
    result = policy.generate_for_wave(
        wave=1,
        workshop_tracks=_tracks(),
        workshop_levels_current=levels,
        stat_values={
            'canonical_stat::free_attack_upgrade_chance_pct': 300.0,
            'canonical_stat::free_defense_upgrade_chance_pct': 0.0,
            'canonical_stat::free_utility_upgrade_chance_pct': 0.0,
        },
        state=state,
        black_hole_disable_ranged=True,
    )
    assert all(e.track_name != 'Range' for e in result.generated_events)


def test_generate_for_wave_allows_range_when_bhd_inactive():
    policy = FreeUpgradeGenerationPolicy()
    tracks = _tracks()
    levels = {name: track.current_level for name, track in tracks.items()}
    levels['Damage'] = tracks['Damage'].max_level
    levels['Attack Speed'] = tracks['Attack Speed'].max_level
    state = FreeUpgradeGenerationState()
    result = policy.generate_for_wave(
        wave=1,
        workshop_tracks=tracks,
        workshop_levels_current=levels,
        stat_values={
            'canonical_stat::free_attack_upgrade_chance_pct': 100.0,
            'canonical_stat::free_defense_upgrade_chance_pct': 0.0,
            'canonical_stat::free_utility_upgrade_chance_pct': 0.0,
        },
        state=state,
        black_hole_disable_ranged=False,
    )
    assert [e.track_name for e in result.generated_events] == ['Range']
