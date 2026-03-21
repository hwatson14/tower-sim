from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from engine.boss_wave_engine import BossWaveEngine, BossWaveEngineConfig, ProgressionFixedInputs
from engine.progression_state import build_progression_init_state
from parsers.ids_parser import parse_ids

def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def test_enemy_table_lookup_interpolates_sparse_rows():
    engine = BossWaveEngine()
    table = {
        10: {'Tier 12': 100.0},
        20: {'Tier 12': 200.0},
    }
    assert engine._lookup_wave_value(table, 15, 'Tier 12') == 150.0
    assert engine._lookup_wave_value(table, 5, 'Tier 12') == 100.0
    assert engine._lookup_wave_value(table, 25, 'Tier 12') == 200.0


def test_run_many_groups_configs_by_progression_signature():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    calls = {'count': 0}
    original = engine._build_progression_snapshots

    def wrapped_build_progression_snapshots(*, account_state, init_state, config, fixed_inputs):
        calls['count'] += 1
        return original(account_state=account_state, init_state=init_state, config=config, fixed_inputs=fixed_inputs)

    engine._build_progression_snapshots = wrapped_build_progression_snapshots
    batch = engine.run_many(
        account_state=state,
        init_state=init,
        configs=[
            BossWaveEngineConfig(preset_name='Farming', mode_id='farming', tier_column='Tier 12', start_boss_wave=10, end_boss_wave=10),
            BossWaveEngineConfig(preset_name='Farming', mode_id='farming', tier_column='Tier 13', start_boss_wave=10, end_boss_wave=10),
        ],
    )
    assert calls['count'] == 1
    assert batch.diagnostics['grouped_progression_execution'] is True
    assert len(batch.runs) == 2


def test_boss_wave_engine_uses_no_warmup_skip_in_live_run():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            enemy_skip_warmup_waves=1000,
        ),
    )
    row = result.rows[0]
    assert 'no warmup' in ' '.join(row.notes).lower()


def test_run_many_splits_groups_when_skip_reduction_differs():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    calls = {'count': 0}
    original = engine._build_progression_snapshots

    def wrapped_build_progression_snapshots(*, account_state, init_state, config, fixed_inputs):
        calls['count'] += 1
        return original(account_state=account_state, init_state=init_state, config=config, fixed_inputs=fixed_inputs)

    engine._build_progression_snapshots = wrapped_build_progression_snapshots
    batch = engine.run_many(
        account_state=state,
        init_state=init,
        configs=[
            BossWaveEngineConfig(
                preset_name='Farming',
                mode_id='farming',
                tier_column='Tier 12',
                start_boss_wave=10,
                end_boss_wave=10,
                scenario_runtime_inputs={'enemy_level_skip_reduction_pp': 0.0},
            ),
            BossWaveEngineConfig(
                preset_name='Farming',
                mode_id='farming',
                tier_column='Tier 13',
                start_boss_wave=10,
                end_boss_wave=10,
                scenario_runtime_inputs={'enemy_level_skip_reduction_pp': 2.5},
            ),
        ],
    )
    assert calls['count'] == 2
    assert len(batch.runs) == 2


def test_run_honours_scenario_owned_boss_cadence_interval():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=20,
            boss_wave_step=10,
            scenario_runtime_inputs={'boss_wave_interval': 5},
        ),
    )
    assert [row.boss_wave for row in result.rows] == [10, 15, 20]
    assert result.diagnostics['boss_wave_interval_used'] == 5


def test_build_progression_snapshots_avoids_full_recompute_when_state_is_unchanged():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    calls = {'count': 0}

    class _FakeRecalc:
        def __init__(self):
            self.statbook = type('StatBook', (), {'rows': {
                'canonical_stat::free_attack_upgrade_chance_pct': type('Row', (), {'final_value': 0.0})(),
                'canonical_stat::free_defense_upgrade_chance_pct': type('Row', (), {'final_value': 0.0})(),
                'canonical_stat::free_utility_upgrade_chance_pct': type('Row', (), {'final_value': 0.0})(),
                'canonical_stat::enemy_attack_level_skip_pct': type('Row', (), {'final_value': 0.0})(),
                'canonical_stat::enemy_health_level_skip_pct': type('Row', (), {'final_value': 0.0})(),
                'capability::capability.uw.black_hole.disable_ranged': type('Row', (), {'final_value': 0.0})(),
            }})

    def fake_recompute_row_map(*, account_state, config, workshop_levels_current, perk_counts):
        calls['count'] += 1
        return _FakeRecalc()

    engine._recompute_row_map = fake_recompute_row_map
    snapshots = engine._build_progression_snapshots(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=5,
            perks_enabled=False,
        ),
        fixed_inputs=ProgressionFixedInputs(boss_wave_interval=10, enemy_level_skip_reduction_pp=0.0),
    )
    assert len(snapshots) == 5
    assert calls['count'] == 1
