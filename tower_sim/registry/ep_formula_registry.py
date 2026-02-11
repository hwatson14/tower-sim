from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

import yaml


BUILTIN_FUNCTIONS: Set[str] = {
    "LET",
    "IF",
    "AND",
    "OR",
    "MIN",
    "MAX",
    "FLOOR",
    "SUM",
    "ARRAYFORMULA",
    "SEQUENCE",
    "VLOOKUP",
    "RIGHT",
    "ROUND",
    "INT",
    "LOG",
    "LN",
    "EXP",
    "ABS",
    "SQRT",
    "POWER",
    "MOD",
    "CEILING",
    "AVERAGE",
    "COUNT",
    "COUNTA",
    "XLOOKUP",
    "INDEX",
    "MATCH",
    "SWITCH",
    "CHOOSE",
    "TEXT",
    "VALUE",
    "IFERROR",
    "ISNUMBER",
    "ISBLANK",
    "ISERROR",
    "SIN",
    "COS",
    "TAN",
    "ASIN",
    "ACOS",
    "ATAN",
    "RADIANS",
    "DEGREES",
    "CONCAT",
    "CONCATENATE",
    "SUBSTITUTE",
    "TRIM",
    "LAMBDA",
}

KNOWN_IMPLICIT_GLOBALS: Mapping[str, Set[str]] = {}


class RegistryValidationError(ValueError):
    def __init__(self, message: str, missing_symbols: Iterable[str] | None = None) -> None:
        super().__init__(message)
        self.missing_symbols = list(missing_symbols or [])


@dataclass(frozen=True)
class LambdaMechanic:
    name: str
    excel_definition: str
    parameters: Tuple[str, ...]
    body: str
    implicit_globals: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CellFormula:
    formula_id: str
    name: str
    sheet: str
    cell: str
    excel_formula: str
    depends_on: Tuple[str, ...]


@dataclass(frozen=True)
class FormulaRegistry:
    mechanics: Mapping[str, LambdaMechanic]
    formulas: Mapping[str, CellFormula]
    targets: Mapping[str, Sequence[str]]
    sources: Mapping[str, Mapping[str, str]]

    def validate(self) -> None:
        missing = _collect_missing_functions(
            mechanics=self.mechanics,
            formulas=self.formulas.values(),
        )
        if missing:
            raise RegistryValidationError(
                "Registry references missing mechanic symbols.",
                missing_symbols=sorted(missing),
            )


def load_ep_formula_registry(
    registry_dir: Path | None = None, *, strict: bool = True
) -> FormulaRegistry:
    resolved_dir = registry_dir or _default_registry_dir()
    formula_data = _load_yaml(resolved_dir / "formula_library.yaml")
    mechanics_data = _load_yaml(resolved_dir / "mechanics_library.yaml")
    targets = _load_yaml(resolved_dir / "targets.yaml")
    sources = _load_yaml(resolved_dir / "sources.yaml")

    mechanics = _parse_mechanics(mechanics_data)
    formulas = _parse_formulas(formula_data, mechanics)

    registry = FormulaRegistry(
        mechanics=mechanics,
        formulas=formulas,
        targets=targets,
        sources=sources,
    )
    if strict:
        registry.validate()
    return registry


def _default_registry_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tables" / "meta" / "registry" / "ep_formulas"


def _load_yaml(path: Path) -> Mapping[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _parse_mechanics(raw: Mapping[str, object]) -> Dict[str, LambdaMechanic]:
    mechanics: Dict[str, LambdaMechanic] = {}
    for group in raw.values():
        if not isinstance(group, dict):
            continue
        for item in group.get("mechanics", []) or []:
            name = item["name"]
            definition = item["excel_definition"]
            params, body = _parse_lambda_signature(definition)
            implicit_globals = _resolve_implicit_globals(name, body, params)
            if name in mechanics:
                raise ValueError(f"Duplicate mechanic name: {name}")
            mechanics[name] = LambdaMechanic(
                name=name,
                excel_definition=definition,
                parameters=tuple(params),
                body=body,
                implicit_globals=tuple(sorted(implicit_globals)),
            )
    return mechanics


def _parse_formulas(
    raw: Mapping[str, object], mechanics: Mapping[str, LambdaMechanic]
) -> Dict[str, CellFormula]:
    formulas: Dict[str, CellFormula] = {}
    cells_by_sheet = _collect_cells(raw)
    for group in raw.values():
        if not isinstance(group, dict):
            continue
        for item in group.get("formulas", []) or []:
            formula_id = item["id"]
            sheet = item["sheet"]
            cell = _normalize_cell_ref(item["cell"])
            excel_formula = item["excel_formula"]
            depends_on = _resolve_formula_dependencies(
                excel_formula, sheet, cells_by_sheet
            )
            if formula_id in formulas:
                raise ValueError(f"Duplicate formula id: {formula_id}")
            formulas[formula_id] = CellFormula(
                formula_id=formula_id,
                name=item["name"],
                sheet=sheet,
                cell=cell,
                excel_formula=excel_formula,
                depends_on=tuple(depends_on),
            )
    return formulas


def _collect_cells(raw: Mapping[str, object]) -> Dict[str, Dict[str, str]]:
    cells_by_sheet: Dict[str, Dict[str, str]] = {}
    for group in raw.values():
        if not isinstance(group, dict):
            continue
        for item in group.get("formulas", []) or []:
            sheet = item["sheet"]
            cell = _normalize_cell_ref(item["cell"])
            cells_by_sheet.setdefault(sheet, {})[cell] = item["id"]
    return cells_by_sheet


def _resolve_formula_dependencies(
    excel_formula: str, sheet: str, cells_by_sheet: Mapping[str, Mapping[str, str]]
) -> List[str]:
    dependencies: List[str] = []
    for cell_ref in _find_cell_references(excel_formula):
        normalized = _normalize_cell_ref(cell_ref)
        match = cells_by_sheet.get(sheet, {}).get(normalized)
        if match and match not in dependencies:
            dependencies.append(match)
    return dependencies


def _collect_missing_functions(
    *, mechanics: Mapping[str, LambdaMechanic], formulas: Iterable[CellFormula]
) -> Set[str]:
    missing: Set[str] = set()
    mechanic_names = set(mechanics.keys())
    for mechanic in mechanics.values():
        missing.update(
            _missing_function_calls(
                mechanic.body,
                mechanic_names,
            )
        )
    for formula in formulas:
        missing.update(
            _missing_function_calls(
                formula.excel_formula,
                mechanic_names,
            )
        )
    return missing


def _missing_function_calls(formula: str, mechanic_names: Set[str]) -> Set[str]:
    missing: Set[str] = set()
    for name in _find_function_calls(formula):
        if name in BUILTIN_FUNCTIONS or name in mechanic_names:
            continue
        missing.add(name)
    return missing


def _find_function_calls(formula: str) -> List[str]:
    return [match.group(1) for match in _FUNCTION_CALL_RE.finditer(formula)]


def _find_cell_references(formula: str) -> List[str]:
    return [match.group(0) for match in _CELL_REF_RE.finditer(formula)]


def _parse_lambda_signature(definition: str) -> Tuple[List[str], str]:
    trimmed = definition.strip()
    if trimmed.startswith("="):
        trimmed = trimmed[1:]
    if not trimmed.upper().startswith("LAMBDA("):
        raise ValueError(f"Expected LAMBDA definition, got: {definition}")
    content = trimmed[trimmed.find("(") + 1 : trimmed.rfind(")")]
    args = _split_top_level_args(content)
    if len(args) < 2:
        raise ValueError(f"Invalid LAMBDA definition: {definition}")
    params = [arg.strip() for arg in args[:-1] if arg.strip()]
    body = args[-1].strip()
    return params, body


def _resolve_implicit_globals(
    name: str, body: str, params: Sequence[str]
) -> Set[str]:
    implicit: Set[str] = set()
    missing = KNOWN_IMPLICIT_GLOBALS.get(name, set())
    for candidate in missing:
        if _contains_identifier(body, candidate) and candidate not in params:
            implicit.add(candidate)
    if implicit != missing and _contains_identifier(body, "vault") and name != "EPD_BST":
        raise RegistryValidationError(
            "Unexpected implicit global symbol referenced in LAMBDA definition.",
            missing_symbols=[name],
        )
    return implicit


def _contains_identifier(expression: str, identifier: str) -> bool:
    pattern = rf"\b{identifier}\b"
    return bool(re.search(pattern, expression, flags=re.IGNORECASE))


def _split_top_level_args(content: str) -> List[str]:
    args: List[str] = []
    current: List[str] = []
    depth = 0
    in_string = False
    i = 0
    while i < len(content):
        char = content[i]
        if char == '"':
            if in_string and i + 1 < len(content) and content[i + 1] == '"':
                current.append('"')
                i += 2
                continue
            in_string = not in_string
            current.append(char)
            i += 1
            continue
        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
                i += 1
                continue
        current.append(char)
        i += 1
    if current:
        args.append("".join(current).strip())
    return args


def _normalize_cell_ref(cell: str) -> str:
    return cell.replace("$", "").upper()


_FUNCTION_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CELL_REF_RE = re.compile(r"\$?[A-Za-z]{1,3}\$?\d+")
