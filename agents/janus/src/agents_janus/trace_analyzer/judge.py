"""LLM-as-Judge — evaluates Langfuse traces against the 10 named checks.

An independent agent (not a janus subagent) that receives a Langfuse trace
JSON and uses an LLM to determine whether each of the 10 sibling-coordination
checks passed or failed. This is the "LLM as a Judge" pattern.

Usage:
    from agents_janus.trace_analyzer.judge import judge_trace
    verdict = judge_trace(trace_json, provider="openrouter", model="xiaomi/mimo-v2.5")
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from agents_janus.trace_analyzer.checks import CHECKS, Check


JUDGE_SYSTEM_PROMPT = """\
You are a trace evaluator for the MalariaSentinel sibling coordination system.
You receive a Langfuse trace JSON from a janus trial run. Your job is to
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


def _build_checks_table() -> str:
    """Build a markdown table of the 10 checks for the judge prompt."""
    lines = ["| # | Check | Description |"]
    lines.append("|---|---|---|")
    for i, c in enumerate(CHECKS, 1):
        lines.append(f"| {i} | `{c.name}` | {c.description} |")
    return "\n".join(lines)


def _build_trace_summary(trace_data: dict, max_chars: int = 30000) -> str:
    """Build a condensed trace summary for the judge (full traces can be huge).
    
    Extracts: tool calls, span names, generation previews, top-level metadata.
    Drops: raw message content, large outputs,重复 spans.
    """
    summary_parts = []

    # Top-level metadata
    meta = trace_data.get("metadata", {})
    if meta:
        summary_parts.append(f"## Metadata\n{json.dumps(meta, indent=2)[:2000]}")

    # Tool calls (most important for evidence)
    tool_calls = trace_data.get("tool_calls", [])
    if tool_calls:
        tc_summary = []
        for tc in tool_calls[:50]:  # cap at 50
            tc_summary.append({
                "name": tc.get("name", "unknown"),
                "args_preview": str(tc.get("args", {}))[:200],
                "output_preview": str(tc.get("output", ""))[:200],
            })
        summary_parts.append(f"## Tool Calls ({len(tool_calls)} total)\n{json.dumps(tc_summary, indent=2)}")

    # Spans
    spans = trace_data.get("spans", [])
    if spans:
        span_summary = []
        for s in spans[:30]:  # cap at 30
            span_summary.append({
                "name": s.get("name", "unknown"),
                "output_preview": str(s.get("output", ""))[:300],
            })
        summary_parts.append(f"## Spans ({len(spans)} total)\n{json.dumps(span_summary, indent=2)}")

    # Generations (LLM calls)
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


def judge_trace(
    trace_data: dict,
    *,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    api_key: str | None = None,
) -> dict:
    """Evaluate a Langfuse trace using an LLM as judge.
    
    Args:
        trace_data: Parsed Langfuse trace JSON (dict).
        provider: LLM provider for the judge.
        model: Model identifier for the judge.
        api_key: API key (defaults to env var).
    
    Returns:
        Verdict dict with verdict, checks, failures, score, summary.
    """
    import os

    # Build the judge prompt
    checks_table = _build_checks_table()
    trace_summary = _build_trace_summary(trace_data)

    user_prompt = f"""\
## Langfuse Trace to Evaluate

{trace_summary}

## Instructions

Evaluate each of the 10 checks against this trace. Return ONLY the JSON verdict.
"""

    system_prompt = JUDGE_SYSTEM_PROMPT.format(checks_table=checks_table)

    # Resolve LLM
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

    # Call the LLM
    from langchain_core.messages import HumanMessage, SystemMessage
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    # Parse the response
    raw = response.content if isinstance(response.content, str) else str(response.content)
    return _parse_judge_response(raw)


def _parse_judge_response(raw: str) -> dict:
    """Parse the LLM judge response into a verdict dict."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
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

    # Ensure required fields
    verdict.setdefault("verdict", "fail")
    verdict.setdefault("score", 0.0)
    verdict.setdefault("checks", [])
    verdict.setdefault("failures", [])
    verdict.setdefault("summary", "")

    return verdict
