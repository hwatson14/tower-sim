from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
from typing import Any, Dict, Mapping

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from tower_sim.run.api import TASK_MAX_WAVE, run_task  # noqa: E402
from tower_sim.run.spec_loader import parse_problem_spec_data  # noqa: E402


_OUT_DIR = Path("out/max_wave_runner")
_OUT_RUNNER_PATH = _OUT_DIR / "runner_output_latest.json"
_OUT_MAX_WAVE_PATH = _OUT_DIR / "max_wave_latest.json"


def run(
    *,
    spec_path: Path,
    ids_path: Path | None = None,
    patch_path: Path | None = None,
) -> Dict[str, Any]:
    if not spec_path.exists():
        raise FileNotFoundError(f"Problem spec not found: {spec_path}")
    if ids_path is not None and not ids_path.exists():
        raise FileNotFoundError(f"IDS snapshot not found: {ids_path}")
    if patch_path is not None and not patch_path.exists():
        raise FileNotFoundError(f"Patch spec not found: {patch_path}")

    spec_data = _load_yaml_mapping(spec_path)
    if patch_path is not None:
        patch_data = _load_yaml_mapping(patch_path)
        spec_data = _overlay_mapping(spec_data, patch_data)

    parsed_spec = parse_problem_spec_data(spec_data)
    result = run_task(
        TASK_MAX_WAVE,
        {"problem_spec": asdict(parsed_spec)},
        ids_path=ids_path,
    )
    if not bool(result.get("ok")):
        missing = result.get("missing", [])
        raise RuntimeError(f"MAX_WAVE runner fail-closed. Missing inputs: {missing}")
    _write_json(_OUT_RUNNER_PATH, result)
    _write_json(_OUT_MAX_WAVE_PATH, result.get("result", {}))
    return result


def _load_yaml_mapping(path: Path) -> Dict[str, Any]:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a mapping in YAML file: {path}")
    return dict(raw)


def _overlay_mapping(base: Mapping[str, Any], patch: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, patch_value in patch.items():
        base_value = merged.get(key)
        if isinstance(base_value, Mapping) and isinstance(patch_value, Mapping):
            merged[key] = _overlay_mapping(base_value, patch_value)
            continue
        merged[key] = patch_value
    return merged


def _to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, tuple):
        return [_to_dict(item) for item in value]
    if isinstance(value, list):
        return [_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _to_dict(v) for k, v in value.items()}
    return value


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical MAX_WAVE v1 runner.")
    parser.add_argument("--spec", type=Path, required=True, help="Problem spec YAML path.")
    parser.add_argument(
        "--patch",
        type=Path,
        default=None,
        help="Optional YAML patch applied as a pure overlay before execution.",
    )
    parser.add_argument(
        "--ids",
        type=Path,
        default=None,
        help="Path to _IDS.csv (defaults to canonical loader fallback).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run(spec_path=args.spec, patch_path=args.patch, ids_path=args.ids)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Wrote {_OUT_RUNNER_PATH}")
    print(f"Wrote {_OUT_MAX_WAVE_PATH}")
    payload = result.get("result", {}) if isinstance(result, Mapping) else {}
    diagnostics = payload.get("diagnostics", {}) if isinstance(payload, Mapping) else {}
    print(
        "SUMMARY "
        f"w_max={payload.get('w_max')} "
        f"contract_status={diagnostics.get('contract_status')} "
        f"unmapped_hard_count={diagnostics.get('unmapped_hard_count')} "
        f"fail_closed={payload.get('fail_closed')}"
    )


if __name__ == "__main__":
    main()
