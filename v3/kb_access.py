"""Canonical extracted KB access helpers for v3.

v3 requires a single extracted canonical KB tree at ``./kb``.
No zip fallback is allowed in normal workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml

_DEFAULT_EXTRACTED_ROOT = Path(".")


class V3KbAccessError(RuntimeError):
    pass


@dataclass(frozen=True)
class KbLocation:
    mode: str  # always "extracted"
    root: Path


def resolve_kb_location(
    *,
    extracted_root: Path = _DEFAULT_EXTRACTED_ROOT,
) -> KbLocation:
    extracted_kb = extracted_root / "kb"
    if extracted_kb.exists() and extracted_kb.is_dir():
        return KbLocation(mode="extracted", root=extracted_root)
    raise V3KbAccessError(
        "Extracted canonical KB not found. Expected ./kb (canonical extracted KB tree)."
    )


def read_text(rel_path: str, *, location: KbLocation | None = None) -> str:
    loc = location or resolve_kb_location()
    path = loc.root / rel_path
    if not path.exists():
        raise V3KbAccessError(f"KB path missing in extracted tree: {rel_path}")
    return path.read_text(encoding="utf-8")


def load_yaml(rel_path: str, *, location: KbLocation | None = None) -> dict:
    payload = yaml.safe_load(read_text(rel_path, location=location))
    if not isinstance(payload, dict):
        raise V3KbAccessError(f"KB YAML at {rel_path} did not parse to mapping.")
    return payload


def content_sha256(rel_path: str, *, location: KbLocation | None = None) -> str:
    text = read_text(rel_path, location=location)
    return sha256(text.encode("utf-8")).hexdigest()
