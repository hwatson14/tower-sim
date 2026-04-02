"""
evaluators/ranker.py -- Ranking and sorting.

Owns: path ranking, upgrade candidate ranking, sort-by-score logic.

Extracted from: optimizer/path_ranker.py (T5).
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable
from typing import Mapping
from evaluators.scorer import compute_ehp, compute_edamage, compute_eecon

ROOT = Path(__file__).resolve().parents[1]
_LAB_ADVISORY_TABLE_PATH = ROOT / 'kb' / 'labs' / 'advisory' / 'tables' / 'lab-tier-list-v27_0_3.csv'
_LAB_ADVISORY_SOURCE_REGISTRY_PATH = ROOT / 'kb' / 'labs' / 'advisory' / 'registry' / 'lab-advisory-source-registry.csv'


@dataclass(frozen=True)
class LabAdvisoryInputRow:
    workbook_row: int
    lab_name: str
    unlock_tier: str | None
    ranking_primary: str | None
    ranking_conditional: str | None
    notes: str | None
    is_unlocked_cached: bool | None
    player_ranking_cached: str | None
    status_cached: str | None
    lab_canonical_id: str
    mapping_status: str
    ranking_primary_order: int | None
    ranking_conditional_order: float | None
    evidence_type: str
    source_workbook: str
    source_sheet: str
    source_version: str
    advisory_status: str
    authoritative_for: str
    not_authoritative_for: str


@dataclass(frozen=True)
class LabAdvisorySourceRegistryInputRow:
    advisory_surface_id: str
    surface_name: str
    surface_kind: str
    canonical_location: str
    source_workbook: str
    source_sheet: str
    provenance_note: str
    usage_role: str
    do_not_use_for: str
    version_tag: str


@dataclass(frozen=True)
class LabAdvisoryBundle:
    advisory_rows: tuple[LabAdvisoryInputRow, ...]
    advisory_rows_by_canonical_id: Mapping[str, LabAdvisoryInputRow]
    source_registry_rows: tuple[LabAdvisorySourceRegistryInputRow, ...]


@lru_cache(maxsize=1)
def load_lab_advisory_bundle() -> LabAdvisoryBundle:
    with _LAB_ADVISORY_TABLE_PATH.open(newline='', encoding='utf-8') as handle:
        advisory_rows = tuple(_parse_lab_advisory_input_row(row) for row in csv.DictReader(handle))
    if not advisory_rows:
        raise ValueError('Lab advisory table is empty; advisory imports must fail closed.')

    advisory_rows_by_canonical_id: dict[str, LabAdvisoryInputRow] = {}
    for row in advisory_rows:
        if row.lab_canonical_id in advisory_rows_by_canonical_id:
            raise ValueError(f'Duplicate advisory lab canonical id {row.lab_canonical_id!r}.')
        advisory_rows_by_canonical_id[row.lab_canonical_id] = row

    with _LAB_ADVISORY_SOURCE_REGISTRY_PATH.open(newline='', encoding='utf-8') as handle:
        source_registry_rows = tuple(
            LabAdvisorySourceRegistryInputRow(**row) for row in csv.DictReader(handle)
        )
    if not source_registry_rows:
        raise ValueError('Lab advisory source registry is empty; advisory provenance must fail closed.')

    return LabAdvisoryBundle(
        advisory_rows=advisory_rows,
        advisory_rows_by_canonical_id=advisory_rows_by_canonical_id,
        source_registry_rows=source_registry_rows,
    )


def _parse_lab_advisory_input_row(row: dict[str, str]) -> LabAdvisoryInputRow:
    return LabAdvisoryInputRow(
        workbook_row=int(row['workbook_row']),
        lab_name=row['lab_name'],
        unlock_tier=_optional_str(row['unlock_tier']),
        ranking_primary=_optional_str(row['ranking_primary']),
        ranking_conditional=_optional_str(row['ranking_conditional']),
        notes=_optional_str(row['notes']),
        is_unlocked_cached=_optional_bool(row['is_unlocked_cached']),
        player_ranking_cached=_optional_str(row['player_ranking_cached']),
        status_cached=_optional_str(row['status_cached']),
        lab_canonical_id=row['lab_canonical_id'],
        mapping_status=row['mapping_status'],
        ranking_primary_order=_optional_int(row['ranking_primary_order']),
        ranking_conditional_order=_optional_float(row['ranking_conditional_order']),
        evidence_type=row['evidence_type'],
        source_workbook=row['source_workbook'],
        source_sheet=row['source_sheet'],
        source_version=row['source_version'],
        advisory_status=row['advisory_status'],
        authoritative_for=row['authoritative_for'],
        not_authoritative_for=row['not_authoritative_for'],
    )


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_bool(value: str | None) -> bool | None:
    token = _optional_str(value)
    if token is None:
        return None
    if token == 'True':
        return True
    if token == 'False':
        return False
    raise ValueError(f'Unsupported advisory bool token {value!r}.')


def _optional_int(value: str | None) -> int | None:
    token = _optional_str(value)
    return None if token is None else int(token)


def _optional_float(value: str | None) -> float | None:
    token = _optional_str(value)
    return None if token is None else float(token)


def rank_lab_path(
    run_pipeline: Callable,
    get_lab_duration: Callable,
    candidate_labs: list[str],
    score_fn: Callable,
    current_labs: dict,
    steps: int = 15,
    max_level: int = 100,
) -> list[dict]:
    """
    Greedy lab path optimizer.

    Parameters
    ----------
    run_pipeline : callable(lab_overrides: dict) -> statbook_dict
        Runs the full stat pipeline with optional lab level overrides.
    get_lab_duration : callable(lab_name: str, level: int) -> float
        Returns raw lab duration in days for the given lab at given level.
    candidate_labs : list[str]
        Lab names to consider for upgrades.
    score_fn : callable(rows: dict) -> float
        Composite score function (compute_ehp, compute_edamage, or compute_eecon).
    current_labs : dict
        Current lab levels {lab_name: level}.
    steps : int
        Number of path steps to generate.
    max_level : int
        Maximum lab level to consider.

    Returns
    -------
    list[dict] with keys: step, lab, level, roi, delta_pct, score
    """
    labs = dict(current_labs)
    base_sb = run_pipeline(labs)
    base_score = score_fn(base_sb.get('rows', {}))
    path = []

    for step_num in range(1, steps + 1):
        best = {'roi': -1, 'lab': None, 'level': None, 'score': None}

        for lab in candidate_labs:
            cur = labs.get(lab, 0)
            nxt = cur + 1
            if nxt > max_level:
                continue
            dur = get_lab_duration(lab, nxt)
            if dur >= 1e9:
                continue

            trial = dict(labs)
            trial[lab] = nxt
            new_sb = run_pipeline(trial)
            new_score = score_fn(new_sb.get('rows', {}))
            delta = (new_score / base_score) - 1.0
            roi = delta / dur if dur > 0 else 0

            if roi > best['roi']:
                best = {'roi': roi, 'lab': lab, 'level': nxt, 'score': new_score}

        if best['lab'] is None:
            break

        delta_pct = (best['score'] / base_score - 1.0) * 100
        path.append({
            'step': step_num,
            'lab': best['lab'],
            'level': best['level'],
            'roi_per_day': best['roi'],
            'delta_pct': delta_pct,
            'score': best['score'],
        })

        labs[best['lab']] = best['level']
        base_score = best['score']

    return path


# Pre-defined lab candidate sets per objective
EHP_LABS = [
    'Health', 'Wall Fortification', 'Defense Absolute', 'Defense %',
    'Wall Health', 'Standard Perks Bonus', 'Improve Trade-off Perks',
    'Chrono Field Reduction %', 'Death Wave Health',
    'Assist Module Bonus - Armor', 'Assist Module Substats - Armor',
]

EDAMAGE_LABS = [
    'Damage', 'Attack Speed', 'Critical Chance', 'Critical Factor',
    'Range', 'Damage / Meter', 'Super Critical Chance', 'Super Critical Mult',
    'Assist Module Bonus - Core', 'Assist Module Substats - Core',
]

EECON_LABS = [
    'Coins / Kill Bonus', 'Golden Tower Bonus', 'Golden Tower Duration',
    'Black Hole Coin Bonus', 'Gold Bot - Duration',
    'Assist Module Bonus - Generator', 'Assist Module Substats - Generator',
    'Spotlight Coin Bonus', 'Death Wave Coin Bonus',
]
