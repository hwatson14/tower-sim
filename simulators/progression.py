from __future__ import annotations

from dataclasses import dataclass, replace
from math import floor
from time import perf_counter
from typing import Any, Dict, List, Optional

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
from qe.kernel import QueryResponse, StatQueryKernel, get_default_query_kernel
from qe.routing import QEResolutionPlanner
from input.state_types import AccountState
from qe.models import StatInput
from qe.models import StatBook
from simulators.contracts import DirtyLedger, ProjectedRunState, WaveCheckpoint
from simulators.wave_progression_policy import WaveProgressionPolicy, WaveProgressionState


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


def run_stats_progression_family_id(*, state_mode: str, perks_enabled: bool) -> str:
    if state_mode == 'start_of_run' and not perks_enabled:
        return 'progression_start_of_run'
    return 'progression_runtime_with_perks' if perks_enabled else 'progression_runtime_no_perks'


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
        planner = QEResolutionPlanner()
        bundle = resolve_consumer_bundle(
            'progression_runtime',
            'progression_wave_skips',
            family_id=family_id,
            trace_mode='contributors',
        )
        return planner.resolve_declared_family_statbook(
            patched,
            family_id=family_id,
            requested_surface_ids=bundle.surface_ids,
            notes='Bounded progression consumer bundle surface used for runtime publication.',
            diagnostics={'family_id': family_id},
            preset_name=request.preset_name,
            state_mode=request.state_mode,
            card_preset_name=request.card_preset_name or request.preset_name,
            module_preset_name=request.module_preset_name or request.preset_name,
            perk_preset_name=request.perk_preset_name or request.preset_name,
            perks_enabled=request.perks_enabled,
            trace_mode='contributors',
        )

    @staticmethod
    def _progression_family_id(request: ProgressionRecalcRequest) -> str:
        return 'progression_runtime_with_perks' if request.perks_enabled else 'progression_runtime_no_perks'

    def _bounded_reference_statbook(
        self,
        *,
        patched: AccountState,
        request: ProgressionRecalcRequest,
    ) -> StatBook:
        family_id = self._progression_family_id(request)
        planner = QEResolutionPlanner()
        return planner.resolve_declared_family_statbook(
            patched,
            family_id=family_id,
            requested_surface_ids=tuple(sorted(load_family_surface_ids()[family_id])),
            notes='Bounded progression family surface used for recalc reference publication.',
            diagnostics={'family_id': family_id, 'source': 'bounded_progression_family_reference'},
            preset_name=request.preset_name,
            state_mode=request.state_mode,
            card_preset_name=request.card_preset_name or request.preset_name,
            module_preset_name=request.module_preset_name or request.preset_name,
            perk_preset_name=request.perk_preset_name or request.preset_name,
            perks_enabled=request.perks_enabled,
            trace_mode='contributors',
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
    bound_stat_inputs=None,
) -> FamilyBaselineContributorMap:
    query_materializer = materializer or FamilyBaselineMaterializer()
    query_materializer.assert_family_compatibility(
        family_id=family_id,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
        scenario_mode_id='progression',
    )
    bound = bound_stat_inputs or compile_stat_inputs_with_identity(
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
    bound_stat_inputs=None,
    copy_result: bool = True,
) -> QueryResponse:
    query_kernel = kernel or get_default_query_kernel()
    if kernel is not None:
        query_kernel = kernel
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
            bound_stat_inputs=bound_stat_inputs,
        )
        return query_kernel.resolve_surfaces(baseline, requested_surface_ids=requested_surface_ids, trace_mode=trace_mode)

    planner = QEResolutionPlanner()
    if bound_stat_inputs is not None:
        result = planner.resolve_bound_declared_family_query(
            bound_stat_inputs,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            trace_mode=trace_mode,
            copy_result=copy_result,
        )
    else:
        result = planner.resolve_declared_family_query(
            account_state,
            family_id=family_id,
            requested_surface_ids=requested_surface_ids,
            preset_name=preset_name,
            state_mode=state_mode,
            card_preset_name=card_preset_name or preset_name,
            module_preset_name=module_preset_name or preset_name,
            perk_preset_name=perk_preset_name or preset_name,
            perks_enabled=perks_enabled,
            trace_mode=trace_mode,
        )
    return result.response


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
    bound_stat_inputs=None,
    copy_result: bool = True,
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
        bound_stat_inputs=bound_stat_inputs,
        copy_result=copy_result,
    )


def resolve_run_stats_progression_bundle(
    *,
    account_state: AccountState,
    family_id: str,
    preset_name: str,
    perks_enabled: bool,
    state_mode: str = 'start_of_run',
    runtime_branch_id: str = 'branch_base',
    trace_mode: str | None = None,
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    kernel: StatQueryKernel | None = None,
    bound_stat_inputs=None,
    copy_result: bool = True,
) -> QueryResponse:
    """Resolve the sanctioned bounded progression bundle for the run_stats consumer."""
    return resolve_progression_consumer_bundle(
        account_state=account_state,
        consumer_id='run_stats',
        bundle_id='progression_core_stats',
        family_id=family_id,
        include_optional_surface_ids=(
            'state::cards.berserker.assumed_bonus_multiplier',
            'state::uw.black_hole.base_duration_seconds',
            'state::uw.black_hole.base_cooldown_seconds',
            'state::uw.golden_tower.base_duration_seconds',
            'state::uw.golden_tower.base_cooldown_seconds',
            'support_surface::ehp.health_relic_pct',
            'support_surface::ehp.dabs_relic_pct',
            'support_surface::ehp.def_pct_relic_pct',
            'support_surface::eecon.adstarter_theme_relic_factor',
            'support_surface::eecon.freeup_attack_relic_pct',
            'support_surface::eecon.freeup_defense_relic_pct',
            'support_surface::eecon.freeup_utility_relic_pct',
            'support_surface::ehp.black_hole_duration_seconds',
            'support_surface::ehp.black_hole_cooldown_seconds',
        ),
        preset_name=preset_name,
        perks_enabled=perks_enabled,
        state_mode=state_mode,
        runtime_branch_id=runtime_branch_id,
        trace_mode=trace_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        kernel=kernel,
        bound_stat_inputs=bound_stat_inputs,
        copy_result=copy_result,
    )


def advance_projected_wave_state(
    state: ProjectedRunState,
    *,
    target_display_wave: int,
    attack_skip_pct: float,
    health_skip_pct: float,
    policy: WaveProgressionPolicy | None = None,
) -> ProjectedRunState:
    policy = policy or WaveProgressionPolicy()
    current = dict(state.wave_progression_state or {})
    start_display_wave = int(current.get('display_wave', state.checkpoint.display_wave))
    attack_wave = int(current.get('attack_wave', start_display_wave))
    health_wave = int(current.get('health_wave', start_display_wave))
    attack_skip_counter = float(current.get('attack_skip_counter', 0.0))
    health_skip_counter = float(current.get('health_skip_counter', 0.0))
    next_state = policy.advance_to_wave(
        state=WaveProgressionState(
            display_wave=start_display_wave,
            attack_wave=attack_wave,
            health_wave=health_wave,
            attack_skip_counter=attack_skip_counter,
            health_skip_counter=health_skip_counter,
        ),
        target_display_wave=int(target_display_wave),
        attack_skip_pct=float(max(0.0, min(1.0, attack_skip_pct))),
        health_skip_pct=float(max(0.0, min(1.0, health_skip_pct))),
    )
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(target_display_wave)),
        workshop_levels_current=dict(state.workshop_levels_current),
        perk_state=state.perk_state,
        wave_progression_state={
            'display_wave': int(next_state.display_wave),
            'attack_wave': int(next_state.attack_wave),
            'health_wave': int(next_state.health_wave),
            'attack_skip_counter': float(next_state.attack_skip_counter),
            'health_skip_counter': float(next_state.health_skip_counter),
        },
        free_upgrade_state=dict(state.free_upgrade_state),
        counters=dict(state.counters),
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=False, timing_dirty=False),
        notes=state.notes,
    )


def advance_projected_free_upgrade_state(
    state: ProjectedRunState,
    *,
    target_display_wave: int,
    free_attack_upgrade_chance_pct: float,
    free_defense_upgrade_chance_pct: float,
    free_utility_upgrade_chance_pct: float,
) -> ProjectedRunState:
    start_display_wave = int((state.wave_progression_state or {}).get('display_wave', state.checkpoint.display_wave))
    wave_count = max(0, int(target_display_wave) - start_display_wave)
    free_upgrade_state = dict(state.free_upgrade_state)
    carry_by_category = {
        'attack': float((free_upgrade_state.get('carry_by_category') or {}).get('attack', 0.0)),
        'defense': float((free_upgrade_state.get('carry_by_category') or {}).get('defense', 0.0)),
        'utility': float((free_upgrade_state.get('carry_by_category') or {}).get('utility', 0.0)),
    }
    generated_last_step = {'attack': 0, 'defense': 0, 'utility': 0}
    chance_map = {
        'attack': float(free_attack_upgrade_chance_pct) / 100.0,
        'defense': float(free_defense_upgrade_chance_pct) / 100.0,
        'utility': float(free_utility_upgrade_chance_pct) / 100.0,
    }
    for _ in range(wave_count):
        for category, per_wave_rate in chance_map.items():
            carry_by_category[category] += per_wave_rate
            guaranteed = int(floor(carry_by_category[category] + 1e-12))
            if guaranteed > 0:
                generated_last_step[category] += guaranteed
                carry_by_category[category] -= guaranteed
    counters = dict(state.counters)
    cumulative = dict(counters.get('generated_free_upgrades_by_category') or {})
    for category in ('attack', 'defense', 'utility'):
        cumulative[category] = int(cumulative.get(category, 0) or 0) + int(generated_last_step[category])
    counters['generated_free_upgrades_by_category'] = cumulative
    counters['generated_free_upgrades_last_step_by_category'] = generated_last_step
    counters['generated_free_upgrades_total'] = sum(int(v) for v in generated_last_step.values())
    free_upgrade_state['carry_by_category'] = carry_by_category
    free_upgrade_state.setdefault('next_index_by_category', {'attack': 0, 'defense': 0, 'utility': 0})
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(target_display_wave)),
        workshop_levels_current=dict(state.workshop_levels_current),
        perk_state=state.perk_state,
        wave_progression_state=dict(state.wave_progression_state),
        free_upgrade_state=free_upgrade_state,
        counters=counters,
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=False, timing_dirty=False),
        notes=state.notes,
    )


def allocate_generated_free_upgrades_to_workshop(
    state: ProjectedRunState,
    *,
    category_track_order: Dict[str, list[str]],
    track_max_levels: Dict[str, int],
) -> ProjectedRunState:
    workshop_levels = dict(state.workshop_levels_current)
    free_upgrade_state = dict(state.free_upgrade_state)
    next_index_by_category = {
        'attack': int((free_upgrade_state.get('next_index_by_category') or {}).get('attack', 0)),
        'defense': int((free_upgrade_state.get('next_index_by_category') or {}).get('defense', 0)),
        'utility': int((free_upgrade_state.get('next_index_by_category') or {}).get('utility', 0)),
    }
    generated_last_step = dict(state.counters.get('generated_free_upgrades_last_step_by_category') or {})
    allocated_by_category = {'attack': 0, 'defense': 0, 'utility': 0}
    unallocated_by_category = {'attack': 0, 'defense': 0, 'utility': 0}
    changed_tracks: list[str] = []

    for category in ('attack', 'defense', 'utility'):
        track_order = list(category_track_order.get(category) or [])
        generated = int(generated_last_step.get(category, 0) or 0)
        for _ in range(generated):
            candidates = [track for track in track_order if int(workshop_levels.get(track, 0)) < int(track_max_levels.get(track, 0))]
            if not candidates:
                unallocated_by_category[category] += 1
                continue
            idx = next_index_by_category[category] % len(candidates)
            track_name = candidates[idx]
            workshop_levels[track_name] = int(workshop_levels.get(track_name, 0)) + 1
            allocated_by_category[category] += 1
            if track_name not in changed_tracks:
                changed_tracks.append(track_name)
            next_index_by_category[category] += 1
        if len(track_order) > 1:
            next_index_by_category[category] %= len(track_order)
    counters = dict(state.counters)
    counters['allocated_free_upgrades_by_category'] = allocated_by_category
    counters['unallocated_free_upgrades_by_category'] = unallocated_by_category
    counters['allocated_free_upgrades_total'] = sum(allocated_by_category.values())
    counters['unallocated_free_upgrades_total'] = sum(unallocated_by_category.values())
    counters['changed_workshop_tracks_last_step'] = tuple(changed_tracks)
    free_upgrade_state['next_index_by_category'] = next_index_by_category
    changed = bool(changed_tracks)
    return ProjectedRunState(
        checkpoint=WaveCheckpoint(display_wave=int(state.checkpoint.display_wave)),
        workshop_levels_current=workshop_levels,
        perk_state=state.perk_state,
        wave_progression_state=dict(state.wave_progression_state),
        free_upgrade_state=free_upgrade_state,
        counters=counters,
        dirty_ledger=DirtyLedger(progression_dirty=True, qe_dirty=changed, timing_dirty=changed),
        notes=state.notes,
    )
