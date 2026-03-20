"""v3 mechanics activation staging.

Step-5 scope: declare ordered domain activation requirements and validate they
map to canonical KB tables/contracts while preserving manifest-governed runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from v3.kb_access import read_text


class V3MechanicsActivationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DomainActivation:
    domain: str
    enabled: bool
    required_surfaces: tuple[str, ...]


_DOMAIN_ORDER = (
    "workshop",
    "labs",
    "cards",
    "modules",
    "ultimate-weapons",
    "bots",
    "perks",
    "combat",
    "enemies",
)

_REQUIRED_SURFACES: dict[str, tuple[str, ...]] = {
    "workshop": (
        "kb/workshop/tables/wiki-verified-damage-cost-snapshot.csv",
        "kb/workshop/contracts/workshop-runtime-contract.md",
    ),
    "labs": (
        "kb/labs/tables/lab-application-registry.csv",
        "kb/labs/contracts/lab-runtime-application-contract.md",
    ),
    "cards": (
        "kb/cards/tables/card-effect-registry.csv",
        "kb/cards/contracts/card-runtime-contract.md",
    ),
    "modules": (
        "kb/modules/tables/module-main-effect-total-multipliers-package-canon.csv",
        "kb/modules/tables/module-substats.csv",
    ),
    "ultimate-weapons": (
        "kb/ultimate-weapons/tables/ultimate-weapon-track-ladders.csv",
        "kb/ultimate-weapons/contracts/ultimate-weapon-runtime-contract.md",
    ),
    "bots": (
        "kb/bots/tables/bot-upgrade-tracks-long.csv",
        "kb/bots/contracts/bot-runtime-contract.md",
    ),
    "perks": (
        "kb/perks/tables/perks.csv",
        "kb/perks/contracts/perk-runtime-contract.md",
    ),
    "combat": (
        "kb/combat/tables/wiki-verified-core-combat-formulas.csv",
        "kb/combat/contracts/towersim-mechanics-runtime-corrected.md",
    ),
    "enemies": (
        "kb/enemies/tables/enemy-health-table.csv",
        "kb/enemies/contracts/enemy-runtime-contract.md",
    ),
}


def _load_manifest() -> dict:
    manifest_path = Path("mechanics/manifest.yaml")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise V3MechanicsActivationError("mechanics/manifest.yaml invalid.")
    return data


def _validate_manifest() -> None:
    manifest = _load_manifest()
    active_pack = str(manifest.get("active_pack", "")).strip()
    packs = manifest.get("packs")
    if active_pack == "":
        raise V3MechanicsActivationError("manifest_missing_active_pack")
    if not isinstance(packs, dict) or active_pack not in packs:
        raise V3MechanicsActivationError(f"manifest_active_pack_missing:{active_pack}")


def _validate_surface_path(rel_path: str) -> None:
    norm = rel_path.replace("\\", "/")
    if "/notes/" in norm or "/sources/" in norm or "/derived/" in norm:
        raise V3MechanicsActivationError(f"noncanonical_surface:{rel_path}")
    if "/tables/" not in norm and "/contracts/" not in norm:
        raise V3MechanicsActivationError(f"unsupported_surface_role:{rel_path}")
    read_text(rel_path)


def build_domain_activation_plan() -> list[DomainActivation]:
    _validate_manifest()
    plan: list[DomainActivation] = []
    for idx, domain in enumerate(_DOMAIN_ORDER):
        surfaces = _REQUIRED_SURFACES[domain]
        for surface in surfaces:
            _validate_surface_path(surface)
        plan.append(
            DomainActivation(
                domain=domain,
                enabled=idx == 0,
                required_surfaces=surfaces,
            )
        )
    return plan


def next_disabled_domain() -> str | None:
    for item in build_domain_activation_plan():
        if not item.enabled:
            return item.domain
    return None
