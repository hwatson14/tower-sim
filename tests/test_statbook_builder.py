from __future__ import annotations

import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.engines.statbook_builder import build_statbook  # noqa: E402
from tower_sim.util.account_snapshot import (  # noqa: E402
    AccountSnapshot,
    ModuleAllocation,
    ModulePresetSelection,
    ModuleSystemState,
    TableSnapshot,
    UltimateWeaponSnapshot,
    WorkshopEntrySnapshot,
)


def _snapshot_with_levels() -> AccountSnapshot:
    module_system_state = {
        "Armor": ModuleSystemState(
            slot_type="Armor",
            assist_unlocked=True,
            assist_level=1,
            rarity_cap=None,
            multiplier_cap=None,
            substat_cap=None,
        )
    }
    module_presets = {
        "Farming": {
            "Armor": ModulePresetSelection(primary=None, assist=None),
        }
    }
    allocation_levels = {
        "Armor": ModuleAllocation(primary_level=1, assist_level=1),
    }
    inferred_shards = {"Armor": 0}
    return AccountSnapshot(
        ids_path=Path("dummy.csv"),
        labs={"LabA": 5, "LabB": None},
        workshop={
            "Health": WorkshopEntrySnapshot(
                name="Health",
                coin_level=10,
                end_level=10,
                max_level=10,
                unlocked=None,
                category=None,
            ),
            "Health Regen": WorkshopEntrySnapshot(
                name="Health Regen",
                coin_level=7,
                end_level=7,
                max_level=7,
                unlocked=None,
                category=None,
            ),
        },
        workshop_enhancements=TableSnapshot(header=[], rows=[]),
        ultimate_weapons={
            "Chain Lightning": UltimateWeaponSnapshot(
                name="Chain Lightning",
                unlocked="true",
                track_levels=["5", "5", "5", "5"],
            )
        },
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
        raw_sections={},
    )


def test_build_statbook_outputs_canonical_rows() -> None:
    snapshot = _snapshot_with_levels()
    statbook = build_statbook(snapshot)
    assert statbook.rows
    ids = {row.stat_id for row in statbook.rows}
    assert "tower_hp" in ids
    assert any(stat_id.startswith("uw_") for stat_id in ids)
    assert all(row.phase.value == "start_of_run" for row in statbook.rows)


def test_build_statbook_places_wall_stats_before_uw_rows() -> None:
    snapshot = _snapshot_with_levels()
    statbook = build_statbook(snapshot)
    row_ids = [row.stat_id for row in statbook.rows]
    first_uw_index = min(index for index, stat_id in enumerate(row_ids) if stat_id.startswith("uw_"))
    assert row_ids.index("wall_hp") < first_uw_index
    assert row_ids.index("wall_regen") < first_uw_index
