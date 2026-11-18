"""The four acceptance assertions of the paper corpus (plan §7).

a. Every DOI resolves, or its entry has no DOI and a ``pending_*``/``withdrawn``
   status as the reason. Resolution is a network call, so it is opt-in
   (``resolve=True``); the default run checks structure only. This is a local
   command, not a CI gate.
b. Every ``doi:`` token in a tracked document maps to a manifest entry.
c. Every fetched PDF has a sha256 equal to its manifest value (unpinned entries
   are reported as warnings, not failures).
d. ``git ls-files <corpus>/`` equals the allowlist, and no tracked file under the
   corpus exceeds 64 KiB.

Every check takes its I/O as an argument (resolver, hasher, tracked-file list,
file sizes, document texts), so the unit tests run offline.
"""

from __future__ import annotations

import re
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .harvest import clean_doi
from .manifest import Manifest
from .provenance import read_observed_status, sha256_file

MAX_TRACKED_BYTES = 64 * 1024
TEXT_SUFFIXES = frozenset(
    {".md", ".tex", ".py", ".yaml", ".yml", ".json", ".txt", ".rst", ".toml", ".cfg", ".ini", ".sh", ".cpp", ".hpp", ".h"}
)
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
# Statuses that count as a recorded reason when an entry has no DOI.
REASON_STATUSES = frozenset(
    {"pending_no_source", "pending_paywalled", "pending_network", "pending_extraction_failed", "withdrawn"}
)

DOI_RESOLVER_URL = "https://doi.org/{doi}"
DoiResolver = Callable[[str], bool | None]
Hasher = Callable[[Path], str]
SizeOf = Callable[[str], int]

# A DOI token is the registrant prefix ``10.NNNN/`` followed by a non-empty suffix.
# ``doi:10.1136/`` in prose (a bare prefix) is not a DOI and must not be reported.
_DOI_LABEL = re.compile(r"doi:(10\.\d{4,9}/[^\s\"'<>`|]+)")
_DOI_BODY = re.compile(r"10\.\d{4,9}/\S+")


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def merge(self, other: "Report") -> None:
        self.failures += other.failures
        self.warnings += other.warnings
        self.notes += other.notes


def http_doi_resolver(doi: str, timeout: float = 20.0) -> bool | None:
    """True if doi.org answers the DOI, False if it says it is unknown, None if unreachable."""
    request = urllib.request.Request(DOI_RESOLVER_URL.format(doi=doi), method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return True
    except urllib.error.HTTPError as exc:
        return False if exc.code == 404 else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def check_dois(manifest: Manifest, *, resolve: bool = False, resolver: DoiResolver | None = None) -> Report:
    """Assertion (a)."""
    report = Report()
    if resolve and resolver is None:
        resolver = http_doi_resolver
    for entry in manifest.entries:
        if entry.doi is None:
            if entry.expected_status in REASON_STATUSES:
                report.notes.append(f"{entry.id}: no DOI, reason recorded as {entry.expected_status}")
            elif entry.expected_status == "ok" and entry.id.startswith(("pmc:", "hal:")):
                report.notes.append(f"{entry.id}: no DOI, obtainable through its pmc:/hal: identifier")
            else:
                report.failures.append(
                    f"{entry.id}: no DOI and expected_status {entry.expected_status!r} gives no pending reason"
                )
            continue
        if not resolve:
            continue
        assert resolver is not None
        verdict = resolver(entry.doi)
        if verdict is True:
            continue
        if verdict is False:
            report.failures.append(f"{entry.id}: DOI {entry.doi} does not resolve (doi.org)")
        else:
            report.warnings.append(f"{entry.id}: DOI {entry.doi} could not be checked (network)")
    return report


def extract_doi_tokens(text: str) -> list[tuple[int, str]]:
    """``(line_number, doi)`` for every ``doi:`` token. Line numbers start at 1."""
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _DOI_LABEL.finditer(line):
            raw = match.group(1).split("#", 1)[0]
            doi = clean_doi(raw)
            if doi and _DOI_BODY.fullmatch(doi):
                found.append((lineno, doi))
    return found


def check_doi_tokens(manifest: Manifest, documents: Mapping[str, str]) -> Report:
    """Assertion (b). ``documents`` maps repository-relative path to text."""
    report = Report()
    known = set(manifest.doi_index())
    for path in sorted(documents):
        for lineno, doi in extract_doi_tokens(documents[path]):
            if doi.lower() not in known:
                report.failures.append(f"{path}:{lineno}: doi:{doi} has no manifest entry")
    return report


def check_hashes(manifest: Manifest, papers_root: Path, *, hasher: Hasher = sha256_file) -> Report:
    """Assertion (c). Only fetched PDFs (present on disk) are compared."""
    report = Report()
    not_fetched = 0
    for entry in manifest.entries:
        pdf = papers_root / entry.pdf_relpath
        if not pdf.is_file():
            # provenance.yaml is the only record of observed status; "ok" with no PDF is a broken state.
            if read_observed_status(pdf.parent) == "ok":
                report.failures.append(f"{entry.id}: provenance records observed_status ok but {pdf} is missing")
            not_fetched += 1
            continue
        if entry.pdf_sha256 is None:
            report.warnings.append(f"{entry.id}: PDF present but pdf_sha256 is not pinned in the manifest")
            continue
        actual = hasher(pdf)
        if actual != entry.pdf_sha256:
            report.failures.append(
                f"{entry.id}: sha256 of {pdf} is {actual}, manifest pins {entry.pdf_sha256}"
            )
    report.notes.append(f"{not_fetched} entries have no PDF on disk (not checked)")
    return report


def check_tracked(
    tracked: Iterable[str],
    *,
    prefix: str,
    allowlist: Iterable[str],
    size_of: SizeOf,
    max_bytes: int = MAX_TRACKED_BYTES,
) -> Report:
    """Assertion (d). ``tracked`` is the output of ``git ls-files``, relative to the repo root."""
    report = Report()
    under = sorted(f for f in tracked if f.startswith(prefix.rstrip("/") + "/"))
    allowed = set(allowlist)
    unexpected = [f for f in under if f not in allowed]
    missing = sorted(allowed - set(under))
    if unexpected:
        sample = ", ".join(unexpected[:5])
        report.failures.append(f"{len(unexpected)} tracked file(s) under {prefix}/ are not allowlisted, e.g. {sample}")
    if missing:
        report.failures.append(f"allowlisted file(s) not tracked: {', '.join(missing)}")
    for path in under:
        size = size_of(path)
        if size > max_bytes:
            report.failures.append(f"{path} is tracked with {size} bytes (limit {max_bytes})")
    return report


def allowlist_for(prefix: str) -> tuple[str, ...]:
    """The allowlist of §6.3: indexes and the manifest, nothing else under the corpus root."""
    base = prefix.rstrip("/")
    return (f"{base}/README.md", f"{base}/REFERENCES.md", f"{base}/manifest.json")


def read_documents(repo_root: Path, tracked: Iterable[str]) -> dict[str, str]:
    """Text of tracked documents for assertion (b). Binary and oversized files are skipped."""
    docs: dict[str, str] = {}
    for rel in tracked:
        path = repo_root / rel
        if Path(rel).suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            continue
        docs[rel] = path.read_text(encoding="utf-8", errors="ignore")
    return docs


def git_tracked_files(repo_root: Path) -> list[str]:
    """All tracked paths, relative to ``repo_root``, using ``git ls-files -z``."""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    return [p for p in proc.stdout.decode("utf-8", errors="replace").split("\0") if p]


def run_checks(
    manifest: Manifest,
    *,
    papers_root: Path,
    prefix: str,
    documents: Mapping[str, str],
    tracked: Iterable[str],
    size_of: SizeOf,
    resolve: bool = False,
    resolver: DoiResolver | None = None,
    hasher: Hasher = sha256_file,
) -> Report:
    """All four assertions, merged into one report."""
    report = Report()
    report.merge(check_dois(manifest, resolve=resolve, resolver=resolver))
    report.merge(check_doi_tokens(manifest, documents))
    report.merge(check_hashes(manifest, papers_root, hasher=hasher))
    report.merge(check_tracked(tracked, prefix=prefix, allowlist=allowlist_for(prefix), size_of=size_of))
    return report
