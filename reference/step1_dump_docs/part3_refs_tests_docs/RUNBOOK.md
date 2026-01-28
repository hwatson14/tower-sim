
RUNBOOK (Step 1 freeze)

This repo is a recovery snapshot that is designed to be runnable and fail-closed.
It is NOT yet a full gameplay simulator. Until the combat/perk/workshop engines
are reconstructed, execution will intentionally block with a structured reason.

Prereqs
1. Python 3.11+ (3.10 may work, but Step 1 is tested on 3.11 in this environment)

Authoritative input
* The only runtime input is a wide _IDS.csv export.
* This repo ships a default at: refs/_IDS.csv

Quick commands
1) Basic entry (validates then attempts execution)
   python main.py

2) One-line runner (preferred UX)
   python run_cmd.py "Milestone t17" --ids refs/_IDS.csv --out out.json
   python run_cmd.py "Farm t14" --ids refs/_IDS.csv --out out.json

Tournament tokens (placeholders by design)
* Champs / Legends are present as placeholder entries and MUST be filled in
  refs/league_map.json before tournament runs are allowed.

IDS ABI lock drift
* The loader fail-closes if the wide IDS header row drifts from the locked header
  in refs/ids_abi_lock/IDS_ABI_LOCKED_RAW_v1.csv.
* If you update refs/_IDS.csv (new export), regenerate the lock artifacts:
  python tools/update_ids_abi_lock.py --ids refs/_IDS.csv

Tests
   pytest

Expected Step-1 behavior
* If engines are still stubs, run_cmd.py will write out.json with execution_blocked=true
  and a clear reason (e.g., IDS ABI drift or combat engine not implemented).
