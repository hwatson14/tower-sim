"""Audit cached wiki CSV tables for per-level value integrity."""

from __future__ import annotations

from pathlib import Path

from tower_sim.loaders.wiki.cache_audit import (
    audit_cache_dir,
    write_json_report,
    write_md_report,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    cache_dir = repo_root / "tables" / "wiki_cache"
    audit_dir = repo_root / "audit"

    results = audit_cache_dir(cache_dir)
    write_json_report(results, audit_dir / "wiki_cache_audit.json")
    write_md_report(results, audit_dir / "wiki_cache_audit.md")

    summary = {
        "total": len(results),
        "PROMOTABLE": 0,
        "PROMOTABLE_WITH_GAPS": 0,
        "NOT_PROMOTABLE": 0,
    }
    for result in results:
        summary[result.status] += 1

    print("Wiki cache audit summary")
    print(f"- Total tables: {summary['total']}")
    print(f"- PROMOTABLE: {summary['PROMOTABLE']}")
    print(f"- PROMOTABLE_WITH_GAPS: {summary['PROMOTABLE_WITH_GAPS']}")
    print(f"- NOT_PROMOTABLE: {summary['NOT_PROMOTABLE']}")


if __name__ == "__main__":
    main()
