"""CLI entry point for running calibration tests via pytest."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer

CALIBRATION_DIR = Path(__file__).resolve().parent.parent / "tests" / "calibration"

app = typer.Typer(help="Run calibration tests.")


@app.command()
def test() -> None:
    """Run ``uv run pytest -m fast -v`` in the calibration tests directory."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "fast", "-v"],
        cwd=CALIBRATION_DIR,
        capture_output=True,
        text=True,
    )
    output = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    typer.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    app()
