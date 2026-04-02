from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.loader import IDS_CSV_PATH, load_inputs
from input.loader import _load_json_optional, _load_json_required, _load_yaml_required

pytestmark = pytest.mark.live


def test_load_yaml_required__malformed_yaml__raises_value_error_with_path_and_reason(tmp_path: Path):
    target = tmp_path / "manual_inputs.yaml"
    target.write_text("loadout: [", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            rf"manual_inputs: failed to parse YAML at {re.escape(str(target))}:"
        ),
    ):
        _load_yaml_required(target, context="manual_inputs")


def test_load_json_required__malformed_json__raises_value_error_with_path_and_reason(tmp_path: Path):
    target = tmp_path / "perks_derived.json"
    target.write_text("{bad json", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            rf"perks_derived: failed to parse JSON at {re.escape(str(target))}:"
        ),
    ):
        _load_json_required(target, context="perks_derived")


def test_load_inputs__missing_required_file__raises_filenotfounderror_with_path(tmp_path: Path):
    missing_manual = tmp_path / "missing_manual_inputs.yaml"
    perks = tmp_path / "perks_derived.json"
    perks.write_text("{}", encoding="utf-8")

    with pytest.raises(
        FileNotFoundError,
        match=rf"manual_inputs: required file not found: {re.escape(str(missing_manual))}",
    ):
        load_inputs(
            ids_path=IDS_CSV_PATH,
            manual_inputs_path=missing_manual,
            perks_derived_path=perks,
        )


def test_load_inputs__wrong_top_level_types__raise_value_error_with_path(tmp_path: Path):
    manual = tmp_path / "manual_inputs.yaml"
    manual.write_text("- not-a-dict\n", encoding="utf-8")
    perks = tmp_path / "perks_derived.json"
    perks.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            rf"manual_inputs: expected top-level YAML mapping \(dict\) at {re.escape(str(manual))}, got list"
        ),
    ):
        load_inputs(
            ids_path=IDS_CSV_PATH,
            manual_inputs_path=manual,
            perks_derived_path=perks,
        )

    manual.write_text("{}", encoding="utf-8")
    with pytest.raises(
        ValueError,
        match=(
            rf"perks_derived: expected top-level JSON object \(dict\) at {re.escape(str(perks))}, got list"
        ),
    ):
        load_inputs(
            ids_path=IDS_CSV_PATH,
            manual_inputs_path=manual,
            perks_derived_path=perks,
        )


def test_load_inputs__success_path_with_required_inputs_and_optional_manifest_fallback(tmp_path: Path):
    manual = tmp_path / "manual_inputs.yaml"
    manual.write_text(
        "loadout:\n  mode: test\nperk_config:\n  projected_perks: false\n",
        encoding="utf-8",
    )
    perks = tmp_path / "perks_derived.json"
    perks.write_text('{"perks": {}}', encoding="utf-8")

    bundle = load_inputs(
        ids_path=IDS_CSV_PATH,
        manual_inputs_path=manual,
        perks_derived_path=perks,
    )

    assert bundle.manual_inputs["loadout"]["mode"] == "test"
    assert bundle.perk_config["projected_perks"] is False
    assert bundle.perks_derived["perks"] == {}

    missing_manifest = tmp_path / "missing_manifest.json"
    assert _load_json_optional(missing_manifest) == {}
