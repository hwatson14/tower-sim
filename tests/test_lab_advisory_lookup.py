from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.lab_advisory import (
    get_lab_advisory_row,
    load_lab_advisory_rows,
    load_lab_advisory_source_registry,
)


def test_lab_advisory_rows_lookup_by_canonical_id_preserves_archive_provenance_and_notes():
    workshop_enhancement = get_lab_advisory_row('LAB_WORKSHOP_ENHANCEMENT')
    assert workshop_enhancement.lab_name == 'Workshop Enhancements'
    assert workshop_enhancement.mapping_status == 'manual_alias_override'
    assert workshop_enhancement.ranking_primary == 'B'
    assert workshop_enhancement.ranking_conditional == 'S'
    assert workshop_enhancement.notes == 'becomes required to progress after 1T~ LTC'
    assert workshop_enhancement.source_workbook == 'Copy of Laboratory v2.5.7.xlsx'
    assert workshop_enhancement.source_sheet == 'Tier List / Remote Tier List'
    assert workshop_enhancement.source_version == 'Updated for version 27.0.3'

    wall_thorns = get_lab_advisory_row('LAB_WALL_THORN')
    assert wall_thorns.lab_name == 'Wall Thorns'
    assert wall_thorns.ranking_primary == 'S'
    assert wall_thorns.ranking_conditional == 'C'
    assert 'useful percentage damage' in (wall_thorns.notes or '')


def test_lab_advisory_rows_are_non_mechanical_and_fail_closed_to_known_registry():
    rows = load_lab_advisory_rows()
    assert len(rows) == 180
    assert all(row.lab_canonical_id.startswith('LAB_') for row in rows)
    assert all(row.advisory_status == 'non-mechanical' for row in rows)
    assert all(row.evidence_type == 'advisory_heuristic' for row in rows)
    assert all(row.authoritative_for == 'planner/advisor prior only' for row in rows)
    assert all('runtime formulas' in row.not_authoritative_for for row in rows)

    registry_rows = load_lab_advisory_source_registry()
    assert len(registry_rows) == 1
    registry_row = registry_rows[0]
    assert registry_row.canonical_location == 'kb/labs/advisory/tables/lab-tier-list-v27_0_3.csv'
    assert 'mechanics|lab_costs|lab_durations|runtime_formula_truth' == registry_row.do_not_use_for


def test_lab_advisory_rows_map_to_repo_canonical_lab_catalog_with_only_documented_manual_overrides():
    rows = load_lab_advisory_rows()
    catalog_path = ROOT / 'kb' / 'ledgers' / 'sources' / 'raw' / 'repo-meta' / 'registry' / 'catalog.yaml'
    catalog_text = catalog_path.read_text(encoding='utf-8')
    catalog_ids = set(re.findall(r'canonical_id:\s+(LAB_[A-Z0-9_]+)', catalog_text))

    advisory_ids = {row.lab_canonical_id for row in rows}
    assert advisory_ids <= catalog_ids

    manual_override_rows = {row.lab_name: row.lab_canonical_id for row in rows if row.mapping_status == 'manual_alias_override'}
    assert manual_override_rows == {
        'Workshop Enhancements': 'LAB_WORKSHOP_ENHANCEMENT',
        'Enhancement Attack - Coin Discount': 'LAB_ENHANCEMENT_ATTACK_COIN_DISCOUNT',
        'Enhancement Defense - Coin Discount': 'LAB_ENHANCEMENT_DEFENSE_COIN_DISCOUNT',
        'Enhancement Utility - Coin Discount': 'LAB_ENHANCEMENT_UTILITY_COIN_DISCOUNT',
    }


def test_lab_advisory_rankings_are_not_routed_into_mechanical_or_optimizer_surfaces():
    result = subprocess.run(
        [
            'rg',
            '-n',
            'lab-tier-list-v27_0_3\\.csv|ranking_primary|ranking_conditional|planner/advisor prior only',
            'compilers',
            'optimizer',
            'run_stats.py',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout
    assert result.stdout == ''
