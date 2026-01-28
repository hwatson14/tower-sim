from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_DATA_DIRS: Sequence[Path] = (
    Path("tests/fixtures/tower-sim-data"),
    Path("tests/fixtures"),
    Path("data/tower-sim-data"),
)


def resolve_data_file(filename: str, search_dirs: Iterable[Path] = DEFAULT_DATA_DIRS) -> Path:
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.exists():
            return candidate
    candidates = ", ".join(str(Path(directory) / filename) for directory in search_dirs)
    raise FileNotFoundError(f"Missing data file {filename}. Tried: {candidates}")
