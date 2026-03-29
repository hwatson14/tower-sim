from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from input.state_types import AccountState
from qe.routing import resolve_checkpoint_surfaces
from qe.shared_runtime_context import get_default_qe_shared_runtime_context
from simulators.contracts import SimulatorCheckpointResolution, SimulatorCheckpointState
from simulators.perks import apply_checkpoint_perk_state


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


class SimulatorSnapshotResolver:
    """Lightweight QE-backed row/checkpoint resolver for simulator snapshots."""

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

        resolved_values = {
            row.surface_id: row.final_value
            for row in response.resolved_surface_rows
        }
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
