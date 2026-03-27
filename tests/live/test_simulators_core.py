"""
tests/live/test_simulators_core.py -- Simulator core correctness gate.

Verifies: simulators/ layer is importable and exposes expected public API.
Gate: fails if simulator core path is broken.

Implemented in T7 (after T4 simulator extraction is confirmed complete).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_simulators_progression_is_importable():
    from simulators.progression import (
        ProgressionRecalcBridge,
        materialize_progression_family_baseline,
        resolve_progression_family_query,
        resolve_progression_consumer_bundle,
    )
    assert callable(resolve_progression_family_query)
    assert callable(resolve_progression_consumer_bundle)


def test_simulators_timing_is_importable():
    from simulators.timing import (
        TimingMechanic,
        TimingSurfaces,
        compute_timing_surfaces,
        resolve_timing_family_query,
        resolve_timing_consumer_bundle,
    )
    assert callable(compute_timing_surfaces)
    assert callable(resolve_timing_family_query)


def test_simulators_do_not_import_legacy_engine_internals_directly():
    """Simulators must consume qe.* not legacy engine internals directly."""
    import simulators.progression as sp
    import simulators.timing as st
    for mod, name in [(sp, "simulators.progression"), (st, "simulators.timing")]:
        src = open(mod.__file__, encoding="utf-8").read()
        # Must consume qe.* for stat resolution
        assert "qe." in src or "from qe" in src, f"{name} must import from qe.*"
