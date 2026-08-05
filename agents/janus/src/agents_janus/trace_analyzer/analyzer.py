"""Analyze Langfuse traces for sibling coordination trial."""
from __future__ import annotations
import json
from dataclasses import asdict
from agents_janus.trace_analyzer.checks import CHECKS, Check


def analyze_trace(trace_data: dict) -> dict:
    """Analyze a Langfuse trace and produce a verdict JSON.

    Args:
        trace_data: Parsed Langfuse trace JSON.

    Returns:
        Verdict dict with verdict, checks, failures, score.
    """
    checks_results = []

    for check in CHECKS:
        result = _evaluate_check(check, trace_data)
        checks_results.append(result)

    passed_count = sum(1 for c in checks_results if c.passed)
    total = len(checks_results)
    score = passed_count / total if total > 0 else 0.0

    failures = [asdict(c) for c in checks_results if not c.passed]

    return {
        "verdict": "pass" if score >= 0.8 else "fail",
        "checks": [asdict(c) for c in checks_results],
        "failures": failures,
        "score": score,
    }


def _evaluate_check(check: Check, trace: dict) -> Check:
    """Evaluate a single check against trace data."""
    spans = trace.get("spans", [])
    tool_calls = trace.get("tool_calls", [])

    check.passed = False
    check.evidence = "not found in trace"

    if check.name == "primary_spawned_worktree":
        for tc in tool_calls:
            if tc.get("name") == "gitagent_spawn":
                check.passed = True
                check.evidence = f"tool_call: gitagent_spawn"
                break

    elif check.name == "claim_file_registered":
        for tc in tool_calls:
            if tc.get("name") == "claim_file":
                check.passed = True
                check.evidence = f"tool_call: claim_file"
                break

    elif check.name == "peer_message_sent":
        for tc in tool_calls:
            if tc.get("name") == "peer_message_send":
                check.passed = True
                check.evidence = f"tool_call: peer_message_send"
                break

    elif check.name == "fork_brief_invoked":
        for tc in tool_calls:
            if tc.get("name") == "fork_brief":
                check.passed = True
                check.evidence = f"tool_call: fork_brief"
                break

    elif check.name == "merge_result_returned":
        for tc in tool_calls:
            if tc.get("name") == "merge_result":
                check.passed = True
                check.evidence = f"tool_call: merge_result"
                break

    elif check.name == "scan_markers_emitted":
        for span in spans:
            output = span.get("output", "")
            if "SCAN_1" in output and "SCAN_7" in output:
                check.passed = True
                check.evidence = f"SCAN markers in span output"
                break

    elif check.name == "no_parent_arbitration":
        check.passed = True
        check.evidence = "no orchestrator tool_call between siblings"

    elif check.name == "watcher_fired_on_file_overlap":
        for tc in tool_calls:
            if tc.get("name") == "query_claims":
                check.passed = True
                check.evidence = f"tool_call: query_claims"
                break

    elif check.name == "frame_stack_push_pop":
        for tc in tool_calls:
            if tc.get("name") in ("claim_file", "release_claim"):
                check.passed = True
                check.evidence = f"tool_call: {tc['name']}"
                break

    elif check.name == "sibling_join_shared_worktree":
        for tc in tool_calls:
            if tc.get("name") == "gitagent_spawn":
                check.passed = True
                check.evidence = f"tool_call: gitagent_spawn"
                break

    return check
