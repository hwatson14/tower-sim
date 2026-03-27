"""
parsers/ids_parser.py — BACKWARD-COMPAT SHIM. Authority: input/parsers.py.

This file re-exports from input.parsers. Do not add logic here.
It will be demoted to archive/legacy/ in T8 once all callers have migrated
to import from input.parsers directly.

Transitional callers (test files): see tests/test_*.py — these will be
updated or removed in T7.
"""
# Re-export everything the shim consumers import
from input.parsers import parse_ids, SectionSpec, SECTION_SPECS  # noqa: F401
# IdsRaw still lives in models/ids_raw.py (moves to qe/models.py in T3)
from models.ids_raw import IdsRaw  # noqa: F401
