from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders import account_snapshot_compiler as account_snapshot_compiler_module
from tower_sim.loaders.source_state_v2 import (
    SourceStateV2Error,
    normalize_source_state,
    required_source_state_families,
)
from tower_sim.util.account_snapshot import (
    AccountSnapshot,
    CardSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSnapshot,
    ModuleSubstat,
    ModuleSystemState,
    TableSnapshot,
    UltimateWeaponSnapshot,
    UwPlusTrackSnapshot,
    WorkshopEntrySnapshot,
)


def _snapshot() -> AccountSnapshot:
    return AccountSnapshot(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        labs={"Health": 10},
        workshop={
            "Health": WorkshopEntrySnapshot(
                name="Health",
                coin_level=25,
                end_level=25,
                max_level=5000,
                unlocked="Y",
                category="Defense",
            )
        },
        workshop_enhancements=TableSnapshot(header=["k"], rows=[["v"]]),
        ultimate_weapons={
            "Black Hole": UltimateWeaponSnapshot(name="Black Hole", unlocked="Y", track_levels=["1", "2"])
        },
        relics={"Health Relic": 0.1},
        vault={"Damage": 5},
        bots=["Flame Bot"],
        bot_upgrades={"Flame Bot": {"Damage": 3}},
        guardians=TableSnapshot(header=["a"], rows=[["b"]]),
        player_meta={"x": "y"},
        cards_inventory={"Damage": CardSnapshot(name="Damage", level=1, mastery_unlocked=False, mastery_lab_level=None)},
        card_presets={"Farming": ["Damage"], "Tourney": [], "Testing": [], "Preset 4": [], "Preset 5": []},
        module_system_state={
            "Cannon": ModuleSystemState(
                slot_type="Cannon",
                assist_unlocked=True,
                assist_level=1,
                rarity_cap="Epic",
                multiplier_cap=None,
                substat_cap=None,
            )
        },
        module_presets={
            "Farming": {"Cannon": ModulePresetSelection(primary=None, assist=None)},
            "Tourney": {"Cannon": ModulePresetSelection(primary=None, assist=None)},
            "Testing": {"Cannon": ModulePresetSelection(primary=None, assist=None)},
            "Preset 4": {"Cannon": ModulePresetSelection(primary=None, assist=None)},
            "Preset 5": {"Cannon": ModulePresetSelection(primary=None, assist=None)},
        },
        modules_inventory={
            "My Module": ModuleSnapshot(
                name="My Module",
                slot_type="Cannon",
                rarity="Epic",
                level=10,
                stat="Damage",
                substats=[ModuleSubstat(stat_name="Damage", rarity="Epic", value_display="1", value_num=1.0)],
            )
        },
        allocation_levels={"Cannon": ModuleAllocation(primary_level=1, assist_level=1)},
        inferred_shard_budgets={"Cannon": 0},
        default_preset="Farming",
        raw_sections={},
        uw_plus_tracks={
            "Black Hole::Consume": UwPlusTrackSnapshot(
                uw_name="Black Hole",
                plus_track_name="Consume",
                current_state="Locked",
                display_token="Lo | Locked",
            )
        },
    )


def test_required_source_state_family_presence() -> None:
    assert required_source_state_families() == (
        "workshop",
        "labs",
        "relics",
        "cards",
        "module_main",
        "module_sub",
        "module_unique",
        "ultimate_weapons",
        "uw_plus",
        "bots",
        "perks",
        "battle_conditions",
        "guardians",
        "vault",
        "enhancement",
    )


def test_runtime_static_separation_in_adapters() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    forbidden = {"wave", "wave_attack_index", "wave_health_index", "combat_state", "boss_state"}
    assert not any(record.source_state_field in forbidden for record in result.records)


def test_provenance_preservation() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    assert result.records
    assert all(record.provenance for record in result.records)


def test_adapters_do_not_emit_canonical_target_stats_directly() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    canonical_target_like = {"health", "damage", "wall_health", "defense_pct"}
    assert not any(record.source_state_field in canonical_target_like for record in result.records)


def test_adapters_do_not_emit_fabricated_contributor_ids() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    assert not any(
        record.source_state_field.startswith(("legacy_stage__", "resolved__", "helper__"))
        for record in result.records
    )


def test_adapter_rejects_runtime_field_identifier() -> None:
    from tower_sim.loaders import source_state_v2 as module

    with pytest.raises(SourceStateV2Error, match="runtime_field_not_allowed_in_source_state"):
        module._validate_source_state_identifier("wave_attack_index", contract=module.load_static_v2_contract())


def test_uw_plus_source_state_records_are_emitted_from_typed_snapshot_surface() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    uw_plus_records = [record for record in result.records if record.family == "uw_plus"]
    assert uw_plus_records
    assert any("black_hole_consume" in record.source_state_field for record in uw_plus_records)


def test_uw_plus_family_is_marked_implemented_in_coverage() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    rows = [row for row in result.coverage if row.family == "uw_plus"]
    assert len(rows) == 1
    assert rows[0].adapter_implemented is True
    assert rows[0].blocked_or_deferred is False


def test_account_snapshot_compiler_exposes_typed_uw_plus_row4_surface() -> None:
    rows = [
        ["Black Hole", "", "Size", "48", "09 | 48m | Cost 76 ? | Next 89 ?"],
        ["", "", "Duration", "32", "17 | 32s | Cost 224 ? | Next 308 ?"],
        ["true", "UW Unlocked", "Cooldown", "50", "15 | 50s | Cost 262 ? | Maxed"],
        ["UW+", "", "Consume", "Locked", "Lo | Locked"],
    ]
    tracks = account_snapshot_compiler_module._parse_uw_plus_tracks(rows)
    assert tracks
    sample = next(iter(tracks.values()))
    assert sample.uw_name == "Black Hole"
    assert sample.plus_track_name == "Consume"



def test_perks_and_battle_conditions_source_records_are_emitted() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    families = {record.family for record in result.records}
    assert "perks" in families
    assert "battle_conditions" in families
    assert any(record.provenance.startswith("table:tables/inputs/perks/") for record in result.records if record.family == "perks")
    assert any(record.provenance.startswith("table:tables/inputs/combat/") for record in result.records if record.family == "battle_conditions")


def test_perks_and_battle_conditions_are_marked_implemented_in_coverage() -> None:
    snapshot = _snapshot()
    result = normalize_source_state(snapshot)
    rows = {row.family: row for row in result.coverage}
    assert rows["perks"].adapter_implemented is True
    assert rows["perks"].blocked_or_deferred is False
    assert rows["battle_conditions"].adapter_implemented is True
    assert rows["battle_conditions"].blocked_or_deferred is False
