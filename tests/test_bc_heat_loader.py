import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.bc_heat_loader import (  # noqa: E402
    HeatDataError,
    load_heat_bundle,
    load_tournament_heat_table,
)


def _write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_load_heat_bundle_parses_rows(tmp_path: Path) -> None:
    heat_path = tmp_path / "heat.csv"
    magnitudes_path = tmp_path / "magnitudes.csv"
    _write_csv(heat_path, "league,wave,heat_scalar\nbronze,1,1.0\n")
    _write_csv(magnitudes_path, "bc_id,league,wave,magnitude\nstat_a,bronze,1,2.5\n")

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


def test_tournament_heat_value_at_stepwise_and_bounds_per_league(tmp_path: Path) -> None:
    scale_path = tmp_path / "heat_scale_long.csv"
    registry_path = tmp_path / "heat_bc_registry.csv"
    _write_csv(
        scale_path,
        "league,wave_actual,bc_key,bc_variant,value_raw,value_num,value_unit,value_kind\n"
        "champion,0,enemy_speed,,0.2,0.2,ratio,multiplier\n"
        "champion,20,enemy_speed,,0.4,0.4,ratio,multiplier\n"
        "legend,0,enemy_speed,,0.3,0.3,ratio,multiplier\n"
        "legend,20,enemy_speed,,0.5,0.5,ratio,multiplier\n"
        "champion,0,more_bosses,,6,6,waves,interval_waves\n"
        "legend,0,more_bosses,,6,6,waves,interval_waves\n"
        "champion,0,death_defy_down,,-0.01,-0.01,ratio,probability_delta\n"
        "legend,0,death_defy_down,,-0.01,-0.01,ratio,probability_delta\n"
        "champion,0,energy_shields_down,,0.01,0.01,ratio,recharge_time_multiplier_or_delta\n"
        "legend,0,energy_shields_down,,0.01,0.01,ratio,recharge_time_multiplier_or_delta\n",
    )
    _write_csv(
        registry_path,
        "bc_key,bc_variant,value_unit,value_kind,applies_champion,applies_legend\n"
        "enemy_speed,,ratio,multiplier,true,true\n"
        "more_bosses,,waves,interval_waves,true,true\n"
        "death_defy_down,,ratio,probability_delta,true,true\n"
        "energy_shields_down,,ratio,recharge_time_multiplier_or_delta,true,true\n",
    )

    table = load_tournament_heat_table(scale_path, registry_path)

    assert table.value_at(league="champion", wave_actual=19, bc_id="enemy_speed:").value_num == 0.2
    assert table.value_at(league="legend", wave_actual=19, bc_id="enemy_speed:").value_num == 0.3

    with pytest.raises(HeatDataError, match="outside coverage"):
        table.value_at(league="champion", wave_actual=-1, bc_id="enemy_speed:")


def test_tournament_heat_unknown_league_or_bc_id_raises(tmp_path: Path) -> None:
    scale_path = tmp_path / "heat_scale_long.csv"
    registry_path = tmp_path / "heat_bc_registry.csv"
    _write_csv(
        scale_path,
        "league,wave_actual,bc_key,bc_variant,value_raw,value_num,value_unit,value_kind\n"
        "champion,0,enemy_speed,,0.2,0.2,ratio,multiplier\n"
        "legend,0,enemy_speed,,0.3,0.3,ratio,multiplier\n"
        "champion,0,more_bosses,,6,6,waves,interval_waves\n"
        "legend,0,more_bosses,,6,6,waves,interval_waves\n"
        "champion,0,death_defy_down,,-0.01,-0.01,ratio,probability_delta\n"
        "legend,0,death_defy_down,,-0.01,-0.01,ratio,probability_delta\n"
        "champion,0,energy_shields_down,,0.01,0.01,ratio,recharge_time_multiplier_or_delta\n"
        "legend,0,energy_shields_down,,0.01,0.01,ratio,recharge_time_multiplier_or_delta\n",
    )
    _write_csv(
        registry_path,
        "bc_key,bc_variant,value_unit,value_kind,applies_champion,applies_legend\n"
        "enemy_speed,,ratio,multiplier,true,true\n"
        "more_bosses,,waves,interval_waves,true,true\n"
        "death_defy_down,,ratio,probability_delta,true,true\n"
        "energy_shields_down,,ratio,recharge_time_multiplier_or_delta,true,true\n",
    )
    table = load_tournament_heat_table(scale_path, registry_path)

    with pytest.raises(HeatDataError, match="Unsupported tournament league"):
        table.value_at(league="platinum", wave_actual=0, bc_id="enemy_speed:")
    with pytest.raises(HeatDataError, match="Unknown tournament bc_id"):
        table.value_at(league="champion", wave_actual=0, bc_id="enemy_speed:fast")
