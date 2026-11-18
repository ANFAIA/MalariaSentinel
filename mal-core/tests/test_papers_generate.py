"""REFERENCES.md generation: header on every table (line-57 regression), determinism, drift gate."""
from __future__ import annotations

from _papers_fixtures import make_entry, make_manifest, two_entry_manifest
from mal_core.papers.generate import (
    HEADERS,
    is_up_to_date,
    render_references,
    write_references,
)
from mal_core.papers.manifest import parse_manifest


def _tables(text: str) -> list[list[str]]:
    """Every contiguous block of lines that starts with '|'."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def test_every_table_has_a_header_and_separator_row():
    text = render_references(parse_manifest(two_entry_manifest()))
    tables = _tables(text)
    assert len(tables) == 2  # one per theme
    for table in tables:
        assert table[0] == "| " + " | ".join(HEADERS) + " |"
        assert table[1] == "|" + "|".join("---" for _ in HEADERS) + "|"
        # Escaped pipes (\\|) inside cells are content, not column separators.
        unescaped = [row.replace("\\|", "").count("|") for row in table]
        assert len(set(unescaped)) == 1, "ragged table row"


def test_no_blank_line_splits_a_table():
    text = render_references(parse_manifest(two_entry_manifest()))
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and lines[i + 1] == "" and i + 2 < len(lines):
            assert not lines[i + 2].startswith("|"), f"table split at line {i + 2}"


def test_rendering_is_deterministic_and_independent_of_entry_order():
    data = two_entry_manifest()
    reversed_data = make_manifest(*reversed(data["entries"]))
    first = render_references(parse_manifest(data))
    assert first == render_references(parse_manifest(data))
    assert first == render_references(parse_manifest(reversed_data))


def test_sections_are_themes_in_alphabetical_order():
    text = render_references(parse_manifest(two_entry_manifest()))
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == ["## abm-geospatial", "## core-hypothesis"]


def test_doi_is_linked_and_missing_doi_is_shown_as_none():
    entries = [
        make_entry(),
        make_entry(
            id="local:no-doi-paper",
            doi=None,
            slug="no-doi-paper",
            expected_status="pending_no_source",
        ),
    ]
    text = render_references(parse_manifest(make_manifest(*entries)))
    assert "[10.1186/s12936-000-0001-x](https://doi.org/10.1186/s12936-000-0001-x)" in text
    assert "| none | pending_no_source |" in text


def test_null_bibliographic_fields_render_as_visible_gaps_and_sort_without_error():
    entries = [
        make_entry(authors=None, year=None, journal=None, doi=None, id="local:internal-note",
                   slug="internal-note", expected_status="pending_no_source"),
        make_entry(),
    ]
    text = render_references(parse_manifest(make_manifest(*entries)))
    assert "[no authors recorded]. A fixture paper. (n.d.)." in text


def test_pipes_in_cells_are_escaped():
    text = render_references(parse_manifest(two_entry_manifest()))
    assert "Host seeking \\| a fixture with a pipe" in text
    for line in text.splitlines():
        if line.startswith("| 2 "):
            assert line.count("|") == line.count("\\|") + 7


def test_citation_format_and_status_column():
    text = render_references(parse_manifest(two_entry_manifest()))
    assert "Doe J, Roe R. A fixture paper. *Malaria Journal* (2020)." in text
    assert "| pending_paywalled |" in text


def test_write_reports_change_and_drift_gate(tmp_path):
    manifest = parse_manifest(two_entry_manifest())
    target = tmp_path / "REFERENCES.md"
    assert not is_up_to_date(manifest, target)
    assert write_references(manifest, target) is True
    assert write_references(manifest, target) is False
    assert is_up_to_date(manifest, target)
    target.write_text(target.read_text(encoding="utf-8") + "hand edit\n", encoding="utf-8")
    assert not is_up_to_date(manifest, target)
