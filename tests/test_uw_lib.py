import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.libs.uw_lib import load_uw_table  # noqa: E402


def test_uw_missing_table_fails_closed() -> None:
    with pytest.raises(FileNotFoundError):
        load_uw_table("Missing_UW_Table.csv")
