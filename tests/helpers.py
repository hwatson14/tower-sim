from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from parsers.ids_parser import parse_ids



def build_state():
    ids = parse_ids(ROOT / 'input' / '_IDS.csv')
    loadout = json.loads((ROOT / 'input' / 'loadout.json').read_text())
    perks = json.loads((ROOT / 'input' / 'perks.json').read_text())
    return compile_account_state(ids, default_preset='Farming', loadout_config=loadout, perk_config=perks)
