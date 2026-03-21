from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAT_ENGINE = ROOT / 'engine' / 'stat_engine.py'

FORBIDDEN_SNIPPETS = [
    'def _apply_phase3_exact_overrides(',
    'def _apply_exact_free_upgrade_formula(',
    '_apply_phase3_exact_overrides(rows)',
    '_apply_exact_free_upgrade_formula(rows)',
]


def test_stat_engine_has_no_named_canonical_override_helpers():
    text = STAT_ENGINE.read_text(encoding='utf-8')
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in text, f'Forbidden canonical override snippet present: {snippet}'
