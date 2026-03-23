"""
Optimizer scorer v4 - Query Engine consumed Phase 3 objective scores.

Phase 3 closure rule:
- Optimizer consumes governed derived objective surfaces only.
- Optimizer must not re-derive canonical eHP/eDamage/eEcon formulas locally.
- Missing governed surfaces fail closed.
"""
from __future__ import annotations


class MissingGovernedSurfaceError(KeyError):
    """Raised when a Phase 3 governed derived surface is missing."""


def _fmt(v):
    if v is None:
        return 'N/A'
    for th, s in [(1e18, 'Q'), (1e15, 'q'), (1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k')]:
        if abs(v) >= th:
            return f'{v / th:.2f} {s}'
    return f'{v:.4f}'


def _published(rows, key):
    e = rows.get(key)
    if e is None:
        return None
    if isinstance(e, dict):
        v = e.get('final_value')
    else:
        v = getattr(e, 'final_value', None)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _require_published(rows, key: str) -> float:
    value = _published(rows, key)
    if value is None:
        raise MissingGovernedSurfaceError(
            f"Missing governed derived surface: {key}. Optimizer must consume Query Engine-owned objective surfaces only."
        )
    return value


def compute_ehp(rows):
    """Consume governed Query Engine-owned eHP only."""
    return _require_published(rows, 'derived::ehp')


def compute_edamage(rows):
    """Consume governed Query Engine-owned eDamage only."""
    return _require_published(rows, 'derived::edamage')


def compute_eecon(rows):
    """Consume governed Query Engine-owned eEcon only."""
    return _require_published(rows, 'derived::eecon')




def optimizer_consumption_contract_snapshot() -> dict:
    """Expose the optimizer's governed Phase 3 consumption contract for audits."""
    return {
        'required_objective_surfaces': [
            'derived::ehp',
            'derived::edamage',
            'derived::eecon',
        ],
        'forbidden_legacy_prefixes': [
            'objective_state::',
        ],
        'missing_surface_policy': 'fail_closed',
        'local_canonical_formula_fallback': False,
    }

def compute_optimizer_scores(statbook_dict):
    rows = statbook_dict.get('rows', {})
    ehs = compute_ehp(rows)
    eds = compute_edamage(rows)
    ecs = compute_eecon(rows)

    return {
        'objectives': {
            'ehp': {
                'score': ehs,
                'display': _fmt(ehs),
                'accuracy': 'query_owned_surface',
                'formula': 'consumes derived::ehp',
            },
            'edamage': {
                'score': eds,
                'display': _fmt(eds),
                'accuracy': 'query_owned_surface',
                'formula': 'consumes derived::edamage',
            },
            'eecon': {
                'score': ecs,
                'display': _fmt(ecs),
                'accuracy': 'query_owned_surface',
                'formula': 'consumes derived::eecon',
            },
        },
        'meta': {
            'version': 'v4',
            'note': 'Optimizer consumes Query Engine-owned derived objective surfaces only; local canonical fallback formulas removed.',
            'requires': 'derived::ehp, derived::edamage, and derived::eecon must already be published by Query Engine surfaces',
        },
    }
