from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.util.ids_state import IdsState
from tower_sim.run.problem_spec import ProblemSpec
from tower_sim.loaders.sources import DatasetBundle, IdsOnlyBundle, load_ids_only_bundle, load_snapshot_bundle
from tower_sim.run.spec_loader import spec_as_dict

LOGGER = logging.getLogger(__name__)


def run(
    problem_spec: ProblemSpec,
    ids_path: Optional[Path] = None,
    ids_state: Optional[IdsState] = None,
) -> Dict[str, Any]:
    bundle = _resolve_bundle()
    resolved_ids_state = _resolve_ids_state(bundle, ids_path, ids_state)
    if resolved_ids_state is None:
        return {
            "evaluator": problem_spec.evaluator,
            "fail_closed": True,
            "missing": ["ids_state"],
            "w_max": None,
        }

    _log_problem_spec(problem_spec)

    evaluator = MaxWaveEvaluator()
    result = evaluator.evaluate(problem_spec, resolved_ids_state)
    result["resolved_from"] = bundle.resolved_from
    return result


def _resolve_bundle() -> DatasetBundle | IdsOnlyBundle:
    try:
        return load_snapshot_bundle(_default_cache_dirs())
    except FileNotFoundError:
        return load_ids_only_bundle(_default_ids_paths())


def _default_cache_dirs():
    from tower_sim.libs.data_paths import DEFAULT_DATA_DIRS

    return list(DEFAULT_DATA_DIRS)


def _default_ids_paths():
    from tower_sim.loaders.ids_parser import DEFAULT_IDS_PATHS

    return list(DEFAULT_IDS_PATHS)


def _resolve_ids_state(
    bundle: DatasetBundle | IdsOnlyBundle,
    ids_path: Optional[Path],
    ids_state: Optional[IdsState],
) -> Optional[IdsState]:
    if ids_state is not None:
        return ids_state
    try:
        if ids_path is not None:
            return parse_ids(ids_path)
        if isinstance(bundle, DatasetBundle) and "_IDS.csv" in bundle.files:
            return parse_ids(bundle.files["_IDS.csv"])
        if isinstance(bundle, IdsOnlyBundle):
            return parse_ids(bundle.ids_path)
    except (FileNotFoundError, ValueError):
        return None
    return None


def _log_problem_spec(problem_spec: ProblemSpec) -> None:
    payload = json.dumps(spec_as_dict(problem_spec), sort_keys=True)
    LOGGER.info("Resolved ProblemSpec: %s", payload)
