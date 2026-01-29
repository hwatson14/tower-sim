from __future__ import annotations

from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    import sys

    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.audit import status  # noqa: E402


def test_status_report_matches_file() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report_path = repo_root / "tower_sim" / "audit" / "implementation_status_report.md"
    expected = report_path.read_text(encoding="utf-8")
    assert status.generate_report() == expected
