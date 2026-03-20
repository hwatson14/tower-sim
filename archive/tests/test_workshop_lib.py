import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.workshop_lib import load_workshop_tables, workshop_value  # noqa: E402


def test_workshop_values_lookup() -> None:
    tables = load_workshop_tables()
    assert workshop_value("Damage", 1, tables, section="WSValues") == "5.877"
    assert workshop_value("Damage", 0, tables, section="Workshop +") == "0"


def test_workshop_missing_raises() -> None:
    tables = load_workshop_tables()
    with pytest.raises(KeyError):
        workshop_value("Damage", 9999, tables)
