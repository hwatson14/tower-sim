"""
evaluators/ranker.py -- Ranking and sorting.

Owns: path ranking, upgrade candidate ranking, sort-by-score logic.

Extracted from: optimizer/path_ranker.py (T5).
"""
from __future__ import annotations
from typing import Callable
from evaluators.scorer import compute_ehp, compute_edamage, compute_eecon


def rank_lab_path(
    run_pipeline: Callable,
    get_lab_duration: Callable,
    candidate_labs: list[str],
    score_fn: Callable,
    current_labs: dict,
    steps: int = 15,
    max_level: int = 100,
) -> list[dict]:
    """
    Greedy lab path optimizer.

    Parameters
    ----------
    run_pipeline : callable(lab_overrides: dict) -> statbook_dict
        Runs the full stat pipeline with optional lab level overrides.
    get_lab_duration : callable(lab_name: str, level: int) -> float
        Returns raw lab duration in days for the given lab at given level.
    candidate_labs : list[str]
        Lab names to consider for upgrades.
    score_fn : callable(rows: dict) -> float
        Composite score function (compute_ehp, compute_edamage, or compute_eecon).
    current_labs : dict
        Current lab levels {lab_name: level}.
    steps : int
        Number of path steps to generate.
    max_level : int
        Maximum lab level to consider.

    Returns
    -------
    list[dict] with keys: step, lab, level, roi, delta_pct, score
    """
    labs = dict(current_labs)
    base_sb = run_pipeline(labs)
    base_score = score_fn(base_sb.get('rows', {}))
    path = []

    for step_num in range(1, steps + 1):
        best = {'roi': -1, 'lab': None, 'level': None, 'score': None}

        for lab in candidate_labs:
            cur = labs.get(lab, 0)
            nxt = cur + 1
            if nxt > max_level:
                continue
            dur = get_lab_duration(lab, nxt)
            if dur >= 1e9:
                continue

            trial = dict(labs)
            trial[lab] = nxt
            new_sb = run_pipeline(trial)
            new_score = score_fn(new_sb.get('rows', {}))
            delta = (new_score / base_score) - 1.0
            roi = delta / dur if dur > 0 else 0

            if roi > best['roi']:
                best = {'roi': roi, 'lab': lab, 'level': nxt, 'score': new_score}

        if best['lab'] is None:
            break

        delta_pct = (best['score'] / base_score - 1.0) * 100
        path.append({
            'step': step_num,
            'lab': best['lab'],
            'level': best['level'],
            'roi_per_day': best['roi'],
            'delta_pct': delta_pct,
            'score': best['score'],
        })

        labs[best['lab']] = best['level']
        base_score = best['score']

    return path


# Pre-defined lab candidate sets per objective
EHP_LABS = [
    'Health', 'Wall Fortification', 'Defense Absolute', 'Defense %',
    'Wall Health', 'Standard Perks Bonus', 'Improve Trade-off Perks',
    'Chrono Field Reduction %', 'Death Wave Health',
    'Assist Module Bonus - Armor', 'Assist Module Substats - Armor',
]

EDAMAGE_LABS = [
    'Damage', 'Attack Speed', 'Critical Chance', 'Critical Factor',
    'Range', 'Damage / Meter', 'Super Critical Chance', 'Super Critical Mult',
    'Assist Module Bonus - Core', 'Assist Module Substats - Core',
]

EECON_LABS = [
    'Coins / Kill Bonus', 'Golden Tower Bonus', 'Golden Tower Duration',
    'Black Hole Coin Bonus', 'Gold Bot - Duration',
    'Assist Module Bonus - Generator', 'Assist Module Substats - Generator',
    'Spotlight Coin Bonus', 'Death Wave Coin Bonus',
]
