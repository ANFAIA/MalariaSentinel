"""LLM-as-Judge — evaluates traces against 10 gawt MCP coordination checks.

Two evaluation paths:

1. **Local** (langchain): `judge_trace()` builds a prompt, calls an LLM directly,
   parses the JSON verdict. Used by `harness.py` for offline trial evaluation.

2. **Langfuse MCP**: `create_langfuse_evaluator()` returns the evaluator config
   to register in Langfuse via `langfuse_upsertEvaluator` MCP tool.
   `create_langfuse_verdict_score()` returns the score payload to create via
   `langfuse_createScore` MCP tool. Used by the opencode agent for online
   evaluation of production traces.

Usage:
    # Path 1: local (harness)
    from agents_janus.trace_analyzer.judge import judge_trace
    verdict = judge_trace(trace_json, provider="openrouter", model="xiaomi/mimo-v2.5")

    # Path 2: Langfuse MCP (agent)
    from agents_janus.trace_analyzer.judge import create_langfuse_evaluator, create_langfuse_verdict_score
    eval_config = create_langfuse_evaluator()  # → call langfuse_upsertEvaluator
    score_config = create_langfuse_verdict_score(trace_id, verdict)  # → call langfuse_createScore
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from agents_janus.trace_analyzer.checks import CHECKS, Check


JUDGE_SYSTEM_PROMPT = """\
You are a trace evaluator for the MalariaSentinel coordination system.
You receive a trace JSON from a janus trial run. Your job is to
evaluate whether each of the 10 checks below passed or failed, based on
the evidence in the trace.

## The 10 checks

{checks_table}

## How to evaluate

For each check:
1. Search the trace for evidence (tool calls, spans, output content).
2. Determine if the evidence satisfies the check.
3. If passed, cite the specific evidence (tool call name, span ID, output excerpt).
4. If failed, explain what's missing.

## Output format

Return ONLY a JSON object (no markdown, no explanation outside the JSON):
{{
  "verdict": "pass" | "fail",
  "score": 0.0-1.0,
  "checks": [
    {{
      "name": "check_name",
      "passed": true|false,
      "evidence": "specific evidence from trace"
    }},
    ...
  ],
  "failures": [
    {{
      "name": "check_name",
      "evidence": "what's missing"
    }}
  ],
  "summary": "one-paragraph overall assessment"
}}

## Rules
- A check passes if there is DIRECT evidence in the trace (tool call, span output, etc.).
- A check fails if the evidence is absent or ambiguous.
- The verdict is "pass" if score >= 0.8 (8 of 10 checks pass).
- Do NOT hallucinate evidence. If you can't find it, the check fails.
- Return ONLY the JSON object. No preamble, no postamble.
"""


# ── Prompt + parser (shared by both paths) ────────────────────────────


def build_checks_table() -> str:
    """Build a markdown table of the 10 checks for the judge prompt."""
    lines = ["| # | Check | Description |"]
    lines.append("|---|---|---|")
    for i, c in enumerate(CHECKS, 1):
        lines.append(f"| {i} | `{c.name}` | {c.description} |")
    return "\n".join(lines)


def build_trace_summary(trace_data: dict, max_chars: int = 30000) -> str:
    """Build a condensed trace summary for the judge (full traces can be huge).

    Extracts: tool calls, span names, generation previews, top-level metadata.
    Drops: raw message content, large outputs.
    """
    summary_parts = []

    meta = trace_data.get("metadata", {})
    if meta:
        summary_parts.append(f"## Metadata\n{json.dumps(meta, indent=2)[:2000]}")

    tool_calls = trace_data.get("tool_calls", [])
    if tool_calls:
        tc_summary = []
        for tc in tool_calls[:50]:
            tc_summary.append({
                "name": tc.get("name", "unknown"),
                "args_preview": str(tc.get("args", {}))[:200],
                "output_preview": str(tc.get("output", ""))[:200],
            })
        summary_parts.append(f"## Tool Calls ({len(tool_calls)} total)\n{json.dumps(tc_summary, indent=2)}")

    spans = trace_data.get("spans", [])
    if spans:
        span_summary = []
        for s in spans[:30]:
            span_summary.append({
                "name": s.get("name", "unknown"),
                "output_preview": str(s.get("output", ""))[:300],
            })
        summary_parts.append(f"## Spans ({len(spans)} total)\n{json.dumps(span_summary, indent=2)}")

    generations = trace_data.get("generations", [])
    if generations:
        gen_summary = []
        for g in generations[:10]:
            gen_summary.append({
                "model": g.get("model", "unknown"),
                "input_preview": str(g.get("input", ""))[:200],
                "output_preview": str(g.get("output", ""))[:300],
            })
        summary_parts.append(f"## Generations ({len(generations)} total)\n{json.dumps(gen_summary, indent=2)}")

    result = "\n\n".join(summary_parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"
    return result


def parse_judge_response(raw: str) -> dict:
    """Parse the LLM judge response into a verdict dict."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                verdict = json.loads(match.group())
            except json.JSONDecodeError:
                return {
                    "verdict": "fail",
                    "score": 0.0,
                    "checks": [],
                    "failures": [{"name": "parse_error", "evidence": f"Could not parse judge response: {text[:500]}"}],
                    "summary": "Judge response was not valid JSON",
                }
        else:
            return {
                "verdict": "fail",
                "score": 0.0,
                "checks": [],
                "failures": [{"name": "parse_error", "evidence": f"No JSON found in judge response: {text[:500]}"}],
                "summary": "Judge response contained no JSON",
            }

    verdict.setdefault("verdict", "fail")
    verdict.setdefault("score", 0.0)
    verdict.setdefault("checks", [])
    verdict.setdefault("failures", [])
    verdict.setdefault("summary", "")
    return verdict


# ── Path 1: local judge via langchain ────────────────────────────────


def judge_trace(
    trace_data: dict,
    *,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    api_key: str | None = None,
) -> dict:
    """Evaluate a trace using an LLM as judge (local langchain call).

    Args:
        trace_data: Parsed trace JSON (dict).
        provider: LLM provider for the judge.
        model: Model identifier for the judge.
        api_key: API key (defaults to env var).

    Returns:
        Verdict dict with verdict, checks, failures, score, summary.
    """
    import os

    checks_table = build_checks_table()
    trace_summary = build_trace_summary(trace_data)

    user_prompt = f"""\
## Trace to Evaluate

{trace_summary}

## Instructions

Evaluate each of the 10 checks against this trace. Return ONLY the JSON verdict.
"""

    system_prompt = JUDGE_SYSTEM_PROMPT.format(checks_table=checks_table)

    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("langchain-openai required for OpenRouter judge")
        key = api_key or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY required for judge")
        llm = ChatOpenAI(model=model, base_url="https://openrouter.ai/api/v1", api_key=key)
    else:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError("langchain-core required for judge")
        llm = init_chat_model(model=model, model_provider=provider)

    from langchain_core.messages import HumanMessage, SystemMessage
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    raw = response.content if isinstance(response.content, str) else str(response.content)
    return parse_judge_response(raw)


# ── Path 2: Langfuse MCP evaluator config ────────────────────────────


def create_langfuse_evaluator() -> dict:
    """Return evaluator config for langfuse_upsertEvaluator MCP tool.

    Call this once to register the judge evaluator in Langfuse.
    The evaluator is an LLM-as-judge that receives a trace and outputs
    a JSON verdict with 10 check results.

    Returns:
        Dict with kwargs for langfuse_upsertEvaluator:
        {name, type, prompt, outputDefinition, modelConfig}
    """
    checks_table = build_checks_table()
    prompt = JUDGE_SYSTEM_PROMPT.format(checks_table=checks_table)

    return {
        "name": "janus-coordination-judge",
        "type": "llm_as_judge",
        "prompt": prompt,
        "outputDefinition": {
            "dataType": "NUMERIC",
            "reasoning": {
                "description": "The LLM evaluates 10 coordination checks and returns a score 0.0-1.0 based on how many passed.",
            },
            "score": {
                "description": "Score 0.0-1.0 representing fraction of checks that passed. Threshold: 0.8 = pass.",
            },
        },
        "modelConfig": {
            "provider": "openrouter",
            "model": "xiaomi/mimo-v2.5",
        },
    }


def create_langfuse_verdict_score(trace_id: str, verdict: dict) -> dict:
    """Return score payload for langfuse_createScore MCP tool.

    Args:
        trace_id: Langfuse trace ID to score.
        verdict: Verdict dict from judge_trace or parse_judge_response.

    Returns:
        Dict with kwargs for langfuse_createScore:
        {name, value, traceId, dataType, comment, metadata}
    """
    score_value = verdict.get("score", 0.0)
    passed = verdict.get("verdict", "fail") == "pass"
    summary = verdict.get("summary", "")

    checks_detail = []
    for c in verdict.get("checks", []):
        status = "✓" if c.get("passed") else "✗"
        checks_detail.append(f"{status} {c.get('name', '?')}: {c.get('evidence', '')[:100]}")

    comment_parts = [f"verdict: {'PASS' if passed else 'FAIL'}", f"score: {score_value}"]
    if summary:
        comment_parts.append(f"summary: {summary[:200]}")
    if checks_detail:
        comment_parts.append("checks:\n" + "\n".join(checks_detail))

    return {
        "name": "janus-coordination-judge",
        "value": score_value,
        "traceId": trace_id,
        "dataType": "NUMERIC",
        "comment": "\n".join(comment_parts),
        "metadata": {
            "verdict": verdict.get("verdict", "fail"),
            "failures": [f["name"] for f in verdict.get("failures", [])],
        },
    }


# Backward compat alias (will be removed in future cleanup)
_build_checks_table = build_checks_table
_build_trace_summary = build_trace_summary
_parse_judge_response = parse_judge_response
