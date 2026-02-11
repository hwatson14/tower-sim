from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence, Tuple

import yaml

from tower_sim.engines.stat_input_compiler import _UW_TRACK_SPECS, _WORKSHOP_STAT_SPECS
from tower_sim.libs.bots_lib import load_bot_upgrades
from tower_sim.libs.modules_library import SUBSTATS_BY_SLOT, UNIQUE_EFFECTS
from tower_sim.registry.combat_stat_contract import required_combat_stat_ids
from tower_sim.registry.stat_registry import default_registry


# Provenance:
# - Canonical stat IDs/display names: `tower_sim/registry/stat_registry.py`.
# - Workshop + UW track names: `tower_sim/engines/stat_input_compiler.py`.
# - Cards/Labs/UWs aliases: `tables/meta/registry/catalog.yaml`.
# - Module names + substats: `tower_sim/libs/modules_library.py`.
# - Bot names + attributes: `tables/inputs/.../bot_upgrades.csv` via
#   `tower_sim/libs/bots_lib.py`.

_EXPLICIT_STAT_ALIAS_TO_ID: Dict[str, str] = {
    "hp": "tower_hp",
    "tower health": "tower_hp",
    "health": "tower_hp",
    "hpregen": "tower_regen",
    "tower health regen": "tower_regen",
    "defence %": "def_pct",
    "defense": "def_pct",
    "wall hp": "wall_hp",
    "thorn damage": "thorns_damage_mult",
    "thorns": "thorns_damage_mult",
}


_EXPLICIT_ENTITY_ALIASES: Dict[str, Dict[str, str]] = {
    "cards": {
        "extra orb": "CARD_EXTRA_ORBS",
        "plasma canon": "CARD_PLASMA_CANNON",
    },
    "workshop": {
        "land mine chance": "Land Mine Chance",
        "land mine radius": "Land Mine Radius",
        "orb speed": "Orb Speed",
        "orbs": "Orbs",
        "package chance": "Package Chance",
        "wall rebuild": "Wall Rebuild",
    },
    "module_substats": {
        "critical factor": "Crit Factor",
        "defense %": "Defense",
        "package chance": "Recovery Package Chance",
    },
}


# Disallowed duplicate canonicals retained here to fail-closed on semantic drift.
# These names must resolve via aliases on the canonical entries instead.
_DISALLOWED_CANONICAL_IDS: Dict[str, str] = {
    "LAB_BLACK_HOLE_COIN_BONUS": "Use LAB_BLACK_HOLE_COINS_BONUS with alias 'Black Hole Coin Bonus'.",
    "LAB_COINS_WAVE": "Use LAB_COINS_PER_WAVE with alias 'Coins / Wave'.",
    "LAB_DAMAGE_METER": "Use LAB_DAMAGE_PER_METER with alias 'Damage / Meter'.",
    "LAB_DEATH_WAVE_CELLS_BONUS": "Use LAB_DEATH_WAVE_CELL_BONUS with alias 'Death Wave Cells Bonus'.",
    "LAB_MISSILE_DESPAWN_TIME": "Use LAB_MISSILES_DESPAWN_TIME with alias 'Missile Despawn Time'.",
    "LAB_MISSILE_RADIUS": "Use LAB_MISSILES_RADIUS with alias 'Missile Radius'.",
    "LAB_AMP_BOT_COOLDOWN": "Use LAB_AMPLIFY_BOT_COOLDOWN with alias 'Amp Bot - Cooldown'.",
    "LAB_AMP_BOT_DURATION": "Use LAB_AMPLIFY_BOT_DURATION with alias 'Amp Bot - Duration'.",
}


def normalize_identifier(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


@lru_cache(maxsize=1)
def _catalog_yaml() -> dict:
    path = Path("tables/meta/registry/catalog.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Naming catalog YAML must be a mapping.")
    categories = data.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Naming catalog YAML missing categories mapping.")
    return data


def _validate_catalog_category_entries(entries: list, *, category_key: str) -> None:
    seen_canonical_ids: Dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"Catalog entry for {category_key!r} must be a mapping")
        canonical_id = str(entry.get("canonical_id", "")).strip()
        primary_name = str(entry.get("primary_name", "")).strip()
        aliases = entry.get("aliases")
        if not canonical_id or not primary_name:
            raise ValueError(f"Catalog {category_key!r} entry missing canonical_id/primary_name")
        if not isinstance(aliases, list):
            raise ValueError(f"Catalog {category_key!r} entry {canonical_id!r} missing aliases list")
        previous = seen_canonical_ids.get(canonical_id)
        if previous is not None:
            raise ValueError(
                f"Catalog {category_key!r} canonical_id {canonical_id!r} is duplicated"
            )
        seen_canonical_ids[canonical_id] = primary_name


def validate_catalog_contract() -> Tuple[str, ...]:
    errors: list[str] = []
    catalog = _catalog_yaml()
    categories = catalog.get("categories", {})
    if not isinstance(categories, dict):
        return ("catalog_missing_categories",)

    seen_global_ids: Dict[str, str] = {}
    for category_key, entries in categories.items():
        if not isinstance(entries, list):
            errors.append(f"catalog_category_not_list:{category_key}")
            continue
        normalized_primary_to_id: Dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"catalog_entry_not_mapping:{category_key}")
                continue
            canonical_id = str(entry.get("canonical_id", "")).strip()
            primary_name = str(entry.get("primary_name", "")).strip()
            aliases = entry.get("aliases")
            if not canonical_id or not primary_name:
                errors.append(f"catalog_missing_required_fields:{category_key}")
                continue
            if not isinstance(aliases, list):
                errors.append(f"catalog_aliases_not_list:{category_key}:{canonical_id}")
            owner = seen_global_ids.get(canonical_id)
            if owner is not None and owner != category_key:
                errors.append(f"catalog_global_id_duplicate:{canonical_id}:{owner}:{category_key}")
            else:
                seen_global_ids[canonical_id] = category_key

            if canonical_id in _DISALLOWED_CANONICAL_IDS:
                errors.append(
                    f"catalog_disallowed_canonical_id:{category_key}:{canonical_id}:{_DISALLOWED_CANONICAL_IDS[canonical_id]}"
                )

            normalized_primary = normalize_identifier(primary_name)
            prior = normalized_primary_to_id.get(normalized_primary)
            if prior is not None and prior != canonical_id:
                errors.append(
                    f"catalog_normalized_primary_collision:{category_key}:{normalized_primary}:{prior}:{canonical_id}"
                )
            else:
                normalized_primary_to_id[normalized_primary] = canonical_id

        try:
            _validate_catalog_category_entries(entries, category_key=str(category_key))
        except ValueError as exc:
            errors.append(f"catalog_category_invalid:{category_key}:{exc}")

    return tuple(sorted(set(errors)))


def _register_alias(
    alias_map: MutableMapping[str, str],
    conflicts: MutableMapping[str, set[str]],
    alias: str,
    canonical: str,
) -> None:
    key = normalize_identifier(alias)
    existing = alias_map.get(key)
    if existing is not None and existing != canonical:
        conflicts.setdefault(key, {existing}).add(canonical)
        return
    alias_map[key] = canonical


@lru_cache(maxsize=1)
def _build_stat_alias_map() -> tuple[Dict[str, str], Dict[str, set[str]]]:
    alias_map: Dict[str, str] = {}
    conflicts: Dict[str, set[str]] = {}

    for definition in default_registry().all_defs():
        _register_alias(alias_map, conflicts, definition.stat_id, definition.stat_id)
        _register_alias(alias_map, conflicts, definition.display_name, definition.stat_id)

    for alias, stat_id in _EXPLICIT_STAT_ALIAS_TO_ID.items():
        _register_alias(alias_map, conflicts, alias, stat_id)

    return alias_map, conflicts


@lru_cache(maxsize=1)
def alias_to_stat_id_map() -> Mapping[str, str]:
    alias_map, _ = _build_stat_alias_map()
    return dict(alias_map)


def resolve_stat_id(value: str) -> str:
    alias = normalize_identifier(value)
    stat_id = alias_to_stat_id_map().get(alias)
    if stat_id is None:
        raise KeyError(f"Unmapped IDS/display alias: {value!r}")
    return stat_id


def required_repo_stat_ids() -> Tuple[str, ...]:
    return tuple(sorted(definition.stat_id for definition in default_registry().all_defs()))


def validate_registry_parity(
    registry,
    *,
    required_stat_ids: Sequence[str] | None = None,
) -> Tuple[str, ...]:
    errors = []
    alias_map, _conflicts = _build_stat_alias_map()
    mapped_ids = set(alias_map.values())


    for stat_id in sorted(mapped_ids):
        try:
            registry.validate_stat_id(stat_id)
        except Exception:  # noqa: BLE001
            errors.append(f"mapped_id_missing_in_registry:{stat_id}")

    required_ids = set(required_stat_ids or required_repo_stat_ids())
    for stat_id in sorted(required_ids - mapped_ids):
        errors.append(f"required_id_missing_in_alias_map:{stat_id}")

    return tuple(sorted(errors))


@lru_cache(maxsize=1)
def _build_named_entity_maps() -> tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, set[str]]]]:
    categories: Dict[str, Dict[str, str]] = {
        "workshop": {},
        "cards": {},
        "labs": {},
        "uws": {},
        "uw_tracks": {},
        "modules": {},
        "module_substats": {},
        "bots": {},
        "bot_attributes": {},
    }
    conflicts: Dict[str, Dict[str, set[str]]] = {k: {} for k in categories}

    for workshop_name in _WORKSHOP_STAT_SPECS:
        _register_alias(categories["workshop"], conflicts["workshop"], workshop_name, workshop_name)

    catalog = _catalog_yaml()
    catalog_categories = catalog.get("categories", {}) if isinstance(catalog, dict) else {}
    for category_key, target in (("cards", "cards"), ("labs", "labs"), ("uws", "uws")):
        entries = catalog_categories.get(category_key, [])
        if not isinstance(entries, list):
            raise ValueError(f"Catalog category {category_key!r} must be a list")
        _validate_catalog_category_entries(entries, category_key=category_key)
        for entry in entries:
            canonical_id = str(entry.get("canonical_id", "")).strip()
            primary_name = str(entry.get("primary_name", "")).strip()
            aliases = entry.get("aliases", []) or []
            _register_alias(categories[target], conflicts[target], canonical_id, canonical_id)
            _register_alias(categories[target], conflicts[target], primary_name, canonical_id)
            if not isinstance(aliases, list):
                raise ValueError(f"Catalog aliases for {canonical_id!r} must be list")
            for alias in aliases:
                _register_alias(categories[target], conflicts[target], str(alias), canonical_id)

    for uw_name, tracks in _UW_TRACK_SPECS.items():
        uw_canonical = categories["uws"].get(normalize_identifier(uw_name), uw_name)
        _register_alias(categories["uws"], conflicts["uws"], uw_name, uw_canonical)
        for track_name in tracks:
            canonical_track = f"{uw_name}.{track_name}"
            _register_alias(categories["uw_tracks"], conflicts["uw_tracks"], canonical_track, canonical_track)
            _register_alias(
                categories["uw_tracks"],
                conflicts["uw_tracks"],
                f"{uw_name}:{track_name}",
                canonical_track,
            )

    for module_name in UNIQUE_EFFECTS:
        _register_alias(categories["modules"], conflicts["modules"], module_name, module_name)

    for slot_name, substats in SUBSTATS_BY_SLOT.items():
        _register_alias(categories["module_substats"], conflicts["module_substats"], slot_name, slot_name)
        if not isinstance(substats, dict):
            continue
        for sub_name in substats:
            canonical_sub = str(sub_name)
            _register_alias(
                categories["module_substats"],
                conflicts["module_substats"],
                canonical_sub,
                canonical_sub,
            )
            _register_alias(
                categories["module_substats"],
                conflicts["module_substats"],
                f"{slot_name}:{canonical_sub}",
                canonical_sub,
            )

    for category, aliases in _EXPLICIT_ENTITY_ALIASES.items():
        if category not in categories:
            continue
        for alias, canonical in aliases.items():
            _register_alias(categories[category], conflicts[category], alias, canonical)

    bot_table = load_bot_upgrades()
    for bot_name, attrs in bot_table.items():
        _register_alias(categories["bots"], conflicts["bots"], bot_name, bot_name)
        for attr_name in attrs:
            canonical_attr = f"{bot_name}.{attr_name}"
            _register_alias(
                categories["bot_attributes"],
                conflicts["bot_attributes"],
                canonical_attr,
                canonical_attr,
            )
            _register_alias(
                categories["bot_attributes"],
                conflicts["bot_attributes"],
                f"{bot_name}:{attr_name}",
                canonical_attr,
            )

    return categories, conflicts


@lru_cache(maxsize=1)
def named_entity_alias_maps() -> Mapping[str, Mapping[str, str]]:
    categories, _ = _build_named_entity_maps()
    return {k: dict(v) for k, v in categories.items()}


def resolve_named_entity(category: str, value: str) -> str:
    maps = named_entity_alias_maps()
    if category not in maps:
        raise KeyError(f"Unknown naming category: {category!r}")
    alias = normalize_identifier(value)
    resolved = maps[category].get(alias)
    if resolved is None:
        raise KeyError(f"Unmapped alias for category {category!r}: {value!r}")
    return resolved


def validate_named_entity_coverage() -> Tuple[str, ...]:
    errors = list(validate_catalog_contract())
    maps, conflicts = _build_named_entity_maps()
    for category, alias_map in maps.items():
        if not alias_map:
            errors.append(f"empty_naming_category:{category}")
    for category, category_conflicts in conflicts.items():
        for alias_key, conflict_ids in sorted(category_conflicts.items()):
            errors.append(f"entity_alias_conflict:{category}:{alias_key}:{sorted(conflict_ids)}")
    return tuple(sorted(errors))


def unsupported_or_unmapped_items(items: Iterable[str]) -> Tuple[str, ...]:
    failures = []
    decisive_ids = set(required_combat_stat_ids())
    for item in items:
        if ":" not in item:
            continue
        kind, label = item.split(":", 1)
        if kind not in {"workshop_mapping", "workshop_unsupported"}:
            continue
        try:
            stat_id = resolve_stat_id(label)
        except KeyError:
            workshop_spec = _WORKSHOP_STAT_SPECS.get(label)
            if workshop_spec is None:
                failures.append(f"{kind}:{label}->unmapped")
                continue
            stat_id = workshop_spec.stat_id
        if stat_id in decisive_ids:
            failures.append(f"{kind}:{label}->{stat_id}")
    return tuple(sorted(set(failures)))



def _is_ignored_placeholder_name(value: str) -> bool:
    norm = normalize_identifier(value)
    return norm in {"true", "false", "end of array"} or norm.startswith("any other")


def validate_account_snapshot_naming(
    snapshot,
    *,
    strict_categories: Sequence[str] = (
        "labs",
        "workshop",
        "cards",
        "uws",
        "bots",
        "bot_attributes",
        "modules",
        "module_substats",
    ),
) -> Tuple[str, ...]:
    errors = []
    strict = set(strict_categories)

    if "labs" in strict:
        for name in snapshot.labs:
            if _is_ignored_placeholder_name(name):
                continue
            try:
                resolve_named_entity("labs", name)
            except KeyError:
                errors.append(f"labs_unmapped:{name}")

    if "workshop" in strict:
        for name in snapshot.workshop:
            try:
                resolve_named_entity("workshop", name)
            except KeyError:
                errors.append(f"workshop_unmapped:{name}")

    if "uws" in strict:
        for name in snapshot.ultimate_weapons:
            if _is_ignored_placeholder_name(name):
                continue
            try:
                resolve_named_entity("uws", name)
            except KeyError:
                errors.append(f"uw_unmapped:{name}")

    if "cards" in strict:
        for name in snapshot.cards_inventory:
            try:
                resolve_named_entity("cards", name)
            except KeyError:
                errors.append(f"card_unmapped:{name}")

    if "bots" in strict:
        for name in snapshot.bots:
            try:
                resolve_named_entity("bots", name)
            except KeyError:
                errors.append(f"bot_unmapped:{name}")

    if "bot_attributes" in strict:
        for bot_name, attrs in snapshot.bot_upgrades.items():
            for attr_name in attrs:
                path = f"{bot_name}:{attr_name}"
                try:
                    resolve_named_entity("bot_attributes", path)
                except KeyError:
                    errors.append(f"bot_attribute_unmapped:{path}")

    if "modules" in strict or "module_substats" in strict:
        for module_name, module in snapshot.modules_inventory.items():
            if "modules" in strict:
                if not _is_ignored_placeholder_name(module_name):
                    try:
                        resolve_named_entity("modules", module_name)
                    except KeyError:
                        errors.append(f"module_unmapped:{module_name}")
            if "module_substats" in strict:
                for substat in module.substats:
                    if module.slot_type:
                        qualified = f"{module.slot_type}:{substat.stat_name}"
                        try:
                            resolve_named_entity("module_substats", qualified)
                            continue
                        except KeyError:
                            pass
                    try:
                        resolve_named_entity("module_substats", substat.stat_name)
                    except KeyError:
                        errors.append(
                            f"module_substat_unmapped:{module_name}:{module.slot_type}:{substat.stat_name}"
                        )

    if "modules" in strict:
        for preset, slots in snapshot.module_presets.items():
            for slot_type, selection in slots.items():
                for role, module_name in (("primary", selection.primary), ("assist", selection.assist)):
                    if module_name is None:
                        continue
                    if _is_ignored_placeholder_name(module_name):
                        continue
                    try:
                        resolve_named_entity("modules", module_name)
                    except KeyError:
                        errors.append(f"module_preset_unmapped:{preset}:{slot_type}:{role}:{module_name}")

    return tuple(sorted(set(errors)))


def validate_repo_naming_contract(*, ids_snapshot=None) -> Tuple[str, ...]:
    errors = []
    errors.extend(validate_registry_parity(default_registry()))
    errors.extend(validate_named_entity_coverage())
    if ids_snapshot is not None:
        errors.extend(validate_account_snapshot_naming(ids_snapshot, strict_categories=("labs", "workshop", "cards", "uws", "bots", "bot_attributes", "modules", "module_substats")))
    return tuple(sorted(set(errors)))


__all__ = [
    "alias_to_stat_id_map",
    "named_entity_alias_maps",
    "normalize_identifier",
    "required_repo_stat_ids",
    "resolve_named_entity",
    "resolve_stat_id",
    "unsupported_or_unmapped_items",
    "validate_catalog_contract",
    "validate_account_snapshot_naming",
    "validate_named_entity_coverage",
    "validate_registry_parity",
    "validate_repo_naming_contract",
]
