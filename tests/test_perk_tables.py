from __future__ import annotations

from pathlib import Path
import pytest

from tower_sim.loaders.perk_tables import (
    PerkTableError,
    load_perk_definitions,
    load_perk_pool_weights,
)


def test_load_perk_definitions() -> None:
    perks = load_perk_definitions(Path("tables/inputs/perks/perks_v1.csv"))
    assert perks
    health_perk = next(perk for perk in perks if perk.perk_name == "x1.20 Max Health")
    assert health_perk.stacking_type == "multiplicative"
    assert health_perk.effect_stat_id == "tower_hp"

    def_pct = next(perk for perk in perks if perk.perk_name == "Defense Percent +4.00")
    assert def_pct.stacking_type == "additive"
    assert def_pct.effect_stat_id == "def_pct"


def test_load_perk_pool_weights() -> None:
    weights = load_perk_pool_weights(Path("tables/inputs/perks/perk_pool_weights_v1.csv"))
    assert weights
    total = sum(weight.weight_percent for weight in weights)
    assert total == 100


def test_load_perk_pool_weights_rejects_non_100_total(tmp_path: Path) -> None:
    bad_weights = tmp_path / "perk_pool_weights_bad.csv"
    bad_weights.write_text(
        "category,weight_percent,notes,source\n"
        "Common,40,,test\n"
        "Rare,40,,test\n",
        encoding="utf-8",
    )
    with pytest.raises(PerkTableError, match="must sum to 100.0"):
        load_perk_pool_weights(bad_weights)
