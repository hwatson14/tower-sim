from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from math import inf, isfinite
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from input.state_types import AccountState, ScenarioRuntimeInputs
from qe.consumer_registry import load_consumer_bundle_definitions
from qe.query_derived_composites import compute_derived_edamage
from qe.models import StatBook, StatRow
from qe.kb_surfaces import (
    BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT,
    BOSS_HP_MULTIPLIER,
    ELECTRON_BOSS_REMAINING_HP_PCT,
    THORNS_BOSS_EFFECTIVENESS,
)
from simulators.contracts import (
    DirtyLedger,
    NormalizedCheckpointState,
    PerkState,
    ProjectedRunState,
    RunResult,
    WaveCheckpoint,
    WaveRowSnapshot,
)
from simulators.progression import (
    advance_projected_free_upgrade_state,
    advance_projected_wave_state,
    allocate_generated_free_upgrades_to_workshop,
)
from simulators.snapshot_resolver import resolve_wave_row_snapshot, resolve_wave_row_snapshot_delta
from simulators.timing import compute_average_damage_reduction_fraction_over_interval
from simulators.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState

ROOT = Path(__file__).resolve().parents[1]
ENEMY_DAMAGE_TABLE = ROOT / 'kb' / 'enemies' / 'tables' / 'enemy-damage-table.csv'
ENEMY_HEALTH_TABLE = ROOT / 'kb' / 'enemies' / 'tables' / 'enemy-health-table.csv'
KILL_HP_THRESHOLD = 1e-9
_BASELINE_SNAPSHOT_CACHE: dict[tuple[object, ...], WaveRowSnapshot] = {}
_WORKSHOP_TRACK_CATEGORY_BY_NAME: dict[str, str] = {
    'Damage': 'attack',
    'Attack Speed': 'attack',
    'Critical Chance': 'attack',
    'Critical Factor': 'attack',
    'Range': 'attack',
    'Damage / Meter': 'attack',
    'Multishot Chance': 'attack',
    'Multishot Targets': 'attack',
    'Rapid Fire Chance': 'attack',
    'Rapid Fire Duration': 'attack',
    'Bounce Shot Chance': 'attack',
    'Bounce Shot Targets': 'attack',
    'Bounce Shot Range': 'attack',
    'Super Critical Chance': 'attack',
    'Super Critical Mult': 'attack',
    'Rend Armor Chance': 'attack',
    'Rend Armor Mult': 'attack',
    'Health': 'defense',
    'Health Regen': 'defense',
    'Defense %': 'defense',
    'Defense Absolute': 'defense',
    'Thorn Damage': 'defense',
    'Lifesteal': 'defense',
    'Knockback Chance': 'defense',
    'Knockback Force': 'defense',
    'Orb Speed': 'defense',
    'Orb Boss Hit': 'defense',
    'Orbs': 'defense',
    'Death Defy': 'defense',
    'Shockwave Size': 'defense',
    'Shockwave Frequency': 'defense',
    'Land Mine Chance': 'defense',
    'Land Mine Damage': 'defense',
    'Land Mine Radius': 'defense',
    'Wall Health': 'defense',
    'Wall Rebuild': 'defense',
    'Wall Regen': 'defense',
    'Wall Thorns': 'defense',
    'Wall Invincibility': 'defense',
    'Wall Fortification': 'defense',
    'Cash Bonus': 'utility',
    'Cash / Wave': 'utility',
    'Coin / Kill Bonus': 'utility',
    'Coin / Wave': 'utility',
    'Free Attack Upgrade': 'utility',
    'Free Defense Upgrade': 'utility',
    'Free Utility Upgrade': 'utility',
    'Interest / Wave': 'utility',
    'Recovery Amount': 'utility',
    'Max Amount': 'utility',
    'Package Chance': 'utility',
    'Enemy Attack Level Skip': 'utility',
    'Enemy Health Level Skip': 'utility',
}


@lru_cache(maxsize=1)
def _boss_wave_hot_surface_ids() -> tuple[str, ...]:
    definition = load_consumer_bundle_definitions()[('simulator_boss_wave', 'boss_wave_hot_surfaces')]
    return definition.required_surface_ids + definition.optional_surface_ids


def _resolve_snapshot_for_projected_state(
    *,
    account_state: AccountState,
    config: RunToMaxConfig,
    projected_state: ProjectedRunState,
    current_snapshot: WaveRowSnapshot,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot],
    changed_tracks: tuple[str, ...],
) -> tuple[WaveRowSnapshot, bool]:
    normalized = _normalized_checkpoint_state_for_projected_state(
        account_state=account_state,
        config=config,
        projected_state=projected_state,
    )
    if row_resolver is not resolve_wave_row_snapshot:
        return row_resolver(normalized), False
    snapshot = resolve_wave_row_snapshot_delta(
        normalized,
        baseline_snapshot=current_snapshot,
        changed_tracks=changed_tracks,
    )
    return snapshot, bool(snapshot.resolved_statbook.diagnostics.get('delta_fallback_used'))


@dataclass(frozen=True)
class RunToMaxConfig:
    execution_mode: str = 'table_sweep'
    preset_name: str = 'Farming'
    mode_id: str = 'farming'
    tier_column: str = 'Tier 14'
    start_wave: int = 10
    end_wave: int = 1000
    boss_wave_step: int = 10
    perks_enabled: bool = True
    state_mode: str = 'start_of_run'
    scenario_runtime_inputs: Optional[ScenarioRuntimeInputs] = None
    perk_timeline: tuple[dict[str, Any], ...] = ()
    max_ttk_seconds: float = 120.0
    incoming_damage_multiplier_override: float = 1.0
    plasma_cannon_resistance_multiplier: float = 1.0
    orb_resistance_multiplier: float = 1.0
    thorns_resistance_multiplier: float = 1.0


@dataclass(frozen=True)
class BossTTKResult:
    ttk_seconds: float


@dataclass(frozen=True)
class BossDamageIntakeResult:
    survival_margin_hp: float
    total_damage_taken: float
    boss_hits_taken: int


def build_start_of_run_state(account_state: AccountState, *, preset_name: str, perk_state) -> ProjectedRunState:
    workshop_levels_current = {
        name: int((entry.preset_levels.get(preset_name) or 0))
        for name, entry in account_state.workshop.items()
        if entry.max_level is not None
    }
    checkpoint = WaveCheckpoint(display_wave=0)
    return ProjectedRunState(
        checkpoint=checkpoint,
        workshop_levels_current=workshop_levels_current,
        perk_state=perk_state,
        wave_progression_state={
            'display_wave': 0,
            'attack_wave': 0,
            'health_wave': 0,
            'attack_skip_counter': 0.0,
            'health_skip_counter': 0.0,
        },
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=True, timing_dirty=True),
    )


def _perk_counts_at_wave(perk_timeline: tuple[dict[str, Any], ...], wave: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in perk_timeline:
        try:
            row_wave = int((row or {}).get('wave') or 0)
        except Exception:
            row_wave = 0
        if row_wave > int(wave):
            continue
        perk_name = str((row or {}).get('perk_taken') or (row or {}).get('perk_name') or '').strip()
        if not perk_name:
            continue
        counts[perk_name] = counts.get(perk_name, 0) + 1
    return counts


def _advance_projected_perk_state(
    projected_state: ProjectedRunState,
    *,
    target_display_wave: int,
    perk_timeline: tuple[dict[str, Any], ...],
) -> ProjectedRunState:
    if not perk_timeline:
        return projected_state
    next_counts = _perk_counts_at_wave(perk_timeline, target_display_wave)
    current_counts = dict(projected_state.perk_state.counts or {})
    next_perk_state = PerkState(
        wave=int(target_display_wave),
        counts=next_counts,
        dirty=next_counts != current_counts,
    )
    next_dirty = DirtyLedger(
        progression_dirty=projected_state.dirty_ledger.progression_dirty,
        qe_dirty=projected_state.dirty_ledger.qe_dirty or next_perk_state.dirty,
        timing_dirty=projected_state.dirty_ledger.timing_dirty or next_perk_state.dirty,
        geometry_dirty=projected_state.dirty_ledger.geometry_dirty,
    )
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(target_display_wave)),
        workshop_levels_current=dict(projected_state.workshop_levels_current),
        perk_state=next_perk_state,
        wave_progression_state=dict(projected_state.wave_progression_state),
        free_upgrade_state=dict(projected_state.free_upgrade_state),
        counters=dict(projected_state.counters),
        dirty_ledger=next_dirty,
        notes=projected_state.notes,
    )


def run_to_max(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot] = resolve_wave_row_snapshot,
) -> RunResult:
    if config.execution_mode != 'table_sweep':
        raise ValueError(
            f"Unsupported run_to_max execution_mode {config.execution_mode!r}. "
            "Supported mode is 'table_sweep'."
        )
    return _run_to_max_table_sweep(
        account_state=account_state,
        initial_projected_state=initial_projected_state,
        config=config,
        row_resolver=row_resolver,
    )


def build_boss_wave_table(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot] = resolve_wave_row_snapshot,
    stop_on_failure: bool = False,
) -> list[dict[str, object]]:
    return build_boss_wave_table_payload(
        account_state=account_state,
        initial_projected_state=initial_projected_state,
        config=config,
        row_resolver=row_resolver,
        stop_on_failure=stop_on_failure,
    )['rows']


def build_boss_wave_table_payload(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot] = resolve_wave_row_snapshot,
    stop_on_failure: bool = False,
) -> dict[str, object]:
    if config.execution_mode != 'table_sweep':
        raise ValueError(
            f"Unsupported build_boss_wave_table execution_mode {config.execution_mode!r}. "
            "Supported mode is 'table_sweep'."
        )

    wave_policy = WaveProgressionPolicy()
    boss_wave_interval = max(1, int(config.boss_wave_step))
    category_track_order = _category_track_order_from_account_state(account_state)
    track_max_levels = _track_max_levels_from_account_state(account_state)
    enemy_damage_table = _load_wave_table(ENEMY_DAMAGE_TABLE)
    enemy_health_table = _load_wave_table(ENEMY_HEALTH_TABLE)
    current_projected_state = _clone_projected_run_state(initial_projected_state)
    current_snapshot = row_resolver(
        _normalized_checkpoint_state_for_projected_state(
            account_state=account_state,
            config=config,
            projected_state=current_projected_state,
        )
    )
    qe_resolution_count = current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
    timing_recompute_count = current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1
    snapshot_reuse_count = 0
    qe_dirty_reresolve_count = 0
    delta_fallback_count = 0
    timing_context = current_snapshot.timing_context
    combat_runtime = current_snapshot.combat_runtime
    hot_values = _extract_hot_surface_values(current_snapshot)
    tower_damage_per_second = _tower_runtime_damage_per_second(current_snapshot)
    rows: list[dict[str, object]] = []
    max_wave = 0
    first_failed_wave = 0
    terminal_snapshot = current_snapshot

    for display_wave in range(int(config.start_wave), int(config.end_wave) + 1, boss_wave_interval):
        current_projected_state = advance_projected_free_upgrade_state(
            current_projected_state,
            target_display_wave=display_wave,
            free_attack_upgrade_chance_pct=float(hot_values.get('state::tower.free_attack_upgrade_chance_pct') or 0.0),
            free_defense_upgrade_chance_pct=float(hot_values.get('state::tower.free_defense_upgrade_chance_pct') or 0.0),
            free_utility_upgrade_chance_pct=float(hot_values.get('state::tower.free_utility_upgrade_chance_pct') or 0.0),
        )
        current_projected_state = advance_projected_wave_state(
            current_projected_state,
            target_display_wave=display_wave,
            attack_skip_pct=float(hot_values.get('state::tower.enemy_attack_level_skip_pct') or 0.0) / 100.0,
            health_skip_pct=float(hot_values.get('state::tower.enemy_health_level_skip_pct') or 0.0) / 100.0,
            policy=wave_policy,
        )
        current_projected_state = allocate_generated_free_upgrades_to_workshop(
            current_projected_state,
            category_track_order=category_track_order,
            track_max_levels=track_max_levels,
        )
        current_projected_state = _advance_projected_perk_state(
            current_projected_state,
            target_display_wave=display_wave,
            perk_timeline=config.perk_timeline,
        )
        changed_tracks = tuple(current_projected_state.counters.get('changed_workshop_tracks_last_step') or ())
        if current_projected_state.dirty_ledger.qe_dirty:
            current_snapshot, delta_fallback_used = _resolve_snapshot_for_projected_state(
                account_state=account_state,
                config=config,
                projected_state=current_projected_state,
                current_snapshot=current_snapshot,
                row_resolver=row_resolver,
                changed_tracks=changed_tracks,
            )
            qe_dirty_reresolve_count += 1
            delta_fallback_count += int(delta_fallback_used)
            qe_resolution_count += current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
            timing_recompute_count += current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1
            timing_context = current_snapshot.timing_context
            combat_runtime = current_snapshot.combat_runtime
            hot_values = _extract_hot_surface_values(current_snapshot)
            tower_damage_per_second = _tower_runtime_damage_per_second(current_snapshot)
        else:
            current_snapshot = _reuse_snapshot_for_projected_state(
                current_snapshot,
                projected_state=current_projected_state,
            )
            snapshot_reuse_count += 1
            timing_context = current_snapshot.timing_context
            combat_runtime = current_snapshot.combat_runtime
            hot_values = _extract_hot_surface_values(current_snapshot)
            tower_damage_per_second = _tower_runtime_damage_per_second(current_snapshot)

        wave_progression_state = current_projected_state.wave_progression_state
        attack_wave = int(wave_progression_state.get('attack_wave', 0))
        health_wave = int(wave_progression_state.get('health_wave', 0))
        wave_attack = _lookup_wave_value(enemy_damage_table, attack_wave, config.tier_column)
        wave_health = _lookup_wave_value(enemy_health_table, health_wave, config.tier_column)
        boss_attack = None if wave_attack is None else float(wave_attack)
        boss_health = None if wave_health is None else float(wave_health) * float(BOSS_HP_MULTIPLIER)
        intake = _evaluate_boss_hot_values_fast(
            hot_values=hot_values,
            tower_damage_per_second=tower_damage_per_second,
            attack_wave=attack_wave,
            health_wave=health_wave,
            config=config,
            timing_context=timing_context,
            combat_runtime=combat_runtime,
            enemy_damage_table=enemy_damage_table,
            enemy_health_table=enemy_health_table,
        )
        survives_boss = bool(intake is not None and intake.survival_margin_hp >= 0.0)
        generated_by_category = dict(current_projected_state.counters.get('generated_free_upgrades_last_step_by_category') or {})
        allocated_by_category = dict(current_projected_state.counters.get('allocated_free_upgrades_by_category') or {})
        rows.append(
            {
                'display_wave': int(display_wave),
                'attack_wave': attack_wave,
                'health_wave': health_wave,
                'wave_attack': None if wave_attack is None else float(wave_attack),
                'wave_health': None if wave_health is None else float(wave_health),
                'boss_attack': boss_attack,
                'boss_health': boss_health,
                'wall_hp': hot_values.get('state::wall.hp'),
                'wall_regen': hot_values.get('state::wall.regen'),
                'wall_fortification_multiplier': hot_values.get('state::wall.fortification_multiplier'),
                'tower_defense_pct': hot_values.get('state::tower.defense_pct'),
                'tower_thorns_damage_pct': hot_values.get('state::tower.thorns_damage_pct'),
                'tower_damage_per_second': tower_damage_per_second,
                'plasma_cannon_effect_pct': hot_values.get('state::cards.plasma_cannon.effect_pct'),
                'effective_damage_reduction_pct_used': combat_runtime.effective_damage_reduction_pct,
                'boss_contact_time_seconds_used': combat_runtime.boss_contact_time_seconds,
                'boss_hit_interval_seconds_used': combat_runtime.boss_hit_interval_seconds,
                'incoming_damage_multiplier_used': combat_runtime.incoming_damage_multiplier,
                'free_attack_upgrade_chance_pct': hot_values.get('state::tower.free_attack_upgrade_chance_pct'),
                'free_defense_upgrade_chance_pct': hot_values.get('state::tower.free_defense_upgrade_chance_pct'),
                'free_utility_upgrade_chance_pct': hot_values.get('state::tower.free_utility_upgrade_chance_pct'),
                'enemy_attack_level_skip_pct': hot_values.get('state::tower.enemy_attack_level_skip_pct'),
                'enemy_health_level_skip_pct': hot_values.get('state::tower.enemy_health_level_skip_pct'),
                'generated_free_upgrades_attack': int(generated_by_category.get('attack', 0) or 0),
                'generated_free_upgrades_defense': int(generated_by_category.get('defense', 0) or 0),
                'generated_free_upgrades_utility': int(generated_by_category.get('utility', 0) or 0),
                'allocated_free_upgrades_attack': int(allocated_by_category.get('attack', 0) or 0),
                'allocated_free_upgrades_defense': int(allocated_by_category.get('defense', 0) or 0),
                'allocated_free_upgrades_utility': int(allocated_by_category.get('utility', 0) or 0),
                'changed_workshop_tracks_last_step': '|'.join(changed_tracks),
                'survives_boss': survives_boss,
                'boss_survival_margin_hp': None if intake is None else float(intake.survival_margin_hp),
                'boss_total_damage_taken': None if intake is None else float(intake.total_damage_taken),
                'boss_hits_taken': None if intake is None else int(intake.boss_hits_taken),
            }
        )
        terminal_snapshot = current_snapshot
        if survives_boss:
            max_wave = int(display_wave)
        elif first_failed_wave == 0:
            first_failed_wave = int(display_wave)
        if stop_on_failure and not survives_boss:
            break

    runtime_inputs = config.scenario_runtime_inputs.to_debug_dict() if config.scenario_runtime_inputs else {}
    terminal_display_wave = int(rows[-1]['display_wave']) if rows else 0
    return {
        'rows': rows,
        'summary': {
            'max_wave': max_wave,
            'max_surviving_wave': max_wave,
            'first_failed_wave': first_failed_wave,
            'row_count': len(rows),
            'terminal_display_wave': terminal_display_wave,
            'survives_through_end': bool(rows) and first_failed_wave == 0,
            'result_consistent_with_rows': max_wave == max((int((row or {}).get('display_wave') or 0) for row in rows if bool((row or {}).get('survives_boss'))), default=0),
        },
        'diagnostics': {
            'execution_mode': config.execution_mode,
            'mode_id': config.mode_id,
            'tier_column': config.tier_column,
            'boss_wave_step': config.boss_wave_step,
            'state_mode': config.state_mode,
            'checkpoint_mode': 'boss_wave_only',
            'checkpoint_resolution_mode': 'per_boss_wave',
            'stop_on_failure': bool(stop_on_failure),
            'scenario_runtime_inputs': runtime_inputs,
            'wave_progression_owner': 'simulators.progression.advance_projected_wave_state',
            'free_upgrade_owner': 'simulators.progression.advance_projected_free_upgrade_state',
            'workshop_allocation_owner': 'simulators.progression.allocate_generated_free_upgrades_to_workshop',
            'perk_timeline_owner': 'simulators.run_executor._advance_projected_perk_state',
            'tower_damage_owner': 'derived::edamage',
            'tower_damage_mode': 'continuous_runtime_dps_proxy',
            'qe_resolution_count': qe_resolution_count,
            'timing_recompute_count': timing_recompute_count,
            'snapshot_reuse_count': snapshot_reuse_count,
            'qe_dirty_reresolve_count': qe_dirty_reresolve_count,
            'delta_fallback_count': delta_fallback_count,
            'execution_architecture': 'table_sweep_hot_columns',
            'terminal_checkpoint_display_wave': terminal_snapshot.checkpoint.display_wave if terminal_snapshot is not None else 0,
        },
    }


def _run_to_max_static_build(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot],
) -> RunResult:
    wave_policy = WaveProgressionPolicy()
    max_wave = 0
    terminal_snapshot: WaveRowSnapshot | None = None
    row_count = 0
    boss_wave_interval = max(1, int(config.boss_wave_step))
    current_projected_state = _clone_projected_run_state(initial_projected_state)
    base_snapshot = row_resolver(
        _normalized_checkpoint_state_for_projected_state(
            account_state=account_state,
            config=config,
            projected_state=ProjectedRunState(
                checkpoint=WaveCheckpoint(display_wave=int(config.start_wave)),
                workshop_levels_current=dict(initial_projected_state.workshop_levels_current),
                perk_state=initial_projected_state.perk_state,
                wave_progression_state=dict(initial_projected_state.wave_progression_state),
                free_upgrade_state=dict(initial_projected_state.free_upgrade_state),
                counters=dict(initial_projected_state.counters),
                dirty_ledger=DirtyLedger(progression_dirty=False, qe_dirty=True, timing_dirty=True),
                notes=initial_projected_state.notes,
            ),
        )
    )
    base_row_map = base_snapshot.resolved_statbook.rows
    base_timing_context = base_snapshot.timing_context
    base_combat_runtime = base_snapshot.combat_runtime

    for display_wave in range(int(config.start_wave), int(config.end_wave) + 1):
        if (display_wave - int(config.start_wave)) % boss_wave_interval != 0:
            continue

        row_count += 1
        attack_skip_pct = _row_float(base_row_map, 'state::tower.enemy_attack_level_skip_pct') or 0.0
        health_skip_pct = _row_float(base_row_map, 'state::tower.enemy_health_level_skip_pct') or 0.0
        current_projected_state = advance_projected_free_upgrade_state(
            current_projected_state,
            target_display_wave=display_wave,
            free_attack_upgrade_chance_pct=_row_float(base_row_map, 'state::tower.free_attack_upgrade_chance_pct') or 0.0,
            free_defense_upgrade_chance_pct=_row_float(base_row_map, 'state::tower.free_defense_upgrade_chance_pct') or 0.0,
            free_utility_upgrade_chance_pct=_row_float(base_row_map, 'state::tower.free_utility_upgrade_chance_pct') or 0.0,
        )
        current_projected_state = advance_projected_wave_state(
            current_projected_state,
            target_display_wave=display_wave,
            attack_skip_pct=float(attack_skip_pct) / 100.0,
            health_skip_pct=float(health_skip_pct) / 100.0,
            policy=wave_policy,
        )
        current_projected_state = _advance_projected_perk_state(
            current_projected_state,
            target_display_wave=display_wave,
            perk_timeline=config.perk_timeline,
        )
        wave_state = WaveProgressionState(
            display_wave=int(current_projected_state.wave_progression_state.get('display_wave', display_wave)),
            attack_wave=int(current_projected_state.wave_progression_state.get('attack_wave', 0)),
            health_wave=int(current_projected_state.wave_progression_state.get('health_wave', 0)),
            attack_skip_counter=float(current_projected_state.wave_progression_state.get('attack_skip_counter', 0.0)),
            health_skip_counter=float(current_projected_state.wave_progression_state.get('health_skip_counter', 0.0)),
        )

        intake = _evaluate_boss_row(
            snapshot=base_snapshot,
            wave_state=wave_state,
            config=config,
            timing_context=base_timing_context,
            combat_runtime=base_combat_runtime,
            row_map=base_row_map,
        )
        terminal_snapshot = base_snapshot
        if intake is None or intake.survival_margin_hp < 0.0:
            break
        max_wave = display_wave

    return RunResult(
        max_wave=max_wave,
        row_count=row_count,
        terminal_checkpoint=None if terminal_snapshot is None else terminal_snapshot.checkpoint,
        terminal_snapshot=terminal_snapshot,
        diagnostics={
            'execution_mode': config.execution_mode,
            'mode_id': config.mode_id,
            'tier_column': config.tier_column,
            'boss_wave_step': config.boss_wave_step,
            'wave_progression_owner': 'simulators.progression.advance_projected_wave_state',
            'free_upgrade_owner': 'simulators.progression.advance_projected_free_upgrade_state',
            'warm_path_required': True,
        },
    )


def _run_to_max_progression_mutating(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot],
) -> RunResult:
    wave_policy = WaveProgressionPolicy()
    max_wave = 0
    terminal_snapshot: WaveRowSnapshot | None = None
    row_count = 0
    qe_resolution_count = 0
    timing_recompute_count = 0
    snapshot_reuse_count = 0
    qe_dirty_reresolve_count = 0
    delta_fallback_count = 0
    boss_wave_interval = max(1, int(config.boss_wave_step))
    category_track_order = _category_track_order_from_account_state(account_state)
    track_max_levels = _track_max_levels_from_account_state(account_state)
    enemy_damage_table = _load_wave_table(ENEMY_DAMAGE_TABLE)
    enemy_health_table = _load_wave_table(ENEMY_HEALTH_TABLE)
    current_projected_state = _clone_projected_run_state(initial_projected_state)
    baseline_key = _baseline_snapshot_cache_key(
        account_state=account_state,
        config=config,
        projected_state=current_projected_state,
    )
    current_snapshot = _BASELINE_SNAPSHOT_CACHE.get(baseline_key)
    if current_snapshot is None:
        current_snapshot = row_resolver(
            _normalized_checkpoint_state_for_projected_state(
                account_state=account_state,
                config=config,
                projected_state=current_projected_state,
            )
        )
        _BASELINE_SNAPSHOT_CACHE[baseline_key] = current_snapshot
    qe_resolution_count += current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
    timing_recompute_count += current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1

    for display_wave in range(int(config.start_wave), int(config.end_wave) + 1):
        if (display_wave - int(config.start_wave)) % boss_wave_interval != 0:
            continue

        row_count += 1
        row_map = current_snapshot.resolved_statbook.rows
        current_projected_state = advance_projected_free_upgrade_state(
            current_projected_state,
            target_display_wave=display_wave,
            free_attack_upgrade_chance_pct=_row_float(row_map, 'state::tower.free_attack_upgrade_chance_pct') or 0.0,
            free_defense_upgrade_chance_pct=_row_float(row_map, 'state::tower.free_defense_upgrade_chance_pct') or 0.0,
            free_utility_upgrade_chance_pct=_row_float(row_map, 'state::tower.free_utility_upgrade_chance_pct') or 0.0,
        )
        current_projected_state = advance_projected_wave_state(
            current_projected_state,
            target_display_wave=display_wave,
            attack_skip_pct=float(_row_float(row_map, 'state::tower.enemy_attack_level_skip_pct') or 0.0) / 100.0,
            health_skip_pct=float(_row_float(row_map, 'state::tower.enemy_health_level_skip_pct') or 0.0) / 100.0,
            policy=wave_policy,
        )
        current_projected_state = allocate_generated_free_upgrades_to_workshop(
            current_projected_state,
            category_track_order=category_track_order,
            track_max_levels=track_max_levels,
        )
        current_projected_state = _advance_projected_perk_state(
            current_projected_state,
            target_display_wave=display_wave,
            perk_timeline=config.perk_timeline,
        )
        changed_tracks = tuple(current_projected_state.counters.get('changed_workshop_tracks_last_step') or ())
        if current_projected_state.dirty_ledger.qe_dirty:
            current_snapshot, delta_fallback_used = _resolve_snapshot_for_projected_state(
                account_state=account_state,
                config=config,
                projected_state=current_projected_state,
                current_snapshot=current_snapshot,
                row_resolver=row_resolver,
                changed_tracks=changed_tracks,
            )
            qe_dirty_reresolve_count += 1
            delta_fallback_count += int(delta_fallback_used)
            qe_resolution_count += current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
            timing_recompute_count += current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1
        else:
            current_snapshot = _reuse_snapshot_for_projected_state(
                current_snapshot,
                projected_state=current_projected_state,
            )
            snapshot_reuse_count += 1
        terminal_snapshot = current_snapshot
        intake = _evaluate_boss_row(
            snapshot=current_snapshot,
            wave_state=WaveProgressionState(
                display_wave=int(current_projected_state.wave_progression_state.get('display_wave', display_wave)),
                attack_wave=int(current_projected_state.wave_progression_state.get('attack_wave', 0)),
                health_wave=int(current_projected_state.wave_progression_state.get('health_wave', 0)),
                attack_skip_counter=float(current_projected_state.wave_progression_state.get('attack_skip_counter', 0.0)),
                health_skip_counter=float(current_projected_state.wave_progression_state.get('health_skip_counter', 0.0)),
            ),
            config=config,
            timing_context=current_snapshot.timing_context,
            combat_runtime=current_snapshot.combat_runtime,
            row_map=current_snapshot.resolved_statbook.rows,
        )
        if intake is None or intake.survival_margin_hp < 0.0:
            break
        max_wave = display_wave

    return RunResult(
        max_wave=max_wave,
        row_count=row_count,
        terminal_checkpoint=None if terminal_snapshot is None else terminal_snapshot.checkpoint,
        terminal_snapshot=terminal_snapshot,
        diagnostics={
            'execution_mode': config.execution_mode,
            'mode_id': config.mode_id,
            'tier_column': config.tier_column,
            'boss_wave_step': config.boss_wave_step,
            'wave_progression_owner': 'simulators.progression.advance_projected_wave_state',
            'free_upgrade_owner': 'simulators.progression.advance_projected_free_upgrade_state',
            'workshop_allocation_owner': 'simulators.progression.allocate_generated_free_upgrades_to_workshop',
            'perk_timeline_owner': 'simulators.run_executor._advance_projected_perk_state',
            'tower_damage_owner': 'derived::edamage',
            'tower_damage_mode': 'continuous_runtime_dps_proxy',
            'qe_resolution_count': qe_resolution_count,
            'timing_recompute_count': timing_recompute_count,
            'snapshot_reuse_count': snapshot_reuse_count,
            'qe_dirty_reresolve_count': qe_dirty_reresolve_count,
            'delta_fallback_count': delta_fallback_count,
            'checkpoint_resolution_mode': 'per_boss_wave',
        },
    )


def _run_to_max_table_sweep(
    *,
    account_state: AccountState,
    initial_projected_state: ProjectedRunState,
    config: RunToMaxConfig,
    row_resolver: Callable[[NormalizedCheckpointState], WaveRowSnapshot],
) -> RunResult:
    wave_policy = WaveProgressionPolicy()
    max_wave = 0
    row_count = 0
    qe_resolution_count = 0
    timing_recompute_count = 0
    snapshot_reuse_count = 0
    qe_dirty_reresolve_count = 0
    delta_fallback_count = 0
    boss_wave_interval = max(1, int(config.boss_wave_step))
    category_track_order = _category_track_order_from_account_state(account_state)
    track_max_levels = _track_max_levels_from_account_state(account_state)
    enemy_damage_table = _load_wave_table(ENEMY_DAMAGE_TABLE)
    enemy_health_table = _load_wave_table(ENEMY_HEALTH_TABLE)
    current_projected_state = _clone_projected_run_state(initial_projected_state)
    current_snapshot = row_resolver(
        _normalized_checkpoint_state_for_projected_state(
            account_state=account_state,
            config=config,
            projected_state=current_projected_state,
        )
    )
    qe_resolution_count += current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
    timing_recompute_count += current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1
    timing_context = current_snapshot.timing_context
    combat_runtime = current_snapshot.combat_runtime
    hot_values = _extract_hot_surface_values(current_snapshot)

    for display_wave in range(int(config.start_wave), int(config.end_wave) + 1, boss_wave_interval):
        row_count += 1
        current_projected_state = advance_projected_free_upgrade_state(
            current_projected_state,
            target_display_wave=display_wave,
            free_attack_upgrade_chance_pct=float(hot_values.get('state::tower.free_attack_upgrade_chance_pct') or 0.0),
            free_defense_upgrade_chance_pct=float(hot_values.get('state::tower.free_defense_upgrade_chance_pct') or 0.0),
            free_utility_upgrade_chance_pct=float(hot_values.get('state::tower.free_utility_upgrade_chance_pct') or 0.0),
        )
        current_projected_state = advance_projected_wave_state(
            current_projected_state,
            target_display_wave=display_wave,
            attack_skip_pct=float(hot_values.get('state::tower.enemy_attack_level_skip_pct') or 0.0) / 100.0,
            health_skip_pct=float(hot_values.get('state::tower.enemy_health_level_skip_pct') or 0.0) / 100.0,
            policy=wave_policy,
        )
        current_projected_state = allocate_generated_free_upgrades_to_workshop(
            current_projected_state,
            category_track_order=category_track_order,
            track_max_levels=track_max_levels,
        )
        current_projected_state = _advance_projected_perk_state(
            current_projected_state,
            target_display_wave=display_wave,
            perk_timeline=config.perk_timeline,
        )
        changed_tracks = tuple(current_projected_state.counters.get('changed_workshop_tracks_last_step') or ())
        if current_projected_state.dirty_ledger.qe_dirty:
            current_snapshot, delta_fallback_used = _resolve_snapshot_for_projected_state(
                account_state=account_state,
                config=config,
                projected_state=current_projected_state,
                current_snapshot=current_snapshot,
                row_resolver=row_resolver,
                changed_tracks=changed_tracks,
            )
            qe_dirty_reresolve_count += 1
            delta_fallback_count += int(delta_fallback_used)
            qe_resolution_count += current_snapshot.metrics.qe_resolution_count if current_snapshot.metrics else 1
            timing_recompute_count += current_snapshot.metrics.timing_recompute_count if current_snapshot.metrics else 1
        else:
            current_snapshot = _reuse_snapshot_for_projected_state(
                current_snapshot,
                projected_state=current_projected_state,
            )
            snapshot_reuse_count += 1
        timing_context = current_snapshot.timing_context
        combat_runtime = current_snapshot.combat_runtime
        hot_values = _extract_hot_surface_values(current_snapshot)
        tower_damage_per_second = _tower_runtime_damage_per_second(current_snapshot)
        wave_progression_state = current_projected_state.wave_progression_state
        intake = _evaluate_boss_hot_values_fast(
            hot_values=hot_values,
            tower_damage_per_second=tower_damage_per_second,
            attack_wave=int(wave_progression_state.get('attack_wave', 0)),
            health_wave=int(wave_progression_state.get('health_wave', 0)),
            config=config,
            timing_context=timing_context,
            combat_runtime=combat_runtime,
            enemy_damage_table=enemy_damage_table,
            enemy_health_table=enemy_health_table,
        )
        if intake is None or intake.survival_margin_hp < 0.0:
            break
        max_wave = display_wave

    terminal_snapshot = _reuse_snapshot_for_projected_state(
        current_snapshot,
        projected_state=current_projected_state,
    )
    return RunResult(
        max_wave=max_wave,
        row_count=row_count,
        terminal_checkpoint=terminal_snapshot.checkpoint,
        terminal_snapshot=terminal_snapshot,
        diagnostics={
            'execution_mode': config.execution_mode,
            'mode_id': config.mode_id,
            'tier_column': config.tier_column,
            'boss_wave_step': config.boss_wave_step,
            'wave_progression_owner': 'simulators.progression.advance_projected_wave_state',
            'free_upgrade_owner': 'simulators.progression.advance_projected_free_upgrade_state',
            'workshop_allocation_owner': 'simulators.progression.allocate_generated_free_upgrades_to_workshop',
            'perk_timeline_owner': 'simulators.run_executor._advance_projected_perk_state',
            'qe_resolution_count': qe_resolution_count,
            'timing_recompute_count': timing_recompute_count,
            'snapshot_reuse_count': snapshot_reuse_count,
            'qe_dirty_reresolve_count': qe_dirty_reresolve_count,
            'delta_fallback_count': delta_fallback_count,
            'checkpoint_resolution_mode': 'per_boss_wave',
            'execution_architecture': 'table_sweep_hot_columns',
        },
    )


def _clone_projected_run_state(state: ProjectedRunState) -> ProjectedRunState:
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(state.checkpoint.display_wave)),
        workshop_levels_current=dict(state.workshop_levels_current),
        perk_state=state.perk_state,
        wave_progression_state=dict(state.wave_progression_state),
        free_upgrade_state=dict(state.free_upgrade_state),
        counters=dict(state.counters),
        dirty_ledger=state.dirty_ledger,
        notes=state.notes,
    )


def _baseline_snapshot_cache_key(
    *,
    account_state: AccountState,
    config: RunToMaxConfig,
    projected_state: ProjectedRunState,
) -> tuple[object, ...]:
    perk_counts = tuple(sorted((projected_state.perk_state.counts or {}).items()))
    workshop_levels = tuple(sorted(projected_state.workshop_levels_current.items()))
    runtime_inputs = None if config.scenario_runtime_inputs is None else repr(config.scenario_runtime_inputs)
    return (
        id(account_state),
        config.preset_name,
        config.mode_id,
        config.state_mode,
        bool(config.perks_enabled),
        runtime_inputs,
        int(projected_state.checkpoint.display_wave),
        perk_counts,
        workshop_levels,
    )


def _normalized_checkpoint_state_for_projected_state(
    *,
    account_state: AccountState,
    config: RunToMaxConfig,
    projected_state: ProjectedRunState,
) -> NormalizedCheckpointState:
    return NormalizedCheckpointState(
        checkpoint=WaveCheckpoint(display_wave=int(projected_state.checkpoint.display_wave)),
        account_state=account_state,
        preset_name=config.preset_name,
        projected_run_state=projected_state,
        state_mode=config.state_mode,
        perks_enabled=config.perks_enabled,
        mode_id=config.mode_id,
        scenario_runtime_inputs=config.scenario_runtime_inputs,
    )


def _reuse_snapshot_for_projected_state(
    snapshot: WaveRowSnapshot,
    *,
    projected_state: ProjectedRunState,
) -> WaveRowSnapshot:
    return WaveRowSnapshot(
        checkpoint=WaveCheckpoint(display_wave=int(projected_state.checkpoint.display_wave)),
        projected_run_state=projected_state,
        resolved_statbook=snapshot.resolved_statbook,
        scenario_context=snapshot.scenario_context,
        timing_context=snapshot.timing_context,
        geometry_context=dict(snapshot.geometry_context),
        combat_runtime=snapshot.combat_runtime,
        metrics=snapshot.metrics,
    )



def _category_track_order_from_account_state(account_state: AccountState) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {'attack': [], 'defense': [], 'utility': []}
    for track_name, entry in account_state.workshop.items():
        if entry.max_level is None:
            continue
        category = _WORKSHOP_TRACK_CATEGORY_BY_NAME.get(track_name)
        if category is None:
            continue
        grouped[category].append(track_name)
    return {category: tuple(names) for category, names in grouped.items()}


def _track_max_levels_from_account_state(account_state: AccountState) -> dict[str, int]:
    return {
        track_name: int(entry.max_level)
        for track_name, entry in account_state.workshop.items()
        if entry.max_level is not None
    }


def _evaluate_boss_row(
    *,
    snapshot: WaveRowSnapshot,
    wave_state: WaveProgressionState,
    config: RunToMaxConfig,
    timing_context,
    combat_runtime,
    row_map: Dict[str, object],
) -> Optional[BossDamageIntakeResult]:
    boss_base_damage = _lookup_wave_value(_load_wave_table(ENEMY_DAMAGE_TABLE), wave_state.attack_wave, config.tier_column)
    common_hp = _lookup_wave_value(_load_wave_table(ENEMY_HEALTH_TABLE), wave_state.health_wave, config.tier_column)
    if boss_base_damage is None or common_hp is None:
        return None
    if combat_runtime is None:
        return None

    tower_thorns_damage_pct = _row_float(row_map, 'state::tower.thorns_damage_pct') or 0.0
    plasma_cannon_effect_pct = _row_float(row_map, 'state::cards.plasma_cannon.effect_pct') or 0.0
    boss_effective_hp = float(common_hp) * float(BOSS_HP_MULTIPLIER)
    ttk = _simulate_boss_ttk(
        boss_effective_hp=boss_effective_hp,
        plasma_cannon_effect_pct=plasma_cannon_effect_pct,
        tower_thorns_damage_pct=tower_thorns_damage_pct,
        combat_runtime=combat_runtime,
        config=config,
    )
    if ttk is None:
        return None

    return _simulate_boss_damage_intake(
        boss_base_damage=float(boss_base_damage),
        ttk_seconds=ttk.ttk_seconds,
        wall_hp=_row_float(row_map, 'state::wall.hp'),
        wall_regen=_row_float(row_map, 'state::wall.regen'),
        wall_fortification_multiplier=_row_float(row_map, 'state::wall.fortification_multiplier'),
        tower_defense_pct=_row_float(row_map, 'state::tower.defense_pct'),
        combat_runtime=combat_runtime,
        timing_context=timing_context,
        config=config,
    )


def _row_float(row_map: Dict[str, object], surface_id: str) -> Optional[float]:
    row = row_map.get(surface_id)
    if row is None or getattr(row, 'final_value', None) is None:
        return None
    try:
        return float(row.final_value)
    except (TypeError, ValueError):
        return None


def _extract_hot_surface_values(snapshot: WaveRowSnapshot) -> dict[str, Optional[float]]:
    row_map = snapshot.resolved_statbook.rows
    return {surface_id: _row_float(row_map, surface_id) for surface_id in _boss_wave_hot_surface_ids()}


def _tower_runtime_damage_per_second(snapshot: WaveRowSnapshot) -> float:
    try:
        return float(compute_derived_edamage(snapshot.resolved_statbook.rows) or 0.0)
    except Exception:
        return 0.0


def _evaluate_boss_hot_values(
    *,
    hot_values: dict[str, Optional[float]],
    tower_damage_per_second: float,
    wave_state: WaveProgressionState,
    config: RunToMaxConfig,
    timing_context,
    combat_runtime,
) -> Optional[BossDamageIntakeResult]:
    boss_base_damage = _lookup_wave_value(_load_wave_table(ENEMY_DAMAGE_TABLE), wave_state.attack_wave, config.tier_column)
    common_hp = _lookup_wave_value(_load_wave_table(ENEMY_HEALTH_TABLE), wave_state.health_wave, config.tier_column)
    if boss_base_damage is None or common_hp is None or combat_runtime is None:
        return None
    tower_thorns_damage_pct = float(hot_values.get('state::tower.thorns_damage_pct') or 0.0)
    plasma_cannon_effect_pct = float(hot_values.get('state::cards.plasma_cannon.effect_pct') or 0.0)
    boss_effective_hp = float(common_hp) * float(BOSS_HP_MULTIPLIER)
    ttk = _simulate_boss_ttk(
        boss_effective_hp=boss_effective_hp,
        tower_damage_per_second=tower_damage_per_second,
        plasma_cannon_effect_pct=plasma_cannon_effect_pct,
        tower_thorns_damage_pct=tower_thorns_damage_pct,
        combat_runtime=combat_runtime,
        config=config,
    )
    if ttk is None:
        return None
    return _simulate_boss_damage_intake(
        boss_base_damage=float(boss_base_damage),
        ttk_seconds=ttk.ttk_seconds,
        wall_hp=hot_values.get('state::wall.hp'),
        wall_regen=hot_values.get('state::wall.regen'),
        wall_fortification_multiplier=hot_values.get('state::wall.fortification_multiplier'),
        tower_defense_pct=hot_values.get('state::tower.defense_pct'),
        combat_runtime=combat_runtime,
        timing_context=timing_context,
        config=config,
    )


def _evaluate_boss_hot_values_fast(
    *,
    hot_values: dict[str, Optional[float]],
    tower_damage_per_second: float,
    attack_wave: int,
    health_wave: int,
    config: RunToMaxConfig,
    timing_context,
    combat_runtime,
    enemy_damage_table: Dict[int, Dict[str, float]],
    enemy_health_table: Dict[int, Dict[str, float]],
) -> Optional[BossDamageIntakeResult]:
    boss_base_damage = _lookup_wave_value(enemy_damage_table, attack_wave, config.tier_column)
    common_hp = _lookup_wave_value(enemy_health_table, health_wave, config.tier_column)
    if boss_base_damage is None or common_hp is None or combat_runtime is None:
        return None
    tower_thorns_damage_pct = float(hot_values.get('state::tower.thorns_damage_pct') or 0.0)
    plasma_cannon_effect_pct = float(hot_values.get('state::cards.plasma_cannon.effect_pct') or 0.0)
    boss_effective_hp = float(common_hp) * float(BOSS_HP_MULTIPLIER)
    ttk = _simulate_boss_ttk(
        boss_effective_hp=boss_effective_hp,
        tower_damage_per_second=tower_damage_per_second,
        plasma_cannon_effect_pct=plasma_cannon_effect_pct,
        tower_thorns_damage_pct=tower_thorns_damage_pct,
        combat_runtime=combat_runtime,
        config=config,
    )
    if ttk is None:
        return None
    return _simulate_boss_damage_intake(
        boss_base_damage=float(boss_base_damage),
        ttk_seconds=ttk.ttk_seconds,
        wall_hp=hot_values.get('state::wall.hp'),
        wall_regen=hot_values.get('state::wall.regen'),
        wall_fortification_multiplier=hot_values.get('state::wall.fortification_multiplier'),
        tower_defense_pct=hot_values.get('state::tower.defense_pct'),
        combat_runtime=combat_runtime,
        timing_context=timing_context,
        config=config,
    )


@lru_cache(maxsize=2)
def _load_wave_table(path: Path) -> Dict[int, Dict[str, float]]:
    out: Dict[int, Dict[str, float]] = {}
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            try:
                wave = int(float(row['wave_actual']))
            except (TypeError, ValueError, KeyError):
                continue
            out[wave] = {}
            for key, value in row.items():
                if key == 'wave_actual':
                    continue
                try:
                    out[wave][key] = float(value)
                except (TypeError, ValueError):
                    continue
    return out


def _lookup_wave_value(table: Dict[int, Dict[str, float]], wave: int, column: str) -> Optional[float]:
    if wave in table and column in table[wave]:
        return table[wave][column]
    eligible = [key for key in table.keys() if key <= wave]
    if not eligible:
        return None
    return table[max(eligible)].get(column)


def _simulate_boss_ttk(
    *,
    boss_effective_hp: float,
    tower_damage_per_second: float,
    plasma_cannon_effect_pct: float,
    tower_thorns_damage_pct: float,
    combat_runtime,
    config: RunToMaxConfig,
) -> Optional[BossTTKResult]:
    if (
        combat_runtime.orb_boss_hit_pct is None
        or combat_runtime.orb_boss_hits_per_second is None
        or combat_runtime.electron_hits_per_second is None
    ):
        return None
    pc_pct = max(0.0, min(100.0, plasma_cannon_effect_pct)) / 100.0
    pc_pct *= config.plasma_cannon_resistance_multiplier
    remaining_hp = boss_effective_hp * max(0.0, 1.0 - pc_pct)
    if remaining_hp <= KILL_HP_THRESHOLD:
        return BossTTKResult(ttk_seconds=0.0)

    orb_pct = max(0.0, float(combat_runtime.orb_boss_hit_pct)) / 100.0
    orb_pct *= config.orb_resistance_multiplier
    electron_pct = ELECTRON_BOSS_REMAINING_HP_PCT
    orb_interval = 1.0 / float(combat_runtime.orb_boss_hits_per_second)
    electron_interval = 1.0 / float(combat_runtime.electron_hits_per_second)
    next_orb = orb_interval
    next_electron = electron_interval
    next_contact = inf
    if combat_runtime.boss_contact_time_seconds is not None:
        next_contact = float(combat_runtime.boss_contact_time_seconds)
    thorns_pct = max(0.0, tower_thorns_damage_pct) / 100.0
    thorns_pct *= THORNS_BOSS_EFFECTIVENESS
    thorns_pct *= config.thorns_resistance_multiplier
    tower_dps = max(0.0, float(tower_damage_per_second or 0.0))
    t = 0.0
    while remaining_hp > KILL_HP_THRESHOLD:
        next_t = min(next_orb, next_electron, next_contact)
        if not isfinite(next_t):
            if tower_dps <= 0.0:
                return None
            kill_time = remaining_hp / tower_dps
            if t + kill_time > float(config.max_ttk_seconds):
                return None
            return BossTTKResult(ttk_seconds=t + kill_time)
        if next_t > float(config.max_ttk_seconds):
            return None
        delta_t = max(0.0, next_t - t)
        if tower_dps > 0.0 and delta_t > 0.0:
            tower_damage = tower_dps * delta_t
            if tower_damage >= remaining_hp:
                return BossTTKResult(ttk_seconds=t + (remaining_hp / tower_dps))
            remaining_hp -= tower_damage
        t = next_t
        if abs(next_orb - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - orb_pct)
            next_orb += orb_interval
        if remaining_hp <= 0:
            break
        if abs(next_electron - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - electron_pct)
            next_electron += electron_interval
        if remaining_hp <= 0:
            break
        if abs(next_contact - t) <= 1e-12:
            remaining_hp *= max(0.0, 1.0 - thorns_pct)
            next_contact += float(combat_runtime.boss_hit_interval_seconds)
    return BossTTKResult(ttk_seconds=t)


def _simulate_boss_damage_intake(
    *,
    boss_base_damage: float,
    ttk_seconds: float,
    wall_hp: Optional[float],
    wall_regen: Optional[float],
    wall_fortification_multiplier: Optional[float],
    tower_defense_pct: Optional[float],
    combat_runtime,
    timing_context,
    config: RunToMaxConfig,
) -> Optional[BossDamageIntakeResult]:
    if wall_hp is None or wall_regen is None or wall_fortification_multiplier is None:
        return None
    dr_pct = combat_runtime.effective_damage_reduction_pct
    if dr_pct is None:
        base_dr_fraction = 0.0 if tower_defense_pct is None else max(0.0, min(100.0, float(tower_defense_pct))) / 100.0
        encounter_timed_dr_fraction = 0.0
        if combat_runtime.boss_contact_time_seconds is not None and ttk_seconds > combat_runtime.boss_contact_time_seconds:
            encounter_timed_dr_fraction = compute_average_damage_reduction_fraction_over_interval(
                timing_context,
                combat_runtime.boss_contact_time_seconds,
                ttk_seconds,
            )
        dr_pct = (1.0 - ((1.0 - base_dr_fraction) * (1.0 - encounter_timed_dr_fraction))) * 100.0
    dr_fraction = max(0.0, min(100.0, float(dr_pct))) / 100.0
    if combat_runtime.boss_contact_time_seconds is None:
        survival_margin_hp = wall_hp * wall_fortification_multiplier + max(0.0, wall_regen * ttk_seconds)
        return BossDamageIntakeResult(
            survival_margin_hp=survival_margin_hp,
            total_damage_taken=0.0,
            boss_hits_taken=0,
        )

    hit_t = float(combat_runtime.boss_contact_time_seconds)
    interval = float(combat_runtime.boss_hit_interval_seconds)
    if interval <= 0:
        return None
    total_damage_taken = 0.0
    hits = 0
    while hit_t <= ttk_seconds + 1e-12:
        heat_multiplier = 1.0 + BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT * hits
        incoming_damage_multiplier = (
            combat_runtime.incoming_damage_multiplier
            if combat_runtime.incoming_damage_multiplier is not None
            else float(config.incoming_damage_multiplier_override)
        )
        damage = float(boss_base_damage) * float(incoming_damage_multiplier) * heat_multiplier
        damage *= max(0.0, 1.0 - dr_fraction)
        total_damage_taken += damage
        hits += 1
        hit_t += interval
    wall_pool = wall_hp * wall_fortification_multiplier
    wall_regen_gained = max(0.0, wall_regen * ttk_seconds)
    return BossDamageIntakeResult(
        survival_margin_hp=wall_pool + wall_regen_gained - total_damage_taken,
        total_damage_taken=total_damage_taken,
        boss_hits_taken=hits,
    )
