"""ABM custom tools for the DeepAgent worker subagent.

These are thin wrappers around the mal-core ABM CLI entry points,
designed to be called by a deepagents worker inside an isolated worktree.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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

    Returns JSON with run metadata including the output directory.
    """
    import time
    start = time.monotonic()

    # Find build.sh and compile if binary doesn't exist
    pkg_dir = Path(__file__).resolve().parent.parent.parent.parent / "mal-core" / "src" / "mal_core" / "abm"
    build_script = pkg_dir / "build.sh"
    build_dir = pkg_dir / "build" / "src" / "mal_abm_fast"

    if not build_dir.exists() and build_script.exists():
        build_result = subprocess.run(
            ["bash", str(build_script)],
            capture_output=True, text=True, timeout=300,
        )
        if build_result.returncode != 0:
            return json.dumps({
                "status": "build_failed",
                "stderr": build_result.stderr[-1000:],
            })

    # Run the simulation via runner
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

    Returns JSON with pass/fail summary.
    """
    import time
    start = time.monotonic()

    cal_dir = Path(__file__).resolve().parent.parent.parent.parent / "mal-core" / "src" / "mal_core" / "abm" / "tests" / "calibration"

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
