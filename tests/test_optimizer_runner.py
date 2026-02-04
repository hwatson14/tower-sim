from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.account_snapshot_loader import load_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import TASK_OPTIMIZE_LOADOUT, run_task


def _to_jsonable(value):
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _snapshot_payload():
    snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    return {"snapshot": _to_jsonable(snapshot)}


def test_load_account_snapshot_from_payload_roundtrip() -> None:
    payload = _snapshot_payload()
    loaded = load_account_snapshot(payload)
    assert loaded.default_preset == payload["snapshot"]["default_preset"]
    assert set(loaded.cards_inventory.keys()) == set(
        payload["snapshot"]["cards_inventory"].keys()
    )
    assert set(loaded.modules_inventory.keys()) == set(
        payload["snapshot"]["modules_inventory"].keys()
    )


def test_run_optimizer_task_requires_snapshot_payload() -> None:
    with pytest.raises(ValueError, match="Missing required args"):
        run_task(TASK_OPTIMIZE_LOADOUT, {"objective": "MAX_WAVE"})


def test_run_optimizer_task_fail_closed_placeholder() -> None:
    payload = _snapshot_payload()
    result = run_task(
        TASK_OPTIMIZE_LOADOUT,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": payload,
        },
    )
    assert result["ok"] is False
    assert result["fail_closed"] is True
    assert "optimizer_not_implemented" in result["missing"]
