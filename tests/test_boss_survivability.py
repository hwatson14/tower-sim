import json
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from tower_sim.combat.boss_params_loader import load_bc_params
from tower_sim.combat.boss_survivability import (
    BossContext,
    BossDataError,
    BossStats,
    TowerDefense,
    resolve_boss_fight,
)


def test_shape():
    boss = BossStats(1000, 100, 1.0, 1.0)
    tower = TowerDefense(0.5, 0.0, 1000)
    ctx = BossContext(
        wave=100,
        tier=14,
        league="Test",
        boss=boss,
        tower=tower,
        combat_params={"boss_dps": 100},
        bc_params={"boss_hp_mult": 1, "boss_attack_mult": 1},
    )
    out = resolve_boss_fight(ctx)
    assert out["outcome"] in ("tower_kills_boss", "boss_kills_tower")


def test_load_bc_params_missing_key(tmp_path: Path):
    path = tmp_path / "boss_bc.json"
    path.write_text(json.dumps({"boss_hp_mult": 1.0}))
    with pytest.raises(BossDataError, match="Missing BC param"):
        load_bc_params(path)
