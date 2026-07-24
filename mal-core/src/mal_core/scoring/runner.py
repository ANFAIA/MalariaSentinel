"""Run calibration scorers against ABM output."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

def run_calibration(run_dir: str | Path, tier: str = "fast", output_dir: str | Path | None = None, experiment_name: str = "pipeline_run") -> dict:
    calibration_dir = Path(__file__).resolve().parents[1] / "abm" / "tests" / "calibration"
    if not calibration_dir.exists():
        raise FileNotFoundError(f"Calibration tests not found at {calibration_dir}")
    cmd = [sys.executable, "-m", "pytest", str(calibration_dir), "-m", tier, "-v", "--tb=short"]
    env = dict(os.environ)
    env["CALIBRATION_TIER"] = tier
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(calibration_dir.parent.parent), env=env)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
