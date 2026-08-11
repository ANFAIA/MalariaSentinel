"""Tests for resolve_conflict tool."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from agents_janus.tools.resolve_conflict import (
    CONFLICT_RESOLUTION_SCHEMA,
    make_resolve_conflict_tool,
    set_agent_ref,
    _agent_ref,
    _fork_depth,
    _make_escalation_doc,
)


class TestConflictResolutionSchema:
    def test_has_required_fields(self):
        required = CONFLICT_RESOLUTION_SCHEMA["required"]
        assert "resolution_id" in required
        assert "timestamp" in required
        assert "conflict" in required
        assert "decision" in required
        assert "summary" in required

    def test_decision_enum(self):
        decisions = CONFLICT_RESOLUTION_SCHEMA["properties"]["decision"]["enum"]
        assert "adapt" in decisions
        assert "counter_propose" in decisions
        assert "both" in decisions
        assert "escalate" in decisions


class TestMakeEscalationDoc:
    def test_basic(self):
        doc = _make_escalation_doc("conflict msg", ["D14.py"], "fork failed")
        assert doc["decision"] == "escalate"
        assert doc["conflict"]["message"] == "conflict msg"
        assert doc["conflict"]["files"] == ["D14.py"]
        assert doc["summary"] == "fork failed"
        assert "resolution_id" in doc
        assert "timestamp" in doc


class TestSetAgentRef:
    def test_sets_ref(self):
        mock_agent = MagicMock()
        mock_config = {"configurable": {"thread_id": "test"}}
        set_agent_ref(mock_agent, mock_config)
        assert _agent_ref["agent"] is mock_agent
        assert _agent_ref["config"] is mock_config

    def test_creates_tool(self):
        tool = make_resolve_conflict_tool()
        assert tool.name == "resolve_conflict"


class TestResolveConflictTool:
    def test_no_agent_ref_escalates(self):
        """When agent ref is not set, tool escalates."""
        import agents_janus.tools.resolve_conflict as mod
        old_agent = mod._agent_ref.get("agent")
        old_config = mod._agent_ref.get("config")
        try:
            mod._agent_ref["agent"] = None
            mod._agent_ref["config"] = None
            tool = make_resolve_conflict_tool()
            result = tool.invoke({"conflict_message": "test conflict", "files": ["D14.py"]})
            parsed = json.loads(result)
            assert parsed["decision"] == "escalate"
            assert "not available" in parsed["summary"]
        finally:
            mod._agent_ref["agent"] = old_agent
            mod._agent_ref["config"] = old_config

    def test_successful_fork_resolution(self):
        """When agent is available, tool forks and resolves."""
        import agents_janus.tools.resolve_conflict as mod

        mock_agent = MagicMock()
        mock_config = {"configurable": {"thread_id": "original"}}

        # Mock get_state
        mock_snapshot = MagicMock()
        mock_snapshot.values = {"messages": []}
        mock_agent.get_state.return_value = mock_snapshot

        # Mock invoke result (fork returns resolution JSON)
        resolution_doc = {
            "resolution_id": "test-123",
            "timestamp": "2026-01-01T00:00:00Z",
            "conflict": {"from_agent": "a_scoring", "message": "test", "files": ["D14.py"]},
            "decision": "adapt",
            "summary": "Resolved by adapting",
        }
        mock_agent.invoke.return_value = {
            "messages": [MagicMock(content=json.dumps(resolution_doc))]
        }

        old_agent = mod._agent_ref.get("agent")
        old_config = mod._agent_ref.get("config")
        try:
            mod._agent_ref["agent"] = mock_agent
            mod._agent_ref["config"] = mock_config
            tool = make_resolve_conflict_tool()
            result = tool.invoke({"conflict_message": "editing D14", "files": ["D14.py"]})
            parsed = json.loads(result)
            assert parsed["decision"] == "adapt"
            assert parsed["summary"] == "Resolved by adapting"
            # Verify fork was created
            mock_agent.update_state.assert_called()
            mock_agent.invoke.assert_called()
        finally:
            mod._agent_ref["agent"] = old_agent
            mod._agent_ref["config"] = old_config

    def test_json_parse_failure_wraps(self):
        """When fork returns non-JSON, tool wraps it."""
        import agents_janus.tools.resolve_conflict as mod

        mock_agent = MagicMock()
        mock_config = {"configurable": {"thread_id": "original"}}
        mock_snapshot = MagicMock()
        mock_snapshot.values = {"messages": []}
        mock_agent.get_state.return_value = mock_snapshot
        mock_agent.invoke.return_value = {
            "messages": [MagicMock(content="I decided to adapt to the peer's changes.")]
        }

        old_agent = mod._agent_ref.get("agent")
        old_config = mod._agent_ref.get("config")
        try:
            mod._agent_ref["agent"] = mock_agent
            mod._agent_ref["config"] = mock_config
            tool = make_resolve_conflict_tool()
            result = tool.invoke({"conflict_message": "conflict", "files": ["foo.py"]})
            parsed = json.loads(result)
            assert parsed["decision"] == "unclear"
            assert "I decided to adapt" in parsed["summary"]
        finally:
            mod._agent_ref["agent"] = old_agent
            mod._agent_ref["config"] = old_config

    def test_fork_failure_escalates(self):
        """When fork invoke raises, tool escalates."""
        import agents_janus.tools.resolve_conflict as mod

        mock_agent = MagicMock()
        mock_config = {"configurable": {"thread_id": "original"}}
        mock_snapshot = MagicMock()
        mock_snapshot.values = {"messages": []}
        mock_agent.get_state.return_value = mock_snapshot
        mock_agent.invoke.side_effect = RuntimeError("LLM timeout")

        old_agent = mod._agent_ref.get("agent")
        old_config = mod._agent_ref.get("config")
        try:
            mod._agent_ref["agent"] = mock_agent
            mod._agent_ref["config"] = mock_config
            tool = make_resolve_conflict_tool()
            result = tool.invoke({"conflict_message": "conflict", "files": ["foo.py"]})
            parsed = json.loads(result)
            assert parsed["decision"] == "escalate"
            assert "timeout" in parsed["summary"].lower() or "failed" in parsed["summary"].lower()
        finally:
            mod._agent_ref["agent"] = old_agent
            mod._agent_ref["config"] = old_config
