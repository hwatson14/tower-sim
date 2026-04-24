"""
input/loader.py — Loads and validates all inputs.

Owns: loading manual_inputs.yaml, loading imports/ (IDS CSV, EP export, progress),
loading derived/perks_derived.json, returning a validated InputBundle.

Must not own: QE logic, simulation, scoring, recommendations.

Extracted from: run_stats.py (_load_json_config, input path constants),
compilers/account_state_compiler.py (account-state assembly entry).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from input.ids_parser import parse_ids
from input.ids_parser import IdsRaw

# ── Default paths (relative to repo root) ─────────────────────────────────────

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent

MANUAL_INPUTS_PATH = _HERE / "manual_inputs.yaml"
PERKS_DERIVED_PATH = _HERE / "derived" / "perks_derived.json"
IDS_CSV_PATH = _HERE / "imports" / "ids.csv"
EP_EXPORT_CSV_PATH = _HERE / "imports" / "ep_export.csv"
PROGRESS_CSV_PATH = _HERE / "imports" / "progress.csv"
MANIFEST_PATH = _HERE / "imports" / "manifest.json"
_YAML_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
_YAML_DUMPER = getattr(yaml, 'CSafeDumper', yaml.SafeDumper)


# ── InputBundle ───────────────────────────────────────────────────────────────

@dataclass
class InputBundle:
    """
    Validated bundle of all runtime inputs.

    Downstream layers (qe/, simulators/) receive this bundle rather than
    reading individual files directly.
    """
    ids_raw: IdsRaw
    manual_inputs: dict
    loadout_config: dict
    perk_config: dict
    perk_policy: dict
    manual_advisory_inputs: dict
    perks_derived: dict
    ep_export_path: Path
    progress_csv_path: Path
    manifest: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json_optional(path: Path) -> dict:
    """Load an optional JSON file; return {} if missing, invalid, or not a dict."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_yaml_optional(path: Path) -> dict:
    """Load an optional YAML file; return {} if missing, invalid, or not a dict."""
    if not path.exists():
        return {}
    try:
        data = yaml.load(path.read_text(encoding='utf-8'), Loader=_YAML_LOADER)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_json_required(path: Path, *, context: str) -> dict:
    """Load a required JSON file and enforce top-level dict payload."""
    if not path.exists():
        raise FileNotFoundError(f"{context}: required file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(f"{context}: failed to parse JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"{context}: expected top-level JSON object (dict) at {path}, got {type(data).__name__}"
        )
    return data


def _load_yaml_required(path: Path, *, context: str) -> dict:
    """Load a required YAML file and enforce top-level dict payload."""
    if not path.exists():
        raise FileNotFoundError(f"{context}: required file not found: {path}")
    try:
        data = yaml.load(path.read_text(encoding='utf-8'), Loader=_YAML_LOADER)
    except Exception as exc:
        raise ValueError(f"{context}: failed to parse YAML at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"{context}: expected top-level YAML mapping (dict) at {path}, got {type(data).__name__}"
        )
    return data


def parse_perk_policy(manual_inputs: dict) -> dict:
    """Extract the input-owned manual perk policy surface."""
    policy = manual_inputs.get("perk_policy") or {}
    return policy if isinstance(policy, dict) else {}


def write_perk_policy(perk_policy: dict, *, manual_inputs_path: Optional[Path] = None) -> dict:
    """Persist the input-owned perk policy surface into manual_inputs.yaml."""
    if not isinstance(perk_policy, dict):
        raise ValueError(f"perk_policy must be a mapping, got {type(perk_policy).__name__}")
    manual_inputs_path = manual_inputs_path or MANUAL_INPUTS_PATH
    manual_inputs = _load_yaml_required(manual_inputs_path, context="manual_inputs")
    manual_inputs["perk_policy"] = dict(perk_policy)
    manual_inputs_path.write_text(
        yaml.dump(
            manual_inputs,
            Dumper=_YAML_DUMPER,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    return parse_perk_policy(manual_inputs)


def parse_manual_advisory_inputs(manual_inputs: dict) -> dict[str, dict]:
    """Extract manual advisory inputs into a stable input-owned keyed map."""
    payload = manual_inputs.get("manual_advisory_inputs") or {}
    if not isinstance(payload, dict):
        return {}

    rows = payload.get("inputs", [])
    out: dict[str, dict] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("input_id"), str):
                out[row["input_id"]] = dict(row)

    module_missions = payload.get("module", {}).get("missions", {}).get("per_week")
    if "module.missions.per_week" not in out and isinstance(module_missions, (int, float)):
        out["module.missions.per_week"] = {
            "input_id": "module.missions.per_week",
            "value": float(module_missions),
            "is_set": True,
            "trust_label": "policy_heuristic",
            "consumer_scope": ["optimizer", "advisor"],
            "input_kind": "accepted_model_override",
        }
    return out


# ── Public API ────────────────────────────────────────────────────────────────

def load_inputs(
    *,
    ids_path: Optional[Path] = None,
    manual_inputs_path: Optional[Path] = None,
    perks_derived_path: Optional[Path] = None,
) -> InputBundle:
    """
    Load all runtime inputs and return a validated InputBundle.

    Uses default paths from input/ unless overrides are provided.
    Raises ValueError or FileNotFoundError on critical missing inputs.
    Perk config is loaded from manual_inputs.yaml['perk_config'] (single manual input surface).
    """
    ids_path = ids_path or IDS_CSV_PATH
    manual_inputs_path = manual_inputs_path or MANUAL_INPUTS_PATH
    perks_derived_path = perks_derived_path or PERKS_DERIVED_PATH

    if not ids_path.exists():
        raise FileNotFoundError(f"IDS CSV not found: {ids_path}")

    ids_raw = parse_ids(ids_path)

    manual_inputs = _load_yaml_required(manual_inputs_path, context="manual_inputs")
    loadout_config = manual_inputs.get("loadout") or {}
    perk_config = manual_inputs.get("perk_config") or {}
    perk_policy = parse_perk_policy(manual_inputs)
    manual_advisory_inputs = parse_manual_advisory_inputs(manual_inputs)
    perks_derived = _load_json_required(perks_derived_path, context="perks_derived")
    manifest = _load_json_optional(MANIFEST_PATH)

    return InputBundle(
        ids_raw=ids_raw,
        manual_inputs=manual_inputs,
        loadout_config=loadout_config,
        perk_config=perk_config,
        perk_policy=perk_policy,
        manual_advisory_inputs=manual_advisory_inputs,
        perks_derived=perks_derived,
        ep_export_path=EP_EXPORT_CSV_PATH,
        progress_csv_path=PROGRESS_CSV_PATH,
        manifest=manifest,
    )
