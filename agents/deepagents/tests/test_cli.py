"""Tests for cli.py — --no-verify, --goal, --dry-run."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from agents.deepagents.cli import app

runner = CliRunner()


class TestCalibrationCommand:
    @patch("agents.deepagents.cycles.calibration_cycle.run_calibration_cycle")
    def test_calibration_dry_run(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "dry_run"})
        result = runner.invoke(app, ["calibration", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0

    @patch("agents.deepagents.cycles.calibration_cycle.run_calibration_cycle")
    def test_calibration_no_verify(self, mock_cycle):
        mock_cycle.return_value = "done"
        result = runner.invoke(app, ["calibration", "-g", "test goal", "--no-verify", "--provider", "openrouter", "--model", "test"])
        assert result.exit_code == 0


class TestFeatureCommand:
    @patch("agents.deepagents.cycles.feature_cycle.run_feature_cycle")
    def test_feature_dry_run(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "dry_run"})
        result = runner.invoke(app, ["feature", "test-feat", "test desc", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0


class TestResearchCommand:
    @patch("agents.deepagents.cycles.research_cycle.run_research_cycle")
    def test_research_dry_run(self, mock_cycle):
        mock_cycle.return_value = json.dumps({"status": "dry_run"})
        result = runner.invoke(app, ["research", "malaria", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0
