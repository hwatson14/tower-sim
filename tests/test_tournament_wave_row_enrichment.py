from __future__ import annotations

from tower_sim.engines.combat_stat_derivation import build_canonical_wave_row
from tower_sim.loaders.bc_heat_loader import HeatDataError
from tower_sim.loaders.tournament_bc_enrichment import map_tournament_heat_bc_to_stat_magnitudes
from tower_sim.registry.stat_registry import default_registry
from tower_sim.run.problem_spec import ProblemSpec, ScenarioSpec, SkipRampSpec


def _tournament_problem(*, wave: int = 10, league: str = "champion") -> ProblemSpec:
    return ProblemSpec(
        scenario=ScenarioSpec(
            mode="tournament",
            tier=12,
            league=league,
            wave=wave,
            eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
            ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        ),
        stat_inputs=[],
    )


def test_map_tournament_heat_bc_to_stat_magnitudes_maps_all_supported_ids() -> None:
    registry = default_registry()
    magnitudes = map_tournament_heat_bc_to_stat_magnitudes(
        registry=registry,
        bc_values={
            "death_ray_resistance:": 1.1,
            "knockback_resistance:": 1.2,
            "orb_resistance:": 1.3,
            "plasma_cannon_resistance:": 1.4,
            "thorns_resistance:": 1.5,
        },
    )

    assert magnitudes == {
        "death_ray_damage_mult": 1.1,
        "knockback_mult": 1.2,
        "orb_damage_mult": 1.3,
        "plasma_cannon_damage_mult": 1.4,
        "thorns_damage_mult": 1.5,
    }


def test_build_canonical_wave_row_uses_cached_heat_lookup_and_applies_mapping(monkeypatch) -> None:
    calls = {"count": 0}

    class _FakeTable:
        def value_at(self, *, league: str, wave_actual: int, bc_id: str):
            class _Row:
                value_num = 1.25

            return _Row()

    def _fake_cached(scale_path: str, registry_path: str):
        calls["count"] += 1
        return _FakeTable()

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation.cached_tournament_heat_table",
        _fake_cached,
    )

    row, missing = build_canonical_wave_row(_tournament_problem(), default_registry(), wave=10)

    assert missing == []
    assert row is not None
    assert calls["count"] == 1
    assert row["battle_conditions"]["thorns_resistance:"] == 1.25
    assert row["heat_magnitudes"]["thorns_damage_mult"] == 1.25


def test_build_canonical_wave_row_fail_closed_on_missing_table(monkeypatch) -> None:
    def _raise(*_args, **_kwargs):
        raise HeatDataError("bad table")

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation.cached_tournament_heat_table",
        _raise,
    )

    row, missing = build_canonical_wave_row(_tournament_problem(), default_registry(), wave=10)

    assert row is None
    assert missing == ["heat_tables"]
