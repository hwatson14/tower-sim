import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.bc_heat_loader import HeatDataError, load_heat_bundle  # noqa: E402


def _write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_load_heat_bundle_parses_rows(tmp_path: Path) -> None:
    heat_path = tmp_path / "heat.csv"
    magnitudes_path = tmp_path / "magnitudes.csv"
    _write_csv(
        heat_path,
        "league,wave,heat_scalar\nbronze,1,1.0\n",
    )
    _write_csv(
        magnitudes_path,
        "bc_id,league,wave,magnitude\nstat_a,bronze,1,2.5\n",
    )

    bundle = load_heat_bundle(heat_path, magnitudes_path)

    assert bundle.heat_scalars[0].league == "bronze"
    assert bundle.heat_scalars[0].wave == 1
    assert bundle.heat_scalars[0].scalar == 1.0
    assert bundle.magnitudes[0].bc_id == "stat_a"
    assert bundle.magnitudes[0].magnitude == 2.5


def test_load_heat_bundle_rejects_missing_columns(tmp_path: Path) -> None:
    heat_path = tmp_path / "heat.csv"
    magnitudes_path = tmp_path / "magnitudes.csv"
    _write_csv(heat_path, "league,wave\nbronze,1\n")
    _write_csv(magnitudes_path, "bc_id,league,wave\nstat_a,bronze,1\n")

    with pytest.raises(HeatDataError, match="Missing columns"):
        load_heat_bundle(heat_path, magnitudes_path)
