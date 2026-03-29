from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_advance_projected_wave_state__advances_from_prior_row_without_rebuilding():
    from simulators.contracts import DirtyLedger, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.progression import advance_projected_wave_state

    initial = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=10),
        workshop_levels_current={'health': 5},
        perk_state=PerkState(wave=10, counts={'perk.test': 2}, dirty=False),
        wave_progression_state={
            'display_wave': 10,
            'attack_wave': 8,
            'health_wave': 7,
            'attack_skip_counter': 0.25,
            'health_skip_counter': 0.50,
        },
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
    )

    advanced = advance_projected_wave_state(
        initial,
        target_display_wave=13,
        attack_skip_pct=0.25,
        health_skip_pct=0.50,
    )

    assert advanced.checkpoint.display_wave == 13
    assert advanced.workshop_levels_current == {'health': 5}
    assert advanced.perk_state.counts == {'perk.test': 2}
    assert advanced.wave_progression_state == {
        'display_wave': 13,
        'attack_wave': 10,
        'health_wave': 8,
        'attack_skip_counter': 0.0,
        'health_skip_counter': 0.0,
    }
    assert advanced.dirty_ledger.qe_dirty is False
    assert advanced.dirty_ledger.timing_dirty is False


def test_advance_projected_free_upgrade_state__accumulates_deterministic_carry_by_wave():
    from simulators.contracts import DirtyLedger, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.progression import advance_projected_free_upgrade_state

    initial = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=10),
        workshop_levels_current={'health': 5},
        perk_state=PerkState(wave=10, counts={}, dirty=False),
        free_upgrade_state={'carry_by_category': {'attack': 0.40, 'defense': 0.0, 'utility': 0.0}},
        counters={'generated_free_upgrades_by_category': {'attack': 1, 'defense': 0, 'utility': 0}},
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
    )

    advanced = advance_projected_free_upgrade_state(
        initial,
        target_display_wave=13,
        free_attack_upgrade_chance_pct=25.0,
        free_defense_upgrade_chance_pct=50.0,
        free_utility_upgrade_chance_pct=0.0,
    )

    assert advanced.checkpoint.display_wave == 13
    assert advanced.free_upgrade_state['carry_by_category'] == pytest.approx(
        {
            'attack': 0.15,
            'defense': 0.50,
            'utility': 0.0,
        }
    )
    assert advanced.counters['generated_free_upgrades_by_category'] == {
        'attack': 2,
        'defense': 1,
        'utility': 0,
    }
    assert advanced.counters['generated_free_upgrades_last_step_by_category'] == {
        'attack': 1,
        'defense': 1,
        'utility': 0,
    }
    assert advanced.counters['generated_free_upgrades_total'] == 2
    assert advanced.dirty_ledger.qe_dirty is False
    assert advanced.dirty_ledger.timing_dirty is False


def test_allocate_generated_free_upgrades_to_workshop__applies_last_step_counts_in_stable_track_order():
    from simulators.contracts import DirtyLedger, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.progression import allocate_generated_free_upgrades_to_workshop

    initial = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=20),
        workshop_levels_current={'Damage': 9, 'Range': 0, 'Health': 4},
        perk_state=PerkState(wave=20, counts={}, dirty=False),
        free_upgrade_state={'next_index_by_category': {'attack': 0, 'defense': 0, 'utility': 0}},
        counters={
            'generated_free_upgrades_last_step_by_category': {'attack': 3, 'defense': 1, 'utility': 0},
        },
        dirty_ledger=DirtyLedger(),
    )

    advanced = allocate_generated_free_upgrades_to_workshop(
        initial,
        category_track_order={
            'attack': ['Damage', 'Range'],
            'defense': ['Health'],
            'utility': [],
        },
        track_max_levels={'Damage': 10, 'Range': 2, 'Health': 5},
    )

    assert advanced.workshop_levels_current == {'Damage': 10, 'Range': 2, 'Health': 5}
    assert advanced.free_upgrade_state['next_index_by_category'] == {'attack': 1, 'defense': 1, 'utility': 0}
    assert advanced.counters['allocated_free_upgrades_by_category'] == {'attack': 3, 'defense': 1, 'utility': 0}
    assert advanced.counters['unallocated_free_upgrades_by_category'] == {'attack': 0, 'defense': 0, 'utility': 0}
    assert advanced.dirty_ledger.qe_dirty is True
    assert advanced.dirty_ledger.timing_dirty is True


def test_allocate_generated_free_upgrades_to_workshop__tracks_unallocated_when_category_is_exhausted():
    from simulators.contracts import DirtyLedger, PerkState, ProjectedRunState, WaveCheckpoint
    from simulators.progression import allocate_generated_free_upgrades_to_workshop

    initial = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=20),
        workshop_levels_current={'Damage': 10},
        perk_state=PerkState(wave=20, counts={}, dirty=False),
        free_upgrade_state={'next_index_by_category': {'attack': 0, 'defense': 0, 'utility': 0}},
        counters={
            'generated_free_upgrades_last_step_by_category': {'attack': 2, 'defense': 0, 'utility': 0},
        },
        dirty_ledger=DirtyLedger(),
    )

    advanced = allocate_generated_free_upgrades_to_workshop(
        initial,
        category_track_order={'attack': ['Damage'], 'defense': [], 'utility': []},
        track_max_levels={'Damage': 10},
    )

    assert advanced.workshop_levels_current == {'Damage': 10}
    assert advanced.counters['allocated_free_upgrades_total'] == 0
    assert advanced.counters['unallocated_free_upgrades_total'] == 2
    assert advanced.dirty_ledger.qe_dirty is False


def test_run_to_max__steps_boss_waves_and_stops_on_negative_survival_margin(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import DirtyLedger, PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave, survival_ok):
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
                        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
                        'state::wall.hp': _FakeRow(1000.0),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0 if survival_ok else 0.1,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0 if survival_ok else 0.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))

    seen = []
    intake_calls = []

    def _resolver(normalized):
        wave = normalized.checkpoint.display_wave
        seen.append(wave)
        return _FakeSnapshot(wave, survival_ok=(wave < 30))

    def _fake_ttk(**kwargs):
        return run_executor_module.BossTTKResult(ttk_seconds=5.0)

    def _fake_intake(**kwargs):
        wave = 10 * (len(intake_calls) + 1)
        intake_calls.append(wave)
        margin = 100.0 if wave < 30 else -1.0
        return run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=margin,
            total_damage_taken=0.0,
            boss_hits_taken=1,
        )

    monkeypatch.setattr(run_executor_module, '_simulate_boss_ttk', _fake_ttk)
    monkeypatch.setattr(run_executor_module, '_simulate_boss_damage_intake', _fake_intake)

    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(start_wave=10, end_wave=50, boss_wave_step=10, tier_column='Tier 14'),
        row_resolver=_resolver,
    )

    assert seen == [0]
    assert intake_calls == [10, 20, 30]
    assert result.max_wave == 20
    assert result.row_count == 3
    assert result.diagnostics['execution_mode'] == 'table_sweep'
    assert result.diagnostics['wave_progression_owner'] == 'simulators.progression.advance_projected_wave_state'
    assert result.diagnostics['free_upgrade_owner'] == 'simulators.progression.advance_projected_free_upgrade_state'


def test_run_to_max__rejects_non_table_execution_mode():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))

    with pytest.raises(ValueError, match="execution_mode"):
        run_to_max(
            account_state=state,
            initial_projected_state=projected,
            config=RunToMaxConfig(execution_mode='unknown_mode'),
        )


def test_run_to_max__table_sweep_reuses_baseline_when_rows_do_not_change(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave):
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
                        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
                        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
                        'state::wall.hp': _FakeRow(1000.0),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    projected = type(projected)(
        checkpoint=projected.checkpoint,
        workshop_levels_current={
            **projected.workshop_levels_current,
            'Damage': 0,
            'Health': 0,
            'Cash Bonus': 0,
        },
        perk_state=projected.perk_state,
        wave_progression_state=dict(projected.wave_progression_state),
        free_upgrade_state=dict(projected.free_upgrade_state),
        counters=dict(projected.counters),
        dirty_ledger=projected.dirty_ledger,
        notes=projected.notes,
    )
    seen = []

    def _resolver(normalized):
        wave = normalized.checkpoint.display_wave
        seen.append(wave)
        return _FakeSnapshot(wave)

    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_ttk',
        lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0),
    )
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_damage_intake',
        lambda **kwargs: run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=100.0,
            total_damage_taken=0.0,
            boss_hits_taken=1,
        ),
    )

    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(execution_mode='table_sweep', start_wave=10, end_wave=30, boss_wave_step=10),
        row_resolver=_resolver,
    )

    assert len(seen) == 1
    assert result.max_wave == 30
    assert result.diagnostics['execution_mode'] == 'table_sweep'
    assert result.diagnostics['qe_resolution_count'] == 1
    assert result.diagnostics['snapshot_reuse_count'] == 3
    assert result.diagnostics['fast_overlay_count'] == 0
    assert result.diagnostics['checkpoint_resolution_mode'] == 'per_boss_wave'


def test_run_to_max__table_sweep_uses_fast_overlay_when_workshop_levels_change(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave):
            from qe.models import StatRow
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': StatRow(
                            stat_name='state::tower.enemy_attack_level_skip_pct',
                            final_value=0.0,
                            value_type='scalar',
                            source_count=3,
                            contributors=[
                                {'contributor_id': 'workshop__tower__enemy_attack_level_skip__pct', 'value': 0.05, 'composition_stage': 'additive_pre_cap', 'active': True},
                                {'contributor_id': 'enhancement.enemy_level_skips_+.account_state', 'value': 1.16, 'composition_stage': 'additive_pre_cap', 'active': True},
                                {'contributor_id': 'enhancements__tower__enemy_attack_level_skip__multiplier', 'value': 1.16, 'composition_stage': 'multiplicative', 'active': True},
                            ],
                        ),
                        'state::tower.enemy_health_level_skip_pct': StatRow(
                            stat_name='state::tower.enemy_health_level_skip_pct',
                            final_value=0.0,
                            value_type='scalar',
                            source_count=2,
                            contributors=[
                                {'contributor_id': 'workshop__tower__enemy_health_level_skip__pct', 'value': 0.05, 'composition_stage': 'additive_pre_cap', 'active': True},
                                {'contributor_id': 'enhancements__tower__enemy_health_level_skip__multiplier', 'value': 1.16, 'composition_stage': 'multiplicative', 'active': True},
                            ],
                        ),
                        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(100.0),
                        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(100.0),
                        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(100.0),
                        'state::wall.hp': StatRow(
                            stat_name='state::wall.hp',
                            final_value=1000.0,
                            value_type='scalar',
                            source_count=2,
                            contributors=[
                                {'contributor_id': 'workshop__wall__health__flat', 'value': 0.2, 'composition_stage': 'additive_pre_cap', 'active': True},
                                {'contributor_id': 'lab__wall__health__pct', 'value': 100.0, 'composition_stage': 'additive_pre_cap', 'active': True},
                            ],
                        ),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    projected = type(projected)(
        checkpoint=projected.checkpoint,
        workshop_levels_current={
            **projected.workshop_levels_current,
            'Damage': 0,
            'Health': 0,
            'Cash Bonus': 0,
        },
        perk_state=projected.perk_state,
        wave_progression_state=dict(projected.wave_progression_state),
        free_upgrade_state=dict(projected.free_upgrade_state),
        counters=dict(projected.counters),
        dirty_ledger=projected.dirty_ledger,
        notes=projected.notes,
    )
    seen = []

    def _resolver(normalized):
        wave = normalized.checkpoint.display_wave
        seen.append((wave, dict(normalized.projected_run_state.workshop_levels_current)))
        return _FakeSnapshot(wave)

    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_ttk',
        lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0),
    )
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_damage_intake',
        lambda **kwargs: run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=100.0,
            total_damage_taken=0.0,
            boss_hits_taken=1,
        ),
    )

    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(execution_mode='table_sweep', start_wave=10, end_wave=30, boss_wave_step=10),
        row_resolver=_resolver,
    )

    assert len(seen) == 1
    assert result.diagnostics['qe_resolution_count'] == 1
    assert result.diagnostics['fast_overlay_count'] > 0


def test_run_to_max__table_sweep_ignores_irrelevant_workshop_change(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import DirtyLedger, PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave):
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
                        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
                        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
                        'state::wall.hp': _FakeRow(1000.0),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    seen = []

    def _resolver(normalized):
        seen.append(normalized.checkpoint.display_wave)
        return _FakeSnapshot(normalized.checkpoint.display_wave)

    def _allocate_irrelevant_change(projected_state, **kwargs):
        counters = dict(projected_state.counters)
        counters['changed_workshop_tracks_last_step'] = ('Damage',)
        workshop_levels = dict(projected_state.workshop_levels_current)
        workshop_levels['Damage'] = workshop_levels.get('Damage', 0) + 1
        return type(projected_state)(
            checkpoint=projected_state.checkpoint,
            workshop_levels_current=workshop_levels,
            perk_state=projected_state.perk_state,
            wave_progression_state=dict(projected_state.wave_progression_state),
            free_upgrade_state=dict(projected_state.free_upgrade_state),
            counters=counters,
            dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
            notes=projected_state.notes,
        )

    monkeypatch.setattr(run_executor_module, 'allocate_generated_free_upgrades_to_workshop', _allocate_irrelevant_change)
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_ttk',
        lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0),
    )
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_damage_intake',
        lambda **kwargs: run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=100.0,
            total_damage_taken=0.0,
            boss_hits_taken=1,
        ),
    )

    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(execution_mode='table_sweep', start_wave=10, end_wave=30, boss_wave_step=10),
        row_resolver=_resolver,
    )

    assert len(seen) == 1
    assert result.diagnostics['qe_resolution_count'] == 1
    assert result.diagnostics['snapshot_reuse_count'] == 3
    assert result.diagnostics['ignored_workshop_track_count'] == 3
    assert result.diagnostics['qe_fallback_track_count'] == 0


def test_run_to_max__table_sweep_reruns_qe_for_fallback_track(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import DirtyLedger, PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave):
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
                        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
                        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
                        'state::wall.hp': _FakeRow(1000.0),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    seen = []

    def _resolver(normalized):
        seen.append(normalized.checkpoint.display_wave)
        return _FakeSnapshot(normalized.checkpoint.display_wave)

    def _allocate_fallback_change(projected_state, **kwargs):
        counters = dict(projected_state.counters)
        counters['changed_workshop_tracks_last_step'] = ('Orbs',)
        workshop_levels = dict(projected_state.workshop_levels_current)
        workshop_levels['Orbs'] = workshop_levels.get('Orbs', 0) + 1
        return type(projected_state)(
            checkpoint=projected_state.checkpoint,
            workshop_levels_current=workshop_levels,
            perk_state=projected_state.perk_state,
            wave_progression_state=dict(projected_state.wave_progression_state),
            free_upgrade_state=dict(projected_state.free_upgrade_state),
            counters=counters,
            dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
            notes=projected_state.notes,
        )

    monkeypatch.setattr(run_executor_module, 'allocate_generated_free_upgrades_to_workshop', _allocate_fallback_change)
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_ttk',
        lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0),
    )
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_damage_intake',
        lambda **kwargs: run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=100.0,
            total_damage_taken=0.0,
            boss_hits_taken=1,
        ),
    )

    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(execution_mode='table_sweep', start_wave=10, end_wave=30, boss_wave_step=10),
        row_resolver=_resolver,
    )

    assert len(seen) == 4
    assert result.diagnostics['qe_resolution_count'] == 4
    assert result.diagnostics['snapshot_reuse_count'] == 0
    assert result.diagnostics['qe_fallback_track_count'] == 3
    assert result.diagnostics['ignored_workshop_track_count'] == 0


def test_build_boss_wave_table__emits_boss_wave_rows_with_attack_and_health(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_boss_wave_table, build_start_of_run_state

    class _FakeRow:
        def __init__(self, value):
            self.final_value = value

    class _FakeSnapshot:
        def __init__(self, wave):
            from simulators.contracts import PerformanceMetrics, WaveCheckpoint
            self.checkpoint = WaveCheckpoint(display_wave=wave)
            self.resolved_statbook = type(
                'StatBook',
                (),
                {
                    'rows': {
                        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
                        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
                        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
                        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
                        'state::wall.hp': _FakeRow(1000.0),
                        'state::wall.regen': _FakeRow(10.0),
                        'state::wall.fortification_multiplier': _FakeRow(1.0),
                        'state::tower.defense_pct': _FakeRow(50.0),
                        'state::tower.thorns_damage_pct': _FakeRow(10.0),
                        'state::cards.plasma_cannon.effect_pct': _FakeRow(30.0),
                    }
                },
            )()
            self.scenario_context = {}
            self.timing_context = type('Timing', (), {})()
            self.geometry_context = {}
            self.combat_runtime = type(
                'Combat',
                (),
                {
                    'orb_boss_hit_pct': 5.0,
                    'orb_boss_hits_per_second': 5.0,
                    'electron_hits_per_second': 5.0,
                    'boss_contact_time_seconds': 1.0,
                    'boss_hit_interval_seconds': 2.0,
                    'effective_damage_reduction_pct': 90.0,
                    'incoming_damage_multiplier': 1.0,
                },
            )()
            self.metrics = PerformanceMetrics(row_resolution_ms=1.0, qe_resolution_count=1, timing_recompute_count=1)

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))

    def _resolver(normalized):
        return _FakeSnapshot(normalized.checkpoint.display_wave)

    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_ttk',
        lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0),
    )
    monkeypatch.setattr(
        run_executor_module,
        '_simulate_boss_damage_intake',
        lambda **kwargs: run_executor_module.BossDamageIntakeResult(
            survival_margin_hp=100.0,
            total_damage_taken=25.0,
            boss_hits_taken=2,
        ),
    )

    rows = build_boss_wave_table(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(start_wave=10, end_wave=30, boss_wave_step=10, tier_column='Tier 14'),
        row_resolver=_resolver,
    )

    assert [row['display_wave'] for row in rows] == [10, 20, 30]
    assert rows[0]['attack_wave'] == 10
    assert rows[0]['health_wave'] == 10
    assert rows[0]['boss_attack'] == rows[0]['wave_attack']
    assert rows[0]['boss_health'] == pytest.approx(rows[0]['wave_health'] * run_executor_module.BOSS_HP_MULTIPLIER)
    assert rows[0]['survives_boss'] is True


@pytest.mark.expensive
def test_run_to_max__warm_path_benchmark_shape():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    result = run_to_max(
        account_state=state,
        initial_projected_state=projected,
        config=RunToMaxConfig(
            start_wave=10,
            end_wave=30,
            boss_wave_step=10,
            tier_column='Tier 14',
        ),
    )
    assert result.row_count >= 1
