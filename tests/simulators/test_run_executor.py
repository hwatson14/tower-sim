from __future__ import annotations

import inspect
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
    assert result.diagnostics['qe_dirty_reresolve_count'] == 0
    assert result.diagnostics['delta_fallback_count'] == 0
    assert result.diagnostics['checkpoint_resolution_mode'] == 'per_boss_wave'


def _safe_mutated_workshop_levels(state, projected, deltas):
    workshop = dict(projected.workshop_levels_current)
    for track_name, delta in deltas.items():
        entry = state.workshop[track_name]
        current = int(workshop.get(track_name, 0))
        max_level = int(entry.max_level) if entry.max_level is not None else current + delta
        workshop[track_name] = min(max_level, current + delta)
    return workshop


def _build_state_and_projected():
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import PerkState
    from simulators.run_executor import build_start_of_run_state

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))
    return state, projected


def test_run_executor_source__does_not_reintroduce_local_qe_formula_recompute():
    import simulators.run_executor as run_executor

    source = inspect.getsource(run_executor)
    assert '_apply_fast_progression_overlay' not in source
    assert '_recompute_hot_surface_row' not in source
    assert '_supports_fast_overlay' not in source
    assert 'WORKSHOP_FORMULA_VALUES' not in source
    assert 'CANONICAL_PCT_CAPS' not in source


def test_resolve_snapshot_for_projected_state__delta_path_matches_full_resolve_for_supported_tracks():
    from simulators.contracts import DirtyLedger, ProjectedRunState, WaveCheckpoint
    from simulators.run_executor import RunToMaxConfig, _normalized_checkpoint_state_for_projected_state, _resolve_snapshot_for_projected_state
    from simulators.snapshot_resolver import resolve_wave_row_snapshot

    state, projected = _build_state_and_projected()
    config = RunToMaxConfig(perks_enabled=False, state_mode='start_of_run')
    baseline_normalized = _normalized_checkpoint_state_for_projected_state(
        account_state=state,
        config=config,
        projected_state=projected,
    )
    baseline_snapshot = resolve_wave_row_snapshot(baseline_normalized)

    workshop = _safe_mutated_workshop_levels(state, projected, {'Health': 1, 'Health Regen': 1, 'Defense %': 1, 'Thorn Damage': 1})
    target_projected = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=10),
        workshop_levels_current=workshop,
        perk_state=projected.perk_state,
        wave_progression_state=dict(projected.wave_progression_state),
        free_upgrade_state=dict(projected.free_upgrade_state),
        counters=dict(projected.counters),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
        notes=projected.notes,
    )

    delta_snapshot, fallback_used = _resolve_snapshot_for_projected_state(
        account_state=state,
        config=config,
        projected_state=target_projected,
        current_snapshot=baseline_snapshot,
        row_resolver=resolve_wave_row_snapshot,
        changed_tracks=('Health', 'Health Regen', 'Defense %', 'Thorn Damage'),
    )
    full_snapshot = resolve_wave_row_snapshot(
        _normalized_checkpoint_state_for_projected_state(
            account_state=state,
            config=config,
            projected_state=target_projected,
        )
    )

    assert fallback_used is False
    assert delta_snapshot.resolved_statbook.diagnostics['qe_bundle_id'] == 'boss_wave_hot_surfaces'
    for surface_id in (
        'state::wall.hp',
        'state::wall.regen',
        'state::tower.defense_pct',
        'state::tower.thorns_damage_pct',
    ):
        assert delta_snapshot.resolved_statbook.rows[surface_id].final_value == full_snapshot.resolved_statbook.rows[surface_id].final_value
        assert delta_snapshot.resolved_statbook.rows[surface_id].contributors


def test_resolve_snapshot_for_projected_state__falls_back_for_unsupported_tracks_and_matches_full_resolve():
    from simulators.contracts import DirtyLedger, ProjectedRunState, WaveCheckpoint
    from simulators.run_executor import RunToMaxConfig, _normalized_checkpoint_state_for_projected_state, _resolve_snapshot_for_projected_state
    from simulators.snapshot_resolver import resolve_wave_row_snapshot

    state, projected = _build_state_and_projected()
    config = RunToMaxConfig(perks_enabled=False, state_mode='start_of_run')
    baseline_snapshot = resolve_wave_row_snapshot(
        _normalized_checkpoint_state_for_projected_state(
            account_state=state,
            config=config,
            projected_state=projected,
        )
    )
    workshop = _safe_mutated_workshop_levels(state, projected, {'Wall Health': 1})
    target_projected = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=10),
        workshop_levels_current=workshop,
        perk_state=projected.perk_state,
        wave_progression_state=dict(projected.wave_progression_state),
        free_upgrade_state=dict(projected.free_upgrade_state),
        counters=dict(projected.counters),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
        notes=projected.notes,
    )

    delta_snapshot, fallback_used = _resolve_snapshot_for_projected_state(
        account_state=state,
        config=config,
        projected_state=target_projected,
        current_snapshot=baseline_snapshot,
        row_resolver=resolve_wave_row_snapshot,
        changed_tracks=('Wall Health',),
    )
    full_snapshot = resolve_wave_row_snapshot(
        _normalized_checkpoint_state_for_projected_state(
            account_state=state,
            config=config,
            projected_state=target_projected,
        )
    )

    assert fallback_used is True
    assert delta_snapshot.resolved_statbook.diagnostics['delta_fallback_used'] is True
    for surface_id in ('state::wall.hp', 'state::wall.regen', 'state::tower.defense_pct'):
        assert delta_snapshot.resolved_statbook.rows[surface_id].final_value == full_snapshot.resolved_statbook.rows[surface_id].final_value


def test_resolve_snapshot_for_projected_state__health_change_keeps_delta_path_and_updates_hp_surfaces():
    from simulators.contracts import DirtyLedger, ProjectedRunState, WaveCheckpoint
    from simulators.run_executor import RunToMaxConfig, _normalized_checkpoint_state_for_projected_state, _resolve_snapshot_for_projected_state
    from simulators.snapshot_resolver import resolve_wave_row_snapshot

    state, projected = _build_state_and_projected()
    config = RunToMaxConfig(perks_enabled=False, state_mode='start_of_run')
    baseline_snapshot = resolve_wave_row_snapshot(
        _normalized_checkpoint_state_for_projected_state(
            account_state=state,
            config=config,
            projected_state=projected,
        )
    )
    workshop = _safe_mutated_workshop_levels(state, projected, {'Health': 1})
    target_projected = ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=10),
        workshop_levels_current=workshop,
        perk_state=projected.perk_state,
        wave_progression_state=dict(projected.wave_progression_state),
        free_upgrade_state=dict(projected.free_upgrade_state),
        counters=dict(projected.counters),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
        notes=projected.notes,
    )

    delta_snapshot, fallback_used = _resolve_snapshot_for_projected_state(
        account_state=state,
        config=config,
        projected_state=target_projected,
        current_snapshot=baseline_snapshot,
        row_resolver=resolve_wave_row_snapshot,
        changed_tracks=('Health',),
    )
    full_snapshot = resolve_wave_row_snapshot(
        _normalized_checkpoint_state_for_projected_state(
            account_state=state,
            config=config,
            projected_state=target_projected,
        )
    )

    assert fallback_used is False
    assert delta_snapshot.resolved_statbook.diagnostics['delta_fallback_used'] is False
    for surface_id in ('state::tower.hp', 'state::wall.hp'):
        assert surface_id in delta_snapshot.resolved_statbook.diagnostics['delta_impacted_surface_ids']
        assert delta_snapshot.resolved_statbook.rows[surface_id].final_value == full_snapshot.resolved_statbook.rows[surface_id].final_value
    assert full_snapshot.resolved_statbook.rows['state::tower.hp'].final_value != baseline_snapshot.resolved_statbook.rows['state::tower.hp'].final_value


def test_run_to_max__table_sweep_uses_delta_path_not_overlay(monkeypatch):
    from input.loader import load_inputs
    from input.runtime_state import build_runtime_state
    from simulators.contracts import DirtyLedger, PerkState
    import simulators.run_executor as run_executor_module
    from simulators.run_executor import RunToMaxConfig, build_start_of_run_state, run_to_max

    bundle = load_inputs()
    state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    projected = build_start_of_run_state(state, preset_name='Farming', perk_state=PerkState(wave=0, counts={}, dirty=False))

    def _raise_if_called(*args, **kwargs):
        raise AssertionError('overlay path must not be used')

    monkeypatch.setattr(run_executor_module, '_apply_fast_progression_overlay', _raise_if_called, raising=False)

    delta_calls = {'count': 0}
    original_delta = run_executor_module.resolve_wave_row_snapshot_delta

    def _counting_delta(*args, **kwargs):
        delta_calls['count'] += 1
        return original_delta(*args, **kwargs)

    monkeypatch.setattr(run_executor_module, 'resolve_wave_row_snapshot_delta', _counting_delta)

    def _allocate_supported_change(projected_state, **kwargs):
        counters = dict(projected_state.counters)
        counters['changed_workshop_tracks_last_step'] = ('Health Regen',)
        workshop_levels = dict(projected_state.workshop_levels_current)
        entry = state.workshop['Health Regen']
        current = int(workshop_levels.get('Health Regen', 0))
        max_level = int(entry.max_level) if entry.max_level is not None else current + 1
        workshop_levels['Health Regen'] = min(max_level, current + 1)
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

    monkeypatch.setattr(run_executor_module, 'allocate_generated_free_upgrades_to_workshop', _allocate_supported_change)
    monkeypatch.setattr(run_executor_module, '_simulate_boss_ttk', lambda **kwargs: run_executor_module.BossTTKResult(ttk_seconds=5.0))
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
        config=RunToMaxConfig(execution_mode='table_sweep', start_wave=10, end_wave=30, boss_wave_step=10, perks_enabled=False, state_mode='start_of_run'),
    )

    assert result.max_wave == 30
    assert delta_calls['count'] == 3
    assert result.diagnostics['qe_dirty_reresolve_count'] == 3
    assert result.diagnostics['delta_fallback_count'] == 0


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
