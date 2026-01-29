from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path
import zipfile

import pytest


def load_module() -> object:
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "assemble_fullrepo_zip.py"
    spec = importlib.util.spec_from_file_location("assemble_fullrepo_zip", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load assemble_fullrepo_zip module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_zip_bytes() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        handle.writestr("hello.txt", "hello")
    return buffer.getvalue()


def split_bytes(data: bytes, size: int) -> list[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)]


def write_parts(tmp_path: Path, prefix: str, chunks: list[bytes]) -> list[Path]:
    parts = []
    for index, chunk in enumerate(chunks):
        part_path = tmp_path / f"{prefix}.part{index:03d}"
        part_path.write_bytes(chunk)
        parts.append(part_path)
    return parts


def test_combines_parts_and_detects_eocd(tmp_path: Path) -> None:
    module = load_module()
    zip_bytes = make_zip_bytes()
    chunks = split_bytes(zip_bytes, 10)
    write_parts(tmp_path, "tower_sim_step1_fullrepo", chunks)

    parts = module.find_parts(tmp_path, "tower_sim_step1_fullrepo")
    module.validate_part_sequence(parts, "tower_sim_step1_fullrepo")

    output_path = tmp_path / "combined.zip"
    module.write_combined(parts, output_path)

    assert output_path.read_bytes() == zip_bytes
    assert module.has_eocd(output_path) is True


def test_validate_part_sequence_detects_gap(tmp_path: Path) -> None:
    module = load_module()
    prefix = "tower_sim_step1_fullrepo"
    (tmp_path / f"{prefix}.part000").write_bytes(b"a")
    (tmp_path / f"{prefix}.part002").write_bytes(b"b")

    parts = module.find_parts(tmp_path, prefix)
    with pytest.raises(SystemExit, match="Missing part indexes"):
        module.validate_part_sequence(parts, prefix)


def test_has_eocd_false_for_non_zip(tmp_path: Path) -> None:
    module = load_module()
    output_path = tmp_path / "combined.zip"
    output_path.write_bytes(b"not a zip")
    assert module.has_eocd(output_path) is False
