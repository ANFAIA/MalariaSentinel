"""The four §7 assertions, offline: resolver, hasher, git listing and sizes are injected."""
from __future__ import annotations

from pathlib import Path

from _papers_fixtures import VALID_SHA, make_entry, make_manifest, two_entry_manifest
from mal_core.papers.check import (
    allowlist_for,
    check_dois,
    check_doi_tokens,
    check_hashes,
    check_tracked,
    extract_doi_tokens,
    read_documents,
    run_checks,
)
from mal_core.papers.manifest import Entry, Manifest, parse_manifest
from mal_core.papers.provenance import update_provenance

DOI_A = "10.1186/s12936-000-0001-x"
DOI_B = "10.1371/journal.pone.0050464"


def _manifest(*entries):
    return parse_manifest(make_manifest(*entries))


# (a) DOIs ------------------------------------------------------------------

def test_a_structural_pass_when_doi_present_and_no_network_call():
    calls = []
    report = check_dois(parse_manifest(two_entry_manifest()), resolve=False, resolver=lambda d: calls.append(d))
    assert report.ok and calls == []


def test_a_missing_doi_without_pending_reason_fails():
    # The schema rejects this combination (ok needs a DOI or pmc:/hal: id), so bypass validation
    # to exercise the defensive branch of check_dois.
    entry = Entry.from_dict(make_entry(doi=None, expected_status="ok"))
    report = check_dois(Manifest(entries=(entry,)))
    assert not report.ok
    assert "gives no pending reason" in report.failures[0]


def test_a_missing_doi_with_pending_reason_is_a_note():
    entry = make_entry(doi=None, expected_status="pending_paywalled")
    report = check_dois(_manifest(entry))
    assert report.ok
    assert any("pending_paywalled" in n for n in report.notes)


def test_a_pmc_identifier_without_doi_is_an_obtainable_source_not_a_failure():
    entry = make_entry(doi=None, expected_status="ok")
    entry["id"] = "pmc:PMC12888552"
    report = check_dois(_manifest(entry))
    assert report.ok
    assert any("pmc:PMC12888552" in n for n in report.notes)


def test_a_resolver_verdicts_map_to_failure_warning_and_pass():
    verdicts = {DOI_A: True, DOI_B: False}
    manifest = parse_manifest(two_entry_manifest())
    report = check_dois(manifest, resolve=True, resolver=lambda d: verdicts.get(d))
    assert len(report.failures) == 1 and DOI_B in report.failures[0]
    assert report.warnings == []
    unreachable = check_dois(manifest, resolve=True, resolver=lambda d: None)
    assert unreachable.ok and len(unreachable.warnings) == 2


# (b) doi: tokens -----------------------------------------------------------

def test_b_known_tokens_pass_and_unknown_token_is_reported_with_location():
    manifest = parse_manifest(two_entry_manifest())
    docs = {
        "docs/a.md": f"see doi:{DOI_A}.\n",
        "docs/b.md": "line one\nsee (doi:10.9999/unknown.1) here\n",
    }
    report = check_doi_tokens(manifest, docs)
    assert len(report.failures) == 1
    assert report.failures[0].startswith("docs/b.md:2: doi:10.9999/unknown.1")


def test_b_bare_registrant_prefix_without_suffix_is_not_a_doi_token():
    # Prose such as "doi:10.1136/ " or "doi:10.1136/)" has no suffix: it must not be extracted.
    text = "see doi:10.1136/ here, doi:10.1136/) there, and doi:10.1136/x.y for real"
    assert [d for _, d in extract_doi_tokens(text)] == ["10.1136/x.y"]
    manifest = parse_manifest(two_entry_manifest())
    assert check_doi_tokens(manifest, {"p.md": "doi:10.1136/ "}).ok


def test_b_truncated_doi_token_is_not_silently_accepted():
    manifest = parse_manifest(two_entry_manifest())
    report = check_doi_tokens(manifest, {"docs/x.md": "per doi:10.1186/s12936-0 we infer"})
    assert not report.ok


def test_b_doi_matching_is_case_insensitive_and_strips_variant_suffix():
    manifest = parse_manifest(two_entry_manifest())
    tokens = extract_doi_tokens("doi:10.1186/S12936-000-0001-X#fig2 and doi:10.1371/journal.pone.0050464`")
    assert [d for _, d in tokens] == ["10.1186/S12936-000-0001-X", "10.1371/journal.pone.0050464"]
    report = check_doi_tokens(manifest, {"d.md": "doi:10.1186/S12936-000-0001-X#fig2"})
    assert report.ok


# (c) sha256 ----------------------------------------------------------------

def _fetched(tmp_path: Path, entry: dict) -> Path:
    pdf = tmp_path / entry["theme"] / entry["slug"] / f"{entry['slug']}.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fixture")
    return pdf


def test_c_match_passes_mismatch_fails_and_unpinned_warns(tmp_path):
    pinned = make_entry(pdf_sha256=VALID_SHA)
    manifest = _manifest(pinned)
    _fetched(tmp_path, pinned)
    assert check_hashes(manifest, tmp_path, hasher=lambda p: VALID_SHA).ok
    bad = check_hashes(manifest, tmp_path, hasher=lambda p: "b" * 64)
    assert not bad.ok and "manifest pins" in bad.failures[0]

    unpinned = _manifest(make_entry())
    report = check_hashes(unpinned, tmp_path, hasher=lambda p: "never called")
    assert report.ok and "not pinned" in report.warnings[0]


def test_c_absent_pdf_with_observed_ok_in_provenance_is_a_failure(tmp_path):
    entry = make_entry(pdf_sha256=VALID_SHA)
    manifest = _manifest(entry)
    # provenance.yaml is the only record of observed status; "ok" with no PDF on disk is broken.
    update_provenance(tmp_path / entry["theme"] / entry["slug"], observed_status="ok")
    report = check_hashes(manifest, tmp_path, hasher=lambda p: VALID_SHA)
    assert not report.ok and "observed_status ok but" in report.failures[0]


def test_c_absent_pdf_is_not_checked_and_is_counted(tmp_path):
    report = check_hashes(_manifest(make_entry(pdf_sha256=VALID_SHA)), tmp_path, hasher=lambda p: "x")
    assert report.ok
    assert report.notes == ["1 entries have no PDF on disk (not checked)"]


# (d) tracked files ---------------------------------------------------------

def test_d_tracked_set_equal_to_allowlist_and_small_files_pass():
    allow = allowlist_for("papers")
    report = check_tracked(
        [*allow, "docs/unrelated.md", "papers-other/x.md"],
        prefix="papers",
        allowlist=allow,
        size_of=lambda p: 10,
    )
    assert report.ok


def test_d_unallowlisted_file_and_missing_allowlisted_file_fail():
    allow = allowlist_for("papers")
    report = check_tracked(
        [allow[0], "papers/abm-geospatial/x.md"],
        prefix="papers",
        allowlist=allow,
        size_of=lambda p: 10,
    )
    assert not report.ok
    joined = " ".join(report.failures)
    assert "not allowlisted" in joined and "not tracked" in joined


def test_d_file_over_64_kib_fails_and_boundary_passes():
    allow = allowlist_for("papers")
    sizes = {"papers/big.md": 64 * 1024 + 1, "papers/edge.md": 64 * 1024}
    report = check_tracked(
        [*allow, "papers/big.md", "papers/edge.md"],
        prefix="papers",
        allowlist=allow,
        size_of=lambda p: sizes.get(p, 1),
    )
    over = [f for f in report.failures if "tracked with" in f]
    assert len(over) == 1 and "big.md" in over[0]


# aggregate ----------------------------------------------------------------

def test_run_checks_merges_all_four_and_offline_by_default(tmp_path):
    manifest = parse_manifest(two_entry_manifest())
    allow = allowlist_for("papers")
    report = run_checks(
        manifest,
        papers_root=tmp_path,
        prefix="papers",
        documents={"docs/a.md": f"doi:{DOI_A}"},
        tracked=list(allow),
        size_of=lambda p: 1,
    )
    assert report.ok
    assert any("not checked" in n for n in report.notes)


def test_read_documents_skips_binary_and_unknown_suffixes(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("doi:10.1000/x.1", encoding="utf-8")
    (tmp_path / "docs" / "img.png").write_bytes(b"\x89PNG")
    docs = read_documents(tmp_path, ["docs/a.md", "docs/img.png", "docs/missing.md"])
    assert list(docs) == ["docs/a.md"]


def test_http_resolver_falls_back_to_doi_org_when_crossref_is_unknown(monkeypatch):
    from mal_core.papers import check as chk

    calls: list[tuple[str, str]] = []

    def fake_probe(url, method, timeout):
        calls.append((url, method))
        if "api.crossref.org" in url:
            return False  # Crossref does not register this DOI (e.g. DataCite)
        return True  # doi.org knows it

    monkeypatch.setattr(chk, "_probe", fake_probe)
    assert chk.http_doi_resolver("10.5281/zenodo.1") is True
    assert calls[0][0].startswith("https://api.crossref.org/works/")


def test_http_resolver_reports_unknown_when_both_say_404(monkeypatch):
    from mal_core.papers import check as chk

    monkeypatch.setattr(chk, "_probe", lambda url, method, timeout: False)
    assert chk.http_doi_resolver("10.9999/none") is False


def test_http_resolver_none_when_network_unreachable(monkeypatch):
    from mal_core.papers import check as chk

    monkeypatch.setattr(chk, "_probe", lambda url, method, timeout: None)
    assert chk.http_doi_resolver("10.1111/x.y") is None
