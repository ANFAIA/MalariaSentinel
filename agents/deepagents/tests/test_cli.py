"""Tests for cli.py — run command with auto-detect mode and --mode flag."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from agents.deepagents.cli import app

runner = CliRunner()


class TestRunCommand:
    @patch("agents.deepagents.cycles.run_cycle.run_cycle")
    def test_run_dry_run_auto_mode(self, mock_cycle):
        """`run` with --dry-run auto-detects mode from goal."""
        mock_cycle.return_value = json.dumps({"status": "dry_run", "mode": "calibration"})
        result = runner.invoke(app, ["run", "-g", "calibration of population extinction", "--dry-run"])
        assert result.exit_code == 0

    @patch("agents.deepagents.cycles.run_cycle.run_cycle")
    def test_run_explicit_mode(self, mock_cycle):
        """`run --mode feature` passes explicit mode."""
        mock_cycle.return_value = json.dumps({"status": "ok", "mode": "feature"})
        result = runner.invoke(app, ["run", "-g", "test goal", "--mode", "feature"])
        assert result.exit_code == 0

    @patch("agents.deepagents.cycles.run_cycle.run_cycle")
    def test_run_no_verify(self, mock_cycle):
        """`run --no-verify` skips approval gates."""
        mock_cycle.return_value = "done"
        result = runner.invoke(app, ["run", "-g", "test goal", "--no-verify", "--provider", "openrouter", "--model", "test"])
        assert result.exit_code == 0

    def test_run_invalid_mode(self):
        """Invalid mode is rejected."""
        result = runner.invoke(app, ["run", "-g", "test", "--mode", "invalid"])
        assert result.exit_code != 0

    @patch("agents.deepagents.cycles.run_cycle.run_cycle")
    def test_run_research_mode(self, mock_cycle):
        """Research mode passes through."""
        mock_cycle.return_value = json.dumps({"status": "ok", "mode": "research"})
        result = runner.invoke(app, ["run", "-g", "review literature on Anopheles", "--mode", "research"])
        assert result.exit_code == 0


class TestBackwardsCompatDeprecated:
    """The old calibration/feature/research commands still work but emit deprecation warnings."""

    @patch("agents.deepagents.cycles.run_cycle.run_calibration_cycle")
    def test_calibration_alias_works(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "ok"})
        result = runner.invoke(app, ["calibration", "-g", "test", "--dry-run"])
        assert result.exit_code == 0

    @patch("agents.deepagents.cycles.run_cycle.run_feature_cycle")
    def test_feature_alias_works(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "ok"})
        result = runner.invoke(app, ["feature", "test-feat", "test desc", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0

    @patch("agents.deepagents.cycles.run_cycle.run_research_cycle")
    def test_research_alias_works(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "ok"})
        result = runner.invoke(app, ["research", "topic", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0