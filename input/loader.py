"""
input/loader.py — Loads and validates all inputs.

Owns: loading manual_inputs.yaml, loading imports/ (IDS CSV, EP export, progress),
loading derived/perks_derived.json, optional perk-config resolution, returning
a validated InputBundle.

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

from input.parsers import parse_ids
from input.runtime_state import IdsRaw

# ── Default paths (relative to repo root) ─────────────────────────────────────

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent

MANUAL_INPUTS_PATH = _HERE / "manual_inputs.yaml"
PERKS_DERIVED_PATH = _HERE / "derived" / "perks_derived.json"
IDS_CSV_PATH = _HERE / "imports" / "ids.csv"
EP_EXPORT_CSV_PATH = _HERE / "imports" / "ep_export.csv"
PROGRESS_CSV_PATH = _HERE / "imports" / "progress.csv"
MANIFEST_PATH = _HERE / "imports" / "manifest.json"


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
    perks_derived: dict
    ep_export_path: Path
    progress_csv_path: Path
    manifest: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json_optional(path: Path) -> dict:
    """Load a JSON file; return {} if missing or invalid."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_yaml_optional(path: Path) -> dict:
    """Load a YAML file; return {} if missing or invalid."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


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

    manual_inputs = _load_yaml_optional(manual_inputs_path)
    loadout_config = manual_inputs.get("loadout") or {}
    perk_config = manual_inputs.get("perk_config") or {}
    perks_derived = _load_json_optional(perks_derived_path)
    manifest = _load_json_optional(MANIFEST_PATH)

    return InputBundle(
        ids_raw=ids_raw,
        manual_inputs=manual_inputs,
        loadout_config=loadout_config,
        perk_config=perk_config,
        perks_derived=perks_derived,
        ep_export_path=EP_EXPORT_CSV_PATH,
        progress_csv_path=PROGRESS_CSV_PATH,
        manifest=manifest,
    )
