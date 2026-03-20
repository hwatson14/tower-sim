from engine.geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE, unify_wall_contact_target_surface


def test_target_surface_alias_is_mapped():
    report = unify_wall_contact_target_surface([{"boss_contact_event_seconds_normalized": 12.5}])
    assert report["rows"][0][CANONICAL_TARGET_SURFACE] == 12.5
    assert "boss_contact_event_seconds_normalized" in report["aliases_consumed"]
