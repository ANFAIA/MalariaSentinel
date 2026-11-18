"""Manifest of the paper corpus (``papers/manifest.json``).

The manifest is the single source of truth for the corpus inventory. Its schema
follows docs/plans/in-process/papers-corpus.md section 6.2. This module loads,
validates and dumps it; it never writes to ``papers/`` by itself.

Validation is strict. Unknown keys, duplicate ids, duplicate ``(theme, slug)``
pairs and duplicate DOIs are errors. Two files with the same DOI are the same
paper and must be merged into one entry (D27); they are never accepted silently.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CLASSES = ("A", "B", "C")
STATUSES = (
    "ok",
    "pending_no_source",
    "pending_paywalled",
    "pending_network",
    "pending_extraction_failed",
    "withdrawn",
)
RESOLVERS = ("crossref", "unpaywall", "europe_pmc")

# Entry fields in canonical order. JSON key "class" maps to attribute paper_class.
# observed_status is not a manifest field: the tool writes it to each paper's provenance.yaml (plan §6.2).
FIELDS = (
    "id",
    "class",
    "theme",
    "slug",
    "title",
    "authors",
    "year",
    "journal",
    "doi",
    "alias_of",
    "expected_status",
    "pdf_sha256",
    "resolver",
    "licence_as_recorded",
)
# Optional keys: absent means the default in Entry.
OPTIONAL_FIELDS = ("superseded_files",)
_ATTR = {"class": "paper_class"}
# Bibliographic fields that may be null only when the source header states no value (plan §6.2).
NULLABLE_FIELDS = frozenset({"authors", "year", "journal", "doi", "alias_of", "pdf_sha256", "resolver"})

_ID_RE = re.compile(r"^(doi:[^\s#]+(#[a-z0-9][a-z0-9-]*)?|pmc:(PMC)?[0-9]+|hal:\S+|local:[a-z0-9][a-z0-9-]*)$")
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DOI_RE = re.compile(r"^10\.[0-9]{4,9}/\S+$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """Raised with the full list of validation problems, not just the first."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("invalid papers manifest:\n  - " + "\n  - ".join(self.errors))


@dataclass(frozen=True)
class Entry:
    id: str
    paper_class: str
    theme: str
    slug: str
    title: str
    authors: str | None
    year: int | None
    journal: str | None
    doi: str | None
    alias_of: str | None
    expected_status: str
    pdf_sha256: str | None
    resolver: str | None
    licence_as_recorded: str
    # File names (not paths) of duplicate-DOI files merged into this entry (D27).
    superseded_files: tuple[str, ...] = ()

    @property
    def pdf_relpath(self) -> str:
        """Path of the fetched PDF, relative to the corpus root."""
        return f"{self.theme}/{self.slug}/{self.slug}.pdf"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        kwargs = {_ATTR.get(k, k): data[k] for k in FIELDS}
        kwargs["superseded_files"] = tuple(data.get("superseded_files", ()))
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        out = {k: getattr(self, _ATTR.get(k, k)) for k in FIELDS}
        if self.superseded_files:
            out["superseded_files"] = list(self.superseded_files)
        return out


@dataclass(frozen=True)
class Manifest:
    entries: tuple[Entry, ...]

    def get(self, paper_id: str) -> Entry:
        for entry in self.entries:
            if entry.id == paper_id:
                return entry
        raise KeyError(paper_id)

    def select(self, *, theme: str | None = None, paper_id: str | None = None) -> list[Entry]:
        """Entries filtered by theme and/or id, in manifest order."""
        out = []
        for entry in self.entries:
            if theme is not None and entry.theme != theme:
                continue
            if paper_id is not None and entry.id != paper_id:
                continue
            out.append(entry)
        return out

    def doi_index(self) -> dict[str, str]:
        """Lower-case DOI -> entry id, for entries that have a DOI."""
        return {e.doi.lower(): e.id for e in self.entries if e.doi}


def _check_entry(where: str, raw: dict[str, Any]) -> list[str]:
    errs: list[str] = []

    for name in ("title", "licence_as_recorded"):
        value = raw[name]
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{where}: {name} must be a non-empty string")

    # Null only when the source header states no value; a non-null value must be well-formed.
    for name in ("authors", "journal"):
        value = raw[name]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errs.append(f"{where}: {name} must be null or a non-empty string, got {value!r}")

    year = raw["year"]
    if year is not None and (not isinstance(year, int) or isinstance(year, bool) or not 1900 <= year <= 2100):
        errs.append(f"{where}: year must be null or an integer between 1900 and 2100, got {year!r}")

    if raw["class"] not in CLASSES:
        errs.append(f"{where}: class must be one of {CLASSES}, got {raw['class']!r}")

    for name in ("theme", "slug"):
        value = raw[name]
        if not isinstance(value, str) or not _NAME_RE.match(value):
            errs.append(f"{where}: {name} must match {_NAME_RE.pattern}, got {value!r}")

    pid = raw["id"]
    if not isinstance(pid, str) or not _ID_RE.match(pid):
        errs.append(f"{where}: id {pid!r} is not doi:/pmc:/hal:/local: form")

    doi = raw["doi"]
    if doi is not None:
        if not isinstance(doi, str) or not _DOI_RE.match(doi):
            errs.append(f"{where}: doi must be null or a DOI string, got {doi!r}")
            doi = None
    if isinstance(pid, str) and pid.startswith("doi:"):
        base = pid[4:].split("#", 1)[0]
        if doi is None:
            errs.append(f"{where}: id {pid!r} is a doi: id but doi is null")
        elif base != doi.lower():
            errs.append(f"{where}: id must be 'doi:' + lower-case DOI {doi.lower()!r}, got {pid!r}")

    if raw["alias_of"] is not None:
        errs.append(f"{where}: alias_of must be null (§6.2: duplicates are merged, not aliased)")

    if raw["expected_status"] not in STATUSES:
        errs.append(f"{where}: expected_status must be one of {STATUSES}, got {raw['expected_status']!r}")
    elif raw["expected_status"] == "ok" and doi is None and not (isinstance(pid, str) and pid.startswith(("pmc:", "hal:"))):
        errs.append(f"{where}: expected_status 'ok' needs a DOI or a pmc:/hal: id; otherwise use pending_no_source")

    superseded = raw.get("superseded_files", [])
    if not isinstance(superseded, list) or not all(isinstance(s, str) and s and "/" not in s for s in superseded):
        errs.append(f"{where}: superseded_files must be a list of file names (no directories)")

    sha = raw["pdf_sha256"]
    if sha is not None and (not isinstance(sha, str) or not _SHA_RE.match(sha)):
        errs.append(f"{where}: pdf_sha256 must be null or 64 lower-case hex digits")

    resolver = raw["resolver"]
    if resolver is not None and resolver not in RESOLVERS:
        errs.append(f"{where}: resolver must be null or one of {RESOLVERS}, got {resolver!r}")

    return errs


def validate_manifest(data: Any) -> list[str]:
    """Return every schema problem in ``data``. An empty list means valid."""
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    errs: list[str] = []
    extra_top = sorted(set(data) - {"schema_version", "entries"})
    if extra_top:
        errs.append(f"unknown top-level keys: {extra_top}")
    if data.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"schema_version must be {SCHEMA_VERSION}, got {data.get('schema_version')!r}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        errs.append("'entries' must be a list")
        return errs

    seen_ids: dict[str, str] = {}
    seen_names: dict[tuple[str, str], str] = {}
    seen_dois: dict[str, str] = {}

    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            errs.append(f"entries[{idx}]: must be an object")
            continue
        where = f"entries[{idx}] ({raw.get('id')!r})"
        missing = [f for f in FIELDS if f not in raw]
        extra = sorted(k for k in raw if k not in FIELDS and k not in OPTIONAL_FIELDS)
        if missing:
            errs.append(f"{where}: missing fields {missing}")
        if extra:
            errs.append(f"{where}: unknown fields {extra}")
        if missing:
            continue

        errs.extend(_check_entry(where, raw))

        pid = raw["id"]
        if isinstance(pid, str):
            if pid in seen_ids:
                errs.append(f"{where}: duplicate id, first seen at {seen_ids[pid]}")
            seen_ids.setdefault(pid, where)

        if isinstance(raw["theme"], str) and isinstance(raw["slug"], str):
            key = (raw["theme"], raw["slug"])
            if key in seen_names:
                errs.append(f"{where}: duplicate theme/slug {key[0]}/{key[1]}, first seen at {seen_names[key]}")
            seen_names.setdefault(key, where)

        doi = raw["doi"]
        if isinstance(doi, str) and _DOI_RE.match(doi):
            norm = doi.lower()
            if norm in seen_dois:
                errs.append(
                    f"{where}: duplicate DOI {doi!r} also used by {seen_dois[norm]}; "
                    "these are one paper and must be merged into one entry (D27)"
                )
            seen_dois.setdefault(norm, where)

    return errs


def parse_manifest(data: Any) -> Manifest:
    """Validate ``data`` and build a :class:`Manifest`. Raises :class:`ManifestError`."""
    errors = validate_manifest(data)
    if errors:
        raise ManifestError(errors)
    return Manifest(entries=tuple(Entry.from_dict(e) for e in data["entries"]))


def load_manifest(path: Path) -> Manifest:
    """Read and validate a manifest file. Raises :class:`ManifestError`."""
    if not path.is_file():
        raise ManifestError([f"manifest not found: {path}"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError([f"{path}: invalid JSON: {exc}"]) from exc
    return parse_manifest(data)


def dump_manifest(manifest: Manifest) -> str:
    """Deterministic JSON text: entries sorted by id, two-space indent, trailing newline."""
    entries = sorted(manifest.entries, key=lambda e: e.id)
    payload = {"schema_version": SCHEMA_VERSION, "entries": [e.to_dict() for e in entries]}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
