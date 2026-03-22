"""Tests for the optimizer scorer v3 module."""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimizer.scorer import compute_optimizer_scores, compute_ehp, compute_edamage, compute_eecon


def _load_statbook():
    path = ROOT / 'out' / 'statbook.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def _optimizer_scores():
    sb = _load_statbook()
    if sb is None:
        return None
    return compute_optimizer_scores(sb)


# ═══ Structure tests ═══


def test_has_all_objectives():
    result = _optimizer_scores()
    if result is None: return
    assert 'objectives' in result
    for name in ('ehp', 'edamage', 'eecon'):
        assert name in result['objectives']


def test_has_meta_v3():
    result = _optimizer_scores()
    if result is None: return
    assert result['meta']['version'] == 'v3'


def test_each_objective_has_required_keys():
    result = _optimizer_scores()
    if result is None: return
    for name, obj in result['objectives'].items():
        assert 'score' in obj, f'{name} missing score'
        assert 'display' in obj, f'{name} missing display'
        assert 'accuracy' in obj, f'{name} missing accuracy'
        assert 'formula' in obj, f'{name} missing formula'


# ═══ Score sanity tests ═══


def test_scores_are_positive_and_finite():
    result = _optimizer_scores()
    if result is None: return
    for name, obj in result['objectives'].items():
        assert obj['score'] > 0, f'{name} score should be positive'
        assert math.isfinite(obj['score']), f'{name} score is not finite'


def test_display_not_empty():
    result = _optimizer_scores()
    if result is None: return
    for name, obj in result['objectives'].items():
        assert obj['display'] and obj['display'] != 'N/A', f'{name} display is empty'


def test_ehp_accuracy_is_ep_verified():
    result = _optimizer_scores()
    if result is None: return
    assert result['objectives']['ehp']['accuracy'] == 'ep_verified'


def test_edamage_and_eecon_accuracy_is_expanded_proxy():
    result = _optimizer_scores()
    if result is None: return
    assert result['objectives']['edamage']['accuracy'] == 'expanded_proxy'
    assert result['objectives']['eecon']['accuracy'] == 'expanded_proxy'


# ═══ Edge case tests ═══


def test_empty_statbook():
    result = compute_optimizer_scores({'rows': {}})
    for name, obj in result['objectives'].items():
        assert math.isfinite(obj['score']), f'{name} should handle empty statbook'


def test_missing_rows_key():
    result = compute_optimizer_scores({})
    for name, obj in result['objectives'].items():
        assert math.isfinite(obj['score'])


# ═══ Individual scorer function tests ═══


def test_compute_ehp_from_statbook():
    sb = _load_statbook()
    if sb is None: return
    rows = sb['rows']
    ehp = compute_ehp(rows)
    assert ehp > 0
    assert math.isfinite(ehp)


def test_compute_edamage_from_statbook():
    sb = _load_statbook()
    if sb is None: return
    rows = sb['rows']
    ed = compute_edamage(rows)
    assert ed > 0
    assert math.isfinite(ed)


def test_compute_eecon_from_statbook():
    sb = _load_statbook()
    if sb is None: return
    rows = sb['rows']
    ec = compute_eecon(rows)
    assert ec > 0
    assert math.isfinite(ec)


# ═══ eHP sensitivity test (EP-verified) ═══


def test_ehp_wall_fort_sensitivity():
    """Wall fortification should contribute positively to eHP."""
    base_rows = {
        'canonical_stat::tower_hp': {'final_value': 1e12},
        'canonical_stat::wall_hp': {'final_value': 2e12},
        'canonical_stat::wall_fortification_multiplier': {'final_value': 5.0},
        'canonical_stat::tower_defense_absolute': {'final_value': 1e6},
        'canonical_stat::tower_defense_pct': {'final_value': 90.0},
        'canonical_stat::max_recovery_multiplier': {'final_value': 16.5},
        'canonical_stat::recovery_package_multiplier': {'final_value': 1.42},
    }
    ehp_base = compute_ehp(base_rows)
    boosted = dict(base_rows)
    boosted['canonical_stat::wall_fortification_multiplier'] = {'final_value': 6.0}
    ehp_boosted = compute_ehp(boosted)
    assert ehp_boosted > ehp_base, 'Higher wall fort should increase eHP'


def test_ehp_defense_pct_sensitivity():
    """Higher defense % should increase eHP."""
    base = {
        'canonical_stat::tower_hp': {'final_value': 1e12},
        'canonical_stat::wall_hp': {'final_value': 2e12},
        'canonical_stat::wall_fortification_multiplier': {'final_value': 5.0},
        'canonical_stat::tower_defense_pct': {'final_value': 90.0},
        'canonical_stat::max_recovery_multiplier': {'final_value': 16.5},
        'canonical_stat::recovery_package_multiplier': {'final_value': 1.42},
    }
    ehp_90 = compute_ehp(base)
    base['canonical_stat::tower_defense_pct'] = {'final_value': 95.0}
    ehp_95 = compute_ehp(base)
    assert ehp_95 > ehp_90


# ═══ Path ranker import test ═══


def test_path_ranker_imports():
    from optimizer.path_ranker import rank_lab_path, EHP_LABS, EDAMAGE_LABS, EECON_LABS
    assert len(EHP_LABS) >= 5
    assert len(EDAMAGE_LABS) >= 5
    assert len(EECON_LABS) >= 5


# ═══ Runner ═══

if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f'  PASS: {fn.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL: {fn.__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    raise SystemExit(1 if failed else 0)
