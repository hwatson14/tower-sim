"""
Boss BC parameter loader.
"""

import json
from pathlib import Path

from tower_sim.combat.boss_survivability import BossDataError


def load_bc_params(path: Path) -> dict:
    data = json.loads(path.read_text())
    for k in ("boss_hp_mult", "boss_attack_mult"):
        if k not in data:
            raise BossDataError(f"Missing BC param: {k}")
    return data
