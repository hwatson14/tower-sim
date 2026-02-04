from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Sequence

import csv
import yaml

from tower_sim.libs.workshop_lib import WorkshopTables, load_workshop_tables, workshop_value
from tower_sim.util.account_snapshot import AccountSnapshot


MECHANICS_FILENAME = "mechanics_library_v0_7.yaml"

# WSValues uses "HPregen" while IDS uses "Health Regen" in the fixture export.
# Provenance: audit/ehp_stat_source_audit.md notes WSValues uses HPregen for base regen.
WORKSHOP_ENTRY_ALIASES = {
    "HPregen": "Health Regen",
}


class StatEvaluationError(ValueError):
    pass


class BlockedByScopeError(StatEvaluationError):
    pass


class MissingIdsPathError(StatEvaluationError):
    pass


class UnknownOperatorError(StatEvaluationError):
    pass


class MissingRuleParamError(StatEvaluationError):
    pass


class TableLookupError(StatEvaluationError):
    pass


@dataclass(frozen=True)
class _MechanicsData:
    stats: Mapping[str, Mapping[str, Any]]
    helpers: Mapping[str, Mapping[str, Any]]


@dataclass
class _EvalContext:
    ids_snapshot: AccountSnapshot
    enabled_stats: Sequence[str]
    allow_out_of_scope: bool
    cache: MutableMapping[str, float]
    helper_cache: MutableMapping[str, float]


def evaluate_stats(
    ids_snapshot: AccountSnapshot,
    enabled_stats: Sequence[str],
    *,
    allow_out_of_scope: bool = False,
) -> Dict[str, float]:
    mechanics = _load_mechanics()
    _validate_enabled_stats(enabled_stats, mechanics)

    context = _EvalContext(
        ids_snapshot=ids_snapshot,
        enabled_stats=enabled_stats,
        allow_out_of_scope=allow_out_of_scope,
        cache={},
        helper_cache={},
    )

    results: Dict[str, float] = {}
    for stat_key in enabled_stats:
        results[stat_key] = _eval_stat(stat_key, context, mechanics)
    return results


def _validate_enabled_stats(
    enabled_stats: Sequence[str],
    mechanics: _MechanicsData,
) -> None:
    missing = [stat for stat in enabled_stats if stat not in mechanics.stats]
    if missing:
        raise StatEvaluationError(
            f"Unknown stat(s) in mechanics YAML: {sorted(missing)}"
        )


def _eval_stat(
    stat_key: str,
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> float:
    if stat_key not in context.enabled_stats:
        raise StatEvaluationError(
            f"Refusing to evaluate stat {stat_key!r} not in enabled_stats."
        )
    if stat_key in context.cache:
        return context.cache[stat_key]

    stat_def = mechanics.stats.get(stat_key)
    if stat_def is None:
        raise StatEvaluationError(f"Missing stat definition for {stat_key!r}.")
    definition = stat_def.get("definition", {})
    op_chain = definition.get("op_chain", [])
    if not op_chain:
        raise StatEvaluationError(f"Missing op_chain for stat {stat_key!r}.")

    current: float | None = None
    for op_step in op_chain:
        op_name = op_step.get("op")
        if op_name is None:
            raise UnknownOperatorError(
                f"stat={stat_key} op=<missing> missing op name"
            )
        current = _apply_op(stat_key, current, op_name, op_step, context, mechanics)

    if current is None:
        raise StatEvaluationError(f"Stat {stat_key!r} evaluated to None.")
    context.cache[stat_key] = float(current)
    return context.cache[stat_key]


def _apply_op(
    stat_key: str,
    current: float | None,
    op_name: str,
    op_step: Mapping[str, Any],
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> float:
    if op_name == "BASE":
        return float(op_step["value"])
    if op_name == "APPLY_WORKSHOP_BASE":
        level = _eval_level(stat_key, op_name, op_step["level"], context)
        base_curve = op_step.get("base_curve") or _infer_base_curve(
            stat_key, op_name, op_step
        )
        return _workshop_base_value(stat_key, level, base_curve)
    if op_name == "MULT":
        if current is None:
            raise StatEvaluationError(
                f"stat={stat_key} op={op_name} missing current value"
            )
        factor = _eval_factor(stat_key, op_name, op_step["factor"], context, mechanics)
        return current * factor
    if op_name == "ADD":
        if current is None:
            raise StatEvaluationError(
                f"stat={stat_key} op={op_name} missing current value"
            )
        term = _eval_term(stat_key, op_name, op_step["term"], context, mechanics)
        return current + term
    if op_name == "ADD_PP":
        if current is None:
            current = 0.0
        term = _eval_term(stat_key, op_name, op_step["term"], context, mechanics)
        return current + term
    if op_name == "CAP_MAX":
        if current is None:
            raise StatEvaluationError(
                f"stat={stat_key} op={op_name} missing current value"
            )
        return min(current, float(op_step["value"]))
    if op_name == "DERIVE":
        expr = op_step.get("expr")
        inputs = op_step.get("inputs", [])
        if expr is None:
            raise MissingRuleParamError(
                f"stat={stat_key} op={op_name} missing expr"
            )
        values = _eval_inputs(stat_key, inputs, context, mechanics)
        return _eval_expr(stat_key, op_name, expr, values)

    raise UnknownOperatorError(f"stat={stat_key} op={op_name} unknown operator")


def _eval_factor(
    stat_key: str,
    op_name: str,
    factor: Mapping[str, Any],
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> float:
    factor_type = factor.get("type")
    if factor_type == "TABLE_LOOKUP":
        return _table_lookup(stat_key, op_name, factor, context)
    if factor_type == "HELPER_REF":
        helper_name = factor.get("name")
        if helper_name is None:
            raise MissingRuleParamError(
                f"stat={stat_key} op={op_name} missing helper name"
            )
        return _eval_helper(helper_name, context, mechanics)
    raise UnknownOperatorError(
        f"stat={stat_key} op={op_name} unknown factor type {factor_type!r}"
    )


def _eval_term(
    stat_key: str,
    op_name: str,
    term: Mapping[str, Any],
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> float:
    term_type = term.get("type")
    if term_type in {"WORKSHOP_RULE", "LAB_RULE"}:
        return _eval_rule(stat_key, op_name, term_type, term, context)
    if term_type == "TABLE_LOOKUP":
        return _table_lookup(stat_key, op_name, term, context)
    if term_type == "CARD_TABLE":
        return _handle_out_of_scope(stat_key, op_name, "cards", context, term)
    raise UnknownOperatorError(
        f"stat={stat_key} op={op_name} unknown term type {term_type!r}"
    )


def _eval_rule(
    stat_key: str,
    op_name: str,
    rule_type: str,
    rule: Mapping[str, Any],
    context: _EvalContext,
) -> float:
    level = _eval_level(stat_key, op_name, rule["level"], context)
    if "pp_per_level" in rule:
        per_level = float(rule["pp_per_level"])
        pp_total = level * per_level
        max_pp = rule.get("max_pp")
        if max_pp is not None:
            pp_total = min(pp_total, float(max_pp))
        return pp_total / 100.0
    if "add_per_level" in rule:
        per_level = float(rule["add_per_level"])
        total = level * per_level
        cap_max = rule.get("cap_max") or rule.get("max")
        if cap_max is not None:
            total = min(total, float(cap_max))
        return total
    raise MissingRuleParamError(
        f"stat={stat_key} op={op_name} missing rule params for {rule_type}"
    )


def _eval_level(
    stat_key: str,
    op_name: str,
    level_spec: Mapping[str, Any],
    context: _EvalContext,
) -> int:
    level_type = level_spec.get("type")
    if level_type == "IDS_PATH":
        path = level_spec.get("path")
        if path is None:
            raise MissingIdsPathError(
                f"stat={stat_key} op={op_name} missing ids_path"
            )
        return _ids_level(stat_key, op_name, path, context)
    if level_type == "MISSING_IDS_PATH":
        expected = level_spec.get("expected")
        if expected is None:
            raise MissingIdsPathError(
                f"stat={stat_key} op={op_name} missing ids_path"
            )
        return _ids_level(stat_key, op_name, expected, context)
    raise UnknownOperatorError(
        f"stat={stat_key} op={op_name} unknown level type {level_type!r}"
    )


def _ids_level(
    stat_key: str,
    op_name: str,
    path: str,
    context: _EvalContext,
) -> int:
    try:
        value = _resolve_ids_path(path, context)
    except KeyError as exc:
        raise MissingIdsPathError(
            f"stat={stat_key} op={op_name} missing ids_path={path}"
        ) from exc
    if value is None:
        raise MissingIdsPathError(
            f"stat={stat_key} op={op_name} missing ids_path={path}"
        )
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise StatEvaluationError(
            f"stat={stat_key} op={op_name} invalid level value {value!r}"
        ) from exc
    if not numeric.is_integer():
        raise StatEvaluationError(
            f"stat={stat_key} op={op_name} non-integer level {value!r}"
        )
    return int(numeric)


_IDS_PATH_RE = re.compile(
    r"^ids\.(?P<section>\w+)\.(?P<collection>\w+)\['(?P<key>[^']+)'\](?:\.(?P<attr>\w+))?$"
)


def _resolve_ids_path(path: str, context: _EvalContext) -> Any:
    match = _IDS_PATH_RE.match(path)
    if match is None:
        raise KeyError(f"Unsupported IDS path: {path}")
    section = match.group("section")
    collection = match.group("collection")
    key = match.group("key")
    attr = match.group("attr")

    if section not in {"labs", "workshop", "cards"}:
        return _handle_out_of_scope(
            "<ids_path>", "IDS_PATH", section, context, {"path": path}
        )
    lookup_key = WORKSHOP_ENTRY_ALIASES.get(key, key)
    if section == "labs":
        if collection != "labs":
            raise KeyError(path)
        if lookup_key not in context.ids_snapshot.labs:
            raise KeyError(path)
        if attr is not None:
            raise KeyError(path)
        return context.ids_snapshot.labs[lookup_key]
    if section == "workshop":
        if collection != "entries":
            raise KeyError(path)
        if lookup_key not in context.ids_snapshot.workshop:
            raise KeyError(path)
        value = context.ids_snapshot.workshop[lookup_key]
        if attr is None:
            return value
        return getattr(value, attr)
    if section == "cards":
        if collection != "cards":
            raise KeyError(path)
        if lookup_key not in context.ids_snapshot.cards_inventory:
            raise KeyError(path)
        value = context.ids_snapshot.cards_inventory[lookup_key]
        if attr is None:
            return value
        return getattr(value, attr)
    raise KeyError(path)


def _workshop_base_value(stat_key: str, level: int, base_curve: str) -> float:
    section, stat_name = _parse_base_curve(base_curve)
    tables = _load_workshop_tables()
    value = workshop_value(stat_name, level, tables, section=section)
    return float(value)


def _parse_base_curve(base_curve: str) -> tuple[str, str]:
    if "/" not in base_curve:
        raise StatEvaluationError(f"Invalid base curve format: {base_curve}")
    section, stat_name = base_curve.split("/", 1)
    return section, stat_name


def _infer_base_curve(
    stat_key: str,
    op_name: str,
    op_step: Mapping[str, Any],
) -> str:
    level_spec = op_step.get("level", {})
    path = level_spec.get("path") or level_spec.get("expected")
    if not path:
        raise MissingRuleParamError(
            f"stat={stat_key} op={op_name} missing base_curve"
        )
    match = _IDS_PATH_RE.match(path)
    if match is None:
        raise MissingRuleParamError(
            f"stat={stat_key} op={op_name} missing base_curve"
        )
    stat_name = match.group("key")
    return f"WSValues/{stat_name}"


def _eval_inputs(
    stat_key: str,
    inputs: Iterable[Any],
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for item in inputs:
        if isinstance(item, str):
            if item not in context.enabled_stats:
                raise StatEvaluationError(
                    f"stat={stat_key} depends_on={item} not in enabled_stats"
                )
            values[item] = _eval_stat(item, context, mechanics)
            continue
        if isinstance(item, Mapping) and "helper" in item:
            helper_name = item["helper"]
            values[helper_name] = _eval_helper(helper_name, context, mechanics)
            continue
        raise StatEvaluationError(
            f"stat={stat_key} invalid derive input {item!r}"
        )
    return values


def _eval_expr(
    stat_key: str,
    op_name: str,
    expr: str,
    values: Mapping[str, float],
) -> float:
    try:
        return float(eval(expr, {"__builtins__": {}}, dict(values)))
    except Exception as exc:  # pragma: no cover - defensive
        raise StatEvaluationError(
            f"stat={stat_key} op={op_name} failed expr {expr!r}"
        ) from exc


def _eval_helper(
    helper_name: str,
    context: _EvalContext,
    mechanics: _MechanicsData,
) -> float:
    if helper_name in context.helper_cache:
        return context.helper_cache[helper_name]
    helper_def = mechanics.helpers.get(helper_name)
    if helper_def is None:
        raise StatEvaluationError(f"Missing helper definition {helper_name!r}.")
    definition = helper_def.get("definition", {})
    op_chain = definition.get("op_chain", [])
    if not op_chain:
        raise StatEvaluationError(
            f"Missing op_chain for helper {helper_name!r}."
        )
    current: float | None = None
    for op_step in op_chain:
        op_name = op_step.get("op")
        if op_name is None:
            raise UnknownOperatorError(
                f"helper={helper_name} op=<missing> missing op name"
            )
        current = _apply_op(
            helper_name,
            current,
            op_name,
            op_step,
            context,
            mechanics,
        )
    if current is None:
        raise StatEvaluationError(f"Helper {helper_name!r} evaluated to None.")
    context.helper_cache[helper_name] = float(current)
    return context.helper_cache[helper_name]


def _table_lookup(
    stat_key: str,
    op_name: str,
    spec: Mapping[str, Any],
    context: _EvalContext,
) -> float:
    table = spec.get("table")
    key_spec = spec.get("key")
    if table is None or key_spec is None:
        raise MissingRuleParamError(
            f"stat={stat_key} op={op_name} missing table/key"
        )
    canonical_id = key_spec.get("canonical_id")
    if canonical_id is None:
        raise TableLookupError(
            f"stat={stat_key} op={op_name} missing canonical_id"
        )
    if canonical_id == "LAB_STANDARD_PERKS_BONUS":
        return _handle_out_of_scope(stat_key, op_name, "perks", context, spec)

    level_spec = key_spec.get("level")
    if level_spec is None:
        raise MissingRuleParamError(
            f"stat={stat_key} op={op_name} missing level spec"
        )
    level = _eval_level(stat_key, op_name, level_spec, context)

    table_path = _resolve_table_path(table)
    table_data = _load_table(table_path)

    if canonical_id not in table_data:
        raise TableLookupError(
            f"stat={stat_key} op={op_name} table missing canonical_id={canonical_id}"
        )
    levels = table_data[canonical_id]
    if level not in levels:
        raise TableLookupError(
            f"stat={stat_key} op={op_name} table missing level={level}"
        )
    value, unit = levels[level]
    return _apply_unit(value, unit)


def _resolve_table_path(table: str) -> Path:
    if table.startswith("tables/"):
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / table
    return Path(table)


def _apply_unit(value: float, unit: str) -> float:
    if unit == "raw_number":
        return float(value)
    if unit == "percent":
        return float(value) / 100.0
    if unit == "percent_points":
        return float(value) / 100.0
    raise TableLookupError(f"Unsupported unit {unit!r} in lab table")


@lru_cache(maxsize=8)
def _load_table(table_path: Path) -> Dict[str, Dict[int, tuple[float, str]]]:
    if not table_path.exists():
        raise TableLookupError(f"Missing table: {table_path}")
    table: Dict[str, Dict[int, tuple[float, str]]] = {}
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise TableLookupError(f"Missing headers in table: {table_path}")
        for row in reader:
            canonical_id = row.get("lab_canonical_id")
            if canonical_id is None:
                raise TableLookupError(
                    f"Missing lab_canonical_id in table {table_path}"
                )
            level = int(float(row["level"]))
            value = float(row["value"])
            unit = row["unit"]
            table.setdefault(canonical_id, {})[level] = (value, unit)
    if not table:
        raise TableLookupError(f"Table is empty: {table_path}")
    return table


@lru_cache(maxsize=1)
def _load_mechanics() -> _MechanicsData:
    mechanics_path = _default_mechanics_path()
    raw = yaml.safe_load(mechanics_path.read_text(encoding="utf-8"))
    stat_definitions = raw.get("stat_definitions", {})
    stats = stat_definitions.get("stats", {})
    helpers = stat_definitions.get("helpers", {})
    return _MechanicsData(stats=stats, helpers=helpers)


def _default_mechanics_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "tables" / "registry" / "ep_formulas" / MECHANICS_FILENAME


@lru_cache(maxsize=1)
def _load_workshop_tables() -> WorkshopTables:
    return load_workshop_tables()


def _handle_out_of_scope(
    stat_key: str,
    op_name: str,
    scope: str,
    context: _EvalContext,
    payload: Mapping[str, Any],
) -> float:
    if not context.allow_out_of_scope:
        raise BlockedByScopeError(
            f"stat={stat_key} op={op_name} blocked_by_scope={scope}"
        )
    if op_name == "MULT":
        return 1.0
    if op_name in {"ADD", "ADD_PP", "IDS_PATH"}:
        return 0.0
    if payload.get("type") == "CARD_TABLE":
        return 0.0
    return 1.0


__all__ = [
    "BlockedByScopeError",
    "MissingIdsPathError",
    "StatEvaluationError",
    "TableLookupError",
    "evaluate_stats",
]
