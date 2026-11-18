"""Download a paper's PDF into its folder, with the sha256 checked against the manifest.

Failure never raises (D2). An unobtainable paper gets an observed status from
the ``pending_*`` vocabulary and the run continues:

* no candidate URL at all                       -> pending_no_source
* a candidate answered with a non-PDF or 401/402/403 -> pending_paywalled
* a candidate failed at the transport level     -> pending_network
* every candidate that was a PDF had another sha256 -> pending_no_source (nothing written)

Entries whose hand-authored status is ``withdrawn`` or one of the non-retryable
``pending_*`` values are not fetched. Their observed status is recorded as-is.
"""

from __future__ import annotations

import os
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

from .manifest import Entry
from .provenance import read_provenance, sha256_bytes, sha256_file, update_provenance, utc_now_iso
from .resolve import Attempt, Candidate, user_agent

PDF_MAGIC = b"%PDF-"
# Expected statuses that permit a network attempt. Everything else is recorded, not retried.
FETCHABLE_STATUSES = frozenset({"ok", "pending_network"})
_PAYWALL_CODES = frozenset({401, 402, 403})


class DownloadError(Exception):
    """A candidate could not be downloaded. ``kind`` is ``network`` or ``paywalled``."""

    def __init__(self, message: str, kind: str = "network") -> None:
        super().__init__(message)
        self.kind = kind


Downloader = Callable[[str], bytes]


def urllib_downloader(*, user_agent_value: str, timeout: float = 120.0) -> Downloader:
    """Build a Downloader that fetches URLs with urllib and the given User-Agent."""
    def download(url: str) -> bytes:
        """Fetch url and return its bytes. Paywall HTTP codes raise DownloadError of kind 'paywalled'; other failures raise kind 'network'."""
        request = urllib.request.Request(
            url, headers={"User-Agent": user_agent_value, "Accept": "application/pdf,*/*;q=0.5"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            kind = "paywalled" if exc.code in _PAYWALL_CODES else "network"
            raise DownloadError(f"HTTP {exc.code} from {url}", kind) from exc
        except (URLError, OSError, ValueError) as exc:
            raise DownloadError(f"{type(exc).__name__}: {exc}", "network") from exc

    return download


@dataclass(frozen=True)
class FetchResult:
    """Outcome of fetching one paper: observed status, PDF path and hash, resolver used."""
    paper_id: str
    observed_status: str
    pdf_path: Path | None
    sha256: str | None
    source_url: str | None
    resolver: str | None
    failures: tuple[str, ...] = ()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def fetch_entry(
    entry: Entry,
    papers_root: Path,
    *,
    candidates: Iterable[Candidate],
    downloader: Downloader,
    attempts: list[Attempt] | None = None,
    force: bool = False,
    fetched_at: str | None = None,
) -> FetchResult:
    """Fetch one entry's PDF, or record why it could not be obtained.

    ``candidates`` is consumed lazily; the first candidate that yields a PDF
    whose sha256 matches the manifest (or any PDF, when the manifest pin is null)
    wins. ``attempts`` is the list the resolver chain appends to, if any.
    """
    paper_dir = papers_root / entry.theme / entry.slug
    pdf_path = paper_dir / f"{entry.slug}.pdf"
    stamp = fetched_at or utc_now_iso()

    def record(observed: str, fetch: dict | None = None, failures: tuple[str, ...] = ()) -> FetchResult:
        # Read the attempts at record time: the resolver chain fills the list lazily while candidates are consumed.
        """Write the observed status (and fetch block, if any) to provenance and return the FetchResult."""
        blocks: dict = {
            "id": entry.id,
            "class": entry.paper_class,
            "expected_status": entry.expected_status,
            "observed_status": observed,
        }
        if fetch is not None:
            attempt_lines = [str(a) for a in attempts or []]
            blocks["fetch"] = {**fetch, "fetched_at": stamp, "failures": list(failures), "attempts": attempt_lines}
        update_provenance(paper_dir, **blocks)
        return FetchResult(
            paper_id=entry.id,
            observed_status=observed,
            pdf_path=pdf_path if observed == "ok" and pdf_path.is_file() else None,
            sha256=(fetch or {}).get("sha256"),
            source_url=(fetch or {}).get("source_url"),
            resolver=(fetch or {}).get("resolver"),
            failures=failures,
        )

    if entry.expected_status not in FETCHABLE_STATUSES:
        return record(entry.expected_status)

    if pdf_path.is_file() and not force:
        present = sha256_file(pdf_path)
        if entry.pdf_sha256 in (None, present):
            prior = read_provenance(paper_dir).get("fetch") or {}
            return record(
                "ok",
                fetch={
                    "sha256": present,
                    "source_url": prior.get("source_url"),
                    "resolver": prior.get("resolver"),
                    "bytes": pdf_path.stat().st_size,
                },
            )

    failures: list[tuple[str, str]] = []
    for candidate in candidates:
        label = f"{candidate.resolver} {candidate.url}"
        try:
            data = downloader(candidate.url)
        except DownloadError as exc:
            failures.append((exc.kind, f"{label}: {exc}"))
            continue
        if not data.startswith(PDF_MAGIC):
            failures.append(("paywalled", f"{label}: response is not a PDF"))
            continue
        digest = sha256_bytes(data)
        if entry.pdf_sha256 is not None and digest != entry.pdf_sha256:
            failures.append(("mismatch", f"{label}: sha256 {digest[:12]} != pinned {entry.pdf_sha256[:12]}"))
            continue
        _write_atomic(pdf_path, data)
        return record(
            "ok",
            fetch={"sha256": digest, "source_url": candidate.url, "resolver": candidate.resolver, "bytes": len(data)},
            failures=tuple(msg for _, msg in failures),
        )

    kinds = {kind for kind, _ in failures}
    if "network" in kinds:
        observed = "pending_network"
    elif "paywalled" in kinds:
        observed = "pending_paywalled"
    else:
        observed = "pending_no_source"
    return record(observed, fetch={"sha256": None, "source_url": None, "resolver": None}, failures=tuple(msg for _, msg in failures))
