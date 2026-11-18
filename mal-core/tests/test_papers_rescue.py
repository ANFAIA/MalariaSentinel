"""Rescue back end: open-licence filter, adopt checks, candidate listing. No network."""
from __future__ import annotations

import pytest
import yaml

from _papers_fixtures import make_entry
from mal_core.papers.manifest import Entry
from mal_core.papers.provenance import sha256_bytes
from mal_core.papers.rescue import adopt_pdf, is_open_licence, rescue_candidates

PDF = b"%PDF-1.4\n% rescued fixture\n"
CC_BY = "https://creativecommons.org/licenses/by/4.0/"


def _entry(**kw) -> Entry:
    return Entry.from_dict(make_entry(**kw))


def _paywalled(root, entry: Entry) -> None:
    d = root / entry.theme / entry.slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "provenance.yaml").write_text(
        yaml.safe_dump({"id": entry.id, "observed_status": "pending_paywalled"}), encoding="utf-8"
    )


@pytest.mark.parametrize(
    "licence, expected",
    [
        (CC_BY, True),
        ("https://creativecommons.org/publicdomain/zero/1.0/", True),
        ("cc-by", True),
        ("cc0", True),
        ("CC BY 4.0", True),
        ("https://www.elsevier.com/tdm/userlicense/1.0/", False),
        ("https://onlinelibrary.wiley.com/termsAndConditions", False),
        ("", False),
        (None, False),
    ],
)
def test_open_licence_filter(licence, expected):
    assert is_open_licence(licence) is expected


def test_adopt_records_valid_pdf_as_ok(tmp_path):
    entry = _entry(pdf_sha256=sha256_bytes(PDF))
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    result = adopt_pdf(entry, tmp_path / "papers", src, source_url="https://example.org/a.pdf", licence=CC_BY)
    assert result.observed_status == "ok"
    assert result.pdf_path is not None and result.pdf_path.read_bytes() == PDF
    prov = yaml.safe_load((tmp_path / "papers" / entry.theme / entry.slug / "provenance.yaml").read_text())
    assert prov["observed_status"] == "ok"
    assert prov["fetch"]["resolver"] == "rescue"
    assert prov["fetch"]["source_url"] == "https://example.org/a.pdf"


def test_adopt_refuses_non_pdf_without_touching_provenance(tmp_path):
    entry = _entry()
    src = tmp_path / "page.html"
    src.write_bytes(b"<!DOCTYPE html><title>Client Challenge</title>")
    with pytest.raises(ValueError, match="not a PDF"):
        adopt_pdf(entry, tmp_path / "papers", src, source_url="https://x", licence=CC_BY)
    assert not (tmp_path / "papers" / entry.theme / entry.slug).exists()


def test_adopt_refuses_sha_mismatch(tmp_path):
    entry = _entry(pdf_sha256="0" * 64)
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    with pytest.raises(ValueError, match="sha256"):
        adopt_pdf(entry, tmp_path / "papers", src, source_url="https://x", licence=CC_BY)


def test_adopt_refuses_closed_licence(tmp_path):
    entry = _entry()
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    with pytest.raises(ValueError, match="not open"):
        adopt_pdf(entry, tmp_path / "papers", src, source_url="https://x", licence="Elsevier TDM")


def test_candidates_list_only_paywalled_entries_with_open_licence(tmp_path):
    from mal_core.papers.manifest import Manifest

    root = tmp_path / "papers"
    open_entry = _entry(doi="10.1186/open-1", slug="open-paper-2020")
    closed_entry = _entry(doi="10.1016/closed-1", slug="closed-paper-2020")
    ok_entry = _entry(doi="10.1186/ok-1", slug="ok-paper-2020")
    for e in (open_entry, closed_entry):
        _paywalled(root, e)
    ok_dir = root / ok_entry.theme / ok_entry.slug
    ok_dir.mkdir(parents=True)
    (ok_dir / "provenance.yaml").write_text(yaml.safe_dump({"observed_status": "ok"}), encoding="utf-8")

    def get_json(url: str):
        if "open-1" in url:
            return {"message": {"link": [{"URL": "https://pub.example/open.pdf", "content-type": "application/pdf"}],
                                "license": [{"URL": CC_BY}]}}
        if "closed-1" in url:
            return {"message": {"link": [{"URL": "https://pub.example/closed.pdf", "content-type": "application/pdf"}],
                                "license": [{"URL": "https://www.elsevier.com/tdm/userlicense/1.0/"}]}}
        return {"message": {}}

    manifest = Manifest(entries=(open_entry, closed_entry, ok_entry))
    items = rescue_candidates(manifest, root, get_json=get_json, email=None)
    assert [i.entry.id for i in items] == [open_entry.id]
    assert items[0].candidates[0].url == "https://pub.example/open.pdf"
