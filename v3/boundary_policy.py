"""v3 boundary-policy helpers.

Step-6 scope: enforce explicit stop behavior for accepted knowledge boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

from v3.kb_access import read_csv_rows


class V3BoundaryPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class BoundaryRow:
    scope: str
    item_id: str
    status: str
    notes: str


def load_unknowns_operating_policy() -> list[BoundaryRow]:
    rows = read_csv_rows("kb/UNKNOWNS_OPERATING_POLICY.csv")
    out: list[BoundaryRow] = []
    for row in rows:
        out.append(
            BoundaryRow(
                scope=str(row.get("scope", "")).strip(),
                item_id=str(row.get("item_id", "")).strip(),
                status=str(row.get("status", "")).strip(),
                notes=str(row.get("notes", "")).strip(),
            )
        )
    return out


def load_out_of_scope_tick_precedence_rows() -> list[BoundaryRow]:
    paths = (
        "kb/bots/tables/bot-runtime-boundary-registry.csv",
        "kb/ultimate-weapons/tables/uw-runtime-boundary-registry.csv",
    )
    out: list[BoundaryRow] = []
    for path in paths:
        rows = read_csv_rows(path, authority="mechanics")
        for row in rows:
            out.append(
                BoundaryRow(
                    scope=f"runtime_boundary:{path}",
                    item_id=str(row.get("entity_id", "")).strip(),
                    status=str(row.get("status", "")).strip(),
                    notes=str(row.get("runtime_surface", "")).strip(),
                )
            )
    return out


def assert_boundary_supported(*, scope: str, item_id: str) -> None:
    for row in load_unknowns_operating_policy():
        if row.scope == scope and row.item_id == item_id:
            if row.status == "accepted_unknown_boundary":
                raise V3BoundaryPolicyError(
                    f"accepted_unknown_boundary:{scope}:{item_id}"
                )
            return


def assert_tick_precedence_supported(*, entity_id: str) -> None:
    for row in load_out_of_scope_tick_precedence_rows():
        if row.item_id == entity_id and row.status == "out_of_scope_tick_precedence":
            raise V3BoundaryPolicyError(f"out_of_scope_tick_precedence:{entity_id}")
