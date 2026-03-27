"""optimizer/path_ranker.py -- T5 shim. Authority transferred to evaluators.ranker."""
from evaluators.ranker import (
    rank_lab_path,
    EHP_LABS,
    EDAMAGE_LABS,
    EECON_LABS,
)
# re-export scorer functions that callers may have imported via path_ranker
from evaluators.scorer import compute_ehp, compute_edamage, compute_eecon

__all__ = [
    'rank_lab_path',
    'EHP_LABS',
    'EDAMAGE_LABS',
    'EECON_LABS',
    'compute_ehp',
    'compute_edamage',
    'compute_eecon',
]
