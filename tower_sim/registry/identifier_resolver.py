from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable, Mapping, Sequence


DEFAULT_RUNTIME_DIR = Path("reference/runtime")
DEFAULT_REGISTRY_FILENAME = "IDENTIFIER_REGISTRY.csv"
DEFAULT_LEDGER_FILENAME = "STAT_LEDGER_eHP_ROOTED.csv"


class RegistryFormatError(ValueError):
    pass


class LedgerFormatError(ValueError):
    pass


@dataclass(frozen=True)
class IdentifierRegistry:
    mapping: Mapping[str, str]
    registry_path: Path


@dataclass(frozen=True)
class StatLedger:
    identifiers: Sequence[str]
    ledger_path: Path


def list_remaining_unresolved(
    ledger_path: Path | None = None,
    registry_path: Path | None = None,
) -> list[str]:
    registry = load_identifier_registry(registry_path)
    ledger = load_stat_ledger(ledger_path)
    unresolved = sorted({token for token in ledger.identifiers if token not in registry.mapping})
    return unresolved


def print_remaining_unresolved(
    ledger_path: Path | None = None,
    registry_path: Path | None = None,
) -> list[str]:
    unresolved = list_remaining_unresolved(
        ledger_path=ledger_path,
        registry_path=registry_path,
    )
    for token in unresolved:
        print(token)
    return unresolved


def load_identifier_registry(registry_path: Path | None = None) -> IdentifierRegistry:
    resolved_path = registry_path or _default_registry_path()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Missing identifier registry: {resolved_path}")
    mapping = _parse_registry_csv(resolved_path)
    return IdentifierRegistry(mapping=mapping, registry_path=resolved_path)


def load_stat_ledger(ledger_path: Path | None = None) -> StatLedger:
    resolved_path = ledger_path or _default_ledger_path()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Missing stat ledger: {resolved_path}")
    identifiers = _parse_ledger_csv(resolved_path)
    return StatLedger(identifiers=identifiers, ledger_path=resolved_path)


def _default_registry_path() -> Path:
    return DEFAULT_RUNTIME_DIR / DEFAULT_REGISTRY_FILENAME


def _default_ledger_path() -> Path:
    return DEFAULT_RUNTIME_DIR / DEFAULT_LEDGER_FILENAME


def _parse_registry_csv(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RegistryFormatError("Identifier registry CSV missing headers.")
        key_column, value_column = _resolve_registry_columns(reader.fieldnames)
        mapping: dict[str, str] = {}
        for row in reader:
            key = (row.get(key_column) or "").strip()
            value = (row.get(value_column) or "").strip()
            if not key or not value:
                continue
            mapping[key] = value
    if not mapping:
        raise RegistryFormatError("Identifier registry CSV has no mappings.")
    return mapping


def _parse_ledger_csv(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise LedgerFormatError("Stat ledger CSV missing headers.")
        token_column = _resolve_ledger_column(reader.fieldnames)
        identifiers: list[str] = []
        for row in reader:
            value = (row.get(token_column) or "").strip()
            if value:
                identifiers.append(value)
    if not identifiers:
        raise LedgerFormatError("Stat ledger CSV has no identifiers.")
    return identifiers


def _resolve_registry_columns(headers: Iterable[str]) -> tuple[str, str]:
    candidates = (
        ("identifier", "resolved_identifier"),
        ("identifier", "canonical_id"),
        ("token", "canonical_id"),
        ("token", "resolved_identifier"),
    )
    header_set = {header.strip() for header in headers}
    for key, value in candidates:
        if key in header_set and value in header_set:
            return key, value
    raise RegistryFormatError(
        "Identifier registry CSV missing expected columns. "
        "Expected one of: "
        f"{', '.join(f'{key}+{value}' for key, value in candidates)}."
    )


def _resolve_ledger_column(headers: Iterable[str]) -> str:
    candidates = ("identifier", "token", "raw_identifier")
    header_set = {header.strip() for header in headers}
    for name in candidates:
        if name in header_set:
            return name
    raise LedgerFormatError(
        "Stat ledger CSV missing expected identifier column. "
        f"Expected one of: {', '.join(candidates)}."
    )


__all__ = [
    "DEFAULT_LEDGER_FILENAME",
    "DEFAULT_REGISTRY_FILENAME",
    "DEFAULT_RUNTIME_DIR",
    "IdentifierRegistry",
    "LedgerFormatError",
    "RegistryFormatError",
    "StatLedger",
    "list_remaining_unresolved",
    "load_identifier_registry",
    "load_stat_ledger",
    "print_remaining_unresolved",
]
