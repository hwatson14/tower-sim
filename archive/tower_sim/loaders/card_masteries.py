from __future__ import annotations

from pathlib import Path

from tower_sim.libs.card_masteries_lib import CardMasteryRow, load_card_mastery_map


def load_card_masteries(path: Path | None = None) -> dict[str, CardMasteryRow]:
    return load_card_mastery_map(path)


__all__ = ["CardMasteryRow", "load_card_masteries"]
