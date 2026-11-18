"""DOI resolver chain: Crossref -> Unpaywall -> Europe PMC (D16).

The chain yields candidate PDF URLs in that order. A consumer (``fetch``) takes
candidates lazily and stops at the first one that delivers a valid PDF, so a
later resolver is queried only when the earlier ones failed to produce a usable
file.

Transport is injected: ``get_json(url)`` returns decoded JSON, ``None`` when the
service has no record for the request, and raises :class:`TransportError` on a
network or server failure. Tests pass a fake transport, so they never touch the
network. The contact e-mail is an argument, read from ``config/papers.yaml`` by
the caller; it is never hard-coded here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .config import email_is_usable

CROSSREF = "crossref"
UNPAYWALL = "unpaywall"
EUROPE_PMC = "europe_pmc"
RESOLVER_ORDER = (CROSSREF, UNPAYWALL, EUROPE_PMC)

CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
UNPAYWALL_WORKS = "https://api.unpaywall.org/v2/{doi}"
EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_PDF = "https://europepmc.org/articles/{pmcid}?pdf=render"


class TransportError(Exception):
    """A resolver request failed (network, HTTP status other than 404, bad JSON)."""


JsonGetter = Callable[[str], Any]


@dataclass(frozen=True)
class Candidate:
    """An open-licence PDF URL proposed by a resolver, with its licence when known."""
    resolver: str
    url: str
    licence: str | None = None


@dataclass(frozen=True)
class Attempt:
    """One resolver's attempt for a paper; str() gives a compact log line."""
    resolver: str
    outcome: str  # candidate | no_candidate | no_record | skipped | error
    detail: str = ""

    def __str__(self) -> str:
        text = f"{self.resolver}:{self.outcome}"
        return f"{text} ({self.detail})" if self.detail else text


def user_agent(email: str | None) -> str:
    """User-Agent string; includes the contact address only when it is usable."""
    base = "mal-core-papers/0.2"
    return f"{base} (mailto:{email.strip()})" if email_is_usable(email) else base


def urllib_json_getter(*, user_agent_value: str, timeout: float = 30.0) -> JsonGetter:
    """Default transport. HTTP 404 means "no record"; other failures raise."""

    def get(url: str) -> Any:
        """Fetch url and decode its JSON body. A 404 returns None; transport errors raise TransportError."""
        request = Request(url, headers={"User-Agent": user_agent_value, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise TransportError(f"HTTP {exc.code} from {url}") from exc
        except (URLError, OSError, ValueError) as exc:
            raise TransportError(f"{type(exc).__name__}: {exc}") from exc

    return get


def _as_dict(data: Any, resolver: str) -> dict[str, Any] | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise TransportError(f"{resolver}: unexpected JSON shape")
    return data


def _crossref(doi: str, get: JsonGetter, email: str | None) -> tuple[Attempt, list[Candidate]]:
    url = CROSSREF_WORKS.format(doi=quote(doi, safe="/"))
    if email_is_usable(email):
        url += "?" + urlencode({"mailto": email.strip()})
    data = _as_dict(get(url), CROSSREF)
    if data is None:
        return Attempt(CROSSREF, "no_record"), []
    message = _as_dict(data.get("message"), CROSSREF) or {}
    licences = message.get("license") or []
    licence = licences[0].get("URL") if licences and isinstance(licences[0], dict) else None
    candidates = [
        Candidate(CROSSREF, link["URL"], licence)
        for link in message.get("link") or []
        if isinstance(link, dict) and link.get("content-type") == "application/pdf" and link.get("URL")
    ]
    return _outcome(CROSSREF, candidates)


def _unpaywall(doi: str, get: JsonGetter, email: str | None) -> tuple[Attempt, list[Candidate]]:
    if not email_is_usable(email):
        return Attempt(UNPAYWALL, "skipped", "no usable contact e-mail in config/papers.yaml"), []
    url = UNPAYWALL_WORKS.format(doi=quote(doi, safe="/")) + "?" + urlencode({"email": email.strip()})
    data = _as_dict(get(url), UNPAYWALL)
    if data is None:
        return Attempt(UNPAYWALL, "no_record"), []
    locations: list[dict[str, Any]] = []
    best = data.get("best_oa_location")
    if isinstance(best, dict):
        locations.append(best)
    locations += [loc for loc in data.get("oa_locations") or [] if isinstance(loc, dict)]
    candidates: list[Candidate] = []
    seen: set[str] = set()
    for loc in locations:
        pdf_url = loc.get("url_for_pdf")
        if pdf_url and pdf_url not in seen:
            seen.add(pdf_url)
            candidates.append(Candidate(UNPAYWALL, pdf_url, loc.get("license")))
    return _outcome(UNPAYWALL, candidates)


def _europe_pmc(doi: str, get: JsonGetter, email: str | None) -> tuple[Attempt, list[Candidate]]:
    query = urlencode({"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"})
    data = _as_dict(get(f"{EUROPE_PMC_SEARCH}?{query}"), EUROPE_PMC)
    if data is None:
        return Attempt(EUROPE_PMC, "no_record"), []
    results = (_as_dict(data.get("resultList"), EUROPE_PMC) or {}).get("result") or []
    candidates = [
        Candidate(EUROPE_PMC, EUROPE_PMC_PDF.format(pmcid=r["pmcid"]), None)
        for r in results
        if isinstance(r, dict) and r.get("pmcid") and r.get("isOpenAccess") == "Y"
    ]
    return _outcome(EUROPE_PMC, candidates)


def _outcome(resolver: str, candidates: list[Candidate]) -> tuple[Attempt, list[Candidate]]:
    if candidates:
        return Attempt(resolver, "candidate", f"{len(candidates)} candidate(s)"), candidates
    return Attempt(resolver, "no_candidate"), []


_STEPS: tuple[tuple[str, Callable[[str, JsonGetter, str | None], tuple[Attempt, list[Candidate]]]], ...] = (
    (CROSSREF, _crossref),
    (UNPAYWALL, _unpaywall),
    (EUROPE_PMC, _europe_pmc),
)


def iter_candidates(
    doi: str,
    *,
    get_json: JsonGetter,
    email: str | None,
    attempts: list[Attempt],
) -> Iterator[Candidate]:
    """Yield candidate PDF URLs for ``doi`` in resolver order, lazily.

    Each step's outcome is appended to ``attempts`` when the step runs. A
    transport failure is recorded as an ``error`` attempt and the chain goes on.
    """
    for name, step in _STEPS:
        try:
            attempt, candidates = step(doi, get_json, email)
        except TransportError as exc:
            attempt, candidates = Attempt(name, "error", str(exc)), []
        attempts.append(attempt)
        yield from candidates
