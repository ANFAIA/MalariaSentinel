"""Main orchestrator that calls OpenCode CLI for research tasks.

This module replaces the old DeepAgents-based harness with OpenCode CLI calls.
OpenCode has Exa built-in via the websearch tool — no custom search needed.
"""

import subprocess
import logging
from pathlib import Path

from .config import PROJECT_ROOT, PAPERS_DIR, OPENCODE_TIMEOUT, DEFAULT_MODEL
from .prompts import (
    RESEARCHER_PROMPT,
    WRITER_PROMPT,
    REVIEWER_PROMPT,
    HYPOTHESIS_PROMPT,
    FULL_CYCLE_PROMPT,
)

logger = logging.getLogger(__name__)


def call_opencode(prompt: str, model: str | None = None, timeout: int | None = None) -> str:
    """Call OpenCode CLI with a prompt in non-interactive mode.

    Uses MIMO V2.5 by default. Override with model param or OPENCODE_MODEL env var.

    Args:
        prompt: The prompt to send to OpenCode
        model: Model override (format: provider/model). Defaults to config.DEFAULT_MODEL
        timeout: Seconds before timeout (default: config value)

    Returns:
        OpenCode's stdout output
    """
    import os
    timeout = timeout or OPENCODE_TIMEOUT
    # Priority: explicit param > env var > config default
    resolved_model = model or os.environ.get("OPENCODE_MODEL") or DEFAULT_MODEL
    logger.info("Calling OpenCode CLI (model=%s, timeout=%ds)", resolved_model, timeout)

    try:
        cmd = ["opencode", "--model", resolved_model, "--print", prompt]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error("OpenCode stderr: %s", result.stderr)
            return f"OpenCode error (exit {result.returncode}): {result.stderr}"
        return result.stdout
    except FileNotFoundError:
        return "Error: opencode CLI not found. Install opencode first."
    except subprocess.TimeoutExpired:
        return f"Error: OpenCode call timed out after {timeout}s"


def run_research_phase(topic: str) -> str:
    """Phase 1: Research — search for papers using OpenCode with Exa."""
    prompt = f"{RESEARCHER_PROMPT}\n\nTopic: {topic}"
    return call_opencode(prompt)


def run_writing_phase(research_results: str) -> str:
    """Phase 2: Writing — condense findings into papers/."""
    prompt = f"{WRITER_PROMPT}\n\nResearch findings to summarize:\n{research_results}"
    return call_opencode(prompt)


def run_review_phase() -> str:
    """Phase 3: Review — check papers for quality."""
    return call_opencode(REVIEWER_PROMPT)


def run_hypothesis_phase() -> str:
    """Phase 4: Hypothesize — generate new research directions."""
    return call_opencode(HYPOTHESIS_PROMPT)


def run_research_cycle(topic: str | None = None) -> str:
    """Run a complete research cycle: research → write → review → hypothesize.

    Args:
        topic: Research topic. If None, uses default topics from config.

    Returns:
        Summary of the cycle's output.
    """
    from .config import DEFAULT_TOPICS

    topic = topic or " | ".join(DEFAULT_TOPICS)
    logger.info("Starting research cycle for: %s", topic)

    results = []

    # Phase 1: Research
    logger.info("Phase 1: Research")
    research = run_research_phase(topic)
    results.append(f"=== RESEARCH ===\n{research}")

    # Phase 2: Writing
    logger.info("Phase 2: Writing")
    writing = run_writing_phase(research)
    results.append(f"=== WRITING ===\n{writing}")

    # Phase 3: Review
    logger.info("Phase 3: Review")
    review = run_review_phase()
    results.append(f"=== REVIEW ===\n{review}")

    # Phase 4: Hypothesis
    logger.info("Phase 4: Hypothesis")
    hypothesis = run_hypothesis_phase()
    results.append(f"=== HYPOTHESIS ===\n{hypothesis}")

    summary = f"Research cycle complete for: {topic}\n\n" + "\n\n".join(results)
    logger.info("Research cycle finished")
    return summary


def run_single_phase(phase: str, topic: str | None = None) -> str:
    """Run a single phase of the research cycle.

    Args:
        phase: One of 'search', 'condense', 'review', 'hypothesize'
        topic: Research topic (required for search phase)

    Returns:
        Phase output
    """
    phase = phase.lower()
    if phase == "search":
        if not topic:
            return "Error: topic is required for search phase"
        return run_research_phase(topic)
    elif phase == "condense":
        return call_opencode(WRITER_PROMPT)
    elif phase == "review":
        return run_review_phase()
    elif phase == "hypothesize":
        return run_hypothesis_phase()
    else:
        return f"Unknown phase: {phase}. Use search, condense, review, or hypothesize."
