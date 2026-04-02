"""
advisors/upgrade_advisor.py -- Upgrade/next-step advice.

Owns: upgrade recommendation generation, lab advisory output,
next-best-action output assembly.

Extracted from: engine/lab_advisory.py (T5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from evaluators.ranker import (
    LabAdvisoryBundle,
    LabAdvisoryInputRow,
    LabAdvisorySourceRegistryInputRow,
)


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


def load_lab_advisory_rows(bundle: LabAdvisoryBundle) -> tuple[LabAdvisoryRow, ...]:
    return tuple(_to_lab_advisory_row(row) for row in bundle.advisory_rows)


def load_lab_advisory_rows_by_canonical_id(bundle: LabAdvisoryBundle) -> Mapping[str, LabAdvisoryRow]:
    return {
        row.lab_canonical_id: _to_lab_advisory_row(row)
        for row in bundle.advisory_rows_by_canonical_id.values()
    }


def load_lab_advisory_source_registry(bundle: LabAdvisoryBundle) -> tuple[LabAdvisorySourceRegistryRow, ...]:
    return tuple(_to_lab_advisory_source_registry_row(row) for row in bundle.source_registry_rows)


def get_lab_advisory_row(bundle: LabAdvisoryBundle, lab_canonical_id: str) -> LabAdvisoryRow:
    try:
        return load_lab_advisory_rows_by_canonical_id(bundle)[lab_canonical_id]
    except KeyError as exc:
        raise KeyError(f'Unknown advisory lab canonical id {lab_canonical_id!r}.') from exc


def _to_lab_advisory_row(row: LabAdvisoryInputRow) -> LabAdvisoryRow:
    return LabAdvisoryRow(
        workbook_row=row.workbook_row,
        lab_name=row.lab_name,
        unlock_tier=row.unlock_tier,
        ranking_primary=row.ranking_primary,
        ranking_conditional=row.ranking_conditional,
        notes=row.notes,
        is_unlocked_cached=row.is_unlocked_cached,
        player_ranking_cached=row.player_ranking_cached,
        status_cached=row.status_cached,
        lab_canonical_id=row.lab_canonical_id,
        mapping_status=row.mapping_status,
        ranking_primary_order=row.ranking_primary_order,
        ranking_conditional_order=row.ranking_conditional_order,
        evidence_type=row.evidence_type,
        source_workbook=row.source_workbook,
        source_sheet=row.source_sheet,
        source_version=row.source_version,
        advisory_status=row.advisory_status,
        authoritative_for=row.authoritative_for,
        not_authoritative_for=row.not_authoritative_for,
    )


def _to_lab_advisory_source_registry_row(
    row: LabAdvisorySourceRegistryInputRow,
) -> LabAdvisorySourceRegistryRow:
    return LabAdvisorySourceRegistryRow(
        advisory_surface_id=row.advisory_surface_id,
        surface_name=row.surface_name,
        surface_kind=row.surface_kind,
        canonical_location=row.canonical_location,
        source_workbook=row.source_workbook,
        source_sheet=row.source_sheet,
        provenance_note=row.provenance_note,
        usage_role=row.usage_role,
        do_not_use_for=row.do_not_use_for,
        version_tag=row.version_tag,
    )
