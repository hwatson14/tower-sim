from __future__ import annotations

import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.ids_state import (  # noqa: E402
    BotsState,
    CardsState,
    GuardiansState,
    IdsState,
    LabsState,
    ModulesState,
    PlayerStuffState,
    RelicsState,
    ThemesSongsState,
    UltimateWeaponsState,
    VaultState,
    WorkshopEntry,
    WorkshopPlusState,
    WorkshopState,
)
from tower_sim.statbook_builder import build_statbook  # noqa: E402


def _ids_state_with_levels() -> IdsState:
    labs = LabsState(labs={"LabA": "5", "LabB": None}, raw_rows=[])
    workshop_entries = {
        "Attack": WorkshopEntry(
            name="Attack",
            unlocked=None,
            coin_level="3",
            max_level="7",
            category=None,
            raw_row=[],
        ),
        "Defense": WorkshopEntry(
            name="Defense",
            unlocked=None,
            coin_level=None,
            max_level=None,
            category=None,
            raw_row=[],
        ),
    }
    workshop = WorkshopState(entries=workshop_entries, raw_rows=[])
    return IdsState(
        labs=labs,
        workshop=workshop,
        workshop_plus=WorkshopPlusState(raw_rows=[]),
        ultimate_weapons=UltimateWeaponsState(
            entries={},
            uw_plus_placeholder=None,
            raw_rows=[],
        ),
        cards=CardsState(cards={}, equipped_preset_only=[], raw_rows=[]),
        relics=RelicsState(relics={}, raw_rows=[]),
        vault=VaultState(vault={}, raw_rows=[]),
        bots=BotsState(bots={}, raw_rows=[]),
        themes_songs=ThemesSongsState(raw_rows=[]),
        modules=ModulesState(slots=[], raw_rows=[]),
        guardians=GuardiansState(raw_rows=[]),
        player_stuff=PlayerStuffState(key_values={}, raw_rows=[]),
        raw_sections={},
    )


def test_build_statbook_outputs_rows() -> None:
    ids_state = _ids_state_with_levels()
    statbook = build_statbook(ids_state)
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
