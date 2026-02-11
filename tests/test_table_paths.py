from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders.table_paths import TableEntry, TablePathError, _validate_manifest, resolve_table_path


def test_resolve_table_path_valid_key() -> None:
    path = resolve_table_path("perks")
    assert path.as_posix().endswith("tables/inputs/perks/perks_v1.csv")
    assert path.exists()


def test_resolve_table_path_missing_key_error() -> None:
    with pytest.raises(TablePathError, match="Unknown table manifest key"):
        resolve_table_path("unknown-key")


def test_validate_manifest_duplicate_key_error() -> None:
    entries = (
        TableEntry("dup", "tables/inputs/perks/perks_v1.csv"),
        TableEntry("dup", "tables/inputs/perks/perk_pool_weights_v1.csv"),
    )
    with pytest.raises(TablePathError, match="Duplicate table manifest key"):
        _validate_manifest(entries)


def test_resolve_table_path_rejects_legacy_in_runtime_mode() -> None:
    with pytest.raises(TablePathError, match="Runtime table resolution rejected"):
        resolve_table_path("tier_wave_damage_legacy")
