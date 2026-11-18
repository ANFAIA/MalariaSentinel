"""Browser rescue: barrier classification, host pacing and stop rules. No browser, no network."""
from __future__ import annotations

from pathlib import Path

import yaml

from _papers_fixtures import make_entry
from mal_core.papers.manifest import Entry
from mal_core.papers.rescue import RescueItem
from mal_core.papers.resolve import Candidate
from mal_core.papers.rescue_browser import (
    MAX_CONSECUTIVE_HOST_FAILURES,
    HostGate,
    classify_page,
    rescue_items,
)

PDF = b"%PDF-1.4\n% rescued\n"
CC = "https://creativecommons.org/licenses/by/4.0/"


def _item(doi: str, slug: str, *urls: str) -> RescueItem:
    entry = Entry.from_dict(make_entry(doi=doi, slug=slug))
    return RescueItem(entry=entry, candidates=tuple(Candidate("crossref", u, CC) for u in urls))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _gate() -> tuple[HostGate, FakeClock]:
    fc = FakeClock()
    return HostGate(clock=fc.clock, sleep=fc.sleep, min_interval_s=10.0), fc


def test_bot_check_interstitial_is_not_a_barrier():
    html = "<html><title>Client Challenge</title><script>window.__cf=1</script>Checking your browser</html>"
    assert classify_page(html, "Client Challenge") is None


def test_captcha_login_paywall_denied_are_barriers():
    assert classify_page("<div class='g-recaptcha'></div>", "x") == "captcha"
    assert classify_page("<h1>Please sign in to continue</h1>", "x") == "login"
    assert classify_page("<button>Buy this article</button>", "x") == "paywall"
    assert classify_page("<p>403 Forbidden</p>", "x") == "denied"


def test_plain_article_page_has_no_barrier():
    assert classify_page("<h1>Mosquito abundance in Accra</h1><p>Abstract ...</p>", "Article") is None


def test_host_is_paced_and_pdf_adopted(tmp_path: Path):
    root = tmp_path / "papers"
    item = _item("10.1186/a-1", "paper-a-2020", "https://pub.example/a.pdf", "https://pub.example/b.pdf")
    (root / item.entry.theme / item.entry.slug).mkdir(parents=True)
    gate, fc = _gate()
    calls: list[str] = []

    def load(url):
        calls.append(url)
        return (PDF, None) if url.endswith("b.pdf") else (None, None)

    # first candidate has no PDF, second does: two loads on one host -> one wait of 10 s
    out = rescue_items([item], papers_root=root, scratch_dir=tmp_path / "s", load_pdf=load, gate=gate)
    assert [o.status for o in out] == ["adopted"]
    assert calls == ["https://pub.example/a.pdf", "https://pub.example/b.pdf"]
    assert fc.slept == [10.0]  # the second load on the same host waits the full interval


def test_barrier_abandons_candidate_without_retry(tmp_path: Path):
    item = _item("10.1186/a-2", "paper-b-2020", "https://pub.example/a.pdf", "https://pub.example/b.pdf")
    gate, _ = _gate()
    calls: list[str] = []

    def load(url):
        calls.append(url)
        return None, "login"

    out = rescue_items([item], papers_root=tmp_path, scratch_dir=tmp_path / "s", load_pdf=load, gate=gate)
    assert [(o.status, o.detail) for o in out] == [("barrier", "login")]
    assert calls == ["https://pub.example/a.pdf"]


def test_three_consecutive_failures_block_the_host(tmp_path: Path):
    items = [_item(f"10.1186/h-{i}", f"host-paper-{i}-2020", f"https://pub.example/{i}.pdf") for i in range(5)]
    gate, _ = _gate()
    calls: list[str] = []

    def load(url):
        calls.append(url)
        return None, None  # no PDF, no barrier

    out = rescue_items(items, papers_root=tmp_path, scratch_dir=tmp_path / "s", load_pdf=load, gate=gate)
    assert len(calls) == MAX_CONSECUTIVE_HOST_FAILURES
    # the three loaded papers failed (no_pdf); the two never loaded are blocked by the host, not attempted
    assert [o.status for o in out] == ["no_pdf"] * 3 + ["host_blocked"] * 2


def test_run_cap_reports_the_rest_as_not_attempted(tmp_path: Path):
    items = [_item(f"10.1186/c-{i}", f"cap-paper-{i}-2020", f"https://h{i}.example/x.pdf") for i in range(4)]
    gate, _ = _gate()
    out = rescue_items(items, papers_root=tmp_path, scratch_dir=tmp_path / "s",
                       load_pdf=lambda u: (None, None), gate=gate, max_loads=2)
    statuses = [o.status for o in out]
    assert statuses.count("not_attempted") == 2
    assert len(out) == 4


def test_refused_pdf_is_reported_not_adopted(tmp_path: Path):
    # a pinned sha256 that the downloaded bytes do not match
    entry = Entry.from_dict(make_entry(doi="10.1186/r-1", slug="refused-paper-2020", pdf_sha256="0" * 64))
    item = RescueItem(entry=entry, candidates=(Candidate("crossref", "https://pub.example/r.pdf", CC),))
    root = tmp_path / "papers"
    gate, _ = _gate()
    out = rescue_items([item], papers_root=root, scratch_dir=tmp_path / "s",
                       load_pdf=lambda u: (PDF, None), gate=gate)
    assert out[0].status == "refused"
    prov = root / entry.theme / entry.slug / "provenance.yaml"
    assert not prov.exists()
