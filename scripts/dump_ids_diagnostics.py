from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from tower_sim.engines.statbook_builder import build_statbook
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids, resolve_ids_path
from tower_sim.util.account_snapshot import PRESET_NAMES


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _safe_get(
    path_label: str,
    getter: Callable[[], Any],
    missing_sections: list[str],
) -> Any:
    try:
        return getter()
    except (AttributeError, KeyError):
        missing_sections.append(path_label)
        return None


def _resolve_git_sha() -> str | None:
    env_sha = os.getenv("GITHUB_SHA")
    if env_sha:
        return env_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    sha = result.stdout.strip()
    return sha or None


def build_diagnostics(ids_path: Path, *, include_raw: bool) -> Dict[str, Any]:
    ids_raw = parse_ids(ids_path)
    snapshot = compile_account_snapshot(ids_raw)
    statbook = build_statbook(snapshot)

    sorted_rows = sorted(statbook.rows, key=lambda row: (row.stat_id, str(row.phase)))
    base_stats = []
    for row in sorted_rows:
        base_stats.append(
            {
                "stat_id": row.stat_id,
                "phase": row.phase,
                "base_value": row.base_value,
                "final_value": row.final_value,
                "provenance": _to_jsonable(row.provenance),
            }
        )

    missing_sections: list[str] = []
    inventory = {
        "cards": _to_jsonable(
            _safe_get(
                "cards",
                lambda: snapshot.cards_inventory,
                missing_sections,
            )
        ),
        "modules": _to_jsonable(
            _safe_get(
                "modules",
                lambda: snapshot.modules_inventory,
                missing_sections,
            )
        ),
        "relics": _to_jsonable(
            _safe_get("relics", lambda: snapshot.relics, missing_sections)
        ),
        "vault": _to_jsonable(_safe_get("vault", lambda: snapshot.vault, missing_sections)),
        "bots": _to_jsonable(_safe_get("bots", lambda: snapshot.bots, missing_sections)),
        "ultimate_weapons": _to_jsonable(
            _safe_get("ultimate_weapons", lambda: snapshot.ultimate_weapons, missing_sections)
        ),
        "workshop": _to_jsonable(
            _safe_get("workshop", lambda: snapshot.workshop, missing_sections)
        ),
        "labs": _to_jsonable(_safe_get("labs", lambda: snapshot.labs, missing_sections)),
        "themes_songs": None,
        "guardians": None,
        "player_stuff": None,
    }
    if include_raw:
        inventory["themes_songs"] = _to_jsonable(
            _safe_get(
                "themes_songs",
                lambda: ids_raw.raw_sections.get("Themes & Songs", []),
                missing_sections,
            )
        )
        inventory["guardians"] = _to_jsonable(
            _safe_get(
                "guardians",
                lambda: ids_raw.raw_sections.get("Guardians", []),
                missing_sections,
            )
        )
        inventory["player_stuff"] = _to_jsonable(
            _safe_get(
                "player_stuff",
                lambda: snapshot.player_meta,
                missing_sections,
            )
        )

    return {
        "schema_version": 3,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _resolve_git_sha(),
        "ids_path": str(ids_path),
        "base_stats": base_stats,
        "inventory": inventory,
        "snapshot": _to_jsonable(snapshot),
        "missing_sections": sorted(set(missing_sections)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile IDS snapshot and write audit JSON artifacts."
    )
    parser.add_argument(
        "--ids-path",
        type=Path,
        help="Path to _IDS.csv (defaults to resolve_ids_path).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "audit",
        help="Output directory for audit JSON (default: audit/).",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw inventory sections (themes/songs, guardians, player stuff).",
    )
    args = parser.parse_args()

    ids_path = args.ids_path or resolve_ids_path()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_diagnostics(ids_path, include_raw=args.include_raw)

    snapshot_path = output_dir / "account_snapshot.json"
    summary_path = output_dir / "account_snapshot.summary.json"
    diff_path = output_dir / "account_snapshot.diff.json"

    previous = _read_json(snapshot_path)
    snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    summary_path.write_text(json.dumps(_build_summary(payload), indent=2, sort_keys=True))
    if previous is not None:
        diff_path.write_text(
            json.dumps(_build_diff(previous, payload), indent=2, sort_keys=True)
        )
    print(f"Wrote {snapshot_path}")
    print(f"Wrote {summary_path}")
    if diff_path.exists():
        print(f"Wrote {diff_path}")


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = payload.get("snapshot", {})
    return {
        "ids_path": payload.get("ids_path"),
        "schema_version": payload.get("schema_version"),
        "preset_names": list(PRESET_NAMES),
        "labs_count": len(snapshot.get("labs", {})),
        "workshop_count": len(snapshot.get("workshop", {})),
        "cards_count": len(snapshot.get("cards_inventory", {})),
        "modules_count": len(snapshot.get("modules_inventory", {})),
        "module_slots": sorted(snapshot.get("module_system_state", {}).keys()),
        "allocation_levels": snapshot.get("allocation_levels", {}),
        "inferred_shard_budgets": snapshot.get("inferred_shard_budgets", {}),
    }


def _build_diff(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    changes = _diff_paths(previous, current)
    return {"changed": bool(changes), "changed_paths": changes}


def _diff_paths(previous: Any, current: Any, prefix: str = "") -> List[str]:
    if type(previous) is not type(current):
        return [prefix or "<root>"]
    if isinstance(previous, dict):
        changes: List[str] = []
        keys = set(previous.keys()) | set(current.keys())
        for key in sorted(keys):
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in previous or key not in current:
                changes.append(new_prefix)
                continue
            changes.extend(_diff_paths(previous[key], current[key], new_prefix))
        return changes
    if isinstance(previous, list):
        changes = []
        if len(previous) != len(current):
            return [prefix or "<root>"]
        for idx, (old, new) in enumerate(zip(previous, current)):
            new_prefix = f"{prefix}[{idx}]"
            changes.extend(_diff_paths(old, new, new_prefix))
        return changes
    if previous != current:
        return [prefix or "<root>"]
    return []


if __name__ == "__main__":
    main()
