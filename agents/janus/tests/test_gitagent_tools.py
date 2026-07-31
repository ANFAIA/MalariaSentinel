"""Tests for gitagent_tool.py — all 12 functions."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from agents.janus.tools.gitagent_tool import (
    gitagent_init,
    gitagent_start,
    gitagent_spawn,
    gitagent_list_agents,
    gitagent_kill,
    gitagent_proposals,
    gitagent_diff,
    gitagent_accept,
    gitagent_reject,
    gitagent_revise,
    gitagent_integrate,
    gitagent_finalize,
)


def _mock_subprocess(returncode=0, stdout="", stderr=""):
    """Create a mock subprocess.run result."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


class TestGitagentInit:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_init_success(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Initialized", "")
        result = json.loads(gitagent_init())
        assert result["status"] == "initialized"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_init_already_initialized(self, mock_run):
        mock_run.return_value = _mock_subprocess(1, "", "already initialized")
        result = json.loads(gitagent_init())
        assert result["status"] == "already_initialized"


class TestGitagentStart:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_start_success(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Session s_abc123 (test-feature) at sha -> main", "")
        result = json.loads(gitagent_start("test-feature"))
        assert result["status"] == "started"
        assert result["feature"] == "test-feature"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_start_failure(self, mock_run):
        mock_run.return_value = _mock_subprocess(1, "", "Session already active")
        result = json.loads(gitagent_start("test-feature"))
        assert result["status"] == "failed"


class TestGitagentSpawn:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    @patch("agents.janus.tools.gitagent_tool.Path")
    def test_spawn_parses_worktree(self, mock_path, mock_run):
        mock_run.return_value = _mock_subprocess(
            0, "Agent abm-worker-1 -> \n/tmp/worktree/path", ""
        )
        # Mock Path.is_dir() to return True for the worktree path
        mock_path_instance = MagicMock()
        mock_path_instance.is_dir.return_value = True
        mock_path.return_value = mock_path_instance

        result = json.loads(gitagent_spawn("test-feature", "abm-worker-1", "abm"))
        assert result["status"] == "spawned"
        assert result["agent_id"] == "abm-worker-1"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_spawn_failure(self, mock_run):
        mock_run.return_value = _mock_subprocess(1, "", "Agent already exists")
        result = json.loads(gitagent_spawn("test-feature", "abm-worker-1", "abm"))
        assert result["status"] == "failed"


class TestGitagentProposals:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_proposals_json(self, mock_run):
        proposals_data = [
            {"manifest": {"id": "p_abc", "title": "test"}, "review": {"state": "pending"}}
        ]
        mock_run.return_value = _mock_subprocess(0, json.dumps(proposals_data), "")
        result = json.loads(gitagent_proposals("test-feature"))
        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["proposals"][0]["manifest"]["id"] == "p_abc"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_proposals_empty(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "[]", "")
        result = json.loads(gitagent_proposals("test-feature"))
        assert result["status"] == "ok"
        assert result["count"] == 0


class TestGitagentDiff:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_diff_success(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "diff --git a/file.py ...", "")
        result = json.loads(gitagent_diff("p_abc", "test-feature"))
        assert result["status"] == "ok"
        assert "diff" in result


class TestGitagentDecisions:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_accept(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Accepted", "")
        result = json.loads(gitagent_accept("p_abc", "test-feature"))
        assert result["status"] == "accepted"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_reject(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Rejected", "")
        result = json.loads(gitagent_reject("p_abc", "test-feature", "bad code"))
        assert result["status"] == "rejected"
        assert result["reason"] == "bad code"

    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_revise(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Revised", "")
        result = json.loads(gitagent_revise("p_abc", "test-feature", "fix this"))
        assert result["status"] == "revised"


class TestGitagentIntegrate:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_integrate_no_verify(self, mock_run):
        integrate_result = {"applied": ["p_abc"], "conflicted": [], "skipped": []}
        mock_run.return_value = _mock_subprocess(0, json.dumps(integrate_result), "")
        result = json.loads(gitagent_integrate("test-feature", verify=False))
        assert result["status"] == "ok"
        assert result["applied"] == ["p_abc"]


class TestGitagentFinalize:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_finalize_no_verify(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Finalized. Single commit abc123.", "")
        result = json.loads(gitagent_finalize("test-feature", "test commit", verify=False))
        assert result["status"] == "finalized"

    @patch("builtins.input", return_value="y")
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_finalize_with_verify_accepted(self, mock_run, mock_input):
        proposals_data = [
            {"manifest": {"id": "p_abc", "title": "test"}, "review": {"state": "accepted"}}
        ]
        # First call: proposals --json; Second call: finalize
        mock_run.side_effect = [
            _mock_subprocess(0, json.dumps(proposals_data), ""),
            _mock_subprocess(0, "Finalized. Single commit abc123.", ""),
        ]
        result = json.loads(gitagent_finalize("test-feature", "test commit", verify=True))
        assert result["status"] == "finalized"

    @patch("builtins.input", return_value="n")
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_finalize_with_verify_rejected(self, mock_run, mock_input):
        proposals_data = [
            {"manifest": {"id": "p_abc", "title": "test"}, "review": {"state": "accepted"}}
        ]
        mock_run.return_value = _mock_subprocess(0, json.dumps(proposals_data), "")
        result = json.loads(gitagent_finalize("test-feature", "test commit", verify=True))
        assert result["status"] == "aborted"


class TestGitagentListAgents:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_list_agents_json(self, mock_run):
        agents_data = [{"id": "abm-worker-1", "role": "abm", "worktree": "/tmp/wt"}]
        mock_run.return_value = _mock_subprocess(0, json.dumps(agents_data), "")
        result = json.loads(gitagent_list_agents("test-feature"))
        assert result["status"] == "ok"


class TestGitagentKill:
    @patch("agents.janus.tools.gitagent_tool.subprocess.run")
    def test_kill_success(self, mock_run):
        mock_run.return_value = _mock_subprocess(0, "Killed", "")
        result = json.loads(gitagent_kill("abm-worker-1", "test-feature"))
        assert result["status"] == "killed"
