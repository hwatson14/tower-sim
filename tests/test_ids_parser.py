import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.ids_parser import parse_ids  # noqa: E402


def test_parse_ids_fixture_sections() -> None:
    ids_state = parse_ids()

    assert ids_state.labs.labs
    assert ids_state.workshop.entries
    assert ids_state.modules.slots
    assert ids_state.ultimate_weapons.entries
    assert ids_state.cards.cards
    assert ids_state.bots.bots
    assert ids_state.relics.relics
    assert ids_state.vault.vault
    assert ids_state.themes_songs.raw_rows
    assert ids_state.guardians.raw_rows
    assert ids_state.player_stuff.key_values
