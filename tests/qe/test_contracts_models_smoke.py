from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest
import yaml

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

ROOT = Path(__file__).resolve().parents[2]


RUNTIME_NON_FORMULA_OWNED_WHITELIST: set[str] = set()
MAX_APPROVED_EXCEPTION_COUNT = 0
MAX_NON_FORMULA_OWNED_COUNT = 0


def _contract_ids_from_yaml(path: Path) -> set[str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ids: set[str] = set()

    def collect(value):
        if isinstance(value, dict):
            if "id" in value:
                ids.add(str(value["id"]))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    return ids


def _contract_entries_from_yaml(path: Path) -> dict[str, dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries: dict[str, dict] = {}

    def collect(value):
        if isinstance(value, dict):
            if "id" in value:
                entries[str(value["id"])] = value
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    return entries


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
    assert normalized["requested_surface_ids"] == ["state::uw.black_hole.base_cooldown_seconds"]
    assert "canonical_stat::tower_damage" not in normalized["note"]


def test_normalize_contract_payload__keeps_clean_containers_and_converts_tuples():
    clean = {"rows": [{"surface_id": "state::tower.damage", "value": 1.0}]}
    tuple_payload = {"requested_surface_ids": ("state::tower.damage",)}

    assert normalize_contract_payload(clean) is clean
    assert normalize_contract_payload(tuple_payload) == {
        "requested_surface_ids": ["state::tower.damage"],
    }


def test_module_substat_registry_names_all_have_explicit_qe_routes():
    from qe.query_routing import slug_text

    route_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "query-routing-mappings.yaml").read_text(
            encoding="utf-8"
        )
    )
    canonical_ids = _contract_ids_from_yaml(
        ROOT / "kb" / "global-rules" / "contracts" / "canonical-stats.yaml"
    )
    mechanic_ids = _contract_ids_from_yaml(
        ROOT / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
    )

    routes = {
        slug_text(name): tuple(destination)
        for name, destination in route_contract["module_substat_name_to_destination"].items()
    }
    substat_names = {
        slug_text(row["substat"])
        for row in csv.DictReader(
            (ROOT / "kb" / "modules" / "tables" / "module-substats.csv").open(
                encoding="utf-8-sig"
            )
        )
        if row.get("substat")
    }

    missing_routes = sorted(name for name in substat_names if name not in routes)
    assert missing_routes == []

    bad_destinations = {}
    for name in sorted(substat_names):
        destination_type, destination_id = routes[name]
        if destination_type == "canonical_stat":
            ok = destination_id in canonical_ids
        elif destination_type in {"mechanic_param", "runtime_mechanic_param"}:
            ok = destination_id in mechanic_ids
        else:
            ok = False
        if not ok:
            bad_destinations[name] = (destination_type, destination_id)
    assert bad_destinations == {}


def test_requested_effect_family_closure_routes_target_existing_contract_ids():
    requested_families = {
        "bot_upgrade",
        "card",
        "enhancements",
        "module",
        "relic",
        "workshop",
    }
    expected_route_counts = {
        "bot_upgrade": 22,
        "card": 7,
        "enhancements": 17,
        "module": 42,
        "relic": 27,
        "workshop": 48,
    }
    contract_ids_by_type = {
        "canonical_stat": _contract_ids_from_yaml(
            ROOT / "kb" / "global-rules" / "contracts" / "canonical-stats.yaml"
        ),
        "mechanic_param": _contract_ids_from_yaml(
            ROOT / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
        ),
        "runtime_mechanic_param": _contract_ids_from_yaml(
            ROOT / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
        ),
        "environment_param": _contract_ids_from_yaml(
            ROOT / "kb" / "global-rules" / "contracts" / "environment-params.yaml"
        ),
        "capability": _contract_ids_from_yaml(
            ROOT / "kb" / "global-rules" / "contracts" / "capabilities.yaml"
        ),
    }

    family_counts: Counter[str] = Counter()
    bad_destinations = {}
    bad_statuses = {}
    with (ROOT / "kb" / "ledgers" / "tables" / "contributor-routing-closure.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            family = str(row.get("source_family") or "").strip()
            if family not in requested_families:
                continue
            contributor_id = str(row.get("contributor_id") or "").strip()
            destination_type = str(row.get("destination_object_type") or "").strip()
            destination_id = str(row.get("destination_id") or "").strip()
            family_counts[family] += 1
            if row.get("registration_status") != "registered":
                bad_statuses[contributor_id] = row.get("registration_status")
            valid_ids = contract_ids_by_type.get(destination_type)
            if valid_ids is None or destination_id not in valid_ids:
                bad_destinations[contributor_id] = (destination_type, destination_id)

    assert dict(sorted(family_counts.items())) == expected_route_counts
    assert bad_statuses == {}
    assert bad_destinations == {}


def test_relic_input_registry_has_explicit_semantic_units():
    registry_path = ROOT / "kb" / "global-rules" / "tables" / "relic-input-registry.csv"
    rows = {
        row["contributor_id"]: row
        for row in csv.DictReader(registry_path.open(newline="", encoding="utf-8"))
    }
    expected_hints = {
        "relic__tower__lab_speed__pct": "pct_bonus",
        "relic__tower__ultimate_damage__pct": "pct_bonus",
        "relic__tower__attack_speed__pct": "pct_bonus",
        "relic__tower__crit_chance__pct": "percent_points",
        "relic__tower__crit_multiplier__pct": "pct_bonus",
        "relic__tower__damage_per_meter__pct": "pct_bonus",
        "relic__tower__supercrit_chance__pct": "percent_points",
        "relic__tower__supercrit_multiplier__pct": "pct_bonus",
        "relic__tower__rend_armor_multiplier__pct": "pct_bonus",
        "relic__tower__defense_pct__pct": "percent_points",
        "relic__tower__thorns__pct": "percent_points",
        "relic__tower__knockback_force__pct": "pct_bonus",
        "relic__tower__orb_speed__pct": "pct_bonus",
        "relic__tower__cash__pct": "pct_bonus",
        "relic__tower__coins__pct": "pct_bonus",
        "relic__tower__free_attack_upgrade__pct": "percent_points",
        "relic__tower__free_defense_upgrade__pct": "percent_points",
        "relic__tower__free_utility_upgrade__pct": "percent_points",
        "relic__tower__recovery_amount__pct": "percent_points",
        "relic__tower__enemy_attack_level_skip__pct": "percent_points",
        "relic__tower__enemy_health_level_skip__pct": "percent_points",
    }

    ambiguous = {
        contributor_id
        for contributor_id, row in rows.items()
        if row.get("semantic_unit_hint") == "percent_points_or_pct_bonus"
    }
    assert ambiguous == set()
    for contributor_id, expected_hint in expected_hints.items():
        assert rows[contributor_id]["semantic_unit_hint"] == expected_hint


def test_requested_effect_family_closure_matches_contributor_mappings():
    requested_families = {
        "bot_upgrade",
        "card",
        "enhancements",
        "module",
        "relic",
        "workshop",
    }
    mapping_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "contributor-mappings-full.yaml").read_text(
            encoding="utf-8"
        )
    )
    mapped_routes = {
        family: {
            row["contributor_id"]: (
                row["destination_object_type"],
                row["destination_id"],
            )
            for row in mapping_contract["source_families"][family]
        }
        for family in requested_families
    }
    closure_routes = {family: {} for family in requested_families}
    with (ROOT / "kb" / "ledgers" / "tables" / "contributor-routing-closure.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            family = row.get("source_family")
            if family not in requested_families:
                continue
            closure_routes[family][row["contributor_id"]] = (
                row["destination_object_type"],
                row["destination_id"],
            )

    assert closure_routes == mapped_routes


def test_module_closure_ledger_covers_all_module_contributor_mappings():
    mapping_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "contributor-mappings-full.yaml").read_text(
            encoding="utf-8"
        )
    )
    mapped_module_routes = {
        row["contributor_id"]: (
            row["destination_object_type"],
            row["destination_id"],
        )
        for row in mapping_contract["source_families"]["module"]
    }
    closure_routes = {}
    with (ROOT / "kb" / "ledgers" / "tables" / "contributor-routing-closure.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            if row.get("source_family") != "module":
                continue
            closure_routes[row["contributor_id"]] = (
                row["destination_object_type"],
                row["destination_id"],
            )

    assert closure_routes == mapped_module_routes


def test_relic_registry_and_closure_ledger_match_contributor_mappings():
    mapping_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "contributor-mappings-full.yaml").read_text(
            encoding="utf-8"
        )
    )
    mapped_relic_routes = {
        row["contributor_id"]: (
            row["destination_object_type"],
            row["destination_id"],
            row["resolver"],
        )
        for row in mapping_contract["source_families"]["relic"]
    }

    registry_routes = {}
    with (ROOT / "kb" / "global-rules" / "tables" / "relic-input-registry.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            registry_routes[row["contributor_id"]] = (
                row["destination_object_type"],
                row["destination_id"],
                row["resolver"],
            )

    closure_routes = {}
    with (ROOT / "kb" / "ledgers" / "tables" / "contributor-routing-closure.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            if row.get("source_family") != "relic":
                continue
            closure_routes[row["contributor_id"]] = (
                row["destination_object_type"],
                row["destination_id"],
                mapped_relic_routes[row["contributor_id"]][2],
            )

    assert registry_routes == mapped_relic_routes
    assert closure_routes == mapped_relic_routes


def test_card_effect_registry_base_targets_are_qe_routable():
    from qe.query_routing import slug_text

    route_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "query-routing-mappings.yaml").read_text(
            encoding="utf-8"
        )
    )
    direct_targets = set(route_contract["card_target_surface_to_destination"])
    canonical_targets = set(route_contract["card_target_surface_to_canonical"])
    fallback_names = set(route_contract["card_name_fallback_destination"])

    unrouted = {}
    route_counts: Counter[str] = Counter()
    with (ROOT / "kb" / "cards" / "tables" / "card-effect-registry.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            if row.get("layer") != "base_card":
                continue
            card_id = str(row.get("card_id") or "").strip()
            target_surface = str(row.get("target_surface") or "").strip()
            effect_name = slug_text(str(row.get("effect_name") or ""))
            if target_surface in direct_targets:
                route_counts["direct_target"] += 1
            elif target_surface in canonical_targets:
                route_counts["canonical_target"] += 1
            elif effect_name in fallback_names:
                route_counts["fallback_name"] += 1
            else:
                unrouted[card_id] = (effect_name, target_surface)

    assert sum(route_counts.values()) == 31
    assert route_counts == {
        "direct_target": 29,
        "canonical_target": 1,
        "fallback_name": 1,
    }
    assert unrouted == {}


def test_card_mastery_registry_effects_have_declared_mechanic_params():
    from qe.query_routing import slug_text

    def unit_from_token(raw: str) -> str:
        token = str(raw or "").strip().replace("+", "")
        if token.startswith("x"):
            return "multiplier"
        if token.endswith("%"):
            return "pct"
        if token.endswith("s"):
            return "seconds"
        return "count"

    mechanic_entries = _contract_entries_from_yaml(
        ROOT / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
    )
    expected = {}
    inconsistent_units = {}
    with (ROOT / "kb" / "cards" / "tables" / "card-masteries.csv").open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            raw_name = str(row.get("card_mastery") or "").strip()
            if not raw_name:
                continue
            card_name = "Recovery Package Chance" if raw_name == "Package Chance" else raw_name
            mastery_name = f"{card_name} Mastery"
            card_slug = slug_text(mastery_name[:-8]).replace(" ", "_")
            destination_id = f"cards.{card_slug}.mastery_effect"
            units = {unit_from_token(row[f"level_{level}"]) for level in range(10)}
            if len(units) != 1:
                inconsistent_units[mastery_name] = sorted(units)
                continue
            expected[destination_id] = units.pop()

    assert len(expected) == 31
    assert inconsistent_units == {}

    missing = sorted(destination_id for destination_id in expected if destination_id not in mechanic_entries)
    assert missing == []

    bad_metadata = {}
    for destination_id, expected_unit in sorted(expected.items()):
        entry = mechanic_entries[destination_id]
        expected_resolver = "integer_count_param" if expected_unit == "count" else "standard_scalar_param"
        if entry.get("unit") != expected_unit or entry.get("resolver") != expected_resolver:
            bad_metadata[destination_id] = {
                "expected": {
                    "unit": expected_unit,
                    "resolver": expected_resolver,
                },
                "actual": {
                    "unit": entry.get("unit"),
                    "resolver": entry.get("resolver"),
                },
            }

    assert bad_metadata == {}


def test_thunder_bot_linger_split_keeps_upgrade_slow_and_lab_duration():
    from qe.stat_input_compiler import BOT_UPGRADE_BINDINGS

    route_contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "query-routing-mappings.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert BOT_UPGRADE_BINDINGS[("Thunder Bot", "Linger")] == (
        "bot_upgrade__thunder_bot__linger_slow__pct",
        "linger_seconds",
    )
    assert tuple(route_contract["uw_lab_direct_destination"]["Thunder Bot - Linger Time"]) == (
        "mechanic_param",
        "bot.thunder.linger_duration_seconds",
    )


def test_qe_publication_display_text_normalizer_caches_string_inputs():
    from qe.publication import _normalize_display_text, _normalize_display_text_from_string

    _normalize_display_text_from_string.cache_clear()

    assert _normalize_display_text(None) == "—"
    assert _normalize_display_text(" +  2.500 % ") == "+ 2.5%"
    assert _normalize_display_text(" +  2.500 % ") == "+ 2.5%"

    cache_info = _normalize_display_text_from_string.cache_info()
    assert cache_info.hits >= 1
    assert cache_info.currsize == 2


def test_surface_id_roundtrip__legacy_owned_uw_tracks_publish_under_distinct_base_state_ids():
    v2 = to_v2_surface_id("mechanic_param::uw.black_hole.cooldown_seconds")
    assert v2 == "state::uw.black_hole.base_cooldown_seconds"
    assert to_legacy_surface_id(v2) == "mechanic_param::uw.black_hole.cooldown_seconds"


def test_surface_id_roundtrip__runtime_timing_uws_publish_under_effective_state_ids():
    v2 = to_v2_surface_id("runtime_mechanic_param::uw.black_hole.cooldown_seconds")
    assert v2 == "state::uw.black_hole.cooldown_seconds"
    assert to_legacy_surface_id(v2) == "runtime_mechanic_param::uw.black_hole.cooldown_seconds"


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


def test_environment_param_metadata_declares_enemy_level_skip_reduction_unit():
    from qe.routing import load_bounded_resolution_metadata

    metadata = load_bounded_resolution_metadata()

    assert metadata['bc.enemy_level_skip_reduction_pp'] == {
        'domain': 'bc',
        'unit': 'pct',
        'resolver': 'bc_effective_value',
    }


def test_capability_metadata_loads_capabilities_contract_units():
    from qe.routing import load_bounded_resolution_metadata

    metadata = load_bounded_resolution_metadata()

    assert metadata['capability.additional_card_slot.count'] == {
        'domain': 'capability',
        'unit': 'count',
        'resolver': 'capability_passthrough',
    }
    assert metadata['capability.perks.first_choice'] == {
        'domain': 'capability',
        'unit': 'enum',
        'resolver': 'capability_passthrough',
    }


def test_account_metadata_contract_units_load_into_bounded_metadata():
    from qe.routing import load_bounded_resolution_metadata

    metadata = load_bounded_resolution_metadata()

    assert metadata['account_flag.disable_ads'] == {
        'domain': 'account_flag',
        'unit': 'bool',
        'resolver': 'capability_passthrough',
    }
    assert metadata['account_meta.total_relic_count'] == {
        'domain': 'account_meta',
        'unit': 'count',
        'resolver': 'standard_scalar_param',
    }
    assert metadata['game_runtime.speed_multiplier'] == {
        'domain': 'game_runtime',
        'unit': 'multiplier',
        'resolver': 'standard_scalar_param',
    }


def test_enemy_level_skip_reduction_environment_param_resolves_with_pct_schema():
    from qe.routing import load_bounded_resolution_metadata, resolve_bounded_bucket

    metadata = load_bounded_resolution_metadata()
    contributor = StatInput(
        stat_name='Enemy Level Skip Reduction',
        source_family='lab',
        source_name='Enemy Level Skip Reduction',
        value=2.5,
        value_type='percent_display',
        stage='additive_pre_cap',
        destination_object_type='environment_param',
        destination_id='bc.enemy_level_skip_reduction_pp',
        resolver_id='bc_effective_value',
        kb_mapped=True,
    )

    final_value, status, _notes, schema = resolve_bounded_bucket(
        'environment_param',
        'bc.enemy_level_skip_reduction_pp',
        [contributor],
        metadata['bc.enemy_level_skip_reduction_pp'],
    )

    assert status == 'resolved'
    assert final_value == pytest.approx(2.5)
    assert schema['unit'] == 'pct'
    assert 'percentage_points' in schema['expected_input_semantics']


def test_ranged_enemy_attack_distance_rule_resolves_as_raw_text_passthrough():
    from qe.routing import load_bounded_resolution_metadata, resolve_bounded_bucket

    metadata = load_bounded_resolution_metadata()
    contributor = StatInput(
        stat_name='Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3::effect_1',
        source_family='perk',
        source_name='Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3',
        value='wiki_named_effect',
        value_type='raw_text',
        stage='run_selected',
        destination_object_type='environment_param',
        destination_id='enemy.ranged.attack_distance_rule',
        resolver_id='raw_text_passthrough',
        kb_mapped=True,
    )

    final_value, status, _notes, schema = resolve_bounded_bucket(
        'environment_param',
        'enemy.ranged.attack_distance_rule',
        [contributor],
        metadata['enemy.ranged.attack_distance_rule'],
    )

    assert status == 'resolved'
    assert final_value == 'wiki_named_effect'
    assert schema['unit'] == 'raw_text'
    assert 'raw_text' in schema['expected_input_semantics']


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
    allowed = {'canonical_formula_registry'}
    approved_exception_keys: set[str] = set()
    non_formula_owned_keys: set[str] = set()

    for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items():
        source = metadata.get('authority_source')
        assert source in allowed, f'{runtime_key} has unsupported authority source: {source!r}'
        if source == 'canonical_formula_registry':
            formula_id = (metadata.get('formula_id') or '').strip()
            assert formula_id, f'{runtime_key} is canonical but formula_id is empty.'
    assert approved_exception_keys == set()
    assert len(approved_exception_keys) <= MAX_APPROVED_EXCEPTION_COUNT
    assert non_formula_owned_keys == RUNTIME_NON_FORMULA_OWNED_WHITELIST
    assert len(non_formula_owned_keys) <= MAX_NON_FORMULA_OWNED_COUNT


def test_bot_effective_range_formula_policy__exists_for_all_tower_range_amplified_bots() -> None:
    policy_path = ROOT / "kb" / "ledgers" / "formula_surface_policy.yaml"
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    surfaces = payload["surfaces"]
    expected = {
        "state::bot.golden.effective_range_m": "state::bot.golden.range_m",
        "state::bot.amplify.effective_range_m": "state::bot.amplify.range_m",
        "state::bot.flame.effective_range_m": "state::bot.flame.range_m",
        "state::bot.thunder.effective_range_m": "state::bot.thunder.range_m",
    }

    for surface_id, raw_surface_id in expected.items():
        assert surface_id in surfaces, f"Missing sanctioned formula policy for {surface_id}"
        entry = surfaces[surface_id]
        rationale = str(entry.get("rationale") or "")
        assert entry.get("publish_policy") == "allow_if_resolved"
        assert "state::bot.global.range_bonus_m" in rationale
        assert "1.33 * (state::tower.range_m / 69.5)" in rationale
        assert raw_surface_id in rationale


def test_dissonant_run_restriction_contract__owns_boss_wave_masks() -> None:
    from qe.kb_surfaces import load_dissonant_run_restrictions

    restrictions = load_dissonant_run_restrictions()

    assert set(restrictions) == {"attack", "defense", "utility", "ultimate_weapons"}
    assert restrictions["attack"]["disabled_category"] == "Attack"
    assert restrictions["attack"]["max_boost"] == pytest.approx(5.0)
    assert "range is locked to 30m" in restrictions["attack"]["public_restriction_summary"]
    assert restrictions["attack"]["workshop_tracks"] == (
        "Damage",
        "Attack Speed",
        "Critical Chance",
        "Critical Factor",
        "Range",
        "Damage / Meter",
        "Multishot Chance",
        "Multishot Targets",
        "Rapid Fire Chance",
        "Rapid Fire Duration",
        "Bounce Shot Chance",
        "Bounce Shot Targets",
        "Bounce Shot Range",
        "Super Critical Chance",
        "Super Critical Mult",
        "Rend Armor Chance",
        "Rend Armor Mult",
    )
    assert restrictions["attack"]["zero_workshop_tracks"] == restrictions["attack"]["workshop_tracks"]
    assert restrictions["attack"]["stat_surface_restrictions"]["state::tower.damage"] == pytest.approx(1.0)
    assert restrictions["attack"]["stat_surface_restrictions"]["state::tower.attack_speed"] == pytest.approx(1.0)
    assert restrictions["attack"]["primitive_restrictions"]["tower_damage"] == pytest.approx(1.0)
    assert restrictions["attack"]["primitive_restrictions"]["tower_attack_speed"] == pytest.approx(1.0)
    assert "Bounce Shot Range" in restrictions["attack"]["zero_workshop_tracks"]
    assert restrictions["defense"]["disabled_category"] == "Defense"
    assert restrictions["defense"]["max_boost"] == pytest.approx(5.0)
    assert "Health is locked to 1" in restrictions["defense"]["public_restriction_summary"]
    assert restrictions["defense"]["workshop_tracks"] == (
        "Health",
        "Health Regen",
        "Defense %",
        "Defense Absolute",
        "Thorn Damage",
        "Lifesteal",
        "Knockback Chance",
        "Knockback Force",
        "Orb Speed",
        "Orbs",
        "Shockwave Size",
        "Shockwave Frequency",
        "Land Mine Chance",
        "Land Mine Damage",
        "Land Mine Radius",
        "Death Defy",
        "Wall Health",
        "Wall Rebuild",
    )
    assert restrictions["defense"]["zero_workshop_tracks"] == restrictions["defense"]["workshop_tracks"]
    assert restrictions["defense"]["non_workshop_runtime_effects"] == (
        "Wall Regen",
        "Wall Thorns",
        "Wall Invincibility",
        "Wall Fortification",
    )
    assert restrictions["defense"]["stat_surface_restrictions"]["state::tower.hp"] == pytest.approx(1.0)
    assert restrictions["defense"]["stat_surface_restrictions"]["state::wall.hp"] == pytest.approx(0.0)
    assert restrictions["defense"]["primitive_restrictions"]["tower_hp"] == pytest.approx(1.0)
    assert restrictions["defense"]["primitive_restrictions"]["tower_shockwave_size_m"] == pytest.approx(0.0)
    assert restrictions["defense"]["primitive_restrictions"]["wall_thorns_damage_increase_per_hit"] == pytest.approx(0.0)
    assert "Orbs" in restrictions["defense"]["zero_workshop_tracks"]
    assert restrictions["utility"]["disabled_category"] == "Utility"
    assert restrictions["utility"]["max_boost"] == pytest.approx(3.0)
    assert "enemy level skips are disabled" in restrictions["utility"]["public_restriction_summary"]
    assert restrictions["utility"]["workshop_tracks"] == (
        "Cash Bonus",
        "Cash / Wave",
        "Coin / Kill Bonus",
        "Coin / Wave",
        "Free Attack Upgrade",
        "Free Defense Upgrade",
        "Free Utility Upgrade",
        "Interest / Wave",
        "Recovery Amount",
        "Max Amount",
        "Package Chance",
        "Enemy Attack Level Skip",
        "Enemy Health Level Skip",
    )
    assert restrictions["utility"]["zero_workshop_tracks"] == restrictions["utility"]["workshop_tracks"]
    assert restrictions["utility"]["stat_surface_restrictions"]["state::tower.enemy_attack_level_skip_pct"] == pytest.approx(0.0)
    assert restrictions["utility"]["stat_surface_restrictions"]["state::economy.coins_per_kill_bonus"] == pytest.approx(0.0)
    assert restrictions["utility"]["primitive_restrictions"]["attack_skip_workshop_track"] == ""
    assert "Enemy Attack Level Skip" in restrictions["utility"]["zero_workshop_tracks"]
    assert restrictions["ultimate_weapons"]["disabled_category"] == "Ultimate Weapons"
    assert restrictions["ultimate_weapons"]["max_boost"] == pytest.approx(5.0)
    assert restrictions["ultimate_weapons"]["public_restriction_summary"] == "All ultimate weapons are disabled."
    assert restrictions["ultimate_weapons"]["workshop_tracks"] == ()
    assert restrictions["ultimate_weapons"]["ultimate_weapon_tracks"] == (
        "Black Hole",
        "Chain Lightning",
        "Chrono Field",
        "Death Wave",
        "Golden Tower",
        "Inner Land Mines",
        "Poison Swamp",
        "Smart Missiles",
        "Spotlight",
    )
    assert restrictions["ultimate_weapons"]["stat_surface_restrictions"]["state::uw.chain_lightning.damage_multiplier"] == pytest.approx(0.0)
    assert restrictions["ultimate_weapons"]["stat_surface_restrictions"]["state::uw.chrono_field.damage_reduction_pct"] == pytest.approx(0.0)
    conditional = restrictions["ultimate_weapons"]["conditional_primitive_restrictions"]["gc_boss_damage_per_second"]
    assert conditional["unless_gc_boss_damage_source"] == "runtime_input_boss_applicable_damage_per_second"
    assert conditional["value"] == pytest.approx(0.0)


def test_dissonant_run_scenario_context_restricts_qe_stat_surfaces() -> None:
    from qe.kb_surfaces import load_dissonant_run_restrictions
    from qe.publication import publish_query_surfaces
    from qe.routing import query_response_to_statbook, resolve_checkpoint_surfaces

    bundle = load_inputs()
    account_state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )

    restrictions = load_dissonant_run_restrictions()
    support_surfaces = tuple(
        f"support_surface::dissonance.{category}_run_active"
        for category in restrictions
    )

    def restricted_book(category: str) -> StatBook:
        spec = restrictions[category]
        requested_surface_ids = tuple(
            dict.fromkeys(
                tuple(dict(spec.get("stat_surface_restrictions") or {}).keys())
                + support_surfaces
            )
        )
        response = resolve_checkpoint_surfaces(
            account_state,
            requested_surface_ids=requested_surface_ids,
            preset_name="Farming",
            state_mode="start_of_run",
            perks_enabled=False,
            scenario_context={"mode_id": "farming", "tier": 14, "dissonance_run_category": category},
        )
        book = query_response_to_statbook(response, notes=f"test {category} dissonance scenario")
        publish_query_surfaces(book.rows, account_state_labs=account_state.labs)
        return book

    default_response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=support_surfaces,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
        scenario_context={"mode_id": "farming", "tier": 14, "dissonance_run_category": "none"},
    )
    default_book = query_response_to_statbook(
        default_response,
        notes="test default non-dissonant scenario",
    )
    publish_query_surfaces(default_book.rows, account_state_labs=account_state.labs)
    for support_surface_id in support_surfaces:
        row = default_book.rows[support_surface_id]
        assert row.status == "resolved"
        assert row.final_value is False

    books = {category: restricted_book(category) for category in restrictions}

    for category, spec in restrictions.items():
        book = books[category]
        for support_category in restrictions:
            support_surface_id = f"support_surface::dissonance.{support_category}_run_active"
            assert book.rows[support_surface_id].final_value is (support_category == category)
        for surface_id, expected_value in dict(spec.get("stat_surface_restrictions") or {}).items():
            actual_value = book.rows[str(surface_id)].final_value
            if isinstance(expected_value, bool):
                assert actual_value is expected_value
            elif isinstance(expected_value, str):
                assert actual_value == expected_value
            else:
                assert actual_value == pytest.approx(float(expected_value))

    attack_book = books["attack"]
    assert attack_book.rows["support_surface::dissonance.attack_run_active"].final_value is True
    assert attack_book.rows["support_surface::dissonance.defense_run_active"].final_value is False
    assert attack_book.rows["state::tower.damage"].final_value == pytest.approx(1.0)
    assert attack_book.rows["state::tower.attack_speed"].final_value == pytest.approx(1.0)
    assert attack_book.rows["state::tower.range_m"].final_value == pytest.approx(30.0)
    assert attack_book.rows["derived::edamage.attack_dissonance_restricted"].final_value == pytest.approx(1.0)

    defense_book = books["defense"]
    assert defense_book.rows["support_surface::dissonance.defense_run_active"].final_value is True
    assert defense_book.rows["state::tower.hp"].final_value == pytest.approx(1.0)
    assert defense_book.rows["state::tower.regen"].final_value == pytest.approx(1.0)
    assert defense_book.rows["state::wall.hp"].final_value == pytest.approx(0.0)
    assert defense_book.rows["state::wall.fortification_multiplier"].final_value == pytest.approx(1.0)
    assert defense_book.rows["derived::ehp"].final_value <= 1.0

    utility_book = books["utility"]
    assert utility_book.rows["support_surface::dissonance.utility_run_active"].final_value is True
    assert utility_book.rows["state::tower.free_attack_upgrade_chance_pct"].final_value == pytest.approx(0.0)
    assert utility_book.rows["state::tower.enemy_attack_level_skip_pct"].final_value == pytest.approx(0.0)
    assert utility_book.rows["state::economy.coins_per_kill_bonus"].final_value == pytest.approx(0.0)
    assert utility_book.rows["state::tower.package_chance_pct"].final_value == pytest.approx(0.0)
    assert utility_book.rows["derived::eecon"].final_value == pytest.approx(0.0)

    uw_book = books["ultimate_weapons"]
    assert uw_book.rows["support_surface::dissonance.ultimate_weapons_run_active"].final_value is True
    assert uw_book.rows["state::uw.chain_lightning.damage_multiplier"].final_value == pytest.approx(0.0)
    assert uw_book.rows["state::uw.chrono_field.damage_reduction_pct"].final_value == pytest.approx(0.0)
    assert uw_book.rows["derived::edamage.uw.chain_lightning_dps"].final_value == pytest.approx(0.0)


def test_enemy_ultimate_enabled_context_surfaces_resolve_as_booleans() -> None:
    bundle = load_inputs()
    account_state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )

    lab_names_by_surface = {
        "context::enemy.fast.ultimate_enabled": "Fast's Ultimate",
        "context::enemy.ranged.ultimate_enabled": "Ranged Ultimate",
        "context::enemy.boss.ultimate_enabled": "Boss's Ultimate",
        "context::enemy.basic.ultimate_enabled": "Basic's Ultimate",
        "context::enemy.tank.ultimate_enabled": "Tank's Ultimate",
        "context::enemy.protector.ultimate_enabled": "Protector's Ultimate",
    }

    snapshot = QEResolutionPlanner().resolve_report_snapshot(
        account_state,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
    )

    for surface_id, lab_name in lab_names_by_surface.items():
        try:
            expected = float(account_state.labs.get(lab_name, 0) or 0) > 0
        except (TypeError, ValueError):
            expected = bool(account_state.labs.get(lab_name))
        row = snapshot.statbook.rows[surface_id]
        assert row.status == "resolved"
        assert row.final_value is expected


def test_report_snapshot_resolves_level_and_duration_account_surfaces() -> None:
    bundle = load_inputs()
    account_state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    snapshot = QEResolutionPlanner().resolve_report_snapshot(
        account_state,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
    )

    level_surface_ids = (
        "state::labs.dissonant_echo.attack.level",
        "state::labs.dissonant_echo.defense.level",
        "state::labs.dissonant_echo.utility.level",
        "state::labs.dissonant_echo.ultimate_weapons.level",
        "state::tower.range_lab_level",
        "state::shockwave.size_lab_level",
    )
    for surface_id in level_surface_ids:
        row = snapshot.statbook.rows[surface_id]
        assert row.status == "resolved"
        assert row.schema["unit"] == "level"
        assert row.final_value == pytest.approx(float(row.contributors[0]["value"]))

    duration_row = snapshot.statbook.rows["state::module.amplifying_strike.tower_damage_5x_duration_s"]
    assert duration_row.status == "resolved"
    assert duration_row.schema["unit"] == "seconds"
    assert duration_row.final_value == pytest.approx(float(duration_row.contributors[0]["value"]))


def test_report_snapshot_resolves_raw_text_passthrough_surfaces() -> None:
    bundle = load_inputs()
    account_state = build_runtime_state(
        bundle.ids_raw,
        default_preset="Farming",
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )
    snapshot = QEResolutionPlanner().resolve_report_snapshot(
        account_state,
        preset_name="Farming",
        state_mode="start_of_run",
        perks_enabled=False,
    )

    expected_values = {
        "state::capability.target_priority": "2",
        "state::capability.perks.first_choice": "1",
        "state::capability.perks.auto_pick_ranking": "12",
        "state::meta.account_context.farming_tier": "Tier 14",
    }

    for surface_id, expected_value in expected_values.items():
        row = snapshot.statbook.rows[surface_id]
        assert row.status == "resolved"
        assert row.final_value == expected_value
        assert "raw_text" in row.schema["expected_input_semantics"]


def test_level_contributors_still_block_non_level_formula_surfaces() -> None:
    from qe.routing import resolve_bounded_bucket

    contributor = StatInput(
        stat_name="Example Formula Level",
        source_family="lab",
        source_name="Example Formula",
        value=26.0,
        value_type="level",
        stage="account_state",
        destination_object_type="mechanic_param",
        destination_id="example.multiplier",
        resolver_id="standard_scalar_param",
        kb_mapped=True,
    )

    final_value, status, notes, schema = resolve_bounded_bucket(
        "mechanic_param",
        "example.multiplier",
        [contributor],
        {"unit": "unknown", "resolver": "standard_scalar_param"},
    )

    assert final_value is None
    assert status == "mapped_not_resolved"
    assert "unresolved" in notes
    assert "level" not in schema["expected_input_semantics"]


def test_raw_text_contributors_still_block_non_passthrough_formula_surfaces() -> None:
    from qe.routing import resolve_bounded_bucket

    contributor = StatInput(
        stat_name="Example Formula Text",
        source_family="lab",
        source_name="Example Formula",
        value="Tier 14",
        value_type="raw_text",
        stage="account_state",
        destination_object_type="mechanic_param",
        destination_id="example.multiplier",
        resolver_id="standard_scalar_param",
        kb_mapped=True,
    )

    final_value, status, notes, schema = resolve_bounded_bucket(
        "mechanic_param",
        "example.multiplier",
        [contributor],
        {"unit": "unknown", "resolver": "standard_scalar_param"},
    )

    assert final_value is None
    assert status == "mapped_not_resolved"
    assert "unresolved" in notes
    assert "raw_text" not in schema["expected_input_semantics"]


def test_bot_runtime_contract__declares_raw_and_effective_range_split() -> None:
    contract_path = ROOT / "kb" / "bots" / "contracts" / "bot-runtime-contract.md"
    text = contract_path.read_text(encoding="utf-8")

    assert "## Bot Range Ownership" in text
    assert "### Raw range owners" in text
    assert "### Shared flat bonus owner" in text
    assert "### Effective range family" in text
    assert "### Effective range formula" in text
    assert "state::bot.global.range_bonus_m" in text
    assert "state::bot.golden.effective_range_m" in text
    assert "state::bot.amplify.effective_range_m" in text
    assert "state::bot.flame.effective_range_m" in text
    assert "state::bot.thunder.effective_range_m" in text
    assert "(raw_bot_range_m + state::bot.global.range_bonus_m) * 1.33 * (state::tower.range_m / 69.5)" in text


def test_workshop_defense_pct_formula_matches_expected_track() -> None:
    defense_pct_formula = WORKSHOP_FORMULA_VALUES['Defense %']
    assert defense_pct_formula(99) == pytest.approx(49.5)


def test_workshop_attack_chance_formulas_match_verified_max_rows() -> None:
    assert WORKSHOP_FORMULA_VALUES['Multishot Chance'](99) == pytest.approx(49.5)
    assert WORKSHOP_FORMULA_VALUES['Rapid Fire Chance'](85) == pytest.approx(34.0)
    assert WORKSHOP_FORMULA_VALUES['Bounce Shot Chance'](0) == pytest.approx(0.0)
    assert WORKSHOP_FORMULA_VALUES['Bounce Shot Chance'](85) == pytest.approx(68.0)


def test_workshop_interest_per_wave_formula_matches_corrected_track() -> None:
    interest_formula = WORKSHOP_FORMULA_VALUES['Interest / Wave']
    assert interest_formula(99) == pytest.approx(5.94)


def test_workshop_wall_rebuild_formula_matches_corrected_track() -> None:
    wall_rebuild_formula = WORKSHOP_FORMULA_VALUES['Wall Rebuild']
    assert wall_rebuild_formula(1) == pytest.approx(1198.0)
    assert wall_rebuild_formula(300) == pytest.approx(600.0)


def test_runtime_formula_authority_migration_complete_or_exceptioned() -> None:
    non_migrated_entries = [
        runtime_key
        for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items()
        if (metadata.get('authority_source') or '').strip()
        not in {'canonical_formula_registry'}
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
        else:
            pytest.fail(f'{runtime_key} has unexpected authority source {source!r}.')


def test_runtime_formula_authority_canonical_entries_use_runtime_callable_generator_kinds() -> None:
    canonical_registry_path = Path(__file__).resolve().parents[2] / 'kb' / 'formulas' / 'tables' / 'canonical-formula-registry.csv'
    with canonical_registry_path.open(newline='', encoding='utf-8') as handle:
        formula_rows_by_id = {row['formula_id'].strip(): row for row in csv.DictReader(handle)}

    for runtime_key, metadata in RUNTIME_FORMULA_AUTHORITY.items():
        if (metadata.get('authority_source') or '').strip() != 'canonical_formula_registry':
            continue
        formula_id = (metadata.get('formula_id') or '').strip()
        formula_row = formula_rows_by_id[formula_id]
        generator_kind = (formula_row.get('generator_kind') or '').strip()
        assert generator_kind in kb_surfaces.RUNTIME_CALLABLE_GENERATOR_KINDS, (
            f'{runtime_key} references formula_id {formula_id!r} with unsupported generator_kind {generator_kind!r}.'
        )


def test_canonical_formula_callables_fails_with_runtime_key_and_formula_id_for_unsupported_generator_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_key = ('workshop', 'Damage')
    formula_id = 'tower.damage.test'

    monkeypatch.setattr(
        kb_surfaces,
        '_load_runtime_formula_authority_rows',
        lambda: {
            runtime_key: {
                'authority_source': 'canonical_formula_registry',
                'formula_id': formula_id,
                'approved_exception_reason': '',
            }
        },
    )
    monkeypatch.setattr(
        kb_surfaces,
        '_read_csv',
        lambda path: [
            {
                'formula_id': formula_id,
                'generator_kind': 'exact_linear_generator_from_live_wiki',
                'domain': 'workshop',
                'start_level': '0',
                'base_value': '1',
                'delta_per_step': '1',
            }
        ]
        if path == kb_surfaces._CANONICAL_FORMULA_REGISTRY_PATH
        else [],
    )

    with pytest.raises(
        ValueError,
        match=r"workshop:Damage uses unsupported generator_kind .* for formula_id 'tower\.damage\.test'",
    ):
        kb_surfaces._canonical_formula_callables()


def test_runtime_formula_authority_is_sourced_directly_from_kb_mapping_table() -> None:
    authority_table_path = Path(__file__).resolve().parents[2] / 'kb' / 'global-rules' / 'tables' / 'runtime-formula-authority.csv'
    with authority_table_path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    expected: dict[str, dict[str, str]] = {}
    for row in rows:
        runtime_key = f"{row['source_domain'].strip()}:{row['stat_name'].strip()}"
        source = row['authority_source'].strip()
        formula_id = (row.get('formula_id') or '').strip()
        if source == 'canonical_formula_registry':
            expected[runtime_key] = {'authority_source': source, 'formula_id': formula_id}
        else:
            pytest.fail(f'{runtime_key} has unexpected authority source {source!r} in KB mapping table.')

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


def test_load_workshop_formulas_uses_canonical_registry_callables_for_canonical_runtime_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_authority_rows = kb_surfaces._load_runtime_formula_authority_rows()
    approved_exception_keys = {
        f'{domain}:{stat_name}'
        for (domain, stat_name), metadata in runtime_authority_rows.items()
        if metadata.get('authority_source') == 'approved_exception'
    }
    canonical_keys = {
        f'{domain}:{stat_name}'
        for (domain, stat_name), metadata in runtime_authority_rows.items()
        if metadata.get('authority_source') == 'canonical_formula_registry'
    }
    rows = kb_surfaces._read_csv(kb_surfaces._WORKSHOP_FORMULAS_PATH)
    canonical_only_rows = [
        row
        for row in rows
        if f"{row['source_domain'].strip()}:{row['stat_name'].strip().removesuffix(' (lab)')}" in canonical_keys
    ]

    canonical_callables = kb_surfaces._canonical_formula_callables()
    original_read_csv = kb_surfaces._read_csv

    def _read_csv_canonical_only(path: Path) -> list[dict]:
        if path == kb_surfaces._WORKSHOP_FORMULAS_PATH:
            return canonical_only_rows
        return original_read_csv(path)

    with monkeypatch.context() as canonical_context:
        canonical_context.setattr(
            kb_surfaces,
            '_build_formula',
            lambda formula_type, base, per_level, floor: (_ for _ in ()).throw(
                AssertionError('_build_formula should not be called for canonical runtime keys.')
            ),
        )
        canonical_context.setattr(kb_surfaces, '_read_csv', _read_csv_canonical_only)
        canonical_context.setattr(kb_surfaces, '_canonical_formula_callables', lambda: canonical_callables)

        workshop_formulas, lab_formulas = kb_surfaces.load_workshop_formulas()

    for runtime_key in canonical_keys:
        domain, stat_name = runtime_key.split(':', 1)
        runtime_callable = workshop_formulas[stat_name] if domain == 'workshop' else lab_formulas[stat_name]
        assert runtime_callable is canonical_callables[runtime_key]

    original_build_formula = kb_surfaces._build_formula
    approved_call_count = 0

    def _approved_only_build_formula(formula_type: str, base: float, per_level: float, floor: float):
        nonlocal approved_call_count
        approved_call_count += 1
        return original_build_formula(formula_type, base, per_level, floor)

    with monkeypatch.context() as approved_context:
        approved_context.setattr(kb_surfaces, '_build_formula', _approved_only_build_formula)
        kb_surfaces.load_workshop_formulas()

    assert approved_call_count == len(approved_exception_keys)


def test_load_workshop_formulas_canonical_rows_do_not_depend_on_fallback_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_authority_rows = kb_surfaces._load_runtime_formula_authority_rows()
    canonical_domain, canonical_stat_name = next(
        (domain, stat_name)
        for (domain, stat_name), metadata in runtime_authority_rows.items()
        if metadata.get('authority_source') == 'canonical_formula_registry'
    )

    original_read_csv = kb_surfaces._read_csv

    def _patched_read_csv(path: Path) -> list[dict]:
        rows = original_read_csv(path)
        if path != kb_surfaces._WORKSHOP_FORMULAS_PATH:
            return rows
        patched_rows: list[dict] = []
        for row in rows:
            patched = dict(row)
            if (
                patched.get('source_domain', '').strip() == canonical_domain
                and patched.get('stat_name', '').strip().removesuffix(' (lab)') == canonical_stat_name
            ):
                patched['formula_type'] = ''
                patched['base'] = ''
                patched['per_level'] = ''
                patched['floor'] = ''
            patched_rows.append(patched)
        return patched_rows

    monkeypatch.setattr(kb_surfaces, '_read_csv', _patched_read_csv)

    workshop_formulas, lab_formulas = kb_surfaces.load_workshop_formulas()
    runtime_key = f'{canonical_domain}:{canonical_stat_name}'
    canonical_callable = kb_surfaces._canonical_formula_callables()[runtime_key]
    runtime_callable = (
        workshop_formulas[canonical_stat_name]
        if canonical_domain == 'workshop'
        else lab_formulas[canonical_stat_name]
    )
    assert runtime_callable(1) == pytest.approx(canonical_callable(1))
    assert runtime_callable(99) == pytest.approx(canonical_callable(99))


def test_load_workshop_formulas_approved_exception_rows_require_legacy_formula_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_authority_rows = kb_surfaces._load_runtime_formula_authority_rows()
    approved_exceptions = [
        (domain, stat_name)
        for (domain, stat_name), metadata in runtime_authority_rows.items()
        if metadata.get('authority_source') == 'approved_exception'
    ]
    if not approved_exceptions:
        assert all(
            metadata.get('authority_source') == 'canonical_formula_registry'
            for metadata in runtime_authority_rows.values()
        )
        return
    exception_domain, exception_stat_name = approved_exceptions[0]

    original_read_csv = kb_surfaces._read_csv

    def _patched_read_csv(path: Path) -> list[dict]:
        rows = original_read_csv(path)
        if path != kb_surfaces._WORKSHOP_FORMULAS_PATH:
            return rows
        patched_rows: list[dict] = []
        for row in rows:
            patched = dict(row)
            if (
                patched.get('source_domain', '').strip() == exception_domain
                and patched.get('stat_name', '').strip().removesuffix(' (lab)') == exception_stat_name
            ):
                patched['formula_type'] = ''
            patched_rows.append(patched)
        return patched_rows

    monkeypatch.setattr(kb_surfaces, '_read_csv', _patched_read_csv)

    with pytest.raises(ValueError, match=f'{exception_domain}:{exception_stat_name}'):
        kb_surfaces.load_workshop_formulas()


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
        "second_wind_mastery_regen": False,
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


def test_dissonant_run_active_support_surfaces_are_contract_owned() -> None:
    support_surfaces = {
        "support_surface::dissonance.attack_run_active",
        "support_surface::dissonance.defense_run_active",
        "support_surface::dissonance.utility_run_active",
        "support_surface::dissonance.ultimate_weapons_run_active",
    }
    ownership = yaml.safe_load(
        (ROOT / "kb/global-rules/contracts/stat-query-surface-ownership-ledger.yaml").read_text(encoding="utf-8")
    )
    owned = {row["node_id"] for row in ownership["surface_nodes"]}
    assert support_surfaces <= owned
    assert "derived::edamage.defense_dissonance_shockwave_restricted" in owned

    initial_set = yaml.safe_load(
        (ROOT / "kb/global-rules/contracts/stat-query-initial-surface-set.yaml").read_text(encoding="utf-8")
    )
    derived_surfaces = {
        row["surface_id"]
        for row in initial_set["families"]["derived_v1"]["surfaces"]
    }
    assert support_surfaces <= derived_surfaces

    ledger = yaml.safe_load(
        (ROOT / "kb/global-rules/contracts/stat-query-dependency-invalidation-ledger.yaml").read_text(encoding="utf-8")
    )
    dependency_nodes = {row["node_id"] for row in ledger["nodes"]}
    assert support_surfaces <= dependency_nodes

    queryable = {
        row["surface_id"]: row
        for row in initial_set["families"]["derived_v1"]["surfaces"]
        if row["surface_id"] in support_surfaces
    }
    assert all(row["queryable_directly"] is False for row in queryable.values())
    assert all(row["consumer_only"] is True for row in queryable.values())
