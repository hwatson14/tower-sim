from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tower_sim.registry.ep_formula_registry import (
    MechanicsManifestError,
    RegistryValidationError,
    load_active_mechanics_pack,
    load_ep_formula_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "mechanics" / "manifest.yaml"
LOADER_MODULE_PATH = REPO_ROOT / "tower_sim" / "registry" / "ep_formula_registry.py"


FORBIDDEN_BYPASS_TOKENS = (
    "mechanics_library",
    "formula_library",
    "tables/registry/ep_formulas",
    "MECHANICS_FILENAME",
)


ALLOWED_BYPASS_PATHS = {
    "tower_sim/registry/ep_formula_registry.py",
}


REQUIRED_MANIFEST_KEYS = {
    "schema_version",
    "active_pack",
    "packs",
}


def _load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_exists_with_required_minimal_schema() -> None:
    assert MANIFEST_PATH.exists(), "mechanics/manifest.yaml must exist"
    data = _load_manifest()
    assert isinstance(data, dict)
    assert REQUIRED_MANIFEST_KEYS.issubset(data.keys())
    assert data["schema_version"] == 1
    assert isinstance(data["active_pack"], str)
    assert isinstance(data["packs"], dict)
    assert data["active_pack"] in data["packs"]
    active_status = [
        pack_id
        for pack_id, pack_cfg in data["packs"].items()
        if isinstance(pack_cfg, dict) and pack_cfg.get("status") == "active"
    ]
    assert len(active_status) == 1
    assert active_status[0] == data["active_pack"]

    active_pack = data["packs"][data["active_pack"]]
    assert isinstance(active_pack.get("path"), str)
    assert (REPO_ROOT / active_pack["path"]).exists()
    files = active_pack.get("files")
    assert isinstance(files, dict)
    assert {"mechanics", "formulas", "targets", "sources", "ehp_legacy"}.issubset(
        files.keys()
    )


def test_active_pack_loader_fail_closed_for_missing_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        "tower_sim.registry.ep_formula_registry._default_manifest_path",
        lambda: REPO_ROOT / "mechanics" / "missing_manifest.yaml",
    )
    with pytest.raises(MechanicsManifestError):
        load_active_mechanics_pack()


def test_active_pack_loader_fail_closed_for_missing_pack_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    # Intentionally incomplete pack to assert fail-closed behavior.
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "active_pack": "test",
                "packs": {"test": {"path": str(pack_dir.relative_to(tmp_path)), "status": "active"}},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tower_sim.registry.ep_formula_registry._default_manifest_path",
        lambda: manifest_path,
    )
    with pytest.raises(MechanicsManifestError):
        load_active_mechanics_pack()


def test_loader_resolves_active_pack_and_registry_loads() -> None:
    active_pack = load_active_mechanics_pack()
    assert active_pack.pack_id
    assert active_pack.mechanics_library
    assert active_pack.formula_library
    registry = load_ep_formula_registry(strict=False)
    assert "EPD_ASPD" in registry.mechanics


def test_registry_loader_has_no_path_override_hook() -> None:
    loader_text = LOADER_MODULE_PATH.read_text(encoding="utf-8")
    assert "registry_dir" not in loader_text


def test_blocked_symbols_match_strict_registry_missing_symbols() -> None:
    with pytest.raises(RegistryValidationError) as excinfo:
        load_ep_formula_registry(strict=True)

    missing = set(excinfo.value.missing_symbols)
    assert {"EPD_SPB", "EPG_MODULE_BONUS"}.issubset(missing)


def test_no_runtime_bypass_of_mechanics_manifest_loader() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / "tower_sim").rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED_BYPASS_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_BYPASS_TOKENS:
            if token in text:
                offenders.append(f"{rel}: contains {token!r}")
                break
    assert not offenders, "Bypass patterns found outside loader:\n" + "\n".join(offenders)
