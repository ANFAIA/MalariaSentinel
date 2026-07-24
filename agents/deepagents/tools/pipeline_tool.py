"""Pipeline tools for running calibration and comparing scorecards."""
import json
import subprocess
from pathlib import Path


def pipeline_run_calibration(
    seed: int = 1,
    days: int = 30,
    n_rollouts: int = 1,
) -> str:
    """Run the calibration suite and return the scorecard as JSON.

    Args:
        seed: Random seed for reproducibility.
        days: Number of simulation days.
        n_rollouts: Number of simulation rollouts.

    Returns:
        JSON string with the scorecard results.
    """
    calibration_dir = Path("mal-abm-fast/tests/calibration")
    if not calibration_dir.exists():
        return json.dumps({
            "error": f"Calibration directory not found: {calibration_dir}",
            "status": "failed",
        })

    try:
        result = subprocess.run(
            [
                "uv", "run", "pytest", "-m", "fast", "-v",
                "--tb=short",
            ],
            cwd=str(calibration_dir),
            capture_output=True,
            text=True,
            timeout=600,
            env={
                **__import__("os").environ,
                "MAL_SEED": str(seed),
                "MAL_DAYS": str(days),
                "MAL_N_ROLLOUTS": str(n_rollouts),
            },
        )

        # Parse stdout for score lines (scorers print structured output)
        output = result.stdout + "\n" + result.stderr

        return json.dumps({
            "status": "completed" if result.returncode == 0 else "tests_failed",
            "returncode": result.returncode,
            "output": output[-3000:],  # Last 3000 chars to avoid huge output
            "seed": seed,
            "days": days,
            "n_rollouts": n_rollouts,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Calibration timed out after 600s", "status": "timeout"})


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
