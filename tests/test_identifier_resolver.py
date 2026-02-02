from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import pytest

from tower_sim.registry.identifier_resolver import (
    IdentifierResolver,
    UnresolvedIdentifierError,
)


def test_ehp_identifier_resolution_closure() -> None:
    runtime_dir = REPO_ROOT / "reference" / "runtime"
    registry_path = runtime_dir / "IDENTIFIER_REGISTRY.csv"
    ledger_path = runtime_dir / "STAT_LEDGER_eHP_ROOTED.csv"

    resolver = IdentifierResolver(registry_path)
    ledger = pd.read_csv(ledger_path)

    with pytest.raises(UnresolvedIdentifierError) as exc:
        resolver.resolve_ledger(ledger, fail_on_unresolved=True)

    report = exc.value.report
    assert report.unresolved_after > 0
    assert report.unresolved_tokens
