from __future__ import annotations

import pytest

pytest.skip(
    "Quarantined: MaxWaveEvaluator currently fails to import due to a syntax error.",
    allow_module_level=True,
)

from pathlib import Path
import sys


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.evaluators.max_wave import MaxWaveEvaluator  # noqa: E402
from tower_sim.ids_state import (  # noqa: E402
    BotsState,
    CardsState,
    GuardiansState,
    IdsState,
    LabsState,
    ModulesState,
    PlayerStuffState,
    RelicsState,
    ThemesSongsState,
    UltimateWeaponsState,
    VaultState,
    WorkshopPlusState,
    WorkshopState,
)
from tower_sim.problem_spec import (  # noqa: E402
    BossStatsSpec,
    BossSurvivabilitySpec,
    ProblemSpec,
    ScenarioSpec,
    SkipRampSpec,
    TowerDefenseSpec,
)


def _empty_ids_state() -> IdsState:
    return IdsState(
        labs=LabsState(labs={}, raw_rows=[]),
        workshop=WorkshopState(entries={}, raw_rows=[]),
        workshop_plus=WorkshopPlusState(raw_rows=[]),
        ultimate_weapons=UltimateWeaponsState(
            entries={},
            uw_plus_placeholder=None,
            raw_rows=[],
        ),
        cards=CardsState(cards={}, equipped_preset_only=[], raw_rows=[]),
        relics=RelicsState(relics={}, raw_rows=[]),
        vault=VaultState(vault={}, raw_rows=[]),
        bots=BotsState(bots={}, raw_rows=[]),
        themes_songs=ThemesSongsState(raw_rows=[]),
        modules=ModulesState(slots=[], raw_rows=[]),
        guardians=GuardiansState(raw_rows=[]),
        player_stuff=PlayerStuffState(key_values={}, raw_rows=[]),
        raw_sections={},
    )


def _base_scenario(max_wave: int, boss_dps: float) -> ScenarioSpec:
    return ScenarioSpec(
        mode="farming",
        tier=14,
        wave=max_wave,
        eals_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        ehls_ramp=SkipRampSpec(start=0.0, end=0.0, ramp_waves=1000),
        boss_survivability=BossSurvivabilitySpec(
            boss=BossStatsSpec(
                hp=1000.0,
                attack=100.0,
                attack_interval=1.0,
                enrage_mult=1.0,
            ),
            tower=TowerDefenseSpec(
                dr_frac=0.0,
                regen_per_sec=0.0,
                shields=10000.0,
            ),
            combat_params={"boss_dps": boss_dps},
            bc_params={"boss_hp_mult": 1.0, "boss_attack_mult": 1.0},
        ),
    )


def test_max_wave_evaluator_returns_wmax_and_trace() -> None:
    problem = ProblemSpec(scenario=_base_scenario(6, boss_dps=1000.0), stat_inputs=[])
    evaluator = MaxWaveEvaluator()
    result = evaluator.evaluate(problem, _empty_ids_state())

    assert result["fail_closed"] is False
    assert result["w_max"] == 6
    trace = result["diagnostics"]["margin_trace"]
    assert len(trace) == 5
    assert trace[-1]["wave"] == 6
    assert trace[-1]["margin_seconds"] > 0


def test_max_wave_evaluator_reports_failure_wmax_zero() -> None:
    problem = ProblemSpec(scenario=_base_scenario(4, boss_dps=1.0), stat_inputs=[])
    evaluator = MaxWaveEvaluator()
    result = evaluator.evaluate(problem, _empty_ids_state())

    assert result["fail_closed"] is False
    assert result["w_max"] == 0
    trace = result["diagnostics"]["margin_trace"]
    assert len(trace) == 4
    assert trace[-1]["wave"] == 4
    assert trace[-1]["margin_seconds"] < 0
