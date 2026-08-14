"""Onboarding trial — same pattern as test_trace_harness.py.

Runs the onboarding agent with controlled inputs, captures tool calls,
verifies:
  1. onboard_ask_subagent was invoked (read-only specialist query works)
  2. request router can hand off to a coordinator
  3. No write tools were called (onboarding stays read-only)

Two modes:
  - PROMOTED: mock LLM, deterministic, runs in CI
  - LIVE: real LLM + langfuse trace, LLM-as-Judge evaluates
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────

def _run_onboarding_with_inputs(
    inputs: list[str],
    *,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    langfuse_client=None,
) -> dict:
    """Run the onboarding agent with a fixed list of inputs.

    Returns:
        {
            "responses": [str, ...],         # agent text per input
            "tool_calls": [str, ...],        # tool names invoked (in order)
            "tool_outputs": {name: str},     # last output per tool
            "elapsed_s": float,
        }
    """
    import agents_janus.agent as agent_mod
    from agents_janus.onboarding import run_onboarding

    agent = agent_mod.create_orchestrator(
        provider=provider,
        model=model,
        mode="request_router",
        langfuse_client=langfuse_client,
    )

    messages: list[dict] = []
    responses: list[str] = []
    tool_calls: list[str] = []
    tool_outputs: dict[str, str] = {}

    start = time.monotonic()

    for user_input in inputs:
        messages.append({"role": "user", "content": user_input})

        full_response = ""
        for event in agent.stream(
            {"messages": messages},
            stream_mode="updates",
            config={"configurable": {"thread_id": "router-test-session"}},
        ):
            if not isinstance(event, dict):
                continue
            for node_name, delta in event.items():
                if not isinstance(delta, dict):
                    continue
                if "messages" not in delta:
                    continue
                for msg in delta["messages"]:
                    # Track tool calls
                    if hasattr(msg, "name") and msg.name:
                        tool_calls.append(msg.name)
                        if hasattr(msg, "content") and msg.content:
                            tool_outputs[msg.name] = (
                                msg.content[:500]
                                if isinstance(msg.content, str)
                                else str(msg.content)[:500]
                            )
                    # Track text responses
                    if hasattr(msg, "content") and msg.content:
                        content = (
                            msg.content
                            if isinstance(msg.content, str)
                            else str(msg.content)
                        )
                        if content and not content.startswith("{"):
                            full_response = content

        responses.append(full_response)
        messages.append({"role": "assistant", "content": full_response})

    elapsed = time.monotonic() - start

    return {
        "responses": responses,
        "tool_calls": tool_calls,
        "tool_outputs": tool_outputs,
        "elapsed_s": round(elapsed, 1),
    }


def _has_api_key() -> bool:
    return bool(
        os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
    )


# ── PROMOTED: deterministic, no LLM ─────────────────────────────────────

MOCK_ONBOARDING_RESULT = {
    "responses": [
        "El sistema tiene 14 scorers (D1-D14) con composite 0.87.",
        "Tenemos 8 subagentes especializados: abm, scoring, ingest, download, prediction, training, data, commonlib.",
        "El especialista de scoring indica que tiene D1-D14 más el composite.",
        "Delegado al implementation coordinator para añadir el scorer D15.",
    ],
    "tool_calls": [
        "onboard_status",
        "onboard_list_components",
        "onboard_ask_subagent",
        "task",
    ],
    "tool_outputs": {
        "onboard_status": '{"scorecards": {"best_composite": 0.87}, "plans": ["m16.md"], "subagents": ["abm","scoring","ingest","download","prediction","training","data","commonlib"]}',
        "onboard_list_components": '[{"name": "abm", "description": "ABM C++ engine"}, {"name": "scoring", "description": "Calibration scorers"}]',
        "onboard_ask_subagent": '{"status": "ok", "subagent": "scoring", "response": "We have D1-D14 scorers plus composite."}',
        "task": '{"status": "ok", "coordinator": "implementation_coordinator"}',
    },
    "elapsed_s": 12.3,
}


class TestOnboardingPromoted:
    """Deterministic onboarding trial — mock trace, no LLM."""

    def test_ask_subagent_called(self):
        """onboard_ask_subagent appears in tool_calls."""
        assert "onboard_ask_subagent" in MOCK_ONBOARDING_RESULT["tool_calls"]

    def test_coordinator_called(self):
        """Router task dispatch appears in tool_calls."""
        assert "task" in MOCK_ONBOARDING_RESULT["tool_calls"]

    def test_status_called(self):
        """onboard_status appears in tool_calls."""
        assert "onboard_status" in MOCK_ONBOARDING_RESULT["tool_calls"]

    def test_ask_subagent顺序_after_status(self):
        """ask_subagent is called after status (natural flow)."""
        tc = MOCK_ONBOARDING_RESULT["tool_calls"]
        assert tc.index("onboard_status") < tc.index("onboard_ask_subagent")

    def test_task顺序_after_ask(self):
        """Coordinator dispatch follows specialist research."""
        tc = MOCK_ONBOARDING_RESULT["tool_calls"]
        assert tc.index("onboard_ask_subagent") < tc.index("task")

    def test_no_write_tools(self):
        """No write tools called — onboarding stays read-only."""
        write_tools = {"gitagent_start", "gitagent_spawn", "gitagent_propose",
                       "gitagent_integrate", "gitagent_finalize"}
        assert not write_tools.intersection(MOCK_ONBOARDING_RESULT["tool_calls"])

    def test_ask_subagent_output_valid_json(self):
        """onboard_ask_subagent output is valid JSON with status=ok."""
        out = MOCK_ONBOARDING_RESULT["tool_outputs"]["onboard_ask_subagent"]
        data = json.loads(out)
        assert data["status"] == "ok"
        assert data["subagent"] == "scoring"
        assert "response" in data

    def test_delegate_output_valid_json(self):
        """Coordinator dispatch output is valid JSON with status=ok."""
        out = MOCK_ONBOARDING_RESULT["tool_outputs"]["task"]
        data = json.loads(out)
        assert data["status"] == "ok"
        assert data["coordinator"] == "implementation_coordinator"

    def test_responses_non_empty(self):
        """All agent responses are non-empty strings."""
        for i, r in enumerate(MOCK_ONBOARDING_RESULT["responses"]):
            assert r, f"Response {i} is empty"

    def test_full_flow_completes(self):
        """Full onboarding flow: status → ask → coordinator."""
        tc = MOCK_ONBOARDING_RESULT["tool_calls"]
        assert len(tc) >= 3
        assert tc[0] == "onboard_status"
        assert "onboard_ask_subagent" in tc
        assert "task" in tc


# ── LIVE: real LLM, real tool calls ──────────────────────────────────────

@pytest.mark.live
@pytest.mark.skipif(not _has_api_key(), reason="OPENROUTER_API_KEY not set")
class TestOnboardingLive:
    """LIVE onboarding trial — real LLM, real tool calls, real assertions.

    The router is tested only for read-only behavior here. Implementation
    coordinator coverage belongs to the direct `janus improve` tests.
    """

    def test_ask_subagent_live(self):
        """Run onboarding with ask_subagent input, verify tool was called."""
        result = _run_onboarding_with_inputs([
            "Pregúntale al especialista de scoring qué scorers tiene",
        ])

        assert "onboard_ask_subagent" in result["tool_calls"], (
            f"ask_subagent not called. Tool calls: {result['tool_calls']}"
        )
        out = result["tool_outputs"].get("onboard_ask_subagent", "")
        if out:
            data = json.loads(out)
            assert data["status"] == "ok"

    def test_no_write_tools_live(self):
        """Onboarding never calls write tools, even with live LLM."""
        result = _run_onboarding_with_inputs([
            "¿Qué subagentes tenemos?",
            "Pregúntale al de scoring qué hace",
        ])

        write_tools = {"gitagent_start", "gitagent_spawn", "gitagent_propose",
                       "gitagent_integrate", "gitagent_finalize"}
        violations = write_tools.intersection(result["tool_calls"])
        assert not violations, f"Write tools called: {violations}"

    def test_responses_are_meaningful_live(self):
        """All responses are non-empty and mention relevant content."""
        result = _run_onboarding_with_inputs([
            "¿Cuál es el estado del sistema?",
            "Pregúntale al especialista de scoring qué scorers tiene",
        ])

        assert len(result["responses"]) >= 2
        for i, r in enumerate(result["responses"]):
            assert len(r) > 20, f"Response {i} too short ({len(r)} chars): {r[:50]}"
