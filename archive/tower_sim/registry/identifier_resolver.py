from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


ALLOWED_DEFINITION_TYPES = {
    "ALIAS",
    "CONST",
    "DERIVED",
    "IDS",
    "RANGE",
    "REF",
    "TABLE",
}

UNRESOLVED_PATTERN = re.compile(r"UNRESOLVED\(([^)]+)\)")


@dataclass(frozen=True)
class IdentifierDefinition:
    identifier: str
    definition_type: str
    defined_by_ep_cell: Optional[str]
    sheet: Optional[str]
    formula_or_rule: Optional[str]
    notes: Optional[str]

    def replacement_token(self) -> str:
        definition_type = self.definition_type.upper()
        if definition_type == "IDS":
            if not self.formula_or_rule:
                raise ValueError(f"IDS definition missing field key for {self.identifier!r}.")
            return f"IDS({self.formula_or_rule})"
        if definition_type == "CONST":
            if not self.formula_or_rule:
                raise ValueError(f"CONST definition missing value for {self.identifier!r}.")
            return f"CONST({self.formula_or_rule})"
        if definition_type == "REF":
            if not self.sheet or not self.formula_or_rule:
                raise ValueError(f"REF definition missing sheet or cell for {self.identifier!r}.")
            sheet = _format_sheet(self.sheet)
            return f"REF({sheet}!{self.formula_or_rule})"
        if definition_type == "RANGE":
            if not self.sheet or not self.formula_or_rule:
                raise ValueError(f"RANGE definition missing sheet or range for {self.identifier!r}.")
            sheet = _format_sheet(self.sheet)
            return f"RANGE({sheet}!{self.formula_or_rule})"
        if definition_type == "TABLE":
            if not self.formula_or_rule:
                raise ValueError(f"TABLE definition missing lookup spec for {self.identifier!r}.")
            return f"TABLE({self.formula_or_rule})"
        if definition_type == "DERIVED":
            if not self.formula_or_rule:
                raise ValueError(f"DERIVED definition missing stat key for {self.identifier!r}.")
            return f"DERIVED({self.formula_or_rule})"
        if definition_type == "ALIAS":
            if not self.formula_or_rule:
                raise ValueError(f"ALIAS definition missing stat key for {self.identifier!r}.")
            return f"ALIAS({self.formula_or_rule})"
        raise ValueError(f"Unsupported definition type: {self.definition_type!r}.")


@dataclass(frozen=True)
class ResolutionReport:
    unresolved_before: int
    unresolved_after: int
    unresolved_tokens: List[str]
    unresolved_identifiers: List[str]
    replacements_applied: int


class UnresolvedIdentifierError(ValueError):
    def __init__(self, message: str, report: ResolutionReport) -> None:
        super().__init__(message)
        self.report = report


class IdentifierResolver:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self.registry = self._load_registry(registry_path)

    def resolve_ledger(
        self,
        ledger: pd.DataFrame,
        columns: Iterable[str] = ("direct_inputs",),
        fail_on_unresolved: bool = True,
    ) -> tuple[pd.DataFrame, ResolutionReport]:
        resolved = ledger.copy()
        unresolved_tokens: List[str] = []
        unresolved_identifiers: List[str] = []
        replacements_applied = 0

        def replace_token(match: re.Match[str]) -> str:
            nonlocal replacements_applied
            token_body = match.group(1).strip()
            sheet, identifier = _parse_token_identifier(token_body)
            replacement = self._lookup_replacement(sheet, identifier)
            if replacement is None:
                unresolved_tokens.append(match.group(0))
                unresolved_identifiers.append(identifier)
                return match.group(0)
            replacements_applied += 1
            return replacement

        unresolved_before = 0
        for column in columns:
            if column not in resolved.columns:
                continue
            series = resolved[column].fillna("").astype(str)
            unresolved_before += series.str.count(UNRESOLVED_PATTERN).sum()
            resolved[column] = series.apply(lambda value: UNRESOLVED_PATTERN.sub(replace_token, value))

        unresolved_tokens_sorted = sorted(set(unresolved_tokens))
        unresolved_identifiers_sorted = sorted(set(unresolved_identifiers))
        report = ResolutionReport(
            unresolved_before=unresolved_before,
            unresolved_after=len(unresolved_tokens),
            unresolved_tokens=unresolved_tokens_sorted,
            unresolved_identifiers=unresolved_identifiers_sorted,
            replacements_applied=replacements_applied,
        )
        if fail_on_unresolved and unresolved_tokens:
            message = (
                "Unresolved identifiers remain after registry rewrite. "
                f"Unresolved tokens: {len(unresolved_tokens_sorted)}. "
                f"Unresolved identifiers: {len(unresolved_identifiers_sorted)}."
            )
            raise UnresolvedIdentifierError(message, report)
        return resolved, report

    def _lookup_replacement(self, sheet: Optional[str], identifier: str) -> Optional[str]:
        key = (sheet, identifier)
        definition = self.registry.get(key)
        if definition is None:
            return None
        return definition.replacement_token()

    def _load_registry(self, registry_path: Path) -> Dict[Tuple[Optional[str], str], IdentifierDefinition]:
        if not registry_path.exists():
            raise FileNotFoundError(f"Missing identifier registry CSV: {registry_path}")
        df = pd.read_csv(registry_path).fillna("")
        registry: Dict[Tuple[Optional[str], str], IdentifierDefinition] = {}
        for _, row in df.iterrows():
            identifier = str(row.get("identifier", "")).strip()
            definition_type = str(row.get("definition_type", "")).strip()
            if not definition_type:
                continue
            definition_type_upper = definition_type.upper()
            if definition_type_upper not in ALLOWED_DEFINITION_TYPES:
                raise ValueError(f"Unsupported definition type {definition_type!r} for {identifier!r}.")

            defined_by_ep_cell = str(row.get("defined_by_ep_cell", "")).strip() or None
            sheet = str(row.get("sheet", "")).strip() or None
            formula_or_rule = str(row.get("formula_or_rule", "")).strip() or None
            notes = str(row.get("notes", "")).strip() or None

            if definition_type_upper not in {"IDS", "CONST"}:
                if not defined_by_ep_cell or not formula_or_rule:
                    raise ValueError(
                        "Registry entry missing provenance for "
                        f"{identifier!r} ({definition_type_upper})."
                    )

            definition = IdentifierDefinition(
                identifier=identifier,
                definition_type=definition_type_upper,
                defined_by_ep_cell=defined_by_ep_cell,
                sheet=sheet,
                formula_or_rule=formula_or_rule,
                notes=notes,
            )
            key = (sheet, identifier)
            if key in registry:
                raise ValueError(f"Duplicate registry entry for {identifier!r} (sheet={sheet!r}).")
            registry[key] = definition
        return registry


def _parse_token_identifier(token_body: str) -> tuple[Optional[str], str]:
    token_body = token_body.strip()
    if "!" not in token_body:
        return None, token_body
    sheet_part, cell_part = token_body.split("!", 1)
    sheet = sheet_part.strip()
    if sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1]
    if sheet.startswith('"') and sheet.endswith('"'):
        sheet = sheet[1:-1]
    return sheet or None, cell_part.strip()


def _format_sheet(sheet: str) -> str:
    sheet = sheet.strip()
    if sheet.startswith("'") and sheet.endswith("'"):
        return sheet
    if " " in sheet:
        return f"'{sheet}'"
    return sheet
