"""Promoted trial test — deterministic sibling coordination scenario with mock LLM.

After 3 consecutive live trial passes, this test replaces the live trial
with a mock LLM that returns deterministic responses. It asserts the same
10 checks without needing Langfuse or a real LLM.

This is the "promoted trial" from M16 plan §11.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Deterministic trace fixture ───────────────────────────────────────

MOCK_TRACE = {
    "metadata": {
        "session_id": "trial-promoted",
        "llm_calls": 8,
        "tool_calls": 15,
        "total_prompt_tokens": 2500,
        "total_completion_tokens": 1200,
    },
    "tool_calls": [
        {"name": "gitagent_start", "args": {"feature": "trial-sibling"}, "output": '{"status": "ok"}'},
        {"name": "gitagent_spawn", "args": {"id": "abm-primary", "role": "primary"}, "output": '{"worktree": "/path/to/wt"}'},
        {"name": "claim_file", "args": {"filepath": "/src/abm/engine.cpp", "description": "editing oviposition"}, "output": '{"status": "claimed"}'},
        {"name": "gitagent_spawn", "args": {"id": "scoring-sibling", "role": "sibling"}, "output": '{"worktree": "/path/to/wt"}'},
        {"name": "claim_file", "args": {"filepath": "/src/scoring/composite.py", "description": "updating thresholds"}, "output": '{"status": "claimed"}'},
        {"name": "query_claims", "args": {"filepath": "/src/abm/engine.cpp"}, "output": '{"claims": [{"sibling_id": "abm"}, {"sibling_id": "scoring"}], "count": 2}'},
        {"name": "peer_message_send", "args": {"from_sibling": "scoring", "to_sibling": "abm", "re": "file_overlap", "severity": "warn"}, "output": '{"status": "sent"}'},
        {"name": "fork_brief", "args": {"parent_sibling_id": "abm", "task_brief": "adapt to scoring overlap"}, "output": '{"fork_id": "f1", "task_brief": "adapt"}'},
        {"name": "merge_result", "args": {"fork_id": "f1", "result": "adapted successfully"}, "output": '{"merged_summary": "Adapted to scoring overlap on engine.cpp", "token_estimate": 12}'},
        {"name": "release_claim", "args": {"claim_id": "c1"}, "output": '{"status": "released"}'},
    ],
    "spans": [
        {"name": "tool:gitagent_spawn", "output": "spawned abm-primary"},
        {"name": "tool:claim_file", "output": "claimed /src/abm/engine.cpp"},
        {"name": "tool:peer_message_send", "output": "sent to abm"},
        {"name": "fork_negotiation", "output": "SCAN_1: scoring wants to edit engine.cpp\nSCAN_2: my goal is to implement oviposition\nSCAN_3: scoring changed composite.py\nSCAN_4: A) Adapt\nSCAN_5: no API changes\nSCAN_6: breaking oviposition logic\nSCAN_7: split scope: abm takes engine.cpp, scoring takes composite.py\nCHECK: oviposition logic preserved\nMISSED: composite score regression"},
    ],
    "generations": [
        {"model": "xiaomi/mimo-v2.5", "input": "TRIAL: spawn siblings", "output": "I will spawn abm and scoring as siblings"},
    ],
}


class TestPromotedTrial:
    """Deterministic tests using a mock trace — no LLM required."""

    def test_primary_spawned_worktree(self):
        """Check: primary subagent spawned a worktree."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="primary_spawned_worktree", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed, f"Expected passed, got evidence: {result.evidence}"

    def test_sibling_join_shared_worktree(self):
        """Check: sibling joined the shared worktree."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="sibling_join_shared_worktree", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_claim_file_registered(self):
        """Check: claim_file registered in SQLite."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="claim_file_registered", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_watcher_fired(self):
        """Check: watcher detected file overlap (via query_claims)."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="watcher_fired_on_file_overlap", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_peer_message_sent(self):
        """Check: peer message sent between siblings."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="peer_message_sent", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_fork_brief_invoked(self):
        """Check: fork_brief created a sub-context."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="fork_brief_invoked", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_merge_result_returned(self):
        """Check: merge_result returned ≤500 tokens."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="merge_result_returned", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_frame_stack_push_pop(self):
        """Check: frame stack push/pop recorded."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="frame_stack_push_pop", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_no_parent_arbitration(self):
        """Check: no orchestrator tool_call between siblings."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="no_parent_arbitration", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_scan_markers_emitted(self):
        """Check: SCAN markers present in fork output."""
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        check = Check(name="scan_markers_emitted", description="test")
        result = _evaluate_check(check, MOCK_TRACE)
        assert result.passed

    def test_full_analysis_verdict(self):
        """Full analysis produces pass verdict (all 10 checks)."""
        from agents_janus.trace_analyzer.analyzer import analyze_trace
        verdict = analyze_trace(MOCK_TRACE)
        assert verdict["verdict"] == "pass"
        assert verdict["score"] == 1.0
        assert len(verdict["checks"]) == 10
        assert len(verdict["failures"]) == 0


class TestJudgeParsing:
    """Test the judge response parser (no LLM needed)."""

    def test_parse_valid_json(self):
        """Valid JSON verdict is parsed correctly."""
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = json.dumps({
            "verdict": "pass",
            "score": 0.9,
            "checks": [{"name": "test", "passed": True, "evidence": "found"}],
            "failures": [],
            "summary": "All checks passed",
        })
        result = _parse_judge_response(raw)
        assert result["verdict"] == "pass"
        assert result["score"] == 0.9

    def test_parse_json_in_code_fence(self):
        """JSON inside markdown code fences is parsed."""
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = '```json\n{"verdict": "pass", "score": 1.0, "checks": [], "failures": [], "summary": "ok"}\n```'
        result = _parse_judge_response(raw)
        assert result["verdict"] == "pass"

    def test_parse_invalid_json_returns_fail(self):
        """Invalid JSON returns a fail verdict with parse_error."""
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        result = _parse_judge_response("this is not json at all")
        assert result["verdict"] == "fail"
        assert result["score"] == 0.0
        assert any(f["name"] == "parse_error" for f in result["failures"])

    def test_parse_json_with_extra_text(self):
        """JSON embedded in text is extracted."""
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = 'Here is the verdict: {"verdict": "pass", "score": 0.8, "checks": [], "failures": [], "summary": "ok"} hope this helps'
        result = _parse_judge_response(raw)
        assert result["verdict"] == "pass"

    def test_trace_summary_extraction(self):
        """_build_trace_summary extracts key info from trace."""
        from agents_janus.trace_analyzer.judge import _build_trace_summary
        summary = _build_trace_summary(MOCK_TRACE)
        assert "gitagent_spawn" in summary
        assert "claim_file" in summary
        assert "peer_message_send" in summary
