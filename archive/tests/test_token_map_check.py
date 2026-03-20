from __future__ import annotations

from pathlib import Path

import yaml

from tower_sim.audit import token_map_check


def _write(path: Path, text: str) -> None:
    path.write_text(text)


def test_parse_token_inventory_extracts_tokens(tmp_path: Path) -> None:
    markdown = tmp_path / "inventory.md"
    _write(
        markdown,
        "\n".join(
            [
                "# Title",
                "## Workbook One.xlsx",
                "### Sheet: Alpha",
                "- `TOK_ALPHA`: 1 unique formulas",
                "### Sheet: Beta",
                "- `TOK_BETA`: 2 unique formulas",
            ]
        ),
    )

    occurrences = token_map_check.parse_token_inventory(markdown)

    assert set(occurrences) == {"TOK_ALPHA", "TOK_BETA"}
    assert occurrences["TOK_ALPHA"][0].workbook == "Workbook One.xlsx"
    assert occurrences["TOK_ALPHA"][0].sheet == "Alpha"


def test_validate_sources_flags_missing_unmapped_and_conflicts(
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "inventory.md"
    _write(
        markdown,
        "\n".join(
            [
                "## Workbook One.xlsx",
                "### Sheet: Alpha",
                "- `TOK_A`: 1 unique formulas",
                "- `TOK_B`: 1 unique formulas",
                "- `TOK_C`: 1 unique formulas",
            ]
        ),
    )
    inventory = token_map_check.parse_token_inventory(markdown)

    source_map_path = tmp_path / "map.yaml"
    source_entries = [
        {
            "token": "TOK_A",
            "gate": "A",
            "source_type": "repo_csv",
            "source_path": "tables/a.csv",
            "source_locator": "col: a",
            "notes": "primary",
        },
        {
            "token": "TOK_A",
            "gate": "A",
            "source_type": "effective_paths_sheet",
            "source_path": "tables/a.xlsx",
            "source_locator": "Sheet: Alpha",
            "notes": "conflict",
        },
        {
            "token": "TOK_B",
            "gate": "A",
            "source_type": "unknown",
            "source_path": "",
            "source_locator": "",
            "notes": "",
        },
    ]
    source_map_path.write_text(yaml.safe_dump(source_entries, sort_keys=False))

    sources = token_map_check.load_token_sources(source_map_path)
    missing, unmapped, conflicts = token_map_check.validate_sources(inventory, sources)

    assert missing == ["TOK_C"]
    assert unmapped == ["TOK_B"]
    assert "TOK_A" in conflicts
