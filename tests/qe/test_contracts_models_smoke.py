from __future__ import annotations

import csv
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
