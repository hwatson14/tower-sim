from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping

import yaml

from engine.state_identity import BoundStatInputs, StateIdentity
from models.stat_input import StatInput

ROOT = Path(__file__).resolve().parents[1]
_INITIAL_SURFACE_SET_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-initial-surface-set.yaml'
_FAMILY_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-scenario-families.yaml'

_SURFACE_ID_ALIASES = {
    'canonical_stat::free_upgrade_multiplier': 'support_surface::free_upgrade_multiplier',
    'mechanic_param::module.galaxy_compressor.uw_cooldown_reduction_seconds': 'support_surface::timing.gcomp_cooldown_reduction_seconds',
}


_REQUIRED_SURFACE_ENTRY_FIELDS = {
    'surface_id',
    'surface_kind',
    'surface_class',
    'domain',
    'owning_families',
    'query_resolvable_phase_1',
    'queryable_directly',
    'consumer_only',
    'support_only',
    'publish_default',
    'debug_only',
    'scenario_scoped',
    'semantics',
}
_ALLOWED_SURFACE_CLASSES = frozenset({'surface', 'capability', 'environment', 'context_resource'})

_SOURCE_CLASS_BY_FAMILY = {
    'lab': 'labs',
    'workshop': 'workshop',
    'enhancement': 'workshop',
    'relic': 'relics',
    'card': 'cards',
    'module_substat': 'module_substat',
    'uw': 'ultimate_weapons',
    'uw_plus': 'ultimate_weapons',
    'bot': 'bots',
    'guardian': 'base',
    'vault': 'base',
    'player_stuff': 'base',
    'theme_song': 'base',
    'scenario_rules': 'scenario_rules',
    'uw_unlock': 'unlock_mask',
    'bot_unlock': 'unlock_mask',
}


@dataclass(frozen=True)
class BaselineContributorRow:
    surface_id: str
    surface_class: str
    domain: str
    source_class: str
    composition_stage: str
    contributor_id: str
    value: Any
    value_type: str
    active: bool
    gate_reason: str | None
    provenance_ref: str


@dataclass(frozen=True)
class FamilyBaselineContributorMap:
    account_snapshot_id: str
    loadout_id: str
    scenario_id: str
    runtime_branch_id: str
    family_id: str
    baseline_semantics: Mapping[str, bool | str]
    contributor_rows: tuple[BaselineContributorRow, ...]

    @property
    def contributor_rows_by_surface(self) -> Mapping[str, tuple[BaselineContributorRow, ...]]:
        grouped: dict[str, list[BaselineContributorRow]] = {}
        for row in self.contributor_rows:
            grouped.setdefault(row.surface_id, []).append(row)
        return MappingProxyType({surface_id: tuple(rows) for surface_id, rows in grouped.items()})

    def fingerprint(self) -> str:
        payload = {
            'account_snapshot_id': self.account_snapshot_id,
            'loadout_id': self.loadout_id,
            'scenario_id': self.scenario_id,
            'runtime_branch_id': self.runtime_branch_id,
            'family_id': self.family_id,
            'baseline_semantics': dict(self.baseline_semantics),
            'contributor_rows': [row.__dict__ for row in self.contributor_rows],
        }
        return json.dumps(payload, sort_keys=True, default=str)


class FamilyBaselineMaterializer:
    def __init__(self) -> None:
        self._family_surface_ids = load_family_surface_ids()
        self._surface_metadata_by_id = load_surface_metadata_by_id()
        self._family_contracts = load_family_contracts()

    def materialize(self, bound_inputs: BoundStatInputs, family_id: str) -> FamilyBaselineContributorMap:
        self.assert_family_supported(family_id)
        allowed_surfaces = self._family_surface_ids[family_id]
        rows = tuple(
            sorted(
                (
                    self._normalize_row(stat_input)
                    for stat_input in bound_inputs.stat_inputs
                    if _normalized_surface_id(stat_input) in allowed_surfaces
                ),
                key=contributor_row_sort_key,
            )
        )
        return FamilyBaselineContributorMap(
            account_snapshot_id=bound_inputs.binding.identity.account_snapshot_id,
            loadout_id=bound_inputs.binding.identity.loadout_id,
            scenario_id=bound_inputs.binding.identity.scenario_id,
            runtime_branch_id=bound_inputs.binding.identity.runtime_branch_id,
            family_id=family_id,
            baseline_semantics=self._family_contracts[family_id]['baseline_semantics'],
            contributor_rows=rows,
        )

    def materialize_from_rows(self, identity: StateIdentity, family_id: str, stat_inputs: Iterable[StatInput]) -> FamilyBaselineContributorMap:
        self.assert_family_supported(family_id)
        allowed_surfaces = self._family_surface_ids[family_id]
        rows = tuple(
            sorted(
                (
                    self._normalize_row(stat_input)
                    for stat_input in stat_inputs
                    if _normalized_surface_id(stat_input) in allowed_surfaces
                ),
                key=contributor_row_sort_key,
            )
        )
        return FamilyBaselineContributorMap(
            account_snapshot_id=identity.account_snapshot_id,
            loadout_id=identity.loadout_id,
            scenario_id=identity.scenario_id,
            runtime_branch_id=identity.runtime_branch_id,
            family_id=family_id,
            baseline_semantics=self._family_contracts[family_id]['baseline_semantics'],
            contributor_rows=rows,
        )

    def assert_family_supported(self, family_id: str) -> None:
        if family_id not in self._family_surface_ids:
            raise ValueError(f'Unsupported family_id {family_id!r}. Phase 1 only supports bounded families declared in KB contracts.')

    def assert_family_compatibility(
        self,
        *,
        family_id: str,
        state_mode: str,
        perks_enabled: bool,
        scenario_mode_id: str | None,
    ) -> None:
        self.assert_family_supported(family_id)
        family_contract = self._family_contracts[family_id]
        expected_state_mode = family_contract['state_mode']
        if state_mode != expected_state_mode:
            raise ValueError(f'Family {family_id!r} requires state_mode={expected_state_mode!r}, got {state_mode!r}.')
        expected_perks = family_contract['perks_enabled']
        if expected_perks != 'explicit' and bool(perks_enabled) is not bool(expected_perks):
            raise ValueError(f'Family {family_id!r} requires perks_enabled={expected_perks!r}.')
        expected_mode_id = family_contract['mode_id']
        if scenario_mode_id is not None and scenario_mode_id != expected_mode_id:
            raise ValueError(f'Family {family_id!r} requires scenario mode_id={expected_mode_id!r}, got {scenario_mode_id!r}.')

    def _normalize_row(self, row: StatInput) -> BaselineContributorRow:
        surface_id = _normalized_surface_id(row)
        if surface_id is None:
            raise ValueError(f'Stat input {row!r} is missing destination routing and cannot be materialized.')
        surface_metadata = self._surface_metadata_by_id.get(surface_id)
        if surface_metadata is None:
            raise ValueError(f'Surface {surface_id!r} is not declared in the phase-1 family surface registry.')
        source_class = _normalize_source_class(row)
        contributor_id = row.contributor_id or _fallback_contributor_id(row)
        composition_stage = _normalize_composition_stage(surface_id, row)
        gate_reason = None if row.active else (row.notes or 'inactive_compiler_row')
        provenance_ref = row.provenance or row.notes or f'compiler::{row.source_family}::{row.source_name}'
        return BaselineContributorRow(
            surface_id=surface_id,
            surface_class=str(surface_metadata['surface_class']),
            domain=str(surface_metadata['domain']),
            source_class=source_class,
            composition_stage=composition_stage,
            contributor_id=contributor_id,
            value=row.value,
            value_type=_normalize_value_type(row.value_type),
            active=bool(row.active),
            gate_reason=gate_reason,
            provenance_ref=provenance_ref,
        )


def load_surface_registry_contract() -> dict[str, Any]:
    return yaml.safe_load(_INITIAL_SURFACE_SET_PATH.read_text()) or {}


def load_family_surface_ids() -> dict[str, frozenset[str]]:
    initial_surface_contract = load_surface_registry_contract()
    declared_families = set(load_family_contracts())
    bounded: dict[str, frozenset[str]] = {}
    all_surface_ids: set[str] = set()
    for family_group, family_data in (initial_surface_contract.get('families') or {}).items():
        group_surfaces = family_data.get('surfaces') or ()
        seen_in_group: set[str] = set()
        for entry in group_surfaces:
            missing_fields = sorted(_REQUIRED_SURFACE_ENTRY_FIELDS - set(entry))
            if missing_fields:
                raise ValueError(f'Family group {family_group!r} contains a surface entry missing required fields: {missing_fields}.')
            surface_id = str(entry.get('surface_id') or '').strip()
            if not surface_id:
                raise ValueError(f'Family group {family_group!r} contains a surface entry without surface_id.')
            if surface_id in seen_in_group or surface_id in all_surface_ids:
                raise ValueError(f'Duplicate surface_id {surface_id!r} found in stat query surface registry.')
            surface_class = str(entry.get('surface_class') or '').strip()
            if surface_class not in _ALLOWED_SURFACE_CLASSES:
                raise ValueError(f'Surface {surface_id!r} declares unsupported surface_class {surface_class!r}.')
            bool_fields = (
                'query_resolvable_phase_1',
                'queryable_directly',
                'consumer_only',
                'support_only',
                'publish_default',
                'debug_only',
                'scenario_scoped',
            )
            invalid_bool_fields = [field for field in bool_fields if not isinstance(entry.get(field), bool)]
            if invalid_bool_fields:
                raise ValueError(f'Surface {surface_id!r} has non-boolean metadata fields: {invalid_bool_fields}.')
            if entry['debug_only'] and entry['publish_default']:
                raise ValueError(f'Surface {surface_id!r} cannot be debug_only and publish_default simultaneously.')
            seen_in_group.add(surface_id)
            all_surface_ids.add(surface_id)
            owning_families = tuple(entry.get('owning_families') or ())
            if not owning_families:
                raise ValueError(f'Surface {surface_id!r} must declare owning_families.')
            unknown_families = sorted(set(owning_families) - declared_families)
            if unknown_families:
                raise ValueError(f'Surface {surface_id!r} references undeclared owning_families: {unknown_families}.')
            for family_id in owning_families:
                bounded.setdefault(str(family_id), set()).add(surface_id)
        for bundle in family_data.get('query_bundles') or ():
            bundle_id = str(bundle.get('bundle_id') or '').strip()
            if not bundle_id:
                raise ValueError(f'Family group {family_group!r} contains a query bundle without bundle_id.')
            missing_bundle_surfaces = sorted(set(bundle.get('surface_ids') or ()) - seen_in_group)
            if missing_bundle_surfaces:
                raise ValueError(
                    f'Query bundle {bundle_id!r} references undeclared surface_ids for family group {family_group!r}: {missing_bundle_surfaces}.'
                )
    missing_family_assignments = sorted(declared_families - set(bounded))
    if missing_family_assignments:
        raise ValueError(f'Families missing declared query surfaces in phase-1 registry: {missing_family_assignments}.')
    return {family_id: frozenset(surface_ids) for family_id, surface_ids in bounded.items()}


def load_surface_metadata_by_id() -> dict[str, Mapping[str, Any]]:
    metadata: dict[str, Mapping[str, Any]] = {}
    contract = load_surface_registry_contract()
    for family_data in (contract.get('families') or {}).values():
        for entry in family_data.get('surfaces') or ():
            metadata[str(entry['surface_id'])] = MappingProxyType(
                {
                    'surface_class': str(entry['surface_class']),
                    'domain': str(entry['domain']),
                }
            )
    return metadata


def load_family_contracts() -> dict[str, Mapping[str, Any]]:
    family_contract = yaml.safe_load(_FAMILY_CONTRACT_PATH.read_text()) or {}
    family_contracts: dict[str, Mapping[str, Any]] = {}
    for group_id, group_payload in (family_contract.get('family_groups') or {}).items():
        for family_id, payload in (group_payload.get('families') or {}).items():
            baseline_semantics = MappingProxyType(dict(payload.get('baseline_semantics') or {}))
            if not baseline_semantics:
                raise ValueError(f'Family {family_id!r} must declare baseline_semantics.')
            required_semantics = {'deterministic', 'immutable', 'overlay_free', 'bounded_to_declared_surface_set'}
            missing_semantics = sorted(required_semantics - set(baseline_semantics))
            if missing_semantics:
                raise ValueError(f'Family {family_id!r} baseline_semantics missing required fields: {missing_semantics}.')
            family_contracts[str(family_id)] = MappingProxyType(
                {
                    'family_group': str(group_id),
                    'state_mode': str(payload['state_mode']),
                    'mode_id': str(payload['mode_id']),
                    'perks_enabled': payload['perks_enabled'],
                    'allowed_overlay_types': tuple(payload.get('allowed_overlay_types') or ()),
                    'scenario_kind': str(payload.get('scenario_kind') or 'run'),
                    'baseline_semantics': baseline_semantics,
                }
            )
    return family_contracts


def _normalize_source_class(row: StatInput) -> str:
    if row.source_family == 'module':
        stat_name = str(row.stat_name or '')
        notes = str(row.notes or '')
        if stat_name.endswith('::unique') or 'module_' in notes and 'unique_effect' in notes or ':kb_module_unique_routed' in notes:
            return 'module_unique'
        return 'module_main'
    source_class = _SOURCE_CLASS_BY_FAMILY.get(row.source_family)
    if source_class is None:
        raise ValueError(f'Unsupported source_family {row.source_family!r} for bounded baseline materialization.')
    return source_class


def _normalized_surface_id(row: StatInput) -> str | None:
    if not row.destination_object_type or not row.destination_id:
        return None
    raw_surface_id = f'{row.destination_object_type}::{row.destination_id}'
    return _SURFACE_ID_ALIASES.get(raw_surface_id, raw_surface_id)


def _fallback_contributor_id(row: StatInput) -> str:
    source_name = str(row.source_name).strip().lower().replace(' ', '_').replace('/', '_')
    return f'{row.source_family}.{source_name}.{row.stage}'


def _normalize_value_type(value_type: str) -> str:
    return {
        'multiplier': 'scalar',
        'resolved_value': 'scalar',
        'percent_display': 'scalar',
        'bool': 'count',
        'level': 'count',
        'raw_text': 'scalar',
    }.get(value_type, value_type)


def _normalize_composition_stage(surface_id: str, row: StatInput) -> str:
    if not row.active:
        return 'gate_enable_disable'
    if row.destination_object_type == 'capability' or row.value_type == 'bool':
        return 'gate_enable_disable'
    if surface_id == 'support_surface::free_upgrade_multiplier':
        return 'multiplicative'
    if row.destination_object_type == 'runtime_mechanic_param':
        return 'scenario_adjustment'
    return 'additive_pre_cap'


def contributor_row_sort_key(row: BaselineContributorRow) -> tuple[str, str, str, str, str, str, str]:
    return (
        row.surface_id,
        row.source_class,
        row.composition_stage,
        row.contributor_id,
        row.provenance_ref,
        row.value_type,
        repr(row.value),
    )
