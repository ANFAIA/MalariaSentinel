"""Trial harness — runs janus with a trial prompt, captures trace, invokes judge.

This is the "test harness" described in M16 plan §9. It:
1. Runs janus with a TRIAL goal.
2. Captures the Langfuse trace (if tracing is enabled).
3. Feeds the trace to the LLM-as-Judge.
4. Produces a verdict JSON.

Usage:
    # From CLI
    python -m agents_janus.trace_analyzer.harness --goal "TRIAL: ..." --tracing langfuse

    # From code
    from agents_janus.trace_analyzer.harness import run_trial
    verdict = run_trial(goal="TRIAL: run abm + scoring", tracing="langfuse")
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any


def run_trial(
    goal: str,
    *,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "trial-session",
    tracing: str = "langfuse",
    max_iterations: int = 15,
    quiet: bool = True,
    judge_provider: str | None = None,
    judge_model: str | None = None,
) -> dict:
    """Run a trial and evaluate with LLM-as-Judge.
    
    Args:
        goal: The trial goal (required).
        provider: LLM provider for janus.
        model: Model for janus.
        thread_id: Thread ID for checkpointing.
        tracing: Tracing backend ("langfuse" or "").
        max_iterations: Max improvement iterations.
        quiet: Suppress live panel.
        judge_provider: LLM provider for the judge (defaults to same as janus).
        judge_model: Model for the judge (defaults to same as janus).
    
    Returns:
        Verdict dict with verdict, checks, failures, score, summary, trace_id.
    """
    from agents_janus.trace_analyzer.judge import judge_trace

    judge_provider = judge_provider or provider
    judge_model = judge_model or model

    # 1. Build langfuse client if tracing
    langfuse_client = None
    trace_id = None
    if tracing == "langfuse":
        langfuse_client = _build_langfuse_client()
        if langfuse_client:
            trace_id = f"trial-{int(time.time())}"

    # 2. Run janus with the trial goal
    print(f"[harness] Running trial: {goal[:80]}...", file=sys.stderr)
    start = time.monotonic()

    from agents_janus.improvement import run_improvement
    result = run_improvement(
        goal=goal,
        provider=provider,
        model=model,
        thread_id=thread_id,
        quiet=quiet,
        langfuse_client=langfuse_client,
    )

    elapsed = time.monotonic() - start
    print(f"[harness] Trial completed in {elapsed:.1f}s", file=sys.stderr)

    # 3. Flush langfuse and fetch the trace
    trace_data = None
    if langfuse_client:
        try:
            langfuse_client.flush()
            trace_data = _fetch_trace(langfuse_client, trace_id)
        except Exception as e:
            print(f"[harness] Warning: could not fetch trace: {e}", file=sys.stderr)

    if trace_data is None:
        # No trace available — construct a minimal trace from the result
        trace_data = _trace_from_result(result, elapsed)

    # 4. Invoke the judge
    print(f"[harness] Invoking LLM-as-Judge ({judge_provider}/{judge_model})...", file=sys.stderr)
    verdict = judge_trace(
        trace_data,
        provider=judge_provider,
        model=judge_model,
    )

    # 5. Add metadata
    verdict["trial_goal"] = goal
    verdict["trial_elapsed_s"] = round(elapsed, 1)
    verdict["trace_id"] = trace_id
    verdict["janus_result_preview"] = str(result)[:500]

    # 6. Save to fixtures
    fixture_path = _save_fixture(verdict, trace_id)
    verdict["fixture_path"] = str(fixture_path)

    print(f"[harness] Verdict: {verdict['verdict']} (score={verdict['score']})", file=sys.stderr)
    return verdict


def run_trial_from_trace(
    trace_data: dict,
    *,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
) -> dict:
    """Evaluate an existing trace with the LLM-as-Judge (no janus run).
    
    Useful when you already have a Langfuse trace and just need evaluation.
    
    Args:
        trace_data: Parsed Langfuse trace JSON.
        provider: LLM provider for the judge.
        model: Model for the judge.
    
    Returns:
        Verdict dict.
    """
    from agents_janus.trace_analyzer.judge import judge_trace
    return judge_trace(trace_data, provider=provider, model=model)


def _build_langfuse_client():
    """Build a langfuse.Langfuse client from env vars."""
    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (host and public_key and secret_key):
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    except ImportError:
        return None


def _fetch_trace(langfuse_client, trace_id: str | None) -> dict | None:
    """Fetch a trace from Langfuse by ID."""
    if not trace_id or not langfuse_client:
        return None
    try:
        # Langfuse SDK: fetch trace by ID
        trace = langfuse_client.get_trace(trace_id)
        if trace:
            return _langfuse_trace_to_dict(trace)
    except Exception:
        pass
    return None


def _langfuse_trace_to_dict(trace) -> dict:
    """Convert a Langfuse trace object to a dict for the judge."""
    try:
        data = {
            "id": getattr(trace, "id", None),
            "metadata": getattr(trace, "metadata", {}),
            "tool_calls": [],
            "spans": [],
            "generations": [],
        }

        # Extract observations (spans, generations, tool calls)
        observations = getattr(trace, "observations", [])
        for obs in observations:
            obs_type = getattr(obs, "type", "unknown")
            obs_dict = {
                "name": getattr(obs, "name", "unknown"),
                "type": obs_type,
                "input": getattr(obs, "input", None),
                "output": getattr(obs, "output", None),
                "metadata": getattr(obs, "metadata", {}),
            }
            if obs_type == "generation":
                obs_dict["model"] = getattr(obs, "model", "unknown")
                data["generations"].append(obs_dict)
            elif obs_type == "span":
                data["spans"].append(obs_dict)
            else:
                data["spans"].append(obs_dict)

        return data
    except Exception:
        return {}


def _trace_from_result(result: str, elapsed_s: float) -> dict:
    """Construct a minimal trace from the janus result string (no Langfuse)."""
    return {
        "metadata": {
            "source": "trial_harness",
            "elapsed_s": round(elapsed_s, 1),
        },
        "tool_calls": [],
        "spans": [{
            "name": "trial_result",
            "output": str(result)[:2000],
        }],
        "generations": [],
    }


def _save_fixture(verdict: dict, trace_id: str | None) -> Path:
    """Save the verdict to tests/fixtures/ for promotion."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    name = f"trial-{trace_id or int(time.time())}.json"
    path = fixtures_dir / name
    path.write_text(json.dumps(verdict, indent=2))
    return path


# ── CLI entry point ──────────────────────────────────────────────────

def main():
    """CLI entry point for the trial harness."""
    import argparse
    parser = argparse.ArgumentParser(description="Janus trial harness")
    parser.add_argument("--goal", "-g", required=True, help="Trial goal")
    parser.add_argument("--provider", "-p", default="openrouter", help="LLM provider")
    parser.add_argument("--model", "-m", default="xiaomi/mimo-v2.5", help="Model")
    parser.add_argument("--tracing", "-t", default="langfuse", help="Tracing backend")
    parser.add_argument("--judge-provider", default=None, help="Judge LLM provider")
    parser.add_argument("--judge-model", default=None, help="Judge model")
    args = parser.parse_args()

    verdict = run_trial(
        goal=args.goal,
        provider=args.provider,
        model=args.model,
        tracing=args.tracing,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
    )

    print(json.dumps(verdict, indent=2))
    sys.exit(0 if verdict["verdict"] == "pass" else 1)


if __name__ == "__main__":
    main()
