import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.labs_lib import lab_value, load_labs_tables  # noqa: E402


def test_labs_lookup() -> None:
    tables = load_labs_tables()
    assert lab_value("lab_health", 1, tables) == "1.03"


def test_labs_missing_raises() -> None:
    tables = load_labs_tables()
    with pytest.raises(KeyError):
        lab_value("lab_health", 9999, tables)
