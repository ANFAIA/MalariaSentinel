"""Tests for Janus CLI entry points."""
from __future__ import annotations

import json

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

    def test_prompts_command_renders_snapshot(self, tmp_path):
        snapshot = tmp_path / "prompt_snapshots.jsonl"
        snapshot.write_text(json.dumps({
            "ts": "now",
            "agent_role": "abm",
            "system_prompt": "Be precise.",
            "messages": [{"type": "HumanMessage", "content": "Inspect ABM."}],
            "tools": [{"name": "read_file", "description": "Read file."}],
        }) + "\n")

        result = runner.invoke(app, ["prompts", str(tmp_path)])

        assert result.exit_code == 0
        assert "Be precise." in result.output
        assert "read_file" in result.output
