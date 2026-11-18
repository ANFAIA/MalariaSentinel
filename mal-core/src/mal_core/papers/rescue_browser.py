"""Browser-assisted rescue of open-licence PDFs that a scripted client could not fetch.

Scope and stop rules (agreed plan, see .pi/agents/papers-rescue.md):

* Only candidate URLs whose licence is open (``rescue.is_open_licence``).
* One browser page at a time. The page is loaded like a reader would load it, so
  an automatic JavaScript bot check can finish. The PDF is then requested with the
  same browser session's cookies. Nothing is clicked, typed or submitted.
* A page that shows a login, a CAPTCHA or puzzle, a subscription or purchase
  prompt, or an access-denied message is a barrier: the candidate is abandoned.
* At least ``min_interval_s`` between requests to one host; three consecutive
  failures on a host stop that host for the run; ``max_loads`` caps the run.

The pure parts (barrier classification, host bookkeeping) are unit-tested. The
browser part needs Playwright and Chromium, is not run by the test suite, and is
exercised by ``malariasim papers rescue-browser``.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .manifest import Entry
from .rescue import RescueItem, adopt_pdf
from .fetch import PDF_MAGIC

MIN_INTERVAL_S = 10.0
MAX_CONSECUTIVE_HOST_FAILURES = 3
MAX_LOADS = 60
PAGE_TIMEOUT_MS = 30_000

# Text markers of a page that needs a person. Matched case-insensitively on the page text.
_BARRIER_PATTERNS = {
    "login": re.compile(r"\b(sign in|log in|login required|institutional login|create an account)\b", re.I),
    "captcha": re.compile(r"(captcha|verify you are (a )?human|are you a robot|i'm not a robot|hcaptcha|recaptcha)", re.I),
    "paywall": re.compile(r"\b(subscribe|subscription required|purchase (this )?(article|access)|buy (this )?article|get access)\b", re.I),
    "denied": re.compile(r"\b(access denied|403 forbidden|401 unauthorized|402 payment required)\b", re.I),
}


def classify_page(html: str, title: str = "") -> str | None:
    """Return the barrier kind found on a page, or None when no barrier marker matches.

    A bot-check interstitial is not a barrier by itself: it is passed by waiting. Only
    interactive challenges (CAPTCHA widgets) and access prompts are barriers.
    """
    text = f"{title}\n{html}"
    for kind in ("captcha", "login", "paywall", "denied"):
        if _BARRIER_PATTERNS[kind].search(text):
            return kind
    return None


@dataclass
class HostGate:
    """Per-host pacing and consecutive-failure bookkeeping for one run."""

    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    min_interval_s: float = MIN_INTERVAL_S
    _last: dict[str, float] = field(default_factory=dict)
    _failures: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def host(self, url: str) -> str:
        """Hostname of url, or an empty string when it has none."""
        return urlsplit(url).hostname or ""

    def blocked(self, url: str) -> bool:
        """True once the host has failed MAX_CONSECUTIVE_HOST_FAILURES times in a row."""
        return self._failures[self.host(url)] >= MAX_CONSECUTIVE_HOST_FAILURES

    def wait_turn(self, url: str) -> None:
        """Sleep until min_interval_s has elapsed since the last request to the same host."""
        host = self.host(url)
        last = self._last.get(host)
        if last is not None:
            remaining = self.min_interval_s - (self.clock() - last)
            if remaining > 0:
                self.sleep(remaining)
        self._last[host] = self.clock()

    def record(self, url: str, ok: bool) -> None:
        """Reset the host's failure streak on success, or extend it on failure."""
        host = self.host(url)
        self._failures[host] = 0 if ok else self._failures[host] + 1


@dataclass(frozen=True)
class Outcome:
    """Result of one rescue attempt: status, detail and the URL used, if any."""
    id: str
    status: str  # adopted | barrier | no_pdf | refused | host_blocked | not_attempted
    detail: str = ""
    url: str | None = None


def rescue_items(
    items: list[RescueItem],
    *,
    papers_root: Path,
    scratch_dir: Path,
    load_pdf: Callable[[str], tuple[bytes | None, str | None]],
    gate: HostGate,
    max_loads: int = MAX_LOADS,
) -> list[Outcome]:
    """Walk the items; ``load_pdf(url)`` returns ``(pdf_bytes, barrier_or_None)``.

    ``load_pdf`` is the browser step. It is injected so the walk and its stop rules are
    testable offline. Once ``max_loads`` is reached, the remaining items are reported as
    ``not_attempted``.
    """
    scratch_dir.mkdir(parents=True, exist_ok=True)
    outcomes: list[Outcome] = []
    loads = 0
    for index, item in enumerate(items):
        entry: Entry = item.entry
        if loads >= max_loads:
            outcomes.extend(Outcome(rest.entry.id, "not_attempted", "max loads per run") for rest in items[index:])
            break
        done = False
        loaded_any = False
        for candidate in item.candidates:
            if loads >= max_loads:
                break
            if gate.blocked(candidate.url):
                continue
            loaded_any = True
            gate.wait_turn(candidate.url)
            loads += 1
            data, barrier = load_pdf(candidate.url)
            if barrier is not None:
                gate.record(candidate.url, ok=False)
                outcomes.append(Outcome(entry.id, "barrier", barrier, candidate.url))
                done = True
                break
            if data is None or not data.startswith(PDF_MAGIC):
                gate.record(candidate.url, ok=False)
                continue
            gate.record(candidate.url, ok=True)
            tmp = scratch_dir / f"{entry.slug}.pdf"
            tmp.write_bytes(data)
            try:
                adopt_pdf(entry, papers_root, tmp, source_url=candidate.url, licence=candidate.licence or "")
            except ValueError as exc:
                outcomes.append(Outcome(entry.id, "refused", str(exc), candidate.url))
            else:
                outcomes.append(Outcome(entry.id, "adopted", "", candidate.url))
            done = True
            break
        if not done:
            if not loaded_any and item.candidates:
                outcomes.append(Outcome(entry.id, "host_blocked", "three consecutive failures on the host"))
            else:
                outcomes.append(Outcome(entry.id, "no_pdf", "no candidate yielded a PDF"))
    return outcomes


def playwright_loader(*, headless: bool = False, user_agent_value: str):
    """Return ``load_pdf(url)`` backed by Chromium via Playwright (imported lazily).

    Loads the candidate page in a fresh tab, waits for it to settle, classifies it,
    and then requests the PDF with the same browser context (same cookies).
    """
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context(user_agent=user_agent_value, accept_downloads=False)

    def load_pdf(url: str) -> tuple[bytes | None, str | None]:
        """Open url in the browser. Return (pdf_bytes, None), or (None, reason) when a barrier page or a denial is met."""
        page = context.new_page()
        try:
            try:
                page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
            except Exception:  # noqa: BLE001 - a slow page is handled by the checks below
                pass
            barrier = classify_page(page.content(), page.title())
            if barrier is not None:
                return None, barrier
            response = context.request.get(url, timeout=PAGE_TIMEOUT_MS, headers={"Accept": "application/pdf,*/*;q=0.5"})
            if response.status in (401, 402, 403):
                return None, "denied"
            return response.body(), None
        finally:
            page.close()

    def close() -> None:
        """Close the browser context and browser, and stop Playwright."""
        context.close()
        browser.close()
        pw.stop()

    load_pdf.close = close  # type: ignore[attr-defined]
    return load_pdf
