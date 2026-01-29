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
