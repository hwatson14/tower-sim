from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def start_of_run_pipeline_result(tmp_path_factory: pytest.TempPathFactory):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path_factory.mktemp("start_of_run_pipeline_out")
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='start_of_run',
        )
    )
    assert result.exit_code == 0
    return result


@pytest.fixture(scope="module")
def canonical_pipeline_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path_factory.mktemp("canonical_pipeline_out")
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='start_of_run',
        )
    )
    assert result.exit_code == 0

    return {
        'diagnostics': json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8')),
        'statbook_publishable': json.loads((out_dir / 'statbook_publishable.json').read_text(encoding='utf-8')),
        'optimizer_scores': json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8')),
        'ep_oracle_compare': json.loads((out_dir / 'ep_oracle_compare.json').read_text(encoding='utf-8')),
        'pipeline_trace': json.loads((out_dir / 'pipeline_trace.json').read_text(encoding='utf-8')),
        'dashboards': {
            'input_dashboard': json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8')),
            'stats_dashboard': json.loads((out_dir / 'stats_dashboard.json').read_text(encoding='utf-8')),
        },
        'out_dir': out_dir,
    }


def test_request_adapter_and_execute_pipeline_emit_trace(start_of_run_pipeline_result):
    result = start_of_run_pipeline_result

    assert result.exit_code == 0
    assert (result.out_dir / 'pipeline_trace.json').exists()
    trace = result.pipeline_trace.to_dict()
    assert trace['execution_path']['recompute_mode'] is not None
    assert 'cache_status' in trace['execution_path']
    assert 'runtime_consumers' in trace['execution_path']
    stage_ids = [stage['stage_id'] for stage in trace['stages']]
    assert stage_ids[:4] == ['input_load', 'runtime_account_assembly', 'compare_materialization', 'stat_resolution']
    assert 'artifact_write' in stage_ids
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == 'input/manual_inputs.yaml'


@pytest.mark.live
def test_trace_input_load_manual_inputs_path_respects_override(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    manual_inputs_override = tmp_path / 'manual_inputs.partial.yaml'
    manual_inputs_override.write_text('player:\\n  profile_name: fixture-partial\\n', encoding='utf-8')
    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
        manual_inputs=manual_inputs_override,
    )
    result = execute_pipeline(request)

    assert result.exit_code == 0
    trace = result.pipeline_trace.to_dict()
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == manual_inputs_override.as_posix()


def test_trace_artifact_is_listed_in_generated_files(start_of_run_pipeline_result):
    result = start_of_run_pipeline_result
    generated = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in generated


def _streamlit_widget_by_label(widgets, label: str):
    matches = [widget for widget in widgets if getattr(widget, 'label', None) == label]
    assert len(matches) == 1, f"expected one {label!r} widget, found {len(matches)}"
    return matches[0]


def _set_streamlit_text_input(app_test, label: str, value: str) -> None:
    _streamlit_widget_by_label(app_test.text_input, label).set_value(value)


def _set_streamlit_selectbox(app_test, label: str, value: str) -> None:
    _streamlit_widget_by_label(app_test.selectbox, label).set_value(value)


def _click_streamlit_button(app_test, label: str) -> None:
    _streamlit_widget_by_label(app_test.button, label).click()


def _streamlit_labels(widgets) -> list[str]:
    return [str(getattr(widget, 'label', '')) for widget in widgets]


def _streamlit_values(widgets) -> list[str]:
    return [str(getattr(widget, 'value', '')) for widget in widgets]


def test_streamlit_boss_waves_exposes_only_wired_manual_runtime_inputs():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert 'Combat assumptions' in source
    assert 'Recommended model assumptions' in source
    assert 'Use recommended model assumptions' in source
    assert 'BOSS_WAVE_RECOMMENDED_MODEL_RUNTIME_INPUTS' in source
    assert "'flame_bot_damage_reduction_pct': 95.0" in source
    assert "'boss_edamage_target_share': 0.005051405075429985" in source
    assert 'not a recommended default' in source
    assert 'matrix calibration median input is comparison-only' in source
    assert 'Override boss damage calibration' in source
    assert 'Advanced damage calibration' not in source
    assert "number_input('End wave', min_value=10, value=10000, step=10)" in source
    assert "selectbox(\n        'Run type'," in source
    assert 'BOSS_WAVE_DISSONANCE_RUN_LABELS' in source
    assert 'Align clean rows to IDS references' in source
    assert "checkbox('Align clean rows to IDS references', value=True)" in source
    assert 'All run types' in source
    assert 'All tiers' in source
    assert 'matrix_tiers = tuple(range(1, 22)) if bool(matrix_all_tiers) else (int(tier_number),)' in source
    assert 'align_clean_reference_rows=bool(align_clean_reference_rows)' in source
    assert 'Non-boss pressure closure' in source
    assert 'Pressure factor closure' in source
    assert 'boss_wave_pressure_factor' in source
    assert 'Damage/Health Decay closure' in source
    assert 'Damage/Health Decay required fields' in source
    assert 'Damage/Health Decay missing fields' in source
    assert 'Damage/Health Decay source default' in source
    assert 'Damage/Health Decay supplied fields' in source
    assert 'Damage/Health Decay start fields' in source
    for label in (
        'Orb damage to boss (total %)',
        'Electron damage override (total %)',
        'Boss time to contact override (s)',
        'Pressure factor (boss HP + damage)',
        'Death Wave maxed wave',
    ):
        assert label in source
    assert "'boss_wave_pressure_factor': boss_wave_pressure_factor" in source
    for stale_label in (
        'Orb boss hit %',
        'Effective DR %',
        'Incoming damage multiplier',
        'Death Wave health max x',
        'Boss hit interval (s)',
        'Flame Bot boss hit chance (%)',
        'Flame Bot DR %',
        'Defense Field DR %',
        'BH DR %',
        'BH duration (s)',
        'PBH uptime',
    ):
        assert stale_label not in source


def test_boss_wave_recommended_model_assumptions_are_session_local_runtime_inputs():
    from app.streamlit_inspector import (
        _boss_wave_recommended_model_assumption_frame,
        _boss_wave_recommended_model_runtime_inputs,
    )

    runtime_inputs = _boss_wave_recommended_model_runtime_inputs()

    assert {
        key: value
        for key, value in runtime_inputs.items()
        if key != 'boss_edamage_target_share'
    } == {
        'flame_bot_damage_reduction_pct': 95.0,
        'boss_edamage_cadence_uptime_factor': 1.0,
        'boss_edamage_reliability_factor': 1.0,
        'boss_edamage_semantic_normalizer': 1.0,
    }
    assert runtime_inputs['boss_edamage_target_share'] == pytest.approx(0.005051405075429985)
    assert 'flame_bot_boss_hit_chance_pct' not in runtime_inputs
    assert 'boss_time_to_contact_seconds' not in runtime_inputs
    assert 'boss_wave_pressure_factor' not in runtime_inputs

    frame = _boss_wave_recommended_model_assumption_frame()
    assert {'group', 'assumption', 'value', 'runtime_input', 'source'}.issubset(frame.columns)
    assert 'Flame Bot hit chance' in set(frame['assumption'])
    assert 'Boss contact time' in set(frame['assumption'])
    pressure_rows = frame[frame['runtime_input'] == 'boss_wave_pressure_factor'].to_dict('records')
    assert pressure_rows == [
        {
            'group': 'Pressure',
            'assumption': 'Pressure factor',
            'value': 'not a recommended default',
            'runtime_input': 'boss_wave_pressure_factor',
            'source': 'manual control only; matrix calibration median input is comparison-only',
        }
    ]


def test_streamlit_perks_tab_consumes_pipeline_preview_not_local_generator():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "'Perks'" in source
    assert 'build_perk_timeline_preview' in source
    assert 'for column, policy_preset in zip(columns, BOSS_WAVE_PERK_POLICY_PRESETS)' in source
    assert 'replace(request, perk_policy_preset=policy_preset)' in source
    assert 'Priority order' in source
    assert 'Bans' in source
    assert 'Taken by wave' in source
    assert 'Perk plan' in source
    assert 'Final wave' in source
    assert "_arrow_safe_frame(pd.DataFrame(rows), columns=('value', 'picks', 'max value'))" in source
    assert 'generate_timeline_from_policy' not in source
    assert 'PerkTimelinePolicy' not in source


def test_streamlit_boss_waves_operator_surface_renders_cleanly():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error

    assert _streamlit_values(app_test.title) == ['TowerSim Operations Console']
    assert 'Canonical stats, perk plans, and max-wave runs from sanctioned pipeline artifacts.' in _streamlit_values(app_test.caption)

    metric_labels = _streamlit_labels(app_test.metric)
    assert metric_labels.count('Max Boss Wave') == 1
    for stale_label in ('Rows', 'Selected wave', 'First failed wave', 'Perk plan', 'Tier', 'Loadout'):
        assert stale_label not in metric_labels

    selectbox_labels = _streamlit_labels(app_test.selectbox)
    assert 'Boss loadout' in selectbox_labels
    assert 'Perk plan' in selectbox_labels
    assert 'Run type' in selectbox_labels
    run_type_widget = _streamlit_widget_by_label(app_test.selectbox, 'Run type')
    assert list(run_type_widget.options) == [
        'Regular',
        'Attack Dissonant Run',
        'Defense Dissonant Run',
        'Utility Dissonant Run',
        'Ultimate Weapon Dissonant Run',
    ]

    number_input_labels = _streamlit_labels(app_test.number_input)
    assert 'End wave' in number_input_labels
    assert 'Checkpoint cadence (bosses)' in number_input_labels
    assert 'Matrix end wave' in number_input_labels
    assert 'Matrix checkpoint cadence (bosses)' in number_input_labels

    toggle_labels = _streamlit_labels(app_test.toggle)
    assert 'Use recommended model assumptions' in toggle_labels
    assert 'Override boss damage calibration' in toggle_labels
    assert 'Show all checkpoints' in toggle_labels
    assert 'Stop on first failed boss' not in toggle_labels

    expander_labels = _streamlit_labels(app_test.expander)
    for label in (
        'Recommended model assumptions',
        'Combat assumptions',
        'All-tier preset matrix',
        'Model assumptions',
        'Advanced boss-wave evidence',
    ):
        assert label in expander_labels
    assert 'Advanced run settings' not in expander_labels
    assert 'Advanced damage calibration' not in expander_labels
    for stale_label in (
        'Dissonance comparison',
        'Full boss-wave table',
        'Boss-wave diagnostics',
        'Boss-wave raw rows (debug)',
        'Boss-wave execution details',
    ):
        assert stale_label not in expander_labels

    caption_values = _streamlit_values(app_test.caption)
    assert 'Boss checkpoints' in caption_values
    assert 'Runtime inputs' in caption_values
    assert any('Result uses' in value for value in caption_values)
    assert 'Build 4-preset matrix' in _streamlit_labels(app_test.button)


def test_streamlit_boss_waves_run_type_selector_feeds_dissonance_path():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _streamlit_widget_by_label(app_test.selectbox, 'Run type').set_value('Ultimate Weapon Dissonant Run')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    caption_values = _streamlit_values(app_test.caption)
    assert any('Ultimate Weapon Dissonant Run' in value for value in caption_values)
    assert any('IDS Dissonant PB reference' in value for value in caption_values)


def test_streamlit_boss_waves_manual_damage_calibration_is_intentional():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    assert 'Boss eDamage applicability factor' not in _streamlit_labels(app_test.number_input)

    _streamlit_widget_by_label(app_test.toggle, 'Override boss damage calibration').set_value(True)
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    number_input_labels = _streamlit_labels(app_test.number_input)
    for label in (
        'Boss eDamage applicability factor',
        'Boss target share',
        'Boss cadence uptime',
        'Boss reliability',
        'Boss semantic normalizer',
    ):
        assert label in number_input_labels


def test_streamlit_boss_waves_tourney_exposes_legends_wave_override():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert 'Legends tournament wave' not in _streamlit_labels(app_test.number_input)
    _streamlit_widget_by_label(app_test.selectbox, 'Boss loadout').set_value('Tourney')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    assert 'Legends tournament wave' in _streamlit_labels(app_test.number_input)


def test_streamlit_run_controls_are_tab_scoped_not_sidebar_global():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "TowerSim Operations Console" in source
    assert "Canonical stats, perk plans, and max-wave runs from sanctioned pipeline artifacts." in source
    assert "TowerSim Incremental Inspector" not in source
    assert "st.sidebar.header('Run Controls')" not in source
    assert "boss_wave_perk_policy_override" not in source
    assert "perk_policy_override" not in source
    assert "st.sidebar.header('Snapshots')" in source
    assert "def _render_pipeline_run_controls" in source
    assert "def _render_verification_snapshot_controls" in source
    pipeline_start = source.index("def _render_pipeline(trace_payload")
    pipeline_end = source.index("\ndef _render_cards_matrix", pipeline_start)
    main_start = source.index("def main() -> None:")
    pipeline_block = source[pipeline_start:pipeline_end]
    assert "with st.expander('Pipeline evidence', expanded=False)" in pipeline_block
    assert "['Execution', 'Stages', 'Cache', 'Runtime', 'Advanced']" in pipeline_block
    assert "Active snapshot request defaults" in source[pipeline_start:pipeline_end]
    assert "Active snapshot request defaults" not in source[main_start:]
    assert "with st.expander('Execution Path'" not in pipeline_block
    assert "st.subheader('Cache')" not in pipeline_block
    assert "st.subheader('Incremental Plan')" not in pipeline_block
    assert "st.subheader('Runtime Consumers')" not in pipeline_block
    assert "with st.expander('Advanced raw details')" not in pipeline_block
    assert "'Run loadout'" in source
    assert "'Run perk plan'" in source
    assert "'Verification perk plan'" in source
    assert "'Boss loadout'" in source
    assert "'Perk plan'" in source
    assert "'Run type'" in source


def test_streamlit_checks_tab_surfaces_ep_alignment_summary() -> None:
    from app.streamlit_inspector import _ep_alignment_summary_frame

    frame = _ep_alignment_summary_frame(
        {
            'ep_compare_summary': {
                'ep_alignment_status': 'aligned_except_accounted_stage_scope_limits',
                'ep_clean_aligned_count': 26,
                'ep_accounted_stage_scope_limit_count': 23,
                'ep_unaccounted_alignment_gap_count': 0,
                'ep_raw_formula_mismatch_count': 0,
                'ep_true_formula_mismatch_count': 0,
                'ep_compare_count': 49,
            }
        }
    )
    assert frame.to_dict('records') == [
        {'Metric': 'Alignment status', 'Value': 'aligned_except_accounted_stage_scope_limits'},
        {'Metric': 'Clean aligned rows', 'Value': 26},
        {'Metric': 'Accounted EP scope limits', 'Value': 23},
        {'Metric': 'Unaccounted alignment gaps', 'Value': 0},
        {'Metric': 'Raw formula mismatches', 'Value': 0},
        {'Metric': 'True formula mismatches', 'Value': 0},
        {'Metric': 'EP compare rows', 'Value': 49},
    ]

    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    checks_start = source.index('def _render_checks')
    checks_end = source.index("\ndef _render_inputs", checks_start)
    checks_block = source[checks_start:checks_end]
    assert 'ep_unaccounted_alignment_gaps' in checks_block
    assert "st.caption('EP alignment summary')" in checks_block
    assert '_ep_alignment_summary_frame(diagnostics)' in checks_block


def test_streamlit_checks_tab_surfaces_goal_readiness_summary() -> None:
    from app.streamlit_inspector import _tower_goal_readiness_frame

    frame = _tower_goal_readiness_frame(
        {
            'tower_goal_readiness': {
                'status': 'not_complete',
                'requirements': [
                    {
                        'id': 'effect_family_carrythrough_to_boss_waves',
                        'status': 'proven',
                        'evidence': 'current_scope_effect_family_evidence',
                        'family_proof_counts': {
                            'covered_family_count': 7,
                            'requested_family_count': 7,
                            'registered_route_contributor_count': 163,
                            'route_contributor_count': 163,
                            'boss_wave_rows_with_coverage': 105,
                            'boss_wave_selected_row_count': 105,
                        },
                        'remaining_gaps': [],
                    },
                    {
                        'id': 'boss_waves_full_accuracy',
                        'status': 'blocked',
                        'evidence': 'boss_wave_milestone_matrix',
                        'model_completion_blockers': [
                            'source_owned_non_boss_terminal_pressure_formulas',
                        ],
                    },
                    {
                        'id': 'farming_cph_objective',
                        'status': 'blocked',
                        'evidence': 'farming_econ_model_readiness',
                        'coins_per_hour_certification_blockers': [
                            'wave_skip_coin_reward_expected_value_over_per_wave_coin_curve',
                        ],
                    },
                ],
            }
        }
    )

    assert frame.to_dict('records') == [
        {
            'Requirement': 'effect_family_carrythrough_to_boss_waves',
            'Status': 'proven',
            'Evidence': 'current_scope_effect_family_evidence',
            'Proof': 'families 7/7; routes 163/163; boss rows 105/105',
            'Blockers': '',
        },
        {
            'Requirement': 'boss_waves_full_accuracy',
            'Status': 'blocked',
            'Evidence': 'boss_wave_milestone_matrix',
            'Proof': '',
            'Blockers': 'source_owned_non_boss_terminal_pressure_formulas',
        },
        {
            'Requirement': 'farming_cph_objective',
            'Status': 'blocked',
            'Evidence': 'farming_econ_model_readiness',
            'Proof': '',
            'Blockers': 'wave_skip_coin_reward_expected_value_over_per_wave_coin_curve',
        },
    ]

    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    checks_start = source.index('def _render_checks')
    checks_end = source.index("\ndef _render_inputs", checks_start)
    checks_block = source[checks_start:checks_end]
    assert "st.caption('Goal readiness summary')" in checks_block
    assert '_tower_goal_readiness_frame(diagnostics)' in checks_block


def test_streamlit_checks_tab_surfaces_effect_carrythrough_summary() -> None:
    from app.streamlit_inspector import _effect_carrythrough_summary_frame

    families = ['bot', 'card_base', 'card_mastery', 'workshop', 'enhancement', 'module', 'relic']
    frame = _effect_carrythrough_summary_frame(
        {
            'current_scope_effect_family_evidence': {
                'status': 'covered',
                'statbook_route_visibility_exception_status': 'classified_partial_visibility_accepted',
                'requested_effect_families': families,
                'effect_row_carrythrough_incomplete_families': [],
                'families': {
                    family: {
                        'line_verification_status': 'covered',
                        'ep_compare_status_counts': {
                            'matched_exact': 2,
                            'matched_close': 3,
                            'stage_scope_mismatch': 4,
                            'not_ep_compared': 5,
                        },
                        'individual_route_evidence': {
                            'route_contributor_count': 12,
                            'unregistered_route_contributor_count': 0,
                            'statbook_route_visibility_mode_counts': {
                                'exact_statbook_contributor': 8,
                                'destination_surface_visible': 3,
                                'not_visible_in_current_statbook': 1,
                            },
                            'not_visible_route_classification_counts': {
                                'selected_preset_module_card_payload_visible_statbook_route_missing': 1,
                                'other_preset_module_card_payload_visible_in_query_books': 2,
                                'other_preset_module_card_payload_not_in_committed_query_books': 3,
                            },
                        },
                        'effect_row_carrythrough': {
                            'status': 'covered',
                            'boss_wave_selected_row_count': 105,
                            'boss_wave_rows_with_coverage': 105,
                            'line_verification_status': 'covered',
                        },
                    }
                    for family in families
                },
            }
        }
    )
    assert frame.to_dict('records') == [
        {
            'Family': family,
            'Status': 'covered',
            'Boss rows': 105,
            'Covered rows': 105,
            'Line verification': 'covered',
            'Route contributors': 12,
            'Unregistered routes': 0,
            'Visibility policy': 'classified_partial_visibility_accepted',
            'Exact route hits': 8,
            'Destination route hits': 3,
            'Routes not visible': 1,
            'Active route gaps': 1,
            'Other preset routes': 5,
            'Other preset query hits': 2,
            'Inactive route gaps': 0,
            'Other classified gaps': 0,
            'Unclassified route gaps': 0,
            'EP clean': 5,
            'EP scope-limited': 4,
            'EP unaccounted': 0,
        }
        for family in families
    ]

    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    checks_start = source.index('def _render_checks')
    checks_end = source.index("\ndef _render_inputs", checks_start)
    checks_block = source[checks_start:checks_end]
    assert 'effect_carrythrough_incomplete_families' in checks_block
    assert "st.caption('Effect carry-through to Boss Waves')" in checks_block
    assert '_effect_carrythrough_summary_frame(diagnostics)' in checks_block


def test_streamlit_checks_tab_surfaces_boss_wave_readiness_summary() -> None:
    from app.streamlit_inspector import _boss_wave_readiness_summary_frame

    frame = _boss_wave_readiness_summary_frame(
        {
            'boss_wave_milestone_matrix': {
                'model_closure_status': 'partial_missing_required_model_inputs',
                'certified_full_max_wave_model': False,
                'model_completion_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
                'model_blocker_summary': {
                    'rows_with_model_completion_blockers': 35,
                    'rows_with_unsupported_terminal_pressures': 35,
                },
                'model_accuracy_summary': {
                    'comparison_only_pressure_factor_inputs': {
                        'boss_wave_pressure_factor': 2.606384292771721,
                    },
                    'operator_next_step': (
                        'apply_comparison_only_pressure_factor_input_to_review_approximation'
                    ),
                    'non_boss_pressure_driver_model': {
                        'status': 'source_driver_curves_partially_available_terminal_transform_missing',
                        'pressure_factor_policy': 'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved',
                        'rows_with_unsupported_terminal_pressures': 35,
                        'terminal_pressure_transform_readiness': {
                            'status': 'source_driver_curves_available_terminal_transform_missing',
                            'remaining_to_certify': [
                                'normal_spawn_rate_value_to_terminal_pressure',
                                'elite_spawn_pressure_weight_to_terminal_pressure',
                            ],
                        },
                        'pressure_driver_empirical_calibration': {
                            'empirical_transform_candidate': {
                                'validation_status': 'leave_one_out_descriptive_only_not_promoted',
                                'promotion_status': 'not_promoted',
                                'promotion_readiness': {
                                    'status': 'not_ready',
                                    'operator_approval_status': 'not_approved',
                                    'blocking_reasons': [
                                        'not_source_owned_terminal_pressure_formula',
                                        'operator_has_not_approved_empirical_transform_as_default',
                                        'non_capped_dissonance_reference_validation_missing',
                                        'out_of_sample_validation_beyond_clean_regular_rows_missing',
                                    ],
                                    'validation_basis': 'clean_regular_rows_leave_one_out_only',
                                    'mean_absolute_error': 0.6455062281014187,
                                    'max_absolute_error': 2.761589637980494,
                                },
                                'leave_one_out_validation': {
                                    'mean_absolute_error': 0.6455062281014187,
                                },
                            },
                        },
                        'empirical_calibration_policy': {
                            'below_3000_wave_reference_count': 11,
                            'dissonance_pb_5000_cap_count': 42,
                        },
                    },
                },
                'tracker_reference_evidence': {
                    'status': 'tracker_boss_wave_reference_evidence_available_not_applied',
                    'row_count': 23,
                    'matched_regular_reference_count': 19,
                    'unmapped_dissonance_reference_count': 4,
                    'dissonance_tracker_calibration_filter': {
                        'status': 'tracker_dissonance_filter_evidence_available',
                        'dissonance_pb_5000_cap_reference_count': 2,
                        'below_3000_wave_reference_count': 1,
                        'clean_tracker_calibration_candidate_count': 1,
                    },
                    'dissonance_tracker_alignment_summary': {
                        'status': 'tracker_dissonance_alignment_available_not_applied',
                        'category_hint_reference_count': 2,
                        'selected_delta_vs_tracker_max_wave_median': -84.5,
                        'selected_to_tracker_max_wave_ratio_median': 0.982,
                    },
                },
            }
        }
    )
    assert frame.to_dict('records') == [
        {'Metric': 'Model closure status', 'Value': 'partial_missing_required_model_inputs'},
        {'Metric': 'Certified full max-wave model', 'Value': False},
        {'Metric': 'Model blockers', 'Value': 'source_owned_non_boss_terminal_pressure_formulas'},
        {'Metric': 'Rows with blockers', 'Value': 35},
        {'Metric': 'Unsupported pressure rows', 'Value': 35},
        {
            'Metric': 'Pressure model status',
            'Value': 'source_driver_curves_partially_available_terminal_transform_missing',
        },
        {
            'Metric': 'Terminal pressure readiness',
            'Value': 'source_driver_curves_available_terminal_transform_missing',
        },
        {
            'Metric': 'Terminal pressure remaining gaps',
            'Value': (
                'normal_spawn_rate_value_to_terminal_pressure, '
                'elite_spawn_pressure_weight_to_terminal_pressure'
            ),
        },
        {
            'Metric': 'Pressure factor policy',
            'Value': 'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved',
        },
        {'Metric': 'Pressure transform status', 'Value': 'leave_one_out_descriptive_only_not_promoted'},
        {'Metric': 'Pressure transform promoted', 'Value': 'not_promoted'},
        {'Metric': 'Pressure promotion readiness', 'Value': 'not_ready'},
        {'Metric': 'Pressure promotion approval', 'Value': 'not_approved'},
        {
            'Metric': 'Pressure promotion blockers',
            'Value': (
                'not_source_owned_terminal_pressure_formula, '
                'operator_has_not_approved_empirical_transform_as_default, '
                'non_capped_dissonance_reference_validation_missing, '
                'out_of_sample_validation_beyond_clean_regular_rows_missing'
            ),
        },
        {
            'Metric': 'Pressure promotion validation',
            'Value': 'clean_regular_rows_leave_one_out_only',
        },
        {'Metric': 'Pressure promotion MAE', 'Value': 0.6455062281014187},
        {'Metric': 'Pressure promotion max error', 'Value': 2.761589637980494},
        {'Metric': 'Pressure LOO MAE', 'Value': 0.6455062281014187},
        {
            'Metric': 'Comparison pressure review input',
            'Value': '{"boss_wave_pressure_factor": 2.606384292771721}',
        },
        {
            'Metric': 'Pressure review next step',
            'Value': 'apply_comparison_only_pressure_factor_input_to_review_approximation',
        },
        {'Metric': 'Sub-3000 references', 'Value': 11},
        {'Metric': 'Dissonance 5000 cap refs', 'Value': 42},
        {
            'Metric': 'Tracker reference status',
            'Value': 'tracker_boss_wave_reference_evidence_available_not_applied',
        },
        {'Metric': 'Tracker reference rows', 'Value': 23},
        {'Metric': 'Tracker regular matches', 'Value': 19},
        {'Metric': 'Tracker unmapped Dissonance refs', 'Value': 4},
        {
            'Metric': 'Tracker Dissonance filter status',
            'Value': 'tracker_dissonance_filter_evidence_available',
        },
        {'Metric': 'Tracker Dissonance cap refs', 'Value': 2},
        {'Metric': 'Tracker Dissonance sub-3000 refs', 'Value': 1},
        {'Metric': 'Tracker Dissonance clean candidates', 'Value': 1},
        {
            'Metric': 'Tracker Dissonance alignment status',
            'Value': 'tracker_dissonance_alignment_available_not_applied',
        },
        {'Metric': 'Tracker Dissonance hinted refs', 'Value': 2},
        {'Metric': 'Tracker Dissonance selected delta median', 'Value': -84.5},
        {'Metric': 'Tracker Dissonance selected/tracker ratio', 'Value': 0.982},
    ]

    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    checks_start = source.index('def _render_checks')
    checks_end = source.index("\ndef _render_inputs", checks_start)
    checks_block = source[checks_start:checks_end]
    assert 'boss_wave_model_blockers' in checks_block
    assert 'boss_wave_uncertified' in checks_block
    assert "st.caption('Boss Waves readiness summary')" in checks_block
    assert '_boss_wave_readiness_summary_frame(diagnostics)' in checks_block


def test_streamlit_checks_tab_surfaces_farming_econ_readiness_summary() -> None:
    from app.streamlit_inspector import _farming_econ_readiness_summary_frame

    frame = _farming_econ_readiness_summary_frame(
        {
            'farming_econ_model_readiness': {
                'objective': 'coins_per_hour',
                'optimizer_policy': 'farming_should_optimize_coins_per_hour_not_longest_wave',
                'coins_per_hour_certification_status': 'not_certified_missing_formula_links',
                'coins_per_hour_objective_identity': {
                    'status': 'source_owned_identity_available',
                    'formula': 'coins_per_hour = coins_per_run / run_duration_hours',
                },
                'run_duration_projection_readiness': {
                    'status': 'source_timing_projection_available_tracker_comparison_available',
                    'formula': (
                        'played_non_intro_waves_after_expected_wave_skip * '
                        'effective_wave_duration_seconds / effective_game_speed_multiplier'
                    ),
                    'projected_to_anchor_run_hours_ratio': 0.884372735760971,
                    'tracker_skip_adjusted_projected_over_observed_duration_ratio': 1.0,
                    'operator_approval_status': 'not_approved',
                    'approved_projection_closes_formula_link': False,
                },
                'certified_farming_cph_model': False,
                'coins_per_hour_certification_blockers': [
                    'calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed',
                    'spawn_rate_to_enemy_kill_density_by_wave',
                ],
                'coins_per_hour_promotion_readiness': {
                    'status': 'not_ready',
                    'blocking_reasons': [
                        'not_source_owned_run_coin_and_duration_integrals',
                        'operator_has_not_approved_tracker_empirical_cph_as_default',
                        'wave_skip_reward_expected_value_missing',
                        'econ_window_overlap_coin_integral_missing',
                        'validation_across_multiple_exports_and_account_states_missing',
                    ],
                    'validation_basis': 'tracker_t14_recent_and_prior_windows',
                    'observed_median_coins_per_hour': 227_145_000_000_000.0,
                    'component_to_tracker_cph_ratio': 1.0016570458566083,
                    'tracker_run_total_cph': 227_521_389_681_099.3,
                    'tracker_run_total_to_reported_cph_ratio': 1.0016570458566083,
                    'projected_to_tracker_cph_ratio': 1.002507817035684,
                    'tracker_waves_per_hour_consistency_status': (
                        'tracker_reported_waves_per_hour_matches_duration'
                    ),
                    'tracker_game_time_ratio_status': 'tracker_game_time_ratio_available',
                    'tracker_median_game_time_hours': 28.864444444444445,
                    'tracker_game_to_real_duration_ratio': 4.670140869414917,
                    'tracker_reported_median_waves_per_hour': 980.9,
                    'tracker_reported_to_observed_waves_per_hour_ratio': (
                        1.0000003149430778
                    ),
                    'tracker_projected_over_observed_duration_ratio': 1.59,
                    'tracker_skip_adjusted_projected_over_observed_duration_ratio': 1.0,
                    'tracker_skip_semantics_inference_status': (
                        'suggests_tracker_skips_include_intro_sprint'
                    ),
                    'tracker_skip_semantics_best_candidate': 'tracker_skips_include_intro_sprint',
                    'tracker_skip_semantics_best_candidate_distance_from_expected': (
                        0.04970237377443802
                    ),
                    'tracker_latest_coins_per_hour': 240_700_000_000_000.0,
                    'tracker_recent_median_coins_per_hour': 227_145_000_000_000.0,
                    'tracker_prior_median_coins_per_hour': 190_000_000_000_000.0,
                    'tracker_recent_to_prior_coins_per_hour_ratio': 1.1955,
                },
                'calibration_anchor': {
                    'tier': 14,
                    'observed_final_wave': 5500,
                    'observed_run_hours': 5.5,
                    'observed_coins_per_hour': 210_000_000_000_000.0,
                },
                'current_timing_projection': {
                    'estimated_run_hours_after_game_speed': 7.72,
                    'estimated_run_hours_after_wave_skip_intro_and_game_speed': 4.86,
                },
                'tracker_timing_alignment': {
                    'status': 'not_supplied',
                    'skip_semantics_gap_status': None,
                },
                'tracker_cph_calibration_evidence': {
                    'status': 'tracker_t14_farming_cph_band_available',
                    'observed_median_coins_per_hour': 227_145_000_000_000.0,
                    'observed_to_anchor_coins_per_hour_ratio': 1.081642857142857,
                },
                'tracker_cph_identity_evidence': {
                    'status': 'tracker_density_components_reconstruct_cph',
                    'run_total_median_coins_per_hour': 227_521_389_681_099.3,
                    'run_total_to_tracker_cph_ratio': 1.0016570458566083,
                    'run_total_to_tracker_reported_row_ratio_median': (
                        1.0017129814796646
                    ),
                    'component_median_coins_per_hour': 227_521_389_681_099.3,
                    'component_to_tracker_cph_ratio': 1.0016570458566083,
                },
                'tracker_wave_reward_candidate': {
                    'status': 'tracker_intro_wave_skip_reward_candidate_available',
                    'source_audit': {
                        'status': 'base_reward_sources_available_integral_semantics_unresolved',
                        'intro_sprint_coin_suppression': {
                            'status': 'source_backed_available',
                        },
                        'wave_skip_base_reward': {
                            'status': 'source_backed_available_expected_value_missing',
                        },
                        'wave_skip_mastery_double_skip': {
                            'status': 'source_backed_available_reward_integral_missing',
                        },
                        'tracker_skip_count_semantics': {
                            'status': (
                                'tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap'
                            ),
                        },
                    },
                    'coins_per_non_intro_displayed_wave': 307_439_824_945.2954,
                    'coins_per_tracker_played_wave_after_intro': 633_310_795_582.6008,
                    'observed_effective_skip_multiplier_after_intro': 2.0599504169483884,
                    'tracker_reward_field_status': 'tracker_wave_skip_reward_fields_available',
                    'tracker_reported_wave_skip_coin_share': 0.24489081834251847,
                    'tracker_reported_coins_per_skipped_wave': 145_709_053_278.67368,
                    'tracker_reported_coins_per_wave': 252_560_000_000.0,
                    'tracker_reported_coins_per_wave_to_observed_ratio': (
                        1.0826048578558802
                    ),
                    'tracker_reported_coins_per_wave_semantics_status': (
                        'tracker_reported_coins_per_wave_close_to_total_observed'
                    ),
                },
                'wave_skip_reward_readiness': {
                    'status': 'source_reward_semantics_available_expected_value_integral_missing',
                    'operator_approval_status': 'not_approved',
                    'approved_reward_closes_formula_link': False,
                    'source_audit': {
                        'status': 'base_reward_sources_available_integral_semantics_unresolved',
                        'intro_sprint_coin_suppression': {
                            'status': 'source_backed_available',
                        },
                        'wave_skip_base_reward': {
                            'status': 'source_backed_available_expected_value_missing',
                        },
                        'wave_skip_mastery_double_skip': {
                            'status': 'source_backed_available_reward_integral_missing',
                        },
                        'tracker_skip_count_semantics': {
                            'status': (
                                'tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap'
                            ),
                        },
                    },
                },
                'intro_sprint_coin_window_readiness': {
                    'status': (
                        'source_intro_sprint_coin_suppression_available_coin_integral_missing'
                    ),
                    'operator_approval_status': 'not_approved',
                    'approved_window_closes_formula_link': False,
                    'coin_eligible_displayed_waves_after_intro_at_target': 4321.0,
                    'remaining_to_certify': [
                        'source_owned_per_wave_coin_curve_after_intro_sprint',
                        'intro_sprint_boundary_interaction_with_wave_skip_and_wave_rewards',
                        'econ_window_overlap_for_post_intro_played_and_skipped_waves',
                        'run_coin_integral_excluding_intro_sprint_waves',
                    ],
                },
                'econ_sync_window_readiness': {
                    'status': 'window_inputs_available_overlap_integral_not_certified',
                    'phase_model': 'phase_zero_current_helper_only',
                    'available_window_count': 3,
                    'pair_overlap_fractions': {
                        'golden_tower__black_hole_coin': 0.3,
                    },
                    'overlap_integral_readiness': {
                        'status': 'source_window_inputs_available_overlap_integral_missing',
                        'operator_approval_status': 'not_approved',
                        'approved_overlap_closes_formula_link': False,
                        'remaining_to_certify': [
                            'phase_offsets_or_sync_schedule',
                            'kill_density_inside_each_econ_window',
                        ],
                    },
                    'diagnostic_average_combined_multiplier_for_available_windows': 42.0,
                    'tracker_econ_coin_source_evidence': {
                        'status': 'tracker_econ_coin_sources_available',
                        'available_source_count': 6,
                        'tracked_source_sum_to_run_coins_ratio': {
                            'median': 3.2935449464489963,
                        },
                        'overlap_evidence_status': 'source_splits_overlap_or_double_count',
                        'sources': {
                            'coins_from_golden_tower': {
                                'share_of_run_coins': {'median': 0.6986926276385568},
                            },
                            'coins_from_black_hole': {
                                'share_of_run_coins': {'median': 0.6694187636477071},
                            },
                            'coins_from_spotlight': {
                                'share_of_run_coins': {'median': 0.3597176094416138},
                            },
                            'golden_bot_coins_earned': {
                                'share_of_run_coins': {'median': 0.610163408547364},
                            },
                        },
                    },
                },
                'spawn_density_readiness': {
                    'status': 'spawn_rate_curve_available_kill_density_transform_missing',
                    'displayed_spawn_rate': 56.0,
                    'wave_accelerator_spawn_rate_acceleration': 1.8,
                    'normal_enemy_spawn_count_curve_available': False,
                    'kill_density_transform_readiness': {
                        'status': 'source_spawn_rate_available_kill_density_transform_missing',
                        'tracker_candidate_status': (
                            'tracker_spawn_rate_to_kill_density_candidate_available'
                        ),
                        'operator_approval_status': 'not_approved',
                        'approved_transform_closes_formula_link': False,
                        'remaining_to_certify': [
                            'source_owned_normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase',
                            'approved_spawn_rate_to_kill_density_transform',
                            'tier_wave_spawn_phase_validation_set',
                            'integration_with_intro_sprint_wave_skip_and_econ_windows',
                        ],
                    },
                    'normal_enemy_spawn_count_source_audit': {
                        'status': 'source_not_found_spawn_rate_curve_only',
                        'missing_source_owned_surface': (
                            'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase'
                        ),
                    },
                    'non_boss_pressure_driver_evidence': {
                        'status': 'driver_inputs_available_terminal_transform_missing',
                        'elite_spawn_pressure': {
                            'elite_pressure_index_pct': 66.0,
                        },
                        'fleet_spawn_pressure': {
                            'fleet_events_per_wave_pressure': 0.001,
                        },
                    },
                    'tracker_enemy_density_evidence': {
                        'status': 'tracker_t14_farming_enemy_density_available',
                        'observed_median_enemies_per_wave': 136.65,
                        'displayed_spawn_rate_to_observed_enemies_per_wave_ratio': 2.44,
                    },
                    'tracker_enemy_composition_evidence': {
                        'status': 'tracker_enemy_composition_available',
                        'normal_enemy_counts': {
                            'protector': {
                                'count_per_wave': {
                                    'median': 0.16219162793768876,
                                },
                                'share_of_total_enemies': {
                                    'median': 0.0011563682071846562,
                                },
                            },
                        },
                        'elite_enemy_counts': {
                            'vampires': {
                                'share_of_total_enemies': {
                                    'median': 0.0003823225815743974,
                                },
                            },
                            'rays': {
                                'share_of_total_enemies': {
                                    'median': 0.000336105991654569,
                                },
                            },
                            'scatters': {
                                'share_of_total_enemies': {
                                    'median': 0.0003418822589676175,
                                },
                            },
                        },
                        'total_elites_share_of_total_enemies': {
                            'median': 0.0010603108321965839,
                        },
                        'elite_tracked_count_per_wave': {
                            'median': 0.14411844882426642,
                        },
                    },
                    'tracker_kill_density_transform_candidate': {
                        'status': 'tracker_spawn_rate_to_kill_density_candidate_available',
                        'projected_enemies_per_wave_from_tracker_ratio': 136.65,
                        'observed_enemies_per_wave_per_displayed_spawn_rate': 2.44,
                    },
                    'tracker_kill_density_stability_evidence': {
                        'status': 'tracker_recent_prior_kill_density_transform_available',
                        'recent_enemies_per_wave_per_displayed_spawn_rate': 2.56,
                        'prior_enemies_per_wave_per_displayed_spawn_rate': 2.31,
                    },
                    'tracker_coin_density_evidence': {
                        'status': 'tracker_t14_farming_coin_density_available',
                        'observed_median_coins_per_enemy': 1_698_794_935.61,
                        'observed_median_coins_per_wave': 232_272_088_511.65,
                    },
                    'tracker_coin_yield_stability_evidence': {
                        'status': 'tracker_recent_prior_coin_yield_available',
                        'coins_per_enemy_median_ratio': 1.18,
                        'coins_per_wave_median_ratio': 1.17,
                    },
                    'tracker_coin_integral_candidate': {
                        'status': 'tracker_kill_density_to_coin_integral_candidate_available',
                        'projected_coins_per_wave_from_tracker_density': 232_148_757_616.68,
                        'projected_coins_per_hour_from_tracker_density': 227_714_638_100_570.44,
                        'projected_to_tracker_cph_ratio': 1.002507817035684,
                    },
                },
                'driver_coverage': {
                    'available': 22,
                    'total': 23,
                },
                'missing_formula_links': [
                    'calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed',
                    'spawn_rate_to_enemy_kill_density_by_wave',
                ],
            }
        }
    )
    assert frame.to_dict('records') == [
        {'Metric': 'Objective', 'Value': 'coins_per_hour'},
        {'Metric': 'Optimizer policy', 'Value': 'farming_should_optimize_coins_per_hour_not_longest_wave'},
        {'Metric': 'CPH certification status', 'Value': 'not_certified_missing_formula_links'},
        {'Metric': 'CPH objective identity status', 'Value': 'source_owned_identity_available'},
        {'Metric': 'CPH objective identity', 'Value': 'coins_per_hour = coins_per_run / run_duration_hours'},
        {'Metric': 'Certified farming CPH model', 'Value': False},
        {
            'Metric': 'Certification blockers',
            'Value': (
                'calibrated_real_run_duration_after_intro_sprint_wave_skip_and_game_speed, '
                'spawn_rate_to_enemy_kill_density_by_wave'
            ),
        },
        {'Metric': 'CPH promotion readiness', 'Value': 'not_ready'},
        {
            'Metric': 'CPH promotion blockers',
            'Value': (
                'not_source_owned_run_coin_and_duration_integrals, '
                'operator_has_not_approved_tracker_empirical_cph_as_default, '
                'wave_skip_reward_expected_value_missing, '
                'econ_window_overlap_coin_integral_missing, '
                'validation_across_multiple_exports_and_account_states_missing'
            ),
        },
        {
            'Metric': 'CPH promotion validation',
            'Value': 'tracker_t14_recent_and_prior_windows',
        },
        {'Metric': 'CPH promotion tracker CPH', 'Value': 227_145_000_000_000.0},
        {'Metric': 'CPH promotion component ratio', 'Value': 1.0016570458566083},
        {'Metric': 'CPH promotion run-total CPH', 'Value': 227_521_389_681_099.3},
        {'Metric': 'CPH promotion run-total ratio', 'Value': 1.0016570458566083},
        {'Metric': 'CPH promotion projected ratio', 'Value': 1.002507817035684},
        {
            'Metric': 'Duration projection status',
            'Value': 'source_timing_projection_available_tracker_comparison_available',
        },
        {
            'Metric': 'Duration projection formula',
            'Value': (
                'played_non_intro_waves_after_expected_wave_skip * '
                'effective_wave_duration_seconds / effective_game_speed_multiplier'
            ),
        },
        {'Metric': 'Duration projected/anchor', 'Value': 0.884372735760971},
        {'Metric': 'Duration tracker skip-adjusted ratio', 'Value': 1.0},
        {'Metric': 'Duration projection approval', 'Value': 'not_approved'},
        {'Metric': 'Duration formula link closed', 'Value': False},
        {
            'Metric': 'Tracker timing consistency',
            'Value': 'tracker_reported_waves_per_hour_matches_duration',
        },
        {
            'Metric': 'Tracker game-time ratio status',
            'Value': 'tracker_game_time_ratio_available',
        },
        {'Metric': 'Tracker game time hours', 'Value': 28.864444444444445},
        {'Metric': 'Tracker game/real duration', 'Value': 4.670140869414917},
        {'Metric': 'Tracker reported waves/hour', 'Value': 980.9},
        {
            'Metric': 'Tracker reported/observed waves/hour',
            'Value': 1.0000003149430778,
        },
        {'Metric': 'Tracker projected duration ratio', 'Value': 1.59},
        {'Metric': 'Tracker skip-adjusted duration ratio', 'Value': 1.0},
        {
            'Metric': 'Tracker skip semantics inference',
            'Value': 'suggests_tracker_skips_include_intro_sprint',
        },
        {
            'Metric': 'Tracker skip semantics candidate',
            'Value': 'tracker_skips_include_intro_sprint',
        },
        {'Metric': 'Tracker skip semantics distance', 'Value': 0.04970237377443802},
        {'Metric': 'Tracker latest CPH', 'Value': 240_700_000_000_000.0},
        {'Metric': 'Tracker recent median CPH', 'Value': 227_145_000_000_000.0},
        {'Metric': 'Tracker prior median CPH', 'Value': 190_000_000_000_000.0},
        {'Metric': 'Tracker recent/prior CPH', 'Value': 1.1955},
        {'Metric': 'Anchor tier', 'Value': 14},
        {'Metric': 'Anchor final wave', 'Value': 5500},
        {'Metric': 'Anchor run hours', 'Value': 5.5},
        {'Metric': 'Anchor coins/hour', 'Value': 210_000_000_000_000.0},
        {'Metric': 'Projected run hours after speed', 'Value': 7.72},
        {'Metric': 'Projected run hours after intro/skip/speed', 'Value': 4.86},
        {'Metric': 'Tracker alignment status', 'Value': 'not_supplied'},
        {'Metric': 'Tracker skip gap status', 'Value': None},
        {'Metric': 'Tracker CPH band status', 'Value': 'tracker_t14_farming_cph_band_available'},
        {'Metric': 'Tracker median CPH', 'Value': 227_145_000_000_000.0},
        {'Metric': 'Tracker / anchor CPH ratio', 'Value': 1.081642857142857},
        {'Metric': 'Tracker CPH identity status', 'Value': 'tracker_density_components_reconstruct_cph'},
        {'Metric': 'Tracker run-total CPH', 'Value': 227_521_389_681_099.3},
        {'Metric': 'Tracker run-total / reported CPH', 'Value': 1.0016570458566083},
        {
            'Metric': 'Tracker row run-total / reported CPH',
            'Value': 1.0017129814796646,
        },
        {'Metric': 'Tracker component CPH', 'Value': 227_521_389_681_099.3},
        {'Metric': 'Tracker component / reported CPH', 'Value': 1.0016570458566083},
        {'Metric': 'Tracker wave-reward status', 'Value': 'tracker_intro_wave_skip_reward_candidate_available'},
        {
            'Metric': 'Wave Skip reward readiness',
            'Value': 'source_reward_semantics_available_expected_value_integral_missing',
        },
        {
            'Metric': 'Intro Sprint coin-window readiness',
            'Value': 'source_intro_sprint_coin_suppression_available_coin_integral_missing',
        },
        {'Metric': 'Intro Sprint coin-eligible waves', 'Value': 4321.0},
        {
            'Metric': 'Intro Sprint coin-window gaps',
            'Value': (
                'source_owned_per_wave_coin_curve_after_intro_sprint, '
                'intro_sprint_boundary_interaction_with_wave_skip_and_wave_rewards, '
                'econ_window_overlap_for_post_intro_played_and_skipped_waves, '
                'run_coin_integral_excluding_intro_sprint_waves'
            ),
        },
        {'Metric': 'Intro Sprint coin-window approval', 'Value': 'not_approved'},
        {'Metric': 'Intro Sprint formula link closed', 'Value': False},
        {
            'Metric': 'Wave reward source audit',
            'Value': 'base_reward_sources_available_integral_semantics_unresolved',
        },
        {'Metric': 'Intro Sprint reward source', 'Value': 'source_backed_available'},
        {
            'Metric': 'Wave Skip reward source',
            'Value': 'source_backed_available_expected_value_missing',
        },
        {
            'Metric': 'Wave Skip mastery reward source',
            'Value': 'source_backed_available_reward_integral_missing',
        },
        {
            'Metric': 'Tracker skip-count reward semantics',
            'Value': 'tracker_skip_count_semantics_ambiguous_intro_inclusive_candidate_reduces_gap',
        },
        {'Metric': 'Tracker coins/non-Intro displayed wave', 'Value': 307_439_824_945.2954},
        {'Metric': 'Tracker coins/played wave after Intro', 'Value': 633_310_795_582.6008},
        {'Metric': 'Tracker effective skip multiplier', 'Value': 2.0599504169483884},
        {
            'Metric': 'Tracker Wave Skip reward fields',
            'Value': 'tracker_wave_skip_reward_fields_available',
        },
        {'Metric': 'Wave Skip reward approval', 'Value': 'not_approved'},
        {'Metric': 'Wave Skip reward formula link closed', 'Value': False},
        {'Metric': 'Tracker reported coins/wave', 'Value': 252_560_000_000.0},
        {
            'Metric': 'Tracker reported/observed coins/wave',
            'Value': 1.0826048578558802,
        },
        {
            'Metric': 'Tracker coins/wave semantics',
            'Value': 'tracker_reported_coins_per_wave_close_to_total_observed',
        },
        {'Metric': 'Tracker Wave Skip coin share', 'Value': 0.24489081834251847},
        {'Metric': 'Tracker coins/skipped wave', 'Value': 145_709_053_278.67368},
        {'Metric': 'Econ sync status', 'Value': 'window_inputs_available_overlap_integral_not_certified'},
        {
            'Metric': 'Econ overlap readiness',
            'Value': 'source_window_inputs_available_overlap_integral_missing',
        },
        {
            'Metric': 'Econ overlap remaining gaps',
            'Value': 'phase_offsets_or_sync_schedule, kill_density_inside_each_econ_window',
        },
        {'Metric': 'Econ overlap approval', 'Value': 'not_approved'},
        {'Metric': 'Econ overlap formula link closed', 'Value': False},
        {'Metric': 'Econ sync phase model', 'Value': 'phase_zero_current_helper_only'},
        {'Metric': 'Econ windows available', 'Value': 3},
        {'Metric': 'GT/BH overlap fraction', 'Value': 0.3},
        {'Metric': 'Diagnostic window multiplier', 'Value': 42.0},
        {'Metric': 'Tracker econ source status', 'Value': 'tracker_econ_coin_sources_available'},
        {'Metric': 'Tracker econ source count', 'Value': 6},
        {'Metric': 'Tracker econ source sum/run coins', 'Value': 3.2935449464489963},
        {
            'Metric': 'Tracker econ overlap evidence',
            'Value': 'source_splits_overlap_or_double_count',
        },
        {'Metric': 'Tracker GT coin share', 'Value': 0.6986926276385568},
        {'Metric': 'Tracker BH coin share', 'Value': 0.6694187636477071},
        {'Metric': 'Tracker Spotlight coin share', 'Value': 0.3597176094416138},
        {'Metric': 'Tracker Golden Bot coin share', 'Value': 0.610163408547364},
        {'Metric': 'Spawn density status', 'Value': 'spawn_rate_curve_available_kill_density_transform_missing'},
        {
            'Metric': 'Kill-density transform readiness',
            'Value': 'source_spawn_rate_available_kill_density_transform_missing',
        },
        {
            'Metric': 'Kill-density transform gaps',
            'Value': (
                'source_owned_normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase, '
                'approved_spawn_rate_to_kill_density_transform, '
                'tier_wave_spawn_phase_validation_set, '
                'integration_with_intro_sprint_wave_skip_and_econ_windows'
            ),
        },
        {
            'Metric': 'Kill-density tracker candidate',
            'Value': 'tracker_spawn_rate_to_kill_density_candidate_available',
        },
        {'Metric': 'Kill-density transform approval', 'Value': 'not_approved'},
        {'Metric': 'Kill-density formula link closed', 'Value': False},
        {'Metric': 'Farming displayed spawn rate', 'Value': 56.0},
        {'Metric': 'WA spawn acceleration', 'Value': 1.8},
        {'Metric': 'Spawn count curve available', 'Value': False},
        {'Metric': 'Spawn count source audit', 'Value': 'source_not_found_spawn_rate_curve_only'},
        {
            'Metric': 'Spawn count missing source',
            'Value': 'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase',
        },
        {
            'Metric': 'Pressure driver evidence status',
            'Value': 'driver_inputs_available_terminal_transform_missing',
        },
        {'Metric': 'Elite pressure index', 'Value': 66.0},
        {'Metric': 'Fleet events/wave pressure', 'Value': 0.001},
        {'Metric': 'Tracker enemy-density status', 'Value': 'tracker_t14_farming_enemy_density_available'},
        {'Metric': 'Tracker enemies/wave', 'Value': 136.65},
        {'Metric': 'Tracker enemy composition status', 'Value': 'tracker_enemy_composition_available'},
        {'Metric': 'Tracker protector share', 'Value': 0.0011563682071846562},
        {'Metric': 'Tracker protectors/wave', 'Value': 0.16219162793768876},
        {'Metric': 'Tracker elite share', 'Value': 0.0010603108321965839},
        {'Metric': 'Tracker elite subtypes/wave', 'Value': 0.14411844882426642},
        {'Metric': 'Tracker vampire share', 'Value': 0.0003823225815743974},
        {'Metric': 'Tracker ray share', 'Value': 0.000336105991654569},
        {'Metric': 'Tracker scatter share', 'Value': 0.0003418822589676175},
        {'Metric': 'Tracker density / spawn-rate ratio', 'Value': 2.44},
        {
            'Metric': 'Tracker kill-density candidate status',
            'Value': 'tracker_spawn_rate_to_kill_density_candidate_available',
        },
        {'Metric': 'Tracker projected enemies/wave', 'Value': 136.65},
        {'Metric': 'Tracker enemies/wave per spawn rate', 'Value': 2.44},
        {
            'Metric': 'Tracker density stability status',
            'Value': 'tracker_recent_prior_kill_density_transform_available',
        },
        {'Metric': 'Tracker recent density/spawn', 'Value': 2.56},
        {'Metric': 'Tracker prior density/spawn', 'Value': 2.31},
        {'Metric': 'Tracker coin-density status', 'Value': 'tracker_t14_farming_coin_density_available'},
        {'Metric': 'Tracker coins/enemy', 'Value': 1_698_794_935.61},
        {'Metric': 'Tracker coins/wave', 'Value': 232_272_088_511.65},
        {
            'Metric': 'Tracker coin-yield stability status',
            'Value': 'tracker_recent_prior_coin_yield_available',
        },
        {'Metric': 'Tracker coins/enemy recent/prior', 'Value': 1.18},
        {'Metric': 'Tracker coins/wave recent/prior', 'Value': 1.17},
        {
            'Metric': 'Tracker coin-integral status',
            'Value': 'tracker_kill_density_to_coin_integral_candidate_available',
        },
        {'Metric': 'Tracker projected coins/wave', 'Value': 232_148_757_616.68},
        {'Metric': 'Tracker projected CPH', 'Value': 227_714_638_100_570.44},
        {'Metric': 'Tracker projected / reported CPH', 'Value': 1.002507817035684},
        {'Metric': 'Available drivers', 'Value': 22},
        {'Metric': 'Total drivers', 'Value': 23},
        {'Metric': 'Missing formula links', 'Value': 2},
    ]

    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    checks_start = source.index('def _render_checks')
    checks_end = source.index("\ndef _render_inputs", checks_start)
    checks_block = source[checks_start:checks_end]
    assert 'farming_cph_uncertified' in checks_block
    assert 'farming_cph_blockers' in checks_block
    assert "st.caption('Farming CPH readiness summary')" in checks_block
    assert '_farming_econ_readiness_summary_frame(diagnostics)' in checks_block


def test_streamlit_perks_tab_renders_four_policy_columns():
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    markdown_text = '\n'.join(str(item.value) for item in app_test.markdown)
    caption_text = '\n'.join(str(item.value) for item in app_test.caption)
    for policy_preset in ('eHP Max Waves', 'eHP Farming', 'GC Max Waves', 'GC Farming'):
        assert policy_preset in markdown_text
    assert caption_text.count('Priority order') == 4
    assert caption_text.count('Bans') == 4
    assert caption_text.count('Taken by wave') == 4


def test_streamlit_perks_table_does_not_fallback_to_active_preset_for_tourney():
    from app.streamlit_inspector import _perk_display_preset

    account_state = {
        'active_perk_preset': 'ProjectedMaxPolicy_AllExceptManualBans',
        'perk_presets': {
            'ProjectedMaxPolicy_AllExceptManualBans': [{'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1}],
            'Farming': [{'perk_id': 'PERK_X1_15_DAMAGE', 'picks': 1}],
        },
    }

    assert _perk_display_preset(account_state, selected_preset='Tourney') is None
    assert _perk_display_preset(account_state, selected_preset='Farming') == 'Farming'
    assert (
        _perk_display_preset(account_state, selected_preset='Milestone')
        == 'ProjectedMaxPolicy_AllExceptManualBans'
    )


def test_streamlit_pipeline_tourney_gc_max_waves_run_click_is_perk_guarded(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_tourney_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Tourney')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'GC Max Waves')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Tourney'
    assert diagnostics['perk_support']['perk_policy_preset'] == 'GC Max Waves'
    assert diagnostics['perk_support']['perk_materialization'] is False
    assert diagnostics['perk_support']['active_perk_preset'] is None
    assert diagnostics['state_matrix']['start_of_run']['perks_enabled'] is False
    assert diagnostics['state_matrix']['max_progression']['perks_enabled'] is False


def test_streamlit_pipeline_milestone_run_publishes_optimizer_unavailable(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_milestone_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Milestone')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'eHP Max Waves')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    optimizer_scores = json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Milestone'
    assert diagnostics['optimizer_scores']['status'] == 'unavailable'
    assert diagnostics['optimizer_scores']['reason'] == 'missing_governed_surface'
    assert optimizer_scores['meta']['status'] == 'unavailable'
    assert optimizer_scores['meta']['local_canonical_formula_fallback'] is False


def test_streamlit_pipeline_gc_farming_plan_runs_without_errors(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    out_dir = tmp_path / 'streamlit_gc_farming_run'
    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run output dir', str(out_dir))
    _set_streamlit_selectbox(app_test, 'Run loadout', 'Farming')
    _set_streamlit_selectbox(app_test, 'Run perk plan', 'GC Farming')
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert not app_test.error
    diagnostics = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    assert diagnostics['default_preset'] == 'Farming'
    assert diagnostics['perk_support']['perk_policy_preset'] == 'GC Farming'


def test_streamlit_register_snapshot_replaces_stale_label_for_reused_output_dir(monkeypatch, tmp_path):
    from app import streamlit_inspector as inspector

    out_dir = tmp_path / 'streamlit_reused_out'
    stale_label = inspector.snapshot_label(
        preset='Farming',
        state_mode='start_of_run',
        perk_state='auto',
        out_dir=out_dir,
    )
    session_state = {
        'snapshot_dirs': {stale_label: str(out_dir)},
        'active_out_dir': str(out_dir),
    }
    monkeypatch.setattr(inspector.st, 'session_state', session_state)

    inspector._register_snapshot(out_dir, preset='Tourney', state_mode='start_of_run', perk_state='auto')

    labels = list(session_state['snapshot_dirs'])
    assert stale_label not in labels
    assert len(labels) == 1
    assert labels[0].startswith('Tourney | start_of_run | perks auto |')
    assert session_state['snapshot_dirs'][labels[0]] == str(out_dir)


def test_streamlit_fast_checkpoint_button_is_scoped_to_stats_evidence_expander():
    source = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    tools_start = source.index('def _render_stats_debug_tools(')
    tools_end = source.index('\ndef _render_stats(', tools_start)
    tools_block = source[tools_start:tools_end]
    stats_start = source.index('def _render_stats(')
    stats_end = source.index('\ndef _require_boss_wave_payload_rows', stats_start)
    stats_block = source[stats_start:stats_end]

    assert "st.button('Resolve selected stats via fast checkpoint'" in tools_block
    assert 'runtime_state_overlay=request.runtime_state_overlay' in tools_block
    assert "with st.expander('Stats evidence and verification', expanded=False):" in stats_block
    assert '_render_stats_debug_tools(active_artifacts, comparison_artifacts, request)' in stats_block


def test_streamlit_pipeline_run_failures_are_contained(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Run IDS path', str(tmp_path / 'missing_ids.csv'))
    _set_streamlit_text_input(app_test, 'Run output dir', str(tmp_path / 'bad_run_out'))
    _click_streamlit_button(app_test, 'Run snapshot')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert any('Run snapshot failed:' in str(error.value) for error in app_test.error)


def test_streamlit_checks_verification_failures_are_contained(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Verification IDS path', str(tmp_path / 'missing_ids.csv'))
    _set_streamlit_text_input(app_test, 'Verification output dir', str(tmp_path / 'bad_verification_out'))
    _click_streamlit_button(app_test, 'Build default verification set')
    app_test.run(timeout=240)

    assert not app_test.exception
    assert any('Build default verification set failed:' in str(error.value) for error in app_test.error)


def test_streamlit_default_verification_snapshots_can_be_selected(tmp_path):
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")

    app_test = streamlit_testing.AppTest.from_file(str(ROOT / 'app' / 'streamlit_inspector.py'))
    app_test.run(timeout=240)
    _set_streamlit_text_input(app_test, 'Verification output dir', str(tmp_path / 'verification_base'))
    _click_streamlit_button(app_test, 'Build default verification set')
    app_test.run(timeout=360)

    assert not app_test.exception
    assert not app_test.error
    snapshot_options = list(_streamlit_widget_by_label(app_test.sidebar.selectbox, 'Active snapshot').options)
    assert {
        'Farming | start_of_run | perks auto | farming_start_of_run',
        'Farming | max_progression | perks auto | farming_max_progression',
        'Tourney | start_of_run | perks off | tourney_start_of_run',
        'Tourney | max_progression | perks off | tourney_max_progression',
    }.issubset(set(snapshot_options))
    for option in snapshot_options:
        _streamlit_widget_by_label(app_test.sidebar.selectbox, 'Active snapshot').set_value(option)
        app_test.run(timeout=240)
        assert not app_test.exception
        assert not app_test.error


def test_pipeline_writes_input_dashboard_contract(tmp_path, monkeypatch):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    monkeypatch.setattr(
        'app.pipeline._build_input_dashboard_qe_publications',
        lambda **_kwargs: {
            'workshop_coin_values': {'Damage': 'xUI_SENTINEL_COIN'},
            'workshop_max_values': {'Damage': 'xUI_SENTINEL_MAX'},
        },
    )

    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'out',
        )
    )
    assert result.exit_code == 0
    dashboard_path = result.out_dir / 'input_dashboard.json'
    assert dashboard_path.exists()
    payload = json.loads(dashboard_path.read_text(encoding='utf-8'))
    assert sorted(payload.keys()) == [
        'debug_manifest',
        'panels',
        'preset_options',
        'schema_version',
        'selected_preset',
        'upstream_gaps',
    ]
    assert payload.get('schema_version') == 2
    assert payload['selected_preset']
    assert {'Farming', 'Tourney', 'Milestone', 'Preset 4', 'Preset 5'}.issubset(set(payload.get('preset_options') or []))
    panel_ids = [panel.get('panel_id') for panel in (payload.get('panels') or [])]
    panel_types = [panel.get('panel_type') for panel in (payload.get('panels') or [])]
    assert panel_ids == [
        'labs',
        'workshop',
        'workshop_enhancements',
        'ultimate_weapons',
        'cards',
        'bots',
        'relics',
        'modules',
        'vault',
        'guardians',
        'themes_and_songs',
    ]
    assert panel_types == [
        'labs_bucket_grid',
        'grouped_workshop_table',
        'grouped_enhancement_table',
        'uw_track_table',
        'cards_inventory_and_preset',
        'track_table',
        'simple_bonus_table',
        'module_slot_stack',
        'simple_bonus_table',
        'track_table',
        'simple_metric_panel',
    ]
    panel_by_id = {panel.get('panel_id'): panel for panel in (payload.get('panels') or [])}
    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'xUI_SENTINEL_COIN'
    assert damage_row.get('max_value') == 'xUI_SENTINEL_MAX'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']


def test_pipeline_writes_stats_dashboard_contract(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    payload = canonical_pipeline_artifacts['dashboards']['stats_dashboard']

    assert (out_dir / 'stats_dashboard.json').exists()
    assert (out_dir / 'run_stats_query_rows_start_of_run.json').exists()
    assert (out_dir / 'run_stats_query_rows_max_progression.json').exists()
    assert sorted(payload.keys()) == [
        'artifact',
        'contract',
        'dashboard_version',
        'debug_manifest',
        'panels',
        'preset_options',
        'schema_version',
        'secondary_panels',
        'secondary_variants',
        'selected_preset',
        'selected_state_mode',
        'state_mode_options',
        'upstream_gaps',
        'variants',
    ]
    assert payload.get('artifact') == 'stats_dashboard.json'
    assert payload.get('contract', {}).get('owner') == 'qe'
    assert payload.get('schema_version') == 1
    assert payload.get('selected_preset') == 'Farming'
    assert payload.get('selected_state_mode') == 'start_of_run'
    panel_ids = [panel.get('panel_id') for panel in (payload.get('panels') or [])]
    assert panel_ids == [
        'derived_wall_economy',
        'workshop',
        'ultimate_weapons',
        'bots',
        'guardians',
        'modules',
    ]
    secondary_panel_ids = [panel.get('panel_id') for panel in (payload.get('secondary_panels') or [])]
    assert secondary_panel_ids == [
        'offense_resolved',
        'defense_resolved',
        'utility_resolved',
        'wall_economy_resolved',
        'cards_resolved',
        'bots_resolved',
        'guardians_resolved',
        'modules_resolved',
        'uw_stats_resolved',
    ]
    variants = payload.get('variants') or {}
    secondary_variants = payload.get('secondary_variants') or {}
    farming_variants = variants.get('Farming') or {}
    farming_secondary_variants = secondary_variants.get('Farming') or {}
    assert {'start_of_run', 'max_progression'}.issubset(set(farming_variants.keys()))
    assert {'start_of_run', 'max_progression'}.issubset(set(farming_secondary_variants.keys()))
    start_panels = farming_variants['start_of_run']
    max_panels = farming_variants['max_progression']
    start_secondary_panels = farming_secondary_variants['start_of_run']
    start_workshop = next(panel for panel in start_panels if panel.get('panel_id') == 'workshop')
    max_workshop = next(panel for panel in max_panels if panel.get('panel_id') == 'workshop')
    start_uw = next(panel for panel in start_panels if panel.get('panel_id') == 'ultimate_weapons')
    start_derived = next(panel for panel in start_panels if panel.get('panel_id') == 'derived_wall_economy')
    max_derived = next(panel for panel in max_panels if panel.get('panel_id') == 'derived_wall_economy')
    start_bots = next(panel for panel in start_panels if panel.get('panel_id') == 'bots')
    start_guardians = next(panel for panel in start_panels if panel.get('panel_id') == 'guardians')
    start_modules = next(panel for panel in start_panels if panel.get('panel_id') == 'modules')
    assert start_workshop.get('payload', {}).get('sections')
    assert max_workshop.get('payload', {}).get('sections')
    assert any(section.get('title') == 'Derived' for section in (start_derived.get('payload', {}).get('sections') or []))
    assert [table.get('title') for table in (start_derived.get('payload', {}).get('objective_tables') or [])] == ['eHP', 'eDamage', 'eEcon']
    assert [table.get('title') for table in (max_derived.get('payload', {}).get('objective_tables') or [])] == ['eHP', 'eDamage', 'eEcon']
    assert start_uw.get('payload', {}).get('sections')
    assert start_bots.get('payload', {}).get('sections')
    assert start_guardians.get('payload', {}).get('sections')
    assert 'slots' in (start_modules.get('payload') or {})
    assert (start_modules.get('payload') or {}).get('summary_rows')
    assert any(panel.get('panel_id') == 'offense_resolved' for panel in start_secondary_panels)


def test_pipeline_run_stats_query_rows_publish_qe_derived_wall_semantics(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    start_rows = json.loads((out_dir / 'run_stats_query_rows_start_of_run.json').read_text(encoding='utf-8'))
    max_rows = json.loads((out_dir / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))

    start_farming = (start_rows.get('Farming') or {}).get('rows') or {}
    max_farming = (max_rows.get('Farming') or {}).get('rows') or {}

    start_free_attack = start_farming['state::tower.free_attack_upgrade_chance_pct']['final_value']
    max_free_attack = max_farming['state::tower.free_attack_upgrade_chance_pct']['final_value']
    assert start_free_attack > 0.0
    assert max_free_attack > start_free_attack
    assert 'derived::wall.hp_pre_fort' in start_farming
    assert start_farming['derived::wall.hp_pre_fort']['final_value'] > 0
    assert max_farming['derived::wall.hp_pre_fort']['final_value'] > start_farming['derived::wall.hp_pre_fort']['final_value']
    support_bh_duration = start_farming['support_surface::ehp.black_hole_duration_seconds']['final_value']
    support_bh_cooldown = start_farming['support_surface::ehp.black_hole_cooldown_seconds']['final_value']
    bh_duration = start_farming['state::uw.black_hole.duration_seconds']['final_value']
    bh_cooldown = start_farming['state::uw.black_hole.cooldown_seconds']['final_value']
    assert 0.0 < support_bh_duration <= bh_duration
    assert support_bh_cooldown >= bh_cooldown > 0.0
    assert start_farming['state::uw.black_hole.base_duration_seconds']['final_value'] == pytest.approx(
        bh_duration
    )
    assert start_farming['state::uw.black_hole.base_cooldown_seconds']['final_value'] == pytest.approx(
        bh_cooldown
    )
    gt_duration = start_farming['state::uw.golden_tower.duration_seconds']['final_value']
    gt_cooldown = start_farming['state::uw.golden_tower.cooldown_seconds']['final_value']
    assert gt_duration > 0.0
    assert gt_cooldown > gt_duration
    assert start_farming['state::uw.golden_tower.base_duration_seconds']['final_value'] == pytest.approx(
        gt_duration
    )
    assert start_farming['state::uw.golden_tower.base_cooldown_seconds']['final_value'] == pytest.approx(
        gt_cooldown
    )
    assert start_farming['derived::ehp.primordial_black_hole_uptime']['final_value'] == pytest.approx(
        support_bh_duration / (support_bh_duration + support_bh_cooldown)
    )
    assert start_farming['derived::ehp.primordial_black_hole_damage_reduction_factor']['final_value'] > 1.0
    health_relic_pct = start_farming['support_surface::ehp.health_relic_pct']['final_value']
    dabs_relic_pct = start_farming['support_surface::ehp.dabs_relic_pct']['final_value']
    def_pct_relic_pct = start_farming['support_surface::ehp.def_pct_relic_pct']['final_value']
    adstarter_factor = start_farming['support_surface::eecon.adstarter_theme_relic_factor']['final_value']
    assert start_farming['derived::ehp.health_relic_factor']['final_value'] == pytest.approx(
        1.0 + health_relic_pct
    )
    assert start_farming['derived::ehp.dabs_relic_factor']['final_value'] == pytest.approx(
        1.0 + dabs_relic_pct
    )
    assert start_farming['derived::ehp.def_pct_relic_term']['final_value'] == pytest.approx(
        def_pct_relic_pct
    )
    assert start_farming['derived::eecon.base_meta_factor']['final_value'] == pytest.approx(
        adstarter_factor
    )
    assert start_farming['support_surface::eecon.freeup_attack_relic_pct']['final_value'] >= 0.0
    assert start_farming['support_surface::eecon.freeup_defense_relic_pct']['final_value'] >= 0.0
    assert start_farming['support_surface::eecon.freeup_utility_relic_pct']['final_value'] >= 0.0


def test_pipeline_tier_scoped_dissonance_reconciles_t14_ep_panels(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    out_dir = tmp_path / "tier14_pipeline_out"
    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=out_dir,
            preset='Farming',
            state_mode='max_progression',
            tier=14,
            runtime_state_overlay='disco_respec_2026_06_10',
        )
    )
    assert result.exit_code == 0
    rows = json.loads((out_dir / 'run_stats_query_rows_max_progression.json').read_text(encoding='utf-8'))['Farming']['rows']

    assert rows['derived::dissonance.defense.total_multiplier']['final_value'] > 1.0
    assert rows['derived::ehp.health_factor']['final_value'] > 0.0
    chain_thunder_reduction_pct = rows[
        'state::uw.chain_lightning.max_enemy_damage_reduction_pct'
    ]['final_value']
    assert 0.0 < chain_thunder_reduction_pct < 100.0
    assert rows['derived::ehp.chain_thunder_factor']['final_value'] == pytest.approx(
        1.0 / (1.0 - (chain_thunder_reduction_pct / 100.0))
    )
    assert rows['derived::ehp']['final_value'] > 0.0
    assert rows['state::tower.regen']['final_value'] > 0.0
    fortification_multiplier = rows['state::wall.fortification_multiplier']['final_value']
    wall_hp_pre_fort = rows['derived::wall.hp_pre_fort']['final_value']
    assert fortification_multiplier >= 1.0
    assert wall_hp_pre_fort > 0.0
    assert rows['derived::wall.hp_final']['final_value'] == pytest.approx(
        wall_hp_pre_fort * fortification_multiplier
    )
    assert rows['derived::wall.regen_hp_per_second']['final_value'] > 0.0
    assert rows['state::tower.defense_absolute']['status'] == 'resolved'
    assert rows['derived::ehp.dabs_perk_factor']['final_value'] == pytest.approx(1.0)
    assert rows['state::tower.defense_absolute']['final_value'] > 0.0
    assert rows['state::economy.coins_per_kill_bonus']['final_value'] > 0.0
    assert rows['state::economy.all_coin_bonus_multiplier']['final_value'] > 1.0
    assert rows['state::cards.wave_skip.chance_pct']['final_value'] > 0.0
    assert rows['state::cards.intro_sprint.waves']['final_value'] > 0.0
    assert rows['support_surface::scenario.target_farming_wave']['final_value'] > 0.0
    assert rows['support_surface::scenario.waves_per_run_effective']['final_value'] > rows[
        'support_surface::scenario.target_farming_wave'
    ]['final_value']
    assert rows['support_surface::scenario.runs_per_day_effective']['status'] == 'resolved'
    assert rows['derived::eecon.freeup_factor']['final_value'] > 1.0
    assert rows['derived::eecon.wave_factor']['final_value'] > 1.0
    assert rows['derived::eecon.utility_dissonance_factor']['final_value'] > 1.0
    assert rows['derived::eecon.unit_scale_factor']['final_value'] == pytest.approx(1000.0)
    assert rows['derived::eecon']['final_value'] > 0.0


def test_pipeline_cards_payload_publishes_selected_rows_by_preset(canonical_pipeline_artifacts):
    out_dir = canonical_pipeline_artifacts['out_dir']
    dashboard = canonical_pipeline_artifacts['dashboards']['input_dashboard']
    account_state = json.loads((out_dir / 'account_state.json').read_text(encoding='utf-8'))
    cards_panel = next(panel for panel in (dashboard.get('panels') or []) if panel.get('panel_id') == 'cards')
    payload = cards_panel.get('payload') or {}

    selected_preset = str(dashboard.get('selected_preset'))
    preset_options = [str(name) for name in (dashboard.get('preset_options') or [])]
    preset_rows_by_preset = payload.get('preset_rows_by_preset') or {}
    assert isinstance(preset_rows_by_preset, dict)
    assert selected_preset in preset_rows_by_preset
    assert set(preset_options).issubset(set(preset_rows_by_preset))
    selected_names_from_dashboard = {
        str(row.get('name'))
        for row in (preset_rows_by_preset.get(selected_preset) or [])
        if str(row.get('selected') or '').strip() == 'Yes'
    }
    selected_names_from_state = set((account_state.get('card_presets') or {}).get(selected_preset) or [])
    assert selected_names_from_dashboard == selected_names_from_state


def test_streamlit_app_contract_is_frozen_in_repo() -> None:
    contract_path = ROOT / 'app' / 'streamlit_inspector.py'
    text = contract_path.read_text(encoding='utf-8')
    assert '`streamlit` is optional' in text.lower()
    assert 'boss waves is interactive' in text.lower()
    assert 'permanently removed' in text.lower()
    assert 'from input.loader import load_inputs' not in text
    assert 'from input.runtime_state import build_runtime_state' not in text
    assert 'from simulators.run_executor import' not in text
    assert 'from qe.stat_input_compiler import' not in text
    assert 'manual_inputs.yaml' not in text
    assert 'kb/' not in text


def test_streamlit_stats_and_boss_waves_use_sanctioned_facades() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert 'query_rows_dual_state_frame(' in text
    assert 'query_rows_surface_detail(' in text
    assert 'build_boss_wave_payload(' in text
    assert '_module_unique_effect_map(' not in text


def test_boss_waves_render_uses_published_summary_and_execution_contract() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("def _render_boss_waves(request: PipelineRunRequest")
    end = text.index("\ndef main() -> None:", start)
    boss_block = text[start:end]
    assert "stop_on_failure = True" in boss_block
    assert "stop_on_failure=stop_on_failure" in boss_block
    assert "dissonance_run_category=dissonance_run_category" in boss_block
    assert "matrix_all_run_types = matrix_cols[3].checkbox('All run types', value=True)" in boss_block
    assert "matrix_all_tiers = matrix_cols[4].checkbox('All tiers', value=True)" in boss_block
    assert "comparison_pressure_factor = matrix_cols[5].number_input(" in boss_block
    assert "'Comparison pressure factor'" in boss_block
    assert "'Compare fleet terminal wave'" in boss_block
    assert "'Compare elite terminal wave'" in boss_block
    assert "'Compare protector terminal wave'" in boss_block
    assert "'Compare armored terminal wave'" in boss_block
    assert "'Compare boss terminal wave'" in boss_block
    assert "matrix_comparison_inputs = {" in boss_block
    assert "'fleet_terminal_max_wave': comparison_fleet_terminal_max_wave" in boss_block
    assert "'elite_terminal_max_wave': comparison_elite_terminal_max_wave" in boss_block
    assert "'protector_terminal_max_wave': comparison_protector_terminal_max_wave" in boss_block
    assert "'armored_terminal_max_wave': comparison_armored_terminal_max_wave" in boss_block
    assert "'boss_terminal_max_wave': comparison_boss_terminal_max_wave" in boss_block
    assert "('none', *BOSS_WAVE_DISSONANCE_RUN_CATEGORIES)" in boss_block
    assert "else (dissonance_run_category,)" in boss_block
    assert "dissonance_run_categories=matrix_run_categories" in boss_block
    assert "BOSS_WAVE_DISSONANCE_RUN_LABELS" in boss_block
    assert "Stop on first failed boss" not in boss_block
    assert "rows after the first failure" not in boss_block
    assert "'flame_bot_boss_hit_chance_pct':" not in boss_block
    assert "'flame_bot_damage_reduction_pct': flame_bot_damage_reduction_pct" in boss_block
    assert "'boss_applicable_damage_factor': boss_applicable_damage_factor" in boss_block
    assert "'boss_edamage_target_share': boss_edamage_target_share" in boss_block
    assert "'boss_edamage_cadence_uptime_factor': boss_edamage_cadence_uptime_factor" in boss_block
    assert "'boss_edamage_reliability_factor': boss_edamage_reliability_factor" in boss_block
    assert "'boss_edamage_semantic_normalizer': boss_edamage_semantic_normalizer" in boss_block
    assert "if use_recommended_model_assumptions:" in boss_block
    assert "**_boss_wave_recommended_model_runtime_inputs()," in boss_block
    assert "_boss_wave_recommended_model_assumption_frame()" in boss_block
    assert "nonzero manual combat fields override the recommended values" in boss_block
    assert "'fleet_terminal_max_wave': fleet_terminal_max_wave" in boss_block
    assert "'elite_terminal_max_wave': elite_terminal_max_wave" in boss_block
    assert "'protector_terminal_max_wave': protector_terminal_max_wave" in boss_block
    assert "'armored_terminal_max_wave': armored_terminal_max_wave" in boss_block
    assert "'boss_terminal_max_wave': boss_terminal_max_wave" in boss_block
    assert "decomposed_bridge_inputs" in boss_block
    assert "build_boss_wave_milestone_matrix(" in boss_block
    assert "comparison_scenario_runtime_inputs=matrix_comparison_inputs or None" in boss_block
    assert "'boss_wave_pressure_factor': comparison_pressure_factor" in boss_block
    assert "_boss_wave_matrix_comparison_label_from_runtime_inputs(" in boss_block
    assert "matrix_tiers = tuple(range(1, 22)) if bool(matrix_all_tiers) else (int(tier_number),)" in boss_block
    assert "tiers=matrix_tiers" in boss_block
    assert "Build 4-preset matrix" in boss_block
    assert "All-tier preset matrix" in boss_block
    assert "Matrix end wave" in boss_block
    assert "Matrix checkpoint cadence (bosses)" in boss_block
    assert "value=max(30000, int(end_wave))" in boss_block
    assert "value=max(10, int(boss_wave_step))" in boss_block
    assert "Build all-tier milestone matrix" not in boss_block
    assert "All-tier milestone matrix" not in boss_block
    assert "_boss_wave_matrix_alignment_summary_frame(matrix_payload)" in boss_block
    assert "model_blocker_frame = _boss_wave_matrix_model_blocker_frame(matrix_payload)" in boss_block
    assert "if not model_blocker_frame.empty:" in boss_block
    assert "model_accuracy_frame = _boss_wave_matrix_model_accuracy_frame(matrix_payload)" in boss_block
    assert "if not model_accuracy_frame.empty:" in boss_block
    assert "Model accuracy posture" in boss_block
    assert "primitive_family_frame = _boss_wave_matrix_primitive_family_coverage_frame(matrix_payload)" in boss_block
    assert "if not primitive_family_frame.empty:" in boss_block
    assert "Primitive family coverage" in boss_block
    assert "terminal_requirement_frame = _boss_wave_matrix_terminal_pressure_requirement_frame(matrix_payload)" in boss_block
    assert "if not terminal_requirement_frame.empty:" in boss_block
    assert "Terminal pressure inputs" in boss_block
    assert "reference_gap_frame = _boss_wave_matrix_reference_gap_frame(matrix_payload)" in boss_block
    assert "if not reference_gap_frame.empty:" in boss_block
    assert "reference_quality_frame = _boss_wave_matrix_reference_quality_frame(matrix_payload)" in boss_block
    assert "if not reference_quality_frame.empty:" in boss_block
    assert "Reference quality" in boss_block
    assert "pressure_hint_summary_frame = _boss_wave_matrix_pressure_factor_hint_summary_frame(matrix_payload)" in boss_block
    assert "if not pressure_hint_summary_frame.empty:" in boss_block
    assert "Pressure factor hints" in boss_block
    assert "pressure_hint_by_run_type_frame = _boss_wave_matrix_pressure_factor_hint_by_run_type_frame(matrix_payload)" in boss_block
    assert "if not pressure_hint_by_run_type_frame.empty:" in boss_block
    assert "_boss_wave_preset_matrix_frame(matrix_payload)" in boss_block
    assert "comparison_summary_frame = _boss_wave_matrix_comparison_alignment_summary_frame(matrix_payload)" in boss_block
    assert "if not comparison_summary_frame.empty:" in boss_block
    assert (
        "comparison_calculated_summary_frame = _boss_wave_matrix_comparison_calculated_delta_summary_frame("
        in boss_block
    )
    assert "if not comparison_calculated_summary_frame.empty:" in boss_block
    assert "comparison_matrix = dict(dict(matrix_payload.get('comparison') or {}).get('matrix') or {})" in boss_block
    assert "comparison_model_blocker_frame = _boss_wave_matrix_model_blocker_frame(comparison_matrix)" in boss_block
    assert "if not comparison_model_blocker_frame.empty:" in boss_block
    assert "Comparison model status" in boss_block
    assert "comparison_model_accuracy_frame = _boss_wave_matrix_model_accuracy_frame(comparison_matrix)" in boss_block
    assert "if not comparison_model_accuracy_frame.empty:" in boss_block
    assert "Comparison accuracy posture" in boss_block
    assert (
        "comparison_terminal_requirement_frame = _boss_wave_matrix_terminal_pressure_requirement_frame("
        in boss_block
    )
    assert "if not comparison_terminal_requirement_frame.empty:" in boss_block
    assert "Comparison terminal pressure inputs" in boss_block
    assert "comparison_reference_gap_frame = _boss_wave_matrix_reference_gap_frame(comparison_matrix)" in boss_block
    assert "if not comparison_reference_gap_frame.empty:" in boss_block
    assert "Comparison missing references" in boss_block
    assert "comparison_pressure_hint_frame = _boss_wave_matrix_pressure_factor_hint_by_run_type_frame(" in boss_block
    assert "if not comparison_pressure_hint_frame.empty:" in boss_block
    assert "Comparison pressure factor hints" in boss_block
    assert "comparison_frame = _boss_wave_matrix_comparison_frame(matrix_payload)" in boss_block
    assert "if not comparison_frame.empty:" in boss_block
    assert "candidate_count = sum(len(row.get('candidate_results') or []) for row in matrix_rows)" in boss_block
    assert "include_dissonance_run_matrix" not in boss_block
    assert "Dissonance comparison" not in boss_block
    assert "dissonance_run_matrix" not in boss_block
    assert "'tournament_wave': int(tournament_wave_override)" in boss_block
    assert "Legends tournament wave" in boss_block
    assert "boss_calc_elapsed" in boss_block
    assert "display_frame = _build_boss_wave_operator_frame(frame)" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'operator_rows')" in boss_block
    assert "_require_boss_wave_payload_rows(boss_payload, 'download_rows')" in boss_block
    assert "boss_payload.get('rows') or []" not in boss_block
    assert "st.error(str(exc))" in boss_block
    assert "payload_summary = dict(boss_payload.get('summary') or {})" in boss_block
    assert "primitive_inputs = dict(payload_diagnostics.get('replacement_primitive_inputs') or {})" in boss_block
    assert "'terminal_pressure_limiter': payload_summary.get('terminal_pressure_limiter')" in boss_block
    assert "if diagnostics['terminal_pressure_limited']:" in boss_block
    assert "Blocked by `{diagnostics['terminal_pressure_limiter']}`" in boss_block
    assert "elif diagnostics['unsupported_pressure_reference_aligned']:" in boss_block
    assert "Aligned to IDS empirical reference" in boss_block
    assert "uncapped boss-only wave" in boss_block
    assert "_focus_boss_wave_display_frame(" in boss_block
    assert "_boss_wave_assumption_frame(" in boss_block
    assert "_boss_wave_runtime_inputs_frame(" in boss_block
    assert "_boss_wave_terminal_pressure_requirement_frame_from_status(" in boss_block
    assert "Terminal pressure inputs" in boss_block
    assert "metric('Rows'" not in boss_block
    assert "metric('Selected wave'" not in boss_block
    assert "metric('First failed wave'" not in boss_block
    assert "metric('Perk plan'" not in boss_block
    assert "metric('Tier'" not in boss_block
    assert "metric('Loadout'" not in boss_block
    assert "payload_diagnostics.get('model_certification') or {}" in boss_block
    assert "payload_diagnostics.get('contact_time_contract') or {}" in boss_block
    assert "payload_diagnostics.get('replacement_model') or {}" in boss_block
    assert "'replacement_primitive_inputs': primitive_inputs" in boss_block
    assert "'replacement_primitive_family_coverage': payload_diagnostics.get('replacement_primitive_family_coverage') or {}" in boss_block
    assert "payload_diagnostics.get('replacement_primitive_semantics_ledger') or {}" in boss_block
    assert "visible wall regen contribution" in boss_block

    helper_start = text.index("def _build_boss_wave_operator_frame(frame: pd.DataFrame) -> pd.DataFrame:")
    helper_end = text.index("\ndef _render_boss_waves(request: PipelineRunRequest", helper_start)
    helper_block = text[helper_start:helper_end]
    assert "'Wall Regen'" in helper_block
    assert "'Regen Gain'" in helper_block
    assert "'Boss Kill Time'" in helper_block
    assert "'Cont Dmg %'" in helper_block
    assert "'Hit Interval (s)'" in helper_block
    assert "'Damage Reduction'" in helper_block
    assert "'Killed Before Contact'" in helper_block
    assert "'Survival Margin'" in helper_block
    assert "def _boss_wave_assumption_frame(" in helper_block
    assert "def _boss_wave_recommended_model_runtime_inputs(" in helper_block
    assert "def _boss_wave_recommended_model_assumption_frame(" in helper_block
    assert "def _boss_wave_matrix_model_accuracy_frame(" in helper_block
    assert "def _boss_wave_matrix_primitive_family_coverage_frame(" in helper_block
    assert "'Boss damage source'" in helper_block
    assert "'Primitive family coverage'" in helper_block
    assert "'Chain Lightning DPS'" in helper_block
    assert "'EP eDamage base'" in helper_block
    assert "'Spotlight exposure'" in helper_block
    assert "'ACP factor'" in helper_block
    assert "'EN mastery multiplier'" in helper_block
    assert "'Boss time to contact'" in helper_block
    assert "'Chrono Field slow'" in helper_block
    assert "'Slow Aura slow'" in helper_block
    assert "payload_diagnostics = dict(boss_payload.get('diagnostics') or {})" in boss_block
    assert "payload_download = dict(boss_payload.get('download') or {})" in boss_block
    assert "diagnostics['context_status'] not in {'resolved', 'complete'}" in boss_block
    assert "boss_payload.get('contract') or {}" in boss_block
    assert "actual_boss_interval_waves" in boss_block
    assert "checkpoint_every_bosses" in boss_block
    assert "Boss Waves is a bounded runtime estimate" in boss_block
    assert "Advanced boss-wave evidence" in boss_block
    assert "Full boss-wave table" not in boss_block
    assert "Boss-wave diagnostics" not in boss_block
    assert "Boss-wave raw rows (debug)" not in boss_block
    assert "Boss-wave execution details" not in boss_block
    assert "st.download_button(" in boss_block


def test_boss_wave_assumption_frame_exposes_terminal_override_status() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("def _boss_wave_assumption_frame(")
    end = text.index("\ndef _boss_wave_runtime_inputs_frame", start)
    assumption_block = text[start:end]
    assert "terminal_pressure_runtime_override_status" in assumption_block
    assert "effective_model_closure" in assumption_block
    assert "accepted_approximation_closure" in assumption_block
    assert "Model closure status" in assumption_block
    assert "Accepted approximation closure" in assumption_block
    assert "Accepted approximation effect" in assumption_block
    assert "Effective non-boss pressure closure" in assumption_block
    assert "Effective Damage/Health Decay closure" in assumption_block
    assert "Effective boss damage closure" in assumption_block
    assert "Effective GC boss damage closure" in assumption_block
    assert "Terminal override required fields" in assumption_block
    assert "Terminal override missing fields" in assumption_block
    assert "Terminal override unmapped pressure" in assumption_block
    assert "Reference pressure factor hint" in assumption_block
    assert "Reference pressure hint direction" in assumption_block
    assert "Reference pressure hint mode" in assumption_block
    assert "Reference pressure hint input" in assumption_block
    assert "Damage/Health Decay source default" in assumption_block
    assert "Damage/Health Decay supplied fields" in assumption_block
    assert "Damage/Health Decay start fields" in assumption_block


def test_boss_wave_assumption_frame_exposes_pressure_factor_reference_hint() -> None:
    from app.streamlit_inspector import _boss_wave_assumption_frame

    frame = _boss_wave_assumption_frame(
        diagnostics={},
        contract={},
        payload_diagnostics={
            'pressure_factor_reference_hint': {
                'enabled': True,
                'mode': 'raw_calculated_wave_to_reference_ratio_hint',
                'rounded_boss_wave_pressure_factor': 1.795,
                'direction': 'increase_pressure',
                'comparison_scenario_runtime_inputs': {'boss_wave_pressure_factor': 1.794871794871795},
            },
            'model_certification': {
                'model_closure_status': 'closed_with_pressure_factor_approximation',
                'accepted_approximation_closure': {
                    'mode': 'boss_wave_pressure_factor_approximation',
                    'certification_effect': (
                        'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation'
                    ),
                },
            }
        },
        primitive_values={},
        boss_damage_source='test',
    )

    rows = {row['assumption']: row['value'] for row in frame.to_dict('records')}
    assert rows['Model closure status'] == 'closed_with_pressure_factor_approximation'
    assert rows['Accepted approximation closure'] == 'boss_wave_pressure_factor_approximation'
    assert rows['Accepted approximation effect'] == (
        'closes_non_boss_terminal_pressure_blocker_as_explicit_approximation'
    )
    assert rows['Reference pressure factor hint'] == '1.795'
    assert rows['Reference pressure hint direction'] == 'increase_pressure'
    assert rows['Reference pressure hint mode'] == 'raw_calculated_wave_to_reference_ratio_hint'
    assert rows['Reference pressure hint input'] == '{"boss_wave_pressure_factor": 1.794871794871795}'


def test_boss_wave_assumption_frame_exposes_damage_health_decay_closure_details() -> None:
    from app.streamlit_inspector import _boss_wave_assumption_frame

    frame = _boss_wave_assumption_frame(
        diagnostics={},
        contract={},
        payload_diagnostics={
            'model_certification': {
                'effective_model_closure': {
                    'non_boss_terminal_pressure': True,
                    'v28_damage_health_decay_magnitudes': True,
                    'boss_applicable_damage_semantics': False,
                    'gc_boss_applicable_damage_semantics': False,
                },
                'v28_damage_health_decay_closure': {
                    'mode': 'explicit_runtime_inputs',
                    'required_fields': ['tower_damage_decay_pct', 'tower_health_decay_pct'],
                    'missing_fields': [],
                    'source_owned_default_available': False,
                    'supplied_fields': ['tower_damage_decay_pct', 'tower_health_decay_pct'],
                    'supplied_start_wave_fields': ['tower_damage_decay_start_wave'],
                }
            }
        },
        primitive_values={},
        boss_damage_source='test',
    )

    rows = {
        str(row['assumption']): str(row['value'])
        for row in frame.to_dict('records')
        if str(row['assumption']).startswith('Damage/Health Decay')
    }
    assert rows['Damage/Health Decay closure'] == 'explicit_runtime_inputs'
    assert rows['Damage/Health Decay source default'] == 'no'
    assert rows['Damage/Health Decay supplied fields'] == 'tower_damage_decay_pct, tower_health_decay_pct'
    assert rows['Damage/Health Decay start fields'] == 'tower_damage_decay_start_wave'
    effective_rows = {
        str(row['assumption']): str(row['value'])
        for row in frame.to_dict('records')
        if str(row['assumption']).startswith('Effective ')
    }
    assert effective_rows['Effective non-boss pressure closure'] == 'yes'
    assert effective_rows['Effective Damage/Health Decay closure'] == 'yes'
    assert effective_rows['Effective boss damage closure'] == 'no'
    assert effective_rows['Effective GC boss damage closure'] == 'no'


def test_boss_wave_matrix_frame_exposes_model_honesty_columns() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("def _boss_wave_preset_matrix_frame(matrix_payload: dict[str, object])")
    end = text.index("\ndef _slug_text", start)
    matrix_block = text[start:end]
    assert "'Run type': matrix_row.get('label')" in matrix_block
    assert "'Ref caveats': ', '.join" in matrix_block
    assert "'Status': matrix_row.get('best_model_certification_status')" in matrix_block
    assert "'Limiter': matrix_row.get('terminal_pressure_limiter')" in matrix_block
    assert "'Pressure ref': matrix_row.get('terminal_pressure_reference_status')" in matrix_block
    assert "'Calculated': matrix_row.get('best_calculated_selected_max_wave')" in matrix_block
    assert "'Hit-by-hit': matrix_row.get('best_hit_by_hit_max_wave')" in matrix_block
    assert "'Contact env': matrix_row.get('best_contact_envelope_max_wave')" in matrix_block
    assert "'Nearest lane': _boss_wave_matrix_nearest_lane_text(matrix_row)" in matrix_block
    assert "'Nearest delta':" in matrix_block
    assert "'Calc delta':" in matrix_block
    assert "'Calc/ref': _boss_wave_matrix_ratio_text" in matrix_block
    assert "'Alignment': _boss_wave_matrix_alignment_text(matrix_row)" in matrix_block
    assert "'Unsupported': ', '.join" in matrix_block
    assert "'Run type'" in matrix_block
    assert "'Ref caveats'" in matrix_block
    assert "'Calculated'" in matrix_block
    assert "'Hit-by-hit'" in matrix_block
    assert "'Contact env'" in matrix_block
    assert "'Pre-contact'" in matrix_block
    assert "'GC pre-contact'" in matrix_block
    assert "'Nearest lane'" in matrix_block
    assert "'Nearest delta'" in matrix_block
    assert "'Calc delta'" in matrix_block
    assert "'Calc/ref'" in matrix_block
    assert "'Pressure hint'" in matrix_block
    assert "'Hint direction'" in matrix_block
    assert "'Status'" in matrix_block
    assert "'Limiter'" in matrix_block
    assert "'Pressure ref'" in matrix_block
    assert "'Alignment'" in matrix_block
    assert "'Unsupported'" in matrix_block


def test_boss_wave_matrix_pressure_factor_hint_summary_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_pressure_factor_hint_summary_frame

    frame = _boss_wave_matrix_pressure_factor_hint_summary_frame(
        {
            'pressure_factor_hint_summary': {
                'row_count': 105,
                'rows_with_pressure_factor_hint': 76,
                'direction_counts': {
                    'increase_pressure': 60,
                    'no_adjustment': 16,
                },
                'max_factor_distance_from_one': 15.537997587454765,
                'disabled_hint_mode_counts': {
                    'dissonance_pb_bonus_cap_not_exact_reference': 42,
                    'no_positive_reference_wave': 19,
                },
                'max_factor_distance_row': {
                    'tier': 1,
                    'tier_column': 'Tier 1',
                    'dissonance_run_category': 'attack',
                    'label': 'Attack Dissonant Run',
                    'boss_wave_pressure_factor': 16.537997587454765,
                    'direction': 'increase_pressure',
                    'calculated_selected_max_wave': 13710,
                    'reference_wave': 829,
                },
                'calibration_quality': {
                    'definition': 'calibration_candidate_with_no_reference_caveats',
                    'rows_with_pressure_factor_hint': 16,
                    'excluded_caveated_hint_count': 60,
                    'excluded_caveated_hint_reason_counts': {
                        'below_low_wave_threshold': 11,
                        'pb_age_unknown_no_source_timestamp': 56,
                    },
                    'direction_counts': {
                        'increase_pressure': 13,
                        'no_adjustment': 3,
                    },
                    'factor_distribution': {
                        'count': 16,
                        'min_factor': 1.0,
                        'median_factor': 2.606384292771721,
                        'mean_factor': 2.611575562832565,
                        'max_factor': 5.101279317697228,
                        'rounded_median_factor': 2.606,
                        'rounded_mean_factor': 2.612,
                        'comparison_scenario_runtime_inputs': {
                            'boss_wave_pressure_factor': 2.606384292771721,
                        },
                    },
                    'max_factor_distance_from_one': 4.101279317697228,
                    'max_factor_distance_row': {
                        'tier': 2,
                        'tier_column': 'Tier 2',
                        'dissonance_run_category': 'none',
                        'label': 'Regular',
                        'boss_wave_pressure_factor': 5.101279317697228,
                        'direction': 'increase_pressure',
                    },
                },
            }
        }
    )

    rows = {row['Field']: row['Value'] for row in frame.to_dict('records')}
    assert rows == {
        'Rows': '105',
        'Hinted rows': '76',
        'Increase hints': '60',
        'Decrease hints': '0',
        'No-adjustment hints': '16',
        'Max factor distance': '15.538',
        'Disabled hint modes': (
            'dissonance_pb_bonus_cap_not_exact_reference: 42, '
            'no_positive_reference_wave: 19'
        ),
        'Calibration-quality hinted rows': '16',
        'Excluded caveated hints': '60',
        'Excluded caveat reasons': (
            'below_low_wave_threshold: 11, '
            'pb_age_unknown_no_source_timestamp: 56'
        ),
        'Calibration increase hints': '13',
        'Calibration no-adjustment hints': '3',
        'Calibration max factor distance': '4.101',
        'Calibration median factor': '2.606',
        'Calibration mean factor': '2.612',
        'Calibration factor range': '1.0 - 5.101',
        'Calibration median input': '{"boss_wave_pressure_factor": 2.606384292771721}',
        'Worst hint row': 'Tier 1 / Attack Dissonant Run',
        'Worst hint factor': '16.538',
        'Worst hint direction': 'increase_pressure',
        'Worst calculated/reference': '13710 / 829',
        'Calibration worst row': 'Tier 2 / Regular',
        'Calibration worst factor': '5.101',
        'Calibration worst direction': 'increase_pressure',
    }


def test_boss_wave_matrix_pressure_factor_hint_by_run_type_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_pressure_factor_hint_by_run_type_frame

    frame = _boss_wave_matrix_pressure_factor_hint_by_run_type_frame(
        {
            'pressure_factor_hint_summary': {
                'by_run_type': [
                    {
                        'dissonance_run_category': 'none',
                        'label': 'Regular',
                        'row_count': 21,
                        'rows_with_pressure_factor_hint': 16,
                        'pressure_factor_evidence_quality': 'clean_calibration_available',
                        'pressure_factor_distribution': {
                            'median_factor': 2.606384292771721,
                        },
                        'explicit_comparison_input_hint': {
                            'boss_wave_pressure_factor': 2.606384292771721,
                        },
                        'calibration_quality_hint_count': 16,
                        'calibration_quality_factor_distribution': {
                            'median_factor': 2.606384292771721,
                        },
                        'excluded_caveated_hint_count': 0,
                        'direction_counts': {
                            'increase_pressure': 13,
                            'no_adjustment': 3,
                        },
                        'max_factor_distance_row': {
                            'tier': 2,
                            'tier_column': 'Tier 2',
                            'boss_wave_pressure_factor': 5.101279317697228,
                            'direction': 'increase_pressure',
                            'calculated_selected_max_wave': 28710,
                            'reference_wave': 5628,
                        },
                    },
                    {
                        'dissonance_run_category': 'utility',
                        'label': 'Utility Dissonant Run',
                        'row_count': 21,
                        'rows_with_pressure_factor_hint': 0,
                        'pressure_factor_evidence_quality': 'no_reference_hints',
                        'pressure_factor_distribution': {
                            'median_factor': None,
                        },
                        'explicit_comparison_input_hint': {},
                        'calibration_quality_hint_count': 0,
                        'calibration_quality_factor_distribution': {
                            'median_factor': None,
                        },
                        'excluded_caveated_hint_count': 0,
                        'direction_counts': {},
                        'max_factor_distance_row': {},
                    },
                ]
            }
        }
    )

    assert frame.to_dict('records') == [
        {
            'Run type': 'Regular',
            'Rows': 21,
            'Hinted': 16,
            'Evidence': 'clean_calibration_available',
            'Median factor': '2.606',
            'Review input': '{"boss_wave_pressure_factor": 2.606384292771721}',
            'Clean hints': 16,
            'Clean median': '2.606',
            'Caveated hints': 0,
            'Increase': 13,
            'Decrease': 0,
            'No adjustment': 3,
            'Worst factor': '5.101',
            'Worst direction': 'increase_pressure',
            'Worst row': 'Tier 2',
            'Worst calc/ref': '28710 / 5628',
        },
        {
            'Run type': 'Utility Dissonant Run',
            'Rows': 21,
            'Hinted': 0,
            'Evidence': 'no_reference_hints',
            'Median factor': '',
            'Review input': '',
            'Clean hints': 0,
            'Clean median': '',
            'Caveated hints': 0,
            'Increase': 0,
            'Decrease': 0,
            'No adjustment': 0,
            'Worst factor': '',
            'Worst direction': '',
            'Worst row': '',
            'Worst calc/ref': '',
        },
    ]


def test_boss_wave_matrix_primitive_family_coverage_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_primitive_family_coverage_frame

    frame = _boss_wave_matrix_primitive_family_coverage_frame(
        {
            'replacement_primitive_family_coverage_summary': {
                'status': 'covered',
                'selected_row_count': 105,
                'rows_with_coverage': 105,
                'missing_requested_families': [],
                'requested_effect_families': ['card_mastery', 'workshop'],
                'family_status_counts': {
                    'card_mastery': {'covered_by_qe_surface': 105},
                    'workshop': {'covered_by_qe_contributor': 105},
                },
            }
        }
    )

    assert frame.to_dict('records') == [
        {'Metric': 'Status', 'Value': 'covered'},
        {'Metric': 'Selected rows', 'Value': '105'},
        {'Metric': 'Rows with coverage', 'Value': '105'},
        {'Metric': 'Missing families', 'Value': 'n/a'},
        {'Metric': 'card_mastery status counts', 'Value': '{"covered_by_qe_surface": 105}'},
        {'Metric': 'workshop status counts', 'Value': '{"covered_by_qe_contributor": 105}'},
    ]


def test_boss_wave_matrix_frame_shows_clean_ids_reference_alignment() -> None:
    from app.streamlit_inspector import _boss_wave_preset_matrix_frame

    frame = _boss_wave_preset_matrix_frame(
        {
            'rows': [
                {
                    'tier': 14,
                    'tier_column': 'Tier 14',
                    'label': 'Utility Dissonant Run',
                    'reference_wave': 4402,
                    'reference_quality': {
                        'caveats': ['pb_age_unknown_no_source_timestamp'],
                    },
                    'best_display': '4402 (eHP Max Waves)',
                    'best_calculated_selected_max_wave': 3699,
                    'best_hit_by_hit_max_wave': 3699,
                    'best_contact_envelope_max_wave': 4419,
                    'best_pre_contact_boss_kill_max_wave': 999,
                    'best_gc_pre_contact_max_wave': 999,
                    'reference_nearest_lane': 'contact_envelope',
                    'reference_nearest_lane_label': 'Contact envelope',
                    'reference_nearest_lane_wave': 4419,
                    'reference_nearest_lane_delta_vs_reference_wave': 17,
                    'delta_vs_reference_wave': 0,
                    'calculated_delta_vs_reference_wave': -703,
                    'calculated_to_reference_ratio': 3699 / 4402,
                    'pressure_factor_reference_hint': {
                        'enabled': True,
                        'boss_wave_pressure_factor': 3699 / 4402,
                        'direction': 'decrease_pressure',
                    },
                    'best_model_certification_status': 'partial_boss_contact_model',
                    'terminal_pressure_reference_status': 'empirical_reference_aligned',
                    'ids_reference_alignment': {
                        'applied': True,
                        'alignment_direction': 'raised_to_ids_reference',
                    },
                    'candidate_results': [
                        {
                            'loadout_policy_preset': 'eHP Max Waves',
                            'selected_max_wave': 3699,
                        },
                    ],
                }
            ]
        }
    )

    row = frame.to_dict('records')[0]
    assert row['Run type'] == 'Utility Dissonant Run'
    assert row['Best'] == '4402 (eHP Max Waves)'
    assert row['Calculated'] == 3699
    assert row['Hit-by-hit'] == 3699
    assert row['Contact env'] == 4419
    assert row['Pre-contact'] == 999
    assert row['GC pre-contact'] == 999
    assert row['Nearest lane'] == 'Contact envelope (4419)'
    assert row['Nearest delta'] == 17
    assert row['Reference'] == 4402
    assert row['Ref caveats'] == 'pb_age_unknown_no_source_timestamp'
    assert row['Delta'] == 0
    assert row['Calc delta'] == -703
    assert row['Calc/ref'] == 0.84
    assert row['Pressure hint'] == 0.84
    assert row['Hint direction'] == 'decrease_pressure'
    assert row['Pressure ref'] == 'empirical_reference_aligned'
    assert row['Alignment'] == 'raised_to_ids_reference'
    assert row['eHP Max Waves'] == 3699


def test_boss_wave_matrix_reference_quality_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_reference_quality_frame

    frame = _boss_wave_matrix_reference_quality_frame(
        {
            'reference_quality_summary': {
                'by_run_type': [
                    {
                        'dissonance_run_category': 'defense',
                        'label': 'Defense Dissonant Run',
                        'rows_with_reference': 7,
                        'calibration_candidate_count': 6,
                        'low_wave_reference_count': 1,
                        'pb_age_unknown_count': 7,
                        'dissonance_pb_bonus_cap_count': 2,
                        'rows_with_caveats': 7,
                    }
                ]
            }
        }
    )

    assert frame.to_dict('records') == [
        {
            'Run type': 'Defense Dissonant Run',
            'Reference rows': 7,
            'Calibration candidates': 6,
            'Below 3000': 1,
            'PB age unknown': 7,
            'PB bonus cap': 2,
            'Rows with caveats': 7,
        }
    ]


def test_boss_wave_matrix_model_blocker_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_model_blocker_frame

    frame = _boss_wave_matrix_model_blocker_frame(
        {
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification_status': 'partial_boss_contact_model',
            'certified_full_max_wave_model': False,
            'model_blocker_summary': {
                'row_count': 105,
                'rows_with_model_completion_blockers': 35,
                'model_completion_blocker_counts': {
                    'source_owned_non_boss_terminal_pressure_formulas': 35,
                },
                'rows_with_unsupported_terminal_pressures': 35,
                'unsupported_terminal_pressure_counts': {
                    'armored_enemies_blocked_hits': 35,
                    'protector_ultimate_deferred': 30,
                },
            },
        }
    )

    rows = {row['Field']: row['Value'] for row in frame.to_dict('records')}
    assert rows == {
        'Model scope': 'boss_contact_survivability',
        'Certification': 'partial_boss_contact_model',
        'Full max-wave model': 'No',
        'Certified full model': 'No',
        'Rows': '105',
        'Rows with blockers': '35',
        'Blockers': 'source_owned_non_boss_terminal_pressure_formulas: 35',
        'Unsupported pressure rows': '35',
        'Unsupported pressures': 'armored_enemies_blocked_hits: 35, protector_ultimate_deferred: 30',
    }


def test_boss_wave_matrix_model_blocker_frame_shows_reference_gaps() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_model_blocker_frame

    frame = _boss_wave_matrix_model_blocker_frame(
        {
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification_status': 'partial_boss_contact_model',
            'certified_full_max_wave_model': False,
            'model_blocker_summary': {
                'row_count': 105,
                'rows_with_model_completion_blockers': 35,
                'model_completion_blocker_counts': {
                    'source_owned_non_boss_terminal_pressure_formulas': 35,
                },
                'rows_with_unsupported_terminal_pressures': 35,
                'unsupported_terminal_pressure_counts': {},
            },
            'reference_gap_summary': {
                'missing_reference_blocked_count': 19,
                'ordinary_missing_reference_blocked_count': 1,
                'dissonance_pb_cap_omitted_reference_count': 18,
                'by_reference_kind': {
                    'ids_dissonant_pb_wave': 18,
                    'ids_milestone_wave': 1,
                },
            },
        }
    )

    rows = {row['Field']: row['Value'] for row in frame.to_dict('records')}
    assert rows['Missing reference rows'] == '19'
    assert rows['Cap-omitted Disco PB rows'] == '18'
    assert rows['Ordinary missing reference rows'] == '1'
    assert rows['Missing reference kinds'] == 'ids_dissonant_pb_wave: 18, ids_milestone_wave: 1'


def test_boss_wave_matrix_model_blocker_frame_shows_terminal_closure_inputs() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_model_blocker_frame

    frame = _boss_wave_matrix_model_blocker_frame(
        {
            'model_scope': 'boss_contact_survivability',
            'not_full_max_wave_model': True,
            'model_certification_status': 'partial_boss_contact_model',
            'certified_full_max_wave_model': False,
            'model_blocker_summary': {
                'row_count': 105,
                'rows_with_model_completion_blockers': 35,
                'model_completion_blocker_counts': {
                    'source_owned_non_boss_terminal_pressure_formulas': 35,
                },
                'rows_with_unsupported_terminal_pressures': 35,
                'unsupported_terminal_pressure_counts': {},
            },
            'terminal_pressure_runtime_override_status': {
                'closed': False,
                'mode': 'active_unsupported_pressure_inputs',
                'required_fields': [
                    'armored_terminal_max_wave',
                    'fleet_terminal_max_wave',
                    'protector_terminal_max_wave',
                ],
                'missing_fields': [
                    'armored_terminal_max_wave',
                    'fleet_terminal_max_wave',
                ],
                'required_fields_by_pressure': {},
                'missing_fields_by_pressure': {},
                'unmapped_pressures': ['new_terminal_pressure'],
            },
            'non_boss_terminal_pressure_closure': {
                'closed': False,
                'mode': 'missing',
                'exact_terminal_override_closed': False,
                'pressure_factor_approximation_closed': False,
                'boss_wave_pressure_factor': None,
            },
        }
    )

    rows = {row['Field']: row['Value'] for row in frame.to_dict('records')}
    assert rows['Terminal closure mode'] == 'missing'
    assert rows['Terminal closure closed'] == 'No'
    assert rows['Required terminal inputs'] == (
        'armored_terminal_max_wave, fleet_terminal_max_wave, protector_terminal_max_wave'
    )
    assert rows['Missing terminal inputs'] == 'armored_terminal_max_wave, fleet_terminal_max_wave'
    assert rows['Unmapped terminal pressures'] == 'new_terminal_pressure'


def test_boss_wave_matrix_model_accuracy_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_model_accuracy_frame

    frame = _boss_wave_matrix_model_accuracy_frame(
        {
            'model_accuracy_summary': {
                'status': 'default_partial_comparison_calibration_available',
                'model_closure_status': 'partial_missing_required_model_inputs',
                'model_certification_status': 'partial_boss_contact_model',
                'certified_full_max_wave_model': False,
                'model_completion_blockers': ['source_owned_non_boss_terminal_pressure_formulas'],
                'rows_with_model_completion_blockers': 35,
                'comparison_only_pressure_factor_inputs': {
                    'boss_wave_pressure_factor': 2.606384292771721,
                },
                'non_boss_pressure_driver_model': {
                    'status': 'source_driver_curves_partially_available_terminal_transform_missing',
                    'pressure_factor_policy': (
                        'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved'
                    ),
                    'source_backed_curve_coverage': {
                        'elite_spawn_curve_by_tier_and_wave': True,
                        'fleet_related_enemy_group_count_range': True,
                        'fleet_spawn_curve_by_tier_and_wave': True,
                        'normal_spawn_rate_curve_by_wave_and_wave_accelerator': True,
                        'normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase': False,
                    },
                    'missing_source_owned_formula_links': [
                        'enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight',
                        'normal_spawn_rate_value_to_terminal_pressure',
                    ],
                    'empirical_calibration_policy': {
                        'below_3000_wave_policy': 'reported_as_caveated_sensitivity_not_clean_calibration',
                        'dissonance_pb_5000_cap_policy': 'excluded_from_calibration_lower_bound_only',
                    },
                },
                'reference_row_count': 76,
                'calibration_candidate_count': 23,
                'missing_reference_blocked_count': 19,
                'reference_caveat_counts': {
                    'below_3000_wave_perk_volatility': 11,
                    'pb_age_unknown_no_source_timestamp': 56,
                    'dissonance_pb_5000_bonus_cap_floor': 42,
                },
                'rows_with_reference_caveats': 60,
                'operator_next_step': 'apply_comparison_only_pressure_factor_input_to_review_approximation',
            }
        }
    )

    rows = {row['Field']: row['Value'] for row in frame.to_dict('records')}
    assert rows == {
        'Accuracy status': 'default_partial_comparison_calibration_available',
        'Model closure': 'partial_missing_required_model_inputs',
        'Certification': 'partial_boss_contact_model',
        'Certified full model': 'No',
        'Model blockers': 'source_owned_non_boss_terminal_pressure_formulas',
        'Rows with blockers': '35',
        'Comparison pressure input': '{"boss_wave_pressure_factor": 2.606384292771721}',
        'Pressure driver status': 'source_driver_curves_partially_available_terminal_transform_missing',
        'Pressure driver policy': (
            'manual_or_comparison_only_until_terminal_transform_source_owned_or_empirically_approved'
        ),
        'Pressure source coverage': (
            '{"elite_spawn_curve_by_tier_and_wave": true, '
            '"fleet_related_enemy_group_count_range": true, '
            '"fleet_spawn_curve_by_tier_and_wave": true, '
            '"normal_enemy_spawn_count_curve_by_tier_wave_and_spawn_phase": false, '
            '"normal_spawn_rate_curve_by_wave_and_wave_accelerator": true}'
        ),
        'Pressure formula gaps': (
            'enemy_balance_spawn_multiplier_to_normal_spawn_pressure_weight, '
            'normal_spawn_rate_value_to_terminal_pressure'
        ),
        'Pressure calibration policy': (
            '{"below_3000_wave_policy": "reported_as_caveated_sensitivity_not_clean_calibration", '
            '"dissonance_pb_5000_cap_policy": "excluded_from_calibration_lower_bound_only"}'
        ),
        'Reference rows': '76',
        'Calibration candidates': '23',
        'Missing references': '19',
        'Reference caveats': (
            'below_3000_wave_perk_volatility: 11, '
            'dissonance_pb_5000_bonus_cap_floor: 42, '
            'pb_age_unknown_no_source_timestamp: 56'
        ),
        'Rows with caveats': '60',
        'Next step': 'apply_comparison_only_pressure_factor_input_to_review_approximation',
    }


def test_boss_wave_matrix_terminal_pressure_requirement_frame_maps_pressures_to_inputs() -> None:
    from app.streamlit_inspector import (
        _boss_wave_matrix_terminal_pressure_requirement_frame,
        _boss_wave_terminal_pressure_requirement_frame_from_status,
    )

    terminal_status = {
        'required_fields_by_pressure': {
            'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            'protector_ultimate_deferred': ['protector_terminal_max_wave'],
            'fast_ultimate_deferred': ['fleet_terminal_max_wave'],
        },
        'missing_fields_by_pressure': {
            'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            'fast_ultimate_deferred': [],
        },
        'unmapped_pressures': ['new_terminal_pressure'],
    }

    frame = _boss_wave_matrix_terminal_pressure_requirement_frame(
        {
            'terminal_pressure_runtime_override_status': terminal_status,
        }
    )
    selected_frame = _boss_wave_terminal_pressure_requirement_frame_from_status(terminal_status)

    assert selected_frame.to_dict('records') == frame.to_dict('records')

    rows = {row['Pressure']: row for row in selected_frame.to_dict('records')}
    assert rows == {
        'armored_enemies_blocked_hits': {
            'Pressure': 'armored_enemies_blocked_hits',
            'Mapped': 'Yes',
            'Required inputs': 'armored_terminal_max_wave',
            'Missing inputs': 'armored_terminal_max_wave',
        },
        'fast_ultimate_deferred': {
            'Pressure': 'fast_ultimate_deferred',
            'Mapped': 'Yes',
            'Required inputs': 'fleet_terminal_max_wave',
            'Missing inputs': '',
        },
        'new_terminal_pressure': {
            'Pressure': 'new_terminal_pressure',
            'Mapped': 'No',
            'Required inputs': '',
            'Missing inputs': '',
        },
        'protector_ultimate_deferred': {
            'Pressure': 'protector_ultimate_deferred',
            'Mapped': 'Yes',
            'Required inputs': 'protector_terminal_max_wave',
            'Missing inputs': '',
        },
    }


def test_boss_wave_selected_terminal_pressure_requirement_frame_maps_pressures_to_inputs() -> None:
    from app.streamlit_inspector import _boss_wave_terminal_pressure_requirement_frame_from_status

    frame = _boss_wave_terminal_pressure_requirement_frame_from_status(
        {
            'required_fields_by_pressure': {
                'knockback_resistance_non_boss_pressure': ['fleet_terminal_max_wave'],
                'armored_enemies_blocked_hits': ['armored_terminal_max_wave'],
            },
            'missing_fields_by_pressure': {
                'knockback_resistance_non_boss_pressure': ['fleet_terminal_max_wave'],
                'armored_enemies_blocked_hits': [],
            },
        }
    )

    rows = {row['Pressure']: row for row in frame.to_dict('records')}
    assert rows == {
        'armored_enemies_blocked_hits': {
            'Pressure': 'armored_enemies_blocked_hits',
            'Mapped': 'Yes',
            'Required inputs': 'armored_terminal_max_wave',
            'Missing inputs': '',
        },
        'knockback_resistance_non_boss_pressure': {
            'Pressure': 'knockback_resistance_non_boss_pressure',
            'Mapped': 'Yes',
            'Required inputs': 'fleet_terminal_max_wave',
            'Missing inputs': 'fleet_terminal_max_wave',
        },
    }


def test_boss_wave_matrix_reference_gap_frame_uses_published_rows() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_reference_gap_frame

    frame = _boss_wave_matrix_reference_gap_frame(
        {
            'reference_gap_summary': {
                'missing_references': [
                    {
                        'tier': 16,
                        'tier_column': 'Tier 16',
                        'dissonance_run_category': 'utility',
                        'label': 'Utility Dissonant Run',
                        'reference_kind': 'ids_dissonant_pb_wave',
                        'reference_wave': None,
                        'reference_raw_wave': 0,
                        'reference_gap_reason': 'zero_reference_wave',
                        'dissonance_pb_cap_omitted_reference': True,
                        'dissonance_pb_cap_omission_context': {
                            'applies': True,
                            'mode': 'zero_ids_dissonant_pb_after_bonus_cap_reached',
                            'evidence_source': 'account_state.dissonance_pbs_by_tier',
                        },
                        'best_calculated_selected_max_wave': 0,
                        'unsupported_pressure_uncapped_selected_max_wave': 1477,
                        'unsupported_terminal_pressures': [
                            'armored_enemies_blocked_hits',
                            'protector_ultimate_deferred',
                        ],
                        'terminal_pressure_required_fields': [
                            'armored_terminal_max_wave',
                            'protector_terminal_max_wave',
                        ],
                        'terminal_pressure_missing_fields': [
                            'armored_terminal_max_wave',
                            'protector_terminal_max_wave',
                        ],
                    }
                ]
            }
        }
    )

    assert frame.to_dict('records') == [
        {
            'Tier': 'Tier 16',
            'Run type': 'Utility Dissonant Run',
            'Reference kind': 'ids_dissonant_pb_wave',
            'Reference': 0,
            'Reason': 'zero_reference_wave',
            'Cap omission': 'Yes',
            'Cap evidence': 'account_state.dissonance_pbs_by_tier',
            'Calculated': 0,
            'Uncapped': 1477,
            'Unsupported': 'armored_enemies_blocked_hits, protector_ultimate_deferred',
            'Required inputs': 'armored_terminal_max_wave, protector_terminal_max_wave',
            'Missing inputs': 'armored_terminal_max_wave, protector_terminal_max_wave',
        }
    ]


def test_boss_wave_matrix_alignment_summary_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_alignment_summary_frame

    frame = _boss_wave_matrix_alignment_summary_frame(
        {
            'reference_alignment_summary': {
                'by_run_type': [
                    {
                        'dissonance_run_category': 'utility',
                        'label': 'Utility Dissonant Run',
                        'row_count': 21,
                        'ids_reference_alignment_applied_count': 12,
                        'raw_delta_over_reference_count': 13,
                        'raw_delta_under_reference_count': 1,
                        'raw_delta_match_count': 1,
                        'reference_nearest_lane_counts': {'contact_envelope': 19, 'hit_by_hit': 2},
                        'max_abs_calculated_delta_wave': 15710,
                    }
                ],
                'calibration_reference_alignment': {
                    'by_run_type': [
                        {
                            'dissonance_run_category': 'utility',
                            'label': 'Utility Dissonant Run',
                            'rows_with_reference': 5,
                            'raw_delta_over_reference_count': 4,
                            'raw_delta_under_reference_count': 0,
                            'raw_delta_match_count': 1,
                            'max_abs_calculated_delta_wave': 1200,
                        }
                    ],
                    'excluded_by_run_type': [
                        {
                            'dissonance_run_category': 'utility',
                            'label': 'Utility Dissonant Run',
                            'excluded_from_calibration_reference_count': 8,
                        }
                    ],
                },
            }
        }
    )

    row = frame.to_dict('records')[0]
    assert row == {
        'Run type': 'Utility Dissonant Run',
        'Rows': 21,
        'Aligned': 12,
        'Raw over': 13,
        'Raw under': 1,
        'Raw match': 1,
        'Nearest lanes': 'contact_envelope: 19, hit_by_hit: 2',
        'Worst raw delta': 15710,
        'Calibration refs': 5,
        'Calibration over': 4,
        'Calibration under': 0,
        'Calibration match': 1,
        'Excluded refs': 8,
        'Calibration worst delta': 1200,
    }


def test_boss_wave_matrix_comparison_alignment_summary_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_comparison_alignment_summary_frame

    frame = _boss_wave_matrix_comparison_alignment_summary_frame(
        {
            'comparison': {
                'label': 'pressure_factor_assumptions',
                'matrix': {
                    'reference_alignment_summary': {
                        'by_run_type': [
                            {
                                'dissonance_run_category': 'utility',
                                'label': 'Utility Dissonant Run',
                                'row_count': 1,
                                'ids_reference_alignment_applied_count': 1,
                                'raw_delta_over_reference_count': 0,
                                'raw_delta_under_reference_count': 1,
                                'raw_delta_match_count': 0,
                                'reference_nearest_lane_counts': {'contact_envelope': 1},
                                'max_abs_calculated_delta_wave': 793,
                            }
                        ],
                        'calibration_reference_alignment': {
                            'by_run_type': [
                                {
                                    'dissonance_run_category': 'utility',
                                    'label': 'Utility Dissonant Run',
                                    'rows_with_reference': 1,
                                    'raw_delta_over_reference_count': 0,
                                    'raw_delta_under_reference_count': 0,
                                    'raw_delta_match_count': 1,
                                    'max_abs_calculated_delta_wave': 0,
                                }
                            ],
                            'excluded_by_run_type': [
                                {
                                    'dissonance_run_category': 'utility',
                                    'label': 'Utility Dissonant Run',
                                    'excluded_from_calibration_reference_count': 0,
                                }
                            ],
                        },
                    }
                },
            }
        }
    )

    row = frame.to_dict('records')[0]
    assert row == {
        'Scenario': 'pressure_factor_assumptions',
        'Run type': 'Utility Dissonant Run',
        'Rows': 1,
        'Aligned': 1,
        'Raw over': 0,
        'Raw under': 1,
        'Raw match': 0,
        'Nearest lanes': 'contact_envelope: 1',
        'Worst raw delta': 793,
        'Calibration refs': 1,
        'Calibration over': 0,
        'Calibration under': 0,
        'Calibration match': 1,
        'Excluded refs': 0,
        'Calibration worst delta': 0,
    }


def test_boss_wave_matrix_comparison_calculated_delta_summary_frame_uses_published_summary() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_comparison_calculated_delta_summary_frame

    frame = _boss_wave_matrix_comparison_calculated_delta_summary_frame(
        {
            'comparison': {
                'label': 'pressure_factor_assumptions',
                'calculated_delta_summary': {
                    'by_run_type': [
                        {
                            'dissonance_run_category': 'utility',
                            'label': 'Utility Dissonant Run',
                            'row_count': 1,
                            'comparison_raw_wave_higher_count': 0,
                            'comparison_raw_wave_lower_count': 1,
                            'comparison_raw_wave_match_count': 0,
                            'max_abs_calculated_delta_wave': 90,
                        }
                    ]
                },
            }
        }
    )

    row = frame.to_dict('records')[0]
    assert row == {
        'Scenario': 'pressure_factor_assumptions',
        'Run type': 'Utility Dissonant Run',
        'Rows': 1,
        'Raw higher': 0,
        'Raw lower': 1,
        'Raw match': 0,
        'Worst raw move': 90,
    }


def test_boss_wave_matrix_comparison_frame_uses_published_rows() -> None:
    from app.streamlit_inspector import _boss_wave_matrix_comparison_frame

    frame = _boss_wave_matrix_comparison_frame(
        {
            'dissonance_run_categories': ['none', 'utility'],
            'comparison': {
                'label': 'pressure_factor_assumptions',
                'wide_rows': [
                    {
                        'tier': 14,
                        'tier_column': 'Tier 14',
                        'regular_default_display': '5761 (eHP Max Waves)',
                        'regular_comparison_display': '5311 (eHP Max Waves)',
                        'regular_delta_wave': -450,
                        'utility_default_display': '4402 (eHP Max Waves)',
                        'utility_comparison_display': '4402 (eHP Max Waves)',
                        'utility_delta_wave': 0,
                        'utility_default_calculated_wave': 3699,
                        'utility_comparison_calculated_wave': 3609,
                        'utility_calculated_delta_wave': -90,
                        'utility_default_calculated_delta_vs_reference_wave': -703,
                        'utility_comparison_calculated_delta_vs_reference_wave': -793,
                        'utility_default_calculated_to_reference_ratio': 0.840299863698319,
                        'utility_comparison_calculated_to_reference_ratio': 0.819854611540209,
                        'utility_default_pressure_factor_hint': 0.840299863698319,
                        'utility_comparison_pressure_factor_hint': 0.819854611540209,
                        'utility_default_pressure_factor_hint_direction': 'decrease_pressure',
                        'utility_comparison_pressure_factor_hint_direction': 'decrease_pressure',
                        'utility_default_unsupported_pressure_reference_alignment_direction': 'raised_to_ids_reference',
                        'utility_comparison_unsupported_pressure_reference_alignment_direction': 'raised_to_ids_reference',
                    }
                ],
            },
        }
    )

    rows = frame.to_dict('records')
    assert rows == [
        {
            'Scenario': 'pressure_factor_assumptions',
            'Tier': 'Tier 14',
            'Run type': 'Regular',
            'Default': '5761 (eHP Max Waves)',
            'Comparison': '5311 (eHP Max Waves)',
            'Delta': -450,
            'Default calc': '',
            'Comparison calc': '',
            'Calc delta': '',
            'Default calc delta': '',
            'Comparison calc delta': '',
            'Default calc/ref': '',
            'Comparison calc/ref': '',
            'Default pressure hint': '',
            'Comparison pressure hint': '',
            'Default hint direction': '',
            'Comparison hint direction': '',
            'Default limiter': '',
            'Comparison limiter': '',
            'Default pressure ref': '',
            'Comparison pressure ref': '',
            'Default alignment': '',
            'Comparison alignment': '',
            'Default uncapped': '',
            'Comparison uncapped': '',
        },
        {
            'Scenario': 'pressure_factor_assumptions',
            'Tier': 'Tier 14',
            'Run type': 'Utility Dissonant Run',
            'Default': '4402 (eHP Max Waves)',
            'Comparison': '4402 (eHP Max Waves)',
            'Delta': 0,
            'Default calc': '3699',
            'Comparison calc': '3609',
            'Calc delta': '-90',
            'Default calc delta': '-703',
            'Comparison calc delta': '-793',
            'Default calc/ref': '0.84',
            'Comparison calc/ref': '0.82',
            'Default pressure hint': '0.84',
            'Comparison pressure hint': '0.82',
            'Default hint direction': 'decrease_pressure',
            'Comparison hint direction': 'decrease_pressure',
            'Default limiter': '',
            'Comparison limiter': '',
            'Default pressure ref': '',
            'Comparison pressure ref': '',
            'Default alignment': 'raised_to_ids_reference',
            'Comparison alignment': 'raised_to_ids_reference',
            'Default uncapped': '',
            'Comparison uncapped': '',
        },
    ]


def test_boss_waves_renderer_payload_contract_fails_closed_without_selected_rows() -> None:
    from app.streamlit_inspector import _require_boss_wave_payload_rows

    assert _require_boss_wave_payload_rows({'operator_rows': []}, 'operator_rows') == []
    with pytest.raises(ValueError, match="operator_rows"):
        _require_boss_wave_payload_rows({'rows': [{'display_wave': 9}]}, 'operator_rows')
    with pytest.raises(ValueError, match="download_rows"):
        _require_boss_wave_payload_rows({'download_rows': {'display_wave': 9}}, 'download_rows')
    with pytest.raises(ValueError, match="download_rows"):
        _require_boss_wave_payload_rows({'download_rows': [object()]}, 'download_rows')


def test_inputs_dashboard_production_render_avoids_native_streamlit_tables() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("dashboard = active_artifacts.get('input_dashboard.json') or {}")
    end = text.index("with st.expander('Input lineage and artifact evidence'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


def test_input_lineage_debug_table_uses_arrow_safe_display_frame() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("st.subheader('Input lineage')")
    end = text.index("\ndef _require_boss_wave_payload_rows", start)
    lineage_block = text[start:end]

    assert "input_lineage_rows_frame(" in lineage_block
    assert "_arrow_safe_frame(lineage_frame, columns=('source_value', 'resolved_value'))" in lineage_block


def test_inputs_dashboard_cards_panel_uses_published_rows_without_account_state_mutation() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("elif panel_type == 'cards_inventory_and_preset':")
    end = text.index("elif panel_type == 'track_table':", start)
    cards_block = text[start:end]
    assert "payload.get('preset_rows_by_preset')" in cards_block
    assert "preset_rows_by_preset.get(selected_preset)" in cards_block
    assert "active_artifacts.get('account_state.json'" not in cards_block
    assert "st.error(" in cards_block


def test_stats_dashboard_production_render_avoids_native_streamlit_tables() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    start = text.index("dashboard = active_artifacts.get('stats_dashboard.json') or {}")
    end = text.index("with st.expander('Stats evidence and verification'", start)
    production_block = text[start:end]
    assert 'st.table(' not in production_block
    assert 'st.dataframe(' not in production_block
    assert 'st.data_editor(' not in production_block


def test_stats_dashboard_production_render_demotes_secondary_panels_and_guards_debug_failures() -> None:
    text = (ROOT / 'app' / 'streamlit_inspector.py').read_text(encoding='utf-8')
    assert "Detailed QE rows and secondary context" in text
    assert "dashboard.get('secondary_panels')" in text
    assert "secondary_variants" in text
    assert "requested_preset = str(request.preset or '').strip()" in text
    assert "render_grouped_modules_html(payload)" in text
    assert "compare_df[['surface_id', 'ep_value', 'ep_value_raw', 'compare_preset', 'compare_perk_state', 'status', 'label']]" not in text
    assert "_render_stats_debug_tools(active_artifacts, comparison_artifacts, request)" in text
    assert "Stats evidence tools unavailable for this snapshot" in text
    for stale_label in (
        'Dashboard artifact debug (stats_dashboard.json)',
        'Dashboard artifact debug (input_dashboard.json)',
        'Stats debug and verification',
        'Legacy input debug views',
        'Raw artifacts',
    ):
        assert stale_label not in text


def test_load_streamlit_reference_data_uses_request_ids_path(monkeypatch, tmp_path):
    from app import pipeline as pipeline_mod

    captured: dict[str, object] = {}

    class _Bundle:
        perk_policy = {}

    def _fake_load_inputs(*, ids_path, manual_inputs_path):
        captured['ids_path'] = ids_path
        captured['manual_inputs_path'] = manual_inputs_path
        return _Bundle()

    monkeypatch.setattr(pipeline_mod, 'load_inputs', _fake_load_inputs)
    monkeypatch.setattr(pipeline_mod, 'load_perk_entities', lambda: {})

    ids_path = tmp_path / 'custom_ids.csv'
    ids_path.write_text('h1,h2\n', encoding='utf-8')
    manual_path = tmp_path / 'manual.yaml'
    manual_path.write_text('perk_policy: {}\n', encoding='utf-8')

    payload = pipeline_mod.load_streamlit_reference_data(ids_path=ids_path, manual_inputs_path=manual_path)

    assert captured['ids_path'] == ids_path
    assert captured['manual_inputs_path'] == manual_path
    assert isinstance(payload, dict)


def test_load_streamlit_reference_data_exposes_module_lookup_contract():
    from app.pipeline import load_streamlit_reference_data

    payload = load_streamlit_reference_data(
        ids_path=ROOT / 'input' / 'imports' / 'ids.csv',
        manual_inputs_path=None,
    )

    module_lookup = payload.get('module_substat_lookup')
    assert isinstance(module_lookup, dict)
    assert ('armor', 'Knockback Force') in module_lookup
    rows = module_lookup[('armor', 'Knockback Force')]
    assert isinstance(rows, list)
    assert rows
    assert {'rarity', 'unit', 'value'}.issubset(rows[0].keys())


def test_default_verification_matrix_requests_returns_expected_pairs(tmp_path):
    from app.pipeline import PipelineRunRequest, _default_verification_matrix_requests

    requests = _default_verification_matrix_requests(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'matrix',
        )
    )

    assert len(requests) == 4
    assert [(request.preset, request.state_mode) for request in requests] == [
        ('Farming', 'start_of_run'),
        ('Farming', 'max_progression'),
        ('Tourney', 'start_of_run'),
        ('Tourney', 'max_progression'),
    ]
    assert [request.perk_state for request in requests] == ['auto', 'auto', 'off', 'off']


def test_build_verification_snapshot_set_orchestrates_execution(monkeypatch, tmp_path):
    from app.models import PipelineRunResult, PipelineTrace
    from app.pipeline import PipelineRunRequest, build_verification_snapshot_set, _default_verification_matrix_requests

    captured_requests = []

    def _fake_execute_pipeline(request):
        captured_requests.append(request)
        return PipelineRunResult(
            exit_code=0,
            request=request,
            out_dir=request.out,
            diagnostics={},
            generated_files=(),
            pipeline_trace=PipelineTrace(request={}, execution_path={}, stages=[], artifacts_written=[]),
        )

    import app.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, 'execute_pipeline', _fake_execute_pipeline)
    base_request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'matrix',
    )
    expected_requests = _default_verification_matrix_requests(base_request)

    results = build_verification_snapshot_set(base_request)

    assert len(results) == len(expected_requests)
    assert captured_requests == list(expected_requests)
    assert [result.request for result in results] == list(expected_requests)


def test_resolve_fast_checkpoint_returns_requested_surfaces():
    from app.pipeline import FastCheckpointRequest, resolve_fast_checkpoint

    result = resolve_fast_checkpoint(
        FastCheckpointRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            preset='Farming',
            state_mode='start_of_run',
            requested_surface_ids=('state::tower.hp', 'state::wall.hp'),
        )
    )

    rows = result.statbook.get('rows') or {}
    assert result.diagnostics['resolver_kind'] == 'simulator_checkpoint_qe_light'
    assert set(rows) == {'state::tower.hp', 'state::wall.hp'}

