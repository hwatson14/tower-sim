from __future__ import annotations

from pathlib import Path

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.engines.stat_engine import StatInput
from tower_sim.engines.combat_stat_derivation import (
    build_canonical_wave_row,
    cached_tournament_heat_table,
    canonical_stat_inputs_for_wave,
    TOURNAMENT_HEAT_BC_IDS,
    CanonicalStatInputBuild,
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
from tower_sim.run.spec_loader import load_problem_spec


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
    updated, diag = canonical_stat_inputs_for_wave(
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
    cached_tournament_heat_table.cache_clear()
    calls = {"count": 0}

    called_ids = []

    class _FakeTable:
        def value_at(self, *, league: str, wave_actual: int, bc_id: str):
            called_ids.append(bc_id)

            class _Row:
                value_num = 1.0

            return _Row()

    def _fake_loader(scale_path, registry_path):
        calls["count"] += 1
        return _FakeTable()

    monkeypatch.setattr("tower_sim.engines.combat_stat_derivation.load_tournament_heat_table", _fake_loader)

    problem = _problem(mode="tournament", wave=2)
    registry = default_registry()

    row1, missing1 = build_canonical_wave_row(problem, registry, wave=1)
    row2, missing2 = build_canonical_wave_row(problem, registry, wave=2)

    assert not missing1
    assert not missing2
    assert row1 is not None
    assert row2 is not None
    assert calls["count"] == 1
    assert tuple(called_ids[: len(TOURNAMENT_HEAT_BC_IDS)]) == TOURNAMENT_HEAT_BC_IDS
    assert tuple(called_ids[len(TOURNAMENT_HEAT_BC_IDS):]) == TOURNAMENT_HEAT_BC_IDS


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
        stat_inputs=[s for s in base_problem.stat_inputs if s.stat_id != "orb_damage_mult"],
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


def test_max_wave_reports_override_policy_mode() -> None:
    strict_problem = _problem(mode="farming", wave=10)
    strict_result = MaxWaveEvaluator().evaluate(strict_problem, _snapshot())
    assert strict_result["diagnostics"]["core_stat_override_policy"] == "strict_fail_closed"

    relaxed_scenario = ScenarioSpec(
        mode=strict_problem.scenario.mode,
        tier=strict_problem.scenario.tier,
        league=strict_problem.scenario.league,
        wave=strict_problem.scenario.wave,
        eals_ramp=strict_problem.scenario.eals_ramp,
        ehls_ramp=strict_problem.scenario.ehls_ramp,
        perk_timeline_path=strict_problem.scenario.perk_timeline_path,
        boss_survivability=strict_problem.scenario.boss_survivability,
        allow_core_stat_overrides=True,
    )
    relaxed_problem = ProblemSpec(
        scenario=relaxed_scenario,
        stat_inputs=strict_problem.stat_inputs,
        evaluator=strict_problem.evaluator,
    )
    relaxed_result = MaxWaveEvaluator().evaluate(relaxed_problem, _snapshot())
    assert relaxed_result["diagnostics"]["core_stat_override_policy"] == "explicit_override_mode"


def test_max_wave_emits_combat_snapshot_source_diagnostics() -> None:
    result = MaxWaveEvaluator().evaluate(_problem(mode="farming", wave=10), _snapshot())
    diag = result["diagnostics"]
    assert "combat_snapshot_sources_scenario_wave" in diag
    assert "combat_snapshot_sources" in diag["w_max_search"]
    assert "10" in diag["w_max_search"]["combat_snapshot_sources"]
    assert "tower_hp" in diag["combat_snapshot_sources_scenario_wave"]


def test_sample_spec_fixture_produces_nonzero_max_wave() -> None:
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.yaml"))
    result = MaxWaveEvaluator().evaluate(spec, _snapshot())

    assert result["fail_closed"] is False
    assert result["w_max"] is not None
    assert result["w_max"] > 0


def test_preflight_returns_validation_only() -> None:
    evaluator = MaxWaveEvaluator()
    result = evaluator.preflight(_problem(mode="farming", wave=10), _snapshot())
    assert result["w_max"] is None
    assert "w_max_search" not in result["diagnostics"]
    assert result["override_collisions"] == []


def test_evaluate_short_circuits_search_on_preflight_fail(monkeypatch) -> None:
    base_problem = _problem(mode="farming", wave=10)
    problem = ProblemSpec(
        scenario=base_problem.scenario,
        stat_inputs=[s for s in base_problem.stat_inputs if s.stat_id != "orb_damage_mult"],
        evaluator=base_problem.evaluator,
    )

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("search should not run when preflight fails")

    monkeypatch.setattr("tower_sim.evaluators.max_wave._search_wmax", _fail_if_called)
    result = MaxWaveEvaluator().evaluate(problem, _snapshot())
    assert result["fail_closed"] is True
    assert "stat_input:orb_damage_mult" in result["missing"]


def test_override_collisions_are_reported_outside_missing(monkeypatch) -> None:
    base_problem = _problem(mode="farming", wave=10)

    class _Compiled:
        missing = []
        stat_inputs = [
            StatInput(
                stat_id="tower_hp",
                phase=Phase.START_OF_RUN,
                base_value=999.0,
                provenance="compiled",
            )
        ]

    monkeypatch.setattr(
        "tower_sim.engines.combat_stat_derivation.compile_full_stat_inputs",
        lambda _ids: _Compiled(),
    )
    result = MaxWaveEvaluator().evaluate(base_problem, _snapshot())
    assert result["fail_closed"] is True
    assert result["override_collisions"] == ["tower_hp@start_of_run"]
    assert "stat_override:tower_hp@start_of_run" not in result["missing"]


def test_preflight_reports_duration_ms() -> None:
    result = MaxWaveEvaluator().preflight(_problem(mode="farming", wave=10), _snapshot())
    assert isinstance(result["diagnostics"]["preflight_ms"], float)
    assert result["diagnostics"]["preflight_ms"] >= 0.0



def test_preflight_does_not_run_heavy_builds(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise AssertionError("heavy path should not run in preflight")

    monkeypatch.setattr("tower_sim.evaluators.max_wave.StatEngine.build", _raise)
    monkeypatch.setattr("tower_sim.evaluators.max_wave.StatEngine.build_with_tier_rules", _raise)
    monkeypatch.setattr("tower_sim.evaluators.max_wave._resolve_wave_snapshot", _raise)

    result = MaxWaveEvaluator().preflight(_problem(mode="farming", wave=10), _snapshot())
    assert result["w_max"] is None


def test_runner_contract_schema_stability() -> None:
    evaluator = MaxWaveEvaluator()
    preflight = evaluator.preflight(_problem(mode="farming", wave=10), _snapshot())
    evaluate = evaluator.evaluate(_problem(mode="farming", wave=10), _snapshot())

    assert set(preflight.keys()) == {
        "evaluator",
        "fail_closed",
        "missing",
        "override_collisions",
        "w_max",
        "diagnostics",
        "assumptions_manifest",
    }
    assert set(evaluate.keys()) >= {
        "evaluator",
        "fail_closed",
        "missing",
        "override_collisions",
        "w_max",
        "diagnostics",
        "assumptions_manifest",
    }
    assert isinstance(preflight["override_collisions"], list)
    assert isinstance(evaluate["override_collisions"], list)
    assert preflight["w_max"] is None


def test_preflight_fails_closed_for_decisive_unmapped_or_unsupported(monkeypatch) -> None:
    def _stub_build(*, problem_spec, ids_snapshot, registry):
        stat_inputs = [spec.to_stat_input() for spec in problem_spec.stat_inputs]
        return CanonicalStatInputBuild(
            stat_inputs=stat_inputs,
            blocked_core_overrides=[],
            invalid_stat_inputs=[],
            missing_required_stat_inputs=[],
            compiled_missing=["workshop_unsupported:Health"],
            core_stat_override_policy="strict_fail_closed",
        )

    monkeypatch.setattr("tower_sim.evaluators.max_wave.build_canonical_stat_inputs", _stub_build)
    result = MaxWaveEvaluator().preflight(_problem(mode="farming", wave=10), _snapshot())

    assert result["fail_closed"] is True
    assert any(item.startswith("ids_unmapped_or_unsupported:workshop_unsupported:Health") for item in result["missing"])


def test_preflight_emits_canonical_naming_contract_diagnostics() -> None:
    result = MaxWaveEvaluator().preflight(_problem(mode="farming", wave=10), _snapshot())
    contract = result["diagnostics"]["canonical_naming_contract"]

    assert contract["status"] == "ok"
    assert contract["aliases"]["health"] == "tower_hp"
    assert contract["aliases"]["wall regen"] == "wall_regen"
