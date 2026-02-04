from __future__ import annotations


def dvt_module_shards_cost(level: int) -> int:
    if level < 1:
        raise ValueError(f"Level must be >= 1. Got {level}.")
    if level == 1:
        return 0
    if level <= 5:
        return 7
    if level <= 10:
        return 12
    if level <= 15:
        return 20
    if level <= 20:
        return 25
    if level <= 25:
        return 40
    if level <= 30:
        return 50
    if level <= 35:
        return 75
    if level <= 40:
        return 90
    if level <= 50:
        return 120
    if level <= 60:
        return 180
    if level <= 70:
        return 250
    if level <= 80:
        return 350
    if level <= 90:
        return 500
    if level <= 100:
        return 700
    if level <= 110:
        return 1000
    if level <= 120:
        return 1300
    if level <= 130:
        return 1800
    if level <= 140:
        return 2500
    if level <= 150:
        return 3000
    if level <= 160:
        return 4000
    if level <= 200:
        return 5000 + (level - 161) * 125
    if level == 300:
        return 49500
    if level <= 300:
        return 10000 + (level - 201) * 250
    raise ValueError(f"Unsupported level for shard cost: {level}.")


def shards_to_reach_level(level: int) -> int:
    if level < 0:
        raise ValueError(f"Level must be >= 0. Got {level}.")
    if level == 0:
        return 0
    total = 0
    for current in range(1, level + 1):
        total += dvt_module_shards_cost(current)
    return total
