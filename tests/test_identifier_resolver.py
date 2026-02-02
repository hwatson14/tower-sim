from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.registry.identifier_resolver import list_remaining_unresolved


def test_list_remaining_unresolved_from_temp_files(tmp_path: Path) -> None:
    registry_path = tmp_path / "IDENTIFIER_REGISTRY.csv"
    ledger_path = tmp_path / "STAT_LEDGER_eHP_ROOTED.csv"

    registry_path.write_text(
        "identifier,canonical_id\n"
        "HP,STAT_TOWER_HP\n"
        "REGEN,STAT_TOWER_REGEN\n",
        encoding="utf-8",
    )
    ledger_path.write_text(
        "identifier\n"
        "HP\n"
        "REGEN\n"
        "DEF_PCT\n",
        encoding="utf-8",
    )

    remaining = list_remaining_unresolved(
        ledger_path=ledger_path,
        registry_path=registry_path,
    )

    assert remaining == ["DEF_PCT"]


@pytest.mark.skip(
    reason=(
        "Requires complete runtime identifier registry and eHP ledger "
        "in reference/runtime to validate closure success."
    )
)
def test_ehp_closure_succeeds_when_registry_complete() -> None:
    remaining = list_remaining_unresolved()
    assert remaining == []
