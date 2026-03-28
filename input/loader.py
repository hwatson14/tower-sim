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

from input.ids_parser import parse_ids
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


# ===========================================================================
# T12 migrated: perk-config resolution (moved from run_stats.py)
# ===========================================================================
import csv
import json as _loader_json



def _loader_relpath_str(path_like) -> str:
    p = Path(path_like)
    try:
        return str(p.resolve().relative_to(_ROOT))
    except Exception:
        try:
            return str(p.relative_to(_ROOT))
        except Exception:
            return str(p)

def _perk_config_has_active_preset(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    active = config.get('active_perk_preset')
    presets = config.get('perk_presets') or {}
    return bool(active) and active in presets and bool(presets.get(active))



_PERK_MAX_POLICY_PATH = MANUAL_INPUTS_PATH


def _load_perk_entity_registry() -> list[dict]:
    path = _ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


def _default_tradeoff_alias_map() -> dict[str, str]:
    return {
        "TO1": "x1.50 Tower Damage, but Bosses Have 8x Health",
        "TO2": "x1.80 coins, but Tower Max Health -70%",
        "TO3": "Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%",
        "TO4": "Enemies Damage -50%, but Tower Damage -50%",
        "TO5": "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3",
        "TO6": "Enemies Speed -40%, But Enemies Damage x2.5",
        "TO7": "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash",
        "TO8": "Tower Health Regen x8.00, But Tower Max Max Health -60%",
        "TO9": "Boss Health -70%, But Boss Speed +50%",
        "TO10": "Lifesteal x2.50, But Knockback force -70%",
    }


def _resolve_policy_banned_perk_names(raw_policy: dict) -> list[str]:
    alias_map = _default_tradeoff_alias_map()
    ordered: list[str] = []
    seen: set[str] = set()
    for alias in list(raw_policy.get("banned_perk_aliases", []) or []):
        key = str(alias).strip().upper()
        name = alias_map.get(key)
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in list(raw_policy.get("banned_perks", []) or []):
        perk_name = str(name).strip()
        if perk_name and perk_name not in seen:
            ordered.append(perk_name)
            seen.add(perk_name)
    return ordered


def _ids_player_value(ids_raw, name: str, default: int = 0) -> int:
    rows = ids_raw.raw_sections.get('Player & Stuff', []) if ids_raw else []
    for row in rows:
        if row and str(row[0]).strip() == name:
            token = str(row[1]).strip() if len(row) > 1 else ''
            try:
                return int(float(token.replace(',', '')))
            except Exception:
                return default
    return default


def _build_generated_max_progression_perk_config(ids_raw, primary_config: dict | None = None, *, default_policy_path: Path = _PERK_MAX_POLICY_PATH, diag_output_dir: 'Path | None' = None) -> tuple[dict, dict]:
    from simulators.perk_timeline_generator import generate_timeline, perk_state_at_wave

    primary_config = primary_config or {}
    policy_seed = 42
    target_wave = 50000
    priority_order = []
    first_perk_choice = None
    policy_notes = []
    raw_policy = {}
    policy_banned_names: list[str] = []
    if default_policy_path.exists():
        try:
            _text = default_policy_path.read_text(encoding='utf-8')
            if default_policy_path.suffix in ('.yaml', '.yml'):
                raw_policy = (yaml.safe_load(_text) or {}).get('perk_policy') or {}
            else:
                raw_policy = json.loads(_text)
            policy_seed = int(raw_policy.get('seed', policy_seed))
            target_wave = int(raw_policy.get('target_wave', target_wave))
            priority_order = list(raw_policy.get('priority_order', []) or [])
            first_perk_choice = raw_policy.get('first_perk_choice')
            policy_banned_names = _resolve_policy_banned_perk_names(raw_policy)
            if raw_policy.get('notes'):
                policy_notes.append(str(raw_policy.get('notes')))
        except Exception as exc:
            policy_notes.append(f'Failed to parse policy file {_loader_relpath_str(default_policy_path)}: {exc}')

    banned_ids = list(primary_config.get('banned_perk_ids') or [])

    entities = _load_perk_entity_registry()
    by_id = {row.get('perk_id'): row for row in entities if row.get('perk_id')}
    by_name = {row.get('perk_name'): row for row in entities if row.get('perk_name')}
    primary_banned_names = [by_id[perk_id]['perk_name'] for perk_id in banned_ids if perk_id in by_id and by_id[perk_id].get('perk_name')]
    banned_names = list(primary_banned_names or policy_banned_names)
    if not banned_ids and banned_names:
        banned_ids = [row.get('perk_id') for row in entities if row.get('perk_name') in set(banned_names) and row.get('perk_id')]

    lab_rows = ids_raw.raw_sections.get('Labs', []) if ids_raw else []
    labs = {}
    for row in lab_rows:
        if row and str(row[0]).strip():
            try:
                labs[str(row[0]).strip()] = int(float(str(row[1]).strip().replace(',', '')))
            except Exception:
                pass

    standard_perk_bonus_level = labs.get('Standard Perks Bonus', 0)
    ids_ban_capacity = _ids_player_value(ids_raw, 'Ban Perks', 0)
    effective_ban_capacity = max(ids_ban_capacity, len(banned_names))
    policy_payload = {
        'seed': policy_seed,
        'target_wave': target_wave,
        'waves_required_lab': int(labs.get('Waves Required', 0) or 0),
        'standard_perk_bonus': float(standard_perk_bonus_level) / 100.0,
        'perk_option_quantity': _ids_player_value(ids_raw, 'Perk Option Quantity', 0),
        'ban_perks_capacity': effective_ban_capacity,
        'banned_perks': banned_names,
        'priority_order': priority_order,
        'first_perk_choice': first_perk_choice,
    }
    (_ROOT / 'input' / 'derived').mkdir(parents=True, exist_ok=True)
    policy_runtime_path = _ROOT / 'input' / 'derived' / 'perks_derived.json'
    policy_runtime_path.write_text(json.dumps(policy_payload, indent=2), encoding='utf-8')
    timeline, diag = generate_timeline(policy_runtime_path)
    taken_counts = perk_state_at_wave(timeline, policy_payload['target_wave'])
    selections = []
    unknown_names = []
    for perk_name, picks in sorted(taken_counts.items()):
        meta = by_name.get(perk_name)
        if not meta or not meta.get('perk_id'):
            unknown_names.append(perk_name)
            continue
        selections.append({'perk_id': meta['perk_id'], 'picks': int(picks)})
    generated = {
        'preset_namespace_class': 'transient',
        'perk_presets': {
            'ProjectedMax_AllAllowedExceptBanned': selections,
        },
        'active_perk_preset': 'ProjectedMax_AllAllowedExceptBanned',
        'banned_perk_ids': banned_ids,
        'notes': 'Generated from perk timeline policy + IDS-backed perk controls; this preset is authoritative for max_progression when primary perk config has no active preset.',
        'generator': {
            'policy_file': _loader_relpath_str(default_policy_path),
            'runtime_policy_file': _loader_relpath_str(policy_runtime_path),
            'waves_required_lab': policy_payload['waves_required_lab'],
            'standard_perk_bonus_level': standard_perk_bonus_level,
            'perk_option_quantity': policy_payload['perk_option_quantity'],
            'ban_perks_capacity_ids': ids_ban_capacity,
            'ban_perks_capacity_effective': policy_payload['ban_perks_capacity'],
            'target_wave': policy_payload['target_wave'],
            'seed': policy_payload['seed'],
            'priority_order': priority_order,
            'first_perk_choice': first_perk_choice,
            'banned_perks_effective': banned_names,
            'banned_perk_aliases': list(raw_policy.get('banned_perk_aliases', []) or []),
            'unknown_generated_perk_names': unknown_names,
        }
    }
    if diag_output_dir is not None:
        diag_output_dir.mkdir(parents=True, exist_ok=True)
        (diag_output_dir / 'perk_timeline.json').write_text(json.dumps(timeline, indent=2), encoding='utf-8')
        (diag_output_dir / 'perk_final_state.json').write_text(json.dumps({'target_wave': policy_payload['target_wave'], 'taken_counts': taken_counts}, indent=2), encoding='utf-8')
        (diag_output_dir / 'perk_generation_diagnostics.json').write_text(json.dumps(diag, indent=2), encoding='utf-8')
    metadata = {
        'requested_perks_path': 'manual_inputs.yaml:perk_config',
        'resolved_perks_path': str(policy_runtime_path),
        'fallback_applied': True,
        'fallback_reason': 'max_progression_generated_from_timeline_policy',
        'generation_policy_path': str(default_policy_path),
        'generated_runtime_policy_path': str(policy_runtime_path),
    }
    if diag_output_dir is not None:
        metadata['generated_timeline_path'] = str(diag_output_dir / 'perk_timeline.json')
        metadata['generated_diagnostics_path'] = str(diag_output_dir / 'perk_generation_diagnostics.json')
    return generated, metadata

def _resolve_perk_config(path_or_cfg, state_mode: str, ids_raw=None, diag_output_dir=None) -> tuple[dict, dict]:
    # Accepts a dict (from input/loader.py perk_config) or a Path (legacy callers).
    if isinstance(path_or_cfg, dict):
        primary = path_or_cfg
        _src = 'manual_inputs.yaml:perk_config'
    else:
        primary = _load_json_optional(path_or_cfg)
        _src = str(path_or_cfg)
    metadata = {
        'requested_perks_path': _src,
        'resolved_perks_path': _src,
        'fallback_applied': False,
        'fallback_reason': None,
    }
    if state_mode == 'max_progression' and not _perk_config_has_active_preset(primary):
        try:
            generated, gen_meta = _build_generated_max_progression_perk_config(
                ids_raw, primary, diag_output_dir=diag_output_dir,
            )
            return generated, gen_meta
        except Exception as exc:
            metadata['generation_error'] = str(exc)
            metadata['fallback_reason'] = 'max_progression_generation_failed_returning_empty_perk_config'
    return primary, metadata
