"""engine/progression_recalc_bridge.py — backward-compat shim. AUTHORITY transferred to simulators.progression (T4).

All imports from this module continue to work unchanged through this re-export shim.
"""
from simulators.progression import (
    ProgressionRecalcBridge,
    ProgressionRecalcRequest,
    ProgressionRecalcResult,
    compile_stat_inputs,
    compile_stat_inputs_with_identity,
    load_family_surface_ids,
    materialize_progression_family_baseline,
    resolve_consumer_bundle,
    resolve_progression_consumer_bundle,
    resolve_progression_family_query,
)
