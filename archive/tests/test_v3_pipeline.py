from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from v3.pipeline import (
    StageRequest,
    V3PipelineError,
    compose_at_wave,
    compose_baseline_account,
    compose_full_stats,
    compose_baseline_gem_respec,
    compose_baseline_loadout,
    compose_baseline_max_progression,
    compose_static_stage,
    compose_static_stage_from_ids,
    runtime_state_executor,
)

_IDS_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _snapshot():
    return compile_account_snapshot(parse_ids(_IDS_FIXTURE))


def test_compose_static_stage_baselines_smoke() -> None:
    snapshot = _snapshot()

    account = compose_baseline_account(snapshot, strict_kb_routing=False)
    gem = compose_baseline_gem_respec(snapshot, strict_kb_routing=False)
    loadout = compose_baseline_loadout(snapshot, loadout_context="Farming", strict_kb_routing=False)
    max_prog = compose_baseline_max_progression(
        snapshot,
        loadout_context="Farming",
        mode_policy="normal",
        strict_kb_routing=False,
    )

    assert account.context == "baseline_account"
    assert gem.context == "baseline_gem_respec"
    assert loadout.context == "baseline_loadout"
    assert max_prog.context == "baseline_max_progression"
    assert account.resolved_targets
    assert gem.resolved_targets
    assert loadout.resolved_targets
    assert max_prog.resolved_targets


def test_compose_static_stage_request_object() -> None:
    snapshot = _snapshot()
    request = StageRequest(stage="baseline_loadout", loadout_context="Farming", strict_kb_routing=False, debug=True)
    resolved = compose_static_stage(snapshot, request)
    assert resolved.context == "baseline_loadout"
    assert resolved.debug_breakdowns is not None
    assert "dropped_noncanonical" in resolved.debug_breakdowns
    assert "dropped_kb_unwired" in resolved.debug_breakdowns


def test_compose_at_wave_and_runtime_state_executor() -> None:
    snapshot = _snapshot()
    loadout = compose_baseline_loadout(snapshot, loadout_context="Farming", strict_kb_routing=False)
    seed = compose_at_wave(baseline_loadout=loadout, actual_wave=321)
    result = runtime_state_executor(seed)

    assert seed.at_wave.context == "at_wave"
    assert seed.wave_state.W_actual == 321
    assert result.combat_result["status"] == "not_implemented"


def test_compose_static_stage_from_ids_path() -> None:
    request = StageRequest(stage="baseline_gem_respec", strict_kb_routing=False)
    resolved = compose_static_stage_from_ids(_IDS_FIXTURE, request)
    assert resolved.context == "baseline_gem_respec"
    assert resolved.resolved_targets


def test_compose_at_wave_rejects_invalid_wave() -> None:
    snapshot = _snapshot()
    loadout = compose_baseline_loadout(snapshot, loadout_context="Farming", strict_kb_routing=False)
    with pytest.raises(V3PipelineError, match="actual_wave must be >= 1"):
        compose_at_wave(baseline_loadout=loadout, actual_wave=0)


def test_compose_baseline_max_progression_rejects_empty_mode_policy() -> None:
    with pytest.raises(V3PipelineError, match="mode_policy must be non-empty"):
        compose_baseline_max_progression(_snapshot(), mode_policy="   ")


def test_compose_baseline_account_strict_kb_routing_succeeds() -> None:
    resolved = compose_baseline_account(_snapshot(), strict_kb_routing=True)
    assert resolved.resolved_targets


def test_compose_full_stats_smoke() -> None:
    resolved = compose_full_stats(_snapshot(), strict_kb_routing=True, debug=True)
    assert resolved.context == "full"
    assert resolved.resolved_targets
    assert resolved.debug_breakdowns is not None
