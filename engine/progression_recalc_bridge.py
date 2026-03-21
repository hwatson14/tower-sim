from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any, Dict, List, Optional

from engine.perk_timeline_state import apply_perk_counts_to_account_state

from compilers.stat_input_compiler import compile_stat_inputs
from engine.incremental_cache_fingerprint import IncrementalCacheFingerprintBuilder
from engine.incremental_cache_validator import IncrementalCacheValidator
from engine.incremental_overlay_publisher import IncrementalOverlayPublisher
from engine.incremental_parity_harness import IncrementalParityHarness
from engine.incremental_recalc_runtime import IncrementalRecalcRuntime
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.runtime_consumer_executor import RuntimeConsumerExecutor
from engine.stat_engine import resolve_stats
from models.account_state import AccountState
from models.stat_input import StatInput
from models.statbook import StatBook


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


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
    """Safe bridge: progression mutates workshop state, then delegates all stat resolution back to the stat engine pipeline."""

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
            statbook = resolve_stats(stat_inputs)
            phase_timings['resolve_stats'] = _elapsed_ms(t)
            diagnostics = {
                'mode': 'full_safe',
                'plan': plan.to_dict(),
                'cache_fingerprint': current_fingerprint.to_dict(),
            }
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_full_safe_reference',
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
            'plan': plan.to_dict(),
            'runtime_consumers': plan.runtime_consumer_ids,
            'cache_fingerprint': current_fingerprint.to_dict(),
        }
        if plan.fallback_required:
            t = perf_counter()
            reference_statbook = resolve_stats(stat_inputs)
            phase_timings['resolve_stats'] = _elapsed_ms(t)
            diagnostics['status'] = 'fallback_full_safe'
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
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=probe_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_probe_subset',
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
                reference_statbook = resolve_stats(stat_inputs)
                phase_timings['resolve_stats'] = _elapsed_ms(t)
                diagnostics['status'] = 'fallback_full_safe'
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
                published_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=published,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_cached_overlay',
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
        reference_statbook = resolve_stats(stat_inputs)
        phase_timings['resolve_stats'] = _elapsed_ms(t)
        t = perf_counter()
        parity = IncrementalParityHarness().compare(candidate_rows, reference_statbook)
        phase_timings['compare_parity'] = _elapsed_ms(t)
        diagnostics['parity'] = {
            'status': parity.status,
            'compared_nodes': parity.compared_nodes,
            'mismatches': parity.mismatches,
        }

        if request.recompute_mode == 'incremental_parity_guarded':
            diagnostics['status'] = 'parity_only_full_safe_return'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                t = perf_counter()
                outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=reference_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                phase_timings['execute_runtime_publication'] = _elapsed_ms(t)
                diagnostics['runtime_publication'] = {
                    'status': 'published_from_full_safe_reference',
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
            diagnostics['status'] = 'published_candidate_overlay_over_full_reference'
            if request.runtime_target_display_wave is not None and plan.runtime_consumer_ids:
                reference_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=reference_statbook,
                    target_display_wave=request.runtime_target_display_wave,
                )
                t = perf_counter()
                published_outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(
                    statbook=published,
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

        diagnostics['status'] = 'fallback_full_safe'
        return self._build_result(
            patched=patched,
            stat_inputs=stat_inputs,
            statbook=reference_statbook,
            diagnostics=diagnostics,
            phase_timings=phase_timings,
        )
