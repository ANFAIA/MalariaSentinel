"""Tests for Janus CLI entry points."""
from __future__ import annotations

from typer.testing import CliRunner

from agents_janus.cli import app

runner = CliRunner()


class TestCommandRegistration:
    def test_improve_command_exists(self):
        result = runner.invoke(app, ["improve", "--help"])
        assert result.exit_code == 0
        assert "implementation coordinator" in result.output.lower()

    def test_run_command_removed(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code != 0
