from engine.progression_state import WorkshopTrackState
from engine.workshop_progression_policy import WorkshopProgressionPolicy, WorkshopUpgradeEvent


def _tracks():
    return {
        'Damage': WorkshopTrackState(track_name='Damage', current_level=5750, max_level=6000),
        'Health': WorkshopTrackState(track_name='Health', current_level=5700, max_level=6000),
        'Free Attack Upgrade': WorkshopTrackState(track_name='Free Attack Upgrade', current_level=49, max_level=99),
    }


def test_snapshot_applies_manual_and_free_upgrades_with_clamp():
    policy = WorkshopProgressionPolicy()
    snap = policy.snapshot_at_wave(
        workshop_tracks=_tracks(),
        events=[
            WorkshopUpgradeEvent(wave=40, track_name='Damage', delta_levels=100, source='manual_buy'),
            WorkshopUpgradeEvent(wave=40, track_name='Damage', delta_levels=200, source='free_attack_upgrade'),
            WorkshopUpgradeEvent(wave=50, track_name='Health', delta_levels=400, source='free_defense_upgrade'),
        ],
        wave=45,
    )
    assert snap.workshop_levels_current['Damage'] == 6000
    assert snap.workshop_levels_current['Health'] == 5700
    assert len(snap.applied_upgrades) == 2
    assert sum(x.applied_delta for x in snap.applied_upgrades) == 250
    assert sorted(x.applied_delta for x in snap.applied_upgrades) == [50, 200]


def test_snapshot_rejects_category_mismatch():
    policy = WorkshopProgressionPolicy()
    try:
        policy.snapshot_at_wave(
            workshop_tracks=_tracks(),
            events=[WorkshopUpgradeEvent(wave=20, track_name='Health', delta_levels=1, source='free_attack_upgrade')],
            wave=20,
        )
        assert False, 'expected ValueError'
    except ValueError as exc:
        assert 'source/category mismatch' in str(exc)


def test_snapshot_requires_registered_track_category_for_free_upgrade_validation():
    policy = WorkshopProgressionPolicy()
    tracks = _tracks() | {'Mystery': WorkshopTrackState(track_name='Mystery', current_level=0, max_level=10)}
    try:
        policy.snapshot_at_wave(
            workshop_tracks=tracks,
            events=[WorkshopUpgradeEvent(wave=10, track_name='Mystery', delta_levels=1, source='free_utility_upgrade')],
            wave=10,
        )
        assert False, 'expected KeyError'
    except KeyError as exc:
        assert 'category not registered' in str(exc)
