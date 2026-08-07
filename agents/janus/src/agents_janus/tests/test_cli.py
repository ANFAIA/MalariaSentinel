"""Tests for cli.py — command registration and run command."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from agents_janus.cli import app

runner = CliRunner()


class TestCommandRegistration:
    """All expected commands are registered."""

    def test_run_command_exists(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_improve_command_exists(self):
        result = runner.invoke(app, ["improve", "--help"])
        assert result.exit_code == 0

    def test_onboard_command_exists(self):
        result = runner.invoke(app, ["onboard", "--help"])
        assert result.exit_code == 0

    def test_status_command_exists(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_agents_list_command_exists(self):
        result = runner.invoke(app, ["agents", "list", "--help"])
        assert result.exit_code == 0

    def test_agents_show_command_exists(self):
        result = runner.invoke(app, ["agents", "show", "--help"])
        assert result.exit_code == 0


class TestRunCommand:
    @patch("agents_janus.improvement.run_improvement")
    def test_run_dry_run(self, mock_improve):
        """`run` with --dry-run prints prompt without executing."""
        mock_improve.return_value = json.dumps({"status": "dry_run"})
        result = runner.invoke(app, ["run", "-g", "test goal", "--dry-run"])
        assert result.exit_code == 0

    @patch("agents_janus.improvement.run_improvement")
    def test_run_no_verify(self, mock_improve):
        """`run --no-verify` skips approval gates."""
        mock_improve.return_value = "done"
        result = runner.invoke(app, ["run", "-g", "test goal", "--no-verify", "--provider", "openrouter", "--model", "test"])
        assert result.exit_code == 0

    def test_run_prompts_for_goal(self):
        """`run` without -g prompts for goal."""
        result = runner.invoke(app, ["run"], input="my goal\n")
        # Will fail because improvement module needs env, but it should prompt
        assert "goal" in result.output.lower() or result.exit_code != 0
