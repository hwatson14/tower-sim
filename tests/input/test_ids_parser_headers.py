from __future__ import annotations

import pytest

from input.ids_parser import SECTION_SPECS, _fail_unknown_sections


def _base_rows() -> list[list[str]]:
    width = max(spec.header_col for spec in SECTION_SPECS) + 1
    header = [""] * width
    for spec in SECTION_SPECS:
        header[spec.header_col] = spec.name
    values = [""] * width
    return [header, values]


def test_fail_unknown_sections__accepts_valid_version_token_header() -> None:
    rows = _base_rows()
    rows[0][43] = "v1.2.3"
    _fail_unknown_sections(rows)


def test_fail_unknown_sections__rejects_non_version_v_prefixed_header() -> None:
    rows = _base_rows()
    rows[0][43] = "vNext-release"
    rows[1][43] = "payload"

    with pytest.raises(ValueError, match=r"'vNext-release' at column 43"):
        _fail_unknown_sections(rows)


def test_fail_unknown_sections__reports_unknown_header_and_column_context() -> None:
    rows = _base_rows()
    rows[0][43] = "Mystery Header"
    rows[1][43] = "payload"

    with pytest.raises(ValueError, match=r"'Mystery Header' at column 43\. First row value: 'payload'"):
        _fail_unknown_sections(rows)
