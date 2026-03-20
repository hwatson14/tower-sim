"""v3 KB access helpers.

This module provides a single deterministic accessor for KB content used by v3.
It resolves the extracted in-repo `kb/` tree, enforces path safety, and exposes
small helpers used by lock/drift checks.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTRACTED_KB_ROOT = _REPO_ROOT / "kb"


class V3KBAccessError(RuntimeError):
    """Raised when KB content cannot be resolved safely."""


@dataclass(frozen=True)
class KBLocation:
    mode: str
    root: Path


def resolve_kb_location() -> KBLocation:
    """Resolve the canonical extracted KB tree location.

    v3 currently supports only the extracted in-repo KB tree and fails closed
    when it is unavailable.
    """

    if not _EXTRACTED_KB_ROOT.exists() or not _EXTRACTED_KB_ROOT.is_dir():
        raise V3KBAccessError(f"KB root not found: {_EXTRACTED_KB_ROOT}")
    return KBLocation(mode="extracted", root=_EXTRACTED_KB_ROOT)


def _normalize_legacy_rel_path(rel_path: str, *, location: KBLocation) -> Path:
    raw = Path(rel_path)
    if raw.is_absolute():
        raise V3KBAccessError(f"Absolute KB path is not allowed: {rel_path}")

    candidate = (location.root.parent / raw).resolve()

    # Legacy compatibility: allow callers that reference `kb/<domain>/...`
    # while package content is nested under `kb/kb/<domain>/...`.
    if not candidate.exists() and raw.parts[:1] == ("kb",):
        nested = Path("kb") / raw
        candidate = (location.root.parent / nested).resolve()

    root_guard = location.root.parent.resolve()
    try:
        candidate.relative_to(root_guard)
    except ValueError as exc:
        raise V3KBAccessError(f"KB path escapes repository root: {rel_path}") from exc

    return candidate


def read_text(rel_path: str, *, location: KBLocation | None = None) -> str:
    active = location or resolve_kb_location()
    path = _normalize_legacy_rel_path(rel_path, location=active)
    if not path.exists() or not path.is_file():
        raise V3KBAccessError(f"KB file not found: {rel_path}")
    return path.read_text(encoding="utf-8")


def load_yaml(rel_path: str, *, location: KBLocation | None = None) -> Any:
    payload = yaml.safe_load(read_text(rel_path, location=location))
    if payload is None:
        raise V3KBAccessError(f"KB YAML file is empty: {rel_path}")
    return payload


def content_sha256(rel_path: str, *, location: KBLocation | None = None) -> str:
    payload = read_text(rel_path, location=location)
    return sha256(payload.encode("utf-8")).hexdigest()


def _assert_mechanics_authority_path(rel_path: str) -> None:
    norm = rel_path.replace("\\", "/")
    if "/notes/" in norm or "/sources/" in norm or "/derived/" in norm:
        raise V3KBAccessError(f"noncanonical_mechanics_surface:{rel_path}")


def read_csv_rows(
    rel_path: str,
    *,
    location: KBLocation | None = None,
    authority: str = "any",
) -> list[dict[str, str]]:
    if authority == "mechanics":
        _assert_mechanics_authority_path(rel_path)

    payload = read_text(rel_path, location=location)
    rows = list(csv.DictReader(payload.splitlines()))
    if not rows:
        raise V3KBAccessError(f"KB CSV file is empty: {rel_path}")
    normalized: list[dict[str, str]] = []
    for row in rows:
        normalized.append({str(k): "" if v is None else str(v) for k, v in row.items()})
    return normalized
