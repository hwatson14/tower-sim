import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.cards_lib import (  # noqa: E402
    card_value,
    card_value_by_rarity,
    load_cards_tables,
)


def test_cards_lookup() -> None:
    tables = load_cards_tables()
    assert card_value_by_rarity("Damage", "Common", 1, tables) == "1.50"
    assert card_value("Damage", 1, tables) == "1.50"


def test_cards_missing_raises() -> None:
    tables = load_cards_tables()
    with pytest.raises(KeyError):
        card_value("DoesNotExist", 1, tables)
