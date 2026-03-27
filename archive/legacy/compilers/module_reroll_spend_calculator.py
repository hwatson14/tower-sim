from __future__ import annotations


def build_module_reroll_spend_calculator(
    attempts: int,
    base_cost_per_attempt: float | None = None,
    numeric_ladder_closed: bool = False,
) -> dict:
    if not numeric_ladder_closed or base_cost_per_attempt is None:
        return {
            'attempts': int(attempts),
            'estimated_total_reroll_cost': None,
            'cost_exactness': 'blocked_numeric_ladder_unclosed',
            'blocked_reasons': ['numeric_ladder_not_closed'],
        }
    total = float(attempts) * float(base_cost_per_attempt)
    return {
        'attempts': int(attempts),
        'base_cost_per_attempt': float(base_cost_per_attempt),
        'estimated_total_reroll_cost': total,
        'cost_exactness': 'exact_flat_rate',
        'blocked_reasons': [],
    }


_LOCK_COSTS = {
    0: 10.0,
    1: 40.0,
    2: 160.0,
    3: 500.0,
    4: 1000.0,
    5: 1600.0,
    6: 2250.0,
    7: 3000.0,
}

def build_module_reroll_spend_calculator_from_qe(lock_count: int, rolls: int) -> dict:
    if lock_count not in _LOCK_COSTS:
        raise ValueError(f'unsupported lock_count: {lock_count}')
    if rolls <= 0:
        raise ValueError('rolls must be > 0')

    per_roll = _LOCK_COSTS[lock_count]
    total = per_roll * float(rolls)
    return {
        'lock_count': int(lock_count),
        'rolls': int(rolls),
        'reroll_cost_per_roll': per_roll,
        'total_reroll_spend': total,
        'cost_exactness': 'exact_wiki_lock_ladder',
        'blocked_reasons': [],
    }
