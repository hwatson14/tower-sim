from pathlib import Path

from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.loaders.ids_parser import parse_ids


ENABLED_STATS = [
    "tower_hp",
    "tower_regen",
    "def_pct",
    "wall_hp",
    "wall_regen",
]


def test_ehp_stat_evaluator_minimal_slice() -> None:
    ids_state = parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    results = evaluate_stats(ids_state, ENABLED_STATS, allow_out_of_scope=True)

    assert set(results.keys()) == set(ENABLED_STATS)
    for value in results.values():
        assert isinstance(value, (int, float))

    assert results["def_pct"] <= 0.98
    assert results["wall_hp"] >= 0
    assert results["wall_regen"] >= 0
