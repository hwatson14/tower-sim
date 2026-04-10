from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from input.state_types import AccountState
from qe.models import StatBook
from qe.routing import (
    query_response_to_statbook,
    resolve_checkpoint_consumer_bundle,
    resolve_checkpoint_consumer_bundle_delta,
    resolve_checkpoint_surfaces,
)
from qe.shared_runtime_context import get_default_qe_shared_runtime_context
from simulators.contracts import (
    NormalizedCheckpointState,
    PerformanceMetrics,
    SimulatorCheckpointResolution,
    SimulatorCheckpointState,
    WaveRowSnapshot,
)
from simulators.perks import apply_checkpoint_perk_state
from simulators.progression import run_stats_progression_family_id
from simulators.scenario import compute_scenario_surfaces, config_from_statbook
from simulators.timing import compute_timing_surfaces, resolve_combat_runtime_surfaces

_BOSS_WAVE_CONSUMER_ID = 'simulator_boss_wave'
_BOSS_WAVE_BUNDLE_ID = 'boss_wave_hot_surfaces'
_BOSS_WAVE_DAMAGE_BASIS_OPTIONAL_SURFACES = (
    'state::tower.damage',
    'state::tower.attack_speed',
    'state::tower.crit_chance_pct',
    'state::tower.crit_multiplier',
    'state::tower.range_m',
    'state::tower.multishot_chance_pct',
    'state::tower.multishot_targets',
    'state::tower.rapid_fire_chance_pct',
    'state::tower.rapid_fire_duration_seconds',
    'state::tower.bounce_shot_chance_pct',
    'state::tower.bounce_shot_targets',
    'state::tower.bounce_shot_range_m',
    'state::tower.damage_per_meter_multiplier',
    'state::tower.rend_armor_chance_pct',
    'state::tower.rend_armor_multiplier',
    'state::tower.supercrit_chance_pct',
    'state::tower.supercrit_multiplier',
    'state::tower.max_rend_multiplier',
    'state::cards.berserker.assumed_bonus_multiplier',
    'state::cards.ultimate_crit.chance_pct',
    'state::uw.black_hole.base_duration_seconds',
    'state::uw.black_hole.base_cooldown_seconds',
    'state::uw.golden_tower.base_duration_seconds',
    'state::uw.golden_tower.base_cooldown_seconds',
    'state::module.primordial_collapse.bh_damage_reduction_pct',
)


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


class SimulatorSnapshotResolver:
    """QE-backed snapshot resolver using contract-owned consumer bundles."""

    def __init__(self) -> None:
        self._runtime_context = get_default_qe_shared_runtime_context()
        self._query_kernel = self._runtime_context.query_kernel

    def apply_workshop_levels(
        self,
        account_state: AccountState,
        *,
        preset_name: str,
        workshop_levels_current: dict[str, int],
    ) -> AccountState:
        if not workshop_levels_current:
            return account_state

        patched_workshop = dict(account_state.workshop)
        for track_name, requested_level in workshop_levels_current.items():
            if track_name not in patched_workshop:
                raise KeyError(f"Unknown workshop track in checkpoint override: {track_name}")
            entry = patched_workshop[track_name]
            max_level = 0 if entry.max_level is None else int(entry.max_level)
            level = int(requested_level)
            if level < 0 or level > max_level:
                raise ValueError(
                    f"Invalid workshop level for {track_name}: {level}. Expected 0 <= level <= {max_level}."
                )
            patched_levels = dict(entry.preset_levels)
            patched_levels[preset_name] = level
            patched_workshop[track_name] = replace(entry, preset_levels=patched_levels)
        return replace(account_state, workshop=patched_workshop)

    def patched_account_state(
        self,
        *,
        account_state: AccountState,
        checkpoint_state: SimulatorCheckpointState,
        preset_name: str,
    ) -> AccountState:
        patched = self.apply_workshop_levels(
            account_state,
            preset_name=preset_name,
            workshop_levels_current=checkpoint_state.workshop_levels_current,
        )
        return apply_checkpoint_perk_state(
            patched,
            perk_counts_override=checkpoint_state.perk_counts_override,
        )

    def resolve_checkpoint(
        self,
        *,
        account_state: AccountState,
        checkpoint_state: SimulatorCheckpointState,
        preset_name: str,
        requested_surface_ids: tuple[str, ...] | list[str],
        family_id: str | None = None,
        state_mode: str = 'start_of_run',
        card_preset_name: str | None = None,
        module_preset_name: str | None = None,
        perk_preset_name: str | None = None,
        perks_enabled: bool | None = None,
    ) -> SimulatorCheckpointResolution:
        timings: dict[str, float] = {}

        t = perf_counter()
        patched = self.apply_workshop_levels(
            account_state,
            preset_name=preset_name,
            workshop_levels_current=checkpoint_state.workshop_levels_current,
        )
        timings['apply_workshop_levels'] = _elapsed_ms(t)

        t = perf_counter()
        patched = apply_checkpoint_perk_state(
            patched,
            perk_counts_override=checkpoint_state.perk_counts_override,
        )
        timings['apply_checkpoint_perks'] = _elapsed_ms(t)

        t = perf_counter()
        response = resolve_checkpoint_surfaces(
            patched,
            requested_surface_ids=tuple(requested_surface_ids),
            preset_name=preset_name,
            family_id=family_id,
            state_mode=state_mode,
            card_preset_name=card_preset_name,
            module_preset_name=module_preset_name,
            perk_preset_name=perk_preset_name,
            perks_enabled=perks_enabled,
            kernel=self._query_kernel,
        )
        timings['resolve_checkpoint_surfaces'] = _elapsed_ms(t)

        resolved_values = {row.surface_id: row.final_value for row in response.resolved_surface_rows}
        diagnostics = {
            'resolver_kind': 'simulator_checkpoint_qe_light',
            'family_id': response.family_id,
            'requested_surface_ids': tuple(requested_surface_ids),
            'resolved_surface_count': len(response.resolved_surface_rows),
            'phase_timing_ms': {
                **timings,
                'total_measured_ms': round(sum(timings.values()), 3),
            },
        }
        return SimulatorCheckpointResolution(
            requested_surface_ids=tuple(requested_surface_ids),
            resolved_values=resolved_values,
            diagnostics=diagnostics,
        )


def _checkpoint_state_from_normalized(normalized: NormalizedCheckpointState) -> SimulatorCheckpointState:
    projected = normalized.projected_run_state
    return SimulatorCheckpointState(
        workshop_levels_current=dict(projected.workshop_levels_current),
        perk_counts_override=dict(projected.perk_state.counts),
        runtime_target_display_wave=int(projected.checkpoint.display_wave),
    )


def _scenario_and_runtime_context(*, normalized: NormalizedCheckpointState, resolver: SimulatorSnapshotResolver, patched_account_state: AccountState, statbook: StatBook):
    scenario_config = config_from_statbook(
        {surface_id: {'final_value': row.final_value, 'value_type': row.value_type, 'status': row.status} for surface_id, row in statbook.rows.items()},
        mode_id=normalized.mode_id,
        tier=normalized.tier,
        league=normalized.league,
        tournament_wave=normalized.tournament_wave,
    )
    scenario_context = compute_scenario_surfaces(scenario_config)
    timing_context = compute_timing_surfaces(scenario_config, scenario_context)
    combat_runtime = resolve_combat_runtime_surfaces(
        config=scenario_config,
        scenario=scenario_context,
        timing=timing_context,
        row_map=statbook.rows,
        account_state=patched_account_state,
        scenario_runtime_inputs=normalized.scenario_runtime_inputs,
    )
    return scenario_context, timing_context, combat_runtime


def _build_snapshot(*, normalized: NormalizedCheckpointState, statbook: StatBook, patched_account_state: AccountState, elapsed_ms: float, qe_resolution_count: int) -> WaveRowSnapshot:
    resolver = SimulatorSnapshotResolver()
    scenario_context, timing_context, combat_runtime = _scenario_and_runtime_context(
        normalized=normalized,
        resolver=resolver,
        patched_account_state=patched_account_state,
        statbook=statbook,
    )
    return WaveRowSnapshot(
        checkpoint=normalized.checkpoint,
        projected_run_state=normalized.projected_run_state,
        resolved_statbook=statbook,
        scenario_context=scenario_context,
        timing_context=timing_context,
        geometry_context={},
        combat_runtime=combat_runtime,
        metrics=PerformanceMetrics(
            row_resolution_ms=elapsed_ms,
            qe_resolution_count=qe_resolution_count,
            timing_recompute_count=1,
            geometry_recompute_count=0,
        ),
    )


def resolve_wave_row_snapshot(normalized: NormalizedCheckpointState) -> WaveRowSnapshot:
    start = perf_counter()
    resolver = SimulatorSnapshotResolver()
    checkpoint_state = _checkpoint_state_from_normalized(normalized)
    patched_account_state = resolver.patched_account_state(
        account_state=normalized.account_state,
        checkpoint_state=checkpoint_state,
        preset_name=normalized.preset_name,
    )
    family_id = run_stats_progression_family_id(
        state_mode=normalized.state_mode,
        perks_enabled=normalized.perks_enabled,
    )
    response = resolve_checkpoint_consumer_bundle(
        patched_account_state,
        consumer_id=_BOSS_WAVE_CONSUMER_ID,
        bundle_id=_BOSS_WAVE_BUNDLE_ID,
        family_id=family_id,
        preset_name=normalized.preset_name,
        state_mode=normalized.state_mode,
        card_preset_name=normalized.card_preset_name,
        module_preset_name=normalized.module_preset_name,
        perk_preset_name=normalized.perk_preset_name,
        perks_enabled=normalized.perks_enabled,
        include_optional_surface_ids=_BOSS_WAVE_DAMAGE_BASIS_OPTIONAL_SURFACES,
        kernel=resolver._query_kernel,
    )
    statbook = query_response_to_statbook(
        response,
        notes='Resolved through simulator checkpoint consumer bundle.',
        diagnostics={
            'resolver_kind': 'simulator_checkpoint_progression_bundle',
            'qe_consumer_id': _BOSS_WAVE_CONSUMER_ID,
            'qe_bundle_id': _BOSS_WAVE_BUNDLE_ID,
            'family_id': family_id,
        },
    )
    elapsed_ms = round((perf_counter() - start) * 1000.0, 3)
    return _build_snapshot(
        normalized=normalized,
        statbook=statbook,
        patched_account_state=patched_account_state,
        elapsed_ms=elapsed_ms,
        qe_resolution_count=1,
    )


def resolve_wave_row_snapshot_delta(
    normalized: NormalizedCheckpointState,
    *,
    baseline_snapshot: WaveRowSnapshot,
    changed_tracks: tuple[str, ...],
) -> WaveRowSnapshot:
    start = perf_counter()
    resolver = SimulatorSnapshotResolver()
    checkpoint_state = _checkpoint_state_from_normalized(normalized)
    patched_account_state = resolver.patched_account_state(
        account_state=normalized.account_state,
        checkpoint_state=checkpoint_state,
        preset_name=normalized.preset_name,
    )
    family_id = run_stats_progression_family_id(
        state_mode=normalized.state_mode,
        perks_enabled=normalized.perks_enabled,
    )
    statbook = resolve_checkpoint_consumer_bundle_delta(
        base_statbook=baseline_snapshot.resolved_statbook,
        account_state=patched_account_state,
        consumer_id=_BOSS_WAVE_CONSUMER_ID,
        bundle_id=_BOSS_WAVE_BUNDLE_ID,
        family_id=family_id,
        preset_name=normalized.preset_name,
        state_mode=normalized.state_mode,
        card_preset_name=normalized.card_preset_name,
        module_preset_name=normalized.module_preset_name,
        perk_preset_name=normalized.perk_preset_name,
        perks_enabled=normalized.perks_enabled,
        mutation_class='workshop_mutation',
        trigger_keys=changed_tracks,
        include_optional_surface_ids=_BOSS_WAVE_DAMAGE_BASIS_OPTIONAL_SURFACES,
        kernel=resolver._query_kernel,
    )
    statbook.diagnostics.setdefault('resolver_kind', 'simulator_checkpoint_progression_bundle_delta')
    statbook.diagnostics.setdefault('qe_consumer_id', _BOSS_WAVE_CONSUMER_ID)
    statbook.diagnostics.setdefault('qe_bundle_id', _BOSS_WAVE_BUNDLE_ID)
    elapsed_ms = round((perf_counter() - start) * 1000.0, 3)
    return _build_snapshot(
        normalized=normalized,
        statbook=statbook,
        patched_account_state=patched_account_state,
        elapsed_ms=elapsed_ms,
        qe_resolution_count=1,
    )
