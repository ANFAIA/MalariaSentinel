"""Tests for InboxCheckMiddleware."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from agents_janus.middleware.inbox_check import (
    InboxCheckMiddleware,
    _extract_agent_id,
    _mark_conflict,
    _inject_messages,
)


class TestExtractAgentId:
    def test_dict_with_agent_id(self):
        assert _extract_agent_id({"agent_id": "a_abm"}) == "a_abm"

    def test_dict_without_agent_id(self):
        assert _extract_agent_id({"file": "foo.py"}) is None

    def test_none(self):
        assert _extract_agent_id(None) is None

    def test_empty_dict(self):
        assert _extract_agent_id({}) is None


class TestMarkConflict:
    def test_string_result(self):
        result = _mark_conflict("tool output", {
            "from_agent": "a_scoring",
            "message": "editing D14",
            "files": ["scorers/D14.py"],
        })
        assert "🛑 CONFLICT DETECTED" in result
        assert "a_scoring" in result
        assert "scorers/D14.py" in result
        assert "resolve_conflict" in result

    def test_dict_result(self):
        result = _mark_conflict({"status": "ok"}, {
            "from_agent": "a_scoring",
            "message": "editing D14",
            "files": ["scorers/D14.py"],
        })
        assert "CONFLICT DETECTED" in result


class TestInjectMessages:
    def test_no_messages(self):
        assert _inject_messages("output", []) == "output"

    def test_single_message(self):
        result = _inject_messages("output", [
            {"from_agent": "a_ingest", "message": "data ready"},
        ])
        assert "📬 Inbox messages:" in result
        assert "[a_ingest]: data ready" in result

    def test_multiple_messages(self):
        result = _inject_messages("output", [
            {"from_agent": "a_ingest", "message": "data ready"},
            {"from_agent": "a_scoring", "message": "D14 done"},
        ])
        assert "[a_ingest]: data ready" in result
        assert "[a_scoring]: D14 done" in result


class TestInboxCheckMiddleware:
    def test_no_agent_id_passthrough(self):
        mw = InboxCheckMiddleware()
        handler = MagicMock(return_value="result")
        request = MagicMock()
        request.tool_call = {"name": "read_file", "args": {"file": "foo.py"}}

        result = mw.wrap_tool_call(request, handler)
        assert result == "result"
        handler.assert_called_once_with(request)

    def test_tracks_agent_id_from_register(self):
        mw = InboxCheckMiddleware()
        handler = MagicMock(return_value="registered")

        # First call: register_agent sets agent_id
        req1 = MagicMock()
        req1.tool_call = {"name": "mcp__gitagent__register_agent", "args": {"agent_id": "a_abm"}}
        mw.wrap_tool_call(req1, handler)
        assert mw._agent_id == "a_abm"

    @patch("agents_janus.middleware.inbox_check._check_inbox_via_mcp")
    def test_injects_routine_messages(self, mock_check):
        mock_check.return_value = [
            {"from_agent": "a_ingest", "message": "data ready"},
        ]
        mw = InboxCheckMiddleware()
        mw._agent_id = "a_abm"
        handler = MagicMock(return_value="tool output")

        req = MagicMock()
        req.tool_call = {"name": "mcp__gitagent__edit_file", "args": {"agent_id": "a_abm", "file": "foo.py"}}
        result = mw.wrap_tool_call(req, handler)

        assert "📬 Inbox messages:" in result
        assert "[a_ingest]: data ready" in result

    @patch("agents_janus.middleware.inbox_check._check_inbox_via_mcp")
    def test_detects_conflict(self, mock_check):
        # gawt sends kind="conflict" with payload as a JSON string
        mock_check.return_value = [
            {"kind": "conflict", "from_agent": "a_scoring", "payload": '{"file": "D14.py", "conflicting_agent": "a_scoring"}'},
        ]
        mw = InboxCheckMiddleware()
        mw._agent_id = "a_abm"
        handler = MagicMock(return_value="tool output")

        req = MagicMock()
        req.tool_call = {"name": "mcp__gitagent__edit_file", "args": {"agent_id": "a_abm", "file": "D14.py"}}
        result = mw.wrap_tool_call(req, handler)

        assert "CONFLICT DETECTED" in result
        assert "a_scoring" in result
        assert "D14.py" in result

    @patch("agents_janus.middleware.inbox_check._check_inbox_via_mcp")
    def test_conflict_with_dict_payload(self, mock_check):
        # Some gawt versions may already parse payload to a dict
        mock_check.return_value = [
            {"kind": "conflict", "from_agent": "a_scoring", "payload": {"file": "D14.py", "other_edit_ts": "..."}},
        ]
        mw = InboxCheckMiddleware()
        mw._agent_id = "a_abm"
        handler = MagicMock(return_value="tool output")

        req = MagicMock()
        req.tool_call = {"name": "mcp__gitagent__edit_file", "args": {"agent_id": "a_abm", "file": "D14.py"}}
        result = mw.wrap_tool_call(req, handler)

        assert "CONFLICT DETECTED" in result
        assert "D14.py" in result

    @patch("agents_janus.middleware.inbox_check._check_inbox_via_mcp")
    def test_mcp_failure_passthrough(self, mock_check):
        mock_check.side_effect = Exception("MCP down")
        mw = InboxCheckMiddleware()
        mw._agent_id = "a_abm"
        handler = MagicMock(return_value="tool output")

        req = MagicMock()
        req.tool_call = {"name": "edit_file", "args": {"agent_id": "a_abm"}}
        result = mw.wrap_tool_call(req, handler)

        # Should pass through without crashing
        assert result == "tool output"

    @patch("agents_janus.middleware.inbox_check._check_inbox_via_mcp")
    def test_empty_inbox_passthrough(self, mock_check):
        mock_check.return_value = []
        mw = InboxCheckMiddleware()
        mw._agent_id = "a_abm"
        handler = MagicMock(return_value="tool output")

        req = MagicMock()
        req.tool_call = {"name": "edit_file", "args": {"agent_id": "a_abm"}}
        result = mw.wrap_tool_call(req, handler)

        assert result == "tool output"
