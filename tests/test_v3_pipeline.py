from pathlib import Path

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from v3.pipeline import (
    StageRequest,
    compose_at_wave,
    compose_baseline_account,
    compose_baseline_gem_respec,
    compose_baseline_loadout,
    compose_baseline_max_progression,
    compose_static_stage,
    runtime_state_executor,
)

_IDS_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _snapshot():
    return compile_account_snapshot(parse_ids(_IDS_FIXTURE))


def test_compose_static_stage_baselines_smoke() -> None:
    snapshot = _snapshot()

    account = compose_baseline_account(snapshot)
    gem = compose_baseline_gem_respec(snapshot)
    loadout = compose_baseline_loadout(snapshot, loadout_context="Farming")
    max_prog = compose_baseline_max_progression(
        snapshot,
        loadout_context="Farming",
        mode_policy="normal",
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
    request = StageRequest(stage="baseline_loadout", loadout_context="Farming", debug=True)
    resolved = compose_static_stage(snapshot, request)
    assert resolved.context == "baseline_loadout"
    assert resolved.debug_breakdowns is not None


def test_compose_at_wave_and_runtime_state_executor() -> None:
    snapshot = _snapshot()
    loadout = compose_baseline_loadout(snapshot, loadout_context="Farming")
    seed = compose_at_wave(baseline_loadout=loadout, actual_wave=321)
    result = runtime_state_executor(seed)

    assert seed.at_wave.context == "at_wave"
    assert seed.wave_state.W_actual == 321
    assert result.combat_result["status"] == "not_implemented"
