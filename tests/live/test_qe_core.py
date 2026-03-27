"""
tests/live/test_qe_core.py -- QE core correctness gate (T3B).

All imports are from qe.* directly. Verifies that qe/ is the live authority
for deterministic stat/query resolution -- not just an extracted copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# All symbols imported directly from qe.* -- no engine/models shims
from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    normalize_preset_name,
    to_v2_surface_id,
    to_legacy_surface_id,
)
from qe.models import (
    StatInput,
    StatBook,
    StatRow,
    StateIdentity,
    BoundPresetFamily,
    bind_preset_family,
)
from qe.kernel import StatQueryKernel, QueryResponse
from qe.materializer import FamilyBaselineMaterializer
from qe.routing import resolve_stats
from qe.publication import publish_phase3_query_surfaces

from tests.helpers import build_state, build_family_baseline


# ---------------------------------------------------------------------------
# qe.contracts
# ---------------------------------------------------------------------------

def test_canonical_preset_names_non_empty():
    assert len(CANONICAL_PRESET_NAMES) >= 2
    assert "Farming" in CANONICAL_PRESET_NAMES
    assert "Tourney" in CANONICAL_PRESET_NAMES


def test_normalize_preset_name_canonical():
    assert normalize_preset_name("Farming", allow_aliases=False) == "Farming"
    assert normalize_preset_name(None, allow_aliases=False) is None
    assert normalize_preset_name("", allow_aliases=False) is None


def test_surface_id_roundtrip():
    v2 = to_v2_surface_id("canonical_stat::tower_defense_pct")
    assert v2 == "state::tower.defense_pct", f"Unexpected v2 id: {v2}"
    legacy = to_legacy_surface_id("state::tower.defense_pct")
    assert legacy == "canonical_stat::tower_defense_pct", f"Unexpected legacy id: {legacy}"


def test_to_v2_surface_id_passthrough():
    # A surface with no remap entry should pass through unchanged
    result = to_v2_surface_id("state::some.unknown.surface")
    assert result == "state::some.unknown.surface"


# ---------------------------------------------------------------------------
# qe.models
# ---------------------------------------------------------------------------

def test_stat_input_construction():
    si = StatInput(
        stat_name="tower.hp",
        source_family="lab",
        source_name="health",
        value=1000.0,
        value_type="scalar",
        stage="additive_pre_cap",
    )
    assert si.stat_name == "tower.hp"
    assert si.active is True


def test_bound_preset_family_canonical():
    bpf = bind_preset_family(
        preset_name="Farming",
        state_mode="start_of_run",
        perk_namespace_class="canonical",
        explicit_card_preset_name=None,
        explicit_module_preset_name=None,
        explicit_perk_preset_name=None,
        active_perk_preset_name=None,
        perks_enabled=False,
    )
    assert bpf.preset_name == "Farming"
    assert bpf.perks_enabled is False


def test_state_identity_as_tuple():
    si = StateIdentity(
        account_snapshot_id="acct_abc",
        loadout_id="loadout_xyz",
        scenario_id="scen_123",
        runtime_branch_id="branch_base",
    )
    assert si.as_tuple() == ("acct_abc", "loadout_xyz", "scen_123", "branch_base")


# ---------------------------------------------------------------------------
# qe.kernel + qe.routing via family baseline
# ---------------------------------------------------------------------------

def test_resolve_stats_returns_statbook():
    """resolve_stats produces a StatBook with rows for known progression surfaces."""
    account_state = build_state()
    from qe.stat_input_compiler import compile_stat_inputs
    stat_inputs = list(compile_stat_inputs(account_state, preset_name="Farming", state_mode="start_of_run"))
    result = resolve_stats(stat_inputs)
    assert isinstance(result, StatBook)
    assert len(result.rows) > 0


def test_resolve_stats_defense_pct_no_type_error():
    """The defense_pct mixed-value-type bug (T3B) must be fixed.

    The QE kernel resolves state::tower.defense_pct via the delegated progression family.
    The merged StatBook keys surfaces under fallback naming (canonical_stat::), so v2
    surface IDs from the delegation are not injected into the flat result. The critical
    guarantee is that resolve_stats does not raise ValueError about mixed value types.
    Direct kernel resolution of the v2 surface ID is verified separately via the kernel test.
    """
    account_state = build_state()
    from qe.stat_input_compiler import compile_stat_inputs
    stat_inputs = list(compile_stat_inputs(account_state, preset_name="Farming", state_mode="start_of_run"))
    # Must not raise ValueError about mixed value types for defense_pct
    result = resolve_stats(stat_inputs)
    assert isinstance(result, StatBook)
    # Delegation succeeded: diagnostic confirms the QE family was invoked
    delegation = result.diagnostics.get('resolve_stats_delegation', {})
    assert delegation.get('delegated_family_id') == 'progression_start_of_run'
    assert 'state::tower.defense_pct' in delegation.get('delegated_surface_ids', [])


def test_stat_query_kernel_progression_family():
    """StatQueryKernel can be instantiated and resolves the progression family."""
    baseline = build_family_baseline("progression_start_of_run")
    kernel = StatQueryKernel()
    from qe.routing import _PROGRESSION_V1_SURFACE_IDS
    response = kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=_PROGRESSION_V1_SURFACE_IDS[:3],
        trace_mode="contributors",
    )
    assert isinstance(response, QueryResponse)
    assert len(response.resolved_surface_rows) == 3


def test_stat_query_kernel_timing_family():
    """StatQueryKernel resolves timing family surfaces."""
    baseline = build_family_baseline("timing_farm_with_perks")
    kernel = StatQueryKernel()
    from qe.routing import _TIMING_V1_SURFACE_IDS
    response = kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=_TIMING_V1_SURFACE_IDS[:2],
        trace_mode="none",
    )
    assert isinstance(response, QueryResponse)
    assert len(response.resolved_surface_rows) == 2


# ---------------------------------------------------------------------------
# qe.materializer
# ---------------------------------------------------------------------------

def test_family_baseline_materializer_instantiates():
    materializer = FamilyBaselineMaterializer()
    assert materializer is not None


def test_family_baseline_from_helper():
    baseline = build_family_baseline("progression_start_of_run")
    assert baseline is not None
    # FamilyBaselineContributorMap should have at least one surface entry
    from qe.materializer import FamilyBaselineContributorMap
    assert isinstance(baseline, FamilyBaselineContributorMap)
