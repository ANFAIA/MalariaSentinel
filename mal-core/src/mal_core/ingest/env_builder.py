"""Ingest stage — builds env tensor + habitat patches for an AOI."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def build_environment(aoi: str = "ghana", year: int = 2024, month: int = 6, output_dir: str | Path | None = None, scale: str = "regional", **kwargs) -> dict:
    script = Path(__file__).resolve().parents[3] / "mal-execution" / "scripts" / "build_environment.py"
    if not script.exists():
        raise FileNotFoundError(f"build_environment.py not found at {script}")
    cmd = [sys.executable, str(script), "--aoi", aoi, "--year", str(year), "--month", str(month), "--scale", scale]
    if output_dir:
        cmd.extend(["--output-dir", str(output_dir)])
    for k, v in kwargs.items():
        if v is not None:
            cmd.extend([f"--{k.replace('_', '-')}", str(v)])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
