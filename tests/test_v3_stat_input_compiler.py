from pathlib import Path

import pytest

from tower_sim.engines.stat_engine import StatInput
from tower_sim.registry.stat_registry import Phase
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from v3.stat_input_compiler import (
    V3StatInputCompilerError,
    compile_v3_baseline_loadout_stat_inputs,
    compile_v3_stat_inputs,
    validate_compiled_stat_inputs,
)

_IDS_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _snapshot():
    return compile_account_snapshot(parse_ids(_IDS_FIXTURE))


def test_compile_v3_stat_inputs_baseline_gem_respec_smoke() -> None:
    compiled = compile_v3_stat_inputs(_snapshot(), stage="baseline_gem_respec")
    assert compiled.stat_inputs
    assert all(item.contributor_family for item in compiled.stat_inputs)


def test_compile_v3_loadout_inputs_smoke() -> None:
    compiled = compile_v3_baseline_loadout_stat_inputs(
        _snapshot(), module_context="Farming"
    )
    assert compiled.stat_inputs
    assert all(item.contributor_family for item in compiled.stat_inputs)


def test_validate_compiled_stat_inputs_rejects_bad_stat_id() -> None:
    bad = [
        StatInput(
            stat_id="BadStat",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="ids:test",
            contributor_family="workshop",
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="stat_id_not_snake_case"):
        validate_compiled_stat_inputs(bad)


def test_validate_compiled_stat_inputs_rejects_missing_contributor_family() -> None:
    bad = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=1.0,
            provenance="workshop_table:Health",
            contributor_family=None,
        )
    ]
    with pytest.raises(V3StatInputCompilerError, match="missing_contributor_family"):
        validate_compiled_stat_inputs(bad)
