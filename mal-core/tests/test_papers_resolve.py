"""DOI resolver chain Crossref -> Unpaywall -> Europe PMC, with an injected transport (offline)."""
from __future__ import annotations

from mal_core.papers.config import DEFAULT_CONFIG, email_is_usable, load_config
from mal_core.papers.resolve import (
    CROSSREF,
    EUROPE_PMC,
    RESOLVER_ORDER,
    UNPAYWALL,
    Attempt,
    TransportError,
    iter_candidates,
    user_agent,
)

DOI = "10.1186/s12936-000-0001-x"
USABLE = "curator@uni-lab.org"
PLACEHOLDER = "REPLACE-ME@example.invalid"


class FakeTransport:
    """Maps a URL prefix to a canned answer; records every URL requested, in order."""

    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.requested: list[str] = []

    def __call__(self, url: str):
        self.requested.append(url)
        for prefix, answer in self.answers.items():
            if url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        return None


CROSSREF_EMPTY = {"message": {"link": [], "license": []}}
CROSSREF_PDF = {
    "message": {
        "link": [
            {"URL": "https://publisher.example/full.html", "content-type": "text/html"},
            {"URL": "https://publisher.example/full.pdf", "content-type": "application/pdf"},
        ],
        "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
    }
}
UNPAYWALL_PDF = {
    "best_oa_location": {"url_for_pdf": "https://repo.example/oa.pdf", "license": "cc-by"},
    "oa_locations": [{"url_for_pdf": "https://repo.example/oa.pdf"}, {"url_for_pdf": "https://mirror.example/x.pdf"}],
}
EPMC_OPEN = {"resultList": {"result": [{"pmcid": "PMC999", "isOpenAccess": "Y"}]}}


def _run(transport: FakeTransport, email: str | None = USABLE):
    attempts: list[Attempt] = []
    urls = list(iter_candidates(DOI, get_json=transport, email=email, attempts=attempts))
    return urls, attempts


def test_order_constant_is_the_decided_chain():
    assert RESOLVER_ORDER == (CROSSREF, UNPAYWALL, EUROPE_PMC) == ("crossref", "unpaywall", "europe_pmc")


def test_all_three_queried_in_order_when_nothing_is_found():
    transport = FakeTransport({})
    candidates, attempts = _run(transport)
    assert candidates == []
    assert [a.resolver for a in attempts] == [CROSSREF, UNPAYWALL, EUROPE_PMC]
    assert [a.outcome for a in attempts] == ["no_record", "no_record", "no_record"]
    assert transport.requested[0].startswith("https://api.crossref.org/works/")
    assert transport.requested[1].startswith("https://api.unpaywall.org/v2/")
    assert transport.requested[2].startswith("https://www.ebi.ac.uk/europepmc/")


def test_crossref_pdf_link_is_used_and_chain_is_lazy():
    transport = FakeTransport({"https://api.crossref.org/": CROSSREF_PDF, "https://api.unpaywall.org/": UNPAYWALL_PDF})
    attempts: list[Attempt] = []
    gen = iter_candidates(DOI, get_json=transport, email=USABLE, attempts=attempts)
    first = next(gen)
    assert first.resolver == CROSSREF
    assert first.url == "https://publisher.example/full.pdf"
    assert first.licence == "https://creativecommons.org/licenses/by/4.0/"
    assert len(transport.requested) == 1, "Unpaywall must not be queried until Crossref is exhausted"
    assert attempts[0].outcome == "candidate"


def test_fallback_to_unpaywall_when_crossref_has_no_pdf_and_dedupes_urls():
    transport = FakeTransport({"https://api.crossref.org/": CROSSREF_EMPTY, "https://api.unpaywall.org/": UNPAYWALL_PDF})
    attempts: list[Attempt] = []
    gen = iter_candidates(DOI, get_json=transport, email=USABLE, attempts=attempts)
    first = next(gen)
    assert first.resolver == UNPAYWALL and first.url == "https://repo.example/oa.pdf"
    assert [a.resolver for a in attempts] == [CROSSREF, UNPAYWALL]
    assert len(transport.requested) == 2, "Europe PMC not queried once Unpaywall supplied a candidate"
    # The duplicated oa_locations entry is dropped; the remaining candidate follows, then Europe PMC runs.
    assert [c.url for c in gen] == ["https://mirror.example/x.pdf"]
    assert [a.resolver for a in attempts] == [CROSSREF, UNPAYWALL, EUROPE_PMC]


def test_europe_pmc_is_the_last_resort_and_builds_render_url():
    transport = FakeTransport({"https://api.crossref.org/": CROSSREF_EMPTY, "https://www.ebi.ac.uk/": EPMC_OPEN})
    candidates, _ = _run(transport, email=PLACEHOLDER)
    assert [c.url for c in candidates] == ["https://europepmc.org/articles/PMC999?pdf=render"]


def test_transport_error_is_recorded_and_chain_continues():
    transport = FakeTransport(
        {"https://api.crossref.org/": TransportError("HTTP 503"), "https://api.unpaywall.org/": UNPAYWALL_PDF}
    )
    candidates, attempts = _run(transport)
    assert attempts[0].outcome == "error" and "HTTP 503" in attempts[0].detail
    assert candidates and candidates[0].resolver == UNPAYWALL


def test_unpaywall_is_skipped_without_a_usable_email_and_never_requested():
    transport = FakeTransport({})
    _, attempts = _run(transport, email=PLACEHOLDER)
    unpaywall = [a for a in attempts if a.resolver == UNPAYWALL][0]
    assert unpaywall.outcome == "skipped"
    assert not any("unpaywall" in url for url in transport.requested)


def test_contact_email_is_sent_only_when_usable():
    transport = FakeTransport({})
    _run(transport, email=USABLE)
    assert any(f"mailto={USABLE.replace('@', '%40')}" in u for u in transport.requested)
    assert any(f"email={USABLE.replace('@', '%40')}" in u for u in transport.requested)
    transport2 = FakeTransport({})
    _run(transport2, email=PLACEHOLDER)
    assert not any("mailto=" in u for u in transport2.requested)


def test_email_usability_rules():
    assert email_is_usable(USABLE)
    assert not email_is_usable(PLACEHOLDER)
    assert not email_is_usable("")
    assert not email_is_usable(None)
    assert not email_is_usable("no-at-sign.org")
    assert not email_is_usable("someone@example.com")


def test_user_agent_carries_contact_only_when_usable():
    assert user_agent(USABLE).endswith(f"(mailto:{USABLE})")
    assert "mailto" not in user_agent(PLACEHOLDER)


def test_shipped_config_has_no_credentials_and_placeholder_email():
    cfg = load_config(DEFAULT_CONFIG, environ={})
    assert cfg.device == "cpu"
    assert cfg.output_root == "papers"
    assert cfg.unpaywall_email == PLACEHOLDER
    assert not email_is_usable(cfg.unpaywall_email)


def test_email_env_var_overrides_shipped_placeholder_without_touching_the_file():
    from mal_core.papers.config import EMAIL_ENV_VAR

    cfg = load_config(DEFAULT_CONFIG, environ={EMAIL_ENV_VAR: "  researcher@uni-mail.org "})
    assert cfg.unpaywall_email == "researcher@uni-mail.org"
    assert email_is_usable(cfg.unpaywall_email)
    # blank variable falls back to the file value
    assert load_config(DEFAULT_CONFIG, environ={EMAIL_ENV_VAR: "  "}).unpaywall_email == PLACEHOLDER
