from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .domain import BanState, EffectSpec, ModuleFamily
from .kb_loader import normalise_effect_id

LAB_CATEGORY_REGISTRY = Path("kb/labs/tables/lab-category-registry.csv")

BAN_LAB_BY_FAMILY: dict[ModuleFamily, str] = {
    ModuleFamily.CANNON: "Cannon Effect Bans",
    ModuleFamily.ARMOR: "Armor Effect Bans",
    ModuleFamily.GENERATOR: "Generator Effect Bans",
    ModuleFamily.CORE: "Core Effect Bans",
}


@dataclass(frozen=True)
class BanLabCapacity:
    family: ModuleFamily
    lab_name: str
    level: int
    source: str


@dataclass(frozen=True)
class BanLabWiringResult:
    capacities: dict[ModuleFamily, BanLabCapacity]
    ban_states: dict[ModuleFamily, BanState]
    selected_ban_effect_ids: dict[ModuleFamily, tuple[str, ...]]
    warnings: tuple[str, ...] = ()

    def as_report_dict(self) -> dict[str, Any]:
        return {
            "capacities": {
                family.value: {
                    "lab_name": capacity.lab_name,
                    "level": capacity.level,
                    "source": capacity.source,
                }
                for family, capacity in self.capacities.items()
            },
            "selected_ban_effect_ids": {
                family.value: list(effect_ids)
                for family, effect_ids in self.selected_ban_effect_ids.items()
            },
            "warnings": list(self.warnings),
        }


def load_module_ban_lab_names(repo_root: Path) -> dict[ModuleFamily, str]:
    """Validate and return the source-known module effect-ban lab names."""
    path = repo_root / LAB_CATEGORY_REGISTRY
    if not path.exists():
        raise FileNotFoundError(f"required module ban lab registry not found: {path}")
    registry: dict[str, dict[str, str]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            registry[row["raw_lab_name"]] = row

    resolved: dict[ModuleFamily, str] = {}
    for family, lab_name in BAN_LAB_BY_FAMILY.items():
        row = registry.get(lab_name)
        if row is None:
            raise ValueError(f"module ban lab missing from lab category registry: {lab_name}")
        if row.get("category_ui") != "modules" or row.get("category_detail") != "module":
            raise ValueError(f"module ban lab has unexpected registry ownership: {lab_name} -> {row!r}")
        resolved[family] = lab_name
    return resolved


def _coerce_lab_level(value: Any, lab_name: str) -> int:
    if value is None or value == "":
        return 0
    try:
        level = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"module ban lab {lab_name!r} has non-integer level {value!r}") from exc
    if level < 0:
        raise ValueError(f"module ban lab {lab_name!r} has negative level {level}")
    return level


def ban_lab_capacities_from_labs(
    labs: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    source: str = "labs",
) -> dict[ModuleFamily, BanLabCapacity]:
    lab_names = load_module_ban_lab_names(repo_root) if repo_root is not None else BAN_LAB_BY_FAMILY
    capacities: dict[ModuleFamily, BanLabCapacity] = {}
    for family, lab_name in lab_names.items():
        capacities[family] = BanLabCapacity(
            family=family,
            lab_name=lab_name,
            level=_coerce_lab_level(labs.get(lab_name), lab_name),
            source=source,
        )
    return capacities


def ban_lab_capacities_from_account_state(
    account_state_payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[ModuleFamily, BanLabCapacity]:
    labs = account_state_payload.get("labs")
    if not isinstance(labs, Mapping):
        raise ValueError("account state payload must contain a mapping at key 'labs'")
    return ban_lab_capacities_from_labs(labs, repo_root=repo_root, source="account_state.labs")


def _normalise_selected_effect(effect: str, effect_specs: Mapping[str, EffectSpec]) -> str:
    raw = str(effect).strip()
    if raw in effect_specs:
        return raw
    effect_id = normalise_effect_id(raw)
    if effect_id in effect_specs:
        return effect_id
    by_display = {normalise_effect_id(spec.display_name): spec.effect_id for spec in effect_specs.values()}
    if effect_id in by_display:
        return by_display[effect_id]
    raise ValueError(f"selected banned effect {effect!r} is not in this module family effect pool")


def _selected_for_family(selected_bans: Mapping[str, Sequence[str]], family: ModuleFamily) -> Sequence[str]:
    return selected_bans.get(family.value) or selected_bans.get(family.name) or selected_bans.get(family.value.lower()) or ()


def build_ban_lab_wiring(
    capacities: Mapping[ModuleFamily, BanLabCapacity],
    selected_bans: Mapping[str, Sequence[str]],
    effect_specs_by_family: Mapping[ModuleFamily, Mapping[str, EffectSpec]],
) -> BanLabWiringResult:
    ban_states: dict[ModuleFamily, BanState] = {}
    selected_by_family: dict[ModuleFamily, tuple[str, ...]] = {}
    warnings: list[str] = []
    for family in ModuleFamily:
        family_specs = effect_specs_by_family.get(family, {})
        selected = tuple(_normalise_selected_effect(effect, family_specs) for effect in _selected_for_family(selected_bans, family))
        unique_selected = tuple(dict.fromkeys(selected))
        if len(unique_selected) != len(selected):
            warnings.append(f"Duplicate selected bans were de-duplicated for {family.value}.")
        capacity = capacities.get(family, BanLabCapacity(family, BAN_LAB_BY_FAMILY[family], 0, "missing"))
        if len(unique_selected) > capacity.level:
            raise ValueError(
                f"{family.value} selected bans exceed {capacity.lab_name} capacity: "
                f"{len(unique_selected)} selected > {capacity.level} available"
            )
        selected_by_family[family] = unique_selected
        ban_states[family] = BanState(family=family, banned_effect_ids=frozenset(unique_selected))
    return BanLabWiringResult(
        capacities=dict(capacities),
        ban_states=ban_states,
        selected_ban_effect_ids=selected_by_family,
        warnings=tuple(warnings),
    )
