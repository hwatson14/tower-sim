from __future__ import annotations

from tower_sim.registry.combat_stat_contract import (
    declared_combat_stat_coverage,
    missing_required_combat_stats,
    required_combat_stat_ids,
    required_survivability_stat_ids,
)


def test_required_combat_stats_have_declared_coverage() -> None:
    coverage = declared_combat_stat_coverage()
    required = set(required_combat_stat_ids())

    assert required == set(coverage)
    for stat_id, declared in coverage.items():
        assert declared.base, stat_id
        assert declared.loadout, stat_id
        assert declared.enhancement, stat_id
        assert declared.tier, stat_id
        assert declared.derived, stat_id


def test_missing_required_combat_stats_reports_unhandled_present_set() -> None:
    missing = missing_required_combat_stats({"tower_hp", "tower_regen", "def_pct"})
    assert missing == ("thorns_damage_mult", "wall_hp", "wall_regen")


def test_required_combat_ids_are_stable_for_max_wave_requirements() -> None:
    assert required_combat_stat_ids() == (
        "tower_hp",
        "tower_regen",
        "def_pct",
        "wall_hp",
        "wall_regen",
        "thorns_damage_mult",
    )


def test_required_survivability_stats_optional_offense_flag() -> None:
    assert required_survivability_stat_ids() == required_combat_stat_ids()
    assert required_survivability_stat_ids(include_optional_offense=True) == (
        *required_combat_stat_ids(),
        "plasma_cannon_damage_mult",
    )
