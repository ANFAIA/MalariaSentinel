"""Onboarding agent tools — direct-execution tools for the conversational onboarding agent.

These tools let the onboarding agent run ABM simulations, pipeline stages,
diagnostics, and status checks without delegating to the improvement orchestrator.
For code-editing tasks, use onboard_delegate to hand off to the improver.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ---------------------------------------------------------------------------
# Stage definitions for the malariasim CLI pipeline
# ---------------------------------------------------------------------------
STAGES = ("download", "ingest", "abm", "score", "train", "predict")


def onboard_run_abm(
    aoi: str = "ghana",
    year: int = 2024,
    month: int = 1,
    days: int = 365,
    seed: int = 1,
    n_rollouts: int = 1,
) -> str:
    """Run an ABM simulation for the given AOI.

    Builds the C++ binary if needed, then runs the simulation.
    Returns JSON with status, duration, and output path.

    Args:
        aoi: Area of interest slug (ghana, niger, tanzania, custom).
        year: Simulation year.
        month: Simulation month.
        days: Simulation duration in days.
        seed: PRNG seed for reproducibility.
        n_rollouts: Number of parallel rollouts.
    """
    start = time.monotonic()
    try:
        from mal_core.abm.runner import run_abm

        result = run_abm(
            aoi=aoi, year=year, month=month, days=days,
            n_rollouts=n_rollouts, seed=seed,
        )
        elapsed = time.monotonic() - start
        return json.dumps({
            "status": "ok" if result.get("returncode", -1) == 0 else "run_failed",
            "aoi": aoi,
            "year": year,
            "days": days,
            "seed": seed,
            "returncode": result.get("returncode"),
            "stdout_tail": result.get("stdout", "")[-500:],
            "stderr_tail": result.get("stderr", "")[-500:],
            "duration_s": round(elapsed, 1),
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "aoi": aoi})


def onboard_run_stage(
    stage: str,
    aoi: str = "ghana",
) -> str:
    """Run a single pipeline stage via the malariasim CLI.

    Args:
        stage: One of: download, ingest, abm, score, train, predict.
        aoi: Area of interest slug.
    """
    if stage not in STAGES:
        return json.dumps({
            "status": "error",
            "error": f"Unknown stage: {stage}. Must be one of: {', '.join(STAGES)}",
        })

    start = time.monotonic()
    cmd = [sys.executable, "-m", "mal_core.cli", stage, "--aoi", aoi]

    # Stage-specific defaults
    if stage == "download":
        cmd.extend(["--datasets", "era5,chirps"])
    elif stage == "abm":
        cmd.extend(["--days", "30", "--seed", "1"])
    elif stage == "score":
        # score needs --run-dir, not --aoi
        run_dir = REPO_ROOT / "runs" / "abm"
        if run_dir.exists():
            cmd = [sys.executable, "-m", "mal_core.cli", "score", "--run-dir", str(run_dir)]
        else:
            return json.dumps({
                "status": "error",
                "error": f"No ABM run directory found at {run_dir}. Run the ABM stage first.",
            })
    elif stage == "train":
        run_dir = REPO_ROOT / "runs" / "abm"
        if run_dir.exists():
            cmd = [sys.executable, "-m", "mal_core.cli", "train", "--run-dir", str(run_dir)]
        else:
            return json.dumps({
                "status": "error",
                "error": f"No ABM run directory found at {run_dir}. Run the ABM stage first.",
            })
    elif stage == "predict":
        cmd.extend(["--scale", "regional", "--year", "2024"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(REPO_ROOT),
        )
        elapsed = time.monotonic() - start
        return json.dumps({
            "status": "ok" if result.returncode == 0 else "stage_failed",
            "stage": stage,
            "aoi": aoi,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-500:],
            "duration_s": round(elapsed, 1),
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "stage": stage, "aoi": aoi})
    except Exception as e:
        return json.dumps({"status": "error", "stage": stage, "error": str(e)})


def onboard_run_pipeline(aoi: str = "ghana") -> str:
    """Run all 6 pipeline stages sequentially for an AOI.

    Stops on first failure and reports per-stage results.
    Order: download → ingest → abm → score → train → predict.
    """
    results = {}
    for stage in STAGES:
        stage_result = json.loads(onboard_run_stage(stage=stage, aoi=aoi))
        results[stage] = stage_result
        if stage_result.get("status") != "ok":
            return json.dumps({
                "status": "pipeline_failed",
                "failed_stage": stage,
                "aoi": aoi,
                "stages": results,
            })
    return json.dumps({
        "status": "ok",
        "aoi": aoi,
        "stages": results,
    })


def onboard_status() -> str:
    """Show current system status: scorecards, plans, subagents, recent runs.

    Returns JSON with all available status information.
    """
    info: dict = {"scorecards": {}, "plans": [], "subagents": [], "recent_runs": []}

    # Best historical scorecard
    best_path = Path("runs/scorecards/best_history.json")
    if best_path.exists():
        try:
            best = json.loads(best_path.read_text())
            info["scorecards"]["best_composite"] = best.get("composite")
            info["scorecards"]["best_ts"] = best.get("ts")
        except (json.JSONDecodeError, OSError):
            pass

    # Open plans
    plans_dir = Path("docs/plans/in-process")
    if plans_dir.exists():
        info["plans"] = [f.name for f in plans_dir.glob("*.md")]

    # Subagents
    try:
        from agents_janus.subagents.registry import load_registry
        reg = load_registry()
        info["subagents"] = list(reg.all().keys())
    except (FileNotFoundError, Exception):
        info["subagents"] = ["registry not available"]

    # Recent ABM runs
    runs_dir = Path("runs/abm")
    if runs_dir.exists():
        run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        info["recent_runs"] = [d.name for d in run_dirs[:5] if d.is_dir()]

    return json.dumps(info, indent=2)


def onboard_diagnose(symptom: str = "") -> str:
    """Run diagnostics: calibration test + trajectory data for agent analysis.

    Executes a 365-day simulation with trajectory to help diagnose issues.
    The agent should analyze the returned data and explain findings to the user.

    Args:
        symptom: Optional description of the symptom to focus on.
    """
    from agents_janus.tools.pipeline_tool import pipeline_run_calibration

    # Run calibration with trajectory
    result = pipeline_run_calibration(seed=1, days=365, include_trajectory=True)
    data = json.loads(result)

    # Add symptom context
    data["symptom_hint"] = symptom if symptom else "general diagnostic"
    data["instructions"] = (
        "Analyze the trajectory data to identify when population changes occur. "
        "Look for: extinction events, sudden drops, oscillations, or plateaus. "
        "Compare against expected biological behavior."
    )

    return json.dumps(data, indent=2)


def onboard_list_components() -> str:
    """List all registered subagents with their specs."""
    try:
        from agents_janus.subagents.registry import load_registry
        reg = load_registry()
        result = []
        for name, spec in reg.all().items():
            result.append({
                "name": name,
                "description": spec.description,
                "model": f"{spec.provider}/{spec.model}",
                "plugins": list(spec.plugins),
                "edits_allow": list(spec.edits_allow),
                "mailbox_inbox": spec.mailbox_inbox,
                "spec": str(spec.spec_path) if spec.spec_path else None,
            })
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def onboard_delegate(goal: str, context: str = "{}") -> str:
    """Delegate a complex task to the improvement orchestrator.

    Use this for tasks that require code editing, spawning workers,
    or multi-step improvement cycles. The improver has full edit access.

    Args:
        goal: The objective for the improvement orchestrator.
        context: JSON string with additional context (answers, menu_key, etc.).
    """
    try:
        ctx = json.loads(context) if isinstance(context, str) else context
    except json.JSONDecodeError:
        ctx = {"raw_context": context}

    from agents_janus.tools.subagent_invoke import handoff_to_improver
    result = handoff_to_improver(goal=goal, context=ctx)
    return result
