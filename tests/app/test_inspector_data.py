from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_load_artifacts_tolerates_missing_optional_reports(tmp_path):
    from app.inspector_data import load_artifacts

    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    for name, payload in {
        'pipeline_trace.json': {'stages': [], 'execution_path': {}},
        'diagnostics.json': {'default_preset': 'Farming'},
        'account_state.json': {'card_presets': {}},
        'statbook.json': {'rows': {}, 'diagnostics': {}},
        'statbook_publishable.json': {'rows': {}, 'diagnostics': {}},
        'run_stats.json': {'presets': {}},
        'statbook_start_of_run.json': {'rows': {}},
        'statbook_max_progression.json': {'rows': {}},
        'state_matrix.json': {},
        'ep_oracle_compare.json': {},
        'line_by_line_verification.json': {},
        'audit_surface_manifest.json': {},
        'family_completeness_matrix.json': {},
    }.items():
        (out_dir / name).write_text(json.dumps(payload), encoding='utf-8')

    artifacts = load_artifacts(out_dir)
    assert artifacts.get('diagnostics.json', {})['default_preset'] == 'Farming'
    assert artifacts.get('tower_regen_closure_report.json', {}) == {}


def test_statbook_rows_frame_groups_mixed_surface_ids():
    from app.inspector_data import statbook_rows_frame

    frame = statbook_rows_frame(
        {
            'rows': {
                'state::tower.hp': {'final_value': 100, 'display_value': '100', 'value_type': 'scalar', 'status': 'resolved', 'contributors': []},
                'mechanic_param::uw.black_hole.cooldown_seconds': {'final_value': 50, 'display_value': '50', 'value_type': 'seconds', 'status': 'resolved', 'contributors': []},
                'environment_param::enemy.boss.damage_multiplier': {'final_value': 2, 'display_value': 'x2', 'value_type': 'multiplier', 'status': 'resolved', 'contributors': []},
            }
        }
    )
    groups = set(frame['group'].tolist())
    assert 'Tower' in groups
    assert 'Ultimate Weapons' in groups
    assert 'Context' in groups
    assert 'raw_surface_id' in frame.columns
    uw_row = frame.loc[frame['raw_surface_id'] == 'mechanic_param::uw.black_hole.cooldown_seconds'].iloc[0]
    assert uw_row['surface_id'] == 'state::uw.black_hole.cooldown_seconds'


def test_run_stats_rows_frame_preserves_all_stats_and_normalizes_ids():
    from app.inspector_data import run_stats_rows_frame

    frame = run_stats_rows_frame(
        {
            'presets': {
                'Farming': {
                    'stats': {
                        'rows': {
                            'canonical_stat::tower_damage': {
                                'changed_in_max_progression': True,
                                'start_of_run': {'final_value': 10, 'display_value': '10', 'value_type': 'scalar', 'status': 'resolved'},
                                'max_progression': {'final_value': 20, 'display_value': '20', 'value_type': 'scalar', 'status': 'resolved'},
                            }
                        }
                    }
                }
            }
        },
        preset='Farming',
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row['raw_surface_id'] == 'canonical_stat::tower_damage'
    assert row['surface_id'] == 'state::tower.damage'
    assert row['start_of_run_value'] == 10
    assert row['max_progression_value'] == 20
