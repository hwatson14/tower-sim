import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.perks_gate import PerksDisabledError, assert_perks_enabled  # noqa: E402


def test_perks_gate_missing_field_raises() -> None:
    with pytest.raises(PerksDisabledError, match="missing"):
        assert_perks_enabled({})


def test_perks_gate_disabled_raises() -> None:
    with pytest.raises(PerksDisabledError, match="disabled"):
        assert_perks_enabled({"perks_enabled": False})


def test_perks_gate_enabled_allows() -> None:
    assert_perks_enabled({"perks_enabled": True})
