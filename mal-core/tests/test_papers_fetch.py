"""Fetch: sha256 check, D2 (pending_* instead of raising), no network (injected downloader)."""
from __future__ import annotations

import yaml

from _papers_fixtures import make_entry
from mal_core.papers.fetch import DownloadError, fetch_entry
from mal_core.papers.manifest import Entry
from mal_core.papers.provenance import sha256_bytes
from mal_core.papers.resolve import CROSSREF, UNPAYWALL, Candidate

PDF = b"%PDF-1.4\n% fixture body\n"
PDF_SHA = sha256_bytes(PDF)
FIXED = "2026-01-01T00:00:00+00:00"


class RecordingDownloader:
    """Answers each URL from a table; a value that is an Exception is raised."""

    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        answer = self.answers.get(url)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise DownloadError("HTTP 404", "network")
        return answer


def _entry(**kw) -> Entry:
    return Entry.from_dict(make_entry(**kw))


def _cand(url: str, resolver: str = CROSSREF) -> Candidate:
    return Candidate(resolver, url)


def _provenance(root, entry: Entry) -> dict:
    return yaml.safe_load((root / entry.theme / entry.slug / "provenance.yaml").read_text(encoding="utf-8"))


def test_success_writes_pdf_checks_sha_and_records_provenance(tmp_path):
    entry = _entry(pdf_sha256=PDF_SHA, expected_status="pending_network")
    dl = RecordingDownloader({"https://a.example/1.pdf": PDF})
    attempts: list = []
    result = fetch_entry(
        entry, tmp_path, candidates=[_cand("https://a.example/1.pdf")], downloader=dl,
        attempts=attempts, fetched_at=FIXED,
    )
    assert result.observed_status == "ok"
    assert result.pdf_path is not None and result.pdf_path.read_bytes() == PDF
    prov = _provenance(tmp_path, entry)
    assert prov["observed_status"] == "ok"
    assert prov["fetch"]["sha256"] == PDF_SHA
    assert prov["fetch"]["resolver"] == CROSSREF
    assert prov["fetch"]["source_url"] == "https://a.example/1.pdf"
    assert prov["fetch"]["fetched_at"] == FIXED


def test_pinned_sha_mismatch_writes_nothing_and_falls_through_to_next_candidate(tmp_path):
    entry = _entry(pdf_sha256=PDF_SHA)
    other = b"%PDF-1.4 a different edition"
    dl = RecordingDownloader({"https://a.example/v2.pdf": other, "https://b.example/v1.pdf": PDF})
    result = fetch_entry(
        entry, tmp_path,
        candidates=[_cand("https://a.example/v2.pdf"), _cand("https://b.example/v1.pdf", UNPAYWALL)],
        downloader=dl, fetched_at=FIXED,
    )
    assert result.observed_status == "ok"
    assert result.resolver == UNPAYWALL
    assert any("sha256" in f and "pinned" in f for f in result.failures)


def test_only_mismatching_pdfs_give_pending_no_source_and_no_file(tmp_path):
    entry = _entry(pdf_sha256=PDF_SHA)
    dl = RecordingDownloader({"https://a.example/x.pdf": b"%PDF-1.4 other"})
    result = fetch_entry(entry, tmp_path, candidates=[_cand("https://a.example/x.pdf")], downloader=dl, fetched_at=FIXED)
    assert result.observed_status == "pending_no_source"
    assert result.pdf_path is None
    assert not (tmp_path / entry.theme / entry.slug / f"{entry.slug}.pdf").exists()


def test_landing_page_instead_of_pdf_is_pending_paywalled(tmp_path):
    entry = _entry()
    dl = RecordingDownloader({"https://pub.example/paywall": b"<html>Subscribe</html>"})
    result = fetch_entry(entry, tmp_path, candidates=[_cand("https://pub.example/paywall")], downloader=dl, fetched_at=FIXED)
    assert result.observed_status == "pending_paywalled"
    assert "not a PDF" in result.failures[0]
    assert _provenance(tmp_path, entry)["observed_status"] == "pending_paywalled"


def test_http_403_is_paywalled_and_timeout_is_network(tmp_path):
    entry = _entry()
    dl = RecordingDownloader({"https://pub.example/403": DownloadError("HTTP 403", "paywalled")})
    paywalled = fetch_entry(entry, tmp_path, candidates=[_cand("https://pub.example/403")], downloader=dl, fetched_at=FIXED)
    assert paywalled.observed_status == "pending_paywalled"

    dl2 = RecordingDownloader({"https://pub.example/slow": DownloadError("timed out", "network")})
    network = fetch_entry(entry, tmp_path, candidates=[_cand("https://pub.example/slow")], downloader=dl2, fetched_at=FIXED)
    assert network.observed_status == "pending_network"


def test_no_candidates_is_pending_no_source_and_never_raises(tmp_path):
    entry = _entry(doi=None, expected_status="ok")
    result = fetch_entry(entry, tmp_path, candidates=[], downloader=RecordingDownloader({}), fetched_at=FIXED)
    assert result.observed_status == "pending_no_source"


def test_non_fetchable_expected_status_makes_no_network_call(tmp_path):
    entry = _entry(doi=None, expected_status="pending_paywalled")
    dl = RecordingDownloader({})
    result = fetch_entry(entry, tmp_path, candidates=[_cand("https://never.example/x.pdf")], downloader=dl, fetched_at=FIXED)
    assert result.observed_status == "pending_paywalled"
    assert dl.calls == []


def test_withdrawn_is_recorded_as_is(tmp_path):
    entry = _entry(doi=None, expected_status="withdrawn")
    result = fetch_entry(entry, tmp_path, candidates=[], downloader=RecordingDownloader({}), fetched_at=FIXED)
    assert result.observed_status == "withdrawn"


def test_present_pdf_matching_pin_is_not_downloaded_again(tmp_path):
    entry = _entry(pdf_sha256=PDF_SHA)
    folder = tmp_path / entry.theme / entry.slug
    folder.mkdir(parents=True)
    (folder / f"{entry.slug}.pdf").write_bytes(PDF)
    dl = RecordingDownloader({})
    result = fetch_entry(entry, tmp_path, candidates=[_cand("https://a.example/x.pdf")], downloader=dl, fetched_at=FIXED)
    assert result.observed_status == "ok"
    assert dl.calls == []


def test_force_redownloads_a_present_pdf(tmp_path):
    entry = _entry(pdf_sha256=PDF_SHA)
    folder = tmp_path / entry.theme / entry.slug
    folder.mkdir(parents=True)
    (folder / f"{entry.slug}.pdf").write_bytes(PDF)
    dl = RecordingDownloader({"https://a.example/x.pdf": PDF})
    fetch_entry(entry, tmp_path, candidates=[_cand("https://a.example/x.pdf")], downloader=dl, force=True, fetched_at=FIXED)
    assert dl.calls == ["https://a.example/x.pdf"]
