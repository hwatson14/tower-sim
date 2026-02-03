from __future__ import annotations

from tower_sim.engines.combat.combat_engine import resolve_wave_damage


def test_resolve_wave_damage_from_tables() -> None:
    assert resolve_wave_damage("Tier 12", 1) == 14710000.0
