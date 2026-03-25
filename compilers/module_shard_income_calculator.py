from __future__ import annotations


_CORE_REQUIRED = [
    'derived::runtime.eligible_bosses_per_run',
    'derived::runtime.hours_per_run',
    'derived::module.runtime_profile.farming_hours_per_day',
    'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss',
    'derived::module.resource_policy.gems_allocated_to_modules_per_week',
]

_MISSION_REQUIRED = [
    'planner.manual_policy.module.missions_per_week',
]

_MISSION_DAILY_TOTAL = 'derived::module.mission_policy.total_daily_mission_shards'
_MISSION_BONUS_ONLY = 'derived::module.mission_policy.daily_mission_shards_bonus'

_DRAW_POLICY_REQUIRED = [
    'derived::module.draw_policy.gem_cost_per_draw',
    'derived::module.draw_policy.common_rate_pct',
    'derived::module.draw_policy.rare_rate_pct',
    'derived::module.draw_policy.epic_rate_pct',
    'derived::module.shatter_policy.common_module_shards',
    'derived::module.shatter_policy.rare_module_shards',
    'derived::module.draw_policy.epic_draw_immediate_shard_value',
    'derived::module.draw_policy.ten_pull_ev_multiplier',
]


def build_module_shard_income_calculator(
    gems_allocated_to_modules_per_week: float,
    expected_shards_per_draw: float,
    manual_weekly_mission_shards: float,
) -> dict:
    gem_cost_per_draw = 20.0
    draws_per_week = gems_allocated_to_modules_per_week / gem_cost_per_draw if gem_cost_per_draw > 0 else 0.0
    draw_shards = draws_per_week * expected_shards_per_draw
    total = draw_shards + manual_weekly_mission_shards

    return {
        'draws_per_week': draws_per_week,
        'gem_draw_shards_per_week': draw_shards,
        'manual_weekly_mission_shards': manual_weekly_mission_shards,
        'total_weekly_module_shards': total,
        'income_source': 'advisory_manual_inputs',
        'income_exactness': 'advisory_assumed',
    }


def build_module_shard_income_calculator_from_qe(qe_surfaces: dict) -> dict:
    total = float(qe_surfaces.get('derived::economy.income.module_shards', 0))
    gems = float(qe_surfaces.get('derived::module.resource_policy.gems_allocated_to_modules_per_week', 0))
    return {
        'total_weekly_module_shards': total,
        'gems_allocated_to_modules_per_week': gems,
        'income_source': 'qe_published_surface',
        'income_exactness': 'qe_externalized',
    }


def build_module_shard_income_calculator_from_drop_qe(qe_surfaces: dict) -> dict:
    core_missing = [k for k in _CORE_REQUIRED if k not in qe_surfaces]
    if core_missing:
        raise ValueError(f'missing core QE surfaces: {core_missing}')

    hours_per_run = float(qe_surfaces['derived::runtime.hours_per_run'])
    if hours_per_run <= 0:
        raise ValueError('derived::runtime.hours_per_run must be > 0')
    runs_per_week = float(qe_surfaces['derived::module.runtime_profile.farming_hours_per_day']) * 7.0 / hours_per_run
    bosses_per_week = float(qe_surfaces['derived::runtime.eligible_bosses_per_run']) * runs_per_week
    gems_per_week = float(qe_surfaces['derived::module.resource_policy.gems_allocated_to_modules_per_week'])

    boss_drop_shatter_equivalent = bosses_per_week * float(qe_surfaces['derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss'])

    blocked_reasons = []

    # Mission income: prefer total_daily_mission_shards, fall back to bonus-only
    missions_per_week = float(qe_surfaces.get('planner.manual_policy.module.missions_per_week', 0))
    if _MISSION_DAILY_TOTAL in qe_surfaces:
        daily_mission_total = missions_per_week * float(qe_surfaces[_MISSION_DAILY_TOTAL])
    elif _MISSION_BONUS_ONLY in qe_surfaces:
        daily_mission_total = missions_per_week * float(qe_surfaces[_MISSION_BONUS_ONLY])
        blocked_reasons.append('base_daily_mission_shards_unresolved')
    else:
        daily_mission_total = 0.0
        blocked_reasons.append('mission_income_unavailable')

    # Draw policy income: full or partial
    draw_missing = [k for k in _DRAW_POLICY_REQUIRED if k not in qe_surfaces]
    gem_draw_shards_lower_bound_per_week = None

    if not draw_missing:
        # Full draw policy — exact computation
        common_rate = float(qe_surfaces['derived::module.draw_policy.common_rate_pct']) / 100.0
        rare_rate = float(qe_surfaces['derived::module.draw_policy.rare_rate_pct']) / 100.0
        epic_rate = float(qe_surfaces['derived::module.draw_policy.epic_rate_pct']) / 100.0
        common_shards = float(qe_surfaces['derived::module.shatter_policy.common_module_shards'])
        rare_shards = float(qe_surfaces['derived::module.shatter_policy.rare_module_shards'])
        epic_immediate_shards = float(qe_surfaces['derived::module.draw_policy.epic_draw_immediate_shard_value'])
        gem_cost_per_draw = float(qe_surfaces['derived::module.draw_policy.gem_cost_per_draw'])
        draws_per_week = gems_per_week / gem_cost_per_draw if gem_cost_per_draw > 0 else 0.0
        ten_pull_multiplier = float(qe_surfaces['derived::module.draw_policy.ten_pull_ev_multiplier'])

        expected_shards_per_draw = (
            common_rate * common_shards
            + rare_rate * rare_shards
            + epic_rate * epic_immediate_shards
        ) * ten_pull_multiplier
        draw_shards_per_week = draws_per_week * expected_shards_per_draw
    else:
        # Check if we can compute a lower bound from common+rare only
        _LOWER_BOUND_KEYS = [
            'derived::module.draw_policy.gem_cost_per_draw',
            'derived::module.draw_policy.common_rate_pct',
            'derived::module.draw_policy.rare_rate_pct',
            'derived::module.shatter_policy.common_module_shards',
            'derived::module.shatter_policy.rare_module_shards',
        ]
        lb_missing = [k for k in _LOWER_BOUND_KEYS if k not in qe_surfaces]
        if not lb_missing:
            common_rate = float(qe_surfaces['derived::module.draw_policy.common_rate_pct']) / 100.0
            rare_rate = float(qe_surfaces['derived::module.draw_policy.rare_rate_pct']) / 100.0
            common_shards = float(qe_surfaces['derived::module.shatter_policy.common_module_shards'])
            rare_shards = float(qe_surfaces['derived::module.shatter_policy.rare_module_shards'])
            gem_cost_per_draw = float(qe_surfaces['derived::module.draw_policy.gem_cost_per_draw'])
            draws_per_week = gems_per_week / gem_cost_per_draw if gem_cost_per_draw > 0 else 0.0
            lower_bound_per_draw = common_rate * common_shards + rare_rate * rare_shards
            gem_draw_shards_lower_bound_per_week = draws_per_week * lower_bound_per_draw
            blocked_reasons.append('epic_draw_shard_equivalent_unresolved')
        else:
            blocked_reasons.append('draw_policy_surfaces_unavailable')

        expected_shards_per_draw = 0.0
        draw_shards_per_week = 0.0

    total = boss_drop_shatter_equivalent + daily_mission_total + draw_shards_per_week

    if blocked_reasons:
        exactness = 'partial_deterministic_shatter_equivalent'
    else:
        exactness = 'exact_under_package_draw_policy'

    result = {
        'runs_per_week': runs_per_week,
        'eligible_bosses_per_week': bosses_per_week,
        'boss_drop_shatter_equivalent_shards_per_week': boss_drop_shatter_equivalent,
        'daily_mission_total_shards_per_week': daily_mission_total,
        'gem_draw_shards_per_week': draw_shards_per_week,
        'expected_shards_per_draw': expected_shards_per_draw,
        'gems_allocated_to_modules_per_week': gems_per_week,
        'total_weekly_module_shards': total,
        'income_source': 'qe_drop_policy_mission_policy_draw_policy_surfaces',
        'income_exactness': exactness,
        'blocked_reasons': blocked_reasons,
    }
    if gem_draw_shards_lower_bound_per_week is not None:
        result['gem_draw_shards_lower_bound_per_week'] = gem_draw_shards_lower_bound_per_week
    return result
