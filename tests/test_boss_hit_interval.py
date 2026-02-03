from pathlib import Path
import sys

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from tower_sim.libs.boss_hit_interval import BossHitIntervalError, boss_hit_interval_seconds


def test_load_default_interval():
    assert boss_hit_interval_seconds("default") == pytest.approx(2.0)


def test_unknown_interval_id():
    with pytest.raises(BossHitIntervalError, match="Unknown hit interval id"):
        boss_hit_interval_seconds("missing-id")
