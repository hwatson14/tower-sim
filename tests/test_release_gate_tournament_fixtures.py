from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import TASK_MAX_WAVE, run_task
from tower_sim.run.spec_loader import load_problem_spec, spec_as_dict


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

    assert payload["fail_closed"] is False
    assert payload["w_max"] is not None
    assert manifest["tournament"]["league"] == league
    assert manifest["tournament"]["supported_leagues"] == ["champion", "legend"]
