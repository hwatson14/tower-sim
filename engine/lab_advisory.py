from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
_LAB_ADVISORY_TABLE_PATH = ROOT / 'kb' / 'labs' / 'advisory' / 'tables' / 'lab-tier-list-v27_0_3.csv'
_LAB_ADVISORY_SOURCE_REGISTRY_PATH = ROOT / 'kb' / 'labs' / 'advisory' / 'registry' / 'lab-advisory-source-registry.csv'


@dataclass(frozen=True)
class LabAdvisoryRow:
    workbook_row: int
    lab_name: str
    unlock_tier: str | None
    ranking_primary: str | None
    ranking_conditional: str | None
    notes: str | None
    is_unlocked_cached: bool | None
    player_ranking_cached: str | None
    status_cached: str | None
    lab_canonical_id: str
    mapping_status: str
    ranking_primary_order: int | None
    ranking_conditional_order: float | None
    evidence_type: str
    source_workbook: str
    source_sheet: str
    source_version: str
    advisory_status: str
    authoritative_for: str
    not_authoritative_for: str


@dataclass(frozen=True)
class LabAdvisorySourceRegistryRow:
    advisory_surface_id: str
    surface_name: str
    surface_kind: str
    canonical_location: str
    source_workbook: str
    source_sheet: str
    provenance_note: str
    usage_role: str
    do_not_use_for: str
    version_tag: str


@lru_cache(maxsize=1)
def load_lab_advisory_rows() -> tuple[LabAdvisoryRow, ...]:
    with _LAB_ADVISORY_TABLE_PATH.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = tuple(_parse_lab_advisory_row(row) for row in reader)
    if not rows:
        raise ValueError('Lab advisory table is empty; advisory imports must fail closed.')
    return rows


@lru_cache(maxsize=1)
def load_lab_advisory_rows_by_canonical_id() -> Mapping[str, LabAdvisoryRow]:
    rows_by_id: dict[str, LabAdvisoryRow] = {}
    for row in load_lab_advisory_rows():
        if row.lab_canonical_id in rows_by_id:
            raise ValueError(f'Duplicate advisory lab canonical id {row.lab_canonical_id!r}.')
        rows_by_id[row.lab_canonical_id] = row
    return rows_by_id


@lru_cache(maxsize=1)
def load_lab_advisory_source_registry() -> tuple[LabAdvisorySourceRegistryRow, ...]:
    with _LAB_ADVISORY_SOURCE_REGISTRY_PATH.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = tuple(LabAdvisorySourceRegistryRow(**row) for row in reader)
    if not rows:
        raise ValueError('Lab advisory source registry is empty; advisory provenance must fail closed.')
    return rows


def get_lab_advisory_row(lab_canonical_id: str) -> LabAdvisoryRow:
    try:
        return load_lab_advisory_rows_by_canonical_id()[lab_canonical_id]
    except KeyError as exc:
        raise KeyError(f'Unknown advisory lab canonical id {lab_canonical_id!r}.') from exc


def _parse_lab_advisory_row(row: dict[str, str]) -> LabAdvisoryRow:
    return LabAdvisoryRow(
        workbook_row=int(row['workbook_row']),
        lab_name=row['lab_name'],
        unlock_tier=_optional_str(row['unlock_tier']),
        ranking_primary=_optional_str(row['ranking_primary']),
        ranking_conditional=_optional_str(row['ranking_conditional']),
        notes=_optional_str(row['notes']),
        is_unlocked_cached=_optional_bool(row['is_unlocked_cached']),
        player_ranking_cached=_optional_str(row['player_ranking_cached']),
        status_cached=_optional_str(row['status_cached']),
        lab_canonical_id=row['lab_canonical_id'],
        mapping_status=row['mapping_status'],
        ranking_primary_order=_optional_int(row['ranking_primary_order']),
        ranking_conditional_order=_optional_float(row['ranking_conditional_order']),
        evidence_type=row['evidence_type'],
        source_workbook=row['source_workbook'],
        source_sheet=row['source_sheet'],
        source_version=row['source_version'],
        advisory_status=row['advisory_status'],
        authoritative_for=row['authoritative_for'],
        not_authoritative_for=row['not_authoritative_for'],
    )


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_bool(value: str | None) -> bool | None:
    token = _optional_str(value)
    if token is None:
        return None
    if token == 'True':
        return True
    if token == 'False':
        return False
    raise ValueError(f'Unsupported advisory bool token {value!r}.')


def _optional_int(value: str | None) -> int | None:
    token = _optional_str(value)
    return None if token is None else int(token)


def _optional_float(value: str | None) -> float | None:
    token = _optional_str(value)
    return None if token is None else float(token)
