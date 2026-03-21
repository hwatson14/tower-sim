from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
import engine.boss_wave_engine as boss_wave_engine_module
from engine.boss_wave_engine import BossWaveEngine, BossWaveEngineConfig
from engine.perk_timeline_state import PerkTimelineEvent
from engine.progression_recalc_bridge import ProgressionRecalcResult
from engine.progression_state import build_progression_init_state
from engine.scenario_engine import ScenarioConfig, compute_scenario_surfaces
from engine.workshop_progression_policy import WorkshopUpgradeEvent
from models.statbook import StatBook, StatRow
from parsers.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.slow


def _build_state():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    return compile_account_state(ids_raw, default_preset='Farming')


def test_boss_wave_engine_resolves_progression_bundle_values_from_declared_bounded_bundles(monkeypatch):
    calls = []

    def _fake_bundle(**kwargs):
        calls.append((kwargs['consumer_id'], kwargs['bundle_id'], kwargs['family_id']))
        if kwargs['bundle_id'] == 'progression_free_upgrades':
            rows = (
                SimpleNamespace(surface_id='canonical_stat::free_attack_upgrade_chance_pct', final_value=101.0),
                SimpleNamespace(surface_id='canonical_stat::free_defense_upgrade_chance_pct', final_value=102.0),
                SimpleNamespace(surface_id='canonical_stat::free_utility_upgrade_chance_pct', final_value=103.0),
            )
        else:
            rows = (
                SimpleNamespace(surface_id='canonical_stat::enemy_attack_level_skip_pct', final_value=11.0),
                SimpleNamespace(surface_id='canonical_stat::enemy_health_level_skip_pct', final_value=12.0),
            )
        return SimpleNamespace(resolved_surface_rows=rows)

    monkeypatch.setattr(boss_wave_engine_module, 'resolve_progression_consumer_bundle', _fake_bundle)

    values = BossWaveEngine._resolve_progression_bundle_values(
        patched_account_state=_build_state(),
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            perks_enabled=True,
            perk_preset_name='Farming',
            card_preset_name='Farming',
            module_preset_name='Farming',
        ),
    )

    assert calls == [
        ('progression_runtime', 'progression_free_upgrades', 'progression_runtime_with_perks'),
        ('progression_runtime', 'progression_wave_skips', 'progression_runtime_with_perks'),
    ]
    assert values == {
        'canonical_stat::free_attack_upgrade_chance_pct': 101.0,
        'canonical_stat::free_defense_upgrade_chance_pct': 102.0,
        'canonical_stat::free_utility_upgrade_chance_pct': 103.0,
        'canonical_stat::enemy_attack_level_skip_pct': 11.0,
        'canonical_stat::enemy_health_level_skip_pct': 12.0,
    }


def test_boss_wave_engine_resolves_progression_family_values_from_bounded_query_helper(monkeypatch):
    seen_family_ids = []

    def _fake_family_query(**kwargs):
        seen_family_ids.append(kwargs['family_id'])
        rows = (
            SimpleNamespace(surface_id='canonical_stat::wall_hp', final_value=1000.0),
            SimpleNamespace(surface_id='canonical_stat::wall_regen', final_value=25.0),
            SimpleNamespace(surface_id='canonical_stat::wall_fortification_multiplier', final_value=1.7),
            SimpleNamespace(surface_id='canonical_stat::tower_defense_pct', final_value=54.0),
            SimpleNamespace(surface_id='canonical_stat::tower_thorns_damage_pct', final_value=12.5),
            SimpleNamespace(surface_id='canonical_stat::tower_orb_count', final_value=8.0),
            SimpleNamespace(surface_id='canonical_stat::tower_orb_speed_rpm', final_value=6.832),
            SimpleNamespace(surface_id='runtime_mechanic_param::cards.plasma_cannon.effect_pct', final_value=54.0),
            SimpleNamespace(surface_id='mechanic_param::module.orbital_augment.electron_count', final_value=2.0),
        )
        return SimpleNamespace(resolved_surface_rows=rows)

    monkeypatch.setattr(boss_wave_engine_module, 'resolve_progression_family_query', _fake_family_query)

    values = BossWaveEngine._resolve_progression_family_values(
        patched_account_state=_build_state(),
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            perks_enabled=False,
            perk_preset_name='Farming',
            card_preset_name='Farming',
            module_preset_name='Farming',
        ),
    )

    assert seen_family_ids == ['progression_runtime_no_perks']
    assert values == {
        'canonical_stat::wall_hp': 1000.0,
        'canonical_stat::wall_regen': 25.0,
        'canonical_stat::wall_fortification_multiplier': 1.7,
        'canonical_stat::tower_defense_pct': 54.0,
        'canonical_stat::tower_thorns_damage_pct': 12.5,
        'canonical_stat::tower_orb_count': 8.0,
        'canonical_stat::tower_orb_speed_rpm': 6.832,
        'runtime_mechanic_param::cards.plasma_cannon.effect_pct': 54.0,
        'mechanic_param::module.orbital_augment.electron_count': 2.0,
    }


def test_boss_wave_engine_scaffold_emits_blocked_rows_until_ttk_inputs_closed():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[PerkTimelineEvent(wave=10, perk_id='PERK_ORBS_1', perk_name='Orbs +1')])
    engine = BossWaveEngine()
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=30,
        ),
    )
    assert len(result.rows) == 3
    assert result.diagnostics['blocked_on_open_runtime_cadence'] is True
    assert all(row.status == 'blocked_open_runtime_cadence' for row in result.rows)
    assert 'governed_orb_boss_hits_per_second_or_override' in result.rows[0].block_reason
    assert result.rows[0].plasma_cannon_effect_pct is not None




def test_boss_wave_engine_auto_resolves_orb_boss_hit_pct_from_account_lab():
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
        ),
    )
    row = result.rows[0]
    assert row.status == 'blocked_open_runtime_cadence'
    assert any('Orb boss-hit pct resolved from account lab level 10' in note for note in row.notes)
    assert 'governed_orb_boss_hit_pct_or_override' not in row.block_reason

def test_boss_wave_engine_scaffold_consumes_timeline_counts():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[
        PerkTimelineEvent(wave=10, perk_id='PERK_ORBS_1', perk_name='Orbs +1'),
        PerkTimelineEvent(wave=30, perk_id='PERK_X1_20_MAX_HEALTH', perk_name='x1.20 Max Health'),
    ])
    engine = BossWaveEngine()
    result = engine.run(account_state=state, init_state=init, config=BossWaveEngineConfig(preset_name='Farming', mode_id='farming', tier_column='Tier 12', start_boss_wave=10, end_boss_wave=30))
    assert result.diagnostics['perk_timeline_consumed'] is True
    assert [row.active_perk_count for row in result.rows] == [1, 1, 2]


def test_boss_wave_engine_scaffold_applies_workshop_progression_events():
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
            workshop_progression_events=[
                WorkshopUpgradeEvent(wave=20, track_name='Health', delta_levels=100, source='manual_buy'),
            ],
        ),
    )
    assert result.rows[0].wall_hp != result.rows[1].wall_hp
    assert any('Workshop progression events applied through wave 20: 1' in note for note in result.rows[1].notes)


def test_boss_wave_engine_ttk_slice_runs_when_explicit_overrides_provided():
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
            orb_boss_hit_pct_override=2.0,
            orb_boss_hits_per_second_override=2.0,
            electron_hits_per_second_override=1.0,
            boss_contact_time_seconds_override=1.5,
            max_ttk_seconds=60.0,
        ),
    )
    row = result.rows[0]
    assert result.diagnostics['ttk_slice_enabled'] is True
    assert row.status == 'survival_resolved'
    assert row.boss_effective_hp == row.boss_base_hp_common_reference * 20.0
    assert row.boss_ttk_seconds is not None and row.boss_ttk_seconds > 0
    assert row.thorns_contact_events_used >= 0


def test_boss_wave_engine_ttk_uses_thorns_contact_when_available():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    fast_contact = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=0.5,
            electron_hits_per_second_override=0.25,
            boss_contact_time_seconds_override=0.5,
            max_ttk_seconds=60.0,
        ),
    ).rows[0]
    late_contact = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=0.5,
            electron_hits_per_second_override=0.25,
            boss_contact_time_seconds_override=4.5,
                max_ttk_seconds=180.0,
        ),
    ).rows[0]
    assert fast_contact.boss_ttk_seconds < late_contact.boss_ttk_seconds
    assert fast_contact.thorns_contact_events_used >= 1


def test_boss_wave_engine_damage_intake_slice_runs_after_ttk():
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
            orb_boss_hit_pct_override=2.0,
            orb_boss_hits_per_second_override=2.0,
            electron_hits_per_second_override=1.0,
            boss_contact_time_seconds_override=1.5,
            max_ttk_seconds=60.0,
        ),
    )
    row = result.rows[0]
    assert result.diagnostics['damage_intake_slice_enabled'] is True
    assert row.status == 'survival_resolved'
    assert row.boss_hits_taken is not None and row.boss_hits_taken >= 0
    assert row.boss_total_damage_taken is not None and row.boss_total_damage_taken >= 0
    assert row.effective_wall_hp_pool is not None and row.effective_wall_hp_pool > 0
    assert row.wall_hp_after_boss is not None
    assert row.damage_reduction_pct_used is not None


def test_boss_wave_engine_damage_intake_uses_override_when_supplied():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    base = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=1.0,
            electron_hits_per_second_override=0.5,
            boss_contact_time_seconds_override=0.5,
            max_ttk_seconds=120.0,
        ),
    ).rows[0]
    boosted = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=1.0,
            electron_hits_per_second_override=0.5,
            boss_contact_time_seconds_override=0.5,
            effective_damage_reduction_pct_override=99.0,
            max_ttk_seconds=120.0,
        ),
    ).rows[0]
    assert base.status == 'survival_resolved'
    assert boosted.status == 'survival_resolved'
    assert boosted.boss_total_damage_taken < base.boss_total_damage_taken
    assert boosted.damage_reduction_pct_used == 99.0


def test_boss_wave_engine_attack_and_health_wave_use_skip_policy():
    account_state = _build_state()
    init_state = build_progression_init_state(account_state, preset_name='Farming', perk_timeline_path=ROOT / 'input' / 'perks_projected_max.timeline.json')
    engine = BossWaveEngine()
    result = engine.run(account_state=account_state, init_state=init_state, config=BossWaveEngineConfig(preset_name='Farming', mode_id='farming', tier_column='Tier 12', start_boss_wave=100, end_boss_wave=100, perks_enabled=True, perk_preset_name='projected_max'))
    row = result.rows[0]
    assert row.attack_wave < row.boss_wave
    assert row.health_wave < row.boss_wave
    assert row.status in {'blocked_open_runtime_cadence', 'ready_for_ttk', 'survival_resolved', 'failed_survival'}


def test_boss_wave_engine_generates_free_upgrades_from_chance_surfaces():
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
        ),
    )
    assert result.diagnostics['generated_free_upgrade_events'] > 0
    assert any('Generated free-upgrade events applied through wave 20' in note for note in result.rows[-1].notes)


def _inject_runtime_surfaces(engine: BossWaveEngine, surfaces: dict[str, float]) -> None:
    original = engine._recompute_row_map

    def patched(*, account_state, config, workshop_levels_current, perk_counts):
        result = original(
            account_state=account_state,
            config=config,
            workshop_levels_current=workshop_levels_current,
            perk_counts=perk_counts,
        )
        rows = dict(result.statbook.rows)
        for key, value in surfaces.items():
            rows[key] = StatRow(stat_name=key, final_value=value, value_type='float', source_count=1, status='resolved')
        return ProgressionRecalcResult(
            patched_account_state=result.patched_account_state,
            stat_inputs=result.stat_inputs,
            statbook=StatBook(rows=rows, diagnostics=dict(result.statbook.diagnostics)),
        )

    engine._recompute_row_map = patched


def test_boss_wave_engine_consumes_governed_runtime_surfaces_when_present():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    _inject_runtime_surfaces(engine, {
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 2.5,
        'runtime_mechanic_param::combat.orb_boss_hits_per_second': 2.0,
        'runtime_mechanic_param::combat.electron_hits_per_second': 1.0,
        'runtime_mechanic_param::combat.boss_contact_time_seconds': 1.25,
        'runtime_mechanic_param::combat.boss_hit_interval_seconds': 3.0,
        'runtime_mechanic_param::combat.effective_damage_reduction_pct': 98.0,
    })
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
        ),
    )
    row = result.rows[0]
    assert row.status == 'survival_resolved'
    assert row.boss_contact_time_seconds == 1.25
    assert row.damage_reduction_pct_used == 98.0
    assert result.diagnostics['governed_runtime_surface_consumed'] is True
    assert result.diagnostics['boss_hit_interval_seconds'] == 3.0




def test_boss_wave_engine_consumes_scenario_runtime_inputs_when_governed_surfaces_absent():
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
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.0,
                'orb_boss_hits_per_second': 2.0,
                'electron_hits_per_second': 1.0,
                'boss_contact_time_seconds': 1.25,
                'boss_hit_interval_seconds': 3.5,
                'effective_damage_reduction_pct': 97.0,
                'incoming_damage_multiplier': 0.5,
            },
        ),
    )
    row = result.rows[0]
    assert row.status == 'survival_resolved'
    assert row.boss_contact_time_seconds == 1.25
    assert row.damage_reduction_pct_used == 97.0
    assert result.diagnostics['scenario_runtime_input_consumed'] is True
    assert result.diagnostics['boss_hit_interval_seconds'] == 2.0
    assert result.diagnostics['scenario_engine_consumed'] is True


def test_boss_wave_engine_prefers_governed_surfaces_over_scenario_runtime_inputs():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    _inject_runtime_surfaces(engine, {
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 3.0,
        'runtime_mechanic_param::combat.orb_boss_hits_per_second': 1.5,
        'runtime_mechanic_param::combat.electron_hits_per_second': 0.75,
        'runtime_mechanic_param::combat.boss_contact_time_seconds': 2.0,
        'runtime_mechanic_param::combat.boss_hit_interval_seconds': 4.0,
        'runtime_mechanic_param::combat.effective_damage_reduction_pct': 96.0,
    })
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 9.0,
                'orb_boss_hits_per_second': 9.0,
                'electron_hits_per_second': 9.0,
                'boss_contact_time_seconds': 0.25,
                'boss_hit_interval_seconds': 0.25,
                'effective_damage_reduction_pct': 50.0,
            },
        ),
    )
    row = result.rows[0]
    assert row.status == 'survival_resolved'
    assert row.boss_contact_time_seconds == 2.0
    assert row.damage_reduction_pct_used == 96.0
    assert result.diagnostics['boss_hit_interval_seconds'] == 4.0

def test_boss_wave_engine_prefers_governed_runtime_surfaces_over_overrides():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    _inject_runtime_surfaces(engine, {
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 3.0,
        'runtime_mechanic_param::combat.orb_boss_hits_per_second': 1.5,
        'runtime_mechanic_param::combat.electron_hits_per_second': 0.75,
        'runtime_mechanic_param::combat.boss_contact_time_seconds': 2.0,
        'runtime_mechanic_param::combat.boss_hit_interval_seconds': 4.0,
    })
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=9.0,
            electron_hits_per_second_override=9.0,
            boss_contact_time_seconds_override=0.5,
            boss_hit_interval_seconds=0.5,
        ),
    )
    row = result.rows[0]
    assert row.status == 'survival_resolved'
    assert row.boss_contact_time_seconds == 2.0
    assert result.diagnostics['boss_hit_interval_seconds'] == 4.0
    assert any('consumed from governed surface' in note for note in row.notes)


def test_boss_wave_engine_consumes_scenario_engine_hit_interval_when_runtime_surface_absent():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    result = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='tournament',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
            league='champion',
            orb_boss_hit_pct_override=1.0,
            orb_boss_hits_per_second_override=1.0,
            electron_hits_per_second_override=1.0,
            boss_contact_time_seconds_override=1.0,
        ),
    )
    expected = compute_scenario_surfaces(ScenarioConfig(mode_id='tournament', tier=12, league='champion', tournament_wave=10)).boss_hit_interval_seconds
    assert result.diagnostics['boss_hit_interval_seconds'] == expected
    assert result.diagnostics['scenario_engine_consumed'] is True


def test_boss_wave_engine_uses_timing_engine_for_encounter_damage_reduction_when_no_explicit_surface():
    state = _build_state()
    init = build_progression_init_state(state, preset_name='Farming', perk_timeline=[])
    engine = BossWaveEngine()
    _inject_runtime_surfaces(engine, {
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 2.0,
        'runtime_mechanic_param::combat.orb_boss_hits_per_second': 2.0,
        'runtime_mechanic_param::combat.electron_hits_per_second': 1.0,
        'runtime_mechanic_param::combat.boss_contact_time_seconds': 1.25,
    })
    with_cf = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
        ),
    ).rows[0]
    engine = BossWaveEngine()
    _inject_runtime_surfaces(engine, {
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 2.0,
        'runtime_mechanic_param::combat.orb_boss_hits_per_second': 2.0,
        'runtime_mechanic_param::combat.electron_hits_per_second': 1.0,
        'runtime_mechanic_param::combat.boss_contact_time_seconds': 1.25,
        'mechanic_param::uw.chrono_field.duration_seconds': 0.0,
        'mechanic_param::uw.chrono_field.damage_reduction_pct': 0.0,
    })
    without_cf = engine.run(
        account_state=state,
        init_state=init,
        config=BossWaveEngineConfig(
            preset_name='Farming',
            mode_id='farming',
            tier_column='Tier 12',
            start_boss_wave=10,
            end_boss_wave=10,
        ),
    ).rows[0]
    assert with_cf.status == 'survival_resolved'
    assert without_cf.status == 'survival_resolved'
    assert with_cf.boss_total_damage_taken < without_cf.boss_total_damage_taken
