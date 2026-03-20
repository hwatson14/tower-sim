from pathlib import Path

import pytest

import v3.stat_input_compiler as v3_compiler
from tower_sim.engines.stat_input_compiler import CompiledStatInputs
from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from v3.stat_input_compiler import (
    V3StatInputCompilerError,
    compile_v3_baseline_loadout_stat_inputs,
    compile_v3_stat_inputs,
    validate_compiled_stat_inputs,
    noncanonical_policy_contract,
)

_IDS_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _snapshot():
    return compile_account_snapshot(parse_ids(_IDS_FIXTURE))


def test_compile_v3_stat_inputs_baseline_gem_respec_smoke() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="baseline_gem_respec")
    assert compiled.stat_inputs
    assert all(item.contributor_family for item in compiled.stat_inputs)


def test_compile_v3_loadout_inputs_smoke() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(
        _snapshot(), module_context="Farming"
    )
    assert compiled.stat_inputs
    assert all(item.contributor_family for item in compiled.stat_inputs)


def test_compile_v3_stat_inputs_full_smoke() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert compiled.stat_inputs
    assert all(item.contributor_family for item in compiled.stat_inputs)


def test_validate_compiled_stat_inputs_rejects_ambiguous_provenance_prefix() -> None:
    bad = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance=" :bad",
            contributor_family=None,
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="ambiguous_provenance_prefix"):
        validate_compiled_stat_inputs(bad)


def test_validate_compiled_stat_inputs_rejects_bad_stat_id() -> None:
    bad = [
        StatInput(
            stat_id="BadStat",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="ids:test",
            contributor_family="workshop",
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="stat_id_not_snake_case"):
        validate_compiled_stat_inputs(bad)


def test_validate_compiled_stat_inputs_rejects_missing_contributor_family() -> None:
    bad = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="workshop_table:Health",
            contributor_family=None,
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="missing_contributor_family"):
        validate_compiled_stat_inputs(bad)


def test_compile_v3_stat_inputs_full_filters_legacy_lab_unmapped_diagnostics() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert all(not item.startswith("lab_table_unmapped:") for item in compiled.missing)


def test_compile_v3_loadout_filters_legacy_lab_unmapped_diagnostics() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(_snapshot(), module_context="Farming")
    assert all(not item.startswith("lab_table_unmapped:") for item in compiled.missing)


def test_compile_v3_loadout_maps_knockback_force_substat() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(_snapshot(), module_context="Farming")
    assert all("Knockback Force" not in gap for gap in compiled.layer_gaps)


def test_compile_v3_loadout_emits_composite_knockback_force_stat() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(_snapshot(), module_context="Farming")
    module_rows = [
        item for item in compiled.stat_inputs if (item.provenance or "").startswith("modules:")
    ]
    assert any(item.stat_id == "tower_knockback_force" for item in module_rows)
    assert all(not item.startswith("kb_unwired:module:tower_knockback_force") for item in compiled.missing)


def test_compile_v3_stat_inputs_full_tracks_noncanonical_drops_separately() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert compiled.dropped_noncanonical
    assert all(item.startswith("noncanonical_stat_surface:") for item in compiled.dropped_noncanonical)
    assert all(not item.startswith("noncanonical_stat_surface:") for item in compiled.missing)


def test_compile_v3_loadout_tracks_noncanonical_drops_separately() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(_snapshot(), module_context="Farming")
    assert compiled.dropped_noncanonical
    assert all(item.startswith("noncanonical_stat_surface:") for item in compiled.dropped_noncanonical)
    assert all(not item.startswith("noncanonical_stat_surface:") for item in compiled.missing)


def test_compile_v3_stat_inputs_full_routes_wall_regen_composite_to_lab_family() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    wall_regen_rows = [item for item in compiled.stat_inputs if item.stat_id == "wall_regen"]
    assert wall_regen_rows
    assert all(item.contributor_family == "lab" for item in wall_regen_rows)
    assert all(not item.startswith("kb_unwired:workshop:wall_regen") for item in compiled.missing)


def test_compile_v3_loadout_has_no_module_kb_unwired_for_modeled_substats() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(_snapshot(), module_context="Farming")
    assert all(not item.startswith("kb_unwired:module:tower_attack_speed") for item in compiled.missing)
    assert all(not item.startswith("kb_unwired:module:tower_crit_multiplier") for item in compiled.missing)
    assert all(not item.startswith("kb_unwired:module:tower_knockback_force") for item in compiled.missing)
    assert all(not item.startswith("kb_unwired:module:tower_regen") for item in compiled.missing)


def test_compile_v3_stat_inputs_rejects_noncanonical_surface_for_canonical_only_family(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="black_hole_cooldown",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="workshop_table:Bad Noncanonical",
                    contributor_family="workshop",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)

    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_kb"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_promotes_legacy_workshop_table_noncanonical_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="workshop_damage",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="workshop_table:Damage",
                    contributor_family="workshop",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert [item.stat_id for item in compiled.stat_inputs] == ["tower_damage"]
    assert compiled.dropped_noncanonical == []


def test_compile_v3_stat_inputs_promotes_workshop_alias_noncanonical_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="workshop_damage",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="workshop_alias:Damage->workshop_damage",
                    contributor_family="workshop",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert [item.stat_id for item in compiled.stat_inputs] == ["tower_damage"]
    assert compiled.dropped_noncanonical == []


def test_validate_compiled_stat_inputs_rejects_unknown_family_not_in_kb() -> None:
    bad = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="workshop_table:Health",
            contributor_family="mystery_family",
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="unknown_contributor_family_not_in_kb"):
        validate_compiled_stat_inputs(bad)


def test_compile_v3_stat_inputs_known_family_without_canonical_route_is_kb_unwired(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="tower_hp",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="bot_table:Amp Bonus",
                    contributor_family="bot_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert compiled.stat_inputs == []
    assert compiled.dropped_kb_unwired == ["kb_unwired:bot_upgrade:tower_hp"]


def test_compile_v3_stat_inputs_allows_kb_noncanonical_family_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_amplify_bonus",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="bot_table:Amp Bonus",
                    contributor_family="bot_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    assert compiled.stat_inputs == []
    assert compiled.dropped_noncanonical == ["noncanonical_stat_surface:bot_upgrade:bot_table:bot_amplify_bonus"]


def test_compile_v3_stat_inputs_rejects_noncanonical_family_without_explicit_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_amplify_bonus",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="relics:Bad Surface",
                    contributor_family="relic",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_policy"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_rejects_enhancements_noncanonical_by_zero_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_amplify_bonus",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="enhancements:Bad Surface",
                    contributor_family="enhancements",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_policy"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_rejects_kb_noncanonical_family_outside_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="uw_black_hole_cooldown",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="bot_table:Bad Surface",
                    contributor_family="bot_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_policy"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_rejects_bot_noncanonical_not_in_policy_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = dict(v3_compiler._NONCANONICAL_OUT_OF_SCOPE_POLICY)
    policy["bot_upgrade"] = {
        **policy["bot_upgrade"],
        "allowed_stat_ids": {"bot_amplify_bonus"},
    }
    monkeypatch.setattr(v3_compiler, "_NONCANONICAL_OUT_OF_SCOPE_POLICY", policy)

    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_flame_damage",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="bot_table:New Surface",
                    contributor_family="bot_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_policy"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_rejects_uw_noncanonical_not_in_policy_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = dict(v3_compiler._NONCANONICAL_OUT_OF_SCOPE_POLICY)
    policy["uw_upgrade"] = {
        **policy["uw_upgrade"],
        "allowed_stat_ids": {"uw_black_hole_cooldown"},
    }
    monkeypatch.setattr(v3_compiler, "_NONCANONICAL_OUT_OF_SCOPE_POLICY", policy)

    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="uw_black_hole_duration",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="uw_section:Unknown Surface",
                    contributor_family="uw_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_policy"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_rejects_unlock_noncanonical_not_in_compat_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_amplify_bonus",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="base:unknown",
                    contributor_family="unlock",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)
    with pytest.raises(V3StatInputCompilerError, match="noncanonical_surface_not_allowed_by_kb"):
        compile_v3_stat_inputs(_snapshot(), stage="full")


def test_compile_v3_stat_inputs_promotes_relic_legacy_aliases_to_canonical() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="full")
    relic_rows = [item for item in compiled.stat_inputs if (item.provenance or "").startswith("relics:")]
    relic_stats = {item.stat_id for item in relic_rows}
    assert "cash_kill_multiplier" in relic_stats
    assert "coin_kill_multiplier" in relic_stats
    assert "tower_damage_per_meter_multiplier" in relic_stats
    assert "tower_defense_pct" in relic_stats
    assert "tower_defense_absolute" in relic_stats
    assert "enemy_attack_level_skip_pct" in relic_stats
    assert "enemy_health_level_skip_pct" in relic_stats
    assert "free_attack_upgrade_chance_pct" in relic_stats
    assert "free_defense_upgrade_chance_pct" in relic_stats
    assert "free_utility_upgrade_chance_pct" in relic_stats
    assert "tower_orb_speed_rpm" in relic_stats
    assert "lab_speed_multiplier" in relic_stats
    assert "tower_supercrit_chance_pct" in relic_stats
    assert "tower_supercrit_multiplier" in relic_stats
    assert "tower_thorns_damage_pct" in relic_stats
    assert "recovery_amount_pct" in relic_stats
    assert "tower_crit_chance_pct" in relic_stats
    assert "ultimate_damage_multiplier" in relic_stats
    assert "wall_rebuild_seconds" in relic_stats

    dropped_stats = {item.split(":")[-1] for item in compiled.dropped_noncanonical}
    assert "cash_bonus" not in dropped_stats
    assert "coins_bonus" not in dropped_stats
    assert "damage_per_meter" not in dropped_stats
    assert "def_pct" not in dropped_stats
    assert "defense_absolute" not in dropped_stats
    assert "eals_pct" not in dropped_stats
    assert "ehls_pct" not in dropped_stats
    assert "free_attack_upgrade" not in dropped_stats
    assert "free_defense_upgrade" not in dropped_stats
    assert "free_utility_upgrade" not in dropped_stats
    assert "orb_speed" not in dropped_stats
    assert "lab_speed" not in dropped_stats
    assert "super_crit_chance" not in dropped_stats
    assert "super_crit_mult" not in dropped_stats
    assert "thorns_damage_mult" not in dropped_stats
    assert "recovery_amount" not in dropped_stats
    assert "tower_crit_chance" not in dropped_stats
    assert "ultimate_damage" not in dropped_stats
    assert "wall_rebuild" not in dropped_stats
    assert "workshop_damage" not in dropped_stats
    assert "workshop_health" not in dropped_stats
    assert "workshop_orbs" not in dropped_stats
    assert "black_hole_cooldown" not in dropped_stats
    assert "chain_lightning_damage" not in dropped_stats
    assert "chrono_field_duration" not in dropped_stats
    assert "death_wave_damage" not in dropped_stats
    assert "golden_tower_multiplier" not in dropped_stats
    assert "inner_land_mines_damage" not in dropped_stats
    assert "poison_swamp_damage" not in dropped_stats
    assert "smart_missiles_damage" not in dropped_stats
    assert "spotlight_multiplier" not in dropped_stats


def test_validate_compiled_stat_inputs_rejects_provenance_family_mismatch() -> None:
    bad = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="workshop_table:Health",
            contributor_family="relic",
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="provenance_family_mismatch"):
        validate_compiled_stat_inputs(bad)


def test_validate_compiled_stat_inputs_allows_wall_regen_composite_exception() -> None:
    row = [
        StatInput(
            stat_id="wall_regen",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="workshop_alias:Wall Regen->wall_regen",
            contributor_family="lab",
        )
    ]
    validate_compiled_stat_inputs(row)


def test_noncanonical_policy_contract_exposes_expected_prefixes_and_unlock_allowlist() -> None:
    contract = noncanonical_policy_contract()
    assert set(contract["allowed_stat_prefixes"]) == {"bot_", "uw_"}
    assert set(contract["allowed_unlock_stat_ids"]) == {
        "death_ray_damage_mult",
        "knockback_mult",
        "orb_damage_mult",
        "plasma_cannon_damage_mult",
    }
    families = contract["families"]
    assert {"unlock", "bot_upgrade", "uw_upgrade", "relic", "card", "module", "enhancements", "vault", "guardian_upgrade", "theme_song", "player_stuff"}.issubset(set(families))
    assert "bot_range" in families["relic"]["allowed_stat_ids"]
    assert "plasma_cannon_damage_mult" in families["card"]["allowed_stat_ids"]
    assert "uw_smart_missiles_damage" in families["module"]["allowed_stat_ids"]
    assert families["enhancements"]["allowed_stat_ids"] == []
    assert families["vault"]["allowed_stat_ids"] == []
    assert contract["coverage_complete"] is True
    assert contract["missing_kb_policy_families"] == []


def test_compile_v3_stat_inputs_fails_if_kb_noncanonical_family_lacks_explicit_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile_full_stat_inputs(_snapshot_obj):
        return CompiledStatInputs(
            stat_inputs=[
                StatInput(
                    stat_id="bot_amplify_bonus",
                    phase=Phase.START_OF_RUN,
                    base_value=1.0,
                    provenance="bot_table:Amp Bonus",
                    contributor_family="bot_upgrade",
                )
            ],
            missing=[],
        )

    monkeypatch.setattr(v3_compiler, "compile_full_stat_inputs", _fake_compile_full_stat_inputs)

    original_policy = dict(v3_compiler._NONCANONICAL_OUT_OF_SCOPE_POLICY)
    modified_policy = dict(original_policy)
    modified_policy.pop("bot_upgrade", None)
    monkeypatch.setattr(v3_compiler, "_NONCANONICAL_OUT_OF_SCOPE_POLICY", modified_policy)

    with pytest.raises(V3StatInputCompilerError, match="noncanonical_policy_missing_for_noncanonical_families"):
        compile_v3_stat_inputs(_snapshot(), stage="full")
