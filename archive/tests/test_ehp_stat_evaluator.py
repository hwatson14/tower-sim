from pathlib import Path

from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot


ENABLED_STATS = [
    "tower_hp",
    "tower_regen",
    "def_pct",
    "wall_hp",
    "wall_regen",
]


def test_ehp_stat_evaluator_minimal_slice() -> None:
    ids_raw = parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    snapshot = compile_account_snapshot(ids_raw)
    results = evaluate_stats(snapshot, ENABLED_STATS, allow_out_of_scope=True)

    assert set(results.keys()) == set(ENABLED_STATS)
    for value in results.values():
        assert isinstance(value, (int, float))

    assert results["def_pct"] <= 0.98
    assert results["wall_hp"] >= 0
    assert results["wall_regen"] >= 0
