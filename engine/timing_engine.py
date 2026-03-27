"""engine/timing_engine.py — backward-compat shim. AUTHORITY transferred to simulators.timing (T4).

All imports from this module continue to work unchanged through this re-export shim.
Private symbols (_uptime, _load_wave_timing_baselines) are re-exported for backward-compat
test/engine consumers. These will be removed in T7.
"""
from simulators.timing import (
    CombatRuntimeSurfaces,
    TimingMechanic,
    TimingSegment,
    TimingSurfaces,
    active_intervals_within_horizon,
    average_active_fraction_over_interval,
    build_default_defensive_timing_mechanics,
    build_default_econ_timing_mechanics,
    build_shared_cycle_segments,
    compile_timing_family_rows,
    compute_average_combined_multiplier,
    compute_average_damage_reduction_fraction_over_interval,
    compute_timing_surfaces,
    is_active_at_time,
    materialize_timing_family_baseline,
    overlap_fraction,
    resolve_combat_runtime_surfaces,
    resolve_consumer_bundle,
    resolve_timing_consumer_bundle,
    resolve_timing_family_query,
    shared_cycle_seconds,
    _load_wave_timing_baselines,
    _uptime,
)
