from __future__ import annotations

from time import perf_counter
from typing import Dict

from qe.kernel import StatQueryKernel
from qe.routing import resolve_checkpoint_surfaces
from simulators.contracts import (
    NormalizedCheckpointState,
    PerformanceMetrics,
    WaveRowSnapshot,
)
from simulators.scenario import config_from_statbook, compute_scenario_surfaces
from simulators.timing import compute_timing_surfaces, resolve_combat_runtime_surfaces
from simulators.perk_timeline_state import apply_perk_counts_to_account_state


def _row_map_to_statbook_dict(statbook) -> Dict[str, Dict[str, object]]:
    return {
        surface_id: {
            "final_value": row.final_value,
            "value_type": row.value_type,
            "status": row.status,
        }
        for surface_id, row in statbook.rows.items()
    }


_CHECKPOINT_SURFACE_IDS: tuple[str, ...] = (
    'state::tower.hp',
    'state::wall.hp',
    'state::wall.regen',
    'state::wall.fortification_multiplier',
    'state::tower.defense_pct',
    'state::tower.thorns_damage_pct',
    'state::tower.orb_count',
    'state::tower.orb_speed_rpm',
    'state::cards.plasma_cannon.effect_pct',
    'mechanic_param::module.orbital_augment.electron_count',
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
)


_QUERY_KERNEL = StatQueryKernel()


def _patched_account_state(normalized: NormalizedCheckpointState):
    account_state = normalized.account_state
    projected = normalized.projected_run_state
    if projected.workshop_levels_current:
        patched_workshop = dict(account_state.workshop)
        for track_name, requested_level in projected.workshop_levels_current.items():
            if track_name not in patched_workshop:
                continue
            entry = patched_workshop[track_name]
            patched_levels = dict(entry.preset_levels)
            patched_levels[normalized.preset_name] = int(requested_level)
            patched_workshop[track_name] = type(entry)(
                **{**entry.__dict__, 'preset_levels': patched_levels}
            )
        account_state = type(account_state)(**{**account_state.__dict__, 'workshop': patched_workshop})
    if projected.perk_state.counts:
        account_state = apply_perk_counts_to_account_state(
            account_state,
            perk_counts=projected.perk_state.counts,
        )
    return account_state


def resolve_wave_row_snapshot(
    normalized: NormalizedCheckpointState,
) -> WaveRowSnapshot:
    """Resolve one wave row through the sanctioned simulator -> QE seam."""
    start = perf_counter()
    projected = normalized.projected_run_state
    patched_account_state = _patched_account_state(normalized)
    response = resolve_checkpoint_surfaces(
        patched_account_state,
        requested_surface_ids=_CHECKPOINT_SURFACE_IDS,
        preset_name=normalized.preset_name,
        state_mode=normalized.state_mode,
        card_preset_name=normalized.card_preset_name,
        module_preset_name=normalized.module_preset_name,
        perk_preset_name=normalized.perk_preset_name,
        perks_enabled=normalized.perks_enabled,
        scenario_runtime_inputs=normalized.scenario_runtime_inputs,
        kernel=_QUERY_KERNEL,
    )
    statbook = _query_response_to_statbook(response)
    statbook_dict = _row_map_to_statbook_dict(statbook)
    scenario_config = config_from_statbook(
        statbook_dict,
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
    elapsed_ms = (perf_counter() - start) * 1000.0
    return WaveRowSnapshot(
        checkpoint=normalized.checkpoint,
        projected_run_state=projected,
        resolved_statbook=statbook,
        scenario_context=scenario_context,
        timing_context=timing_context,
        geometry_context={},
        combat_runtime=combat_runtime,
        metrics=PerformanceMetrics(
            row_resolution_ms=elapsed_ms,
            qe_resolution_count=1,
            timing_recompute_count=1,
            geometry_recompute_count=0,
        ),
    )


def _query_response_to_statbook(response):
    from qe.models import StatBook, StatRow

    contributors_by_surface: dict[str, list[dict[str, object]]] = {}
    for contributor in response.contributor_rows:
        contributors_by_surface.setdefault(contributor.surface_id, []).append(
            {
                'surface_id': contributor.surface_id,
                'surface_class': contributor.surface_class,
                'domain': contributor.domain,
                'source_class': contributor.source_class,
                'composition_stage': contributor.composition_stage,
                'contributor_id': contributor.contributor_id,
                'value': contributor.value,
                'value_type': contributor.value_type,
                'active': contributor.active,
                'gate_reason': contributor.gate_reason,
                'provenance_ref': contributor.provenance_ref,
            }
        )
    rows = {
        row.surface_id: StatRow(
            stat_name=row.surface_id,
            final_value=row.final_value,
            value_type=row.value_type,
            source_count=len(contributors_by_surface.get(row.surface_id, ())),
            status=row.status,
            notes='Resolved through lightweight simulator checkpoint QE seam.',
            contributors=contributors_by_surface.get(row.surface_id, []),
        )
        for row in response.resolved_surface_rows
    }
    return StatBook(
        rows=rows,
        diagnostics={'source': 'simulator_checkpoint_qe_light', 'family_id': response.family_id},
    )
