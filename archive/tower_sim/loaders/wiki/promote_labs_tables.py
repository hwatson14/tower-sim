"""Promote audited lab cache tables into canonical LabsValues v1 CSV."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass

import yaml
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class LabSourceSpec:
    source_path: str
    lab_primary_name: str
    level_column: str
    value_column: str






OUTPUT_HEADERS = [
    "lab_canonical_id",
    "lab_primary_name",
    "level",
    "value",
    "unit",
    "source_path",
    "source_sha256",
    "source_modified_utc",
]

ALLOWED_UNITS = {"percent_points", "percent", "raw_number"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _modified_time(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _load_audit_report(audit_path: Path) -> dict[str, dict]:
    if not audit_path.exists():
        return {}
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    return {entry.get("file_path", ""): entry for entry in results}


def _load_labs_catalog(catalog_path: Path) -> dict[str, str]:
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Naming catalog must be a mapping")

    categories = payload.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Naming catalog missing categories mapping")

    labs_entries = categories.get("labs")
    if not isinstance(labs_entries, list):
        raise ValueError("Naming catalog missing labs category list")

    mapping: dict[str, str] = {}
    for entry in labs_entries:
        if not isinstance(entry, dict):
            raise ValueError("Lab catalog entries must be mappings")
        canonical_id = str(entry.get("canonical_id", "")).strip()
        primary_name = str(entry.get("primary_name", "")).strip()
        if not canonical_id or not primary_name:
            raise ValueError("Lab catalog entry missing canonical_id or primary_name")
        mapping[primary_name] = canonical_id

    if not mapping:
        raise ValueError("No lab entries found in naming catalog")
    return mapping




def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _build_labs_name_index(catalog_path: Path) -> dict[str, str]:
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Naming catalog must be a mapping")
    categories = payload.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Naming catalog missing categories mapping")
    labs_entries = categories.get("labs")
    if not isinstance(labs_entries, list):
        raise ValueError("Naming catalog missing labs category list")

    index: dict[str, str] = {}
    for entry in labs_entries:
        if not isinstance(entry, dict):
            continue
        primary_name = str(entry.get("primary_name", "")).strip()
        if primary_name:
            index[_normalize_name(primary_name)] = primary_name
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                alias_name = str(alias).strip()
                if alias_name:
                    index[_normalize_name(alias_name)] = primary_name
    return index


def _discover_lab_sources(repo_root: Path, catalog_path: Path) -> list[LabSourceSpec]:
    cache_dir = repo_root / "tables" / "cache" / "wiki"
    if not cache_dir.exists():
        raise FileNotFoundError(f"Missing labs cache directory: {cache_dir}")

    name_index = _build_labs_name_index(catalog_path)
    specs: list[LabSourceSpec] = []
    for source_path in sorted(cache_dir.glob("*lab*.csv")):
        stem = source_path.stem
        normalized = stem
        if normalized.startswith("wall_lab_"):
            normalized = normalized[len("wall_lab_") :]
        elif normalized.startswith("lab_"):
            normalized = normalized[len("lab_") :]
        normalized = _normalize_name(normalized.replace("_", " "))
        primary_name = name_index.get(normalized)
        if primary_name is None:
            continue

        with source_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
        level_column = "level" if "level" in headers else "Level" if "Level" in headers else None
        value_column = "value_percent_points" if "value_percent_points" in headers else "Value" if "Value" in headers else None
        if level_column is None or value_column is None:
            continue
        specs.append(
            LabSourceSpec(
                source_path=str(source_path.relative_to(repo_root)),
                lab_primary_name=primary_name,
                level_column=level_column,
                value_column=value_column,
            )
        )
    if not specs:
        raise ValueError("No promotable lab cache CSV files discovered")
    return specs

def _parse_level(value: str) -> int:
    candidate = value.strip().replace(",", "")
    if candidate == "":
        raise ValueError("Missing level value")
    try:
        numeric = float(candidate)
    except ValueError as exc:
        raise ValueError(f"Invalid level value: {value}") from exc
    if not numeric.is_integer():
        raise ValueError(f"Non-integer level value: {value}")
    return int(numeric)


def _parse_value(value: str, value_column: str) -> tuple[float, str]:
    candidate = value.strip()
    if candidate == "":
        raise ValueError("Missing value")
    if value_column == "value_percent_points":
        return float(candidate), "percent_points"
    if "%" in candidate:
        numeric = candidate.replace("%", "").replace("+", "").strip()
        if numeric == "":
            raise ValueError(f"Invalid percent value: {value}")
        return float(numeric), "percent"
    return float(candidate), "raw_number"


def _get_provenance(
    source_path: Path,
    audit_index: dict[str, dict],
) -> tuple[str, str]:
    entry = audit_index.get(str(source_path))
    if entry is not None:
        status = entry.get("status")
        if status != "PROMOTABLE":
            raise ValueError(f"Audit status for {source_path} is {status}")
        sha256 = entry.get("sha256")
        modified = entry.get("modified_time")
        if not sha256 or not modified:
            raise ValueError(f"Audit metadata missing for {source_path}")
        return sha256, modified
    return _sha256(source_path), _modified_time(source_path)


def build_labs_values_v1(output_path: Path | None = None) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    catalog_path = repo_root / "tables" / "meta" / "registry" / "catalog.yaml"
    audit_path = repo_root / "audit" / "wiki_cache_audit.json"
    labs_catalog = _load_labs_catalog(catalog_path)
    audit_index = _load_audit_report(audit_path)

    if output_path is None:
        output_path = repo_root / "tables" / "inputs" / "economy" / "labs_values_v1.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[list[str]] = []
    source_specs = _discover_lab_sources(repo_root, catalog_path)
    for spec in source_specs:
        source_path = repo_root / spec.source_path
        if not source_path.exists():
            raise FileNotFoundError(f"Source CSV missing: {spec.source_path}")
        lab_canonical_id = labs_catalog.get(spec.lab_primary_name)
        if lab_canonical_id is None:
            raise ValueError(f"Unknown lab primary name: {spec.lab_primary_name}")
        sha256, modified = _get_provenance(source_path, audit_index)

        with source_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"Missing headers in {spec.source_path}")
            if spec.level_column not in reader.fieldnames:
                raise ValueError(
                    f"Missing level column {spec.level_column} in {spec.source_path}"
                )
            if spec.value_column not in reader.fieldnames:
                raise ValueError(
                    f"Missing value column {spec.value_column} in {spec.source_path}"
                )
            records: list[tuple[int, float, str]] = []
            for row in reader:
                level = _parse_level(row[spec.level_column])
                value, unit = _parse_value(row[spec.value_column], spec.value_column)
                if unit not in ALLOWED_UNITS:
                    raise ValueError(f"Unsupported unit {unit} in {spec.source_path}")
                records.append((level, value, unit))

        records.sort(key=lambda item: item[0])
        for level, value, unit in records:
            rows.append(
                [
                    lab_canonical_id,
                    spec.lab_primary_name,
                    str(level),
                    str(float(value)),
                    unit,
                    spec.source_path,
                    sha256,
                    modified,
                ]
            )

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTPUT_HEADERS)
        writer.writerows(rows)

    return output_path


def main() -> None:
    output_path = build_labs_values_v1()
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
