from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class IdsRaw:
    ids_path: Path
    header: List[str]
    raw_sections: Dict[str, List[List[str]]]
