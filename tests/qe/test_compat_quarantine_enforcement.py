from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QE_ROOT = REPO_ROOT / 'qe'
QUARANTINE_ROOT = QE_ROOT / 'compat'
ALLOWED_NON_QUARANTINE = {
    QE_ROOT / 'contracts.py',
}
TARGET_FILES = {
    QE_ROOT / 'routing.py',
    QE_ROOT / 'query_derived_composites.py',
    QE_ROOT / 'materializer.py',
    QE_ROOT / 'stat_resolution.py',
}


def _iter_qe_modules() -> list[Path]:
    return sorted(path for path in QE_ROOT.glob('**/*.py') if path.is_file())


def test_no_new_compat_or_legacy_helper_defs_outside_quarantine() -> None:
    violations: list[str] = []
    for module in _iter_qe_modules():
        if module.is_relative_to(QUARANTINE_ROOT) or module in ALLOWED_NON_QUARANTINE:
            continue
        tree = ast.parse(module.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith(('compat_', 'legacy_', '_compat_', '_legacy_')):
                violations.append(f'{module.relative_to(REPO_ROOT)}::{node.name}')
    assert not violations, (
        'Compatibility/legacy helper defs must stay quarantined in qe/compat. '
        f'Found: {violations}'
    )


def test_target_modules_do_not_import_legacy_bridges_from_qe_contracts() -> None:
    violations: list[str] = []
    for module in sorted(TARGET_FILES):
        tree = ast.parse(module.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != 'qe.contracts':
                continue
            for alias in node.names:
                imported = alias.name
                if imported.startswith('compat_surface_from_legacy') or imported == 'to_legacy_surface_id':
                    violations.append(f'{module.relative_to(REPO_ROOT)} imports {imported} from qe.contracts')
    assert not violations, (
        'Legacy bridge imports in routing/materializer/stat resolution surfaces must '
        f'route through qe.compat quarantine only. Found: {violations}'
    )
