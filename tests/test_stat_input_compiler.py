from __future__ import annotations

from pathlib import Path

from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs, compile_workshop_values_at_wave
from tower_sim.libs.workshop_lib import load_workshop_tables, workshop_value
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


def test_compile_full_stat_inputs_reports_uw_value_mismatch() -> None:
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

    assert "uw_value_mismatch:Golden Tower:Multiplier:1" in compiled.missing


def test_compile_full_stat_inputs_reports_unsupported_workshop_stat() -> None:
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

    assert "workshop_unsupported:Bounce Shot Range" in compiled.missing


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
    health_input = next(
        stat for stat in compiled.stat_inputs if stat.stat_id == "workshop_health"
    )
    assert health_input.enhancement_multiplier is not None
    assert health_input.enhancement_multiplier > 1.0
