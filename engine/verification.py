# engine/verification.py -- SHIM (T9: authority moved to evaluators/compare.py)
from evaluators.compare import (
    kb_alignment_status_from_compare_status,
    verdict_from_verification,
    build_compare_status_summary,
    classify_compare_status,
    annotate_compare_display_fields,
    build_ep_compare,
    ensure_compare_authoritative_verdict_fields,
    ensure_line_verification_authoritative_verdict_fields,
    build_survivor_closure_report,
    build_survivability_residue_analysis,
    build_line_by_line_verification,
)
