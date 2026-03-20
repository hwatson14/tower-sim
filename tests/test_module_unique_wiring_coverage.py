from pathlib import Path
import csv
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")

def test_all_module_unique_scalars_have_contract_and_mapping():
    rows = list(csv.DictReader(open(ROOT / "kb/modules/contracts/module-unique-mechanic-contracts.csv")))
    mech = yaml.safe_load(open(ROOT / "kb/global-rules/contracts/mechanic-params.yaml"))
    routes = yaml.safe_load(open(ROOT / "kb/global-rules/contracts/contributor-mappings-full.yaml"))["source_families"]["module"]
    mech_ids = {row["id"] for row in mech["domains"]["modules.uniques"]}
    route_ids = {row["contributor_id"] for row in routes}
    slot_slug = {"Cannon": "cannon", "Armor": "armor", "Generator": "generator", "Core": "core"}
    missing = []
    for row in rows:
        module_slug = _slug(row["module"])
        scalar = row["scalar_param"]
        mech_id = f"module.{module_slug}.{scalar}"
        route_id = f"module__{slot_slug[row['slot']]}__{module_slug}__{scalar}"
        if mech_id not in mech_ids or route_id not in route_ids:
            missing.append((row["module"], mech_id, route_id))
    assert not missing, missing
