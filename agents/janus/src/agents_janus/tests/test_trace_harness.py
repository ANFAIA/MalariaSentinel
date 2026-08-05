"""Sibling coordination trial — the test IS the trial.

This file contains two layers:
1. LIVE trial: runs janus with a real LLM + langfuse, captures trace, evaluates with LLM-as-Judge.
2. PROMOTED trial: deterministic trace (mock) for fast CI without LLM.

The live trial is the canonical validation. The promoted trial is the
fast fallback after 3 consecutive live passes (plan §11).
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
    "TRIAL: run a full e2e test of the sibling coordination system. "
    "Use abm-worker as primary, spawn scoring-worker and ingest-worker as siblings. "
    "Have them edit overlapping files in the shared worktree. Verify the watcher "
    "fires, peer_message is sent, fork_brief is invoked, merge_result is returned. "
    "End when scoring-worker has consumed ingest-worker's output."
)


@pytest.mark.live
@pytest.mark.skipif(not _has_langfuse(), reason="langfuse not configured")
def test_trial_live_janus_with_judge():
    """THE test: run janus live → capture langfuse trace → LLM-as-Judge evaluates.
    
    This is not a mock. This runs a real LLM, generates a real langfuse trace,
    and uses a separate LLM call to judge whether the 10 sibling-coordination
    checks passed.
    
    Marks: live (skip with -m "not live")
    """
    from agents_janus.improvement import run_improvement
    from agents_janus.trace_analyzer.judge import judge_trace

    langfuse = _build_langfuse()
    trial_id = f"trial-{int(time.time())}"

    # 1. Run janus with the trial goal
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

    # 2. Flush langfuse and fetch the trace
    trace_data = None
    if langfuse:
        langfuse.flush()
        try:
            # Find the trace by session ID
            traces = langfuse.get_traces(limit=5)
            for t in traces:
                meta = getattr(t, "metadata") or {}
                if meta.get("session_id") == langfuse.flush.__self__.session_dir.name if hasattr(langfuse.flush, '__self__') else True:
                    trace_data = _langfuse_trace_to_dict(t)
                    break
            # Fallback: use the most recent trace
            if trace_data is None and traces:
                trace_data = _langfuse_trace_to_dict(traces[0])
        except Exception as e:
            print(f"[trial] Warning: could not fetch langfuse trace: {e}", file=sys.stderr)

    # 3. Construct trace from result if no langfuse trace
    if trace_data is None:
        trace_data = {
            "metadata": {"trial_id": trial_id, "elapsed_s": round(elapsed, 1)},
            "tool_calls": [],
            "spans": [{"name": "trial_result", "output": str(result)[:2000]}],
            "generations": [],
        }

    # 4. LLM-as-Judge evaluates the trace
    verdict = judge_trace(
        trace_data,
        provider="openrouter",
        model="xiaomi/mimo-v2.5",
    )

    # 5. Save fixture for promotion
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    fixture_path = fixtures_dir / f"{trial_id}.json"
    fixture_path.write_text(json.dumps({
        "verdict": verdict,
        "trial_id": trial_id,
        "elapsed_s": round(elapsed, 1),
        "result_preview": str(result)[:500],
    }, indent=2))

    # 6. Assert
    assert verdict["verdict"] == "pass", (
        f"Trial FAILED (score={verdict['score']}):\n"
        + "\n".join(f"  ✗ {f['name']}: {f['evidence']}" for f in verdict.get("failures", []))
    )
    assert verdict["score"] >= 0.8, f"Score {verdict['score']} < 0.8 threshold"


# ── PROMOTED trial (deterministic, no LLM) ──────────────────────────

MOCK_TRACE = {
    "metadata": {"session_id": "trial-promoted", "llm_calls": 8, "tool_calls": 15},
    "tool_calls": [
        {"name": "gitagent_start", "args": {"feature": "trial-sibling"}, "output": '{"status": "ok"}'},
        {"name": "gitagent_spawn", "args": {"id": "abm-primary", "role": "primary"}, "output": '{"worktree": "/path/to/wt"}'},
        {"name": "claim_file", "args": {"filepath": "/src/abm/engine.cpp"}, "output": '{"status": "claimed"}'},
        {"name": "gitagent_spawn", "args": {"id": "scoring-sibling", "role": "sibling"}, "output": '{"worktree": "/path/to/wt"}'},
        {"name": "claim_file", "args": {"filepath": "/src/scoring/composite.py"}, "output": '{"status": "claimed"}'},
        {"name": "query_claims", "args": {"filepath": "/src/abm/engine.cpp"}, "output": '{"claims": [{"sibling_id": "abm"}, {"sibling_id": "scoring"}], "count": 2}'},
        {"name": "peer_message_send", "args": {"from_sibling": "scoring", "to_sibling": "abm"}, "output": '{"status": "sent"}'},
        {"name": "fork_brief", "args": {"parent_sibling_id": "abm"}, "output": '{"fork_id": "f1"}'},
        {"name": "merge_result", "args": {"fork_id": "f1"}, "output": '{"merged_summary": "adapted", "token_estimate": 12}'},
        {"name": "release_claim", "args": {"claim_id": "c1"}, "output": '{"status": "released"}'},
    ],
    "spans": [
        {"name": "fork_negotiation", "output": "SCAN_1: scoring wants engine.cpp\nSCAN_2: my goal oviposition\nSCAN_3: scoring changed composite.py\nSCAN_4: A) Adapt\nSCAN_5: no API changes\nSCAN_6: breaking oviposition\nSCAN_7: split scope\nCHECK: preserved\nMISSED: none"},
    ],
    "generations": [
        {"model": "xiaomi/mimo-v2.5", "input": "TRIAL", "output": "spawn siblings"},
    ],
}


class TestPromotedTrial:
    """Deterministic trial — same 10 checks, mock trace, no LLM."""

    def test_primary_spawned_worktree(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="primary_spawned_worktree", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_sibling_join_shared_worktree(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="sibling_join_shared_worktree", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_claim_file_registered(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="claim_file_registered", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_watcher_fired(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="watcher_fired_on_file_overlap", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_peer_message_sent(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="peer_message_sent", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_fork_brief_invoked(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="fork_brief_invoked", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_merge_result_returned(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="merge_result_returned", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_frame_stack_push_pop(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="frame_stack_push_pop", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_no_parent_arbitration(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="no_parent_arbitration", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_scan_markers_emitted(self):
        from agents_janus.trace_analyzer.analyzer import _evaluate_check
        from agents_janus.trace_analyzer.checks import Check
        c = Check(name="scan_markers_emitted", description="")
        assert _evaluate_check(c, MOCK_TRACE).passed

    def test_full_verdict_pass(self):
        from agents_janus.trace_analyzer.analyzer import analyze_trace
        v = analyze_trace(MOCK_TRACE)
        assert v["verdict"] == "pass"
        assert v["score"] == 1.0
        assert len(v["failures"]) == 0


class TestJudgeParsing:
    """Judge response parser — no LLM needed."""

    def test_parse_valid_json(self):
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = json.dumps({"verdict": "pass", "score": 0.9, "checks": [], "failures": [], "summary": "ok"})
        assert _parse_judge_response(raw)["verdict"] == "pass"

    def test_parse_json_in_code_fence(self):
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = '```json\n{"verdict": "pass", "score": 1.0, "checks": [], "failures": [], "summary": "ok"}\n```'
        assert _parse_judge_response(raw)["verdict"] == "pass"

    def test_parse_invalid_json(self):
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        r = _parse_judge_response("not json")
        assert r["verdict"] == "fail"
        assert r["score"] == 0.0

    def test_parse_json_with_extra_text(self):
        from agents_janus.trace_analyzer.judge import _parse_judge_response
        raw = 'result: {"verdict": "pass", "score": 0.8, "checks": [], "failures": [], "summary": "ok"} done'
        assert _parse_judge_response(raw)["verdict"] == "pass"

    def test_trace_summary_extraction(self):
        from agents_janus.trace_analyzer.judge import _build_trace_summary
        s = _build_trace_summary(MOCK_TRACE)
        assert "gitagent_spawn" in s
        assert "claim_file" in s
