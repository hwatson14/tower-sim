"""engine/stat_engine.py - BACKWARD-COMPAT SHIM. Authority: qe.routing."""
from qe.routing import (  # noqa: F401
    resolve_stats,
    _multiplier_from_value,
    _canonical_source_multiplier,
)
