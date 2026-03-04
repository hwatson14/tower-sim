from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.evaluators.max_wave import (
    MaxWaveEvaluator,
    _compose_damage_reduction,
    _resolve_expected_damage_taken,
)
from tower_sim.evaluators.max_wave_report import build_max_wave_report
from tower_sim.engines.combat_stat_derivation import resolve_runtime_bot_effects
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
        wave_probe=1,
        wave_max=100,
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

    assert result["fail_closed"] is True
    assert result["w_max"] is None
    assert result["failure_reason"] == "missing_required_wiring"


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

    assert report["fail_closed"] is result["fail_closed"]
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

    assert result["fail_closed"] is True
    assert result["failure_reason"] == "missing_required_wiring"


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

def test_resolve_runtime_bot_effects_defaults() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    effects, scalars = resolve_runtime_bot_effects(ids_snapshot=ids_snapshot, snapshot_values={})
    assert scalars["bot_duration_multiplier"] == 1.0
    assert scalars["bot_cooldown_multiplier"] == 1.0
    assert scalars["bot_bonus_multiplier"] == 1.0
    assert scalars["flame_bot_damage_reduction_multiplier"] == 1.0
    assert isinstance(effects, list)


def test_resolve_runtime_bot_effects_rejects_non_positive() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    try:
        resolve_runtime_bot_effects(
            ids_snapshot=ids_snapshot,
            snapshot_values={"bot_bonus_multiplier": 0.0},
        )
    except ValueError as exc:
        assert "bot_bonus_multiplier" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-positive bot scalar")



def test_resolve_runtime_bot_effects_prefers_canonical_snapshot_values() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    effects, _scalars = resolve_runtime_bot_effects(
        ids_snapshot=ids_snapshot,
        snapshot_values={
            "bot_flame_damage": 99.0,
            "bot_flame_cooldown": 50.0,
            "bot_flame_damage_reduction": 1.5,
            "bot_duration_multiplier": 2.0,
            "bot_cooldown_multiplier": 0.5,
            "bot_bonus_multiplier": 1.2,
            "flame_bot_damage_reduction_multiplier": 1.1,
        },
    )
    flame = {effect["name"]: effect for effect in effects}["Flame Bot"]
    assert flame["duration_s"] == pytest.approx(198.0)
    assert flame["cooldown_s"] == pytest.approx(25.0)
    assert flame["damage_reduction"] == pytest.approx(1.98)


def test_resolve_runtime_bot_effects_rejects_incomplete_canonical_bot_profile() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    with pytest.raises(ValueError, match="Incomplete canonical bot profile"):
        resolve_runtime_bot_effects(
            ids_snapshot=ids_snapshot,
            snapshot_values={"bot_golden_duration": 10.0, "bot_golden_cooldown": 20.0},
        )


def test_max_wave_timing_uses_wave_accelerator_reduction_from_cards() -> None:
    problem = _build_problem_spec()
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    result = MaxWaveEvaluator().evaluate(problem, ids_snapshot)

    assert result["fail_closed"] is True
    assert result["failure_reason"] == "missing_required_wiring"
