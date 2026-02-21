from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs, compile_workshop_values_at_wave
from tower_sim.libs.workshop_lib import load_workshop_tables, workshop_value
from tower_sim.loaders.wiki.enemy_level_skip import workshop_level_to_chance
from tower_sim.util.account_snapshot import (
    AccountSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSystemState,
    PRESET_NAMES,
    SLOT_TYPES,
    TableSnapshot,
    WorkshopEntrySnapshot,
)


def _snapshot_with_workshop_and_uw(
    *,
    workshop_entries: dict[str, WorkshopEntrySnapshot],
    uw_rows: list[list[str]],
) -> AccountSnapshot:
    module_presets = {
        preset: {
            slot: ModulePresetSelection(primary=None, assist=None)
            for slot in SLOT_TYPES
        }
        for preset in PRESET_NAMES
    }
    module_system_state = {
        slot: ModuleSystemState(
            slot_type=slot,
            assist_unlocked=False,
            assist_level=0,
            rarity_cap=None,
            multiplier_cap=None,
            substat_cap=None,
        )
        for slot in SLOT_TYPES
    }
    allocation_levels = {
        slot: ModuleAllocation(primary_level=0, assist_level=0) for slot in SLOT_TYPES
    }
    inferred_shards = {slot: 0 for slot in SLOT_TYPES}
    return AccountSnapshot(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        labs={},
        workshop=workshop_entries,
        workshop_enhancements=TableSnapshot(
            header=["Workshop Enhancement", "", "Farming"],
            rows=[["Damage +", "1.56", "56"]],
        ),
        ultimate_weapons={},
        relics={},
        vault={},
        bots=[],
        bot_upgrades={},
        guardians=TableSnapshot(header=[], rows=[]),
        player_meta={},
        cards_inventory={},
        card_presets={},
        module_system_state=module_system_state,
        module_presets=module_presets,
        modules_inventory={},
        allocation_levels=allocation_levels,
        inferred_shard_budgets=inferred_shards,
        default_preset="Farming",
        raw_sections={"UWs": uw_rows},
    )


def test_compile_full_stat_inputs_includes_workshop_and_uw() -> None:
    workshop_entries = {
        "Damage": WorkshopEntrySnapshot(
            name="Damage",
            unlocked=None,
            coin_level=1,
            end_level=1,
            max_level=1,
            category=None,
        )
    }
    uw_rows = [
        ["Golden Tower", "", "Multiplier", "1", "01 | x1 | Cost 5 ? | Next 13 ?"],
    ]
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=uw_rows,
    )

    compiled = compile_full_stat_inputs(snapshot)

    tables = load_workshop_tables()
    expected_damage = float(workshop_value("Damage", 1, tables, section="WSValues"))

    value = 1.0
    next_cost = 13.0

    damage_input = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_damage"
    )
    assert damage_input.base_value == expected_damage
    assert damage_input.enhancement_multiplier == 1.56

    uw_input = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "uw_golden_tower_multiplier"
    )
    assert uw_input.base_value == value

    uw_cost_input = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "uw_golden_tower_multiplier_next_cost"
    )
    assert uw_cost_input.base_value == next_cost


def test_compile_full_stat_inputs_prefers_ids_uw_track_value() -> None:
    workshop_entries = {
        "Damage": WorkshopEntrySnapshot(
            name="Damage",
            unlocked=None,
            coin_level=1,
            end_level=1,
            max_level=1,
            category=None,
        )
    }
    uw_rows = [
        ["Golden Tower", "", "Multiplier", "5.8", "01 | x5.8 | Cost 5 ? | Next 13 ?"],
    ]
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=uw_rows,
    )

    compiled = compile_full_stat_inputs(snapshot)

    assert "uw_value_mismatch:Golden Tower:Multiplier:1" not in compiled.missing
    uw_input = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "uw_golden_tower_multiplier"
    )
    assert uw_input.base_value == 5.8


def test_compile_full_stat_inputs_compiles_bounce_shot_range_formula() -> None:
    workshop_entries = {
        "Bounce Shot Range": WorkshopEntrySnapshot(
            name="Bounce Shot Range",
            unlocked=None,
            coin_level=1,
            end_level=1,
            max_level=1,
            category=None,
        )
    }
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=[],
    )

    compiled = compile_full_stat_inputs(snapshot)

    assert "workshop_unsupported:Bounce Shot Range" not in compiled.missing
    bounce = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_bounce_shot_range"
    )
    assert bounce.base_value == 2.1


def test_compile_full_stat_inputs_aliases_max_amount_to_max_recovery() -> None:
    workshop_entries = {
        "Max Amount": WorkshopEntrySnapshot(
            name="Max Amount",
            unlocked=None,
            coin_level=500,
            end_level=500,
            max_level=500,
            category=None,
        )
    }
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=[],
    )

    compiled = compile_full_stat_inputs(snapshot)

    assert "workshop_unsupported:Max Amount" not in compiled.missing
    max_recovery = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_max_recovery"
    )
    assert max_recovery.base_value == 16.5


def test_compile_full_stat_inputs_rejects_attack_speed_above_workshop_cap() -> None:
    workshop_entries = {
        "Attack Speed": WorkshopEntrySnapshot(
            name="Attack Speed",
            unlocked=None,
            coin_level=100,
            end_level=100,
            max_level=100,
            category=None,
        )
    }
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=[],
    )

    compiled = compile_full_stat_inputs(snapshot)

    assert "workshop_unsupported:Attack Speed" in compiled.missing






def test_enemy_level_skip_level_zero_semantics_are_explicit() -> None:
    # IDS uses level 0 for unpurchased workshop; skip chance is 0%.
    assert workshop_level_to_chance(0) == pytest.approx(0.0)

    workshop_entries = {
        "Enemy Attack Level Skip": WorkshopEntrySnapshot(
            name="Enemy Attack Level Skip",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=699,
            category="Utility",
        ),
        "Enemy Health Level Skip": WorkshopEntrySnapshot(
            name="Enemy Health Level Skip",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=699,
            category="Utility",
        ),
    }
    snapshot = _snapshot_with_workshop_and_uw(workshop_entries=workshop_entries, uw_rows=[])

    compiled = compile_full_stat_inputs(snapshot)
    attack = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_enemy_attack_level_skip"
    )
    health = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_enemy_health_level_skip"
    )

    assert attack.base_value == pytest.approx(0.0)
    assert health.base_value == pytest.approx(0.0)

def test_enemy_level_skip_workshop_scaling_matches_wiki_points() -> None:
    table_points = {
        1: 0.0005,
        10: 0.0050,
        100: 0.0500,
        699: 0.3495,
    }
    for level, expected in table_points.items():
        workshop_entries = {
            "Enemy Attack Level Skip": WorkshopEntrySnapshot(
                name="Enemy Attack Level Skip",
                unlocked=None,
                coin_level=level,
                end_level=level,
                max_level=699,
                category="Utility",
            ),
            "Enemy Health Level Skip": WorkshopEntrySnapshot(
                name="Enemy Health Level Skip",
                unlocked=None,
                coin_level=level,
                end_level=level,
                max_level=699,
                category="Utility",
            ),
        }
        snapshot = _snapshot_with_workshop_and_uw(workshop_entries=workshop_entries, uw_rows=[])

        compiled = compile_full_stat_inputs(snapshot)

        attack = next(
            stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_enemy_attack_level_skip"
        )
        health = next(
            stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_enemy_health_level_skip"
        )
        assert attack.base_value == pytest.approx(expected)
        assert health.base_value == pytest.approx(expected)

def test_compile_workshop_values_at_wave_progresses_damage_deterministically() -> None:
    workshop_entries = {
        "Damage": WorkshopEntrySnapshot(
            name="Damage",
            unlocked=None,
            coin_level=1,
            end_level=5,
            max_level=5,
            category="Attack",
        ),
        "Free Attack Upgrade": WorkshopEntrySnapshot(
            name="Free Attack Upgrade",
            unlocked=None,
            coin_level=99,
            end_level=99,
            max_level=99,
            category="Utility",
        ),
        "Free Defense Upgrade": WorkshopEntrySnapshot(
            name="Free Defense Upgrade",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=99,
            category="Utility",
        ),
        "Free Utility Upgrade": WorkshopEntrySnapshot(
            name="Free Utility Upgrade",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=99,
            category="Utility",
        ),
    }
    snapshot = _snapshot_with_workshop_and_uw(workshop_entries=workshop_entries, uw_rows=[])

    at_wave_values, missing = compile_workshop_values_at_wave(snapshot, wave=4)

    assert missing == []
    assert "workshop_damage" in at_wave_values

    tables = load_workshop_tables()
    start_damage = float(workshop_value("Damage", 1, tables, section="WSValues"))
    assert at_wave_values["workshop_damage"] > start_damage


def test_compile_workshop_values_at_wave_emits_canonical_survivability_ids(monkeypatch) -> None:
    workshop_entries = {
        "Health": WorkshopEntrySnapshot(
            name="Health",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Health Regen": WorkshopEntrySnapshot(
            name="Health Regen",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Wall Health": WorkshopEntrySnapshot(
            name="Wall Health",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Wall Regen": WorkshopEntrySnapshot(
            name="Wall Regen",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Free Attack Upgrade": WorkshopEntrySnapshot(
            name="Free Attack Upgrade",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=99,
            category="Utility",
        ),
        "Free Defense Upgrade": WorkshopEntrySnapshot(
            name="Free Defense Upgrade",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=99,
            category="Utility",
        ),
        "Free Utility Upgrade": WorkshopEntrySnapshot(
            name="Free Utility Upgrade",
            unlocked=None,
            coin_level=0,
            end_level=0,
            max_level=99,
            category="Utility",
        ),
    }
    snapshot = _snapshot_with_workshop_and_uw(workshop_entries=workshop_entries, uw_rows=[])

    from tower_sim.engines import stat_input_compiler as compiler

    real_resolve = compiler._resolve_workshop_value

    def _patched_resolve(tables, spec, *, level):
        if spec.stat_id == "workshop_wall_regen":
            return 0.2
        return real_resolve(tables, spec, level=level)

    monkeypatch.setattr(compiler, "_resolve_workshop_value", _patched_resolve)

    at_wave_values, missing = compile_workshop_values_at_wave(snapshot, wave=1)

    assert missing == []
    assert at_wave_values["tower_hp"] == pytest.approx(at_wave_values["workshop_health"])
    assert at_wave_values["tower_regen"] == pytest.approx(at_wave_values["workshop_health_regen"])
    assert at_wave_values["wall_hp"] == pytest.approx(
        at_wave_values["tower_hp"] * at_wave_values["workshop_wall_health"]
    )
    assert at_wave_values["wall_regen"] == pytest.approx(
        at_wave_values["tower_regen"] * at_wave_values["workshop_wall_regen"]
    )


def test_compile_full_stat_inputs_wall_regen_alias_uses_workshop_ratio_without_lab(monkeypatch) -> None:
    workshop_entries = {
        "Health": WorkshopEntrySnapshot(
            name="Health",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Health Regen": WorkshopEntrySnapshot(
            name="Health Regen",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Wall Health": WorkshopEntrySnapshot(
            name="Wall Health",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
        "Wall Regen": WorkshopEntrySnapshot(
            name="Wall Regen",
            unlocked=None,
            coin_level=10,
            end_level=10,
            max_level=10,
            category="Defense",
        ),
    }
    snapshot = _snapshot_with_workshop_and_uw(workshop_entries=workshop_entries, uw_rows=[])

    from tower_sim.engines import stat_input_compiler as compiler

    real_resolve = compiler._resolve_workshop_value

    def _patched_resolve(tables, spec, *, level):
        if spec.stat_id == "workshop_wall_regen":
            return 0.2
        return real_resolve(tables, spec, level=level)

    monkeypatch.setattr(compiler, "_resolve_workshop_value", _patched_resolve)

    compiled = compile_full_stat_inputs(snapshot)

    by_id = {item.stat_id: item for item in compiled.stat_inputs}
    assert by_id["wall_regen"].base_value == pytest.approx(
        by_id["tower_regen"].base_value * by_id["workshop_wall_regen"].base_value
    )


def test_compile_full_stat_inputs_applies_health_lab_multiplier() -> None:
    workshop_entries = {
        "Health": WorkshopEntrySnapshot(
            name="Health",
            unlocked=None,
            coin_level=1,
            end_level=1,
            max_level=1,
            category=None,
        )
    }
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries=workshop_entries,
        uw_rows=[],
    )
    snapshot = AccountSnapshot(
        **{
            **snapshot.__dict__,
            "labs": {"Health": 1},
        }
    )

    compiled = compile_full_stat_inputs(snapshot)
    health_input = next(stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_health")
    tower_hp_alias = next(stat for stat in compiled.stat_inputs if stat.stat_id == "tower_hp")
    assert health_input.enhancement_multiplier is not None
    assert health_input.enhancement_multiplier > 1.0
    assert tower_hp_alias.enhancement_multiplier == health_input.enhancement_multiplier
    assert tower_hp_alias.provenance == "workshop_alias:Health->tower_hp"


def test_compile_full_stat_inputs_emits_canonical_survivability_aliases() -> None:
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries={
            "Health": WorkshopEntrySnapshot(name="Health", coin_level=1, end_level=1, max_level=6000, unlocked=None, category=None),
            "Health Regen": WorkshopEntrySnapshot(name="Health Regen", coin_level=1, end_level=1, max_level=6000, unlocked=None, category=None),
            "Defense %": WorkshopEntrySnapshot(name="Defense %", coin_level=1, end_level=1, max_level=99, unlocked=None, category=None),
            "Wall Health": WorkshopEntrySnapshot(name="Wall Health", coin_level=1, end_level=1, max_level=1800, unlocked=None, category=None),
            "Wall Regen": WorkshopEntrySnapshot(name="Wall Regen", coin_level=1, end_level=1, max_level=1800, unlocked=None, category=None),
            "Thorn Damage": WorkshopEntrySnapshot(name="Thorn Damage", coin_level=1, end_level=1, max_level=99, unlocked=None, category=None),
            "Enemy Attack Level Skip": WorkshopEntrySnapshot(name="Enemy Attack Level Skip", coin_level=1, end_level=1, max_level=99, unlocked=None, category=None),
            "Enemy Health Level Skip": WorkshopEntrySnapshot(name="Enemy Health Level Skip", coin_level=1, end_level=1, max_level=99, unlocked=None, category=None),
        },
        uw_rows=[],
    )

    compiled = compile_full_stat_inputs(snapshot)
    by_id = {item.stat_id: item for item in compiled.stat_inputs}

    for stat_id in (
        "tower_hp",
        "tower_regen",
        "def_pct",
        "wall_hp",
        "wall_regen",
        "thorns_damage_mult",
        "eals_pct",
        "ehls_pct",
    ):
        assert stat_id in by_id
        assert by_id[stat_id].base_value is not None


def test_compile_full_stat_inputs_wall_aliases_use_resolved_values_not_raw_levels() -> None:
    snapshot = _snapshot_with_workshop_and_uw(
        workshop_entries={
            "Health": WorkshopEntrySnapshot(name="Health", coin_level=100, end_level=100, max_level=6000, unlocked=None, category=None),
            "Health Regen": WorkshopEntrySnapshot(name="Health Regen", coin_level=100, end_level=100, max_level=6000, unlocked=None, category=None),
            "Wall Health": WorkshopEntrySnapshot(name="Wall Health", coin_level=100, end_level=100, max_level=1800, unlocked=None, category=None),
            "Wall Regen": WorkshopEntrySnapshot(name="Wall Regen", coin_level=100, end_level=100, max_level=1800, unlocked=None, category=None),
        },
        uw_rows=[],
    )
    snapshot = AccountSnapshot(
        **{
            **snapshot.__dict__,
            "workshop_enhancements": TableSnapshot(
                header=["Workshop Enhancement", "", "Farming"],
                rows=[
                    ["Health +", "3.0", "200"],
                    ["Wall Health +", "2.0", "100"],
                ],
            ),
        }
    )

    compiled = compile_full_stat_inputs(snapshot)
    by_id = {item.stat_id: item for item in compiled.stat_inputs}

    tower_hp = by_id["tower_hp"]
    wall_hp = by_id["wall_hp"]
    resolved_tower_hp = float(tower_hp.base_value or 0.0) * float(
        tower_hp.enhancement_multiplier or 1.0
    )
    resolved_wall_ratio = float(by_id["workshop_wall_health"].base_value or 0.0) * float(
        by_id["workshop_wall_health"].enhancement_multiplier or 1.0
    )

    assert wall_hp.base_value == pytest.approx(
        resolved_tower_hp * resolved_wall_ratio,
        rel=1e-12,
    )


def test_compile_full_stat_inputs_includes_relic_modifiers() -> None:
    snapshot = _snapshot_with_workshop_and_uw(workshop_entries={}, uw_rows=[])
    snapshot = AccountSnapshot(
        **{
            **snapshot.__dict__,
            "relics": {
                "Health": 0.39,
                "Health Regen": 0.21,
                "Defense %": 0.04,
                "Enemy Attack Level Skip": 0.02,
                "Enemy Health Level Skip": 0.02,
            },
        }
    )

    compiled = compile_full_stat_inputs(snapshot)
    by_id = {item.stat_id: item for item in compiled.stat_inputs}

    assert by_id["tower_hp"].enhancement_multiplier == pytest.approx(1.39, rel=1e-12)
    assert by_id["tower_regen"].enhancement_multiplier == pytest.approx(1.21, rel=1e-12)
    assert by_id["def_pct"].loadout_delta == 0.04
    assert by_id["eals_pct"].loadout_delta == 0.02
    assert by_id["ehls_pct"].loadout_delta == 0.02
