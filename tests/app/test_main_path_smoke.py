"""App main-path smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_main_entrypoint_is_importable__callable():
    from app.run_stats import main

    assert callable(main)


def test_analysis_entrypoint_is_importable__callable():
    from app.run_analysis import main

    assert callable(main)


def test_pipeline_entrypoints_are_importable__callable():
    from app.pipeline import (
        RunStatsSession,
        execute_pipeline,
        get_default_run_stats_session,
        run_analysis_pipeline,
        run_stats_client,
        run_stats_ensure_local_server,
        run_stats_local_server_is_healthy,
        run_pipeline,
        run_stats_pipeline,
        run_stats_server,
        run_stats_watch_loop,
    )

    assert callable(execute_pipeline)
    assert callable(run_stats_pipeline)
    assert callable(run_stats_server)
    assert callable(run_stats_client)
    assert callable(run_stats_ensure_local_server)
    assert callable(run_stats_local_server_is_healthy)
    assert callable(run_stats_watch_loop)
    assert callable(run_analysis_pipeline)
    assert callable(run_pipeline)
    assert callable(RunStatsSession)
    assert get_default_run_stats_session() is get_default_run_stats_session()


def test_pipeline_module_imports_active_layers__contains_expected_imports():
    import app.pipeline as pipeline_mod

    src = Path(pipeline_mod.__file__).read_text(encoding="utf-8")
    assert "from qe.publication import publish_query_surfaces" in src
    assert "from qe.shared_runtime_context import get_default_qe_shared_runtime_context" in src
    assert "from simulators.progression import resolve_run_stats_progression_bundle" in src
    assert "resolve_run_stats_progression_bundle" in src
    assert "resolve_timing_consumer_bundle" in src
    assert "QEResolutionPlanner" in src
    assert "publish_query_surfaces" in src
    assert "from evaluators.scorer import compute_optimizer_scores" in src
    assert "from input.loader import load_inputs" in src
    assert "from input.runtime_state import build_runtime_state" in src


def test_pipeline_uses_explicit_report_snapshot_path():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "resolve_report_snapshot(" in src
    assert "resolve_snapshot(" not in src


def test_run_stats_cli_defaults_to_current_stats_mode():
    src = Path((ROOT / "app" / "run_stats.py")).read_text(encoding="utf-8")
    assert "--perk-mode" in src
    assert "--watch" in src
    assert "--server" in src
    assert "--use-server" in src
    assert "--state-mode" not in src
    assert "--preset" not in src
    assert "default='none'" in src


def test_run_analysis_cli_preserves_analysis_flags():
    src = Path((ROOT / "app" / "run_analysis.py")).read_text(encoding="utf-8")
    assert "--include-slow-audits" in src
    assert "max_progression_policy" in src


def test_streamlit_inspector_is_importable_when_streamlit_available():
    pytest.importorskip("streamlit")
    import app.streamlit_inspector as inspector_mod

    assert callable(inspector_mod.main)


def test_module_substat_rarity_inference_uses_kb_values_and_assist_cap():
    import app.streamlit_inspector as inspector_mod

    primary_rarity = inspector_mod._infer_module_substat_rarity(
        'armor',
        {'name': 'Knockback Force', 'raw_token': '0.9'},
        role='primary',
        slot_state=None,
    )
    assist_rarity = inspector_mod._infer_module_substat_rarity(
        'armor',
        {'name': 'Knockback Force', 'raw_token': '0.9'},
        role='assist',
        slot_state={'rarity_cap': 'Epic'},
    )
    alias_rarity = inspector_mod._infer_module_substat_rarity(
        'cannon',
        {'name': 'Critical Factor', 'raw_token': '15'},
        role='primary',
        slot_state=None,
    )

    assert primary_rarity == 'Mythic'
    assert assist_rarity == 'Epic'
    assert alias_rarity == 'Ancestral'


def test_module_substat_unlock_count_matches_expected_thresholds():
    import app.streamlit_inspector as inspector_mod

    assert inspector_mod._module_substat_unlock_count(1) == 1
    assert inspector_mod._module_substat_unlock_count(40) == 1
    assert inspector_mod._module_substat_unlock_count(41) == 2
    assert inspector_mod._module_substat_unlock_count(100) == 3
    assert inspector_mod._module_substat_unlock_count(101) == 4
    assert inspector_mod._module_substat_unlock_count(165) == 6
    assert inspector_mod._module_substat_unlock_count(241) == 8

def test_run_stats_pipeline_targets_farming_and_tourney():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "preset_names = ['Farming', 'Tourney']" in src


def test_run_stats_pipeline_writes_query_artifacts_not_fake_statbooks():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "run_stats_query_rows_start_of_run.json" in src
    assert "run_stats_query_rows_max_progression.json" in src
    assert "run_stats_query_plan_start_of_run.json" in src
    assert "run_stats_query_plan_max_progression.json" in src
    assert "_remove_run_stats_legacy_outputs" in src


def test_run_stats_main_prefers_local_server_when_available(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    called = {"ensure": 0, "client": 0, "pipeline": 0}

    def _ensure(args):
        called["ensure"] += 1
        return True

    def _client(args):
        called["client"] += 1
        return 0

    def _pipeline(args):
        called["pipeline"] += 1
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_ensure_local_server", _ensure)
    monkeypatch.setattr(pipeline_mod, "run_stats_client", _client)
    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats"])

    assert run_stats_mod.main() == 0
    assert called == {"ensure": 1, "client": 1, "pipeline": 0}


def test_run_stats_main_falls_back_to_pipeline_when_local_server_cannot_be_ensured(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    called = {"ensure": 0, "client": 0, "pipeline": 0}

    def _ensure(args):
        called["ensure"] += 1
        return False

    def _client(args):
        called["client"] += 1
        return 0

    def _pipeline(args):
        called["pipeline"] += 1
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_ensure_local_server", _ensure)
    monkeypatch.setattr(pipeline_mod, "run_stats_client", _client)
    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats"])

    assert run_stats_mod.main() == 0
    assert called == {"ensure": 1, "client": 0, "pipeline": 1}


def test_run_stats_ensure_local_server_forwards_host_and_port_to_spawned_command(monkeypatch):
    """run_stats_ensure_local_server must pass --host and --port to the spawned server subprocess.

    This exercises the real implementation — not a monkeypatched stub — to verify the
    CLI contract: health checks and the spawned server use the same address.
    """
    import app.pipeline as pipeline_mod
    from types import SimpleNamespace

    spawned_commands = []

    class _FakePopen:
        def __init__(self, command, **kwargs):
            spawned_commands.append(command)

    # Health check always fails so we reach the Popen call, then always fails
    # the retry loop so ensure returns False. We only care about the command built.
    monkeypatch.setattr(pipeline_mod, "run_stats_local_server_is_healthy", lambda args: False)
    monkeypatch.setattr("subprocess.Popen", _FakePopen)

    args = SimpleNamespace(host='0.0.0.0', port=9123)
    pipeline_mod.run_stats_ensure_local_server(args)

    assert len(spawned_commands) == 1, "Expected exactly one Popen call"
    cmd = spawned_commands[0]
    assert '--host' in cmd, "Spawned server command must include --host"
    assert '--port' in cmd, "Spawned server command must include --port"
    host_idx = cmd.index('--host')
    port_idx = cmd.index('--port')
    assert cmd[host_idx + 1] == '0.0.0.0', f"--host value must be forwarded from args; got {cmd[host_idx + 1]!r}"
    assert cmd[port_idx + 1] == '9123', f"--port value must be forwarded from args; got {cmd[port_idx + 1]!r}"
    assert '--server' in cmd, "Spawned command must include --server flag"


def test_run_stats_ensure_local_server_default_host_port_forwarded(monkeypatch):
    """run_stats_ensure_local_server must forward defaults (127.0.0.1:8765) when args has no host/port."""
    import app.pipeline as pipeline_mod
    from types import SimpleNamespace

    spawned_commands = []

    class _FakePopen:
        def __init__(self, command, **kwargs):
            spawned_commands.append(command)

    monkeypatch.setattr(pipeline_mod, "run_stats_local_server_is_healthy", lambda args: False)
    monkeypatch.setattr("subprocess.Popen", _FakePopen)

    # args has no host/port attributes — ensure falls back to defaults
    args = SimpleNamespace()
    pipeline_mod.run_stats_ensure_local_server(args)

    assert len(spawned_commands) == 1
    cmd = spawned_commands[0]
    host_idx = cmd.index('--host')
    port_idx = cmd.index('--port')
    assert cmd[host_idx + 1] == '127.0.0.1'
    assert cmd[port_idx + 1] == '8765'
