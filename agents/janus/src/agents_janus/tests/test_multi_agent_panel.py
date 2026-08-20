"""Tests for MultiAgentPanel -- multi-agent status display."""
from __future__ import annotations

import time

from agents_janus.live_panel import MultiAgentPanel


class TestMultiAgentPanel:
    def test_initial_state_empty(self):
        panel = MultiAgentPanel()
        assert len(panel._agents) == 0

    def test_update_agent(self):
        panel = MultiAgentPanel()
        panel.update_agent("a_1", "abm", intent="fix engine", last_edit="engine.cpp", edit_count=2)
        assert "a_1" in panel._agents
        assert panel._agents["a_1"]["role"] == "abm"
        assert panel._agents["a_1"]["intent"] == "fix engine"
        assert panel._agents["a_1"]["edit_count"] == 2

    def test_remove_agent(self):
        panel = MultiAgentPanel()
        panel.update_agent("a_1", "abm")
        panel.remove_agent("a_1")
        assert "a_1" not in panel._agents

    def test_remove_nonexistent_noop(self):
        panel = MultiAgentPanel()
        panel.remove_agent("nonexistent")  # should not raise

    def test_render_empty(self):
        panel = MultiAgentPanel()
        r = panel._render()
        assert r is not None

    def test_render_with_agents(self):
        panel = MultiAgentPanel()
        panel.update_agent("a_1", "abm", intent="fix engine")
        panel.update_agent("a_2", "scoring", intent="add D15")
        r = panel._render()
        assert r is not None

    def test_quiet_mode(self):
        panel = MultiAgentPanel(quiet=True)
        with panel:
            assert panel._live is None
            panel.update_agent("a_1", "abm")
            # No exception
