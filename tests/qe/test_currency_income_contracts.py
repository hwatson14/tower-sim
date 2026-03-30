from __future__ import annotations

import pytest

from qe.query_currency_income import (
    currency_income_surface_contract_snapshot,
    income_resolution_audit_snapshot,
)

pytestmark = pytest.mark.live


def test_currency_income_contract_snapshot__uses_kb_aligned_power_stones_and_excludes_modules():
    contract = currency_income_surface_contract_snapshot()

    assert "shards" in contract["deterministic"]
    assert contract["deterministic"]["shards"]["surface_id"] == "derived::economy.income.shards"
    assert "shards" not in contract["externalized_manual"]

    assert "power_stones" in contract["externalized_manual"]
    assert contract["externalized_manual"]["power_stones"]["surface_id"] == "derived::economy.income.power_stones"
    assert contract["externalized_manual"]["power_stones"]["manual_input_id"] == "income.power_stones.per_week"

    assert "modules" not in contract["unsupported"]


def test_currency_income_audit_snapshot__partitions_supported_and_unsupported_resources():
    audit = income_resolution_audit_snapshot()

    assert "shards" in audit["deterministic_resources"]
    assert "shards" not in audit["externalized_manual_resources"]
    assert "power_stones" in audit["supported_resources"]
    assert "modules" not in audit["unsupported_resources"]
