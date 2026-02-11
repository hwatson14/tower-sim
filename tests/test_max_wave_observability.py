from __future__ import annotations

from pathlib import Path

from tower_sim.evaluators.max_wave import (
    MaxWaveEvaluator,
    _compose_damage_reduction,
    _resolve_expected_damage_taken,
)
from tower_sim.evaluators.max_wave_report import build_max_wave_report
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.registry.stat_registry import Phase
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


def _build_problem_spec() -> ProblemSpec:
    scenario = ScenarioSpec(
        mode="farming",
        tier=12,
        wave=1,
        eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        boss_survivability=BossSurvivabilitySpec(
            boss=BossStatsSpec(
                hp=1.0,
                attack=1.0,
                attack_interval=1.0,
                enrage_mult=1.0,
            ),
            tower=TowerDefenseSpec(
                dr_frac=0.0,
                regen_per_sec=0.0,
                shields=0.0,
            ),
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


def test_max_wave_returns_failure_snapshot() -> None:
    problem = _build_problem_spec()

    evaluator = MaxWaveEvaluator()
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    result = evaluator.evaluate(problem, ids_snapshot)

    assert result["fail_closed"] is False
    assert result["w_max"] == 0
    assert result["failure_wave"] == 1
    assert result["failure_reason"] == "boss_kills_tower"
    snapshot = result["at_failure_snapshot"]
    assert snapshot["wave"] == 1
    assert "tower_stats" in snapshot
    assert "boss_stats" in snapshot
    assert snapshot["margins"]["margin_seconds"] is not None


def test_max_wave_report_includes_debug_sections() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    evaluator = MaxWaveEvaluator()
    problem = _build_problem_spec()
    result = evaluator.evaluate(problem, ids_snapshot)

    report = build_max_wave_report(
        problem,
        ids_snapshot,
        result,
        module_context="Testing",
        allow_provisional=True,
        include_trace=True,
    )

    assert report["fail_closed"] is False
    assert "base_state" in report
    assert "inventory" in report
    assert "loadout_compilation" in report
    assert "wave_mapping" in report
    assert "trace" in report
    assert len(report["trace"]) <= 20


def test_max_wave_includes_timing_uptime_diagnostics() -> None:
    problem = _build_problem_spec()
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    result = MaxWaveEvaluator().evaluate(problem, ids_snapshot)

    timing = result["diagnostics"]["timing_uptime"]
    assert timing["package_event_model"] == "uniform_from_rate"
    assert "wa_reduction" in timing
    assert "gcomp_enabled" in timing
    assert "expected_coin_multiplier" in timing or "missing" in timing
    assert timing["contract_scope"]["contract_status"] == "excluded"


def test_timing_damage_reduction_composition() -> None:
    # Base DR and timing expected-damage-taken compose multiplicatively on damage taken.
    composed = _compose_damage_reduction(
        base_damage_reduction=0.30,
        expected_damage_taken=0.80,
    )
    assert abs(composed - 0.44) < 1e-12


def test_resolve_expected_damage_taken_from_timing_diag() -> None:
    timing = {"expected_damage_taken": 1.0}
    assert _resolve_expected_damage_taken(timing) == 1.0
    assert timing["contract_scope"]["contract_status"] == "consumed"
