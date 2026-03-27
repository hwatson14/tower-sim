"""engine/scenario_engine.py — backward-compat shim. AUTHORITY transferred to simulators.scenario (T4).

All imports from this module continue to work unchanged through this re-export shim.
Private symbols are re-exported for backward-compat test consumers. These will be removed in T7.
"""
from simulators.scenario import (
    ScenarioConfig,
    ScenarioSurfaces,
    compute_cf_damage_reduction_pct,
    compute_scenario_surfaces,
    config_from_statbook,
    _interpolate_bc_magnitude,
    _load_boss_enemy_class_resistances,
    _load_tier_battle_conditions,
    _load_tournament_bc_magnitudes,
    _reduce_additive_magnitude,
    _reduce_resistance_multiplier,
    _uptime,
)

__all__ = [
    'ScenarioConfig',
    'ScenarioSurfaces',
    'compute_cf_damage_reduction_pct',
    'compute_scenario_surfaces',
    'config_from_statbook',
    '_interpolate_bc_magnitude',
    '_load_boss_enemy_class_resistances',
    '_load_tier_battle_conditions',
    '_load_tournament_bc_magnitudes',
    '_reduce_additive_magnitude',
    '_reduce_resistance_multiplier',
    '_uptime',
]
