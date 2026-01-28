from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def _load_cache_audit_module() -> object:
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "tower_sim" / "wiki" / "cache_audit.py"
    spec = spec_from_file_location("cache_audit", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load cache_audit module.")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CACHE_AUDIT = _load_cache_audit_module()
audit_cache_file = _CACHE_AUDIT.audit_cache_file


def test_cache_audit_promotable() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cache_file = repo_root / "tower_sim" / "wiki" / "cache" / "lab_health.csv"
    result = audit_cache_file(cache_file)
    assert result.status in {"PROMOTABLE", "PROMOTABLE_WITH_GAPS"}
    assert result.level_column is not None
    assert result.value_column is not None


def test_cache_audit_not_promotable() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "bad_cache.csv"
    result = audit_cache_file(fixture)
    assert result.status == "NOT_PROMOTABLE"
    assert result.reason == "non_numeric_or_missing_values"
