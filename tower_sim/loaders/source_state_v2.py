from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
import re
from typing import Any, Mapping

from tower_sim.registry.static_v2_contract import StaticV2ContractError, load_static_v2_contract
from tower_sim.util.account_snapshot import AccountSnapshot


_REQUIRED_FAMILIES: tuple[str, ...] = (
    "workshop",
    "labs",
    "relics",
    "cards",
    "module_main",
    "module_sub",
    "module_unique",
    "ultimate_weapons",
    "uw_plus",
    "bots",
    "perks",
    "battle_conditions",
    "guardians",
    "vault",
    "enhancement",
)

_IMPLEMENTED_FAMILIES = {
    "workshop",
    "labs",
    "relics",
    "cards",
    "module_main",
    "module_sub",
    "module_unique",
    "ultimate_weapons",
    "uw_plus",
    "bots",
    "perks",
    "battle_conditions",
    "guardians",
    "vault",
    "enhancement",
}

_TABLE_PATHS = {
    "perks": Path("tables/inputs/perks/perks_v1.csv"),
    "battle_conditions": Path("tables/inputs/combat/tier_battle_conditions.csv"),
}


class SourceStateV2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceStateRecord:
    family: str
    source_state_field: str
    value: Any
    provenance: str


@dataclass(frozen=True)
class FamilyCoverage:
    family: str
    in_scope: bool
    adapter_implemented: bool
    blocked_or_deferred: bool
    reason: str | None


@dataclass(frozen=True)
class SourceStateNormalizationResult:
    records: list[SourceStateRecord]
    coverage: list[FamilyCoverage]


def required_source_state_families() -> tuple[str, ...]:
    return _REQUIRED_FAMILIES


def normalize_source_state(snapshot: AccountSnapshot) -> SourceStateNormalizationResult:
    contract = load_static_v2_contract()
    records: list[SourceStateRecord] = []

    records.extend(_workshop_records(snapshot))
    records.extend(_labs_records(snapshot))
    records.extend(_relic_records(snapshot))
    records.extend(_card_records(snapshot))
    records.extend(_module_records(snapshot))
    records.extend(_uw_records(snapshot))
    records.extend(_uw_plus_records(snapshot))
    records.extend(_bot_records(snapshot))
    records.extend(_perk_records())
    records.extend(_battle_condition_records())
    records.extend(_guardian_records(snapshot))
    records.extend(_vault_records(snapshot))
    records.extend(_enhancement_records(snapshot))

    for record in records:
        _validate_source_state_identifier(record.source_state_field, contract=contract)
        if record.provenance.strip() == "":
            raise SourceStateV2Error(f"missing_provenance:{record.family}:{record.source_state_field}")

    coverage = _coverage_rows()
    return SourceStateNormalizationResult(records=records, coverage=coverage)


def _coverage_rows() -> list[FamilyCoverage]:
    rows: list[FamilyCoverage] = []
    for family in _REQUIRED_FAMILIES:
        implemented = family in _IMPLEMENTED_FAMILIES
        blocked = not implemented
        reason = None
        if blocked:
            reason = "phase_b_blocked_missing_static_source_surface_in_account_snapshot"
        rows.append(
            FamilyCoverage(
                family=family,
                in_scope=True,
                adapter_implemented=implemented,
                blocked_or_deferred=blocked,
                reason=reason,
            )
        )
    return rows


def _validate_source_state_identifier(value: str, *, contract) -> None:
    candidate = value.strip()
    if candidate in contract.static_runtime_deny_list:
        raise SourceStateV2Error(f"runtime_field_not_allowed_in_source_state:{candidate}")
    if candidate in contract.canonical_target_stats:
        raise SourceStateV2Error(f"canonical_target_not_allowed_as_source_state_field:{candidate}")
    if candidate in contract.canonical_contributor_ids:
        raise SourceStateV2Error(f"canonical_contributor_not_allowed_as_source_state_field:{candidate}")
    if candidate.startswith(("legacy_stage__", "resolved__", "helper__")):
        raise SourceStateV2Error(f"fabricated_contributor_prefix_not_allowed:{candidate}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _workshop_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for name, entry in snapshot.workshop.items():
        key = _slug(name)
        out.append(SourceStateRecord("workshop", f"workshop__{key}__coin_level", entry.coin_level, "ids:WS"))
        out.append(SourceStateRecord("workshop", f"workshop__{key}__max_level", entry.max_level, "ids:WS"))
    return out


def _labs_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    return [
        SourceStateRecord("labs", f"labs__{_slug(name)}__level", level, "ids:Labs")
        for name, level in snapshot.labs.items()
    ]


def _relic_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    return [
        SourceStateRecord("relics", f"relics__{_slug(name)}__value", value, "ids:Relics")
        for name, value in snapshot.relics.items()
    ]


def _card_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for name, card in snapshot.cards_inventory.items():
        key = _slug(name)
        out.append(SourceStateRecord("cards", f"cards__{key}__level", card.level, "ids:Cards"))
        out.append(SourceStateRecord("cards", f"cards__{key}__mastery_unlocked", card.mastery_unlocked, "ids:Cards"))
    return out


def _module_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for name, module in snapshot.modules_inventory.items():
        key = _slug(name)
        out.append(SourceStateRecord("module_main", f"module_main__{key}__level", module.level, "ids:Modules"))
        out.append(SourceStateRecord("module_unique", f"module_unique__{key}__stat", module.stat, "ids:Modules"))
        for index, sub in enumerate(module.substats):
            out.append(
                SourceStateRecord(
                    "module_sub",
                    f"module_sub__{key}__slot_{index}__value",
                    sub.value_num,
                    "ids:Modules",
                )
            )
    return out


def _uw_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for name, uw in snapshot.ultimate_weapons.items():
        key = _slug(name)
        out.append(SourceStateRecord("ultimate_weapons", f"ultimate_weapons__{key}__unlocked", uw.unlocked, "ids:UWs"))
        for index, level in enumerate(uw.track_levels):
            out.append(
                SourceStateRecord(
                    "ultimate_weapons",
                    f"ultimate_weapons__{key}__track_{index}__level",
                    level,
                    "ids:UWs",
                )
            )
    return out




def _uw_plus_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for key, track in snapshot.uw_plus_tracks.items():
        safe_key = _slug(key)
        out.append(
            SourceStateRecord(
                "uw_plus",
                f"uw_plus__{safe_key}__current_state",
                track.current_state,
                "ids:UWs",
            )
        )
        out.append(
            SourceStateRecord(
                "uw_plus",
                f"uw_plus__{safe_key}__display_token",
                track.display_token,
                "ids:UWs",
            )
        )
    return out

def _bot_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    out: list[SourceStateRecord] = []
    for bot_name in snapshot.bots:
        out.append(SourceStateRecord("bots", f"bots__{_slug(bot_name)}__owned", True, "ids:Bots"))
    for bot_name, upgrades in snapshot.bot_upgrades.items():
        for attribute, level in upgrades.items():
            out.append(
                SourceStateRecord(
                    "bots",
                    f"bots__{_slug(bot_name)}__{_slug(attribute)}__level",
                    level,
                    "ids:Bots",
                )
            )
    return out




def _count_data_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    return max(0, len(rows) - 1)


def _perk_records() -> list[SourceStateRecord]:
    path = _TABLE_PATHS["perks"]
    if not path.exists():
        raise SourceStateV2Error(f"missing_source_table:{path}")
    return [
        SourceStateRecord(
            "perks",
            "perks__reference_table__rows",
            _count_data_rows(path),
            f"table:{path}",
        )
    ]


def _battle_condition_records() -> list[SourceStateRecord]:
    path = _TABLE_PATHS["battle_conditions"]
    if not path.exists():
        raise SourceStateV2Error(f"missing_source_table:{path}")
    return [
        SourceStateRecord(
            "battle_conditions",
            "battle_conditions__reference_table__rows",
            _count_data_rows(path),
            f"table:{path}",
        )
    ]

def _guardian_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    return [
        SourceStateRecord("guardians", "guardians__raw_table__rows", len(snapshot.guardians.rows), "ids:Guardians")
    ]


def _vault_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    return [
        SourceStateRecord("vault", f"vault__{_slug(name)}__level", level, "ids:Vault")
        for name, level in snapshot.vault.items()
    ]


def _enhancement_records(snapshot: AccountSnapshot) -> list[SourceStateRecord]:
    return [
        SourceStateRecord(
            "enhancement",
            "enhancement__raw_table__rows",
            len(snapshot.workshop_enhancements.rows),
            "ids:WS+",
        )
    ]
