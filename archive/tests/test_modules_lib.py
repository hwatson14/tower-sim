import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.modules_lib import (  # noqa: E402
    load_modules_library,
    substat_definitions,
    unique_effect_value,
)
from tower_sim.libs.modules_library import Rarity  # noqa: E402


def test_modules_lookup() -> None:
    library = load_modules_library()
    assert unique_effect_value("Astral Deliverance", Rarity.EPIC, library) == 20.0
    assert substat_definitions("Cannon", library)


def test_modules_missing_raises() -> None:
    library = load_modules_library()
    with pytest.raises(KeyError):
        unique_effect_value("Missing Module", Rarity.EPIC, library)
