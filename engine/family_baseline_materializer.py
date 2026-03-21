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

_SOURCE_CLASS_BY_FAMILY = {
    'lab': 'labs',
    'workshop': 'workshop',
    'enhancement': 'workshop',
    'relic': 'relics',
    'card': 'cards',
    'module': 'modules_main',
    'module_substat': 'modules_substats',
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
            'contributor_rows': [row.__dict__ for row in self.contributor_rows],
        }
        return json.dumps(payload, sort_keys=True, default=str)


class FamilyBaselineMaterializer:
    def __init__(self) -> None:
        self._family_surface_ids = _load_family_surface_ids()

    def materialize(self, bound_inputs: BoundStatInputs, family_id: str) -> FamilyBaselineContributorMap:
        # Phase-1 note: family/scenario compatibility remains query-kernel work.
        # This materializer only normalizes compiler-emitted rows into bounded family maps.
        allowed_surfaces = self._family_surface_ids.get(family_id)
        if allowed_surfaces is None:
            raise ValueError(f'Unsupported family_id {family_id!r}. Phase 1 only supports bounded families declared in KB contracts.')
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
            contributor_rows=rows,
        )

    def materialize_from_rows(self, identity: StateIdentity, family_id: str, stat_inputs: Iterable[StatInput]) -> FamilyBaselineContributorMap:
        allowed_surfaces = self._family_surface_ids.get(family_id)
        if allowed_surfaces is None:
            raise ValueError(f'Unsupported family_id {family_id!r}. Phase 1 only supports bounded families declared in KB contracts.')
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
            contributor_rows=rows,
        )

    def _normalize_row(self, row: StatInput) -> BaselineContributorRow:
        surface_id = _normalized_surface_id(row)
        if surface_id is None:
            raise ValueError(f'Stat input {row!r} is missing destination routing and cannot be materialized.')
        source_class = _SOURCE_CLASS_BY_FAMILY.get(row.source_family)
        if source_class is None:
            raise ValueError(f'Unsupported source_family {row.source_family!r} for bounded baseline materialization.')
        contributor_id = row.contributor_id or _fallback_contributor_id(row)
        composition_stage = _normalize_composition_stage(surface_id, row)
        gate_reason = None if row.active else (row.notes or 'inactive_compiler_row')
        provenance_ref = row.provenance or row.notes or f'compiler::{row.source_family}::{row.source_name}'
        return BaselineContributorRow(
            surface_id=surface_id,
            source_class=source_class,
            composition_stage=composition_stage,
            contributor_id=contributor_id,
            value=row.value,
            value_type=_normalize_value_type(row.value_type),
            active=bool(row.active),
            gate_reason=gate_reason,
            provenance_ref=provenance_ref,
        )


def _load_family_surface_ids() -> dict[str, frozenset[str]]:
    initial_surface_contract = yaml.safe_load(_INITIAL_SURFACE_SET_PATH.read_text()) or {}
    family_contract = yaml.safe_load(_FAMILY_CONTRACT_PATH.read_text()) or {}
    initial_by_group = {
        family_group: frozenset(family_data.get('canonical_and_support_surfaces', []))
        for family_group, family_data in (initial_surface_contract.get('families') or {}).items()
    }
    bounded: dict[str, frozenset[str]] = {}
    for group_name, group_payload in (family_contract.get('family_groups') or {}).items():
        surface_group = initial_by_group.get(f'{group_name}_v1')
        if surface_group is None:
            raise ValueError(f'Missing initial surface contract for family group {group_name!r}.')
        for family_id in (group_payload.get('families') or {}).keys():
            bounded[family_id] = surface_group
    return bounded


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
