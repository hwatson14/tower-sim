from __future__ import annotations

from collections.abc import Sequence

from qe.contracts import to_v2_surface_id
from qe.models import StateIdentity
from qe.kernel import QueryResponse, StatQueryKernel
from engine.stat_resolution_core import (
    _canonical_source_multiplier,
    _multiplier_from_value,
    resolve_stats as _fallback_resolve_stats,
)
from qe.models import StatInput
from qe.models import StatBook, StatRow

_TIMING_TOURNAMENT_NO_PERKS = 'timing_tournament_no_perks'
_TIMING_FARM_WITH_PERKS = 'timing_farm_with_perks'
_PROGRESSION_START_OF_RUN = 'progression_start_of_run'
_PROGRESSION_RUNTIME_WITH_PERKS = 'progression_runtime_with_perks'

# Canonical timing-v1 surface IDs declared in stat-query-initial-surface-set.yaml (timing_v1 group).
# All declared timing families share this surface set.
# wave_accelerator uses state:: (canonical per naming-contract-pack-v2-remap.csv and KB contracts),
# not the legacy runtime_mechanic_param:: prefix.
_TIMING_V1_SURFACE_IDS: tuple[str, ...] = (
    'mechanic_param::uw.black_hole.cooldown_seconds',
    'mechanic_param::uw.black_hole.duration_seconds',
    'mechanic_param::uw.golden_tower.cooldown_seconds',
    'mechanic_param::uw.golden_tower.duration_seconds',
    'state::tower.package_chance_pct',
    'support_surface::timing.gcomp_cooldown_reduction_seconds',
    'support_surface::timing.wave_duration_seconds_effective',
    'state::cards.wave_accelerator.spawn_rate_acceleration',
)

# Declared progression-family surface set. All three declared progression families share the
# same surface denominator at the flat statbook compatibility boundary; their semantic split
# only matters once bounded runtime/overlay execution begins inside the QE-owned progression stack.
_PROGRESSION_V1_SURFACE_IDS: tuple[str, ...] = (
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
    'mechanic_param::module.black_hole_digestor.extra_coin_kill_bonus_per_free_upgrade_pct',
    'mechanic_param::module.primordial_collapse.bh_damage_reduction_pct',
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'support_surface::free_upgrade_multiplier',
)

_TIMING_SURFACE_IDS: tuple[str, ...] = _TIMING_V1_SURFACE_IDS
_PROGRESSION_SURFACE_ID_SET = frozenset(_PROGRESSION_V1_SURFACE_IDS)

_DELEGATED_FAMILY_SURFACE_IDS: dict[str, tuple[str, ...]] = {
    _TIMING_TOURNAMENT_NO_PERKS: _TIMING_V1_SURFACE_IDS,
    _TIMING_FARM_WITH_PERKS: _TIMING_V1_SURFACE_IDS,
    # timing_scenario_probe surface set declared; not in _TIMING_FAMILY_BY_PRESET because it
    # shares the 'Farming' preset with timing_farm_with_perks (no fixed detection convention).
    'timing_scenario_probe': _TIMING_V1_SURFACE_IDS,
    # progression_start_of_run is the flat-statbook compatibility contract used by resolve_stats().
    # progression_runtime_no_perks shares this exact bounded surface set and remains QE-owned
    # through the direct progression helpers and runtime-consumer bundles.
    _PROGRESSION_START_OF_RUN: _PROGRESSION_V1_SURFACE_IDS,
    _PROGRESSION_RUNTIME_WITH_PERKS: _PROGRESSION_V1_SURFACE_IDS,
}

# Unambiguous preset-name → declared timing family mapping used by _infer_manifest_approved_family.
# timing_scenario_probe is not included: it has no fixed preset-name convention and is not
# delegated through the resolve_stats compatibility entrypoint in PH4-B.
_TIMING_FAMILY_BY_PRESET: dict[str, str] = {
    'Tourney': _TIMING_TOURNAMENT_NO_PERKS,
    'Farming': _TIMING_FARM_WITH_PERKS,
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

    preset_name = next(iter(preset_names))
    has_timing_rows = any(row.source_family == 'scenario_rules' for row in stat_inputs)
    if has_timing_rows:
        return _TIMING_FAMILY_BY_PRESET.get(preset_name)

    if _looks_like_progression_family_rows(stat_inputs):
        # Flat stat_inputs do not preserve enough metadata to distinguish
        # progression_start_of_run from progression_runtime_no_perks. The shared bounded
        # surface contract is still QE-owned, so the compatibility entrypoint delegates
        # against the start-of-run contract unless explicit perk rows are present.
        if any(row.source_family == 'perk' for row in stat_inputs):
            return _PROGRESSION_RUNTIME_WITH_PERKS
        return _PROGRESSION_START_OF_RUN

    return None


def _looks_like_progression_family_rows(stat_inputs: Sequence[StatInput]) -> bool:
    return any(_normalized_surface_id(row) in _PROGRESSION_SURFACE_ID_SET for row in stat_inputs)


def _normalized_surface_id(row: StatInput) -> str | None:
    if not row.destination_object_type or not row.destination_id:
        return None
    return to_v2_surface_id(f'{row.destination_object_type}::{row.destination_id}')


def _resolve_manifest_approved_family(*, family_id: str, stat_inputs: Sequence[StatInput]) -> QueryResponse:
    if family_id not in _DELEGATED_FAMILY_SURFACE_IDS:
        raise ValueError(f'Unsupported manifest-approved resolve_stats delegation family {family_id!r}.')
    query_kernel = StatQueryKernel()
    baseline = query_kernel.materializer.materialize_from_rows(
        StateIdentity(
            account_snapshot_id='resolve_stats_compatibility_entrypoint',
            loadout_id=f'resolve_stats_{family_id}_loadout',
            scenario_id=f'resolve_stats_{family_id}',
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
    if family_id == _PROGRESSION_START_OF_RUN:
        diagnostics['resolve_stats_delegation']['compat_equivalent_declared_families'] = [
            'progression_start_of_run',
            'progression_runtime_no_perks',
        ]
    return StatBook(rows=merged_rows, diagnostics=diagnostics)


__all__ = [
    'resolve_stats',
    '_multiplier_from_value',
    '_canonical_source_multiplier',
]
