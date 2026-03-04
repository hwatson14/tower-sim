from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import TASK_MAX_WAVE, run_task
from tower_sim.run.spec_loader import load_problem_spec, spec_as_dict
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition, TierBattleConditions


FIXTURE_SPECS = [
    ("champion", Path("tests/fixtures/specs/tournament_champion_spec.yaml")),
    ("legend", Path("tests/fixtures/specs/tournament_legend_spec.yaml")),
]


def _fixture_ids_snapshot():
    return compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )


@pytest.mark.parametrize(("league", "spec_path"), FIXTURE_SPECS)
def test_release_gate_tournament_fixture_matrix(league: str, spec_path: Path) -> None:
    ids_snapshot = _fixture_ids_snapshot()
    spec = load_problem_spec(spec_path)

    result = run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(spec)},
        ids_snapshot=ids_snapshot,
    )

    payload = result["result"]
    manifest = payload["assumptions_manifest"]

    assert payload["fail_closed"] is True
    assert payload["failure_reason"] == "missing_required_wiring"
    assert payload["w_max"] is None
    assert payload["missing"]
    assert payload["diagnostics"]["contract_status"] == "fail"
    assert payload["diagnostics"]["unmapped_hard_count"] >= 1
    assert manifest["tournament"]["league"] == league
    assert manifest["tournament"]["supported_leagues"] == ["champion", "legend"]
    assert manifest["tournament"]["heat_required"] is True
    assert manifest["tournament"]["bc_required"] is True


def test_release_gate_tournament_fails_closed_on_unsupported_bc_family(monkeypatch) -> None:
    ids_snapshot = _fixture_ids_snapshot()
    spec = load_problem_spec(Path("tests/fixtures/specs/tournament_champion_spec.yaml"))

    def _with_unsupported_bc(*args, **kwargs):
        return TierBattleConditions(
            [
                TierBattleCondition(
                    tier=14,
                    name="Unsupported BC",
                    kind="additive",
                    value=0.05,
                    unit="fraction",
                    notes="fixture unsupported family",
                )
            ]
        )

    monkeypatch.setattr(
        "tower_sim.evaluators.max_wave.load_tier_battle_conditions",
        _with_unsupported_bc,
    )
    monkeypatch.setattr(
        "tower_sim.engines.stat_pipeline.load_tier_battle_conditions",
        _with_unsupported_bc,
    )

    result = run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(spec)},
        ids_snapshot=ids_snapshot,
    )
    payload = result["result"]

    assert payload["fail_closed"] is True
    assert "tier_battle_conditions_unsupported" in payload["missing"]
    assert payload["w_max"] is None
