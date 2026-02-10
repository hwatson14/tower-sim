from __future__ import annotations

from pathlib import Path

from tower_sim.evaluators.max_wave import (
    MaxWaveEvaluator,
    _build_wave_row,
    _cached_tournament_heat_table,
    _stat_inputs_for_wave,
)
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.run.problem_spec import (
    BossStatsSpec,
    BossSurvivabilitySpec,
    ProblemSpec,
    ScenarioSpec,
    SkipRampSpec,
    StatInputSpec,
    TowerDefenseSpec,
)


def _stat_input(stat_id: str, value: float) -> StatInputSpec:
    return StatInputSpec(
        stat_id=stat_id,
        phase=Phase.START_OF_RUN,
        base_value=value,
        provenance="test",
    )


def _problem(mode: str = "farming", wave: int = 20) -> ProblemSpec:
    scenario = ScenarioSpec(
        mode=mode,
        tier=12,
        league="champion" if mode == "tournament" else None,
        wave=wave,
        eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        perk_timeline_path="tests/fixtures/does_not_exist.json",
        boss_survivability=BossSurvivabilitySpec(
            boss=BossStatsSpec(hp=1.0, attack=1.0, attack_interval=1.0, enrage_mult=1.0),
            tower=TowerDefenseSpec(dr_frac=0.0, regen_per_sec=0.0, shields=0.0),
            combat_params={
                "hit_interval_id": "default",
                "defense_abs": 0.0,
                "damage_reduction": 0.0,
                "pc_frac": 0.0,
                "pc_boss_mult": 1.0,
                "orb_damage_frac": 0.0,
                "electrons_damage_frac": 0.0,
            },
            bc_params={"boss_hp_mult": 1.0, "boss_attack_mult": 1.0},
        ),
    )
    stat_inputs = [
        _stat_input("tower_hp", 1.0),
        _stat_input("tower_regen", 0.0),
        _stat_input("def_pct", 0.0),
        _stat_input("wall_hp", 0.0),
        _stat_input("wall_regen", 0.0),
        _stat_input("thorns_damage_mult", 0.01),
        _stat_input("eals_pct", 0.0),
        _stat_input("ehls_pct", 0.0),
        _stat_input("orb_damage_mult", 1.0),
        _stat_input("death_ray_damage_mult", 1.0),
        _stat_input("plasma_cannon_damage_mult", 1.0),
        _stat_input("knockback_mult", 1.0),
    ]
    return ProblemSpec(scenario=scenario, stat_inputs=stat_inputs)


def _snapshot():
    return compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))


def test_wave_engine_imports_are_low_level_only() -> None:
    source = Path("tower_sim/engines/wave_engine.py").read_text(encoding="utf-8")
    assert "stat_input_compiler" not in source
    assert "stat_snapshots" not in source
    assert "loaders" not in source


def test_max_wave_smoke_returns_dict() -> None:
    result = MaxWaveEvaluator().evaluate(_problem(mode="farming", wave=10), _snapshot())
    assert isinstance(result, dict)
    assert "w_max" in result


def test_tournament_mode_disables_perk_timeline_application() -> None:
    problem = _problem(mode="tournament", wave=1)
    stat_inputs = [spec.to_stat_input() for spec in problem.stat_inputs]
    updated, diag = _stat_inputs_for_wave(
        registry=default_registry(),
        stat_inputs=stat_inputs,
        scenario=problem.scenario,
        wave=1,
    )
    assert updated == stat_inputs
    assert diag["enabled"] is False
    assert diag["reason"] == "tournament_mode"


def test_repo_has_no_rej_artifacts() -> None:
    assert not list(Path(".").glob("**/*.rej"))


def test_tournament_heat_table_is_cached(monkeypatch) -> None:
    _cached_tournament_heat_table.cache_clear()
    calls = {"count": 0}

    class _FakeTable:
        def value_at(self, *, league: str, wave_actual: int, bc_id: str):
            class _Row:
                value_num = 1.0

            return _Row()

    def _fake_loader(scale_path, registry_path):
        calls["count"] += 1
        return _FakeTable()

    monkeypatch.setattr("tower_sim.evaluators.max_wave.load_tournament_heat_table", _fake_loader)

    problem = _problem(mode="tournament", wave=2)
    registry = default_registry()

    row1, missing1 = _build_wave_row(problem, registry, wave=1)
    row2, missing2 = _build_wave_row(problem, registry, wave=2)

    assert not missing1
    assert not missing2
    assert row1 is not None
    assert row2 is not None
    assert calls["count"] == 1


def test_assumptions_manifest_present_on_success() -> None:
    result = MaxWaveEvaluator().evaluate(_problem(mode="farming", wave=10), _snapshot())
    manifest = result["assumptions_manifest"]
    assert manifest["schema_version"] == "v1"
    assert manifest["policy_version"] == "v1"
    assert manifest["tolerance_version"] == "v1"
    assert manifest["perk_timeline"]["required"] is True
    assert manifest["parity_tolerances"]["wmax_wave_relative"] == 0.10
    assert manifest["parity_tolerances"]["stats_relative"] == 0.01


def test_assumptions_manifest_present_on_fail_closed() -> None:
    base_problem = _problem(mode="farming", wave=10)
    problem = ProblemSpec(
        scenario=base_problem.scenario,
        stat_inputs=[s for s in base_problem.stat_inputs if s.stat_id != "tower_hp"],
        evaluator=base_problem.evaluator,
    )
    result = MaxWaveEvaluator().evaluate(problem, _snapshot())
    assert result["fail_closed"] is True
    manifest = result["assumptions_manifest"]
    assert manifest["schema_version"] == "v1"
    assert manifest["perk_timeline"]["required"] is True


def test_assumptions_manifest_tournament_leagues() -> None:
    result = MaxWaveEvaluator().evaluate(_problem(mode="tournament", wave=10), _snapshot())
    manifest = result["assumptions_manifest"]
    assert manifest["tournament"]["supported_leagues"] == ["champion", "legend"]
    assert manifest["perk_timeline"]["required"] is False
