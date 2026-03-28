"""Simulator smoke tests for progression/timing public APIs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_progression_public_api_is_importable__query_callables_exposed():
    from simulators.progression import resolve_progression_consumer_bundle, resolve_progression_family_query

    assert callable(resolve_progression_family_query)
    assert callable(resolve_progression_consumer_bundle)


def test_timing_public_api_is_importable__query_callables_exposed():
    from simulators.timing import compute_timing_surfaces, resolve_timing_consumer_bundle, resolve_timing_family_query

    assert callable(compute_timing_surfaces)
    assert callable(resolve_timing_family_query)
    assert callable(resolve_timing_consumer_bundle)


def test_simulator_modules_reference_qe_imports__expected_qe_strings_present():
    import simulators.progression as progression_module
    import simulators.timing as timing_module

    for mod, name in [(progression_module, "simulators.progression"), (timing_module, "simulators.timing")]:
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "qe." in src or "from qe" in src, f"{name} must import from qe.*"
