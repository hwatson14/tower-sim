from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from math import floor
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional

from simulators.perk_timeline_state import apply_perk_counts_to_account_state

from qe.stat_input_compiler import compile_stat_inputs
from simulators.incremental_cache_fingerprint import IncrementalCacheFingerprintBuilder
from simulators.incremental_cache_validator import IncrementalCacheValidator
from simulators.incremental_overlay_publisher import IncrementalOverlayPublisher
from simulators.incremental_parity_harness import IncrementalParityHarness
from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime
from simulators.incremental_subset_executor import IncrementalSubsetExecutor
from qe.materializer import FamilyBaselineContributorMap, FamilyBaselineMaterializer, load_family_surface_ids
from qe.consumer_registry import resolve_consumer_bundle
from simulators.runtime_consumer_executor import RuntimeConsumerExecutor
from qe.models import compile_stat_inputs_with_identity
from qe.kernel import QueryResponse, StatQueryKernel
from input.state_types import AccountState
from qe.models import StatInput
from qe.models import StatBook, StatRow
from simulators.contracts import DirtyLedger, ProjectedRunState, WaveCheckpoint
from simulators.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


_FREE_UPGRADE_CATEGORIES: tuple[str, ...] = ('attack', 'defense', 'utility')


def advance_projected_wave_state(
    state: ProjectedRunState,
    *,
    target_display_wave: int,
    attack_skip_pct: float,
    health_skip_pct: float,
    policy: WaveProgressionPolicy | None = None,
) -> ProjectedRunState:
    """Advance only the deterministic wave-progression portion of projected run state.

    This helper is intentionally narrow:
    - it treats workshop/perk state as unchanged carry-forward inputs
    - it advances only the attack/health wave plus skip counters
    - it keeps the caller in control of whether downstream QE/timing work is required
    """

    wave_policy = policy or WaveProgressionPolicy()
    prior_wave_state = WaveProgressionState(
        display_wave=int(state.wave_progression_state.get('display_wave', state.checkpoint.display_wave)),
        attack_wave=int(state.wave_progression_state.get('attack_wave', 0)),
        health_wave=int(state.wave_progression_state.get('health_wave', 0)),
        attack_skip_counter=float(state.wave_progression_state.get('attack_skip_counter', 0.0)),
        health_skip_counter=float(state.wave_progression_state.get('health_skip_counter', 0.0)),
    )
    next_wave_state = wave_policy.advance_to_wave(
        state=prior_wave_state,
        target_display_wave=int(target_display_wave),
        attack_skip_pct=float(attack_skip_pct),
        health_skip_pct=float(health_skip_pct),
    )
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(target_display_wave)),
        workshop_levels_current=dict(state.workshop_levels_current),
        perk_state=state.perk_state,
        wave_progression_state={
            'display_wave': next_wave_state.display_wave,
            'attack_wave': next_wave_state.attack_wave,
            'health_wave': next_wave_state.health_wave,
            'attack_skip_counter': next_wave_state.attack_skip_counter,
            'health_skip_counter': next_wave_state.health_skip_counter,
        },
        free_upgrade_state=dict(state.free_upgrade_state),
        counters=dict(state.counters),
        dirty_ledger=DirtyLedger(
            progression_dirty=False,
            qe_dirty=False,
            timing_dirty=False,
            geometry_dirty=state.dirty_ledger.geometry_dirty,
        ),
        notes=tuple(state.notes),
    )


def advance_projected_free_upgrade_state(
    state: ProjectedRunState,
    *,
    target_display_wave: int,
    free_attack_upgrade_chance_pct: float,
    free_defense_upgrade_chance_pct: float,
    free_utility_upgrade_chance_pct: float,
) -> ProjectedRunState:
    """Advance deterministic free-upgrade carry and counters without mutating workshop levels yet.

    This is the first progression-owned free-upgrade slice:
    - carry is accumulated wave-by-wave from the prior row
    - guaranteed upgrades are counted deterministically
    - workshop level allocation remains a later slice once the track-assignment contract is locked
    """

    start_wave = int(state.checkpoint.display_wave)
    end_wave = int(target_display_wave)
    if end_wave < start_wave:
        raise ValueError(f'target_display_wave {end_wave} cannot move backwards from {start_wave}')

    carry_by_category = {
        category: float((state.free_upgrade_state.get('carry_by_category') or {}).get(category, 0.0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    generated_by_category = {
        category: int((state.counters.get('generated_free_upgrades_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    chance_by_category = {
        'attack': max(0.0, float(free_attack_upgrade_chance_pct)) / 100.0,
        'defense': max(0.0, float(free_defense_upgrade_chance_pct)) / 100.0,
        'utility': max(0.0, float(free_utility_upgrade_chance_pct)) / 100.0,
    }

    generated_this_step = 0
    for _display_wave in range(start_wave + 1, end_wave + 1):
        for category in _FREE_UPGRADE_CATEGORIES:
            carry_by_category[category] += chance_by_category[category]
            guaranteed = int(floor(carry_by_category[category] + 1e-12))
            if guaranteed <= 0:
                continue
            carry_by_category[category] -= guaranteed
            generated_by_category[category] += guaranteed
            generated_this_step += guaranteed

    next_counters = dict(state.counters)
    next_counters['generated_free_upgrades_by_category'] = generated_by_category
    next_counters['generated_free_upgrades_last_step_by_category'] = {
        category: generated_by_category[category] - int((state.counters.get('generated_free_upgrades_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    next_counters['generated_free_upgrades_total'] = int(next_counters.get('generated_free_upgrades_total', 0)) + generated_this_step
    next_free_upgrade_state = dict(state.free_upgrade_state)
    next_free_upgrade_state['carry_by_category'] = carry_by_category
    next_free_upgrade_state['next_index_by_category'] = {
        category: int((state.free_upgrade_state.get('next_index_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }

    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=end_wave),
        workshop_levels_current=dict(state.workshop_levels_current),
        perk_state=state.perk_state,
        wave_progression_state=dict(state.wave_progression_state),
        free_upgrade_state=next_free_upgrade_state,
        counters=next_counters,
        dirty_ledger=DirtyLedger(
            progression_dirty=False,
            qe_dirty=False,
            timing_dirty=False,
            geometry_dirty=state.dirty_ledger.geometry_dirty,
        ),
        notes=tuple(state.notes),
    )


def allocate_generated_free_upgrades_to_workshop(
    state: ProjectedRunState,
    *,
    category_track_order: Mapping[str, list[str] | tuple[str, ...]],
    track_max_levels: Mapping[str, int],
    excluded_tracks: tuple[str, ...] = (),
) -> ProjectedRunState:
    """Apply last-step generated free upgrades to workshop levels in stable track order.

    The caller owns the category->track ordering contract. This helper only performs
    deterministic allocation and cursor advancement from the prior projected row state.
    """

    last_step_counts = {
        category: int((state.counters.get('generated_free_upgrades_last_step_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    next_index_by_category = {
        category: int((state.free_upgrade_state.get('next_index_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    allocated_by_category = {
        category: int((state.counters.get('allocated_free_upgrades_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    unallocated_by_category = {
        category: int((state.counters.get('unallocated_free_upgrades_by_category') or {}).get(category, 0))
        for category in _FREE_UPGRADE_CATEGORIES
    }
    workshop_levels_current = dict(state.workshop_levels_current)
    excluded = set(excluded_tracks)
    applied_any = False
    changed_tracks_last_step: list[str] = []

    for category in _FREE_UPGRADE_CATEGORIES:
        requested = last_step_counts[category]
        if requested <= 0:
            continue
        ordered_tracks = [
            track_name
            for track_name in category_track_order.get(category, ())
            if track_name not in excluded and track_name in workshop_levels_current and track_name in track_max_levels
        ]
        idx = next_index_by_category[category]
        for _ in range(requested):
            candidates = [
                track_name
                for track_name in ordered_tracks
                if int(workshop_levels_current[track_name]) < int(track_max_levels[track_name])
            ]
            if not candidates:
                unallocated_by_category[category] += 1
                continue
            chosen_index = idx % len(candidates)
            chosen_track = candidates[chosen_index]
            workshop_levels_current[chosen_track] = min(
                int(track_max_levels[chosen_track]),
                int(workshop_levels_current[chosen_track]) + 1,
            )
            allocated_by_category[category] += 1
            changed_tracks_last_step.append(chosen_track)
            idx = chosen_index + 1
            applied_any = True
        next_index_by_category[category] = idx

    next_counters = dict(state.counters)
    next_counters['allocated_free_upgrades_by_category'] = allocated_by_category
    next_counters['allocated_free_upgrades_total'] = sum(allocated_by_category.values())
    next_counters['unallocated_free_upgrades_by_category'] = unallocated_by_category
    next_counters['unallocated_free_upgrades_total'] = sum(unallocated_by_category.values())
    next_counters['changed_workshop_tracks_last_step'] = tuple(changed_tracks_last_step)
    next_free_upgrade_state = dict(state.free_upgrade_state)
    next_free_upgrade_state['next_index_by_category'] = next_index_by_category

    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(state.checkpoint.display_wave)),
        workshop_levels_current=workshop_levels_current,
        perk_state=state.perk_state,
        wave_progression_state=dict(state.wave_progression_state),
        free_upgrade_state=next_free_upgrade_state,
        counters=next_counters,
        dirty_ledger=DirtyLedger(
            progression_dirty=applied_any,
            qe_dirty=applied_any,
            timing_dirty=applied_any,
            geometry_dirty=state.dirty_ledger.geometry_dirty,
        ),
        notes=tuple(state.notes),
    )


@dataclass(frozen=True)
class ProgressionRecalcRequest:
    account_state: AccountState
    preset_name: str
    workshop_levels_current: Dict[str, int]
    card_preset_name: Optional[str] = None
    module_preset_name: Optional[str] = None
    perk_preset_name: Optional[str] = None
    perks_enabled: bool = True
    perk_counts_override: Optional[Dict[str, int]] = None
    state_mode: str = "start_of_run"
    recompute_mode: str = "full_safe"
    runtime_target_display_wave: Optional[int] = None
    cached_reference_statbook: Optional[StatBook] = None
    cached_reference_workshop_levels_current: Optional[Dict[str, int]] = None
    cached_reference_fingerprint: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ProgressionRecalcResult:
    patched_account_state: AccountState
    stat_inputs: List[StatInput]
    statbook: StatBook
    incremental_diagnostics: Dict[str, Any] | None = None


class ProgressionRecalcBridge:
    """Bridge between query-owned bounded progression execution modes.

    Bounded migrated publishable surfaces now flow through the planner + IncrementalSubsetExecutor path.
    Full-safe, fallback, cache-recovery, and parity-reference branches resolve against the
    declared bounded progression family reference used by the current query-owned runtime path.
    Remaining bridge follow-up is limited to transitional cleanup and acceptance evidence.
    """

    def apply_workshop_overrides(self, account_state: AccountState, *, preset_name: str, workshop_levels_current: Dict[str, int]) -> AccountState:
        if not workshop_levels_current:
            return account_state

        patched_workshop = dict(account_state.workshop)
        for track_name, requested_level in workshop_levels_current.items():
            if track_name not in patched_workshop:
                raise KeyError(f"Unknown workshop track in progression override: {track_name}")
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

    def _build_result(
        self,
        *,
        patched: AccountState,
        stat_inputs: List[StatInput],
        statbook: StatBook,
        diagnostics: Dict[str, Any],
        phase_timings: Dict[str, float],
    ) -> ProgressionRecalcResult:
        diagnostics = dict(diagnostics)
        diagnostics['phase_timing_ms'] = {
            **phase_timings,
            'total_measured_ms': round(sum(phase_timings.values()), 3),
        }
        return ProgressionRecalcResult(
            patched_account_state=patched,
            stat_inputs=stat_inputs,
            statbook=statbook,
            incremental_diagnostics=diagnostics,
        )

    def _runtime_publication_statbook(
        self,
        *,
        patched: AccountState,
        request: ProgressionRecalcRequest,
    ) -> StatBook:
        family_id = self._progression_family_id(request)
        response = resolve_progression_consumer_bundle(
            account_state=patched,
            consumer_id='progression_runtime',
            bundle_id='progression_wave_skips',
            family_id=family_id,
            preset_name=request.preset_name,
            state_mode=request.state_mode,
            perks_enabled=request.perks_enabled,
            trace_mode='contributors',
            card_preset_name=request.card_preset_name,
            module_preset_name=request.module_preset_name,
            perk_preset_name=request.perk_preset_name,
        )
        return self._query_response_to_statbook(
            response,
            notes='Bounded progression consumer bundle surface used for runtime publication.',
            diagnostics={'family_id': response.family_id},
        )

    @staticmethod
    def _progression_family_id(request: ProgressionRecalcRequest) -> str:
        return 'progression_runtime_with_perks' if request.perks_enabled else 'progression_runtime_no_perks'

    @staticmethod
    def _query_response_to_statbook(
        response: QueryResponse,
        *,
        notes: str,
        diagnostics: Dict[str, Any],
    ) -> StatBook:
        contributors_by_surface: dict[str, list[dict[str, object]]] = defaultdict(list)
        for contributor in response.contributor_rows:
            contributors_by_surface[contributor.surface_id].append(
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
                notes=notes,
                contributors=contributors_by_surface.get(row.surface_id, []),
            )
            for row in response.resolved_surface_rows
        }
        return StatBook(
            rows=rows,
            diagnostics=dict(diagnostics),
        )

    def _bounded_reference_statbook(
        self,
        *,
        patched: AccountState,
        request: ProgressionRecalcRequest,
    ) -> StatBook:
        family_id = self._progression_family_id(request)
        response = resolve_progression_family_query(
            account_state=patched,
            family_id=family_id,
            preset_name=request.preset_name,
            requested_surface_ids=tuple(sorted(load_family_surface_ids()[family_id])),
            state_mode=request.state_mode,
            perks_enabled=request.perks_enabled,
            runtime_branch_id='branch_base',
            trace_mode='contributors',
            card_preset_name=request.card_preset_name,
            module_preset_name=request.module_preset_name,
            perk_preset_name=request.perk_preset_name,
        )
        return self._query_response_to_statbook(
            response,
            notes='Bounded progression family surface used for recalc reference publication.',
            diagnostics={'family_id': response.family_id, 'source': 'bounded_progression_family_reference'},
        )

    def recompute(self, request: ProgressionRecalcRequest) -> ProgressionRecalcResult:
        phase_timings: Dict[str, float] = {}

        t = perf_counter()
        patched = self.apply_workshop_overrides(
            request.account_state,
            preset_name=request.preset_name,
            workshop_levels_current=request.workshop_levels_current,
        )
        phase_timings['apply_workshop_overrides'] = _elapsed_ms(t)

        if request.perk_counts_override is not None:
            t = perf_counter()
            patched = apply_perk_counts_to_account_state(
                patched,
                perk_counts=request.perk_counts_override,
            )
            phase_timings['apply_perk_counts_override'] = _elapsed_ms(t)

        t = perf_counter()
        stat_inputs = compile_stat_inputs(
            patched,
            preset_name=request.preset_name,
            state_mode=request.state_mode,
            card_preset_name=request.card_preset_name,
            module_preset_name=request.module_preset_name,
            perk_preset_name=request.perk_preset_name,
            perks_enabled=request.perks_enabled,
        )
        phase_timings['compile_stat_inputs'] = _elapsed_ms(t)

        runtime = IncrementalRecalcRuntime()
        t = perf_counter()
        plan = runtime.plan_from_workshop_overrides(request.workshop_levels_current)
        phase_timings['plan_from_workshop_overrides'] = _elapsed_ms(t)

        t = perf_counter()
        current_fingerprint = IncrementalCacheFingerprintBuilder().build(
            stat_inputs=stat_inputs,
            state_mode=request.state_mode,
            preset_name=request.preset_name,
            card_preset_name=request.card_preset_name,
            module_preset_name=request.module_preset_name,
            perk_preset_name=request.perk_preset_name,
            perks_enabled=request.perks_enabled,
            perk_counts_override=request.perk_counts_override,
        )
        phase_timings['build_cache_fingerprint'] = _elapsed_ms(t)

        if request.recompute_mode == 'full_safe':
            t = perf_counter()
            statbook = self._bounded_reference_statbook(patched=patched, request=request)
            phase_timings['resolve_bounded_reference'] = _elapsed_ms(t)
            diagnostics = {
                'mode': 'full_safe',
                'ownership_boundary': 'bounded_query_owned_declared_family_reference',
                'plan': plan.to_dict(),
                'cache_fingerprint': current_fingerprint.to_dict(),
            }
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                publication_statbook = self._runtime_publication_statbook(
                    patched=patched,
                    request=request,
                )
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=publication_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_bounded_progression_bundle',
                    'outputs': outputs.to_dict(),
                }
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=statbook,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        diagnostics: Dict[str, Any] = {
            'mode': request.recompute_mode,
            'ownership_boundary': 'bounded_query_owned_publishable_subset',
            'plan': plan.to_dict(),
            'runtime_consumers': plan.runtime_consumer_ids,
            'cache_fingerprint': current_fingerprint.to_dict(),
        }
        if plan.fallback_required:
            t = perf_counter()
            reference_statbook = self._bounded_reference_statbook(patched=patched, request=request)
            phase_timings['resolve_bounded_reference'] = _elapsed_ms(t)
            diagnostics['status'] = 'fallback_bounded_family_reference'
            diagnostics['ownership_boundary'] = 'bounded_query_owned_declared_family_reference'
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=reference_statbook,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        executor = IncrementalSubsetExecutor()
        t = perf_counter()
        candidate_rows = executor.execute(
            stat_inputs,
            plan.publishable_dirty_nodes,
            family_id=plan.family_id,
        )
        phase_timings['execute_candidate_subset'] = _elapsed_ms(t)
        diagnostics['candidate_nodes'] = sorted(candidate_rows.keys())

        if request.recompute_mode == 'incremental_targeted_probe_guarded':
            probe_statbook = StatBook(rows=dict(candidate_rows), diagnostics={
                'scope': 'partial_candidate_subset',
                'published_nodes': sorted(candidate_rows.keys()),
            })
            diagnostics['status'] = 'published_targeted_probe_subset'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                publication_statbook = self._runtime_publication_statbook(
                    patched=patched,
                    request=request,
                )
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=publication_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_bounded_progression_bundle',
                    'outputs': outputs.to_dict(),
                }
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=probe_statbook,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        if request.recompute_mode == 'incremental_cached_publish_guarded':
            t = perf_counter()
            cache_validation = IncrementalCacheValidator().validate(
                cached_statbook=request.cached_reference_statbook,
                cached_workshop_levels_current=request.cached_reference_workshop_levels_current,
                requested_workshop_levels_current=request.workshop_levels_current,
                mutated_workshop_keys=list(request.workshop_levels_current.keys()),
                cached_reference_fingerprint=request.cached_reference_fingerprint,
                current_fingerprint=current_fingerprint,
            )
            phase_timings['validate_cached_reference'] = _elapsed_ms(t)
            diagnostics['cache_validation'] = {
                'is_valid': cache_validation.is_valid,
                'reason': cache_validation.reason,
            }
            if not cache_validation.is_valid:
                t = perf_counter()
                reference_statbook = self._bounded_reference_statbook(patched=patched, request=request)
                phase_timings['resolve_bounded_reference'] = _elapsed_ms(t)
                diagnostics['status'] = 'fallback_bounded_family_reference'
                diagnostics['ownership_boundary'] = 'bounded_query_owned_declared_family_reference'
                return self._build_result(
                    patched=patched,
                    stat_inputs=stat_inputs,
                    statbook=reference_statbook,
                    diagnostics=diagnostics,
                    phase_timings=phase_timings,
                )
            t = perf_counter()
            published = IncrementalOverlayPublisher().publish(request.cached_reference_statbook, candidate_rows)
            phase_timings['publish_overlay'] = _elapsed_ms(t)
            diagnostics['status'] = 'published_candidate_overlay_over_cached_reference'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                publication_statbook = self._runtime_publication_statbook(
                    patched=patched,
                    request=request,
                )
                published_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=publication_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_bounded_progression_bundle',
                    'outputs': published_outputs.to_dict(),
                }
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=published,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        t = perf_counter()
        reference_statbook = self._bounded_reference_statbook(patched=patched, request=request)
        phase_timings['resolve_bounded_reference'] = _elapsed_ms(t)
        t = perf_counter()
        parity = IncrementalParityHarness().compare(candidate_rows, reference_statbook)
        phase_timings['compare_parity'] = _elapsed_ms(t)
        diagnostics['parity'] = {
            'status': parity.status,
            'compared_nodes': parity.compared_nodes,
            'mismatches': parity.mismatches,
        }

        if request.recompute_mode == 'incremental_parity_guarded':
            diagnostics['status'] = 'parity_only_bounded_family_return'
            diagnostics['ownership_boundary'] = 'bounded_query_owned_declared_family_reference'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                publication_statbook = self._runtime_publication_statbook(
                    patched=patched,
                    request=request,
                )
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=publication_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_bounded_progression_bundle',
                    'outputs': outputs.to_dict(),
                }
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=reference_statbook,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        if request.recompute_mode == 'incremental_publish_guarded' and parity.status == 'pass':
            t = perf_counter()
            published = IncrementalOverlayPublisher().publish(reference_statbook, candidate_rows)
            phase_timings['publish_overlay'] = _elapsed_ms(t)
            diagnostics['status'] = 'published_candidate_overlay_over_bounded_reference'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                reference_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=self._runtime_publication_statbook(
                        patched=patched,
                        request=request,
                    ),
                    target_display_wave=request.runtime_target_display_wave,
                )
                t = perf_counter()
                published_statbook = self._runtime_publication_statbook(
                    patched=patched,
                    request=request,
                )
                published_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=published_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'pass' if published_outputs.to_dict() == reference_outputs.to_dict() else 'mismatch',
                    'outputs': published_outputs.to_dict(),
                    'reference_outputs': reference_outputs.to_dict(),
                }
            return self._build_result(
                patched=patched,
                stat_inputs=stat_inputs,
                statbook=published,
                diagnostics=diagnostics,
                phase_timings=phase_timings,
            )

        diagnostics['status'] = 'fallback_bounded_family_reference'
        diagnostics['ownership_boundary'] = 'bounded_query_owned_declared_family_reference'
        return self._build_result(
            patched=patched,
            stat_inputs=stat_inputs,
            statbook=reference_statbook,
            diagnostics=diagnostics,
            phase_timings=phase_timings,
        )


def materialize_progression_family_baseline(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    materializer: FamilyBaselineMaterializer | None = None,
) -> FamilyBaselineContributorMap:
    query_materializer = materializer or FamilyBaselineMaterializer()
    query_materializer.assert_family_compatibility(
        family_id=family_id,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        scenario_mode_id='progression',
    )
    bound = compile_stat_inputs_with_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name or preset_name,
        module_preset_name=module_preset_name or preset_name,
        perk_preset_name=perk_preset_name or preset_name,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_context={'mode_id': 'progression'},
    )
    return query_materializer.materialize(bound, family_id)


def resolve_progression_family_query(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    requested_surface_ids: tuple[str, ...] | list[str],
    state_mode: str = 'start_of_run',
    perks_enabled: bool,
    runtime_branch_id: str = 'branch_base',
    trace_mode: str = 'contributors',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    query_kernel = kernel or StatQueryKernel()
    baseline = materialize_progression_family_baseline(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        materializer=query_kernel.materializer,
    )
    return query_kernel.resolve_surfaces(baseline, requested_surface_ids=requested_surface_ids, trace_mode=trace_mode)


def resolve_progression_consumer_bundle(
    *,
    account_state: AccountState,
    consumer_id: str,
    bundle_id: str,
    family_id: str,
    preset_name: str,
    perks_enabled: bool,
    include_optional_surface_ids: tuple[str, ...] | list[str] = (),
    state_mode: str = 'start_of_run',
    runtime_branch_id: str = 'branch_base',
    trace_mode: str | None = None,
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
) -> QueryResponse:
    resolved_bundle = resolve_consumer_bundle(
        consumer_id,
        bundle_id,
        family_id=family_id,
        include_optional_surface_ids=include_optional_surface_ids,
        trace_mode=trace_mode,
    )
    effective_trace_mode = resolved_bundle.minimum_trace_mode if trace_mode is None else str(trace_mode)
    return resolve_progression_family_query(
        account_state=account_state,
        family_id=family_id,
        preset_name=preset_name,
        requested_surface_ids=resolved_bundle.surface_ids,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        runtime_branch_id=runtime_branch_id,
        trace_mode=effective_trace_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        kernel=kernel,
    )
