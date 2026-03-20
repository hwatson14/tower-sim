from pathlib import Path
import subprocess
import sys


def test_kb_drift_report_status_ok(tmp_path: Path) -> None:
    out = tmp_path / "kb_drift_report.json"
    result = subprocess.run(
        [sys.executable, "scripts/generate_kb_drift_report.py", "--strict", "--output", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert out.exists()
