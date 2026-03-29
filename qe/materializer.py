from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping

import yaml

from qe.contracts import (
    compat_surface_from_legacy_canonical,
    compat_surface_from_legacy_mechanic,
    normalize_surface_id_to_contract,
    to_legacy_surface_id,
    to_v2_surface_id,
)
from qe.models import BoundStatInputs, StateIdentity
from qe.models import StatInput

ROOT = Path(__file__).resolve().parents[1]
_INITIAL_SURFACE_SET_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-initial-surface-set.yaml'
_FAMILY_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-scenario-families.yaml'
_OWNERSHIP_LEDGER_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'stat-query-surface-ownership-ledger.yaml'
_CANONICAL_STATS_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'canonical-stats.yaml'
_MECHANIC_PARAMS_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'mechanic-params.yaml'

_COMPATIBILITY_SURFACE_ID_ALIASES = {
    compat_surface_from_legacy_canonical('free_upgrade_multiplier'): 'support_surface::free_upgrade_multiplier',
    'canonical_stat::free_upgrade_multiplier': 'support_surface::free_upgrade_multiplier',
    compat_surface_from_legacy_mechanic('module.galaxy_compressor.uw_cooldown_reduction_seconds'): 'support_surface::timing.gcomp_cooldown_reduction_seconds',
    # PH4-C tranche 5: the compiler routes this module's contribution under the legacy
    # destination_id 'module.primordial_collapse.in_bh_enemy_damage_reduction_pct'; the QE
    # surface set declares it as 'module.primordial_collapse.bh_damage_reduction_pct'.
    # The alias bridges the two so the materializer can include the contributor.
    compat_surface_from_legacy_mechanic('module.primordial_collapse.in_bh_enemy_damage_reduction_pct'): compat_surface_from_legacy_mechanic('module.primordial_collapse.bh_damage_reduction_pct'),
}

# PH4-C tranche 1: free_upgrade_package stats.
# The enhancement "Free Upgrades" routes to support_surface::free_upgrade_multiplier as a
# multiplicative contributor. The three free-upgrade chance surfaces depend on this multiplier
# (final = additive_sum × multiplier). The QE resolves surfaces independently, so we inject
# the multiplier as an additional multiplicative contributor into each dependent surface at
# baseline materialisation time. This correctly implements the cross-surface dependency
# governed in stat-query-dependency-invalidation-ledger.yaml.
_FREE_UPGRADE_MULTIPLIER_SURFACE_ID = 'support_surface::free_upgrade_multiplier'
_FREE_UPGRADE_MULTIPLIER_DEPENDENTS: frozenset[str] = frozenset({
    'state::tower.free_attack_upgrade_chance_pct',
    'state::tower.free_defense_upgrade_chance_pct',
    'state::tower.free_utility_upgrade_chance_pct',
})

# PH4-C tranche 2: enemy-skip and thorns pct surfaces.
# stat_resolution_core applies × 100 for relic/vault values in [0.0, 1.0] on pct-unit surfaces
# (the pct-additive path in _resolve_bucket, lines 1153-1154).  The same normalisation is
# required here for the three progression pct surfaces that carry relic fraction inputs.
# Additionally, some enhancement contributors carry contributor_id ending in '__multiplier',
# encoding a post-additive scaling role in stat_resolution_core (_contributor_measure extracts
# 'multiplier' from the id suffix).  _normalize_composition_stage now routes these to the
# multiplicative stage so the QE produces sum × enhancement_multiplier, matching the legacy.
_ENEMY_SKIP_THORNS_SURFACES: frozenset[str] = frozenset({
    'state::tower.enemy_attack_level_skip_pct',
    'state::tower.enemy_health_level_skip_pct',
    'state::tower.thorns_damage_pct',
})

# PH4-C tranche 4: tower_hp workshop-times-multipliers routing.
# Legacy _resolve_survivability_base_times_multipliers: final = workshop × (1+relic) × (1+vault)
# × lab_mult × card_mult × module_mult × enhancement_mult.  Only state::tower.hp is independent
# (no cross-surface dependency); state::wall.hp and state::wall.regen depend on tower_hp /
# tower_regen post-resolution and remain in the explicit residual list.
_SURVIVABILITY_WORKSHOP_MULTIPLIER_SURFACE_IDS: frozenset[str] = frozenset({
    'state::tower.hp',
    # PH4-C tranche 6: orb_speed_rpm uses the same unit=rpm path in legacy stat_resolution_core
    # (lines 1128-1134): workshop base is additive, relic/vault/module_substat are multiplicative
    # via _canonical_source_multiplier.  Same routing + _scale_survivability_relic_vault_values
    # applies unchanged.
    'state::tower.orb_speed_rpm',
})

# PH4-C tranche 4: wall_fortification_multiplier unique formula.
# Legacy: 1.0 + (lab_pct / 100.0).  The materializer stores raw lab_pct; the QE multiplicative
# stage needs 1 + lab_pct/100 so the kernel returns the correct final multiplier.
_WALL_FORTIFICATION_SURFACE_ID = 'state::wall.fortification_multiplier'


def _inject_free_upgrade_cross_surface_multipliers(
    rows: list['BaselineContributorRow'],
    allowed_surfaces: frozenset[str],
) -> list['BaselineContributorRow']:
    """Inject free_upgrade_multiplier contributors as multiplicative contributors to dependent surfaces.

    Only injects when the dependent surface already has at least one active additive contributor,
    so surfaces with no base contributions stay gated_off rather than resolving to the raw multiplier.
    """
    multiplier_rows = [
        row for row in rows
        if row.surface_id == _FREE_UPGRADE_MULTIPLIER_SURFACE_ID
        and row.composition_stage == 'multiplicative'
        and row.active
    ]
    if not multiplier_rows:
        return rows
    injected = list(rows)
    for dep_surface in _FREE_UPGRADE_MULTIPLIER_DEPENDENTS:
        if dep_surface not in allowed_surfaces:
            continue
        has_active_additive = any(
            row.surface_id == dep_surface and row.composition_stage == 'additive_pre_cap' and row.active
            for row in rows
        )
        if not has_active_additive:
            continue
        for mult_row in multiplier_rows:
            injected.append(replace(mult_row, surface_id=dep_surface))
    return injected


def _scale_free_upgrade_relic_values(
    rows: list['BaselineContributorRow'],
) -> list['BaselineContributorRow']:
    """Scale relic additive contributors to free-upgrade chance surfaces from fraction to percent.

    Relic stat_inputs arrive with resolved_value in [0.0, 1.0] fraction form.
    Legacy stat_resolution_core applies × 100 for values in this range.
    We replicate that normalisation here so QE composition produces the same final values.
    """
    out = []
    for row in rows:
        if (
            row.surface_id in _FREE_UPGRADE_MULTIPLIER_DEPENDENTS
            and row.source_class == 'relics'
            and row.composition_stage == 'additive_pre_cap'
            and row.value_type == 'scalar'
            and isinstance(row.value, (int, float))
            and 0.0 <= float(row.value) <= 1.0
        ):
            out.append(replace(row, value=float(row.value) * 100.0))
        else:
            out.append(row)
    return out


def _scale_enemy_skip_thorns_relic_values(
    rows: list['BaselineContributorRow'],
) -> list['BaselineContributorRow']:
    """Scale relic additive contributors to enemy-skip and thorns pct surfaces from fraction to percent.

    Mirrors the pattern from _scale_free_upgrade_relic_values.  stat_resolution_core
    applies × 100 for relic/vault values in [0.0, 1.0] on pct-unit surfaces
    (_resolve_bucket, unit=='pct' path).  The enemy-skip and thorns surfaces share this
    pattern: relics carry resolved_value in fraction form that must become percentage points.
    """
    out = []
    for row in rows:
        if (
            row.surface_id in _ENEMY_SKIP_THORNS_SURFACES
            and row.source_class == 'relics'
            and row.composition_stage == 'additive_pre_cap'
            and row.value_type == 'scalar'
            and isinstance(row.value, (int, float))
            and 0.0 <= float(row.value) <= 1.0
        ):
            out.append(replace(row, value=float(row.value) * 100.0))
        else:
            out.append(row)
    return out


def _scale_survivability_relic_vault_values(
    rows: list['BaselineContributorRow'],
) -> list['BaselineContributorRow']:
    """Scale relic/vault contributors on survivability surfaces from fraction to (1 + fraction).

    Legacy _resolve_survivability_base_times_multipliers: final *= (1.0 + v) for relic/vault
    source families.  The materializer stores the raw v (e.g., 0.51); the QE multiplicative
    stage receives the stored value directly, so we must convert v -> 1.0 + v before the kernel
    computes the product.

    source_class 'relics' covers source_family='relic'.
    source_class 'base' covers source_family in {'vault', 'guardian', 'player_stuff', 'theme_song'};
    all of these follow the same (1+v) formula in _canonical_source_multiplier / legacy treatment.
    The 0 <= v <= 1.0 guard excludes values already in multiplier form (>1).
    """
    out = []
    for row in rows:
        if (
            row.surface_id in _SURVIVABILITY_WORKSHOP_MULTIPLIER_SURFACE_IDS
            and row.composition_stage == 'multiplicative'
            and row.source_class in {'relics', 'base'}
            and row.active
            and isinstance(row.value, (int, float))
            and 0.0 <= float(row.value) <= 1.0
        ):
            out.append(replace(row, value=1.0 + float(row.value)))
        else:
            out.append(row)
    return out


def _scale_wall_fortification_lab_value(
    rows: list['BaselineContributorRow'],
) -> list['BaselineContributorRow']:
    """Convert wall_fortification_multiplier lab percent to (1 + pct/100) multiplier.

    Legacy: 1.0 + (lab_pct / 100.0).  The materializer stores raw lab_pct (e.g., 940.0);
    the QE multiplicative stage needs (1 + 940.0/100.0) = 10.4 so the kernel returns 10.4
    as the final resolved multiplier value.
    """
    out = []
    for row in rows:
        if (
            row.surface_id == _WALL_FORTIFICATION_SURFACE_ID
            and row.composition_stage == 'multiplicative'
            and row.source_class == 'labs'
            and row.active
            and isinstance(row.value, (int, float))
        ):
            out.append(replace(row, value=1.0 + float(row.value) / 100.0))
        else:
            out.append(row)
    return out


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
_ALLOWED_SURFACE_CLASSES = frozenset({'surface', 'capability', 'environment', 'context_resource', 'support_surface'})

_SOURCE_CLASS_BY_FAMILY = {
    'lab': 'labs',
    'workshop': 'workshop',
    'enhancement': 'workshop',
    'relic': 'relics',
    'perk': 'perks',
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
    source_family: str | None
    source_name: str | None
    composition_stage: str
    contributor_id: str
    value: Any
    value_type: str
    input_value: Any
    input_value_type: str | None
    input_notes: str | None
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
        normalized_rows = [
            self._normalize_row(stat_input, surface_id=resolved_surface_id)
            for stat_input in bound_inputs.stat_inputs
            if (resolved_surface_id := self._resolve_allowed_surface_id(stat_input, allowed_surfaces)) is not None
        ]
        normalized_rows = _inject_free_upgrade_cross_surface_multipliers(normalized_rows, allowed_surfaces)
        normalized_rows = _scale_free_upgrade_relic_values(normalized_rows)
        normalized_rows = _scale_enemy_skip_thorns_relic_values(normalized_rows)
        normalized_rows = _scale_survivability_relic_vault_values(normalized_rows)
        normalized_rows = _scale_wall_fortification_lab_value(normalized_rows)
        rows = tuple(
            sorted(
                self._with_declared_surface_placeholders(normalized_rows, allowed_surfaces),
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
        normalized_rows = [
            self._normalize_row(stat_input, surface_id=resolved_surface_id)
            for stat_input in stat_inputs
            if (resolved_surface_id := self._resolve_allowed_surface_id(stat_input, allowed_surfaces)) is not None
        ]
        normalized_rows = _inject_free_upgrade_cross_surface_multipliers(normalized_rows, allowed_surfaces)
        normalized_rows = _scale_free_upgrade_relic_values(normalized_rows)
        normalized_rows = _scale_enemy_skip_thorns_relic_values(normalized_rows)
        normalized_rows = _scale_survivability_relic_vault_values(normalized_rows)
        normalized_rows = _scale_wall_fortification_lab_value(normalized_rows)
        rows = tuple(
            sorted(
                self._with_declared_surface_placeholders(normalized_rows, allowed_surfaces),
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

    def _resolve_allowed_surface_id(self, row: StatInput, allowed_surfaces: frozenset[str]) -> str | None:
        for surface_id in _surface_id_candidates(row):
            if surface_id in allowed_surfaces:
                return surface_id
        return None

    def _normalize_row(self, row: StatInput, *, surface_id: str | None = None) -> BaselineContributorRow:
        surface_id = surface_id or _normalized_surface_id(row)
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
            source_family=row.source_family,
            source_name=row.source_name,
            composition_stage=composition_stage,
            contributor_id=contributor_id,
            value=row.value,
            value_type=_normalize_value_type(row.value_type),
            input_value=row.value,
            input_value_type=row.value_type,
            input_notes=row.notes,
            active=bool(row.active),
            gate_reason=gate_reason,
            provenance_ref=provenance_ref,
        )

    def _with_declared_surface_placeholders(
        self,
        rows: Iterable[BaselineContributorRow],
        allowed_surfaces: frozenset[str],
    ) -> tuple[BaselineContributorRow, ...]:
        materialized = list(rows)
        present_surfaces = {row.surface_id for row in materialized}
        for surface_id in sorted(allowed_surfaces - present_surfaces):
            surface_metadata = self._surface_metadata_by_id[surface_id]
            materialized.append(
                BaselineContributorRow(
                    surface_id=surface_id,
                    surface_class=str(surface_metadata['surface_class']),
                    domain=str(surface_metadata['domain']),
                    source_class='base',
                    source_family=None,
                    source_name=None,
                    composition_stage='gate_enable_disable',
                    contributor_id=f'query_placeholder::{surface_id}',
                    value=False,
                    value_type=str(surface_metadata['default_value_type']),
                    input_value=False,
                    input_value_type=str(surface_metadata['default_value_type']),
                    input_notes='surface_absent_from_bound_inputs',
                    active=False,
                    gate_reason='surface_absent_from_bound_inputs',
                    provenance_ref='engine.family_baseline_materializer.placeholder',
                )
            )
        return tuple(materialized)


@lru_cache(maxsize=1)
def load_surface_registry_contract() -> dict[str, Any]:
    return yaml.safe_load(_INITIAL_SURFACE_SET_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def load_surface_ownership_ledger() -> dict[str, Any]:
    return yaml.safe_load(_OWNERSHIP_LEDGER_PATH.read_text()) or {}


@lru_cache(maxsize=1)
def load_family_surface_ids() -> dict[str, frozenset[str]]:
    initial_surface_contract = load_surface_registry_contract()
    declared_families = set(load_family_contracts())
    bounded: dict[str, frozenset[str]] = {}
    all_surface_ids: set[str] = set()
    ownership_rows = {
        str(row.get('node_id')): row
        for row in (load_surface_ownership_ledger().get('surface_nodes') or [])
    }
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
            ownership_row = ownership_rows.get(surface_id)
            if ownership_row is None:
                raise ValueError(f'Surface {surface_id!r} is missing from the ownership ledger.')
            if ownership_row.get('ownership_status') != 'query_owned' or ownership_row.get('governed_by') != 'canonical_query_engine':
                raise ValueError(f'Surface {surface_id!r} must be query_owned and governed_by canonical_query_engine in the ownership ledger.')
            if ownership_row.get('ownership_class') != surface_class:
                raise ValueError(
                    f'Surface {surface_id!r} disagrees with the ownership ledger on ownership_class: '
                    f"registry={surface_class!r}, ledger={ownership_row.get('ownership_class')!r}."
                )
            seen_in_group.add(surface_id)
            all_surface_ids.add(surface_id)
            owning_families = tuple(entry.get('owning_families') or ())
            if not owning_families:
                raise ValueError(f'Surface {surface_id!r} must declare owning_families.')
            unknown_families = sorted(set(owning_families) - declared_families - {family_group})
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


@lru_cache(maxsize=1)
def load_surface_metadata_by_id() -> dict[str, Mapping[str, Any]]:
    metadata: dict[str, Mapping[str, Any]] = {}
    contract = load_surface_registry_contract()
    for family_data in (contract.get('families') or {}).values():
        for entry in family_data.get('surfaces') or ():
            surface_id = str(entry['surface_id'])
            query_value_type = entry.get('query_value_type')
            if str(entry.get('surface_kind')) == 'support_surface':
                query_value_type = str(query_value_type or '').strip()
                if query_value_type not in {'scalar', 'count'}:
                    raise ValueError(
                        f'Support surface {surface_id!r} must declare query_value_type scalar|count in the phase-1 registry.'
                    )
            metadata[str(entry['surface_id'])] = MappingProxyType(
                {
                    'surface_class': str(entry['surface_class']),
                    'domain': str(entry['domain']),
                    'default_value_type': _default_value_type_for_surface_id(surface_id, query_value_type=query_value_type),
                }
            )
    return metadata


@lru_cache(maxsize=1)
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
    candidates = _surface_id_candidates(row)
    return candidates[-1] if candidates else None


def _surface_id_candidates(row: StatInput) -> tuple[str, ...]:
    if not row.destination_object_type or not row.destination_id:
        return ()
    raw_surface_id = f'{row.destination_object_type}::{row.destination_id}'
    aliased_surface_id = _COMPATIBILITY_SURFACE_ID_ALIASES.get(raw_surface_id, raw_surface_id)
    candidates: list[str] = []
    for candidate in (raw_surface_id, aliased_surface_id, to_v2_surface_id(aliased_surface_id), to_legacy_surface_id(aliased_surface_id)):
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def _fallback_contributor_id(row: StatInput) -> str:
    source_name = str(row.source_name).strip().lower().replace(' ', '_').replace('/', '_')
    return f'{row.source_family}.{source_name}.{row.stage}'


def _normalize_value_type(value_type: str) -> str:
    return {
        'multiplier': 'scalar',
        'multiplier_display': 'scalar',
        'resolved_value': 'scalar',
        'percent_display': 'scalar',
        'pct': 'scalar',  # T3B: pct is a numeric percentage contribution, resolves as scalar
        'flat': 'scalar',
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
    # Enhancement contributors whose contributor_id ends with '__multiplier' encode a
    # post-additive scaling role in stat_resolution_core: _contributor_measure extracts
    # 'multiplier' from the id suffix and routes the row to multiplier_product.  Mirror
    # that here so the QE applies them as a product over the additive sum.
    if (
        row.source_family == 'enhancement'
        and row.contributor_id is not None
        and row.contributor_id.endswith('__multiplier')
    ):
        return 'multiplicative'
    if row.destination_object_type == 'runtime_mechanic_param':
        return 'scenario_adjustment'
    # PH4-C tranche 4: survivability workshop-times-multipliers routing.
    # source_family='workshop' is the additive base; all other contributors are multiplicative
    # factors in the legacy _resolve_survivability_base_times_multipliers formula.
    if surface_id in _SURVIVABILITY_WORKSHOP_MULTIPLIER_SURFACE_IDS:
        if row.source_family == 'workshop':
            return 'additive_pre_cap'
        return 'multiplicative'
    # PH4-C tranche 4: wall_fortification_multiplier unique formula.
    # Legacy: 1.0 + (lab_pct / 100.0); all contributors route to multiplicative so the
    # kernel returns multiplicative_total = (1 + lab_pct/100) directly.
    if surface_id == _WALL_FORTIFICATION_SURFACE_ID:
        return 'multiplicative'
    return 'additive_pre_cap'


def _default_value_type_for_surface_id(surface_id: str, *, query_value_type: str | None = None) -> str:
    if query_value_type:
        return str(query_value_type)
    object_type, _, destination_id = surface_id.partition('::')
    registry = _contract_registry_value_types()
    return registry.get((object_type, destination_id), 'scalar')


def _unit_to_query_value_type(unit: str) -> str:
    return 'count' if str(unit).strip() == 'count' else 'scalar'


def _resolver_to_query_value_type(resolver: str) -> str:
    return 'count' if 'count' in str(resolver) else 'scalar'


@lru_cache(maxsize=1)
def _contract_registry_value_types() -> dict[tuple[str, str], str]:
    canonical_stats = yaml.safe_load(_CANONICAL_STATS_PATH.read_text()) or {}
    mechanic_params = yaml.safe_load(_MECHANIC_PARAMS_PATH.read_text()) or {}
    out: dict[tuple[str, str], str] = {}

    for entries in (canonical_stats.get('domains') or {}).values():
        for entry in entries or ():
            destination_id = str(entry.get('id') or '').strip()
            if not destination_id:
                continue
            value_type = _unit_to_query_value_type(entry.get('unit', ''))
            out[('canonical_stat', destination_id)] = value_type

    for group_name, entries in (mechanic_params.get('groups') or mechanic_params).items():
        if group_name in {'schema_revision', 'purpose', 'notes'}:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            destination_id = str(entry.get('id') or '').strip()
            if not destination_id:
                continue
            resolver = str(entry.get('resolver') or '')
            unit = str(entry.get('unit') or '')
            value_type = _resolver_to_query_value_type(resolver) if resolver else _unit_to_query_value_type(unit)
            out[('mechanic_param', destination_id)] = value_type
            out[('runtime_mechanic_param', destination_id)] = value_type

    return out


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
