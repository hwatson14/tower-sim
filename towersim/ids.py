
from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

@dataclass
class IDSSection:
    name: str
    start_row: int
    end_row: int
    df: pd.DataFrame

class IDS:
    """
    Minimal IDS parser:
    - Splits by header rows where column A contains a section label (e.g. 'LABS', 'WORKSHOP', 'UWS', 'MODULES', etc.)
    - Preserves raw positions for auditing.
    """
    def __init__(self, df: pd.DataFrame):
        self.raw = df
        self.sections: Dict[str, IDSSection] = self._split_sections()

    def _is_header(self, cell) -> bool:
        return isinstance(cell, str) and cell.strip() != "" and cell.strip() == cell.strip().upper()

    def _split_sections(self) -> Dict[str, IDSSection]:
        sections = {}
        current_name = None
        start = None
        for i in range(len(self.raw)):
            cell = self.raw.iloc[i, 0] if self.raw.shape[1] > 0 else None
            if self._is_header(cell):
                # close previous
                if current_name is not None:
                    end = i - 1
                    sections[current_name] = IDSSection(
                        name=current_name,
                        start_row=start,
                        end_row=end,
                        df=self.raw.iloc[start:end+1].copy()
                    )
                current_name = str(cell).strip()
                start = i + 1
        # close last
        if current_name is not None and start is not None:
            end = len(self.raw) - 1
            sections[current_name] = IDSSection(
                name=current_name,
                start_row=start,
                end_row=end,
                df=self.raw.iloc[start:end+1].copy()
            )
        return sections

    def get_section(self, name: str) -> pd.DataFrame:
        if name not in self.sections:
            raise KeyError(f"Section not found in _IDS: {name}. Available: {list(self.sections.keys())}")
        return self.sections[name].df
