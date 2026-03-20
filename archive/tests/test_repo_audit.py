from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from tower_sim.audit.repo_audit import run_audit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(tmp_path: Path, naming_yaml: str, stub_module: str | None = None) -> Path:
    repo_root = tmp_path
    _write(repo_root / "tables" / "meta" / "registry" / "catalog.yaml", naming_yaml)

    _write(
        repo_root / "tower_sim" / "registry" / "stat_registry.py",
        """
from dataclasses import dataclass

@dataclass(frozen=True)
class StatDef:
    stat_id: str


def default_registry():
    return [StatDef(stat_id=\"tower_hp\")]
""".lstrip(),
    )

    key_modules = [
        "tower_sim/registry/stat_registry.py",
        "tower_sim/util/statbook.py",
        "tower_sim/libs/workshop_lib.py",
        "tower_sim/libs/labs_lib.py",
        "tower_sim/libs/modules_lib.py",
        "tower_sim/libs/uw_lib.py",
        "tower_sim/libs/cards_lib.py",
        "tower_sim/libs/modules_library.py",
    ]

    for rel_path in key_modules:
        file_path = repo_root / rel_path
        if rel_path == stub_module:
            _write(file_path, '"""stub"""\nimport typing\npass\n')
        elif file_path.exists():
            continue
        else:
            _write(file_path, "VALUE = 1\n")

    _write(
        repo_root / "tests" / "test_placeholder.py",
        """
from tower_sim.registry import stat_registry
""".lstrip(),
    )

    return repo_root


def test_audit_runs_without_error(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        """
categories:
  uws:
    - canonical_id: UW_TEST
      primary_name: "Test"
      aliases: ["Test"]
""".lstrip(),
    )
    report = run_audit(repo_root, strict=False)
    assert report


def test_canonical_id_duplicate_detected(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        """
categories:
  uws:
    - canonical_id: UW_TEST
      primary_name: "Test"
      aliases: ["Test"]
  cards:
    - canonical_id: UW_TEST
      primary_name: "Duplicate"
      aliases: ["Dup"]
""".lstrip(),
    )
    report = run_audit(repo_root, strict=False)
    assert any(item.code == "A_CANONICAL_ID_DUPLICATE" for item in report.failures)
    markdown = report.to_markdown()
    assert "Suggested fix" in markdown


def test_stub_detection(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        """
categories:
  uws:
    - canonical_id: UW_TEST
      primary_name: "Test"
      aliases: ["Test"]
""".lstrip(),
        stub_module="tower_sim/util/statbook.py",
    )
    report = run_audit(repo_root, strict=False)
    assert any(item.code == "D_MODULE_STUB" for item in report.failures)


def test_strict_mode_exit_code(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        """
categories:
  uws:
    - canonical_id: UW_TEST
      primary_name: "Test"
      aliases: ["Test"]
""".lstrip(),
        stub_module="tower_sim/util/statbook.py",
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

    result = subprocess.run(
        [sys.executable, "-m", "tower_sim.audit.repo_audit", "--strict"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2


def test_registry_scan_ignores_uppercase_constants(tmp_path: Path) -> None:
    repo_root = _build_repo(
        tmp_path,
        """
categories:
  uws:
    - canonical_id: UW_TEST
      primary_name: "Test"
      aliases: ["Test"]
""".lstrip(),
    )
    _write(repo_root / "tables" / ".keep", "")
    _write(
        repo_root / "tower_sim" / "libs" / "mapping.py",
        """
NOT_A_CANON = "NOT_A_CANON"
ENTRY = {"canonical_id": "UW_TEST"}
""".lstrip(),
    )

    report = run_audit(repo_root, strict=False)
    assert not any(item.code == "B_UNKNOWN_CANONICAL_ID" for item in report.failures)
