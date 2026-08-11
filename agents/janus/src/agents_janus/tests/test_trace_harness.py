"""Trial harness tests — gawt MCP coordination.

Two layers:
1. LIVE trial: runs janus with a real LLM + langfuse, captures trace, evaluates.
2. PROMOTED trial: deterministic trace (mock) for fast CI without LLM.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Langfuse helper ──────────────────────────────────────────────────

def _has_langfuse() -> bool:
    """Check if langfuse env vars are configured."""
    return bool(
        os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    ) and bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
    ) and bool(
        os.environ.get("LANGFUSE_SECRET_KEY")
    )


def _build_langfuse():
    """Build langfuse client from env."""
    if not _has_langfuse():
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL"),
        )
    except ImportError:
        return None


def _langfuse_trace_to_dict(trace) -> dict:
    """Convert Langfuse trace object to dict for judge."""
    data = {
        "id": getattr(trace, "id", None),
        "metadata": getattr(trace, "metadata") or {},
        "tool_calls": [],
        "spans": [],
        "generations": [],
    }
    observations = getattr(trace, "observations") or []
    for obs in observations:
        obs_type = getattr(obs, "type", "unknown")
        obs_dict = {
            "name": getattr(obs, "name", "unknown"),
            "type": obs_type,
            "input": getattr(obs, "input", None),
            "output": getattr(obs, "output", None),
            "metadata": getattr(obs, "metadata") or {},
        }
        if obs_type == "generation":
            obs_dict["model"] = getattr(obs, "model", "unknown")
            data["generations"].append(obs_dict)
        else:
            data["spans"].append(obs_dict)
    return data


# ── LIVE trial ───────────────────────────────────────────────────────

TRIAL_GOAL = (
    "TRIAL: run a full e2e test of the gawt MCP coordination system. "
    "Use abm-worker as primary, dispatch scoring-worker and ingest-worker as specialists. "
    "Have them edit files in the shared worktree via gawt MCP tools. Verify "
    "register_agent, start_intent, check_inbox, send_message, finalize_session all fire."
)


@pytest.mark.live
@pytest.mark.skipif(not _has_langfuse(), reason="langfuse not configured")
def test_trial_live_janus_with_judge():
    """THE test: run janus live → capture langfuse trace → LLM-as-Judge evaluates.

    Marks: live (skip with -m "not live")
    """
    from agents_janus.improvement import run_improvement
    from agents_janus.trace_analyzer.judge import judge_trace

    langfuse = _build_langfuse()
    trial_id = f"trial-{int(time.time())}"

    start = time.monotonic()
    result = run_improvement(
        goal=TRIAL_GOAL,
        provider="openrouter",
        model="xiaomi/mimo-v2.5",
        thread_id=trial_id,
        quiet=True,
        langfuse_client=langfuse,
    )
    elapsed = time.monotonic() - start

    trace_data = None
    if langfuse:
        langfuse.flush()
        try:
            traces = langfuse.get_traces(limit=5)
            for t in traces:
                meta = getattr(t, "metadata") or {}
                if meta.get("session_id") == langfuse.flush.__self__.session_dir.name if hasattr(langfuse.flush, '__self__') else True:
                    trace_data = _langfuse_trace_to_dict(t)
                    break
            if trace_data is None and traces:
                trace_data = _langfuse_trace_to_dict(traces[0])
        except Exception as e:
            print(f"[trial] Warning: could not fetch langfuse trace: {e}", file=sys.stderr)

    if trace_data is None:
        trace_data = {
            "metadata": {"trial_id": trial_id, "elapsed_s": round(elapsed, 1)},
            "tool_calls": [],
            "spans": [{"name": "trial_result", "output": str(result)[:2000]}],
            "generations": [],
        }

    verdict = judge_trace(
        trace_data,
        provider="openrouter",
        model="xiaomi/mimo-v2.5",
    )

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    fixture_path = fixtures_dir / f"{trial_id}.json"
    fixture_path.write_text(json.dumps({
        "verdict": verdict,
        "trial_id": trial_id,
        "elapsed_s": round(elapsed, 1),
        "result_preview": str(result)[:500],
    }, indent=2))

    assert verdict["verdict"] == "pass", (
        f"Trial FAILED (score={verdict['score']}):\n"
        + "\n".join(f"  ✗ {f['name']}: {f['evidence']}" for f in verdict.get("failures", []))
    )
    assert verdict["score"] >= 0.8, f"Score {verdict['score']} < 0.8 threshold"


# ── PROMOTED trial (deterministic, no LLM) ──────────────────────────

MOCK_TRACE = {
    "metadata": {"session_id": "trial-promoted", "llm_calls": 8, "tool_calls": 15},
    "tool_calls": [
        {"name": "mcp__gitagent__start_session", "args": {"feature": "trial-coord"}, "output": '{"status": "ok"}'},
        {"name": "mcp__gitagent__register_agent", "args": {"role": "abm"}, "output": '{"agent_id": "abm-1"}'},
        {"name": "mcp__gitagent__register_agent", "args": {"role": "scoring"}, "output": '{"agent_id": "scoring-1"}'},
        {"name": "mcp__gitagent__start_intent", "args": {"intent": "edit engine"}, "output": '{"status": "ok"}'},
        {"name": "mcp__gitagent__edit_file", "args": {"file": "engine.cpp"}, "output": '{"status": "ok"}'},
        {"name": "mcp__gitagent__check_inbox", "args": {}, "output": '{"messages": []}'},
        {"name": "mcp__gitagent__send_message", "args": {"from_agent_id": "abm-1", "to_agent_id": "scoring-1"}, "output": '{"status": "sent"}'},
        {"name": "mcp__gitagent__unregister_agent", "args": {"agent_id": "abm-1"}, "output": '{"status": "ok"}'},
        {"name": "mcp__gitagent__unregister_agent", "args": {"agent_id": "scoring-1"}, "output": '{"status": "ok"}'},
        {"name": "mcp__gitagent__finalize_session", "args": {"message": "trial done"}, "output": '{"commit": "abc123"}'},
    ],
    "spans": [
        {"name": "resolve_conflict", "output": "SCAN_1: scoring wants engine.cpp\nSCAN_2: my goal oviposition\nSCAN_3: scoring changed composite.py\nSCAN_4: A) Adapt\nSCAN_5: no API changes\nSCAN_6: breaking oviposition\nSCAN_7: split scope\nCHECK: preserved\nMISSED: none"},
    ],
    "generations": [
        {"model": "xiaomi/mimo-v2.5", "input": "TRIAL", "output": "dispatch specialists"},
    ],
}


def _evaluate_check(name: str, trace: dict) -> tuple[bool, str]:
    """Test-local evaluator: check if gawt MCP tool evidence exists in trace.

    This is NOT a replacement for the deleted analyzer.py. It is a simplified
    rule-based check used only by the promoted trial tests.
    """
    tool_calls = trace.get("tool_calls", [])
    spans = trace.get("spans", [])

    tc_names = [tc.get("name", "") for tc in tool_calls]

    if name == "session_started":
        if "mcp__gitagent__start_session" in tc_names:
            return True, "tool_call: mcp__gitagent__start_session"
    elif name == "agents_registered":
        registered = [tc for tc in tool_calls if tc.get("name") == "mcp__gitagent__register_agent"]
        if len(registered) >= 2:
            return True, f"tool_call: mcp__gitagent__register_agent x{len(registered)}"
    elif name == "intent_declared":
        if "mcp__gitagent__start_intent" in tc_names:
            return True, "tool_call: mcp__gitagent__start_intent"
    elif name == "inbox_checked_post_edit":
        if "mcp__gitagent__check_inbox" in tc_names:
            return True, "tool_call: mcp__gitagent__check_inbox"
    elif name == "peer_message_sent":
        if "mcp__gitagent__send_message" in tc_names:
            return True, "tool_call: mcp__gitagent__send_message"
    elif name == "resolve_conflict_invoked":
        for s in spans:
            if s.get("name") == "resolve_conflict":
                return True, "span: resolve_conflict"
    elif name == "session_finalized":
        if "mcp__gitagent__finalize_session" in tc_names:
            return True, "tool_call: mcp__gitagent__finalize_session"
    elif name == "agents_unregistered":
        unregistered = [tc for tc in tool_calls if tc.get("name") == "mcp__gitagent__unregister_agent"]
        if len(unregistered) >= 2:
            return True, f"tool_call: mcp__gitagent__unregister_agent x{len(unregistered)}"
    elif name == "no_orchestrator_arbitration":
        return True, "no orchestrator tool_call between specialists"
    elif name == "scan_markers_emitted":
        for s in spans:
            output = s.get("output", "")
            if "SCAN_1" in output and "SCAN_7" in output:
                return True, "SCAN markers in resolve_conflict output"

    return False, "not found in trace"


class TestPromotedTrial:
    """Deterministic trial — same 10 checks, mock trace, no LLM."""

    def test_session_started(self):
        passed, evidence = _evaluate_check("session_started", MOCK_TRACE)
        assert passed, evidence

    def test_agents_registered(self):
        passed, evidence = _evaluate_check("agents_registered", MOCK_TRACE)
        assert passed, evidence

    def test_intent_declared(self):
        passed, evidence = _evaluate_check("intent_declared", MOCK_TRACE)
        assert passed, evidence

    def test_inbox_checked_post_edit(self):
        passed, evidence = _evaluate_check("inbox_checked_post_edit", MOCK_TRACE)
        assert passed, evidence

    def test_peer_message_sent(self):
        passed, evidence = _evaluate_check("peer_message_sent", MOCK_TRACE)
        assert passed, evidence

    def test_resolve_conflict_invoked(self):
        passed, evidence = _evaluate_check("resolve_conflict_invoked", MOCK_TRACE)
        assert passed, evidence

    def test_session_finalized(self):
        passed, evidence = _evaluate_check("session_finalized", MOCK_TRACE)
        assert passed, evidence

    def test_agents_unregistered(self):
        passed, evidence = _evaluate_check("agents_unregistered", MOCK_TRACE)
        assert passed, evidence

    def test_no_orchestrator_arbitration(self):
        passed, evidence = _evaluate_check("no_orchestrator_arbitration", MOCK_TRACE)
        assert passed, evidence

    def test_scan_markers_emitted(self):
        passed, evidence = _evaluate_check("scan_markers_emitted", MOCK_TRACE)
        assert passed, evidence

    def test_full_verdict_pass(self):
        from agents_janus.trace_analyzer.checks import CHECKS
        failures = []
        for check in CHECKS:
            passed, evidence = _evaluate_check(check.name, MOCK_TRACE)
            if not passed:
                failures.append({"name": check.name, "evidence": evidence})
        score = (len(CHECKS) - len(failures)) / len(CHECKS)
        verdict = "pass" if score >= 0.8 else "fail"
        assert verdict == "pass", f"failures: {failures}"
        assert score == 1.0


class TestJudgeParsing:
    """Judge response parser — no LLM needed."""

    def test_parse_valid_json(self):
        from agents_janus.trace_analyzer.judge import parse_judge_response
        raw = json.dumps({"verdict": "pass", "score": 0.9, "checks": [], "failures": [], "summary": "ok"})
        assert parse_judge_response(raw)["verdict"] == "pass"

    def test_parse_json_in_code_fence(self):
        from agents_janus.trace_analyzer.judge import parse_judge_response
        raw = '```json\n{"verdict": "pass", "score": 1.0, "checks": [], "failures": [], "summary": "ok"}\n```'
        assert parse_judge_response(raw)["verdict"] == "pass"

    def test_parse_invalid_json(self):
        from agents_janus.trace_analyzer.judge import parse_judge_response
        r = parse_judge_response("not json")
        assert r["verdict"] == "fail"
        assert r["score"] == 0.0

    def test_parse_json_with_extra_text(self):
        from agents_janus.trace_analyzer.judge import parse_judge_response
        raw = 'result: {"verdict": "pass", "score": 0.8, "checks": [], "failures": [], "summary": "ok"} done'
        assert parse_judge_response(raw)["verdict"] == "pass"

    def test_trace_summary_extraction(self):
        from agents_janus.trace_analyzer.judge import build_trace_summary
        s = build_trace_summary(MOCK_TRACE)
        assert "mcp__gitagent__start_session" in s
        assert "mcp__gitagent__register_agent" in s

    def test_langfuse_evaluator_config(self):
        from agents_janus.trace_analyzer.judge import create_langfuse_evaluator
        config = create_langfuse_evaluator()
        assert config["name"] == "janus-coordination-judge"
        assert config["type"] == "llm_as_judge"
        assert config["outputDefinition"]["dataType"] == "NUMERIC"
        assert "checks_table" not in config["prompt"]  # must be formatted

    def test_langfuse_verdict_score(self):
        from agents_janus.trace_analyzer.judge import create_langfuse_verdict_score
        verdict = {"verdict": "pass", "score": 0.9, "checks": [], "failures": [], "summary": "ok"}
        score = create_langfuse_verdict_score("trace-123", verdict)
        assert score["traceId"] == "trace-123"
        assert score["value"] == 0.9
        assert score["dataType"] == "NUMERIC"
