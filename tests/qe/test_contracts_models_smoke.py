from __future__ import annotations

import csv
from pathlib import Path

import pytest

from input.state_types import ScenarioProjectionState
from qe.consumer_registry import resolve_consumer_bundle
import qe.kb_surfaces as kb_surfaces
from qe.kb_surfaces import LAB_FORMULA_VALUES, RUNTIME_FORMULA_AUTHORITY, WORKSHOP_FORMULA_VALUES
from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    normalize_contract_payload,
    normalize_preset_name,
    to_legacy_surface_id,
    to_v2_surface_id,
)
from qe.models import BoundPresetFamily, StateIdentity, StatBook, StatInput, StatRow, bind_preset_family
from qe.routing import QEFamilyQueryResult, QEResolutionPlanner
from qe.shared_runtime_context import QESharedRuntimeContext, get_default_qe_shared_runtime_context
from input.loader import load_inputs
from input.runtime_state import build_runtime_state

pytestmark = pytest.mark.live


def test_canonical_preset_names__include_primary_defaults():
    assert len(CANONICAL_PRESET_NAMES) >= 2
    assert "Farming" in CANONICAL_PRESET_NAMES
    assert "Tourney" in CANONICAL_PRESET_NAMES


def test_normalize_preset_name__returns_canonical_or_none():
    assert normalize_preset_name("Farming", allow_aliases=False) == "Farming"
    assert normalize_preset_name(None, allow_aliases=False) is None
    assert normalize_preset_name("", allow_aliases=False) is None


def test_surface_id_roundtrip__legacy_and_v2_are_reversible():
    v2 = to_v2_surface_id("canonical_stat::tower_defense_pct")
    assert v2 == "state::tower.defense_pct"
    assert to_legacy_surface_id(v2) == "canonical_stat::tower_defense_pct"


def test_normalize_contract_payload__rewrites_legacy_surface_tokens_recursively():
    payload = {
        "rows": {
            "canonical_stat::tower_damage": {
                "stat_name": "canonical_stat::tower_damage",
                "contributors": [
                    {"source_surface": "runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier"},
                ],
            }
        },
        "requested_surface_ids": [
            "mechanic_param::uw.black_hole.cooldown_seconds",
        ],
        "note": "legacy canonical_stat::tower_damage and runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier",
    }

    normalized = normalize_contract_payload(payload)

    assert "state::tower.damage" in normalized["rows"]
    assert normalized["rows"]["state::tower.damage"]["stat_name"] == "state::tower.damage"
    assert normalized["rows"]["state::tower.damage"]["contributors"][0]["source_surface"] == (
        "state::uw.black_hole.coin_bonus_multiplier"
    )
    assert normalized["requested_surface_ids"] == ["state::uw.black_hole.cooldown_seconds"]
    assert "canonical_stat::tower_damage" not in normalized["note"]


def test_surface_id_roundtrip__legacy_timing_uws_publish_under_v2_state_ids():
    v2 = to_v2_surface_id("mechanic_param::uw.black_hole.cooldown_seconds")
    assert v2 == "state::uw.black_hole.cooldown_seconds"
    assert to_legacy_surface_id(v2) == "mechanic_param::uw.black_hole.cooldown_seconds"


def test_model_construction__creates_valid_instances():
    stat_input = StatInput(
        stat_name="tower.hp",
        source_family="lab",
        source_name="health",
        value=1000.0,
        value_type="scalar",
        stage="additive_pre_cap",
    )
    stat_row = StatRow(
        stat_name="tower.hp",
        final_value=1000.0,
        value_type="scalar",
        source_count=1,
        contributors=[],
    )
    stat_book = StatBook(rows={"tower.hp": stat_row}, diagnostics={})
    assert stat_input.active is True
    assert stat_book.rows["tower.hp"].final_value == 1000.0


def test_state_identity_and_bound_preset_family__binds_successfully():
    identity = StateIdentity(
        account_snapshot_id="acct_abc",
        loadout_id="loadout_xyz",
        scenario_id="scen_123",
        runtime_branch_id="branch_base",
    )
    assert identity.as_tuple() == ("acct_abc", "loadout_xyz", "scen_123", "branch_base")

    bound = bind_preset_family(
        preset_name="Farming",
        state_mode="start_of_run",
        perk_namespace_class="canonical",
        explicit_card_preset_name=None,
        explicit_module_preset_name=None,
        explicit_perk_preset_name=None,
        active_perk_preset_name=None,
        perks_enabled=False,
    )
    assert isinstance(bound, BoundPresetFamily)
    assert bound.preset_name == "Farming"


def test_qe_resolution_planner__is_importable():
    planner = QEResolutionPlanner()
    assert planner is not None


def test_qe_shared_runtime_context__is_importable_and_cached():
    context = get_default_qe_shared_runtime_context()
    assert isinstance(context, QESharedRuntimeContext)
    assert context is get_default_qe_shared_runtime_context()
    payload = context.to_dict()
    assert payload["context_kind"] == "qe_shared_runtime_context"
    assert payload["consumer_bundle_count"] > 0
    assert payload["compiler_mapping_count"] > 0


def test_qe_resolution_planner_snapshot__carries_native_interface_label():
    from qe.routing import QEResolvedSnapshot

    snapshot = QEResolvedSnapshot(binding=None, stat_inputs=tuple(), statbook=StatBook(rows={}, diagnostics={}), resolution_path="report_snapshot_hybrid")
    assert snapshot.resolution_path == "report_snapshot_hybrid"


def test_qe_family_query_result__supports_native_family_path_shape():
    result = QEFamilyQueryResult(
        binding=None,
        stat_inputs=tuple(),
        family_id="progression_runtime_with_perks",
        requested_surface_ids=("state::tower.hp",),
        response=None,
        resolution_path="native_family_query",
    )
    assert result.family_id == "progression_runtime_with_perks"
    assert result.resolution_path == "native_family_query"


def test_qe_resolution_planner__can_run_native_family_query_for_progression_surface():
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    planner = QEResolutionPlanner()
    result = planner.resolve_family_query(
        state,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=True,
        requested_surface_ids=("state::tower.hp",),
    )

    assert result.resolution_path == "native_family_query"
    assert result.family_id == "progression_start_of_run"
    assert result.response.resolved_surface_rows[0].surface_id == "state::tower.hp"


def test_qe_resolution_planner__can_build_native_family_statbook_for_progression_surface():
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    planner = QEResolutionPlanner()
    statbook = planner.resolve_declared_family_statbook(
        state,
        family_id="progression_start_of_run",
        requested_surface_ids=("state::tower.hp",),
        notes="test native progression statbook",
        diagnostics={"source": "test"},
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
    )

    assert "state::tower.hp" in statbook.rows
    assert statbook.diagnostics["qe_resolution_interface"] == "native_family_query"
    assert statbook.diagnostics["qe_resolution_backend"] == "native_family_query"
    assert statbook.diagnostics["qe_native_family_id"] == "progression_start_of_run"


def test_qe_resolution_planner__report_snapshot_uses_hybrid_backend_when_native_family_exists():
    bundle = load_inputs()
    state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    planner = QEResolutionPlanner()
    snapshot = planner.resolve_report_snapshot(
        state,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
    )

    assert snapshot.resolution_path == "report_snapshot_hybrid"
    assert snapshot.statbook.diagnostics["qe_resolution_interface"] == "report_snapshot_planner"
    assert snapshot.statbook.diagnostics["qe_resolution_backend"] == "report_snapshot_hybrid"
    assert snapshot.statbook.diagnostics["qe_native_family_available"] is True


def test_runtime_formula_keys_have_explicit_authority() -> None:
    runtime_keys = {f'workshop:{key}' for key in WORKSHOP_FORMULA_VALUES} | {f'lab:{key}' for key in LAB_FORMULA_VALUES}
    assert runtime_keys == set(RUNTIME_FORMULA_AUTHORITY)


def test_runtime_formula_keys_have_single_valid_authority_source() -> None:
    allowed = {'canonical_formula_registry', 'approved_exception'}
    for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items():
        source = metadata.get('authority_source')
        assert source in allowed, f'{runtime_key} has unsupported authority source: {source!r}'
        if source == 'canonical_formula_registry':
            formula_id = (metadata.get('formula_id') or '').strip()
            assert formula_id, f'{runtime_key} is canonical but formula_id is empty.'
        if source == 'approved_exception':
            reason = (metadata.get('approved_exception_reason') or '').strip()
            assert reason, f'{runtime_key} approved_exception must include approved_exception_reason.'


def test_workshop_defense_pct_formula_matches_expected_track() -> None:
    defense_pct_formula = WORKSHOP_FORMULA_VALUES['Defense %']
    assert defense_pct_formula(99) == pytest.approx(49.5)


def test_runtime_formula_authority_migration_complete_or_exceptioned() -> None:
    non_migrated_entries = [
        runtime_key
        for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items()
        if (metadata.get('authority_source') or '').strip()
        not in {'canonical_formula_registry', 'approved_exception'}
    ]
    assert not non_migrated_entries, f'Found unsupported migration state entries: {non_migrated_entries}'


def test_runtime_formula_authority_has_1_to_1_runtime_coverage_and_valid_formula_ids() -> None:
    runtime_keys = {f'workshop:{key}' for key in WORKSHOP_FORMULA_VALUES} | {f'lab:{key}' for key in LAB_FORMULA_VALUES}
    authority_keys = set(RUNTIME_FORMULA_AUTHORITY)
    assert runtime_keys == authority_keys

    canonical_registry_path = Path(__file__).resolve().parents[2] / 'kb' / 'formulas' / 'tables' / 'canonical-formula-registry.csv'
    with canonical_registry_path.open(newline='', encoding='utf-8') as handle:
        canonical_formula_ids = {row['formula_id'].strip() for row in csv.DictReader(handle)}

    for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items():
        source = (metadata.get('authority_source') or '').strip()
        formula_id = (metadata.get('formula_id') or '').strip()
        if source == 'canonical_formula_registry':
            assert formula_id in canonical_formula_ids, f'{runtime_key} references unknown formula_id: {formula_id!r}'
        elif source == 'approved_exception':
            assert not formula_id, f'{runtime_key} approved_exception must not provide formula_id.'


def test_runtime_formula_authority_is_sourced_directly_from_kb_mapping_table() -> None:
    authority_table_path = Path(__file__).resolve().parents[2] / 'kb' / 'global-rules' / 'tables' / 'runtime-formula-authority.csv'
    with authority_table_path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    expected: dict[str, dict[str, str]] = {}
    for row in rows:
        runtime_key = f"{row['source_domain'].strip()}:{row['stat_name'].strip()}"
        source = row['authority_source'].strip()
        formula_id = (row.get('formula_id') or '').strip()
        reason = (row.get('approved_exception_reason') or '').strip()
        if source == 'canonical_formula_registry':
            expected[runtime_key] = {'authority_source': source, 'formula_id': formula_id}
        elif source == 'approved_exception':
            expected[runtime_key] = {
                'authority_source': source,
                'formula_id': '',
                'approved_exception_reason': reason,
            }

    assert RUNTIME_FORMULA_AUTHORITY == expected


def test_load_workshop_formulas_fails_closed_when_canonical_callable_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_authority_rows = kb_surfaces._load_runtime_formula_authority_rows()
    canonical_runtime_key = next(
        (domain, stat_name)
        for (domain, stat_name), metadata in runtime_authority_rows.items()
        if metadata.get('authority_source') == 'canonical_formula_registry'
    )
    canonical_runtime_key_text = f'{canonical_runtime_key[0]}:{canonical_runtime_key[1]}'

    monkeypatch.setattr(kb_surfaces, '_canonical_formula_callables', lambda: {})

    with pytest.raises(ValueError, match=canonical_runtime_key_text):
        kb_surfaces.load_workshop_formulas()


def test_load_workshop_formulas_uses_canonical_registry_callables_for_canonical_runtime_keys() -> None:
    workshop_formulas, lab_formulas = kb_surfaces.load_workshop_formulas()
    canonical_callables = kb_surfaces._canonical_formula_callables()
    runtime_authority_rows = kb_surfaces._load_runtime_formula_authority_rows()

    for (domain, stat_name), metadata in runtime_authority_rows.items():
        if metadata.get('authority_source') != 'canonical_formula_registry':
            continue
        runtime_key = f'{domain}:{stat_name}'
        expected_callable = canonical_callables[runtime_key]
        runtime_callable = workshop_formulas[stat_name] if domain == 'workshop' else lab_formulas[stat_name]
        assert runtime_callable(1) == pytest.approx(expected_callable(1)), f'{runtime_key} level-1 mismatch.'
        assert runtime_callable(99) == pytest.approx(expected_callable(99)), f'{runtime_key} level-99 mismatch.'


def test_scenario_projection_state__debug_payload_is_explicit():
    projection = ScenarioProjectionState(
        max_workshop=True,
        projected_perks=True,
        death_wave_health=True,
        berserker_damage_bonus=False,
    )
    assert projection.to_debug_dict() == {
        "max_workshop": True,
        "projected_perks": True,
        "death_wave_health": True,
        "berserker_damage_bonus": False,
    }


def test_run_stats_progression_core_bundle__resolves_for_progression_family():
    bundle = resolve_consumer_bundle(
        "run_stats",
        "progression_core_stats",
        family_id="progression_start_of_run",
        trace_mode="contributors",
    )
    assert bundle.family_id == "progression_start_of_run"
    assert "state::tower.hp" in bundle.surface_ids
    assert "state::tower.free_attack_upgrade_chance_pct" in bundle.surface_ids
    assert "state::module.orbital_augment.electron_count" in bundle.surface_ids
