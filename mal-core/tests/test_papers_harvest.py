"""Header harvest is a pure function over strings (plan §9 step 2 helper)."""
from __future__ import annotations

from mal_core.papers.harvest import clean_doi, harvest_header

STANDARD = """# Mosquito host seeking in a fixture

**Authors:** Doe J, Roe R, et al.
**Journal:** Malaria Journal | **Year:** 2014 (13:424) | **DOI:** 10.1186/1475-2875-13-424
**File:** papers/abm-geospatial/doe-2014.md

---

## Abstract

Body text that also mentions 10.9999/not-a-header-doi in prose.
"""


def test_standard_header_fields():
    h = harvest_header(STANDARD)
    assert h.title == "Mosquito host seeking in a fixture"
    assert h.authors == "Doe J, Roe R, et al."
    assert h.journal == "Malaria Journal"
    assert h.year == 2014
    assert h.doi == "10.1186/1475-2875-13-424"
    assert h.warnings == ("header mentions other DOIs: ['10.9999/not-a-header-doi']",)


def test_year_with_posted_note_takes_first_year():
    text = "# T\n**Authors:** A B\n**Journal:** Research Square preprint | **Year:** 2026 (posted 5 October 2026) | **DOI:** 10.21203/rs.3.rs-10515996/v1\n"
    h = harvest_header(text)
    assert h.year == 2026
    assert h.doi == "10.21203/rs.3.rs-10515996/v1"


def test_doi_stops_before_pipe_and_pmid_fields():
    text = "# T\n**Authors:** A B\n**Journal:** Nature | **Year:** 2014 | **Volume/Pages:** 516(7531): 387–390 | **DOI:** 10.1038/nature13987 | **PMID:** 25470038\n"
    h = harvest_header(text)
    assert h.doi == "10.1038/nature13987"
    assert h.warnings == ()


def test_doi_with_brackets_survives_and_trailing_bracket_is_trimmed():
    text = "# T\n**Authors:** A B\n**Journal:** J | **Year:** 2007 | **DOI:** 10.1603/0022-2585(2007)44[923:EDASOA]2.0.CO;2\n"
    assert harvest_header(text).doi == "10.1603/0022-2585(2007)44[923:EDASOA]2.0.CO;2"


def test_clean_doi_trims_prose_punctuation_only_when_unbalanced():
    assert clean_doi("10.1000/abc.") == "10.1000/abc"
    assert clean_doi("10.1000/abc).") == "10.1000/abc"
    assert clean_doi("10.1000/a(b)") == "10.1000/a(b)"
    assert clean_doi("   ") is None


def test_doi_label_fallback_is_reported():
    text = "# T\n**Authors:** A B\n**Journal:** J | **Year:** 2001\nSee doi: 10.5555/xyz.9 for details.\n"
    h = harvest_header(text)
    assert h.doi == "10.5555/xyz.9"
    assert "DOI taken from a doi: token" in h.warnings[0]


def test_missing_fields_are_none_and_warned():
    h = harvest_header("Just some prose without a header.\n")
    assert h.title is None and h.authors is None and h.journal is None
    assert h.year is None and h.doi is None
    assert "no DOI in header" in h.warnings
    assert "no parsable **Year:** field" in h.warnings


def test_header_scan_is_limited_to_the_first_lines():
    late = "\n" * 60 + "**DOI:** 10.1000/late.1\n"
    assert harvest_header("# T\n**Authors:** A\n" + late).doi is None
