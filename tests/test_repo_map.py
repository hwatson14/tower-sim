from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_repo_map_validation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "check_repo_map.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "REPO_MAP validation failed:\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )



def test_docs_contract_consistency() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    contract = (repo_root / "CONTRACT.md").read_text(encoding="utf-8")

    for expected in [
        "[`CONTRACT.md`](./CONTRACT.md)",
        "[`AGENTS.md`](./AGENTS.md)",
        "[`REPO_MAP.yaml`](./REPO_MAP.yaml)",
        "[`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md)",
    ]:
        assert expected in readme, f"README missing required authority link: {expected}"

    assert "[`CONTRACT.md`](./CONTRACT.md) is authoritative" in agents

    for expected_section in [
        "## 2) Scope and intent (v1 locked)",
        "## 5) Source of truth hierarchy",
        "## 6) Mechanics manifest authority",
        "## 9) Pull request requirements",
        "## 10) Definition of done",
    ]:
        assert expected_section in contract, f"CONTRACT missing section: {expected_section}"
