from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tower_sim.engines.statbook_builder import build_statbook
from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs
from tower_sim.engines.stat_engine import StatEngine, StatInput
from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.registry.stat_registry import Phase, default_registry
from tower_sim.run.problem_spec import ProblemSpec, ScenarioSpec
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.loaders.account_snapshot_compiler import (
    compile_account_snapshot,
    resolve_loadout,
)
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


def _canonical_json(obj: Any) -> str:
    return json.dumps(_to_jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _serialize_stat_input(item: StatInput) -> Dict[str, Any]:
    return {
        "stat_id": item.stat_id,
        "phase": item.phase.value if isinstance(item.phase, Phase) else str(item.phase),
        "base_value": item.base_value,
        "loadout_delta": item.loadout_delta,
        "enhancement_multiplier": item.enhancement_multiplier,
        "tier_rule_delta": item.tier_rule_delta,
        "tier_rule_multiplier": item.tier_rule_multiplier,
        "derived_value": item.derived_value,
        "provenance": item.provenance,
    }


def _build_ids_raw_index(ids_raw: Any) -> Dict[str, Any]:
    sections = []
    for name, rows in ids_raw.raw_sections.items():
        sections.append({"name": name, "rows": len(rows), "hash": _sha256(rows)})
    sections.sort(key=lambda s: s["name"])
    obj = {"sections": sections}
    obj["hash"] = _sha256(obj)
    return obj


def _default_problem_spec() -> ProblemSpec:
    # Deterministic baseline spec for debug bundle runs.
    return ProblemSpec(scenario=ScenarioSpec(mode="farming", tier=12, wave=1000), stat_inputs=[])


def _filter_statbook_rows(rows: list[Any], allowlist: Optional[Set[str]]) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    for row in rows:
        stat_id = getattr(row, "stat_id", None)
        if allowlist is not None and stat_id not in allowlist:
            continue
        out.append(
            {
                "stat_id": row.stat_id,
                "phase": row.phase,
                "base_value": row.base_value,
                "loadout_delta": getattr(row, "loadout_delta", None),
                "enhancement_multiplier": getattr(row, "enhancement_multiplier", None),
                "tier_rule_delta_or_multiplier": getattr(row, "tier_rule_delta_or_multiplier", None),
                "final_value": row.final_value,
                "provenance": _to_jsonable(getattr(row, "provenance", None)),
            }
        )
    return out


def _build_pipeline_bundle(
    ids_raw: Any,
    snapshot: Any,
    *,
    include_run_stats: bool,
    include_statbook_rows: bool,
    statbook_allowlist: Optional[Set[str]],
    include_max_wave: bool,
    problem_spec_path: Optional[Path],
) -> Dict[str, Any]:
    pipeline: Dict[str, Any] = {}
    stage_hashes: Dict[str, str] = {}

    raw_index = _build_ids_raw_index(ids_raw)
    pipeline["ids_raw_index"] = raw_index
    stage_hashes["ids_raw_index"] = raw_index["hash"]

    compiled = compile_full_stat_inputs(snapshot)
    compiled_obj: Dict[str, Any] = {
        "stat_inputs": [_serialize_stat_input(i) for i in compiled.stat_inputs],
        "missing": list(compiled.missing),
        "fail_closed": bool(compiled.missing),
    }
    compiled_obj["hash"] = _sha256(compiled_obj)
    pipeline["compiled_stat_inputs"] = compiled_obj
    stage_hashes["compiled_stat_inputs"] = compiled_obj["hash"]

    if include_run_stats:
        registry = default_registry()
        engine = StatEngine(registry)
        engine_result = engine.build(compiled.stat_inputs)

        run_stats_base = {phase.value: rs.values for phase, rs in engine_result.run_stats.items()}
        stat_engine_obj: Dict[str, Any] = {"run_stats_base": run_stats_base}

        if include_statbook_rows:
            stat_engine_obj["statbook_rows_filtered"] = _filter_statbook_rows(
                engine_result.statbook.rows,
                statbook_allowlist,
            )

        stat_engine_obj["hash"] = _sha256(stat_engine_obj)
        pipeline["stat_engine"] = stat_engine_obj
        stage_hashes["stat_engine"] = stat_engine_obj["hash"]

    if include_max_wave:
        spec = _default_problem_spec()
        if problem_spec_path is not None:
            spec = load_problem_spec(problem_spec_path)
        result = MaxWaveEvaluator().evaluate(spec, snapshot)
        max_wave_obj: Dict[str, Any] = {
            "problem_spec": _to_jsonable(asdict(spec)),
            "result": _to_jsonable(result),
        }
        max_wave_obj["hash"] = _sha256(max_wave_obj)
        pipeline["max_wave"] = max_wave_obj
        stage_hashes["max_wave"] = max_wave_obj["hash"]

    pipeline["stage_hashes"] = stage_hashes
    pipeline["hash"] = _sha256(pipeline)
    return pipeline


def _safe_get(
    path_label: str,
    getter: Callable[[], Any],
    missing_sections: list[str],
) -> Any:
    try:
        return getter()
    except (AttributeError, KeyError, ValueError):
        missing_sections.append(path_label)
        return None


def _build_base_stats_components(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    workshop_coin_levels = {}
    for name, entry in snapshot.get("workshop", {}).items():
        coin_level = entry.get("coin_level")
        if coin_level is not None:
            workshop_coin_levels[name] = int(coin_level)

    uw_start_end = {}
    for name, uw in snapshot.get("ultimate_weapons", {}).items():
        levels = [str(level) for level in uw.get("track_levels", [])]
        uw_start_end[name] = {
            "unlocked": uw.get("unlocked"),
            "start_of_run": levels,
            "end_of_run": levels,
        }

    return {
        "themes_songs": list(snapshot.get("raw_sections", {}).get("Themes & Songs", [])),
        "labs": dict(snapshot.get("labs", {})),
        "ultimate_weapons": uw_start_end,
        "vault_v2": dict(snapshot.get("vault", {})),
        "relics": dict(snapshot.get("relics", {})),
        "workshop_coin_levels": workshop_coin_levels,
        "enhancements": {
            "header": list(snapshot.get("workshop_enhancements", {}).get("header", [])),
            "rows": list(snapshot.get("workshop_enhancements", {}).get("rows", [])),
        },
        "guardians": {
            "header": list(snapshot.get("guardians", {}).get("header", [])),
            "rows": list(snapshot.get("guardians", {}).get("rows", [])),
        },
        "bots": {
            "names": list(snapshot.get("bots", [])),
            "upgrades": dict(snapshot.get("bot_upgrades", {})),
        },
    }


def _build_inventory_components(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    cards_mastery_inventory = {}
    for name, card in snapshot.get("cards_inventory", {}).items():
        cards_mastery_inventory[name] = {
            "level": card.get("level"),
            "mastery_unlocked": card.get("mastery_unlocked"),
            "mastery_lab_level": card.get("mastery_lab_level"),
        }

    modules_inventory = {}
    for name, module in snapshot.get("modules_inventory", {}).items():
        modules_inventory[name] = {
            "slot_type": module.get("slot_type"),
            "rarity": module.get("rarity"),
            "level": module.get("level"),
            "stat": module.get("stat"),
            "substats": [
                {
                    "stat_name": substat.get("stat_name"),
                    "rarity": substat.get("rarity"),
                    "value_display": substat.get("value_display"),
                    "value_num": substat.get("value_num"),
                }
                for substat in module.get("substats", [])
            ],
        }

    shard_allocation = {
        "slot_levels": {
            slot: {
                "primary_level": allocation.get("primary_level"),
                "assist_level": allocation.get("assist_level"),
            }
            for slot, allocation in snapshot.get("allocation_levels", {}).items()
        },
        "calculated_shards_per_category": dict(snapshot.get("inferred_shard_budgets", {})),
    }

    return {
        "cards_mastery_inventory": cards_mastery_inventory,
        "card_presets": dict(snapshot.get("card_presets", {})),
        "modules_inventory": modules_inventory,
        "module_presets": {
            preset: {
                slot: {
                    "primary": selection.get("primary"),
                    "assist": selection.get("assist"),
                }
                for slot, selection in slots.items()
            }
            for preset, slots in snapshot.get("module_presets", {}).items()
        },
        "shard_allocation": shard_allocation,
    }


def _build_run_stats_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for row in payload.get("base_stats", []):
        rows.append(
            {
                "stat_id": row.get("stat_id"),
                "phase": row.get("phase"),
                "start_of_run": row.get("base_value"),
                "loadout_delta": None,
                "end_of_run": row.get("final_value"),
                "provenance": row.get("provenance"),
            }
        )
    rows.sort(key=lambda r: (str(r["stat_id"]), str(r["phase"])))
    return {
        "rows": rows,
        "missing": list(payload.get("missing_sections", [])),
        "fail_closed": bool(payload.get("missing_sections")),
    }


def _build_staged_outputs(
    *,
    payload: Dict[str, Any],
    snapshot: Any,
    resolved_spec: ProblemSpec,
    preflight: Dict[str, Any],
    include_max_wave: bool,
) -> Dict[str, Dict[str, Any]]:
    snapshot_dict = _to_jsonable(snapshot)
    pipeline = payload.get("pipeline", {})
    loadout = payload.get("loadout", {})
    run_stats = _build_run_stats_report(payload)

    stage_1 = {
        "name": "locked_base",
        "description": "Themes & Songs, Labs, UWs, Vault, Relics",
        "themes_songs": list(snapshot_dict.get("raw_sections", {}).get("Themes & Songs", [])),
        "labs": dict(snapshot_dict.get("labs", {})),
        "ultimate_weapons": dict(snapshot_dict.get("ultimate_weapons", {})),
        "vault": dict(snapshot_dict.get("vault", {})),
        "relics": dict(snapshot_dict.get("relics", {})),
        "fail_closed": False,
        "missing": [],
    }

    workshop_coin = {
        name: entry.get("coin_level")
        for name, entry in snapshot_dict.get("workshop", {}).items()
        if entry.get("coin_level") is not None
    }
    stage_2 = {
        "name": "gem_respec_base",
        "description": "Workshop Coin, Enhancements, Guardians, Bots",
        "workshop_coin": workshop_coin,
        "enhancements": {
            "header": list(snapshot_dict.get("workshop_enhancements", {}).get("header", [])),
            "rows": list(snapshot_dict.get("workshop_enhancements", {}).get("rows", [])),
        },
        "guardians": {
            "header": list(snapshot_dict.get("guardians", {}).get("header", [])),
            "rows": list(snapshot_dict.get("guardians", {}).get("rows", [])),
        },
        "bots": {
            "names": list(snapshot_dict.get("bots", [])),
            "upgrades": dict(snapshot_dict.get("bot_upgrades", {})),
        },
        "fail_closed": False,
        "missing": [],
    }

    stage_3 = {
        "name": "loadout",
        "description": "Cards and Modules",
        "preset_name": loadout.get("preset_name"),
        "cards": list(loadout.get("cards", [])),
        "modules": dict(loadout.get("modules", {})),
        "fail_closed": bool(payload.get("missing_sections")),
        "missing": list(payload.get("missing_sections", [])),
    }

    stage_4_missing: List[str] = []
    diagnostics = preflight.get("diagnostics", {}) if isinstance(preflight, dict) else {}
    if not diagnostics:
        stage_4_missing.append("battle_conditions_context")
    stage_4 = {
        "name": "battle_conditions",
        "description": "Tier battle conditions and scenario context",
        "problem_spec": _to_jsonable(asdict(resolved_spec)),
        "mode": resolved_spec.scenario.mode,
        "tier": resolved_spec.scenario.tier,
        "league": resolved_spec.scenario.league,
        "wave": resolved_spec.scenario.wave,
        "wave_state": diagnostics.get("wave_state"),
        "wave_rows": diagnostics.get("wave_rows", {}),
        "missing_tier_rules": diagnostics.get("missing_tier_rules", []),
        "missing_heat": diagnostics.get("missing_heat", []),
        "fail_closed": bool(preflight.get("fail_closed", False) or stage_4_missing),
        "missing": sorted(set(stage_4_missing + list(preflight.get("missing", [])))),
    }

    stage_5 = {
        "name": "end_of_run",
        "description": "Run stats and evaluator outputs",
        "stat_engine": dict(pipeline.get("stat_engine", {})),
        "run_stats": run_stats,
        "max_wave": dict(pipeline.get("max_wave", {})) if include_max_wave else {},
        "fail_closed": bool(run_stats.get("fail_closed")),
        "missing": list(run_stats.get("missing", [])),
    }

    return {
        "stage_1_base_no_respec": stage_1,
        "stage_2_base_with_respec": stage_2,
        "stage_3_with_loadout": stage_3,
        "stage_4_with_battle_conditions": stage_4,
        "stage_5_end_of_run": stage_5,
    }


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


def build_diagnostics(
    ids_path: Path,
    *,
    include_raw: bool,
    include_pipeline: bool = False,
    include_run_stats: bool = False,
    include_statbook_rows: bool = False,
    statbook_allowlist: Optional[Set[str]] = None,
    include_max_wave: bool = False,
    problem_spec_path: Optional[Path] = None,
) -> Dict[str, Any]:
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
    loadout = _to_jsonable(
        _safe_get(
            "loadout",
            lambda: resolve_loadout(snapshot),
            missing_sections,
        )
    )
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

    payload: Dict[str, Any] = {
        "schema_version": 5,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _resolve_git_sha(),
        "ids_path": str(ids_path),
        "base_stats": base_stats,
        "inventory": inventory,
        "loadout": loadout,
        "snapshot": _to_jsonable(snapshot),
        "missing_sections": sorted(set(missing_sections)),
    }
    payload["pipeline"] = _build_pipeline_bundle(
        ids_raw,
        snapshot,
        include_run_stats=include_run_stats,
        include_statbook_rows=include_statbook_rows,
        statbook_allowlist=statbook_allowlist,
        include_max_wave=include_max_wave,
        problem_spec_path=problem_spec_path,
    )
    resolved_spec = _default_problem_spec() if problem_spec_path is None else load_problem_spec(problem_spec_path)
    preflight = MaxWaveEvaluator().preflight(resolved_spec, snapshot)
    payload["staged_outputs"] = _build_staged_outputs(
        payload=payload,
        snapshot=snapshot,
        resolved_spec=resolved_spec,
        preflight=preflight,
        include_max_wave=include_max_wave,
    )
    return payload



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compile an IDS account snapshot and write IDS dump artifacts "
            "(snapshot + extracts)."
        )
    )
    parser.add_argument(
        "--ids-path",
        type=Path,
        help="Path to _IDS.csv (defaults to resolve_ids_path).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "out",
        help="Output directory for JSON artifacts (default: out/).",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw inventory sections (themes/songs, guardians, player stuff).",
    )
    parser.add_argument(
        "--include-pipeline",
        action="store_true",
        help="Deprecated flag (pipeline snapshots are always emitted).",
    )
    parser.add_argument(
        "--include-run-stats",
        action="store_true",
        help="Deprecated flag (StatEngine run_stats are always emitted).",
    )
    parser.add_argument(
        "--include-statbook-rows",
        action="store_true",
        help="Emit computed StatEngine statbook rows (filtered; can be large).",
    )
    parser.add_argument(
        "--statbook-allowlist",
        type=str,
        default="",
        help="Comma-separated stat_ids to include in statbook_rows_filtered. Empty = all rows.",
    )
    parser.add_argument(
        "--include-max-wave",
        action="store_true",
        help="Run MaxWaveEvaluator and emit result+diagnostics in the pipeline bundle.",
    )
    parser.add_argument(
        "--problem-spec",
        type=Path,
        default=None,
        help="Optional path to a ProblemSpec YAML/JSON used when --include-max-wave is set.",
    )

    args = parser.parse_args()

    ids_path = args.ids_path or resolve_ids_path()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    allowlist: Optional[Set[str]] = None
    if args.statbook_allowlist.strip():
        allowlist = {s.strip() for s in args.statbook_allowlist.split(",") if s.strip()}

    payload = build_diagnostics(
        ids_path,
        include_raw=args.include_raw,
        include_pipeline=True,
        include_run_stats=True,
        include_statbook_rows=args.include_statbook_rows,
        statbook_allowlist=allowlist,
        include_max_wave=args.include_max_wave,
        problem_spec_path=args.problem_spec,
    )

    snapshot_path = output_dir / "account_snapshot.json"
    summary_path = output_dir / "account_snapshot.summary.json"
    diff_path = output_dir / "account_snapshot.diff.json"
    base_stats_path = output_dir / "base_stats.json"
    inventory_path = output_dir / "inventory.json"
    loadout_path = output_dir / "loadout.json"
    base_components_path = output_dir / "base_stats_components.json"
    inventory_components_path = output_dir / "inventory_components.json"
    run_stats_path = output_dir / "run_stats.json"
    ids_raw_index_path = output_dir / "ids_raw_index.json"
    compiled_stat_inputs_path = output_dir / "compiled_stat_inputs.json"
    stat_engine_path = output_dir / "stat_engine.json"
    resolved_problem_spec_path = output_dir / "resolved_problem_spec.json"
    max_wave_path = output_dir / "max_wave.json"
    stage_1_path = output_dir / "stage_1_base_no_respec.json"
    stage_2_path = output_dir / "stage_2_base_with_respec.json"
    stage_3_path = output_dir / "stage_3_with_loadout.json"
    stage_4_path = output_dir / "stage_4_with_battle_conditions.json"
    stage_5_path = output_dir / "stage_5_end_of_run.json"

    previous = _read_json(snapshot_path)
    snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    summary_path.write_text(json.dumps(_build_summary(payload), indent=2, sort_keys=True))
    base_stats_path.write_text(
        json.dumps(payload.get("base_stats", []), indent=2, sort_keys=True)
    )
    inventory_path.write_text(
        json.dumps(payload.get("inventory", {}), indent=2, sort_keys=True)
    )
    loadout_path.write_text(
        json.dumps(payload.get("loadout", {}), indent=2, sort_keys=True)
    )
    snapshot = payload.get("snapshot", {})
    base_components_path.write_text(
        json.dumps(_build_base_stats_components(snapshot), indent=2, sort_keys=True)
    )
    inventory_components_path.write_text(
        json.dumps(_build_inventory_components(snapshot), indent=2, sort_keys=True)
    )
    run_stats_path.write_text(json.dumps(_build_run_stats_report(payload), indent=2, sort_keys=True))
    pipeline = payload.get("pipeline", {})
    ids_raw_index_path.write_text(
        json.dumps(pipeline.get("ids_raw_index", {}), indent=2, sort_keys=True)
    )
    compiled_stat_inputs_path.write_text(
        json.dumps(pipeline.get("compiled_stat_inputs", {}), indent=2, sort_keys=True)
    )
    stat_engine_path.write_text(
        json.dumps(pipeline.get("stat_engine", {}), indent=2, sort_keys=True)
    )

    resolved_spec = _default_problem_spec() if args.problem_spec is None else load_problem_spec(args.problem_spec)
    resolved_problem_spec_path.write_text(
        json.dumps(_to_jsonable(asdict(resolved_spec)), indent=2, sort_keys=True)
    )
    max_wave_path.write_text(
        json.dumps(pipeline.get("max_wave", {}), indent=2, sort_keys=True)
    )

    staged_outputs = payload.get("staged_outputs", {})
    stage_1_path.write_text(
        json.dumps(staged_outputs.get("stage_1_base_no_respec", {}), indent=2, sort_keys=True)
    )
    stage_2_path.write_text(
        json.dumps(staged_outputs.get("stage_2_base_with_respec", {}), indent=2, sort_keys=True)
    )
    stage_3_path.write_text(
        json.dumps(staged_outputs.get("stage_3_with_loadout", {}), indent=2, sort_keys=True)
    )
    stage_4_path.write_text(
        json.dumps(staged_outputs.get("stage_4_with_battle_conditions", {}), indent=2, sort_keys=True)
    )
    stage_5_path.write_text(
        json.dumps(staged_outputs.get("stage_5_end_of_run", {}), indent=2, sort_keys=True)
    )
    if previous is not None:
        diff_path.write_text(
            json.dumps(_build_diff(previous, payload), indent=2, sort_keys=True)
        )
    print(f"Wrote {snapshot_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {base_stats_path}")
    print(f"Wrote {inventory_path}")
    print(f"Wrote {loadout_path}")
    print(f"Wrote {base_components_path}")
    print(f"Wrote {inventory_components_path}")
    print(f"Wrote {run_stats_path}")
    print(f"Wrote {ids_raw_index_path}")
    print(f"Wrote {compiled_stat_inputs_path}")
    print(f"Wrote {stat_engine_path}")
    print(f"Wrote {resolved_problem_spec_path}")
    print(f"Wrote {max_wave_path}")
    print(f"Wrote {stage_1_path}")
    print(f"Wrote {stage_2_path}")
    print(f"Wrote {stage_3_path}")
    print(f"Wrote {stage_4_path}")
    print(f"Wrote {stage_5_path}")
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
