"""Trace analyzer — reads Langfuse traces and produces verdict JSON.

Two modes:
1. Static analysis: analyze_trace(trace_data) — rule-based, no LLM.
2. LLM-as-Judge: judge_trace(trace_data, provider, model) — LLM evaluates evidence.
3. Trial harness: run_trial(goal) — runs janus, captures trace, invokes judge.
"""
from agents_janus.trace_analyzer.analyzer import analyze_trace
from agents_janus.trace_analyzer.checks import CHECKS, Check, get_check
from agents_janus.trace_analyzer.judge import judge_trace
from agents_janus.trace_analyzer.harness import run_trial, run_trial_from_trace

__all__ = [
    "analyze_trace",
    "judge_trace",
    "run_trial",
    "run_trial_from_trace",
    "CHECKS",
    "Check",
    "get_check",
]
