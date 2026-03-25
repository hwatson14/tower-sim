from __future__ import annotations


def build_module_reroll_income_calculator(
    runtime_profile: dict,
    farming_hours_per_day: float,
    cash_mastery_drop_chance_pct: float,
) -> dict:
    elites = float(runtime_profile.get("elites_per_run", 0))
    hours_per_run = float(runtime_profile.get("hours_per_run", 1))
    if hours_per_run <= 0:
        raise ValueError("hours_per_run must be > 0")
    runs_per_week = farming_hours_per_day * 7.0 / hours_per_run
    bosses_per_week = elites * runs_per_week
    assumed_shards_per_boss = 1.0
    drop_chance = cash_mastery_drop_chance_pct / 100.0
    expected_weekly = bosses_per_week * drop_chance * assumed_shards_per_boss

    return {
        "runs_per_week": runs_per_week,
        "eligible_bosses_per_week": bosses_per_week,
        "reroll_shard_drop_chance_pct": cash_mastery_drop_chance_pct,
        "reroll_shards_per_boss": assumed_shards_per_boss,
        "total_weekly_reroll_income": expected_weekly,
        "income_source": "advisory_manual_inputs",
        "income_exactness": "advisory_assumed_drop_quantity",
    }


def build_module_reroll_income_calculator_from_qe(qe_surfaces: dict) -> dict:
    total = float(qe_surfaces.get("derived::economy.income.reroll_shards", 0))
    farming = float(qe_surfaces.get("derived::module.runtime_profile.farming_hours_per_day", 0))
    return {
        "total_weekly_reroll_income": total,
        "farming_hours_per_day": farming,
        "income_source": "qe_published_surface",
        "income_exactness": "qe_externalized",
    }


def build_module_reroll_income_calculator_from_drop_qe(qe_surfaces: dict) -> dict:
    required = [
        'derived::runtime.eligible_bosses_per_run',
        'derived::runtime.hours_per_run',
        'derived::module.runtime_profile.farming_hours_per_day',
        'derived::module.drop_policy.reroll_shard_drop_chance_pct',
        'derived::module.drop_policy.reroll_shards_per_boss',
    ]
    missing = [k for k in required if k not in qe_surfaces]
    if missing:
        raise ValueError(f'missing QE surfaces: {missing}')

    hours_per_run = float(qe_surfaces['derived::runtime.hours_per_run'])
    if hours_per_run <= 0:
        raise ValueError('derived::runtime.hours_per_run must be > 0')
    runs_per_week = float(qe_surfaces['derived::module.runtime_profile.farming_hours_per_day']) * 7.0 / hours_per_run
    bosses_per_week = float(qe_surfaces['derived::runtime.eligible_bosses_per_run']) * runs_per_week
    drop_chance = float(qe_surfaces['derived::module.drop_policy.reroll_shard_drop_chance_pct']) / 100.0
    shards_per_boss = float(qe_surfaces['derived::module.drop_policy.reroll_shards_per_boss'])
    expected_weekly = bosses_per_week * drop_chance * shards_per_boss

    return {
        'runs_per_week': runs_per_week,
        'eligible_bosses_per_week': bosses_per_week,
        'reroll_shard_drop_chance_pct': drop_chance * 100.0,
        'reroll_shards_per_boss': shards_per_boss,
        'total_weekly_reroll_income': expected_weekly,
        'income_source': 'qe_drop_policy_surfaces',
        'income_exactness': 'qe_routed_manual_plus_wiki_truth',
    }
