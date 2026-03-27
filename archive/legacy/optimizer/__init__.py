"""Optimizer package consuming query-owned Phase 3 objective surfaces."""

from optimizer.scorer import (
    MissingGovernedSurfaceError,
    compute_optimizer_scores,
    compute_ehp,
    compute_edamage,
    compute_eecon,
)
from optimizer.path_ranker import rank_lab_path, EHP_LABS, EDAMAGE_LABS, EECON_LABS
