from __future__ import annotations

import sys
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.ids_parser import parse_ids  # noqa: E402
from tower_sim.statbook_builder import PHASE_END, PHASE_START, build_statbook  # noqa: E402

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _reference_xlsx_path() -> Path:
    reference_dir = Path("reference")
    xlsx_files = sorted(reference_dir.glob("*.xlsx"))
    if len(xlsx_files) != 1:
        raise FileNotFoundError(
            f"Expected exactly one StatBook reference .xlsx in {reference_dir}, "
            f"found {len(xlsx_files)}."
        )
    return xlsx_files[0]


def _inline_string(cell: ET.Element) -> str:
    inline = cell.find("main:is", NS)
    if inline is None:
        return ""
    return "".join(t.text or "" for t in inline.findall(".//main:t", NS))


def _sheet_headers(sheet: ET.Element) -> list[str]:
    for row in sheet.findall("main:sheetData/main:row", NS):
        if row.attrib.get("r") != "1":
            continue
        headers = []
        for cell in row.findall("main:c", NS):
            if cell.attrib.get("t") == "inlineStr":
                headers.append(_inline_string(cell))
        return headers
    return []


def _stat_names_from_sheet(sheet: ET.Element) -> list[str]:
    names: list[str] = []
    for row in sheet.findall("main:sheetData/main:row", NS):
        for cell in row.findall("main:c", NS):
            if not cell.attrib.get("r", "").startswith("A"):
                continue
            if cell.attrib.get("t") != "inlineStr":
                continue
            value = _inline_string(cell)
            if value and value != "Stat":
                names.append(value)
    return names


def test_statbook_reference_structure(tmp_path: Path) -> None:
    reference_path = _reference_xlsx_path()
    with zipfile.ZipFile(reference_path) as archive:
        sheet_names = [
            name for name in archive.namelist() if name.startswith("xl/worksheets/sheet")
        ]
        header_sets = []
        stat_names: set[str] = set()
        for sheet_name in sheet_names:
            sheet = ET.fromstring(archive.read(sheet_name))
            headers = _sheet_headers(sheet)
            if headers:
                header_sets.append(set(headers))
            stat_names.update(_stat_names_from_sheet(sheet))

    expected_headers = {"Stat", "Start of Run Value", "End of Run Value"}
    assert any(expected_headers.issubset(headers) for headers in header_sets)
    assert stat_names

    ids_state = parse_ids()
    statbook = build_statbook(ids_state)
    csv_path = tmp_path / "statbook.csv"
    statbook.to_csv(csv_path)

    phases = {row.phase for row in statbook.rows}
    assert {PHASE_START, PHASE_END}.issubset(phases)
    assert stat_names.intersection({row.stat_name for row in statbook.rows})
