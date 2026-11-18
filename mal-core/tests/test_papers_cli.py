"""CLI registration: `malariasim papers {fetch,extract,generate,check}` (plan §6.5), offline."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from _papers_fixtures import two_entry_manifest
from mal_core.cli import app

runner = CliRunner()


def test_papers_group_lists_the_four_subcommands():
    result = runner.invoke(app, ["papers", "--help"])
    assert result.exit_code == 0, result.output
    for name in ("fetch", "extract", "generate", "check"):
        assert name in result.output


def test_generate_check_is_a_drift_gate_on_a_temporary_corpus(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(two_entry_manifest()), encoding="utf-8")
    missing = runner.invoke(app, ["papers", "generate", "--check", "--papers-root", str(tmp_path)])
    assert missing.exit_code == 1

    written = runner.invoke(app, ["papers", "generate", "--papers-root", str(tmp_path)])
    assert written.exit_code == 0, written.output
    assert (tmp_path / "REFERENCES.md").is_file()

    clean = runner.invoke(app, ["papers", "generate", "--check", "--papers-root", str(tmp_path)])
    assert clean.exit_code == 0, clean.output


def test_invalid_manifest_exits_with_code_2(tmp_path):
    bad = two_entry_manifest()
    bad["entries"][0]["class"] = "Z"
    (tmp_path / "manifest.json").write_text(json.dumps(bad), encoding="utf-8")
    result = runner.invoke(app, ["papers", "generate", "--papers-root", str(tmp_path)])
    assert result.exit_code == 2
    assert "class must be one of" in result.output
