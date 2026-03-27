"""optimizer/scorer.py -- T5 shim. Authority transferred to evaluators.scorer."""
from evaluators.scorer import (
    MissingGovernedSurfaceError,
    _fmt,
    _published,
    _require_published,
    compute_edamage,
    compute_eecon,
    compute_ehp,
    compute_optimizer_scores,
    optimizer_consumption_contract_snapshot,
)

__all__ = [
    'MissingGovernedSurfaceError',
    '_fmt',
    '_published',
    '_require_published',
    'compute_edamage',
    'compute_eecon',
    'compute_ehp',
    'compute_optimizer_scores',
    'optimizer_consumption_contract_snapshot',
]
