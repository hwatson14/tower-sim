from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .domain import EffectSpec, ModuleFamily, Rarity

MODULE_SUBSTATS = Path("kb/modules/tables/module-substats.csv")
RARITY_TABLE = Path("kb/modules/tables/module-submodule-reroll-rarity-wiki-truth.csv")
LOCK_COST_TABLE = Path("kb/modules/tables/module-reroll-lock-costs-wiki-truth.csv")
CONSTANTS_TABLE = Path("kb/modules/tables/module-reroll-constants.csv")
LOCK_COST_CONTRACT = Path("kb/modules/contracts/module-reroll-cost-contract-r61.yaml")
RARITY_POLICY_CONTRACT = Path("kb/modules/contracts/module-submodule-reroll-policy-contract-r66.yaml")
SOURCE_TABLES = (MODULE_SUBSTATS, RARITY_TABLE, LOCK_COST_TABLE, CONSTANTS_TABLE)
SOURCE_CONTRACTS = (LOCK_COST_CONTRACT, RARITY_POLICY_CONTRACT)


@dataclass(frozen=True)
class ModuleRerollSourceBundle:
    effect_specs: dict[ModuleFamily, dict[str, EffectSpec]]
    rarity_probabilities: dict[Rarity, float]
    lock_costs: dict[int, int]
    constants: dict[str, Any]
    source_tables: tuple[Path, ...] = SOURCE_TABLES
    source_contracts: tuple[Path, ...] = SOURCE_CONTRACTS

_PREFIXES = {
    "chrono field": "chrono_field",
    "chain lightning": "chain_lightning",
    "golden tower": "golden_tower",
    "black hole": "black_hole",
    "spotlight": "spotlight",
    "death wave": "death_wave",
}


def _path(repo_root: Path, relative: Path) -> Path:
    path = repo_root / relative
    if not path.exists():
        raise FileNotFoundError(f"required module reroll KB table not found: {path}")
    return path


def normalise_effect_id(display_name: str) -> str:
    raw = display_name.strip()
    lowered = raw.lower().replace("/", " ").replace("%", " percent ")
    lowered = re.sub(r"[()]+", " ", lowered)
    parts = [p.strip() for p in re.split(r"\s+-\s+", lowered, maxsplit=1)]
    if len(parts) == 2 and parts[0] in _PREFIXES:
        prefix = _PREFIXES[parts[0]]
        tail = re.sub(r"[^a-z0-9]+", "_", parts[1]).strip("_")
        return f"{prefix}.{tail}"
    token = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    aliases = {
        "multishot_targets": "multishot.targets",
        "crit_factor": "crit.factor",
        "crit_chance": "crit.chance",
        "super_crit_multi": "super_crit.multi",
        "super_crit_chance": "super_crit.chance",
        "bounce_shot_chance": "bounce_shot.chance",
        "bounce_shot_targets": "bounce_shot.targets",
        "bounce_shot_range": "bounce_shot.range",
        "damage_meter": "damage.meter",
        "attack_speed": "attack_speed",
    }
    return aliases.get(token, token)


def _parse_value(value: str) -> float | int | str | None:
    text = value.strip()
    if text == "":
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    return int(number) if number.is_integer() else number


def load_effect_specs(repo_root: Path) -> dict[ModuleFamily, dict[str, EffectSpec]]:
    rows_by_effect: dict[tuple[ModuleFamily, str], dict[str, Any]] = {}
    with _path(repo_root, MODULE_SUBSTATS).open(newline="") as f:
        for row in csv.DictReader(f):
            family = ModuleFamily.parse(row["slot"])
            effect_id = normalise_effect_id(row["substat"])
            rarity = Rarity.parse(row["rarity"])
            key = (family, effect_id)
            existing = rows_by_effect.setdefault(
                key,
                {
                    "family": family,
                    "effect_id": effect_id,
                    "display_name": row["substat"].strip(),
                    "values_by_rarity": {},
                    "units": row.get("unit") or None,
                    "source_row": dict(row),
                },
            )
            if rarity in existing["values_by_rarity"]:
                raise ValueError(f"duplicate rarity row for {family.value} {effect_id} {rarity.value}")
            existing["values_by_rarity"][rarity] = _parse_value(row["value"])
            if existing["display_name"] != row["substat"].strip():
                raise ValueError(f"duplicate effect id {effect_id!r} maps multiple names in {family.value}")

    by_family = {family: {} for family in ModuleFamily}
    for (_family, _effect_id), data in rows_by_effect.items():
        spec = EffectSpec(**data)
        by_family[spec.family][spec.effect_id] = spec
    return by_family


def load_rarity_probabilities(repo_root: Path) -> dict[Rarity, float]:
    probabilities: dict[Rarity, float] = {}
    with _path(repo_root, RARITY_TABLE).open(newline="") as f:
        for row in csv.DictReader(f):
            rarity = Rarity.parse(row["rarity"])
            probabilities[rarity] = float(row["rate_pct"]) / 100.0
    missing = set(Rarity) - set(probabilities)
    if missing:
        raise ValueError(f"rarity probability table missing: {sorted(r.value for r in missing)}")
    total = sum(probabilities.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"rarity probabilities must sum to 1.0, got {total}")
    return probabilities


def load_lock_costs(repo_root: Path) -> dict[int, int]:
    costs: dict[int, int] = {}
    with _path(repo_root, LOCK_COST_TABLE).open(newline="") as f:
        for row in csv.DictReader(f):
            costs[int(row["lock_count"])] = int(row["cost_per_roll"])
    expected = set(range(max(costs) + 1)) if costs else set()
    missing = expected - set(costs)
    if missing:
        raise ValueError(f"lock cost table missing counts: {sorted(missing)}")
    contract_path = _path(repo_root, LOCK_COST_CONTRACT)
    contract = yaml.safe_load(contract_path.read_text())
    if contract.get("status") != "source_closed":
        raise ValueError(f"module reroll lock cost contract is not source_closed: {contract_path}")
    contract_costs = {int(k): int(v) for k, v in contract.get("exact_lock_costs", {}).items()}
    if costs != contract_costs:
        raise ValueError(
            "module reroll lock cost CSV and source-closed contract disagree: "
            f"csv={costs!r} contract={contract_costs!r}"
        )
    return costs


def load_module_reroll_constants(repo_root: Path) -> dict[str, Any]:
    constants: dict[str, Any] = {}
    with _path(repo_root, CONSTANTS_TABLE).open(newline="") as f:
        for row in csv.DictReader(f):
            value: Any = row["value"]
            if row["value_type"] == "boolean":
                value = value.strip().lower() == "true"
            constants[row["constant_id"]] = {
                "value": value,
                "value_type": row["value_type"],
                "closure_class": row["closure_class"],
                "source_ref": row["source_ref"],
                "notes": row["notes"],
            }
    return constants


def load_module_reroll_source_bundle(repo_root: Path) -> ModuleRerollSourceBundle:
    """Load the approved QE/KB source bundle for the standalone reroll tool."""
    return ModuleRerollSourceBundle(
        effect_specs=load_effect_specs(repo_root),
        rarity_probabilities=load_rarity_probabilities(repo_root),
        lock_costs=load_lock_costs(repo_root),
        constants=load_module_reroll_constants(repo_root),
    )
