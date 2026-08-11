"""Trace analyzer — evaluates traces against 10 gawt MCP coordination checks.

Two evaluation paths:
1. Local (langchain): judge_trace(trace_data, provider, model) — LLM evaluates evidence.
2. Langfuse MCP: create_langfuse_evaluator() + create_langfuse_verdict_score() — agent-side.

Trial harness: run_trial(goal) — runs janus, captures trace, invokes judge.
"""
from agents_janus.trace_analyzer.checks import CHECKS, Check, get_check
from agents_janus.trace_analyzer.judge import (
    judge_trace,
    create_langfuse_evaluator,
    create_langfuse_verdict_score,
    build_checks_table,
    build_trace_summary,
    parse_judge_response,
)
from agents_janus.trace_analyzer.harness import run_trial, run_trial_from_trace

__all__ = [
    "judge_trace",
    "create_langfuse_evaluator",
    "create_langfuse_verdict_score",
    "build_checks_table",
    "build_trace_summary",
    "parse_judge_response",
    "run_trial",
    "run_trial_from_trace",
    "CHECKS",
    "Check",
    "get_check",
]
