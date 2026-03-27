"""engine/stat_resolution_core.py - BACKWARD-COMPAT SHIM. Authority: qe.stat_resolution."""
from qe.stat_resolution import *  # noqa: F401, F403
from qe.stat_resolution import (  # noqa: F401
    _canonical_source_multiplier,
    _multiplier_from_value,
    _apply_phase3_postprocessing,
    _load_canonical_stats,
    _resolve_bucket,
    resolve_stats,
)
