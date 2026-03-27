"""naming_contract.py – Programmatic naming contract for TowerSim.

Adapted from the reference archive (tower_sim/registry/naming_contract.py).

Dependency map (archive → current repo):
  tower_sim.registry.stat_registry.default_registry        → engine.stat_resolution_core._load_canonical_stats
  tower_sim.engines.stat_input_compiler._WORKSHOP_STAT_SPECS → engine.query_routing.WORKSHOP_IDS_TO_CONTRIBUTOR
  tower_sim.engines.stat_input_compiler._UW_TRACK_SPECS    → compilers.stat_input_compiler._load_uw_track_order
  tower_sim.libs.bots_lib.load_bot_upgrades                → _load_bot_mechanic_map (derived from mechanic-params.yaml)
  tower_sim.libs.modules_library.UNIQUE_EFFECTS            → _load_module_unique_names (derived from mechanic-params.yaml)
  tower_sim.libs.modules_library.SUBSTATS_BY_SLOT          → models.account_state.SLOT_TYPES (slot keys only; full
                                                             substat maps are DEFERRED – see migration report)
  tower_sim.registry.combat_stat_contract.required_combat_stat_ids → derived from canonical-stats.yaml tower/wall domains
  Catalog path tables/meta/registry/catalog.yaml           → kb/ledgers/sources/raw/repo-meta/registry/catalog.yaml

Semantic taxonomy (state / context / derived):
  state    – player/loadout/current-run-owned quantities.
             Domains: tower, wall.
             Meta-state (economy/progression multipliers): economy_meta.
             Capability flags: account_flag / capability sub-namespace.
  context  – external run/environment/enemy conditions.
             Domains: bc, tier, heat, tournament, enemy, boss (from environment-params.yaml).
  derived  – calculated outputs (eHP, eDamage, eEcon).
             Surfaces composed post-resolution by derived_surface_composer.

See kb/global-rules/contracts/naming-contract.yaml for full grammar.
See kb/ledgers/notes/towersim_static_ledger_naming_contract_v1_10.md for the contributor ledger contract.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence, Tuple

import yaml

from engine.query_routing import WORKSHOP_IDS_TO_CONTRIBUTOR
from compilers.stat_input_compiler import _load_uw_track_order
from engine.stat_resolution_core import _load_canonical_stats
from models.account_state import SLOT_TYPES


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Explicit alias overrides
# ---------------------------------------------------------------------------
# Maps human-readable / legacy aliases to current canonical stat IDs.
# IDs are taken from kb/global-rules/contracts/canonical-stats.yaml.
# Fail-closed: if an alias maps to an ID that is no longer in canonical-stats,
# validate_registry_parity will report it.

_EXPLICIT_STAT_ALIAS_TO_ID: Dict[str, str] = {
    # Tower HP
    "hp":                           "tower_hp",
    "tower health":                 "tower_hp",
    "health":                       "tower_hp",
    # Tower regen
    "hpregen":                      "tower_regen",
    "tower health regen":           "tower_regen",
    # Defence
    "defence %":                    "tower_defense_pct",
    "defense":                      "tower_defense_pct",
    "defense %":                    "tower_defense_pct",
    # Wall
    "wall hp":                      "wall_hp",
    # Thorns  (canonical is tower_thorns_damage_pct in current repo)
    "thorn damage":                 "tower_thorns_damage_pct",
    "thorns":                       "tower_thorns_damage_pct",
    # Recovery / package
    "max amount":                   "max_recovery_multiplier",
    "workshop max amount":          "max_recovery_multiplier",
    # Coin kill – compatibility alias for deprecated id
    "coins per kill":               "coins_per_kill_bonus",
    "coin kill bonus":              "coins_per_kill_bonus",
    # Super-crit normalisation
    "super crit mult":              "tower_supercrit_multiplier",
    "super_crit_mult":              "tower_supercrit_multiplier",
}


# ---------------------------------------------------------------------------
# Explicit entity alias overrides
# ---------------------------------------------------------------------------

_EXPLICIT_ENTITY_ALIASES: Dict[str, Dict[str, str]] = {
    "cards": {
        "extra orb":    "CARD_EXTRA_ORBS",
        "plasma canon": "CARD_PLASMA_CANNON",   # deliberate typo alias from game
    },
    "workshop": {
        "land mine chance":  "Land Mine Chance",
        "land mine radius":  "Land Mine Radius",
        "orb speed":         "Orb Speed",
        "orbs":              "Orbs",
        "package chance":    "Package Chance",
        "wall rebuild":      "Wall Rebuild",
    },
    "module_substats": {
        "critical factor":  "Crit Factor",
        "defense %":        "Defense",
        "package chance":   "Recovery Package Chance",
    },
}


# ---------------------------------------------------------------------------
# Disallowed canonical IDs
# ---------------------------------------------------------------------------
# These names must NOT appear as canonical IDs – use the listed replacement
# with its alias instead.  Retained here to fail-closed on semantic drift.

_DISALLOWED_CANONICAL_IDS: Dict[str, str] = {
    # Labs catalog duplicates (carried forward from reference archive)
    "LAB_BLACK_HOLE_COIN_BONUS":    "Use LAB_BLACK_HOLE_COINS_BONUS with alias 'Black Hole Coin Bonus'.",
    "LAB_COINS_WAVE":               "Use LAB_COINS_PER_WAVE with alias 'Coins / Wave'.",
    "LAB_DAMAGE_METER":             "Use LAB_DAMAGE_PER_METER with alias 'Damage / Meter'.",
    "LAB_DEATH_WAVE_CELLS_BONUS":   "Use LAB_DEATH_WAVE_CELL_BONUS with alias 'Death Wave Cells Bonus'.",
    "LAB_MISSILE_DESPAWN_TIME":     "Use LAB_MISSILES_DESPAWN_TIME with alias 'Missile Despawn Time'.",
    "LAB_MISSILE_RADIUS":           "Use LAB_MISSILES_RADIUS with alias 'Missile Radius'.",
    "LAB_AMP_BOT_COOLDOWN":         "Use LAB_AMPLIFY_BOT_COOLDOWN with alias 'Amp Bot - Cooldown'.",
    "LAB_AMP_BOT_DURATION":         "Use LAB_AMPLIFY_BOT_DURATION with alias 'Amp Bot - Duration'.",
    # Deprecated canonical stat (status: deprecated_transition in canonical-stats.yaml)
    "coin_kill_multiplier":         "Use coins_per_kill_bonus or coin_bonus_multiplier (see canonical-stats.yaml).",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_identifier(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


@lru_cache(maxsize=1)
def _catalog_yaml() -> dict:
    path = (
        _repo_root()
        / "kb"
        / "ledgers"
        / "sources"
        / "raw"
        / "repo-meta"
        / "registry"
        / "catalog.yaml"
    )
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
            raise ValueError(
                f"Catalog {category_key!r} entry {canonical_id!r} missing aliases list"
            )
        if canonical_id in seen_canonical_ids:
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
                errors.append(
                    f"catalog_global_id_duplicate:{canonical_id}:{owner}:{category_key}"
                )
            else:
                seen_global_ids[canonical_id] = category_key

            if canonical_id in _DISALLOWED_CANONICAL_IDS:
                errors.append(
                    f"catalog_disallowed_canonical_id:{category_key}:{canonical_id}"
                    f":{_DISALLOWED_CANONICAL_IDS[canonical_id]}"
                )

            normalized_primary = normalize_identifier(primary_name)
            prior = normalized_primary_to_id.get(normalized_primary)
            if prior is not None and prior != canonical_id:
                errors.append(
                    f"catalog_normalized_primary_collision:{category_key}"
                    f":{normalized_primary}:{prior}:{canonical_id}"
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
    conflicts: MutableMapping[str, set],
    alias: str,
    canonical: str,
) -> None:
    key = normalize_identifier(alias)
    existing = alias_map.get(key)
    if existing is not None and existing != canonical:
        conflicts.setdefault(key, {existing}).add(canonical)
        return
    alias_map[key] = canonical


# ---------------------------------------------------------------------------
# Stat alias map
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_stat_alias_map() -> Tuple[Dict[str, str], Dict[str, set]]:
    alias_map: Dict[str, str] = {}
    conflicts: Dict[str, set] = {}

    # Register every canonical stat ID from the KB contracts.
    # _load_canonical_stats() returns {stat_id: {domain, unit, resolver}}.
    # The current repo does not carry display_name on stat entries, so the
    # stat_id itself is the sole canonical key.
    for stat_id in _load_canonical_stats():
        _register_alias(alias_map, conflicts, stat_id, stat_id)

    # Layered human-readable aliases from the explicit table above.
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
    """Return all canonical stat IDs declared in the KB contracts."""
    return tuple(sorted(_load_canonical_stats().keys()))


# ---------------------------------------------------------------------------
# Registry parity
# ---------------------------------------------------------------------------

def validate_registry_parity(
    *,
    required_stat_ids: Sequence[str] | None = None,
) -> Tuple[str, ...]:
    """Check that every alias-mapped ID exists in canonical-stats and vice-versa."""
    errors: list[str] = []
    canonical = _load_canonical_stats()
    alias_map, _conflicts = _build_stat_alias_map()
    mapped_ids = set(alias_map.values())

    for stat_id in sorted(mapped_ids):
        if stat_id not in canonical:
            errors.append(f"mapped_id_missing_in_registry:{stat_id}")

    required_ids = set(required_stat_ids or required_repo_stat_ids())
    for stat_id in sorted(required_ids - mapped_ids):
        errors.append(f"required_id_missing_in_alias_map:{stat_id}")

    return tuple(sorted(errors))


# ---------------------------------------------------------------------------
# Bot mechanic data loader (replaces archive's bots_lib.load_bot_upgrades)
# ---------------------------------------------------------------------------

# Canonical mapping: mechanic-params.yaml domain suffix → IDS display name.
# Extend if new bots are added to mechanic-params.yaml.
_BOT_DOMAIN_TO_DISPLAY: Dict[str, str] = {
    "golden":  "Golden Bot",
    "amplify": "Amplify Bot",
    "flame":   "Flame Bot",
    "thunder": "Thunder Bot",
}


@lru_cache(maxsize=1)
def _load_bot_mechanic_map() -> Dict[str, Dict[str, str]]:
    """Load bot canonical IDs and their attribute parameter IDs from mechanic-params.yaml.

    Returns {display_name: {attr_key: param_id, ...}}.
    Pattern rows only – expanded from mechanic-params.yaml bot.* domains.
    """
    path = _repo_root() / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, str]] = {}
    for domain, entries in data.get("domains", {}).items():
        if not domain.startswith("bot."):
            continue
        suffix = domain.split(".", 1)[1]
        if "." in suffix:
            # sub-domain like bot.global – skip
            continue
        display = _BOT_DOMAIN_TO_DISPLAY.get(suffix)
        if display is None:
            # Unmapped bot suffix – fail-closed, caller will surface as ambiguous
            display = f"_UNMAPPED_BOT_{suffix}"
        attrs: Dict[str, str] = {}
        for entry in entries:
            param_id = entry["id"]
            # attr_key: last segment of dotted param_id (e.g. "duration_seconds")
            attr_key = param_id.rsplit(".", 1)[-1]
            attrs[attr_key] = param_id
        out[display] = attrs
    return out


# ---------------------------------------------------------------------------
# Module unique name loader (replaces archive's modules_library.UNIQUE_EFFECTS)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_module_unique_names() -> Tuple[str, ...]:
    """Return canonical module unique-effect names from mechanic-params.yaml.

    Pattern rows: extracted deterministically from modules.uniques domain IDs.
    E.g. module.amplifying_strike.* → 'amplifying_strike'.
    """
    path = _repo_root() / "kb" / "global-rules" / "contracts" / "mechanic-params.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    seen: list[str] = []
    for domain, entries in data.get("domains", {}).items():
        if domain != "modules.uniques":
            continue
        for entry in entries:
            param_id = entry["id"]  # e.g. module.amplifying_strike.tower_damage_5x_duration_s
            parts = param_id.split(".")
            if len(parts) >= 2:
                module_name = parts[1]  # amplifying_strike
                if module_name not in seen:
                    seen.append(module_name)
    return tuple(seen)


# ---------------------------------------------------------------------------
# Named entity alias maps
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_named_entity_maps() -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, set]]]:
    categories: Dict[str, Dict[str, str]] = {
        "workshop":        {},
        "cards":           {},
        "labs":            {},
        "uws":             {},
        "uw_tracks":       {},
        "modules":         {},
        "module_substats": {},
        "bots":            {},
        "bot_attributes":  {},
    }
    conflicts: Dict[str, Dict[str, set]] = {k: {} for k in categories}

    # --- workshop ---
    # Concrete rows: WORKSHOP_IDS_TO_CONTRIBUTOR keys are the canonical
    # display names for workshop stats used throughout the compiler layer.
    for workshop_name in WORKSHOP_IDS_TO_CONTRIBUTOR:
        _register_alias(
            categories["workshop"], conflicts["workshop"], workshop_name, workshop_name
        )

    # --- cards / labs / uws from catalog.yaml ---
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
                raise ValueError(f"Catalog aliases for {canonical_id!r} must be a list")
            for alias in aliases:
                _register_alias(categories[target], conflicts[target], str(alias), canonical_id)

    # --- uw_tracks ---
    # Pattern rows: _load_uw_track_order() returns Dict[uw_name, [track_name, ...]]
    # which has identical structure to the archive's _UW_TRACK_SPECS.
    for uw_name, tracks in _load_uw_track_order().items():
        uw_canonical = categories["uws"].get(normalize_identifier(uw_name), uw_name)
        _register_alias(categories["uws"], conflicts["uws"], uw_name, uw_canonical)
        for track_name in tracks:
            canonical_track = f"{uw_name}.{track_name}"
            _register_alias(
                categories["uw_tracks"], conflicts["uw_tracks"],
                canonical_track, canonical_track,
            )
            _register_alias(
                categories["uw_tracks"], conflicts["uw_tracks"],
                f"{uw_name}:{track_name}", canonical_track,
            )

    # --- modules (unique-effect names) ---
    # Pattern rows from mechanic-params.yaml modules.uniques domain.
    for module_name in _load_module_unique_names():
        _register_alias(
            categories["modules"], conflicts["modules"], module_name, module_name
        )

    # --- module_substats ---
    # SLOT_TYPES provides the canonical slot keys (concrete rows).
    # Individual substat names within slots are DEFERRED: they are parsed
    # at runtime from IDS.csv and not statically enumerated in the KB.
    # Only the slot type names themselves are registered here.
    for slot_name in SLOT_TYPES:
        _register_alias(
            categories["module_substats"], conflicts["module_substats"],
            slot_name, slot_name,
        )

    # --- bots / bot_attributes ---
    # Pattern rows: derived deterministically from mechanic-params.yaml bot.* domains.
    for bot_display_name, attrs in _load_bot_mechanic_map().items():
        _register_alias(
            categories["bots"], conflicts["bots"], bot_display_name, bot_display_name
        )
        for attr_key, param_id in attrs.items():
            canonical_attr = f"{bot_display_name}.{attr_key}"
            _register_alias(
                categories["bot_attributes"], conflicts["bot_attributes"],
                canonical_attr, canonical_attr,
            )
            _register_alias(
                categories["bot_attributes"], conflicts["bot_attributes"],
                f"{bot_display_name}:{attr_key}", canonical_attr,
            )

    # --- explicit overrides ---
    for category, aliases in _EXPLICIT_ENTITY_ALIASES.items():
        if category not in categories:
            continue
        for alias, canonical in aliases.items():
            _register_alias(categories[category], conflicts[category], alias, canonical)

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
            errors.append(
                f"entity_alias_conflict:{category}:{alias_key}:{sorted(conflict_ids)}"
            )
    return tuple(sorted(errors))


def unsupported_or_unmapped_items(items: Iterable[str]) -> Tuple[str, ...]:
    """Flag workshop items that are decisive combat stats but unmapped in the alias contract."""
    # Decisive combat stat IDs: tower and wall domain stats (both affect combat outcomes).
    canonical = _load_canonical_stats()
    decisive_ids = {
        stat_id for stat_id, meta in canonical.items()
        if meta.get("domain") in {"tower", "wall"}
    }

    failures = []
    for item in items:
        if ":" not in item:
            continue
        kind, label = item.split(":", 1)
        if kind not in {"workshop_mapping", "workshop_unsupported"}:
            continue
        try:
            stat_id = resolve_stat_id(label)
        except KeyError:
            contributor_id = WORKSHOP_IDS_TO_CONTRIBUTOR.get(label)
            if contributor_id is None:
                failures.append(f"{kind}:{label}->unmapped")
                continue
            # Extract the target stat from contributor_id
            # Format: source__entity__property__unit → use the property segment as hint
            parts = contributor_id.split("__")
            stat_id = parts[2] if len(parts) >= 3 else label
        if stat_id in decisive_ids:
            failures.append(f"{kind}:{label}->{stat_id}")
    return tuple(sorted(set(failures)))


def _is_ignored_placeholder_name(value: str) -> bool:
    norm = normalize_identifier(value)
    return norm in {"true", "false", "end of array"} or norm.startswith("any other")


# ---------------------------------------------------------------------------
# Account snapshot naming validation
# ---------------------------------------------------------------------------

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
    """Validate naming in an AccountState snapshot against the naming contract.

    snapshot must be a models.account_state.AccountState instance.
    """
    errors: list[str] = []
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

    if "modules" in strict:
        for module_name in snapshot.modules_inventory:
            if not _is_ignored_placeholder_name(module_name):
                try:
                    resolve_named_entity("modules", module_name)
                except KeyError:
                    errors.append(f"module_unmapped:{module_name}")

    if "module_substats" in strict:
        for module_name, module in snapshot.modules_inventory.items():
            for substat in module.substats:
                if module.slot_type:
                    qualified = f"{module.slot_type}:{substat.name}"
                    try:
                        resolve_named_entity("module_substats", qualified)
                        continue
                    except KeyError:
                        pass
                try:
                    resolve_named_entity("module_substats", substat.name)
                except KeyError:
                    errors.append(
                        f"module_substat_unmapped"
                        f":{module_name}:{module.slot_type}:{substat.name}"
                    )

    if "modules" in strict:
        for preset, slots in snapshot.module_presets.items():
            for slot_type, selection in slots.items():
                for role, module_name in (
                    ("primary", selection.primary),
                    ("assist", selection.assist),
                ):
                    if module_name is None:
                        continue
                    if _is_ignored_placeholder_name(module_name):
                        continue
                    try:
                        resolve_named_entity("modules", module_name)
                    except KeyError:
                        errors.append(
                            f"module_preset_unmapped"
                            f":{preset}:{slot_type}:{role}:{module_name}"
                        )

    return tuple(sorted(set(errors)))


# ---------------------------------------------------------------------------
# Master validation
# ---------------------------------------------------------------------------

def validate_repo_naming_contract(*, ids_snapshot=None) -> Tuple[str, ...]:
    errors: list[str] = []
    errors.extend(validate_registry_parity())
    errors.extend(validate_named_entity_coverage())
    if ids_snapshot is not None:
        errors.extend(
            validate_account_snapshot_naming(
                ids_snapshot,
                strict_categories=(
                    "labs", "workshop", "cards", "uws",
                    "bots", "bot_attributes", "modules", "module_substats",
                ),
            )
        )
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
