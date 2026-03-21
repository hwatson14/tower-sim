from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from math import inf, isfinite
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.free_upgrade_generation_policy import FreeUpgradeGenerationPolicy, FreeUpgradeGenerationState
from engine.perk_timeline_state import perk_counts_at_wave
from engine.progression_recalc_bridge import ProgressionRecalcBridge, ProgressionRecalcRequest, ProgressionRecalcResult
from engine.scenario_engine import ScenarioConfig, ScenarioSurfaces, config_from_statbook, compute_scenario_surfaces
from engine.scenario_runtime_inputs import ScenarioRuntimeInputs
from engine.timing_engine import TimingSurfaces, compute_average_damage_reduction_fraction_over_interval, compute_timing_surfaces, resolve_combat_runtime_surfaces
from engine.progression_state import ProgressionInitState, WorkshopTrackState
from engine.workshop_progression_policy import AppliedWorkshopUpgrade, WorkshopProgressionPolicy, WorkshopUpgradeEvent
from engine.wave_progression_policy import WaveProgressionPolicy, WaveProgressionPolicyConfig, WaveProgressionState
from models.account_state import AccountState

ROOT = Path(__file__).resolve().parents[1]
ENEMY_DAMAGE_TABLE = ROOT / 'kb' / 'enemies' / 'tables' / 'enemy-damage-table.csv'
ENEMY_HEALTH_TABLE = ROOT / 'kb' / 'enemies' / 'tables' / 'enemy-health-table.csv'
BOSS_HP_MULTIPLIER = 20.0
ELECTRON_BOSS_REMAINING_HP_PCT = 0.15 * 0.25
THORNS_BOSS_EFFECTIVENESS = 0.5
KILL_HP_THRESHOLD = 1.0
BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT = 0.04


@dataclass(frozen=True)
class BossWaveEngineConfig:
    preset_name: str
    mode_id: str
    tier_column: str
    start_boss_wave: int = 10
    end_boss_wave: int = 100
    boss_wave_step: int = 10
    perks_enabled: bool = True
    perk_preset_name: Optional[str] = None
    card_preset_name: Optional[str] = None
    module_preset_name: Optional[str] = None
    league: Optional[str] = None
    tournament_wave: Optional[int] = None
    boss_hit_interval_seconds: float = 2.0
    boss_contact_time_seconds_override: Optional[float] = None
    orb_boss_hit_pct_override: Optional[float] = None
    orb_boss_hits_per_second_override: Optional[float] = None
    electron_hits_per_second_override: Optional[float] = None
    plasma_cannon_resistance_multiplier: float = 1.0
    orb_resistance_multiplier: float = 1.0
    thorns_resistance_multiplier: float = 1.0
    max_ttk_seconds: float = 120.0
    workshop_progression_events: Optional[List[WorkshopUpgradeEvent]] = None
    effective_damage_reduction_pct_override: Optional[float] = None
    incoming_damage_multiplier_override: float = 1.0
    scenario_runtime_inputs: Optional[ScenarioRuntimeInputs | Dict[str, float]] = None
    enemy_skip_warmup_waves: int = 0


@dataclass(frozen=True)
class ResolvedRuntimeInputs:
    boss_hit_interval_seconds: float
    boss_contact_time_seconds: Optional[float]
    orb_boss_hit_pct: Optional[float]
    orb_boss_hits_per_second: Optional[float]
    electron_hits_per_second: Optional[float]
    effective_damage_reduction_pct: Optional[float]
    incoming_damage_multiplier: Optional[float]
    source_notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProgressionRuntimeContext:
    scenario: ScenarioSurfaces
    timing: TimingSurfaces


@dataclass(frozen=True)
class ProgressionFixedInputs:
    boss_wave_interval: int
    enemy_level_skip_reduction_pp: float = 0.0
    source_notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProgressionSnapshot:
    display_wave: int
    perk_counts: Dict[str, int]
    row_map: Dict[str, Any]
    wave_progression_state: WaveProgressionState
    total_generated_free_upgrades: int
    total_explicit_workshop_events: int
    free_upgrade_notes: List[str] = field(default_factory=list)
    explicit_applied_count: int = 0
    generated_free_event_count: int = 0


@dataclass(frozen=True)
class BossWaveRunBatchResult:
    runs: List[BossWaveRunResult]
    diagnostics: Dict[str, Any]


@dataclass(frozen=True)
class BossWaveRow:
    boss_wave: int
    attack_wave: int
    health_wave: int
    boss_base_damage: Optional[float]
    boss_base_hp_common_reference: Optional[float]
    boss_effective_hp: Optional[float]
    boss_ttk_seconds: Optional[float]
    boss_contact_time_seconds: Optional[float]
    thorns_contact_events_used: int
    boss_hits_taken: Optional[int]
    boss_total_damage_taken: Optional[float]
    wall_hp: Optional[float]
    wall_regen: Optional[float]
    wall_fortification_multiplier: Optional[float]
    effective_wall_hp_pool: Optional[float]
    wall_regen_gained_during_ttk: Optional[float]
    wall_hp_after_boss: Optional[float]
    survival_margin_hp: Optional[float]
    damage_reduction_pct_used: Optional[float]
    plasma_cannon_effect_pct: Optional[float]
    orb_count: Optional[float]
    orb_speed_rpm: Optional[float]
    electron_count: Optional[float]
    tower_thorns_damage_pct: Optional[float]
    active_perk_count: int
    status: str
    block_reason: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BossWaveRunResult:
    rows: List[BossWaveRow]
    diagnostics: Dict[str, Any]


@dataclass(frozen=True)
class BossTTKResult:
    boss_effective_hp: float
    remaining_hp_after_opening: float
    ttk_seconds: float
    thorns_contact_events_used: int
    orb_hits_used: int
    electron_hits_used: int


@dataclass(frozen=True)
class BossDamageIntakeResult:
    boss_hits_taken: int
    total_damage_taken: float
    wall_regen_gained: float
    effective_wall_hp_pool: float
    wall_hp_after_boss: float
    survival_margin_hp: float
    damage_reduction_pct_used: float


class BossWaveEngine:
    """Controlled v1 progression scaffold.

    This engine intentionally stops short of claiming final boss-runtime closure.
    It builds per-boss-wave stat snapshots using real stat-engine recompute and
    supports a TTK slice only when all required explicit runtime overrides are provided.
    Damage intake uses the verified +4% per-hit boss heat-up rule and currently relies
    on baseline tower defense pct unless a stronger external effective DR override is supplied.
    """

    def __init__(
        self,
        recalc_bridge: Optional[ProgressionRecalcBridge] = None,
        workshop_policy: Optional[WorkshopProgressionPolicy] = None,
        wave_progression_policy: Optional[WaveProgressionPolicy] = None,
        free_upgrade_policy: Optional[FreeUpgradeGenerationPolicy] = None,
    ) -> None:
        self._bridge = recalc_bridge or ProgressionRecalcBridge()
        self._workshop_policy = workshop_policy or WorkshopProgressionPolicy()
        self._wave_progression_policy = wave_progression_policy or WaveProgressionPolicy()
        self._free_upgrade_policy = free_upgrade_policy or FreeUpgradeGenerationPolicy()
        self._enemy_damage = self._load_wave_table(ENEMY_DAMAGE_TABLE)
        self._enemy_health = self._load_wave_table(ENEMY_HEALTH_TABLE)

    def run(
        self,
        *,
        account_state: AccountState,
        init_state: ProgressionInitState,
        config: BossWaveEngineConfig,
    ) -> BossWaveRunResult:
        fixed_inputs = self._resolve_progression_fixed_inputs(
            account_state=account_state,
            init_state=init_state,
            config=config,
        )
        return self._run_from_snapshots(
            account_state=account_state,
            init_state=init_state,
            config=config,
            snapshots=self._build_progression_snapshots(
                account_state=account_state,
                init_state=init_state,
                config=config,
                fixed_inputs=fixed_inputs,
            ),
            fixed_inputs=fixed_inputs,
        )

    def run_many(
        self,
        *,
        account_state: AccountState,
        init_state: ProgressionInitState,
        configs: List[BossWaveEngineConfig],
    ) -> BossWaveRunBatchResult:
        grouped: Dict[Tuple[Any, ...], List[Tuple[BossWaveEngineConfig, ProgressionFixedInputs]]] = {}
        for config in configs:
            fixed_inputs = self._resolve_progression_fixed_inputs(
                account_state=account_state,
                init_state=init_state,
                config=config,
            )
            grouped.setdefault(self._progression_signature(config, fixed_inputs), []).append((config, fixed_inputs))
        runs: List[BossWaveRunResult] = []
        diagnostics = {
            'group_count': len(grouped),
            'config_count': len(configs),
            'grouped_progression_execution': True,
            'signatures': [list(sig) for sig in grouped.keys()],
        }
        for grouped_configs in grouped.values():
            representative_config, representative_fixed_inputs = grouped_configs[0]
            max_end_wave = max(config.end_boss_wave for config, _fixed_inputs in grouped_configs)
            sweep_config = replace(representative_config, end_boss_wave=max_end_wave)
            snapshots = self._build_progression_snapshots(
                account_state=account_state,
                init_state=init_state,
                config=sweep_config,
                fixed_inputs=representative_fixed_inputs,
            )
            for config, fixed_inputs in grouped_configs:
                run = self._run_from_snapshots(
                    account_state=account_state,
                    init_state=init_state,
                    config=config,
                    snapshots=snapshots,
                    fixed_inputs=fixed_inputs,
                )
                runs.append(
                    BossWaveRunResult(
                        rows=run.rows,
                        diagnostics={**run.diagnostics, 'shared_progression_group_size': len(grouped_configs)},
                    )
                )
        return BossWaveRunBatchResult(runs=runs, diagnostics=diagnostics)

    @staticmethod
    def _progression_signature(config: BossWaveEngineConfig, fixed_inputs: ProgressionFixedInputs) -> Tuple[Any, ...]:
        explicit_events = tuple(
            (int(event.wave), str(event.track_name), int(event.delta_levels), str(event.source), str(event.note or ''))
            for event in (config.workshop_progression_events or [])
        )
        return (
            config.preset_name,
            config.mode_id,
            config.perks_enabled,
            config.perk_preset_name,
            config.card_preset_name,
            config.module_preset_name,
            explicit_events,
            round(float(fixed_inputs.enemy_level_skip_reduction_pp), 9),
            int(fixed_inputs.boss_wave_interval),
        )

    def _build_progression_snapshots(
        self,
        *,
        account_state: AccountState,
        init_state: ProgressionInitState,
        config: BossWaveEngineConfig,
        fixed_inputs: ProgressionFixedInputs,
    ) -> Dict[int, ProgressionSnapshot]:
        snapshots: Dict[int, ProgressionSnapshot] = {}
        wave_progression_policy = WaveProgressionPolicy(WaveProgressionPolicyConfig(warmup_waves=config.enemy_skip_warmup_waves))
        wave_progression_state = WaveProgressionState()
        workshop_levels_current = dict(init_state.workshop_levels_current)
        free_upgrade_state = FreeUpgradeGenerationState()
        total_generated_free_upgrades = 0
        total_explicit_workshop_events = 0
        perk_counts: Dict[str, int] = {}
        timeline_by_wave: Dict[int, List[Any]] = {}
        for event in init_state.perk_timeline:
            timeline_by_wave.setdefault(int(event.wave), []).append(event)
        events_by_wave: Dict[int, List[WorkshopUpgradeEvent]] = {}
        for event in config.workshop_progression_events or []:
            events_by_wave.setdefault(int(event.wave), []).append(event)
        row_map: Optional[Dict[str, Any]] = None
        dirty = True
        last_recalc_result: Optional[ProgressionRecalcResult] = None
        last_recalc_workshop_levels_current = dict(workshop_levels_current)
        for display_wave in range(1, config.end_boss_wave + 1):
            for perk_event in timeline_by_wave.get(display_wave, []):
                perk_counts[str(perk_event.perk_id)] = int(perk_counts.get(str(perk_event.perk_id), 0)) + int(getattr(perk_event, 'quantity', 1) or 1)
                dirty = True
            if dirty or row_map is None:
                recalc = self._recompute_row_map_compat(
                    account_state=account_state,
                    config=config,
                    workshop_levels_current=workshop_levels_current,
                    perk_counts=perk_counts,
                    cached_reference_result=last_recalc_result,
                    cached_reference_workshop_levels_current=last_recalc_workshop_levels_current,
                )
                row_map = recalc.statbook.rows
                last_recalc_result = recalc
                last_recalc_workshop_levels_current = dict(workshop_levels_current)
                dirty = False

            explicit_events = events_by_wave.get(display_wave, [])
            explicit_applied: List[AppliedWorkshopUpgrade] = []
            if explicit_events:
                explicit_snapshot = self._workshop_policy.snapshot_at_wave(
                    workshop_tracks=self._materialize_dynamic_tracks(init_state, workshop_levels_current),
                    events=explicit_events,
                    wave=display_wave,
                )
                workshop_levels_current = dict(explicit_snapshot.workshop_levels_current)
                explicit_applied = list(explicit_snapshot.applied_upgrades)
                total_explicit_workshop_events += len(explicit_applied)
                dirty = True
            if dirty or row_map is None:
                recalc = self._recompute_row_map_compat(
                    account_state=account_state,
                    config=config,
                    workshop_levels_current=workshop_levels_current,
                    perk_counts=perk_counts,
                    cached_reference_result=last_recalc_result,
                    cached_reference_workshop_levels_current=last_recalc_workshop_levels_current,
                )
                row_map = recalc.statbook.rows
                last_recalc_result = recalc
                last_recalc_workshop_levels_current = dict(workshop_levels_current)
                dirty = False

            black_hole_disable_ranged = bool(_row_truthy(row_map, 'capability::capability.uw.black_hole.disable_ranged'))
            free_result = self._free_upgrade_policy.generate_for_wave(
                wave=display_wave,
                workshop_tracks=init_state.workshop_tracks,
                workshop_levels_current=workshop_levels_current,
                stat_values={
                    'canonical_stat::free_attack_upgrade_chance_pct': _row_value(row_map, 'canonical_stat::free_attack_upgrade_chance_pct'),
                    'canonical_stat::free_defense_upgrade_chance_pct': _row_value(row_map, 'canonical_stat::free_defense_upgrade_chance_pct'),
                    'canonical_stat::free_utility_upgrade_chance_pct': _row_value(row_map, 'canonical_stat::free_utility_upgrade_chance_pct'),
                },
                state=free_upgrade_state,
                black_hole_disable_ranged=black_hole_disable_ranged,
            )
            free_upgrade_state = free_result.state
            generated_free_events = list(free_result.generated_events)
            total_generated_free_upgrades += len(generated_free_events)
            if generated_free_events:
                dirty = True
            if dirty or row_map is None:
                recalc = self._recompute_row_map_compat(
                    account_state=account_state,
                    config=config,
                    workshop_levels_current=workshop_levels_current,
                    perk_counts=perk_counts,
                    cached_reference_result=last_recalc_result,
                    cached_reference_workshop_levels_current=last_recalc_workshop_levels_current,
                )
                row_map = recalc.statbook.rows
                last_recalc_result = recalc
                last_recalc_workshop_levels_current = dict(workshop_levels_current)
                dirty = False

            enemy_attack_level_skip_pct = max(0.0, (_row_value(row_map, 'canonical_stat::enemy_attack_level_skip_pct') or 0.0) - float(fixed_inputs.enemy_level_skip_reduction_pp))
            enemy_health_level_skip_pct = max(0.0, (_row_value(row_map, 'canonical_stat::enemy_health_level_skip_pct') or 0.0) - float(fixed_inputs.enemy_level_skip_reduction_pp))
            wave_progression_state = wave_progression_policy.advance_to_wave(
                state=wave_progression_state,
                target_display_wave=display_wave,
                attack_skip_pct=float(enemy_attack_level_skip_pct) / 100.0,
                health_skip_pct=float(enemy_health_level_skip_pct) / 100.0,
            )

            snapshots[display_wave] = ProgressionSnapshot(
                display_wave=display_wave,
                perk_counts=dict(perk_counts),
                row_map=row_map,
                wave_progression_state=wave_progression_state,
                total_generated_free_upgrades=total_generated_free_upgrades,
                total_explicit_workshop_events=total_explicit_workshop_events,
                free_upgrade_notes=list(free_result.notes),
                explicit_applied_count=len(explicit_applied),
                generated_free_event_count=len(generated_free_events),
            )
        return snapshots

    def _resolve_progression_fixed_inputs(
        self,
        *,
        account_state: AccountState,
        init_state: ProgressionInitState,
        config: BossWaveEngineConfig,
    ) -> ProgressionFixedInputs:
        scenario_runtime_inputs = self._normalize_scenario_runtime_inputs(config.scenario_runtime_inputs)
        source_notes: List[str] = []
        recalc = self._recompute_row_map_compat(
            account_state=account_state,
            config=config,
            workshop_levels_current=dict(init_state.workshop_levels_current),
            perk_counts={},
        )
        runtime_context = self._build_runtime_context(
            row_map=recalc.statbook.rows,
            config=config,
            boss_wave=max(1, int(config.start_boss_wave)),
        )
        if scenario_runtime_inputs is not None and scenario_runtime_inputs.boss_wave_interval is not None:
            boss_wave_interval = max(1, int(round(float(scenario_runtime_inputs.boss_wave_interval))))
            source_notes.append('Boss wave interval sourced from scenario runtime inputs.')
        else:
            boss_wave_interval = max(1, int(runtime_context.scenario.boss_wave_interval or config.boss_wave_step or 1))
            source_notes.append('Boss wave interval sourced from scenario engine.')
        if scenario_runtime_inputs is not None and scenario_runtime_inputs.enemy_level_skip_reduction_pp is not None:
            enemy_level_skip_reduction_pp = max(0.0, float(scenario_runtime_inputs.enemy_level_skip_reduction_pp))
            source_notes.append('Enemy level skip reduction sourced from scenario runtime inputs.')
        else:
            enemy_level_skip_reduction_pp = max(0.0, float(runtime_context.scenario.bc_enemy_level_skip_reduction_pp or 0.0))
            if enemy_level_skip_reduction_pp > 0.0:
                source_notes.append('Enemy level skip reduction sourced from scenario engine.')
        return ProgressionFixedInputs(
            boss_wave_interval=boss_wave_interval,
            enemy_level_skip_reduction_pp=enemy_level_skip_reduction_pp,
            source_notes=source_notes,
        )

    def _run_from_snapshots(
        self,
        *,
        account_state: AccountState,
        init_state: ProgressionInitState,
        config: BossWaveEngineConfig,
        snapshots: Dict[int, ProgressionSnapshot],
        fixed_inputs: ProgressionFixedInputs,
    ) -> BossWaveRunResult:
        rows: List[BossWaveRow] = []
        scenario_runtime_inputs = self._normalize_scenario_runtime_inputs(config.scenario_runtime_inputs)
        last_runtime_inputs: Optional[ResolvedRuntimeInputs] = None
        boss_wave_interval = max(1, int(fixed_inputs.boss_wave_interval))
        for display_wave in range(config.start_boss_wave, config.end_boss_wave + 1):
            if (display_wave - config.start_boss_wave) % boss_wave_interval != 0:
                continue
            snapshot = snapshots[display_wave]
            row_map = snapshot.row_map
            perk_counts = snapshot.perk_counts
            boss_wave = display_wave
            attack_wave = snapshot.wave_progression_state.attack_wave
            health_wave = snapshot.wave_progression_state.health_wave
            wall_hp = _row_value(row_map, 'canonical_stat::wall_hp')
            wall_regen = _row_value(row_map, 'canonical_stat::wall_regen')
            wall_fortification_multiplier = _row_value(row_map, 'canonical_stat::wall_fortification_multiplier')
            tower_defense_pct = _row_value(row_map, 'canonical_stat::tower_defense_pct')
            plasma_cannon_effect_pct = _row_value(row_map, 'runtime_mechanic_param::cards.plasma_cannon.effect_pct')
            orb_count = _row_value(row_map, 'canonical_stat::tower_orb_count')
            orb_speed_rpm = _row_value(row_map, 'canonical_stat::tower_orb_speed_rpm')
            electron_count = _row_value(row_map, 'mechanic_param::module.orbital_augment.electron_count')
            tower_thorns_damage_pct = _row_value(row_map, 'canonical_stat::tower_thorns_damage_pct')
            boss_damage = self._lookup_wave_value(self._enemy_damage, attack_wave, config.tier_column)
            common_hp = self._lookup_wave_value(self._enemy_health, health_wave, config.tier_column)
            notes = [
                'Scaffold row built from stat-engine recompute on progression snapshot.',
                'Perk timing is consumed through a fixed static timeline generated upstream; retrospective PWR remains owned by the perk timeline generator.',
                f'Workshop progression events applied through wave {boss_wave}: {snapshot.total_explicit_workshop_events}',
                f'Generated free-upgrade events applied through wave {boss_wave}: {snapshot.total_generated_free_upgrades}',
                'Free-upgrade generation uses accepted deterministic expectation carry with stable per-category track-order allocation; Wave Skip extra-upgrade effects remain excluded.',
                f'Attack/health wave derived via deterministic current-wave skip model with no warmup and current skip pcts attack={max(0.0, (_row_value(row_map, "canonical_stat::enemy_attack_level_skip_pct") or 0.0) - float(fixed_inputs.enemy_level_skip_reduction_pp))} health={max(0.0, (_row_value(row_map, "canonical_stat::enemy_health_level_skip_pct") or 0.0) - float(fixed_inputs.enemy_level_skip_reduction_pp))}.',
            ]
            notes.extend(snapshot.free_upgrade_notes)
            if fixed_inputs.enemy_level_skip_reduction_pp > 0.0:
                notes.append(f'Scenario-owned enemy level skip reduction applied: -{fixed_inputs.enemy_level_skip_reduction_pp} pp.')
            notes.append(f'Scenario-owned boss cadence interval used: every {boss_wave_interval} waves.')
            if snapshot.explicit_applied_count:
                notes.append(f'Explicit workshop events at wave {boss_wave}: {snapshot.explicit_applied_count}')
            if snapshot.generated_free_event_count:
                notes.append(f'Generated free-upgrade events at wave {boss_wave}: {snapshot.generated_free_event_count}')

            runtime_context = self._build_runtime_context(row_map=row_map, config=config, boss_wave=boss_wave)
            runtime_inputs = self._resolve_runtime_inputs(
                row_map=row_map,
                account_state=account_state,
                config=config,
                scenario_runtime_inputs=scenario_runtime_inputs,
                scenario_context=runtime_context.scenario,
                timing_context=runtime_context.timing,
            )
            last_runtime_inputs = runtime_inputs
            notes.extend(runtime_inputs.source_notes)

            status = 'ready_for_ttk'
            block_reason = None
            boss_effective_hp = common_hp * BOSS_HP_MULTIPLIER if common_hp is not None else None
            boss_ttk_seconds: Optional[float] = None
            thorns_contact_events_used = 0
            boss_hits_taken: Optional[int] = None
            boss_total_damage_taken: Optional[float] = None
            effective_wall_hp_pool: Optional[float] = None
            wall_regen_gained_during_ttk: Optional[float] = None
            wall_hp_after_boss: Optional[float] = None
            survival_margin_hp: Optional[float] = None
            damage_reduction_pct_used: Optional[float] = None
            if not self._has_ttk_runtime_inputs(runtime_inputs, tower_thorns_damage_pct=tower_thorns_damage_pct):
                status = 'blocked_open_runtime_cadence'
                block_reason = self._ttk_block_reason(runtime_inputs, tower_thorns_damage_pct=tower_thorns_damage_pct)
            elif boss_effective_hp is None or plasma_cannon_effect_pct is None:
                status = 'blocked_missing_runtime_surface'
                block_reason = 'Missing boss HP reference or Plasma Cannon effect surface.'
            else:
                try:
                    ttk = self._simulate_boss_ttk(
                        boss_effective_hp=boss_effective_hp,
                        plasma_cannon_effect_pct=plasma_cannon_effect_pct,
                        tower_thorns_damage_pct=tower_thorns_damage_pct or 0.0,
                        runtime_inputs=runtime_inputs,
                        config=config,
                    )
                except ValueError as exc:
                    status = 'blocked_ttk_not_resolved'
                    block_reason = str(exc)
                else:
                    boss_ttk_seconds = ttk.ttk_seconds
                    thorns_contact_events_used = ttk.thorns_contact_events_used
                    notes.append(
                        f'TTK solved with runtime inputs: orb_pct={runtime_inputs.orb_boss_hit_pct}, '
                        f'orb_hz={runtime_inputs.orb_boss_hits_per_second}, electron_hz={runtime_inputs.electron_hits_per_second}, '
                        f'contact_t={runtime_inputs.boss_contact_time_seconds}, hit_interval={runtime_inputs.boss_hit_interval_seconds}'
                    )
                    try:
                        intake = self._simulate_boss_damage_intake(
                            boss_base_damage=boss_damage,
                            ttk_seconds=ttk.ttk_seconds,
                            wall_hp=wall_hp,
                            wall_regen=wall_regen,
                            wall_fortification_multiplier=wall_fortification_multiplier,
                            tower_defense_pct=tower_defense_pct,
                            runtime_inputs=runtime_inputs,
                            timing_context=runtime_context.timing,
                            config=config,
                        )
                    except ValueError as exc:
                        status = 'blocked_damage_intake_not_resolved'
                        block_reason = str(exc)
                    else:
                        boss_hits_taken = intake.boss_hits_taken
                        boss_total_damage_taken = intake.total_damage_taken
                        effective_wall_hp_pool = intake.effective_wall_hp_pool
                        wall_regen_gained_during_ttk = intake.wall_regen_gained
                        wall_hp_after_boss = intake.wall_hp_after_boss
                        survival_margin_hp = intake.survival_margin_hp
                        damage_reduction_pct_used = intake.damage_reduction_pct_used
                        status = 'survival_resolved'
                        if runtime_inputs.effective_damage_reduction_pct is None and config.effective_damage_reduction_pct_override is None:
                            notes.append('Damage intake resolved using baseline tower_defense_pct only; stronger scenario DR overlays remain external.')
                        elif runtime_inputs.effective_damage_reduction_pct is not None:
                            notes.append('Damage intake resolved using governed effective damage reduction surface when present.')
                        else:
                            notes.append('Damage intake resolved using explicit effective_damage_reduction_pct_override.')

            rows.append(BossWaveRow(
                boss_wave=boss_wave,
                attack_wave=attack_wave,
                health_wave=health_wave,
                boss_base_damage=boss_damage,
                boss_base_hp_common_reference=common_hp,
                boss_effective_hp=boss_effective_hp,
                boss_ttk_seconds=boss_ttk_seconds,
                boss_contact_time_seconds=runtime_inputs.boss_contact_time_seconds,
                thorns_contact_events_used=thorns_contact_events_used,
                boss_hits_taken=boss_hits_taken,
                boss_total_damage_taken=boss_total_damage_taken,
                wall_hp=wall_hp,
                wall_regen=wall_regen,
                wall_fortification_multiplier=wall_fortification_multiplier,
                effective_wall_hp_pool=effective_wall_hp_pool,
                wall_regen_gained_during_ttk=wall_regen_gained_during_ttk,
                wall_hp_after_boss=wall_hp_after_boss,
                survival_margin_hp=survival_margin_hp,
                damage_reduction_pct_used=damage_reduction_pct_used,
                plasma_cannon_effect_pct=plasma_cannon_effect_pct,
                orb_count=orb_count,
                orb_speed_rpm=orb_speed_rpm,
                electron_count=electron_count,
                tower_thorns_damage_pct=tower_thorns_damage_pct,
                active_perk_count=sum(perk_counts.values()),
                status=status,
                block_reason=block_reason,
                notes=notes,
            ))

        diagnostics = {
            'engine_status': 'progression_scaffold_safe_recompute',
            'mode_id': config.mode_id,
            'preset_name': config.preset_name,
            'tier_column': config.tier_column,
            'boss_hit_interval_seconds': (last_runtime_inputs.boss_hit_interval_seconds if last_runtime_inputs is not None else config.boss_hit_interval_seconds),
            'governed_runtime_surface_consumed': any(('governed runtime surface' in note) or ('governed surface' in note) for row in rows for note in row.notes),
            'scenario_engine_consumed': any(('scenario engine' in note.lower()) or ('scenario_engine surface' in note) for row in rows for note in row.notes),
            'timing_engine_consumed': any('timing_engine' in note for row in rows for note in row.notes),
            'blocked_on_open_runtime_cadence': any(row.status == 'blocked_open_runtime_cadence' for row in rows),
            'ttk_slice_enabled': any(row.status in {'ready_for_damage_intake', 'survival_resolved'} for row in rows),
            'damage_intake_slice_enabled': any(row.status == 'survival_resolved' for row in rows),
            'perk_timeline_consumed': bool(init_state.perk_timeline),
            'scenario_runtime_input_consumed': any('scenario runtime input' in note for row in rows for note in row.notes),
            'grouped_progression_execution': False,
            'boss_wave_interval_used': boss_wave_interval,
            'progression_skip_reduction_pp_applied': float(fixed_inputs.enemy_level_skip_reduction_pp),
        }
        if rows:
            diagnostics['generated_free_upgrade_events'] = snapshots[max(snapshots)].total_generated_free_upgrades
        else:
            diagnostics['generated_free_upgrade_events'] = 0
        return BossWaveRunResult(rows=rows, diagnostics=diagnostics)

    def _recompute_row_map(
        self,
        *,
        account_state: AccountState,
        config: BossWaveEngineConfig,
        workshop_levels_current: Dict[str, int],
        perk_counts: Dict[str, int],
        cached_reference_result: Optional[ProgressionRecalcResult] = None,
        cached_reference_workshop_levels_current: Optional[Dict[str, int]] = None,
    ):
        cached_fingerprint = None
        if cached_reference_result is not None:
            cached_fingerprint = (cached_reference_result.incremental_diagnostics or {}).get('cache_fingerprint')
        return self._bridge.recompute(
            ProgressionRecalcRequest(
                account_state=account_state,
                preset_name=config.preset_name,
                workshop_levels_current=workshop_levels_current,
                card_preset_name=config.card_preset_name,
                module_preset_name=config.module_preset_name,
                perk_preset_name=config.perk_preset_name,
                perks_enabled=config.perks_enabled,
                perk_counts_override=perk_counts,
                state_mode='start_of_run',
                recompute_mode='incremental_cached_publish_guarded' if cached_reference_result is not None else 'full_safe',
                cached_reference_statbook=None if cached_reference_result is None else cached_reference_result.statbook,
                cached_reference_workshop_levels_current=None if cached_reference_result is None else dict(cached_reference_workshop_levels_current or {}),
                cached_reference_fingerprint=cached_fingerprint,
            )
        )

    def _recompute_row_map_compat(
        self,
        *,
        account_state: AccountState,
        config: BossWaveEngineConfig,
        workshop_levels_current: Dict[str, int],
        perk_counts: Dict[str, int],
        cached_reference_result: Optional[ProgressionRecalcResult] = None,
        cached_reference_workshop_levels_current: Optional[Dict[str, int]] = None,
    ):
        try:
            return self._recompute_row_map(
                account_state=account_state,
                config=config,
                workshop_levels_current=workshop_levels_current,
                perk_counts=perk_counts,
                cached_reference_result=cached_reference_result,
                cached_reference_workshop_levels_current=cached_reference_workshop_levels_current,
            )
        except TypeError as exc:
            if 'unexpected keyword argument' not in str(exc):
                raise
            return self._recompute_row_map(
                account_state=account_state,
                config=config,
                workshop_levels_current=workshop_levels_current,
                perk_counts=perk_counts,
            )

    @staticmethod
    def _materialize_dynamic_tracks(init_state: ProgressionInitState, workshop_levels_current: Dict[str, int]) -> Dict[str, WorkshopTrackState]:
        out: Dict[str, WorkshopTrackState] = {}
        for name, track in init_state.workshop_tracks.items():
            out[name] = WorkshopTrackState(
                track_name=track.track_name,
                current_level=int(workshop_levels_current[name]),
                max_level=int(track.max_level),
                category=track.category,
                unlocked=track.unlocked,
            )
        return out

    @staticmethod
    def _load_wave_table(path: Path) -> Dict[int, Dict[str, float]]:
        table: Dict[int, Dict[str, float]] = {}
        with path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                wave_token = (row.get('wave') or row.get('Wave') or row.get('wave_actual') or '').strip()
                if not wave_token:
                    continue
                wave = int(float(wave_token))
                values: Dict[str, float] = {}
                for key, raw in row.items():
                    if key is None or key.lower() in {'wave'}:
                        continue
                    token = (raw or '').strip().replace(',', '')
                    if not token:
                        continue
                    try:
                        values[key] = float(token)
                    except ValueError:
                        continue
                table[wave] = values
        return table

    @staticmethod
    def _lookup_wave_value(table: Dict[int, Dict[str, float]], wave: int, tier_column: str) -> Optional[float]:
        if not table:
            return None
        if wave in table:
            return table[wave].get(tier_column)
        sorted_waves = sorted(table.keys())
        lower = None
        upper = None
        for candidate in sorted_waves:
            if candidate < wave:
                lower = candidate
                continue
            if candidate > wave:
                upper = candidate
                break
        if lower is None:
            return table[sorted_waves[0]].get(tier_column)
        if upper is None:
            return table[sorted_waves[-1]].get(tier_column)
        lower_value = table[lower].get(tier_column)
        upper_value = table[upper].get(tier_column)
        if lower_value is None:
            return upper_value
        if upper_value is None:
            return lower_value
        fraction = (float(wave) - float(lower)) / (float(upper) - float(lower))
        return float(lower_value) + (float(upper_value) - float(lower_value)) * fraction

    @staticmethod
    def _lookup_first_present(row_map: Dict[str, Any], keys: List[str]) -> Optional[float]:
        for key in keys:
            value = _row_value(row_map, key)
            if value is not None:
                return value
        return None

    @classmethod
    def _normalize_scenario_runtime_inputs(self, raw: Optional[ScenarioRuntimeInputs | Dict[str, float]]) -> Optional[ScenarioRuntimeInputs]:
        if raw is None:
            return None
        if isinstance(raw, ScenarioRuntimeInputs):
            return raw
        return ScenarioRuntimeInputs.from_mapping(raw)

    @classmethod
    def _build_runtime_context(
        cls,
        *,
        row_map: Dict[str, Any],
        config: BossWaveEngineConfig,
        boss_wave: int,
    ) -> ProgressionRuntimeContext:
        statbook_rows = {
            key: ({'final_value': value.final_value} if hasattr(value, 'final_value') else value)
            for key, value in row_map.items()
        }
        scenario_config = config_from_statbook(
            statbook_rows,
            mode_id=config.mode_id,
            tier=cls._tier_number_from_column(config.tier_column),
            league=config.league,
            tournament_wave=(int(config.tournament_wave) if config.tournament_wave is not None else (boss_wave if config.mode_id == 'tournament' else 0)),
        )
        scenario = compute_scenario_surfaces(scenario_config)
        timing = compute_timing_surfaces(scenario_config, scenario)
        return ProgressionRuntimeContext(scenario=scenario, timing=timing)

    @staticmethod
    def _tier_number_from_column(tier_column: str) -> int:
        try:
            return int(str(tier_column).split()[-1])
        except (TypeError, ValueError, IndexError):
            return 14

    @classmethod
    def _resolve_runtime_inputs(
        cls,
        *,
        row_map: Dict[str, Any],
        account_state: AccountState,
        scenario_runtime_inputs: Optional[ScenarioRuntimeInputs],
        scenario_context: ScenarioSurfaces,
        timing_context: TimingSurfaces,
        config: BossWaveEngineConfig,
    ) -> ResolvedRuntimeInputs:
        scenario_cfg = ScenarioConfig(
            mode_id=scenario_context.mode_id or config.mode_id,
            tier=cls._tier_number_from_column(config.tier_column),
            league=config.league,
            tournament_wave=(int(config.tournament_wave) if config.tournament_wave is not None else 0),
        )
        combat_runtime = resolve_combat_runtime_surfaces(
            config=scenario_cfg,
            scenario=scenario_context,
            timing=timing_context,
            row_map=row_map,
            account_state=account_state,
            scenario_runtime_inputs=scenario_runtime_inputs,
            orb_boss_hit_pct_override=config.orb_boss_hit_pct_override,
            orb_boss_hits_per_second_override=config.orb_boss_hits_per_second_override,
            electron_hits_per_second_override=config.electron_hits_per_second_override,
            boss_contact_time_seconds_override=config.boss_contact_time_seconds_override,
            effective_damage_reduction_pct_override=config.effective_damage_reduction_pct_override,
            incoming_damage_multiplier_override=config.incoming_damage_multiplier_override,
        )
        return ResolvedRuntimeInputs(
            boss_hit_interval_seconds=float(combat_runtime.boss_hit_interval_seconds),
            boss_contact_time_seconds=None if combat_runtime.boss_contact_time_seconds is None else float(combat_runtime.boss_contact_time_seconds),
            orb_boss_hit_pct=None if combat_runtime.orb_boss_hit_pct is None else float(combat_runtime.orb_boss_hit_pct),
            orb_boss_hits_per_second=None if combat_runtime.orb_boss_hits_per_second is None else float(combat_runtime.orb_boss_hits_per_second),
            electron_hits_per_second=None if combat_runtime.electron_hits_per_second is None else float(combat_runtime.electron_hits_per_second),
            effective_damage_reduction_pct=None if combat_runtime.effective_damage_reduction_pct is None else float(combat_runtime.effective_damage_reduction_pct),
            incoming_damage_multiplier=None if combat_runtime.incoming_damage_multiplier is None else float(combat_runtime.incoming_damage_multiplier),
            source_notes=list(combat_runtime.source_notes),
        )

    @staticmethod
    def _has_ttk_runtime_inputs(runtime_inputs: ResolvedRuntimeInputs, *, tower_thorns_damage_pct: Optional[float]) -> bool:
        if runtime_inputs.orb_boss_hit_pct is None:
            return False
        if runtime_inputs.orb_boss_hits_per_second is None:
            return False
        if runtime_inputs.electron_hits_per_second is None:
            return False
        if (tower_thorns_damage_pct or 0.0) > 0 and runtime_inputs.boss_contact_time_seconds is None:
            return False
        return True

    @staticmethod
    def _ttk_block_reason(runtime_inputs: ResolvedRuntimeInputs, *, tower_thorns_damage_pct: Optional[float]) -> str:
        missing: List[str] = []
        if runtime_inputs.orb_boss_hit_pct is None:
            missing.append('governed_orb_boss_hit_pct_or_override')
        if runtime_inputs.orb_boss_hits_per_second is None:
            missing.append('governed_orb_boss_hits_per_second_or_override')
        if runtime_inputs.electron_hits_per_second is None:
            missing.append('governed_electron_hits_per_second_or_override')
        if (tower_thorns_damage_pct or 0.0) > 0 and runtime_inputs.boss_contact_time_seconds is None:
            missing.append('governed_boss_contact_time_seconds_or_override')
        return 'Provide governed runtime surfaces or explicit overrides before final TTK simulation: ' + ', '.join(missing)

    @staticmethod
    def _simulate_boss_ttk(
        *,
        boss_effective_hp: float,
        plasma_cannon_effect_pct: float,
        tower_thorns_damage_pct: float,
        runtime_inputs: ResolvedRuntimeInputs,
        config: BossWaveEngineConfig,
    ) -> BossTTKResult:
        pc_pct = max(0.0, min(100.0, plasma_cannon_effect_pct)) / 100.0
        pc_pct *= config.plasma_cannon_resistance_multiplier
        remaining_hp = boss_effective_hp * max(0.0, 1.0 - pc_pct)
        if remaining_hp <= 0:
            return BossTTKResult(
                boss_effective_hp=boss_effective_hp,
                remaining_hp_after_opening=0.0,
                ttk_seconds=0.0,
                thorns_contact_events_used=0,
                orb_hits_used=0,
                electron_hits_used=0,
            )

        if runtime_inputs.orb_boss_hit_pct is None or runtime_inputs.orb_boss_hits_per_second is None or runtime_inputs.electron_hits_per_second is None:
            raise ValueError('Boss TTK requires resolved runtime cadence inputs.')

        orb_pct = max(0.0, float(runtime_inputs.orb_boss_hit_pct)) / 100.0
        orb_pct *= config.orb_resistance_multiplier
        electron_pct = ELECTRON_BOSS_REMAINING_HP_PCT
        orb_interval = 1.0 / float(runtime_inputs.orb_boss_hits_per_second)
        electron_interval = 1.0 / float(runtime_inputs.electron_hits_per_second)
        next_orb = orb_interval
        next_electron = electron_interval
        next_contact = inf
        if runtime_inputs.boss_contact_time_seconds is not None:
            next_contact = float(runtime_inputs.boss_contact_time_seconds)
        thorns_pct = max(0.0, tower_thorns_damage_pct) / 100.0
        thorns_pct *= THORNS_BOSS_EFFECTIVENESS
        thorns_pct *= config.thorns_resistance_multiplier
        orb_hits = 0
        electron_hits = 0
        thorns_contacts = 0
        t = 0.0
        while remaining_hp > KILL_HP_THRESHOLD:
            next_t = min(next_orb, next_electron, next_contact)
            if not isfinite(next_t) or next_t > float(config.max_ttk_seconds):
                raise ValueError('Boss TTK exceeded max_ttk_seconds or no runtime events were available.')
            t = next_t
            if abs(next_orb - t) <= 1e-12:
                remaining_hp *= max(0.0, 1.0 - orb_pct)
                orb_hits += 1
                next_orb += orb_interval
            if remaining_hp <= 0:
                break
            if abs(next_electron - t) <= 1e-12:
                remaining_hp *= max(0.0, 1.0 - electron_pct)
                electron_hits += 1
                next_electron += electron_interval
            if remaining_hp <= 0:
                break
            if abs(next_contact - t) <= 1e-12:
                remaining_hp *= max(0.0, 1.0 - thorns_pct)
                thorns_contacts += 1
                next_contact += float(runtime_inputs.boss_hit_interval_seconds)
        return BossTTKResult(
            boss_effective_hp=boss_effective_hp,
            remaining_hp_after_opening=max(0.0, boss_effective_hp * max(0.0, 1.0 - pc_pct)),
            ttk_seconds=t,
            thorns_contact_events_used=thorns_contacts,
            orb_hits_used=orb_hits,
            electron_hits_used=electron_hits,
        )

    @staticmethod
    def _simulate_boss_damage_intake(
        *,
        boss_base_damage: Optional[float],
        ttk_seconds: float,
        wall_hp: Optional[float],
        wall_regen: Optional[float],
        wall_fortification_multiplier: Optional[float],
        tower_defense_pct: Optional[float],
        runtime_inputs: ResolvedRuntimeInputs,
        timing_context: TimingSurfaces,
        config: BossWaveEngineConfig,
    ) -> BossDamageIntakeResult:
        if boss_base_damage is None:
            raise ValueError('Missing boss base damage reference.')
        if wall_hp is None or wall_regen is None or wall_fortification_multiplier is None:
            raise ValueError('Missing wall survivability surfaces for damage intake.')
        dr_pct = runtime_inputs.effective_damage_reduction_pct
        if dr_pct is None:
            base_dr_fraction = 0.0 if tower_defense_pct is None else max(0.0, min(100.0, float(tower_defense_pct))) / 100.0
            encounter_timed_dr_fraction = 0.0
            if runtime_inputs.boss_contact_time_seconds is not None and ttk_seconds > runtime_inputs.boss_contact_time_seconds:
                encounter_timed_dr_fraction = compute_average_damage_reduction_fraction_over_interval(
                    timing_context,
                    runtime_inputs.boss_contact_time_seconds,
                    ttk_seconds,
                )
            combined_dr_fraction = 1.0 - ((1.0 - base_dr_fraction) * (1.0 - encounter_timed_dr_fraction))
            dr_pct = combined_dr_fraction * 100.0
            if tower_defense_pct is None and encounter_timed_dr_fraction <= 0.0:
                raise ValueError('Missing tower_defense_pct and no effective_damage_reduction_pct_override supplied.')
        dr_fraction = max(0.0, min(100.0, float(dr_pct))) / 100.0
        if runtime_inputs.boss_contact_time_seconds is None:
            return BossDamageIntakeResult(
                boss_hits_taken=0,
                total_damage_taken=0.0,
                wall_regen_gained=max(0.0, wall_regen * ttk_seconds),
                effective_wall_hp_pool=wall_hp * wall_fortification_multiplier,
                wall_hp_after_boss=wall_hp * wall_fortification_multiplier + max(0.0, wall_regen * ttk_seconds),
                survival_margin_hp=wall_hp * wall_fortification_multiplier + max(0.0, wall_regen * ttk_seconds),
                damage_reduction_pct_used=float(dr_pct),
            )
        hit_t = float(runtime_inputs.boss_contact_time_seconds)
        interval = float(runtime_inputs.boss_hit_interval_seconds)
        if interval <= 0:
            raise ValueError('boss_hit_interval_seconds must be > 0')
        total_damage_taken = 0.0
        hits = 0
        while hit_t <= ttk_seconds + 1e-12:
            heat_multiplier = 1.0 + BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT * hits
            incoming_damage_multiplier = runtime_inputs.incoming_damage_multiplier
            if incoming_damage_multiplier is None:
                incoming_damage_multiplier = float(config.incoming_damage_multiplier_override)
            damage = float(boss_base_damage) * float(incoming_damage_multiplier) * heat_multiplier
            damage *= max(0.0, 1.0 - dr_fraction)
            total_damage_taken += damage
            hits += 1
            hit_t += interval
        effective_wall_hp_pool = wall_hp * wall_fortification_multiplier
        wall_regen_gained = max(0.0, wall_regen * ttk_seconds)
        wall_hp_after_boss = effective_wall_hp_pool + wall_regen_gained - total_damage_taken
        return BossDamageIntakeResult(
            boss_hits_taken=hits,
            total_damage_taken=total_damage_taken,
            wall_regen_gained=wall_regen_gained,
            effective_wall_hp_pool=effective_wall_hp_pool,
            wall_hp_after_boss=wall_hp_after_boss,
            survival_margin_hp=wall_hp_after_boss,
            damage_reduction_pct_used=float(dr_pct),
        )


def _row_truthy(row_map: Dict[str, Any], key: str) -> bool:
    row = row_map.get(key)
    if row is None:
        return False
    value = row.final_value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = str(value).strip().lower()
    return token in {'1', 'true', 'yes', 'enabled'}


def _row_value(row_map: Dict[str, Any], key: str) -> Optional[float]:
    row = row_map.get(key)
    if row is None:
        return None
    value = row.final_value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
