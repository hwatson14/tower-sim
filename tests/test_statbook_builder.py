from __future__ import annotations

import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.util.account_snapshot import (  # noqa: E402
    AccountSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSystemState,
    PRESET_NAMES,
    SLOT_TYPES,
    TableSnapshot,
    WorkshopEntrySnapshot,
)
from tower_sim.engines.statbook_builder import build_statbook  # noqa: E402


def _snapshot_with_levels() -> AccountSnapshot:
    workshop_entries = {
        "Attack": WorkshopEntrySnapshot(
            name="Attack",
            unlocked=None,
            coin_level=3,
            end_level=3,
            max_level=7,
            category=None,
        ),
        "Defense": WorkshopEntrySnapshot(
            name="Defense",
            unlocked=None,
            coin_level=None,
            end_level=None,
            max_level=None,
            category=None,
        ),
    }
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
        labs={"LabA": 5, "LabB": None},
        workshop=workshop_entries,
        workshop_enhancements=TableSnapshot(header=[], rows=[]),
        ultimate_weapons={},
        relics={},
        vault={},
        bots=[],
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
        raw_sections={},
    )


def test_build_statbook_outputs_rows() -> None:
    snapshot = _snapshot_with_levels()
    statbook = build_statbook(snapshot)
    assert len(statbook.rows) == 8

    lab_start = next(row for row in statbook.rows if row.stat_id == "LabA" and row.phase == "start_of_run")
    assert lab_start.base_value == "5"
    assert lab_start.final_value == "5"

    lab_missing = next(row for row in statbook.rows if row.stat_id == "LabB" and row.phase == "start_of_run")
    assert lab_missing.base_value is None
    assert lab_missing.final_value is None

    workshop_end = next(row for row in statbook.rows if row.stat_id == "Attack" and row.phase == "end_of_run")
    assert workshop_end.final_value == "7"

    workshop_missing = next(row for row in statbook.rows if row.stat_id == "Defense" and row.phase == "end_of_run")
    assert workshop_missing.final_value is None
