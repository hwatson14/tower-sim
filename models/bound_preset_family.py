from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.preset_contract import normalize_preset_name


@dataclass(frozen=True)
class BoundPresetFamily:
    preset_name: str
    card_preset_name: str
    module_preset_name: str
    perk_preset_name: Optional[str]
    perk_namespace_class: str
    state_mode: str
    perks_enabled: bool


def bind_preset_family(
    *,
    preset_name: str,
    state_mode: str,
    perk_namespace_class: str,
    explicit_card_preset_name: Optional[str],
    explicit_module_preset_name: Optional[str],
    explicit_perk_preset_name: Optional[str],
    active_perk_preset_name: Optional[str],
    perks_enabled: Optional[bool],
) -> BoundPresetFamily:
    canonical_preset = normalize_preset_name(preset_name, allow_aliases=False)
    if canonical_preset is None:
        raise ValueError(f"preset_name must be canonical, got {preset_name!r}.")

    card_preset = _bind_loadout_lane('card_preset_name', explicit_card_preset_name, canonical_preset)
    module_preset = _bind_loadout_lane('module_preset_name', explicit_module_preset_name, canonical_preset)

    perk_preset = explicit_perk_preset_name or active_perk_preset_name
    if perk_preset is not None:
        perk_preset = perk_preset.strip()
        if not perk_preset:
            perk_preset = None

    if perk_namespace_class != 'transient' and perk_preset is not None:
        normalized = normalize_preset_name(perk_preset, allow_aliases=False)
        if normalized is None:
            raise ValueError(f"perk_preset_name must be canonical in canonical flows, got {perk_preset!r}.")
        if normalized != canonical_preset:
            raise ValueError(
                f"perk_preset_name must match bound preset_name in canonical flows "
                f"({canonical_preset!r}), got {normalized!r}."
            )
        perk_preset = normalized

    lane_perks_enabled = bool(perk_preset) if perks_enabled is None else bool(perks_enabled)
    return BoundPresetFamily(
        preset_name=canonical_preset,
        card_preset_name=card_preset,
        module_preset_name=module_preset,
        perk_preset_name=perk_preset,
        perk_namespace_class=perk_namespace_class,
        state_mode=state_mode,
        perks_enabled=lane_perks_enabled,
    )


def _bind_loadout_lane(field_name: str, explicit_value: Optional[str], canonical_preset: str) -> str:
    if explicit_value is None:
        return canonical_preset
    normalized = normalize_preset_name(explicit_value, allow_aliases=False)
    if normalized is None:
        raise ValueError(f"{field_name} must be canonical when explicitly provided, got {explicit_value!r}.")
    if normalized != canonical_preset:
        raise ValueError(
            f"{field_name} must match bound preset_name {canonical_preset!r}, got {normalized!r}."
        )
    return normalized
