import json
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from tower_sim.engines.combat.boss_params_loader import load_bc_params
from tower_sim.engines.combat.boss_survivability import (
    BossContext,
    BossDataError,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)


def test_shape():
    boss = BossStats(None, 10, 2.0, 1.0)
    tower = TowerDefense(0.0, 0.0, 0.0)
    ctx = BossContext(
        wave=100,
        tier=14,
        league="Test",
        boss=boss,
        tower=tower,
        combat_params={
            "tower_hp": 100.0,
            "tower_regen": 0.0,
            "defense_pct": 0.0,
            "defense_abs": 0.0,
            "wall_hp": 0.0,
            "wall_regen": 0.0,
            "damage_reduction": 0.0,
            "thorns_frac": 0.1,
            "pc_frac": 0.0,
            "pc_boss_mult": 1.0,
            "orb_damage_frac": 0.0,
            "electrons_damage_frac": 0.0,
        },
        bc_params={"boss_hp_mult": 1, "boss_attack_mult": 1},
    )
    out = resolve_boss_fight(ctx)
    assert out["outcome"] in ("tower_kills_boss", "boss_kills_tower")
    assert out["ttk_seconds"] > 0
    assert out["ttd_seconds"] > 0


def test_load_bc_params_missing_key(tmp_path: Path):
    path = tmp_path / "boss_bc.json"
    path.write_text(json.dumps({"boss_hp_mult": 1.0}))
    with pytest.raises(BossDataError, match="Missing BC param"):
        load_bc_params(path)
