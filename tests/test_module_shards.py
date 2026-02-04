from __future__ import annotations

import pytest

from tower_sim.libs.module_shards import dvt_module_shards_cost, shards_to_reach_level


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (1, 0),
        (2, 7),
        (5, 7),
        (6, 12),
        (10, 12),
        (11, 20),
        (160, 4000),
        (161, 5000),
        (200, 5000 + (200 - 161) * 125),
        (201, 10000),
        (300, 49500),
    ],
)
def test_module_shards_cost_boundaries(level: int, expected: int) -> None:
    assert dvt_module_shards_cost(level) == expected


def test_shards_to_reach_level_monotonic() -> None:
    totals = [shards_to_reach_level(level) for level in range(0, 15)]
    assert totals[0] == 0
    assert all(prev <= nxt for prev, nxt in zip(totals, totals[1:]))


def test_shards_to_reach_level_sanity() -> None:
    assert shards_to_reach_level(1) == 0
    assert shards_to_reach_level(2) == dvt_module_shards_cost(1) + dvt_module_shards_cost(2)
