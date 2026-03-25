from __future__ import annotations

from collections.abc import Sequence

from engine.state_identity import StateIdentity
from engine.stat_query_kernel import QueryResponse, StatQueryKernel
from engine.stat_resolution_core import (
    _canonical_source_multiplier,
    _multiplier_from_value,
    resolve_stats as _fallback_resolve_stats,
)
from models.stat_input import StatInput
from models.statbook import StatBook, StatRow

# Declared preset → family map.  Contract source: stat-query-scenario-families.yaml.
# Extend this map (not the heuristic logic) when new timing families reach live delegation.
_TIMING_PRESET_TO_FAMILY: dict[str, str] = {
    'Tourney': 'timing_tournament_no_perks',
}

_DELEGATED_FAMILY_SURFACE_IDS: dict[str, tuple[str, ...]] = {
    'timing_tournament_no_perks': (
        'mechanic_param::uw.black_hole.cooldown_seconds',
        'mechanic_param::uw.black_hole.duration_seconds',
        'mechanic_param::uw.golden_tower.cooldown_seconds',
        'mechanic_param::uw.golden_tower.duration_seconds',
        'state::tower.package_chance_pct',
        'support_surface::timing.gcomp_cooldown_reduction_seconds',
        'support_surface::timing.wave_duration_seconds_effective',
        'state::cards.wave_accelerator.spawn_rate_acceleration',
    ),
}
def resolve_stats(stat_inputs: list[StatInput]) -> StatBook:
    fallback_statbook = _fallback_resolve_stats(stat_inputs)
    delegated_family_id = _infer_manifest_approved_family(stat_inputs)
    if delegated_family_id is None:
        return fallback_statbook

    delegated_response = _resolve_manifest_approved_family(
        family_id=delegated_family_id,
        stat_inputs=stat_inputs,
    )
    return _merge_delegated_family_rows(
        fallback_statbook=fallback_statbook,
        delegated_response=delegated_response,
        family_id=delegated_family_id,
    )


def _infer_manifest_approved_family(stat_inputs: Sequence[StatInput]) -> str | None:
    preset_names = {str(row.preset_name).strip() for row in stat_inputs if row.preset_name}
    if len(preset_names) != 1:
        return None
    return _TIMING_PRESET_TO_FAMILY.get(next(iter(preset_names)))


def _resolve_manifest_approved_family(*, family_id: str, stat_inputs: Sequence[StatInput]) -> QueryResponse:
    if family_id not in _DELEGATED_FAMILY_SURFACE_IDS:
        raise ValueError(f'Unsupported manifest-approved resolve_stats delegation family {family_id!r}.')
    query_kernel = StatQueryKernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        StateIdentity(
            account_snapshot_id='resolve_stats_compatibility_entrypoint',
            loadout_id='resolve_stats_tourney_loadout',
            scenario_id='resolve_stats_timing_tournament_no_perks',
            runtime_branch_id='branch_base',
        ),
        family_id,
        stat_inputs,
    )
    return query_kernel.resolve_surfaces(
        baseline,
        requested_surface_ids=_DELEGATED_FAMILY_SURFACE_IDS[family_id],
        trace_mode='contributors',
    )


def _merge_delegated_family_rows(
    *,
    fallback_statbook: StatBook,
    delegated_response: QueryResponse,
    family_id: str,
) -> StatBook:
    merged_rows = dict(fallback_statbook.rows)
    for row in delegated_response.resolved_surface_rows:
        if row.surface_id not in fallback_statbook.rows:
            continue
        merged_rows[row.surface_id] = StatRow(
            stat_name=row.surface_id,
            final_value=row.final_value,
            value_type=row.value_type,
            source_count=len([contributor for contributor in delegated_response.contributor_rows if contributor.surface_id == row.surface_id]),
            status=row.status,
            notes=f'Delegated through query kernel for manifest-approved family {family_id}.',
            contributors=[
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
                for contributor in delegated_response.contributor_rows
                if contributor.surface_id == row.surface_id
            ],
            schema={'delegated_family_id': family_id, 'source': 'query_kernel'},
        )
    diagnostics = dict(fallback_statbook.diagnostics)
    diagnostics['resolve_stats_delegation'] = {
        'delegated_family_id': family_id,
        'delegated_surface_ids': list(_DELEGATED_FAMILY_SURFACE_IDS[family_id]),
        'undelegated_fallback_owner': 'engine.stat_resolution_core.resolve_stats',
        'bounded_only': True,
    }
    return StatBook(rows=merged_rows, diagnostics=diagnostics)
__all__ = [
    'resolve_stats',
    '_multiplier_from_value',
    '_canonical_source_multiplier',
]
