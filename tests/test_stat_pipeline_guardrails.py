from __future__ import annotations

from pathlib import Path

from tower_sim.audit import stat_pipeline_guardrails as guardrails


def test_load_allowlist_shape() -> None:
    functions, scan_roots = guardrails.load_allowlist()
    assert "compile_full_stat_inputs" in functions
    assert "tower_sim" in scan_roots


def test_discover_function_calls_finds_known_runtime_callsite() -> None:
    discovered = guardrails.discover_function_calls(
        function_names={"compile_full_stat_inputs"},
        scan_roots=["tower_sim"],
    )
    assert "tower_sim/engines/combat_stat_derivation.py" in discovered[
        "compile_full_stat_inputs"
    ]


def test_validate_guardrails_default_allowlist_has_no_violations() -> None:
    violations = guardrails.validate_guardrails()
    assert violations == []


def test_validate_guardrails_reports_new_unallowlisted_callsite(tmp_path: Path) -> None:
    repo_root = Path(guardrails.REPO_ROOT)
    ephemeral_dir = repo_root / "scripts" / "_guardrail_ephemeral"
    ephemeral_dir.mkdir(parents=True, exist_ok=True)
    try:
        target = ephemeral_dir / "bad_callsite.py"
        target.write_text(
            "from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs\n"
            "def run(snapshot):\n"
            "    return compile_full_stat_inputs(snapshot)\n",
            encoding="utf-8",
        )
        violations = guardrails.validate_guardrails()
        assert any(
            v.function_name == "compile_full_stat_inputs"
            and v.file_path == "scripts/_guardrail_ephemeral/bad_callsite.py"
            for v in violations
        )
    finally:
        if ephemeral_dir.exists():
            for path in sorted(ephemeral_dir.glob("*.py")):
                path.unlink()
            ephemeral_dir.rmdir()
