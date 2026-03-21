"""
Optimizer module — EP-aligned composite scores and greedy path ranking.

eHP scoring is EP-verified (100% match on modelable labs).
eDamage and eEcon are expanded proxies with UW channels. See ACCURACY.md for details.
"""
from optimizer.scorer import compute_optimizer_scores, compute_ehp, compute_edamage, compute_eecon
from optimizer.path_ranker import rank_lab_path, EHP_LABS, EDAMAGE_LABS, EECON_LABS
