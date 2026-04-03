"""
engine/kb_surfaces.py — Runtime KB table loader for source-backed gameplay constants.

Reads wiki-verified mechanic truth from KB CSV tables so that engine code
does not carry execution-authoritative literal values for gameplay data.
Engine modules must import their constants from this module, not define them inline.

Split:
  - Source-backed gameplay truth (boss constants, stat caps, workshop/lab formulas):
    loaded from KB tables here.
  - QE resolver policy (kill thresholds, resolution rules): see qe/policy.py.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]
_BOSS_SUMMARY_PATH = _ROOT / 'kb' / 'enemies' / 'tables' / 'wiki-verified-boss-summary.csv'
_STAT_CAPS_PATH = _ROOT / 'kb' / 'global-rules' / 'tables' / 'game-mechanic-stat-caps.csv'
_WORKSHOP_FORMULAS_PATH = _ROOT / 'kb' / 'global-rules' / 'tables' / 'workshop-formula-params-canonical.csv'
_RUNTIME_FORMULA_AUTHORITY_PATH = _ROOT / 'kb' / 'global-rules' / 'tables' / 'runtime-formula-authority.csv'
_CANONICAL_FORMULA_REGISTRY_PATH = _ROOT / 'kb' / 'formulas' / 'tables' / 'canonical-formula-registry.csv'
_CANONICAL_DOMAIN_ALIASES: dict[str, set[str]] = {
    'lab': {'labs'},
}
RUNTIME_CALLABLE_GENERATOR_KINDS: frozenset[str] = frozenset({
    'exact_linear_generator_from_row_verified_summary',
    'exact_linear_generator_from_row_verified_table',
})


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_boss_constants() -> dict[str, float]:
    """
    Return {rule: value} for boss mechanic constants from wiki-verified-boss-summary.csv.

    Values are converted to engine internal units:
      - health_multiplier_vs_basic: raw multiplier (20.0), 'x' prefix stripped
      - *_pct rules: percentage divided by 100 to give fraction (e.g. 3.75 -> 0.0375)
    """
    rows = _read_csv(_BOSS_SUMMARY_PATH)
    result: dict[str, float] = {}
    for row in rows:
        rule = row['rule'].strip()
        raw = row['value_or_note'].strip()
        try:
            numeric = float(raw.lstrip('x'))
        except (ValueError, AttributeError):
            continue
        # pct-named rules are stored as percentages; convert to fractions for engine use
        if rule.endswith('_pct'):
            result[rule] = numeric / 100.0
        else:
            result[rule] = numeric
    return result


def load_stat_caps() -> dict[str, tuple[str, float]]:
    """
    Return {stat_id: (cap_type, cap_value)} from game-mechanic-stat-caps.csv.
    cap_type is 'max' or 'min'.
    """
    rows = _read_csv(_STAT_CAPS_PATH)
    result: dict[str, tuple[str, float]] = {}
    for row in rows:
        stat_id = row['stat_id'].strip()
        cap_type = row['cap_type'].strip()
        cap_value = float(row['cap_value'])
        result[stat_id] = (cap_type, cap_value)
    return result


def _build_formula(formula_type: str, base: float, per_level: float, floor: float) -> Callable[[float], float]:
    if formula_type == 'linear':
        return lambda level, b=base, p=per_level: b + p * level
    elif formula_type == 'linear_with_floor':
        return lambda level, b=base, p=per_level, fl=floor: max(fl, b + p * level)
    elif formula_type == 'linear_from_level_plus_one':
        return lambda level, b=base, p=per_level: b + p * (level + 1)
    else:
        raise ValueError(f'Unknown formula_type in KB table: {formula_type!r}')


def _build_linear_canonical_formula(start_level: float, base: float, delta: float) -> Callable[[float], float]:
    return lambda level, s=start_level, b=base, d=delta: b + (((level - s) / 1.0) * d)


def _canonical_domain_matches_runtime_domain(runtime_domain: str, canonical_domain: str) -> bool:
    if canonical_domain == runtime_domain:
        return True
    return canonical_domain in _CANONICAL_DOMAIN_ALIASES.get(runtime_domain, set())


def _load_runtime_formula_authority_rows() -> dict[tuple[str, str], dict[str, str]]:
    rows = _read_csv(_RUNTIME_FORMULA_AUTHORITY_PATH)
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        source_domain = row['source_domain'].strip()
        stat_name = row['stat_name'].strip()
        key = (source_domain, stat_name)
        if key in mapping:
            raise ValueError(f'Duplicate runtime formula authority mapping row: {source_domain}:{stat_name}')
        mapping[key] = {
            'authority_source': row['authority_source'].strip(),
            'formula_id': (row.get('formula_id') or '').strip(),
            'approved_exception_reason': (row.get('approved_exception_reason') or '').strip(),
        }
    return mapping


def _canonical_formula_callables() -> dict[str, Callable[[float], float]]:
    rows = _read_csv(_CANONICAL_FORMULA_REGISTRY_PATH)
    runtime_authority_rows = _load_runtime_formula_authority_rows()
    formula_row_by_id = {row['formula_id'].strip(): row for row in rows}
    formulas: dict[str, Callable[[float], float]] = {}
    for (domain, stat_name), metadata in runtime_authority_rows.items():
        if metadata['authority_source'] != 'canonical_formula_registry':
            continue
        formula_id = metadata['formula_id']
        row = formula_row_by_id.get(formula_id)
        if not row:
            raise ValueError(f'Runtime formula mapping references unknown canonical formula_id: {formula_id!r}')
        generator_kind = (row.get('generator_kind') or '').strip()
        if generator_kind not in RUNTIME_CALLABLE_GENERATOR_KINDS:
            raise ValueError(
                f'Runtime formula mapping {domain}:{stat_name} uses unsupported generator_kind '
                f'{generator_kind!r} for formula_id {formula_id!r}.'
            )
        row_domain = (row.get('domain') or '').strip()
        if not _canonical_domain_matches_runtime_domain(domain, row_domain):
            raise ValueError(
                f'Runtime formula mapping domain mismatch for {domain}:{stat_name}: '
                f'formula_id {formula_id!r} belongs to domain {row_domain!r}'
            )
        formulas[f'{domain}:{stat_name}'] = _build_linear_canonical_formula(
            float(row['start_level']),
            float(row['base_value']),
            float(row['delta_per_step']),
        )
    return formulas


def load_workshop_formulas() -> tuple[dict[str, Callable], dict[str, Callable]]:
    """
    Return (workshop_formulas, lab_formulas) where each is {stat_name: callable(level) -> float}.
    Loaded from workshop-formula-params-canonical.csv.
    Lab stat names have the ' (lab)' suffix stripped.
    """
    rows = _read_csv(_WORKSHOP_FORMULAS_PATH)
    workshop: dict[str, Callable] = {}
    lab: dict[str, Callable] = {}
    runtime_authority_rows = _load_runtime_formula_authority_rows()
    canonical_formulas = _canonical_formula_callables()
    for row in rows:
        source_domain = row['source_domain'].strip()
        stat_name = row['stat_name'].strip()
        formula_type = row['formula_type'].strip()
        base = float(row['base'] or 0)
        per_level = float(row['per_level'] or 0)
        floor_raw = row['floor'].strip() if row['floor'] else ''
        floor_val = float(floor_raw) if floor_raw else 0.0
        canonical_key = f'{source_domain}:{stat_name.removesuffix(" (lab)")}'
        authority = runtime_authority_rows.get((source_domain, stat_name.removesuffix(' (lab)')))
        if not authority:
            raise ValueError(f'Runtime formula key missing authority mapping: {canonical_key}')
        authority_source = authority['authority_source']
        if authority_source == 'canonical_formula_registry':
            fn = canonical_formulas.get(canonical_key)
            if fn is None:
                raise ValueError(
                    f'Runtime formula key {canonical_key} is canonical_formula_registry mapped but no canonical '
                    f'callable was built for formula_id {authority["formula_id"]!r}.'
                )
        elif authority_source == 'approved_exception':
            fn = _build_formula(formula_type, base, per_level, floor_val)
        else:
            raise ValueError(
                f'Runtime formula key {canonical_key} has unsupported authority_source {authority_source!r}.'
            )
        key = stat_name.removesuffix(' (lab)')
        if source_domain == 'workshop':
            workshop[key] = fn
        elif source_domain == 'lab':
            lab[key] = fn
    return workshop, lab


def load_runtime_formula_authority() -> dict[str, dict[str, str]]:
    """Return explicit authority metadata for each runtime workshop/lab formula key."""
    runtime_authority_rows = _load_runtime_formula_authority_rows()
    canonical_formula_ids = {row['formula_id'].strip() for row in _read_csv(_CANONICAL_FORMULA_REGISTRY_PATH)}
    workshop, lab = load_workshop_formulas()
    runtime_keys = {(domain, key) for domain, bucket in (('workshop', workshop), ('lab', lab)) for key in bucket}
    mapping_keys = set(runtime_authority_rows)
    if runtime_keys != mapping_keys:
        missing = sorted(runtime_keys - mapping_keys)
        extra = sorted(mapping_keys - runtime_keys)
        raise ValueError(
            f'Runtime authority mapping coverage mismatch. missing={missing!r} extra={extra!r}'
        )

    authority: dict[str, dict[str, str]] = {}
    for domain, key in sorted(runtime_keys):
        mapping = runtime_authority_rows[(domain, key)]
        source = mapping['authority_source']
        formula_id = mapping['formula_id']
        exception_reason = mapping['approved_exception_reason']

        if source == 'canonical_formula_registry':
            if not formula_id:
                raise ValueError(f'{domain}:{key} is canonical_formula_registry but formula_id is empty.')
            if formula_id not in canonical_formula_ids:
                raise ValueError(f'{domain}:{key} references unknown canonical formula_id {formula_id!r}.')
            authority[f'{domain}:{key}'] = {
                'authority_source': source,
                'formula_id': formula_id,
            }
        elif source == 'approved_exception':
            if not exception_reason:
                raise ValueError(f'{domain}:{key} approved_exception must include approved_exception_reason.')
            authority[f'{domain}:{key}'] = {
                'authority_source': source,
                'formula_id': '',
                'approved_exception_reason': exception_reason,
            }
        else:
            raise ValueError(f'{domain}:{key} has unsupported authority_source {source!r}.')
    return authority


# ---------------------------------------------------------------------------
# Module-level constants — loaded once at import time
# ---------------------------------------------------------------------------

_BOSS_CONSTANTS = load_boss_constants()
_STAT_CAPS = load_stat_caps()
_WORKSHOP_FORMULAS, _LAB_FORMULAS = load_workshop_formulas()
_RUNTIME_FORMULA_AUTHORITY = load_runtime_formula_authority()

# Boss mechanic constants (source: kb/enemies/tables/wiki-verified-boss-summary.csv)
BOSS_HP_MULTIPLIER: float = _BOSS_CONSTANTS['health_multiplier_vs_basic']
ELECTRON_BOSS_REMAINING_HP_PCT: float = _BOSS_CONSTANTS['electron_remaining_hp_pct']
THORNS_BOSS_EFFECTIVENESS: float = _BOSS_CONSTANTS['thorns_effectiveness_vs_boss_pct']
BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT: float = _BOSS_CONSTANTS['heat_up_damage_per_hit_pct']

# Stat caps (source: kb/global-rules/tables/game-mechanic-stat-caps.csv)
# {stat_id: cap_value} — preserves the interface expected by stat_resolution_core.py
CANONICAL_PCT_CAPS: dict[str, float] = {
    stat_id: cap_value for stat_id, (cap_type, cap_value) in _STAT_CAPS.items()
}

# Workshop and lab formula callables (source: kb/global-rules/tables/workshop-formula-params-canonical.csv)
WORKSHOP_FORMULA_VALUES: dict[str, Callable] = _WORKSHOP_FORMULAS
LAB_FORMULA_VALUES: dict[str, Callable] = _LAB_FORMULAS
RUNTIME_FORMULA_AUTHORITY: dict[str, dict[str, str]] = _RUNTIME_FORMULA_AUTHORITY
