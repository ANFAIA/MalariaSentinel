"""One-shot header harvest: read bibliographic fields from a paper's Markdown header.

Pure functions over strings, so the harvest can be tested without touching
``papers/``. The header format is the one used by the curated summaries::

    # <title>
    **Authors:** <authors>
    **Journal:** <journal> | **Year:** <year> | **DOI:** <doi>

Fields that cannot be parsed are returned as ``None`` and reported in
``warnings``. The caller decides what to do with them; nothing is written here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HEADER_LINES = 40

_DOI_TOKEN = re.compile(r"10\.\d{4,9}/[^\s|\"<>]+")
_DOI_LABEL = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s|\"<>]+)", re.IGNORECASE)
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2}|21\d{2})\b")
_CLOSERS = {")": "(", "]": "["}


@dataclass(frozen=True)
class Harvest:
    """Bibliographic fields read from a PDF's first pages, with any parsing warnings."""
    title: str | None
    authors: str | None
    journal: str | None
    year: int | None
    doi: str | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def clean_doi(raw: str) -> str | None:
    """Strip prose punctuation that trails a DOI in running text.

    Closing brackets are removed only when unbalanced, so DOIs that legitimately
    contain parentheses or square brackets survive intact.
    """
    s = raw.strip().rstrip(".,;:*_`'\"")
    while s and s[-1] in _CLOSERS and s.count(s[-1]) > s.count(_CLOSERS[s[-1]]):
        s = s[:-1].rstrip(".,;:*_`'\"")
    return s or None


def _field_value(head: str, name: str) -> str | None:
    match = re.search(rf"\*\*{re.escape(name)}:\*\*[ \t]*([^\n]*)", head)
    return match.group(1).strip() if match else None


def harvest_header(text: str) -> Harvest:
    """Parse the bibliographic fields of a paper Markdown file from its first lines."""
    head = "\n".join(text.splitlines()[:HEADER_LINES])
    warnings: list[str] = []

    title = None
    for line in head.splitlines():
        if line.startswith("# "):
            title = line[2:].strip() or None
            break
    if title is None:
        warnings.append("no level-1 title line")

    authors = _field_value(head, "Authors")
    if not authors:
        warnings.append("no **Authors:** field")
        authors = None

    journal_raw = _field_value(head, "Journal")
    journal = journal_raw.split("|", 1)[0].strip() if journal_raw else None
    if not journal:
        warnings.append("no **Journal:** field")
        journal = None

    year_raw = _field_value(head, "Year")
    year = None
    if year_raw:
        match = _YEAR.search(year_raw)
        year = int(match.group(1)) if match else None
    if year is None:
        warnings.append("no parsable **Year:** field")

    doi = None
    doi_raw = _field_value(head, "DOI")
    if doi_raw:
        token = _DOI_TOKEN.search(doi_raw)
        doi = clean_doi(token.group(0)) if token else None
        if doi is None:
            warnings.append(f"**DOI:** field does not contain a DOI: {doi_raw!r}")
    if doi is None:
        label = _DOI_LABEL.search(head)
        if label:
            doi = clean_doi(label.group(1))
            warnings.append("DOI taken from a doi: token, not from a **DOI:** field")
    if doi is None:
        warnings.append("no DOI in header")

    loose = {clean_doi(m.group(0)) for m in _DOI_TOKEN.finditer(head)} - {None}
    if doi is not None and len(loose - {doi}) > 0:
        warnings.append(f"header mentions other DOIs: {sorted(loose - {doi})}")

    return Harvest(
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        doi=doi,
        warnings=tuple(warnings),
    )
