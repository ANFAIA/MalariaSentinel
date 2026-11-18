"""Extract: docling argument list (no shell), device policy, provenance, failure as status (D2)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from _papers_fixtures import make_entry
from mal_core.papers.extract import (
    EXTRACT_FLAGS,
    docling_command,
    docling_version,
    extract_entry,
    validate_device,
)
from mal_core.papers.manifest import Entry

FIXED = "2026-01-01T00:00:00+00:00"


def _entry() -> Entry:
    return Entry.from_dict(make_entry())


def _paper(root, entry: Entry):
    folder = root / entry.theme / entry.slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{entry.slug}.pdf").write_bytes(b"%PDF-1.4 fixture")
    return folder


def _proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_command_is_an_argument_list_with_the_fixed_flags(tmp_path):
    cmd = docling_command(tmp_path / "x.pdf", tmp_path, device="cpu")
    assert isinstance(cmd, list) and all(isinstance(a, str) for a in cmd)
    assert cmd[:2] == ["docling", "convert"]
    for flag in ("--tables", "--ocr", "--no-enrich-picture-description", "--image-export-mode", "referenced"):
        assert flag in cmd
    assert cmd[cmd.index("--device") + 1] == "cpu"
    assert cmd[-1].endswith("x.pdf")


def test_device_policy_allows_only_cpu_and_mps():
    assert validate_device("mps") == "mps"
    for bad in ("cuda", "auto", "MPS", ""):
        with pytest.raises(ValueError):
            validate_device(bad)
        with pytest.raises(ValueError):
            docling_command(Path("a.pdf"), Path("."), device=bad)


def test_flags_constant_matches_plan():
    assert EXTRACT_FLAGS[:2] == ("--to", "md")
    assert "--enrich-picture-description" not in EXTRACT_FLAGS


def test_docling_version_is_parsed_from_version_output():
    run = lambda cmd, **kw: _proc(stdout="Docling version: 2.132.0\nDocling Core version: 2.99.0\n")
    assert docling_version("docling", run=run) == "2.132.0"
    assert docling_version("docling", run=lambda cmd, **kw: _proc(stdout="???")) == "unknown"


def test_missing_pdf_is_skipped_without_running_docling(tmp_path):
    calls = []
    result = extract_entry(_entry(), tmp_path, device="cpu", run=lambda *a, **k: calls.append(a), version="2.132.0")
    assert result.status == "skipped"
    assert calls == []


def test_success_renames_artifacts_rewrites_links_and_records_provenance(tmp_path):
    entry = _entry()
    folder = _paper(tmp_path, entry)

    def fake_run(cmd, **kwargs):
        assert kwargs.get("check") is False
        assert "shell" not in kwargs
        (folder / f"{entry.slug}.md").write_text(f"# T\n![fig]({entry.slug}_artifacts/image_000.png)\n", encoding="utf-8")
        (folder / f"{entry.slug}_artifacts").mkdir()
        (folder / f"{entry.slug}_artifacts" / "image_000.png").write_bytes(b"png")
        return _proc(0)

    result = extract_entry(entry, tmp_path, device="mps", run=fake_run, version="2.132.0", extracted_at=FIXED)
    assert result.status == "extracted" and result.observed_status == "ok"
    md = (folder / f"{entry.slug}.md").read_text(encoding="utf-8")
    assert "](images/image_000.png)" in md
    assert (folder / "images" / "image_000.png").is_file()
    assert not (folder / f"{entry.slug}_artifacts").exists()

    prov = yaml.safe_load((folder / "provenance.yaml").read_text(encoding="utf-8"))
    assert prov["observed_status"] == "ok"
    assert prov["extract"]["docling_version"] == "2.132.0"
    assert prov["extract"]["device"] == "mps"
    assert prov["extract"]["status"] == "extracted"
    assert "--no-enrich-picture-description" in prov["extract"]["flags"]


def test_nonzero_exit_is_recorded_as_pending_extraction_failed(tmp_path):
    entry = _entry()
    folder = _paper(tmp_path, entry)
    result = extract_entry(
        entry, tmp_path, device="cpu",
        run=lambda cmd, **kw: _proc(2, stderr="boom\nlast line\n"),
        version="2.132.0",
    )
    assert result.status == "failed"
    assert result.observed_status == "pending_extraction_failed"
    prov = yaml.safe_load((folder / "provenance.yaml").read_text(encoding="utf-8"))
    assert prov["observed_status"] == "pending_extraction_failed"
    assert prov["extract"]["returncode"] == 2
    assert "last line" in prov["extract"]["detail"]


def test_exit_zero_without_markdown_is_a_failure(tmp_path):
    entry = _entry()
    _paper(tmp_path, entry)
    result = extract_entry(entry, tmp_path, device="cpu", run=lambda cmd, **kw: _proc(0), version="x")
    assert result.observed_status == "pending_extraction_failed"
    assert "produced no" in result.detail


def test_docling_missing_is_reported_not_raised(tmp_path):
    entry = _entry()
    _paper(tmp_path, entry)

    def missing(cmd, **kw):
        raise FileNotFoundError("docling")

    result = extract_entry(entry, tmp_path, device="cpu", run=missing, version="x")
    assert result.status == "failed"
    assert "cannot run docling" in result.detail
