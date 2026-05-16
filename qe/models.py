"""
qe/models.py — Typed stat/query model structs. AUTHORITY.

Extracted from: models/stat_input.py, models/statbook.py,
models/bound_preset_family.py, engine/state_identity.py (T3).
Owns: StatInput, StatRow, StatBook, BoundPresetFamily, bind_preset_family,
StateIdentity, StateIdentityBinding, BoundStatInputs, bind_state_identity,
compile_stat_inputs_with_identity.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from input.state_types import ScenarioProjectionState, ScenarioRuntimeInputs, projection_state_for_mode
from input.state_types import AccountState, ModulePresetSelection, PerkSelection
from qe.contracts import normalize_preset_name, sanitize_preset_name_for_canonical_output


# ---------------------------------------------------------------------------
# StatInput — from models/stat_input.py
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StatInput:
    stat_name: str
    source_family: str
    source_name: str
    value: Any
    value_type: str
    stage: str
    active: bool = True
    preset_name: Optional[str] = None
    provenance: Optional[str] = None
    notes: Optional[str] = None
    contributor_id: Optional[str] = None
    destination_object_type: Optional[str] = None
    destination_id: Optional[str] = None
    resolver_id: Optional[str] = None
    kb_mapped: bool = False
    raw_level: Optional[int] = None
    resolved_value: Optional[float] = None
    resolved_unit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# StatRow, StatBook — from models/statbook.py
# ---------------------------------------------------------------------------

@dataclass
class StatRow:
    stat_name: str
    final_value: Any
    value_type: str
    source_count: int
    status: str = 'unresolved'
    notes: Optional[str] = None
    contributors: List[Dict[str, Any]] = field(default_factory=list)
    schema: Dict[str, Any] | None = None


@dataclass
class StatBook:
    rows: Dict[str, StatRow]
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rows': {k: asdict(v) for k, v in self.rows.items()},
            'diagnostics': self.diagnostics,
        }


# ---------------------------------------------------------------------------
# BoundPresetFamily — from models/bound_preset_family.py
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BoundPresetFamily:
    preset_name: str
    card_preset_name: str
    module_preset_name: str
    perk_preset_name: Optional[str]
    perk_namespace_class: str
    state_mode: str
    perks_enabled: bool


def bind_preset_family(
    *,
    preset_name: str,
    state_mode: str,
    perk_namespace_class: str,
    explicit_card_preset_name: Optional[str],
    explicit_module_preset_name: Optional[str],
    explicit_perk_preset_name: Optional[str],
    active_perk_preset_name: Optional[str],
    perks_enabled: Optional[bool],
) -> BoundPresetFamily:
    canonical_preset = normalize_preset_name(preset_name, allow_aliases=False)
    if canonical_preset is None:
        raise ValueError(f"preset_name must be canonical, got {preset_name!r}.")

    card_preset = _bind_loadout_lane('card_preset_name', explicit_card_preset_name, canonical_preset)
    module_preset = _bind_loadout_lane('module_preset_name', explicit_module_preset_name, canonical_preset)

    perk_preset = explicit_perk_preset_name or active_perk_preset_name
    if perk_preset is not None:
        perk_preset = perk_preset.strip()
        if not perk_preset:
            perk_preset = None

    if perk_namespace_class != 'transient' and perk_preset is not None:
        normalized = normalize_preset_name(perk_preset, allow_aliases=False)
        if normalized is None:
            raise ValueError(f"perk_preset_name must be canonical in canonical flows, got {perk_preset!r}.")
        if normalized != canonical_preset:
            raise ValueError(
                f"perk_preset_name must match bound preset_name in canonical flows "
                f"({canonical_preset!r}), got {normalized!r}."
            )
        perk_preset = normalized

    lane_perks_enabled = bool(perk_preset) if perks_enabled is None else bool(perks_enabled)
    return BoundPresetFamily(
        preset_name=canonical_preset,
        card_preset_name=card_preset,
        module_preset_name=module_preset,
        perk_preset_name=perk_preset,
        perk_namespace_class=perk_namespace_class,
        state_mode=state_mode,
        perks_enabled=lane_perks_enabled,
    )


def _bind_loadout_lane(field_name: str, explicit_value: Optional[str], canonical_preset: str) -> str:
    if explicit_value is None:
        return canonical_preset
    normalized = normalize_preset_name(explicit_value, allow_aliases=False)
    if normalized is None:
        raise ValueError(f"{field_name} must be canonical when explicitly provided, got {explicit_value!r}.")
    if normalized != canonical_preset:
        raise ValueError(
            f"{field_name} must match bound preset_name {canonical_preset!r}, got {normalized!r}."
        )
    return normalized


# ---------------------------------------------------------------------------
# StateIdentity, StateIdentityBinding, BoundStatInputs — from engine/state_identity.py
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateIdentity:
    account_snapshot_id: str
    loadout_id: str
    scenario_id: str
    runtime_branch_id: str

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.account_snapshot_id,
            self.loadout_id,
            self.scenario_id,
            self.runtime_branch_id,
        )


@dataclass(frozen=True)
class StateIdentityBinding:
    identity: StateIdentity
    account_state: AccountState
    scenario_runtime_inputs: Optional[ScenarioRuntimeInputs] = None
    scenario_projection_state: Optional[ScenarioProjectionState] = None


@dataclass(frozen=True)
class BoundStatInputs:
    binding: StateIdentityBinding
    stat_inputs: tuple[Any, ...]


_ACCOUNT_SNAPSHOT_ID_CACHE: dict[int, str] = {}
_LOADOUT_ID_CACHE: dict[tuple[object, ...], str] = {}
_SCENARIO_ID_CACHE: dict[tuple[object, ...], str] = {}


def bind_state_identity(
    account_state: AccountState,
    *,
    preset_name: str | None = None,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool | None = None,
    runtime_branch_id: str = 'branch_base',
    scenario_runtime_inputs: Optional[ScenarioRuntimeInputs] = None,
    scenario_projection_state: Optional[ScenarioProjectionState] = None,
    scenario_context: Optional[Mapping[str, Any]] = None,
) -> StateIdentityBinding:
    resolved_preset = preset_name or account_state.default_preset
    resolved_card_preset = card_preset_name or account_state.active_card_preset or resolved_preset
    resolved_module_preset = module_preset_name or account_state.active_module_preset or resolved_preset
    resolved_perk_preset = perk_preset_name or account_state.active_perk_preset
    resolved_perk_namespace_class = getattr(account_state, 'perk_preset_namespace_class', 'canonical')
    resolved_perks_enabled = bool(account_state.active_perk_preset) if perks_enabled is None else bool(perks_enabled)
    if not runtime_branch_id or not str(runtime_branch_id).strip():
        raise ValueError('runtime_branch_id must be a non-empty string.')

    account_identity_key = id(account_state)
    account_snapshot_id = _ACCOUNT_SNAPSHOT_ID_CACHE.get(account_identity_key)
    if account_snapshot_id is None:
        account_snapshot_id = _fingerprint_id(
            'acct',
            {
                'labs': account_state.labs,
                'workshop': account_state.workshop,
                'workshop_enhancements': account_state.workshop_enhancements,
                'ultimate_weapons': account_state.ultimate_weapons,
                'uw_plus_tracks': account_state.uw_plus_tracks,
                'relics': account_state.relics,
                'vault': account_state.vault,
                'bots': account_state.bots,
                'bot_upgrades': account_state.bot_upgrades,
                'guardians': account_state.guardians,
                'player_meta': account_state.player_meta,
                'theme_song_coin_multiplier': account_state.theme_song_coin_multiplier,
                'cards_inventory': account_state.cards_inventory,
                'card_slots_unlocked': account_state.card_slots_unlocked,
                'module_system_state': account_state.module_system_state,
                'modules_inventory': account_state.modules_inventory,
                'raw_sections': account_state.raw_sections,
            },
        )
        _ACCOUNT_SNAPSHOT_ID_CACHE[account_identity_key] = account_snapshot_id
    canonical_perk_preset_name = sanitize_preset_name_for_canonical_output(
        resolved_perk_preset,
        namespace_class=resolved_perk_namespace_class,
        fallback_preset_name=resolved_preset,
    )
    loadout_cache_key = (
        account_identity_key,
        resolved_preset,
        resolved_card_preset,
        resolved_module_preset,
        canonical_perk_preset_name,
    )
    loadout_id = _LOADOUT_ID_CACHE.get(loadout_cache_key)
    if loadout_id is None:
        loadout_id = _fingerprint_id(
            'loadout',
            {
                'preset_name': resolved_preset,
                'card_preset_name': resolved_card_preset,
                'module_preset_name': resolved_module_preset,
                'perk_preset_name': canonical_perk_preset_name,
                'equipped_cards': account_state.card_presets.get(resolved_card_preset),
                'equipped_modules': _serialize_module_preset(account_state, resolved_module_preset),
                'equipped_perks': _serialize_perk_preset(account_state, resolved_perk_preset, canonical_preset_name=resolved_preset),
            },
        )
        _LOADOUT_ID_CACHE[loadout_cache_key] = loadout_id
    resolved_projection_state = scenario_projection_state or projection_state_for_mode(state_mode)
    runtime_inputs_debug = None if scenario_runtime_inputs is None else scenario_runtime_inputs.to_debug_dict()
    projection_debug = resolved_projection_state.to_debug_dict()
    scenario_context_debug = dict(scenario_context or {})
    scenario_cache_key = (
        state_mode,
        resolved_perks_enabled,
        _stable_jsonish(runtime_inputs_debug),
        _stable_jsonish(projection_debug),
        _stable_jsonish(scenario_context_debug),
    )
    scenario_id = _SCENARIO_ID_CACHE.get(scenario_cache_key)
    if scenario_id is None:
        scenario_id = _fingerprint_id(
            'scenario',
            {
                'state_mode': state_mode,
                'perks_enabled': resolved_perks_enabled,
                'scenario_runtime_inputs': runtime_inputs_debug,
                'scenario_projection_state': projection_debug,
                'scenario_context': scenario_context_debug,
            },
        )
        _SCENARIO_ID_CACHE[scenario_cache_key] = scenario_id
    return StateIdentityBinding(
        identity=StateIdentity(
            account_snapshot_id=account_snapshot_id,
            loadout_id=loadout_id,
            scenario_id=scenario_id,
            runtime_branch_id=str(runtime_branch_id).strip(),
        ),
        account_state=account_state,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=resolved_projection_state,
    )




def compile_stat_inputs_with_identity(
    account_state: AccountState,
    *,
    preset_name: str | None = None,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool | None = None,
    runtime_branch_id: str = 'branch_base',
    scenario_runtime_inputs: Optional[ScenarioRuntimeInputs] = None,
    scenario_projection_state: Optional[ScenarioProjectionState] = None,
    scenario_context: Optional[Mapping[str, Any]] = None,
) -> BoundStatInputs:
    resolved_perks_enabled = bool(account_state.active_perk_preset) if perks_enabled is None else bool(perks_enabled)
    binding = bind_state_identity(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=resolved_perks_enabled,
        runtime_branch_id=runtime_branch_id,
        scenario_runtime_inputs=scenario_runtime_inputs,
        scenario_projection_state=scenario_projection_state,
        scenario_context=scenario_context,
    )
    from qe.stat_input_compiler import compile_stat_inputs  # deferred to avoid circular import
    stat_inputs = compile_stat_inputs(
        account_state,
        preset_name=preset_name,
        state_mode=state_mode,
        card_preset_name=card_preset_name,
        module_preset_name=module_preset_name,
        perk_preset_name=perk_preset_name,
        perks_enabled=resolved_perks_enabled,
        scenario_projection_state=binding.scenario_projection_state,
        scenario_context=scenario_context,
    )
    return BoundStatInputs(binding=binding, stat_inputs=tuple(stat_inputs))


def _serialize_module_preset(account_state: AccountState, preset_name: str) -> dict[str, dict[str, Optional[str]]]:
    selections = account_state.module_presets.get(preset_name)
    if selections is None:
        raise ValueError(f'Module preset {preset_name!r} is not present in account state.')
    out: dict[str, dict[str, Optional[str]]] = {}
    for slot_type, selection in selections.items():
        if not isinstance(selection, ModulePresetSelection):
            raise ValueError(f'Module preset {preset_name!r} slot {slot_type!r} must be a ModulePresetSelection.')
        out[slot_type] = {'primary': selection.primary, 'assist': selection.assist}
    return out


def _serialize_perk_preset(account_state: AccountState, preset_name: str | None, *, canonical_preset_name: str) -> dict[str, Any]:
    namespace_class = getattr(account_state, 'perk_preset_namespace_class', 'canonical')
    if preset_name is None:
        return {'presence': 'missing', 'namespace_class': namespace_class, 'selections': []}
    selections = account_state.perk_presets.get(preset_name)
    if selections is None:
        return {'presence': 'missing', 'namespace_class': namespace_class, 'preset_name': sanitize_preset_name_for_canonical_output(preset_name, namespace_class=namespace_class, fallback_preset_name=canonical_preset_name), 'selections': []}
    out: list[dict[str, Any]] = []
    for selection in selections:
        if not isinstance(selection, PerkSelection):
            raise ValueError(f'Perk preset {preset_name!r} contains an invalid selection entry.')
        out.append({'perk_id': selection.perk_id, 'picks': selection.picks})
    return {'presence': 'explicit', 'namespace_class': namespace_class, 'preset_name': sanitize_preset_name_for_canonical_output(preset_name, namespace_class=namespace_class, fallback_preset_name=canonical_preset_name), 'selections': out}


def _fingerprint_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = sha256(_stable_jsonish(payload).encode('utf-8')).hexdigest()[:16]
    return f'{prefix}_{digest}'


def _stable_jsonish(value: Any) -> str:
    return json.dumps(_normalize_value(value), sort_keys=True, default=str)


def _normalize_value(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize_value(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return value
