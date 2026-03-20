from __future__ import annotations

import json
from pathlib import Path

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot, snapshot_as_dict
from tower_sim.loaders.ids_parser import parse_ids

_IDS_FIXTURE = Path('tests/fixtures/tower-sim-data/_IDS.csv')
_GOLDEN_FIXTURE = Path('tests/fixtures/compiled_snapshot/account_snapshot_golden.json')


def test_compiler_matches_full_golden_snapshot_fixture() -> None:
    snapshot = compile_account_snapshot(parse_ids(_IDS_FIXTURE))
    actual = snapshot_as_dict(snapshot)
    actual['ids_path'] = 'tests/fixtures/tower-sim-data/_IDS.csv'
    expected = json.loads(_GOLDEN_FIXTURE.read_text(encoding='utf-8'))
    assert actual == expected
