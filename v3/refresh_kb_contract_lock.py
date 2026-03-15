from __future__ import annotations

from pathlib import Path

import yaml

from v3.kb_access import content_sha256

_LOCK_PATH = Path("v3/kb_contract_lock.yaml")
_CONTRACT_PATHS = (
    "kb/global-rules/contracts/ids-section-routing.yaml",
    "kb/global-rules/contracts/naming-contract.yaml",
)


def main() -> None:
    payload = {
        "canonical_kb_root": "kb",
        "contracts": {path: content_sha256(path) for path in _CONTRACT_PATHS},
    }
    _LOCK_PATH.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"Wrote {_LOCK_PATH}")


if __name__ == "__main__":
    main()
