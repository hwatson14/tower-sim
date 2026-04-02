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


class _InspectorColumnStub:
    def __init__(self):
        self.metrics: list[tuple[str, object]] = []

    def metric(self, label, value):
        self.metrics.append((label, value))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def caption(self, *_args, **_kwargs):
        return None

    def dataframe(self, *_args, **_kwargs):
        return None

    def text_input(self, *_args, **_kwargs):
        return ''

    def toggle(self, _label, value=False, **_kwargs):
        return value


class _InspectorStreamlitStub:
    def __init__(self):
        self.dataframes = []

    def subheader(self, *_args, **_kwargs):
        return None

    def caption(self, *_args, **_kwargs):
        return None

    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def text_input(self, *_args, **_kwargs):
        return ''

    def toggle(self, _label, value=False, **_kwargs):
        return value

    def selectbox(self, _label, options, index=0, **_kwargs):
        return options[index]

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_InspectorColumnStub() for _ in range(count)]

    def dataframe(self, frame, **kwargs):
        self.dataframes.append((frame, kwargs))
        return None


def test_streamlit_inspector_perks_render_path_handles_minimal_qe_rows(monkeypatch):
    import app.streamlit_inspector as inspector_mod

    st_stub = _InspectorStreamlitStub()
    monkeypatch.setattr(inspector_mod, 'st', st_stub)
    monkeypatch.setattr(inspector_mod, '_perk_entity_map', lambda: {'PERK_X': {'perk_name': 'Test Perk', 'category': 'standard'}})
    monkeypatch.setattr(inspector_mod, '_manual_banned_perks', lambda: set())
    monkeypatch.setattr(inspector_mod, '_load_perk_entities', lambda: {'PERK_X': {'max_picks': 1}})
    monkeypatch.setattr(inspector_mod, '_load_perk_effects', lambda: {'PERK_X': [{'operation': 'multiplier', 'effect_value': '1.1', 'effect_index': '1'}]})
    monkeypatch.setattr(inspector_mod, '_scaled_perk_value', lambda **_kwargs: 1.1)

    account_state = {'perk_presets': {'Farming': [{'perk_id': 'PERK_X', 'picks': 1}]}}
    stat_inputs = [{'source_family': 'perk', 'active': True, 'preset_name': 'Farming', 'contributor_id': 'perk::PERK_X::effect_1', 'value': 1.1, 'value_type': 'multiplier'}]

    inspector_mod._render_perks_table(account_state, selected_preset='Farming', stat_inputs_payload=stat_inputs)

    assert st_stub.dataframes
    perk_frame = st_stub.dataframes[-1][0]
    assert perk_frame.loc[0, 'perk'] == 'Test Perk'
    assert perk_frame.loc[0, 'value'] == 'x1.1'


def test_streamlit_inspector_perk_value_formatter_preserves_bool_text_and_units():
    import app.streamlit_inspector as inspector_mod

    assert inspector_mod._format_qe_perk_value(True, 'resolved_value') == 'true'
    assert inspector_mod._format_qe_perk_value(False, 'resolved_value') == 'false'
    assert inspector_mod._format_qe_perk_value(None, 'resolved_value') == ''
    assert inspector_mod._format_qe_perk_value('raw-text', 'resolved_value') == 'raw-text'
    assert inspector_mod._format_qe_perk_value(1.25, 'multiplier') == 'x1.25'
    assert inspector_mod._format_qe_perk_value(5, 'pct') == '+5%'
    assert inspector_mod._format_qe_perk_value(3, 'percentage_points_add') == '+3%'
    assert inspector_mod._format_qe_perk_value(2, 'seconds_add') == '+2s'
    assert inspector_mod._format_qe_perk_value(4, 'flat') == '+4'
    assert inspector_mod._format_qe_perk_value(2.5, 'resolved_value') == '2.5'


def test_streamlit_inspector_perk_rows_group_by_source_name_then_contributor(monkeypatch):
    import app.streamlit_inspector as inspector_mod

    monkeypatch.setattr(inspector_mod, '_perk_entity_map', lambda: {'PERK_X': {'perk_name': 'Test Perk'}})
    rows = [
        {'source_family': 'perk', 'active': True, 'preset_name': 'Farming', 'source_name': 'By Name', 'value': 1.2, 'value_type': 'multiplier'},
        {'source_family': 'perk', 'active': True, 'preset_name': 'Farming', 'contributor_id': 'perk::PERK_X::effect_1', 'value': 4, 'value_type': 'flat'},
    ]
    groups = inspector_mod._perk_rows_from_qe(rows, selected_preset='Farming')

    assert 'By Name' in groups
    assert groups['By Name'][0]['value'] == 1.2
    assert groups['Test Perk'][0]['value'] == 4


def test_streamlit_inspector_perk_lab_bonus_summary_filters_to_active_lab_rows():
    import app.streamlit_inspector as inspector_mod

    rows = [
        {'source_family': 'perk', 'active': True, 'destination_id': 'perk.standard_perks_bonus_pct', 'value': 99},
        {'source_family': 'lab', 'active': False, 'destination_id': 'perk.standard_perks_bonus_pct', 'value': 40},
        {'source_family': 'lab', 'active': True, 'destination_id': 'perk.standard_perks_bonus_pct', 'value': 25},
        {'source_family': 'lab', 'active': True, 'destination_id': 'perk.tradeoff_bonus_pct', 'value': 10},
    ]
    standard_bonus, tradeoff_bonus = inspector_mod._perk_lab_bonus_summary(rows)

    assert standard_bonus == 25
    assert tradeoff_bonus == 10


def test_streamlit_inspector_resolved_statbook_row_map_supports_root_and_preset_payloads():
    import app.streamlit_inspector as inspector_mod

    root_payload = {
        'rows': {
            'state::tower.damage': {'display_value': '12'},
        }
    }
    nested_payload = {
        'Farming': {
            'rows': {
                'state::tower.hp': {'display_value': '34'},
            }
        }
    }

    root_rows = inspector_mod._resolved_statbook_row_map(root_payload)
    nested_rows = inspector_mod._resolved_statbook_row_map(nested_payload)

    assert root_rows['state::tower.damage']['display_value'] == '12'
    assert nested_rows['state::tower.hp']['display_value'] == '34'


def test_streamlit_inspector_qe_metadata_tables_are_arrow_safe(monkeypatch):
    import app.streamlit_inspector as inspector_mod
    from app.pipeline import PipelineRunRequest

    st_stub = _InspectorStreamlitStub()
    monkeypatch.setattr(inspector_mod, 'st', st_stub)
    monkeypatch.setattr(
        inspector_mod,
        'qe_query_rows_frame',
        lambda *_args, **_kwargs: inspector_mod.pd.DataFrame(
            [{'group': 'Tower', 'display_label': 'Damage', 'surface_id': 'state::tower.damage', 'status': 'resolved', 'bundle_id': 'b', 'family_id': 'f', 'contributor_count': 2, 'resolution_order_index': 0, 'has_trace_steps': True}]
        ),
    )
    monkeypatch.setattr(
        inspector_mod,
        'qe_surface_payload',
        lambda *_args, **_kwargs: {
            'surface_id': 'state::tower.damage',
            'raw_surface_id': 'state::tower.damage',
            'status': 'resolved',
            'final_value': 42.0,
            'display_value': '42',
            'value_type': 'scalar',
            'bundle_id': 'b',
            'family_id': 'f',
            'trace_mode': True,
            'contributors': [{'contributor_id': 'c1', 'value': 2.0, 'display_value': '2.0'}],
            'dependency_trace': {'trace_contract_id': 't', 'trace_mode': 'full', 'resolution_order_index': 1, 'has_runtime_trace_steps': False},
        },
    )
    monkeypatch.setattr(
        inspector_mod,
        'qe_trace_summary_frame',
        lambda *_args, **_kwargs: inspector_mod.pd.DataFrame([('trace_mode', 'full'), ('has_runtime_trace_steps', False)], columns=['field', 'value']),
    )
    monkeypatch.setattr(inspector_mod, 'qe_contributor_rows_frame', lambda *_args, **_kwargs: inspector_mod.pd.DataFrame([{'value': 2.0, 'display_value': '2.0'}]))
    monkeypatch.setattr(inspector_mod, 'qe_dependency_nodes_frame', lambda *_args, **_kwargs: inspector_mod.pd.DataFrame(columns=['node_id']))
    monkeypatch.setattr(inspector_mod, 'qe_trace_steps_frame', lambda *_args, **_kwargs: inspector_mod.pd.DataFrame(columns=['step_index']))
    monkeypatch.setattr(inspector_mod, 'qe_plan_coverage_frame', lambda *_args, **_kwargs: inspector_mod.pd.DataFrame(columns=['bundle_kind']))

    request = PipelineRunRequest(ids=Path('input/imports/ids.csv'), out=Path('out'), preset='Farming', state_mode='start_of_run')
    artifacts = {
        'run_stats_query_rows_start_of_run.json': {'Farming': {'rows': {'state::tower.damage': {}}}},
        'run_stats_query_plan_start_of_run.json': {'presets': {}},
    }
    inspector_mod._render_qe(artifacts, request)

    metadata_frames = [frame for frame, _kwargs in st_stub.dataframes if list(getattr(frame, 'columns', [])) == ['field', 'value']]
    assert len(metadata_frames) >= 2
    for frame in metadata_frames[:2]:
        assert frame['value'].map(type).nunique() == 1
        assert frame['value'].map(type).iloc[0] is str


def test_streamlit_inspector_qe_render_smoke_on_real_out_artifacts(monkeypatch):
    import app.streamlit_inspector as inspector_mod
    from app.inspector_data import load_artifacts
    from app.pipeline import PipelineRunRequest

    st_stub = _InspectorStreamlitStub()
    monkeypatch.setattr(inspector_mod, 'st', st_stub)
    artifacts = load_artifacts(ROOT / 'out')
    request = PipelineRunRequest(ids=Path('input/imports/ids.csv'), out=Path('out'), preset='Farming', state_mode='start_of_run')

    inspector_mod._render_qe(artifacts, request)

    assert st_stub.dataframes


def test_run_stats_pipeline_targets_farming_and_tourney():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "preset_names = ['Farming', 'Tourney']" in src


def test_run_stats_pipeline_writes_query_artifacts_not_fake_statbooks():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "run_stats_query_rows_start_of_run.json" in src
    assert "run_stats_query_rows_max_progression.json" in src
    assert "run_stats_query_plan_start_of_run.json" in src
    assert "run_stats_query_plan_max_progression.json" in src
    assert "_remove_legacy_outputs" in src


def test_residue_artifact_contract_is_internally_consistent():
    """Producer keys in pipeline.py must exactly match the keys consumed by publication.py.

    This asserts the end-to-end contract at the source level:
    - Every key written to diagnostics[] in run_analysis_pipeline() must appear
      as a diagnostics.get('<key>') call in write_core_outputs().
    - The filenames written by publication.py are the single authoritative list.
    """
    pipeline_src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    publication_src = Path((ROOT / "app" / "publication.py")).read_text(encoding="utf-8")

    # These are the 5 residue filenames owned by publication.write_core_outputs().
    # Each file must have a matching producer key in pipeline.py diagnostics.
    expected_contract = {
        'tower_regen_closure_report.json':              "diagnostics['tower_regen_closure_report']",
        'tower_hp_semantic_gap_report.json':            "diagnostics['tower_hp_semantic_gap_report']",
        'tower_regen_ep_semantic_gap_report.json':      "diagnostics['tower_regen_ep_semantic_gap_report']",
        'tower_defense_absolute_semantic_gap_report.json': "diagnostics['tower_defense_absolute_semantic_gap_report']",
        'tower_damage_runtime_gap_report.json':         "diagnostics['tower_damage_runtime_gap_report']",
    }

    for filename, producer_assignment in expected_contract.items():
        assert filename in publication_src, (
            f"publication.py does not reference artifact file '{filename}'"
        )
        assert producer_assignment in pipeline_src, (
            f"pipeline.py is missing producer assignment '{producer_assignment}' "
            f"required to populate '{filename}'"
        )

    # Confirm the builder imports are present at module level (not as late stubs)
    assert "_build_tower_regen_ep_semantic_gap_report" in pipeline_src
    assert "_build_tower_defense_absolute_semantic_gap_report" in pipeline_src
    assert "_build_tower_damage_runtime_gap_report" in pipeline_src


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
