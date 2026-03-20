"""v3 account-input registry loaders (KB-driven).

Step-4 scope: load and normalize account-input registry families from canonical
KB tables only. This module does not invent per-account values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from v3.kb_access import read_csv_rows


class V3AccountInputRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RegistryEntry:
    source_family: str
    contributor_id: str
    destination_object_type: str
    destination_id: str
    resolver: str
    semantic_unit_hint: str
    provenance: str


@dataclass(frozen=True)
class VaultExternalizedEntry:
    source_family: str
    contributor_id: str
    destination_id: str
    resolver: str
    semantic_unit_hint: str
    status: str
    provenance: str


_REGISTRY_PATHS = {
    "relic": "kb/global-rules/tables/relic-input-registry.csv",
    "player_stuff": "kb/global-rules/tables/player-stuff-input-registry.csv",
    "theme_song": "kb/global-rules/tables/theme-song-input-registry.csv",
    "unlock": "kb/global-rules/tables/unlock-input-registry.csv",
}
_VAULT_EXTERNALIZED_PATH = "kb/economy/tables/vault-externalized-simulator-inputs.csv"
_REQUIRED_FAMILIES = ("relic", "player_stuff", "theme_song", "unlock", "vault")


def _require_text(row: dict[str, str], key: str, *, path: str) -> str:
    value = str(row.get(key, "")).strip()
    if value == "":
        raise V3AccountInputRegistryError(f"missing_field:{path}:{key}")
    return value


def _normalize_registry_rows(path: str, expected_family: str) -> list[RegistryEntry]:
    rows = read_csv_rows(path, authority="mechanics")
    out: list[RegistryEntry] = []
    for row in rows:
        source_family = _require_text(row, "source_family", path=path)
        if source_family != expected_family:
            raise V3AccountInputRegistryError(
                f"source_family_mismatch:{path}:expected={expected_family}:observed={source_family}"
            )
        contributor_id = _require_text(row, "contributor_id", path=path)
        out.append(
            RegistryEntry(
                source_family=source_family,
                contributor_id=contributor_id,
                destination_object_type=_require_text(row, "destination_object_type", path=path),
                destination_id=_require_text(row, "destination_id", path=path),
                resolver=_require_text(row, "resolver", path=path),
                semantic_unit_hint=_require_text(row, "semantic_unit_hint", path=path),
                provenance=f"kb_table:{path}:{contributor_id}",
            )
        )
    if not out:
        raise V3AccountInputRegistryError(f"empty_registry:{path}")
    return out


def load_account_input_registry_family(source_family: str) -> list[RegistryEntry | VaultExternalizedEntry]:
    family = source_family.strip()
    if family == "vault":
        rows = read_csv_rows(_VAULT_EXTERNALIZED_PATH, authority="mechanics")
        out: list[VaultExternalizedEntry] = []
        for row in rows:
            status = _require_text(row, "status", path=_VAULT_EXTERNALIZED_PATH)
            if status != "externalized_allowed_input":
                raise V3AccountInputRegistryError(
                    f"unexpected_vault_status:{status}"
                )
            cid = _require_text(row, "vault_canonical_id", path=_VAULT_EXTERNALIZED_PATH)
            out.append(
                VaultExternalizedEntry(
                    source_family="vault",
                    contributor_id=cid.lower(),
                    destination_id=_require_text(row, "input_field", path=_VAULT_EXTERNALIZED_PATH),
                    resolver="externalized_allowed_input",
                    semantic_unit_hint=_require_text(row, "unit", path=_VAULT_EXTERNALIZED_PATH),
                    status=status,
                    provenance=f"kb_table:{_VAULT_EXTERNALIZED_PATH}:{cid}",
                )
            )
        if not out:
            raise V3AccountInputRegistryError(f"empty_registry:{_VAULT_EXTERNALIZED_PATH}")
        return out

    path = _REGISTRY_PATHS.get(family)
    if not path:
        raise V3AccountInputRegistryError(f"unsupported_source_family:{source_family}")
    return _normalize_registry_rows(path, expected_family=family)


def load_all_account_input_registries() -> dict[str, list[RegistryEntry | VaultExternalizedEntry]]:
    loaded = {family: load_account_input_registry_family(family) for family in _REQUIRED_FAMILIES}
    return loaded


def registry_counts() -> dict[str, int]:
    return {family: len(entries) for family, entries in load_all_account_input_registries().items()}
