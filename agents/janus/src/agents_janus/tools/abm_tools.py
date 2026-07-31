"""ABM custom tools for the DeepAgent worker subagent.

These are thin wrappers around the mal-core ABM CLI entry points,
designed to be called by a deepagents worker inside an isolated worktree.

Worktree isolation:
    The orchestrator calls register_worktree()/set_current_agent() before
    spawning a subagent via `task`. The tools resolve paths relative to
    the registered worktree. After the subagent finishes, the orchestrator
    calls unregister_worktree()/clear_current_agent().

    This works because langgraph's `task` tool invokes subagents
    synchronously in the same thread — thread-local state carries over.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Worktree registry — set by orchestrator before spawning subagents
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_WORKTREE_REGISTRY: dict[str, Path] = {}
_thread_local = threading.local()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def register_worktree(agent_id: str, worktree_path: str) -> None:
    """Register a worktree path for an agent. Called by orchestrator."""
    with _lock:
        _WORKTREE_REGISTRY[agent_id] = Path(worktree_path)


def unregister_worktree(agent_id: str) -> None:
    """Unregister a worktree. Called by orchestrator after subagent finishes."""
    with _lock:
        _WORKTREE_REGISTRY.pop(agent_id, None)


def set_current_agent(agent_id: str) -> None:
    """Set the current agent ID in thread-local storage."""
    _thread_local.current_agent_id = agent_id


def clear_current_agent() -> None:
    """Clear the current agent ID from thread-local storage."""
    _thread_local.current_agent_id = None


def _resolve_worktree() -> Path:
    """Resolve the worktree path for the current agent.

    Returns the registered worktree path if an agent is active,
    otherwise falls back to the repo root (backward compat).
    """
    agent_id = getattr(_thread_local, "current_agent_id", None)
    if agent_id:
        with _lock:
            wt = _WORKTREE_REGISTRY.get(agent_id)
            if wt:
                return wt
    return REPO_ROOT


# ---------------------------------------------------------------------------
# ABM tools — all resolve paths via _resolve_worktree()
# ---------------------------------------------------------------------------

def abm_run(
    aoi: str = "ghana",
    year: int = 2024,
    month: int = 1,
    days: int = 365,
    n_rollouts: int = 1,
    seed: int = 1,
    snapshot_every: int = 7,
) -> str:
    """Build (if needed) and run an ABM simulation.

    Paths are resolved relative to the current agent's gitagent worktree.
    Returns JSON with run metadata including the output directory.
    """
    import time
    start = time.monotonic()

    worktree = _resolve_worktree()
    pkg_dir = worktree / "mal-core" / "src" / "mal_core" / "abm"
    build_script = pkg_dir / "build.sh"
    build_dir = pkg_dir / "build" / "src" / "mal_abm_fast"

    if not build_dir.exists() and build_script.exists():
        build_result = subprocess.run(
            ["bash", str(build_script)],
            capture_output=True, text=True, timeout=300,
            cwd=str(worktree),
        )
        if build_result.returncode != 0:
            return json.dumps({
                "status": "build_failed",
                "stderr": build_result.stderr[-1000:],
            })

    try:
        from mal_core.abm.runner import run_abm
        result = run_abm(
            aoi=aoi, year=year, month=month, days=days,
            n_rollouts=n_rollouts, seed=seed,
            snapshot_every=snapshot_every,
        )
        elapsed = time.monotonic() - start
        return json.dumps({
            "status": "ok" if result.get("returncode", -1) == 0 else "run_failed",
            "returncode": result.get("returncode"),
            "stdout_tail": result.get("stdout", "")[-500:],
            "stderr_tail": result.get("stderr", "")[-500:],
            "duration_s": round(elapsed, 1),
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def abm_test() -> str:
    """Run the calibration test suite (pytest -m fast -v).

    Paths are resolved relative to the current agent's gitagent worktree.
    Returns JSON with pass/fail summary.
    """
    import time
    start = time.monotonic()

    worktree = _resolve_worktree()
    cal_dir = worktree / "mal-core" / "src" / "mal_core" / "abm" / "tests" / "calibration"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "fast", "-v", "--tb=short"],
            cwd=str(cal_dir),
            capture_output=True, text=True, timeout=300,
        )
        elapsed = time.monotonic() - start
        return json.dumps({
            "status": "ok" if result.returncode == 0 else "tests_failed",
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-500:],
            "duration_s": round(elapsed, 1),
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def abm_score(run_dir: str, include_llm_verdict: bool = True) -> str:
    """Run calibration scorers on a run directory.

    Returns JSON with scorecard (D1-D14 + composite + optional LLM verdict).
    """
    try:
        from mal_core.abm.tests.calibration.scorers.score import score_run
        from mal_core.abm.tests.calibration.scorers.llm_scorer import score_with_llm

        report = score_run(Path(run_dir))
        scores = report.get("scores", {})

        result = {
            "scores": scores,
            "composite": report.get("composite"),
            "status": "ok",
        }

        if include_llm_verdict:
            try:
                llm_result = score_with_llm(report)
                result["llm_verdict"] = llm_result
            except Exception as e:
                result["llm_verdict"] = {"error": str(e)}

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
