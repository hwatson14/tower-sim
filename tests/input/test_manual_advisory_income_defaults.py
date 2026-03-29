from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_manual_advisory_income_defaults__seed_requested_weekly_values():
    payload = yaml.safe_load((ROOT / "input" / "manual_inputs.yaml").read_text())
    rows = payload["manual_advisory_inputs"]["inputs"]
    keyed = {row["input_id"]: row for row in rows}

    assert keyed["income.gems.per_week"]["value"] == 4000
    assert keyed["income.gems.per_week"]["is_set"] is True

    assert keyed["income.power_stones.per_week"]["value"] == 450
    assert keyed["income.power_stones.per_week"]["is_set"] is True

    assert keyed["income.keys.per_week"]["value"] == 0
    assert keyed["income.keys.per_week"]["is_set"] is True

    assert keyed["income.medals.per_week"]["value"] == 1000
    assert keyed["income.medals.per_week"]["is_set"] is True

    assert "income.shards.per_week" not in keyed

    assert keyed["module.farming.hours_per_day"]["value"] == 23.5
    assert keyed["module.farming.hours_per_day"]["is_set"] is True
