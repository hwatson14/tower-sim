"""Audit cached wiki CSV tables for per-level value integrity."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


LEVEL_HEADERS = {"level", "lvl"}
VALUE_HEADERS = {"value", "val", "effect", "bonus"}
DELIMITERS = [",", "\t", ";", "|"]


@dataclass(frozen=True)
class AuditStats:
    min_level: int | None
    max_level: int | None
    count_levels: int
    is_contiguous: bool | None
    min_value: float | None
    max_value: float | None
    unit_hint: str
    duplicate_levels: list[int] = field(default_factory=list)
    duplicate_values: list[float] = field(default_factory=list)
    missing_value_count: int = 0
    non_numeric_value_count: int = 0
    gaps: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class AuditResult:
    file_path: str
    sha256: str
    modified_time: str
    status: str
    reason: str | None
    delimiter: str | None
    headers: list[str]
    row_count: int
    level_column: str | None
    value_column: str | None
    levels_sorted: bool | None
    stats: AuditStats

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["stats"] = asdict(self.stats)
        return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _modified_time(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def detect_delimiter(sample: str) -> str | None:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=DELIMITERS)
    except csv.Error:
        return None
    return dialect.delimiter


def _normalize_header(value: str) -> str:
    return value.strip().lower()


def _parse_level(value: str) -> int | None:
    candidate = value.strip().replace(",", "")
    if candidate == "":
        return None
    try:
        if re.match(r"^-?\d+$", candidate):
            return int(candidate)
        numeric = float(candidate)
    except ValueError:
        return None
    if numeric.is_integer():
        return int(numeric)
    return None


def _strip_unit(value: str) -> tuple[str, str | None]:
    candidate = value.strip()
    if candidate == "":
        return candidate, None
    if "%" in candidate:
        return candidate.replace("%", ""), "percent_string"
    seconds_match = re.match(r"^\s*-?\d+(?:\.\d+)?\s*s(?:ec(?:onds)?)?\s*$", candidate)
    if seconds_match:
        stripped = re.sub(r"\s*s(?:ec(?:onds)?)?\s*$", "", candidate).strip()
        return stripped, "seconds_string"
    return candidate, None


def _parse_value(value: str) -> tuple[float | None, str | None]:
    stripped, unit_hint = _strip_unit(value)
    candidate = stripped.replace(",", "")
    if candidate.strip() == "":
        return None, unit_hint
    try:
        return float(candidate), unit_hint
    except ValueError:
        return None, unit_hint


def _infer_columns(headers: list[str]) -> tuple[int | None, int | None]:
    normalized = [_normalize_header(h) for h in headers]
    level_idx = None
    value_idx = None
    for idx, header in enumerate(normalized):
        if header in LEVEL_HEADERS and level_idx is None:
            level_idx = idx
        if header in VALUE_HEADERS and value_idx is None:
            value_idx = idx
    return level_idx, value_idx


def _positional_infer(rows: list[list[str]]) -> tuple[int | None, int | None]:
    if not rows:
        return None, None
    if len(rows[0]) != 2:
        return None, None
    levels: list[int] = []
    values: list[float] = []
    for row in rows:
        if len(row) < 2:
            return None, None
        level = _parse_level(row[0])
        value, _ = _parse_value(row[1])
        if level is None or value is None:
            return None, None
        levels.append(level)
        values.append(value)
    if not levels or not values:
        return None, None
    return 0, 1


def _detect_unit_hint(values: Iterable[str], parse_hints: Iterable[str | None]) -> str:
    hints = {hint for hint in parse_hints if hint}
    if "percent_string" in hints:
        return "percent_string"
    if "seconds_string" in hints:
        return "seconds_string"
    for value in values:
        if "%" in value:
            return "percent_string"
    return "raw_number"


def audit_cache_file(path: Path) -> AuditResult:
    if not path.exists():
        return AuditResult(
            file_path=str(path),
            sha256="",
            modified_time="",
            status="NOT_PROMOTABLE",
            reason="file_missing",
            delimiter=None,
            headers=[],
            row_count=0,
            level_column=None,
            value_column=None,
            levels_sorted=None,
            stats=AuditStats(
                min_level=None,
                max_level=None,
                count_levels=0,
                is_contiguous=None,
                min_value=None,
                max_value=None,
                unit_hint="unknown",
            ),
        )

    text = path.read_text(encoding="utf-8", errors="replace")
    sample = "\n".join(text.splitlines()[:5])
    delimiter = detect_delimiter(sample)
    if delimiter is None:
        return _fail_result(path, "delimiter_detection_failed")

    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return _fail_result(path, "empty_file", delimiter=delimiter)

    headers = rows[0]
    data_rows = rows[1:]
    level_idx, value_idx = _infer_columns(headers)
    if level_idx is None or value_idx is None:
        inferred = _positional_infer(data_rows)
        level_idx, value_idx = inferred
    if level_idx is None or value_idx is None:
        return _fail_result(
            path,
            "missing_level_or_value_column",
            delimiter=delimiter,
            headers=headers,
            row_count=len(data_rows),
        )

    levels: list[int] = []
    values: list[float] = []
    raw_values: list[str] = []
    parse_hints: list[str | None] = []
    missing_value_count = 0
    non_numeric_value_count = 0
    for row in data_rows:
        if len(row) <= max(level_idx, value_idx):
            return _fail_result(
                path,
                "row_length_mismatch",
                delimiter=delimiter,
                headers=headers,
                row_count=len(data_rows),
                level_column=headers[level_idx],
                value_column=headers[value_idx],
            )
        level_raw = row[level_idx]
        value_raw = row[value_idx]
        raw_values.append(value_raw)

        level = _parse_level(level_raw)
        if level is None:
            return _fail_result(
                path,
                "invalid_level_value",
                delimiter=delimiter,
                headers=headers,
                row_count=len(data_rows),
                level_column=headers[level_idx],
                value_column=headers[value_idx],
            )
        levels.append(level)

        value, hint = _parse_value(value_raw)
        parse_hints.append(hint)
        if value is None:
            if value_raw.strip() == "":
                missing_value_count += 1
            else:
                non_numeric_value_count += 1
            continue
        values.append(value)

    if missing_value_count or non_numeric_value_count:
        return _fail_result(
            path,
            "non_numeric_or_missing_values",
            delimiter=delimiter,
            headers=headers,
            row_count=len(data_rows),
            level_column=headers[level_idx],
            value_column=headers[value_idx],
            missing_value_count=missing_value_count,
            non_numeric_value_count=non_numeric_value_count,
        )

    if not levels:
        return _fail_result(
            path,
            "no_levels_found",
            delimiter=delimiter,
            headers=headers,
            row_count=len(data_rows),
            level_column=headers[level_idx],
            value_column=headers[value_idx],
        )

    if any(level < 1 for level in levels):
        return _fail_result(
            path,
            "level_below_one",
            delimiter=delimiter,
            headers=headers,
            row_count=len(data_rows),
            level_column=headers[level_idx],
            value_column=headers[value_idx],
        )

    duplicate_levels = _find_duplicates(levels)
    if duplicate_levels:
        return _fail_result(
            path,
            "duplicate_levels",
            delimiter=delimiter,
            headers=headers,
            row_count=len(data_rows),
            level_column=headers[level_idx],
            value_column=headers[value_idx],
            duplicate_levels=duplicate_levels,
        )

    sorted_levels = sorted(levels)
    levels_sorted = levels == sorted_levels
    min_level = sorted_levels[0]
    max_level = sorted_levels[-1]
    expected = set(range(1, max_level + 1))
    missing_levels = sorted(expected - set(levels))
    is_contiguous = len(missing_levels) == 0 and min_level == 1

    unit_hint = _detect_unit_hint(raw_values, parse_hints)
    duplicate_values = _find_duplicates(values)

    stats = AuditStats(
        min_level=min_level,
        max_level=max_level,
        count_levels=len(levels),
        is_contiguous=is_contiguous,
        min_value=min(values) if values else None,
        max_value=max(values) if values else None,
        unit_hint=unit_hint,
        duplicate_levels=duplicate_levels,
        duplicate_values=duplicate_values,
        missing_value_count=missing_value_count,
        non_numeric_value_count=non_numeric_value_count,
        gaps=missing_levels,
    )

    status = "PROMOTABLE" if is_contiguous else "PROMOTABLE_WITH_GAPS"

    return AuditResult(
        file_path=str(path),
        sha256=_sha256(path),
        modified_time=_modified_time(path),
        status=status,
        reason=None,
        delimiter=delimiter,
        headers=headers,
        row_count=len(data_rows),
        level_column=headers[level_idx],
        value_column=headers[value_idx],
        levels_sorted=levels_sorted,
        stats=stats,
    )


def _find_duplicates(values: Iterable[int | float]) -> list:
    seen: set = set()
    duplicates: list = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _fail_result(
    path: Path,
    reason: str,
    *,
    delimiter: str | None = None,
    headers: list[str] | None = None,
    row_count: int = 0,
    level_column: str | None = None,
    value_column: str | None = None,
    missing_value_count: int = 0,
    non_numeric_value_count: int = 0,
    duplicate_levels: list[int] | None = None,
) -> AuditResult:
    stats = AuditStats(
        min_level=None,
        max_level=None,
        count_levels=row_count,
        is_contiguous=None,
        min_value=None,
        max_value=None,
        unit_hint="unknown",
        duplicate_levels=duplicate_levels or [],
        duplicate_values=[],
        missing_value_count=missing_value_count,
        non_numeric_value_count=non_numeric_value_count,
        gaps=[],
    )
    return AuditResult(
        file_path=str(path),
        sha256=_sha256(path) if path.exists() else "",
        modified_time=_modified_time(path) if path.exists() else "",
        status="NOT_PROMOTABLE",
        reason=reason,
        delimiter=delimiter,
        headers=headers or [],
        row_count=row_count,
        level_column=level_column,
        value_column=value_column,
        levels_sorted=None,
        stats=stats,
    )


def audit_cache_dir(cache_dir: Path) -> list[AuditResult]:
    return [audit_cache_file(path) for path in sorted(cache_dir.glob("*.csv"))]


def write_json_report(results: list[AuditResult], path: Path) -> None:
    summary = _summarize(results)
    payload = {
        "summary": summary,
        "results": [result.to_dict() for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def write_md_report(results: list[AuditResult], path: Path) -> None:
    summary = _summarize(results)
    lines = [
        "# Wiki cache audit report",
        "",
        "## Summary",
        f"- Total tables: {summary['total']}",
        f"- PROMOTABLE: {summary['PROMOTABLE']}",
        f"- PROMOTABLE_WITH_GAPS: {summary['PROMOTABLE_WITH_GAPS']}",
        f"- NOT_PROMOTABLE: {summary['NOT_PROMOTABLE']}",
        "",
        "## Tables",
        "",
        "| File | Status | Reason | Levels | Values | Unit |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        levels = _level_range(result.stats.min_level, result.stats.max_level)
        values = _value_range(result.stats.min_value, result.stats.max_value)
        reason = result.reason or ""
        lines.append(
            "| "
            f"{Path(result.file_path).name} | {result.status} | {reason} | "
            f"{levels} | {values} | {result.stats.unit_hint} |"
        )

    lines.append("")
    lines.append("## Details")
    lines.append("")
    for result in results:
        lines.append(f"### {Path(result.file_path).name}")
        lines.append("")
        lines.append(f"- Status: {result.status}")
        if result.reason:
            lines.append(f"- Reason: {result.reason}")
        lines.append(f"- Path: {result.file_path}")
        lines.append(f"- SHA256: {result.sha256}")
        lines.append(f"- Modified: {result.modified_time}")
        lines.append(f"- Delimiter: {result.delimiter}")
        lines.append(f"- Headers: {', '.join(result.headers)}")
        lines.append(f"- Row count: {result.row_count}")
        lines.append(f"- Level column: {result.level_column}")
        lines.append(f"- Value column: {result.value_column}")
        lines.append(f"- Levels sorted: {result.levels_sorted}")
        lines.append(f"- Level range: {_level_range(result.stats.min_level, result.stats.max_level)}")
        lines.append(f"- Level count: {result.stats.count_levels}")
        lines.append(f"- Contiguous: {result.stats.is_contiguous}")
        lines.append(f"- Gaps: {result.stats.gaps}")
        lines.append(f"- Value range: {_value_range(result.stats.min_value, result.stats.max_value)}")
        lines.append(f"- Unit hint: {result.stats.unit_hint}")
        lines.append(f"- Duplicate levels: {result.stats.duplicate_levels}")
        lines.append(f"- Duplicate values: {result.stats.duplicate_values}")
        lines.append(f"- Missing values: {result.stats.missing_value_count}")
        lines.append(f"- Non-numeric values: {result.stats.non_numeric_value_count}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def _summarize(results: list[AuditResult]) -> dict[str, int]:
    summary = {
        "total": len(results),
        "PROMOTABLE": 0,
        "PROMOTABLE_WITH_GAPS": 0,
        "NOT_PROMOTABLE": 0,
    }
    for result in results:
        summary[result.status] += 1
    return summary


def _level_range(min_level: int | None, max_level: int | None) -> str:
    if min_level is None or max_level is None:
        return ""
    return f"{min_level}..{max_level}"


def _value_range(min_value: float | None, max_value: float | None) -> str:
    if min_value is None or max_value is None:
        return ""
    return f"{min_value}..{max_value}"
