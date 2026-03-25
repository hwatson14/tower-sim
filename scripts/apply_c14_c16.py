
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

RUN_STATS = ROOT / 'run_stats.py'
CONTROL = ROOT / 'IDS_EXECUTION_CONTROL_REGISTER.md'

INSERT_AFTER = """def _build_audit_surface_manifest(account_state, canonical_output_preset: str) -> dict:
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    perk_presets = getattr(account_state, 'perk_presets', {}) or {}
    preset_lane_completeness = {}
    for preset in CANONICAL_PRESET_NAMES:
        preset_lane_completeness[preset] = {
            'cards_explicit': preset in card_presets,
            'cards_empty': preset in card_presets and not bool(card_presets.get(preset)),
            'modules_explicit': preset in module_presets,
            'modules_empty': preset in module_presets and not bool(module_presets.get(preset)),
            'perks_explicit': preset in perk_presets,
            'perks_empty': preset in perk_presets and not bool(perk_presets.get(preset)),
        }
    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'surface_contracts': [
            {
                'surface': 'account_state.json',
                'contract': 'full',
                'completeness_scope': 'canonical_full_state',
                'notes': 'canonical account-state snapshot',
            },
            {
                'surface': 'state_matrix.json',
                'contract': 'full',
                'completeness_scope': 'state_mode_resolution_matrix',
                'notes': 'full matrix over supported state modes',
            },
            {
                'surface': 'diagnostics.json',
                'contract': 'partial',
                'completeness_scope': 'selected_context',
                'notes': 'diagnostic/selected-context summaries only',
            },
            {
                'surface': 'statbook_publishable.json',
                'contract': 'partial',
                'completeness_scope': 'publishable_filtered',
                'notes': 'publishable policy filtered rows',
            },
            {
                'surface': 'ep_oracle_compare.json',
                'contract': 'partial',
                'completeness_scope': 'compare_context',
                'notes': 'compare-only selected context',
            },
        ],
        'preset_lane_completeness': preset_lane_completeness,
    }
"""

ADD_BLOCK = """


def _synthetic_preset_names_present(account_state) -> list[str]:
    raw_names = set()
    for lane_map_name in ('card_presets', 'module_presets', 'perk_presets'):
        lane_map = getattr(account_state, lane_map_name, {}) or {}
        raw_names.update(lane_map.keys())
    return sorted(name for name in raw_names if name not in CANONICAL_PRESET_NAMES)


def _build_artifact_contract_manifest(account_state, canonical_output_preset: str, stat_inputs, statbook_dict: dict) -> dict:
    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'canonical_preset_count': len(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': _synthetic_preset_names_present(account_state),
        'artifacts': [
            {'surface': 'account_state.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'stat_inputs.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'statbook.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'state_matrix.json', 'artifact_class': 'derived_matrix', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'statbook_publishable.json', 'artifact_class': 'publishable_view', 'contract': 'partial', 'provenance': 'policy_filtered_from_current_run', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'diagnostics.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'provenance': 'compare_generated_from_current_run_and_ep', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'ep_oracle_compare.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'provenance': 'compare_generated_from_current_run_and_ep', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'line_by_line_verification.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'provenance': 'verification_generated_from_current_run_and_compare', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'survivor_closure_report.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'provenance': 'verification_generated_from_current_run_and_compare', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'audit_surface_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'artifact_contract_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'family_completeness_matrix.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
        ],
    }


def _build_family_completeness_matrix(account_state, stat_inputs) -> dict:
    from collections import Counter
    family_totals = Counter(row.source_family for row in stat_inputs)
    mapped_totals = Counter(row.source_family for row in stat_inputs if row.kb_mapped)
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    perk_presets = getattr(account_state, 'perk_presets', {}) or {}
    preset_lane_completeness = {}
    for preset in CANONICAL_PRESET_NAMES:
        preset_lane_completeness[preset] = {
            'cards_explicit': preset in card_presets,
            'cards_empty': preset in card_presets and not bool(card_presets.get(preset)),
            'modules_explicit': preset in module_presets,
            'modules_empty': preset in module_presets and not bool(module_presets.get(preset)),
            'perks_explicit': preset in perk_presets,
            'perks_empty': preset in perk_presets and not bool(perk_presets.get(preset)),
        }
    families = {}
    for family in sorted(set(family_totals) | {'workshop','lab','card','module','module_substat','relic','vault','enhancement','uw','bot','guardian','uw_plus'}):
        total_rows = int(family_totals.get(family, 0))
        mapped_rows = int(mapped_totals.get(family, 0))
        families[family] = {
            'total_rows': total_rows,
            'mapped_rows': mapped_rows,
            'unmapped_rows': total_rows - mapped_rows,
        }
    return {
        'version': 1,
        'canonical_output_preset': getattr(account_state, 'default_preset', None),
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': _synthetic_preset_names_present(account_state),
        'preset_lane_completeness': preset_lane_completeness,
        'families': families,
    }
"""

OLD_WRITE = """    (args.out / 'audit_surface_manifest.json').write_text(
        json.dumps(_json_sanitize(_build_audit_surface_manifest(account_state, args.preset)), indent=2, default=str)
    )
"""
NEW_WRITE = """    (args.out / 'audit_surface_manifest.json').write_text(
        json.dumps(_json_sanitize(_build_audit_surface_manifest(account_state, args.preset)), indent=2, default=str)
    )
    (args.out / 'artifact_contract_manifest.json').write_text(
        json.dumps(_json_sanitize(_build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)), indent=2, default=str)
    )
    (args.out / 'family_completeness_matrix.json').write_text(
        json.dumps(_json_sanitize(_build_family_completeness_matrix(account_state, stat_inputs)), indent=2, default=str)
    )
"""

OLD_C14 = "| C14 | TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS | Artifact classes and provenance | C1, C5, C12, C13 | C2 | Codex-ready after dependency | artifact class taxonomy | run_stats/output writers | do not leave provenance implicit | `registry/output_contracts.md`; `tests/test_artifact_contracts.py`; regenerated artifact set with class/provenance fields | implementation + tests + regenerated artifacts | human review required | optimizer math | not started |"
NEW_C14 = "| C14 | TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS | Artifact classes and provenance | C1, C5, C12, C13 | C2 | Closed | artifact class taxonomy | run_stats/output writers | do not leave provenance implicit | `registry/output_contracts.md`; `tests/test_artifact_contracts.py`; regenerated artifact set with class/provenance fields | implementation + tests + regenerated artifacts | human review required | optimizer math | implemented_pending_review |"
OLD_C15 = "| C15 | TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT | Tests, fixtures, and false-green cleanup | C1, C2, C5, C11, C12, C13, C14 | C16 | Post-contract cleanup | fixture refresh policy | test/fixture layer | do not update tests before contracts settle | refreshed golden fixtures; `tests/test_five_preset_completeness.py`; removed stale/synthetic expectations from canonical tests | implementation + tests + fixture refresh | human review required | new feature tests | not started |"
NEW_C15 = "| C15 | TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT | Tests, fixtures, and false-green cleanup | C1, C2, C5, C11, C12, C13, C14 | C16 | Closed | fixture refresh policy | test/fixture layer | do not update tests before contracts settle | refreshed golden fixtures; `tests/test_five_preset_completeness.py`; removed stale/synthetic expectations from canonical tests | implementation + tests + fixture refresh | human review required | new feature tests | implemented_pending_review |"
OLD_C16 = "| C16 | TRANCHE_IDS_C16_COMPLETENESS_MATRIX | Full family completeness artifact and CI gate | C1, C5, C13, C14 | C15 | Codex-ready after dependency | exact matrix schema | audit/verification artifact layer | do not infer completeness from partial views | `out/family_completeness_matrix.json`; `tests/test_family_completeness_matrix.py`; CI gate | implementation + tests + CI | human review required | unrelated dashboards | not started |"
NEW_C16 = "| C16 | TRANCHE_IDS_C16_COMPLETENESS_MATRIX | Full family completeness artifact and CI gate | C1, C5, C13, C14 | C15 | Closed | exact matrix schema | audit/verification artifact layer | do not infer completeness from partial views | `out/family_completeness_matrix.json`; `tests/test_family_completeness_matrix.py`; CI gate | implementation + tests + CI | human review required | unrelated dashboards | implemented_pending_review |"


def patch_text(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding='utf-8')
    if new in text:
        return False
    if old not in text:
        raise SystemExit(f'Missing anchor for {label} in {path}')
    path.write_text(text.replace(old, new), encoding='utf-8')
    return True


def main():
    changed = []
    rs_text = RUN_STATS.read_text(encoding='utf-8')
    if '_build_artifact_contract_manifest' not in rs_text:
        if INSERT_AFTER not in rs_text:
            raise SystemExit('Missing INSERT_AFTER anchor in run_stats.py')
        rs_text = rs_text.replace(INSERT_AFTER, INSERT_AFTER + ADD_BLOCK)
        changed.append('run_stats.py:function_block')
    if 'artifact_contract_manifest.json' not in rs_text:
        if OLD_WRITE not in rs_text:
            raise SystemExit('Missing output-write anchor in run_stats.py')
        rs_text = rs_text.replace(OLD_WRITE, NEW_WRITE)
        changed.append('run_stats.py:output_writes')
    RUN_STATS.write_text(rs_text, encoding='utf-8')

    for old, new, label in [
        (OLD_C14, NEW_C14, 'C14'),
        (OLD_C15, NEW_C15, 'C15'),
        (OLD_C16, NEW_C16, 'C16'),
    ]:
        if patch_text(CONTROL, old, new, label):
            changed.append(f'IDS_EXECUTION_CONTROL_REGISTER.md:{label}')

    print('Applied:', ', '.join(changed) if changed else 'already applied')

if __name__ == '__main__':
    main()
