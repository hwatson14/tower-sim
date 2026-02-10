from __future__ import annotations

import re
from pathlib import Path

import yaml


def _snapshot_names_from_worker_index(repo_root: Path) -> set[str]:
    source = (repo_root / "worker" / "src" / "index.js").read_text()
    match = re.search(r"const\s+SNAPSHOT_FILENAMES\s*=\s*\{(?P<body>.*?)\};", source, re.S)
    assert match, "SNAPSHOT_FILENAMES object was not found in worker/src/index.js"

    names: set[str] = set()
    for line in match.group("body").splitlines():
        m = re.match(r'\s*([a-z0-9_]+)\s*:\s*"[^"]+"\s*,?\s*$', line)
        if m:
            names.add(m.group(1))
    assert names, "No snapshot names parsed from SNAPSHOT_FILENAMES"
    return names


def test_worker_openapi_exposes_all_snapshot_surfaces() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec = yaml.safe_load((repo_root / "worker" / "agent_openapi.yaml").read_text())
    assert isinstance(spec, dict)
    paths = spec["paths"]

    snapshot_names = _snapshot_names_from_worker_index(repo_root)
    for name in snapshot_names:
        path = f"/snapshot/{name}"
        assert path in paths, f"Missing OpenAPI path for snapshot '{name}'"
        get_op = paths[path].get("get", {})
        assert get_op.get("operationId"), f"Missing operationId for '{path}'"


def test_worker_agent_instructions_reference_all_snapshot_fetches() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    instructions = (repo_root / "worker" / "agent_instructions.md").read_text()

    assert "fetchIdsDumpLatest" in instructions
    assert "fetchBaseStatsLatest" in instructions
    assert "fetchInventoryLatest" in instructions
    assert "fetchLoadoutLatest" in instructions
    assert "fetchBaseComponentsLatest" in instructions
    assert "fetchInventoryComponentsLatest" in instructions
    assert "fetchRunStatsLatest" in instructions
