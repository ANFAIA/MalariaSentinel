"""Rescue of ``pending_paywalled`` papers whose licence is open (rescue agent back end).

The rescue agent works only from this module's output. Two operations:

* :func:`rescue_candidates` lists the paywalled entries that have at least one
  candidate PDF URL under an open licence (Creative Commons or CC0/public domain),
  with those URLs. Closed-access entries are never listed.
* :func:`adopt_pdf` takes a PDF the agent obtained by other means, checks it with
  the same rules as ``fetch`` (``%PDF-`` header, sha256 pin) and records it in the
  entry's provenance. Invalid input is refused and the provenance is not touched.

Obtaining the bytes (a browser session that passes an open-access site's bot
check) is the agent's job; the stop rules are in ``.pi/agents/papers-rescue.md``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .fetch import PDF_MAGIC, FetchResult, fetch_entry
from .manifest import Entry, Manifest
from .provenance import read_provenance, sha256_bytes
from .resolve import Candidate, JsonGetter, iter_candidates

RESCUE_RESOLVER = "rescue"
PAYWALLED = "pending_paywalled"

_OPEN_LICENCE = re.compile(
    r"(creativecommons\.org/(licenses|publicdomain)/|^cc[-_ ]?(by|zero|0)\b|^cc0\b|^public[- ]?domain)",
    re.IGNORECASE,
)


def is_open_licence(licence: str | None) -> bool:
    """True for a Creative Commons, CC0 or public-domain licence; False otherwise."""
    return bool(licence) and bool(_OPEN_LICENCE.search(licence.strip()))


@dataclass(frozen=True)
class RescueItem:
    """A paywalled entry paired with its open-licence candidate URLs."""
    entry: Entry
    candidates: tuple[Candidate, ...]


def rescue_candidates(
    manifest: Manifest,
    papers_root: Path,
    *,
    get_json: JsonGetter,
    email: str | None,
    entries: Iterable[Entry] | None = None,
) -> list[RescueItem]:
    """Paywalled entries (per their provenance) with open-licence candidate URLs."""
    items: list[RescueItem] = []
    for entry in entries if entries is not None else manifest.entries:
        if not entry.doi:
            continue
        status = read_provenance(papers_root / entry.theme / entry.slug).get("observed_status")
        if status != PAYWALLED:
            continue
        found = [
            c
            for c in iter_candidates(entry.doi, get_json=get_json, email=email, attempts=[])
            if is_open_licence(c.licence)
        ]
        if found:
            items.append(RescueItem(entry=entry, candidates=tuple(found)))
    return items


def adopt_pdf(
    entry: Entry,
    papers_root: Path,
    pdf_file: Path,
    *,
    source_url: str,
    licence: str,
    fetched_at: str | None = None,
) -> FetchResult:
    """Record a PDF obtained by the rescue agent, under the same checks as ``fetch``.

    Raises ``ValueError`` without touching provenance when the file is missing,
    is not a PDF, or does not match the manifest's sha256 pin.
    """
    if not pdf_file.is_file():
        raise ValueError(f"{pdf_file}: no such file")
    data = pdf_file.read_bytes()
    if not data.startswith(PDF_MAGIC):
        raise ValueError(f"{pdf_file}: not a PDF (missing %PDF- header)")
    if entry.pdf_sha256 is not None and sha256_bytes(data) != entry.pdf_sha256:
        raise ValueError(f"{pdf_file}: sha256 does not match the pin in the manifest")
    if not is_open_licence(licence):
        raise ValueError(f"licence {licence!r} is not open; the rescue does not adopt closed-access papers")
    candidate = Candidate(RESCUE_RESOLVER, source_url, licence)
    return fetch_entry(
        entry,
        papers_root,
        candidates=[candidate],
        downloader=lambda _url: data,
        attempts=[],
        force=True,
        fetched_at=fetched_at,
    )
