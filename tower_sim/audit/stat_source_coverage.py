from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from tower_sim.ids_state import IdsState
from tower_sim.stat_registry import StatRegistry, UnknownStatError
from tower_sim.wiki.labs import _LEGACY_LAB_FILES


class CoverageStatus:
    COVERED = "COVERED"
    MISSING_TABLE = "MISSING_TABLE"
    NOT_PROMOTABLE = "NOT_PROMOTABLE"


@dataclass(frozen=True)
class CoverageItem:
    name: str
    status: str
    detail: str | None = None


@dataclass(frozen=True)
class CoverageReport:
    workshop: List[CoverageItem]
    labs: List[CoverageItem]
    summary: Dict[str, int]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["workshop"] = [asdict(item) for item in self.workshop]
        payload["labs"] = [asdict(item) for item in self.labs]
        return payload


def _load_audit_index(audit_path: Path) -> Dict[str, dict]:
    if not audit_path.exists():
        return {}
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    return {entry.get("file_path", ""): entry for entry in results}


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _resolve_lab_cache_path(cache_dir: Path, lab_name: str) -> Path:
    slug = _slugify(lab_name)
    candidate = cache_dir / f"lab_{slug}.csv"
    if candidate.exists():
        return candidate
    legacy = _LEGACY_LAB_FILES.get(lab_name)
    if legacy:
        return cache_dir / legacy
    return candidate


def _validate_registry_ids(stat_ids: Iterable[str], registry: StatRegistry) -> None:
    for stat_id in stat_ids:
        try:
            registry.validate_stat_id(stat_id)
        except UnknownStatError as exc:
            raise UnknownStatError(f"Unknown stat_id in coverage report: {stat_id}") from exc


def audit_stat_coverage(
    ids: IdsState,
    workshop_lib: object,
    labs_lib: object,
    registry: StatRegistry,
) -> CoverageReport:
    repo_root = Path(__file__).resolve().parents[2]
    audit_path = repo_root / "audit" / "wiki_cache_audit.json"
    cache_dir = repo_root / "tower_sim" / "wiki" / "cache"
    audit_index = _load_audit_index(audit_path)

    workshop_tables = workshop_lib.load_workshop_tables()
    lab_names: Sequence[str] = labs_lib.list_labs()

    workshop_items: List[CoverageItem] = []
    for name in sorted(ids.workshop.entries.keys()):
        if name in workshop_tables.wsvalues:
            workshop_items.append(CoverageItem(name=name, status=CoverageStatus.COVERED))
        else:
            workshop_items.append(CoverageItem(name=name, status=CoverageStatus.MISSING_TABLE))

    lab_items: List[CoverageItem] = []
    for name in sorted(ids.labs.labs.keys()):
        if name in lab_names:
            lab_items.append(CoverageItem(name=name, status=CoverageStatus.COVERED))
            continue
        cache_path = _resolve_lab_cache_path(cache_dir, name)
        audit_entry = audit_index.get(str(cache_path))
        if audit_entry is not None and audit_entry.get("status") != "PROMOTABLE":
            lab_items.append(
                CoverageItem(
                    name=name,
                    status=CoverageStatus.NOT_PROMOTABLE,
                    detail=audit_entry.get("status"),
                )
            )
            continue
        lab_items.append(CoverageItem(name=name, status=CoverageStatus.MISSING_TABLE))

    _validate_registry_ids([], registry)

    summary: Dict[str, int] = {}
    for item in [*workshop_items, *lab_items]:
        summary[item.status] = summary.get(item.status, 0) + 1

    return CoverageReport(workshop=workshop_items, labs=lab_items, summary=summary)


def coverage_report_json(report: CoverageReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def coverage_report_markdown(report: CoverageReport) -> str:
    lines = ["# Stat Source Coverage", "", "## Summary"]
    for status, count in sorted(report.summary.items()):
        lines.append(f"- {status}: {count}")
    lines.append("")
    lines.append("## Workshop")
    for item in report.workshop:
        detail = f" ({item.detail})" if item.detail else ""
        lines.append(f"- {item.name}: {item.status}{detail}")
    lines.append("")
    lines.append("## Labs")
    for item in report.labs:
        detail = f" ({item.detail})" if item.detail else ""
        lines.append(f"- {item.name}: {item.status}{detail}")
    lines.append("")
    return "\n".join(lines)


def write_coverage_report_json(report: CoverageReport, path: Path) -> None:
    path.write_text(coverage_report_json(report), encoding="utf-8")
