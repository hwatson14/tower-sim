from __future__ import annotations

def build_module_planner_resource_state(
    reroll_shards_on_hand: float,
    module_shards_on_hand: float,
    gems_allocated_to_modules_per_week: float,
    missions_per_week: float,
    farming_hours_per_day: float,
) -> dict:
    vals = {
        "reroll_shards_on_hand": reroll_shards_on_hand,
        "module_shards_on_hand": module_shards_on_hand,
        "gems_allocated_to_modules_per_week": gems_allocated_to_modules_per_week,
        "missions_per_week": missions_per_week,
        "farming_hours_per_day": farming_hours_per_day,
    }
    for k, v in vals.items():
        if v < 0:
            raise ValueError(f"{k} must be non-negative")

    return {
        "reroll_shards_on_hand": float(reroll_shards_on_hand),
        "module_shards_on_hand": float(module_shards_on_hand),
        "gems_allocated_to_modules_per_week": float(gems_allocated_to_modules_per_week),
        "missions_per_week": float(missions_per_week),
        "farming_hours_per_day": float(farming_hours_per_day),
        "resource_state_exactness": "mixed_manual_policy",
    }


def build_module_planner_resource_state_from_qe(qe_surfaces: dict) -> dict:
    _MAP = {
        "reroll_shards_on_hand": "derived::economy.stock.reroll_shards",
        "module_shards_on_hand": "derived::economy.stock.module_shards",
        "gems_allocated_to_modules_per_week": "derived::module.resource_policy.gems_allocated_to_modules_per_week",
        "farming_hours_per_day": "derived::module.runtime_profile.farming_hours_per_day",
        "missions_per_week": "planner.manual_policy.module.missions_per_week",
    }
    missing = [surface for surface in _MAP.values() if surface not in qe_surfaces]
    result = {}
    for key, surface in _MAP.items():
        result[key] = float(qe_surfaces[surface]) if surface in qe_surfaces else None
    has_missions = "planner.manual_policy.module.missions_per_week" in qe_surfaces
    result["resource_state_source"] = "qe_published_surfaces"
    result["resource_state_exactness"] = "qe_routed_manual_policy" if has_missions else "qe_partial"
    result["missing_qe_surfaces"] = missing
    return result
