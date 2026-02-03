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
from tower_sim.loaders.ids_parser import parse_ids, resolve_ids_path


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
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
    ids_state = parse_ids(ids_path)
    statbook = build_statbook(ids_state)

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
            _safe_get("cards", lambda: ids_state.cards.cards, missing_sections)
        ),
        "modules": _to_jsonable(
            _safe_get("modules", lambda: ids_state.modules.slots, missing_sections)
        ),
        "relics": _to_jsonable(
            _safe_get("relics", lambda: ids_state.relics.relics, missing_sections)
        ),
        "vault": _to_jsonable(
            _safe_get("vault", lambda: ids_state.vault.vault, missing_sections)
        ),
        "bots": _to_jsonable(
            _safe_get("bots", lambda: ids_state.bots.bots, missing_sections)
        ),
        "ultimate_weapons": _to_jsonable(
            _safe_get(
                "ultimate_weapons",
                lambda: ids_state.ultimate_weapons.entries,
                missing_sections,
            )
        ),
        "workshop": _to_jsonable(
            _safe_get("workshop", lambda: ids_state.workshop.entries, missing_sections)
        ),
        "labs": _to_jsonable(
            _safe_get("labs", lambda: ids_state.labs.labs, missing_sections)
        ),
        "themes_songs": None,
        "guardians": None,
        "player_stuff": None,
    }
    if include_raw:
        inventory["themes_songs"] = _to_jsonable(
            _safe_get(
                "themes_songs",
                lambda: ids_state.themes_songs.raw_rows,
                missing_sections,
            )
        )
        inventory["guardians"] = _to_jsonable(
            _safe_get(
                "guardians",
                lambda: ids_state.guardians.raw_rows,
                missing_sections,
            )
        )
        inventory["player_stuff"] = _to_jsonable(
            _safe_get(
                "player_stuff",
                lambda: ids_state.player_stuff.key_values,
                missing_sections,
            )
        )

    return {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _resolve_git_sha(),
        "ids_path": str(ids_path),
        "base_stats": base_stats,
        "inventory": inventory,
        "missing_sections": sorted(set(missing_sections)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dump base stats and IDS inventory to JSON for diagnostics."
    )
    parser.add_argument(
        "--ids-path",
        type=Path,
        help="Path to _IDS.csv (defaults to resolve_ids_path).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "out" / "runner_output.json",
        help="Output JSON path (default: out/runner_output.json).",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw inventory sections (themes/songs, guardians, player stuff).",
    )
    args = parser.parse_args()

    ids_path = args.ids_path or resolve_ids_path()
    output_path = args.output

    payload = build_diagnostics(ids_path, include_raw=args.include_raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
