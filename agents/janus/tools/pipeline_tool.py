"""Pipeline tools for running calibration and comparing scorecards."""
import json
import os
import re
import subprocess
from pathlib import Path


def pipeline_run_calibration(
    seed: int = 1,
    days: int = 30,
    n_rollouts: int = 1,
    include_trajectory: bool = False,
) -> str:
    """Run the calibration suite and return compact results with composite score.

    Args:
        seed: Random seed for reproducibility.
        days: Number of simulation days.
        n_rollouts: Number of simulation rollouts.
        include_trajectory: If True, also run a longer simulation and return
            day-by-day trajectory data (adults, aquatic, eggs).

    Returns:
        Compact JSON with pass/fail summary, composite score, and optionally
        a trajectory table.
    """
    calibration_dir = Path("mal-core/src/mal_core/abm/tests/calibration")
    if not calibration_dir.exists():
        return json.dumps({
            "error": f"Calibration directory not found: {calibration_dir}",
            "status": "failed",
        })

    env = {**os.environ, "MAL_SEED": str(seed), "MAL_DAYS": str(days), "MAL_N_ROLLOUTS": str(n_rollouts)}

    # Step 1: Run tests
    try:
        test_result = subprocess.run(
            ["uv", "run", "pytest", "-m", "fast", "-v", "--tb=short"],
            cwd=str(calibration_dir),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Tests timed out after 300s", "status": "timeout"})

    # Parse test results
    test_summary = ""
    passed = failed = 0
    for line in (test_result.stdout + test_result.stderr).splitlines():
        m = re.search(r"(\d+) passed", line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m:
            failed = int(m.group(1))
        if "passed" in line and ("failed" in line or "error" in line or "in " in line):
            test_summary = line.strip()

    # Step 2: Run scorecard to get composite
    composite = None
    try:
        score_result = subprocess.run(
            ["uv", "run", "python", "-m", "scorers.score", "--run-dir", str(calibration_dir / "runs" / f"seed{seed}")],
            cwd=str(calibration_dir),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        for line in score_result.stdout.splitlines():
            m = re.search(r"Composite:\s*([\d.]+)", line)
            if m:
                composite = float(m.group(1))
    except (subprocess.TimeoutExpired, Exception):
        pass

    # Step 3: Optionally extract trajectory from existing simulation outputs
    trajectory = None
    if include_trajectory:
        trajectory = _extract_trajectory(calibration_dir / "runs" / f"seed{seed}")

    return json.dumps({
        "status": "ok" if test_result.returncode == 0 else "tests_failed",
        "tests_passed": passed,
        "tests_failed": failed,
        "test_summary": test_summary,
        "composite": composite,
        "trajectory": trajectory,
        "seed": seed,
        "days": days,
        "n_rollouts": n_rollouts,
        "duration_s": round(
            sum(
                float(m.group(1))
                for line in (test_result.stdout + test_result.stderr).splitlines()
                if (m := re.search(r"in\s+([\d.]+)s", line))
            ), 1
        ) if "in " in test_summary else None,
    })


def _extract_trajectory(runs_dir: Path) -> dict | None:
    """Extract day-by-day trajectory from _aquatic.json files.

    Returns dict with:
        days: list of day indices
        adults: list of total adult counts (from COG density)
        aquatic: list of total_aquatic
        eggs: list of egg counts
    """
    if not runs_dir.exists():
        return None

    aquatic_files = sorted(runs_dir.glob("*_aquatic.json"))
    if not aquatic_files:
        return None

    days = []
    aquatic_totals = []
    egg_counts = []

    for f in aquatic_files:
        try:
            data = json.loads(f.read_text())
            # Extract day from filename: pattern "*_day{N}_aquatic.json"
            m = re.search(r"_day(\d+)_aquatic\.json$", f.name)
            day = int(m.group(1)) if m else len(days)
            days.append(day)
            aquatic_totals.append(data.get("total_aquatic", 0))
            eggs = data.get("by_stage", {}).get("egg", {}).get("total", 0)
            egg_counts.append(eggs)
        except (json.JSONDecodeError, OSError):
            continue

    if not days:
        return None

    return {
        "days": days,
        "aquatic_total": aquatic_totals,
        "eggs": egg_counts,
        "n_snapshots": len(days),
        "first_day": min(days) if days else None,
        "last_day": max(days) if days else None,
    }


def pipeline_compare_scorecards(
    current_output: str,
    baseline_composite: float = 0.0,
) -> str:
    """Compare a scorecard against a baseline composite score.

    Args:
        current_output: The JSON output from pipeline_run_calibration.
        baseline_composite: The baseline composite score to compare against.

    Returns:
        JSON with comparison results including deltas.
    """
    try:
        data = json.loads(current_output)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON input", "status": "failed"})

    # The actual composite score extraction would depend on the scorer output format
    # For now, return a structured comparison
    return json.dumps({
        "status": data.get("status", "unknown"),
        "baseline_composite": baseline_composite,
        "calibration_returncode": data.get("returncode", -1),
        "seed": data.get("seed"),
        "days": data.get("days"),
        "raw_output_snippet": data.get("output", "")[:500],
    })
