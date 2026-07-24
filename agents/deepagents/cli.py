"""CLI entry point for the MalariaSentinel DeepAgent system."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer

app = typer.Typer(
    name="deepagents",
    help="MalariaSentinel DeepAgent System — multi-agent ABM calibration orchestrator.",
    no_args_is_help=True,
)


@app.command()
def calibration(
    max_iterations: int = typer.Option(10, "--max-iterations", "-n", help="Maximum improvement iterations."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
):
    """Run the ABM calibration improvement cycle."""
    from agents.deepagents.cycles.calibration_cycle import run_calibration_cycle

    result = run_calibration_cycle(max_iterations=max_iterations, dry_run=dry_run)

    if dry_run:
        typer.echo(result)
    else:
        typer.echo(result)


@app.command()
def feature(
    name: str = typer.Argument(..., help="Feature name."),
    description: str = typer.Argument(..., help="Feature description."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
):
    """Run a feature development cycle."""
    from agents.deepagents.cycles.feature_cycle import run_feature_cycle

    result = run_feature_cycle(name=name, description=description, dry_run=dry_run)

    if dry_run:
        typer.echo(result)
    else:
        typer.echo(result)


@app.command()
def research(
    topic: str = typer.Argument(..., help="Research topic to investigate."),
    cycles: int = typer.Option(1, "--cycles", "-c", help="Number of research cycles."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
):
    """Run a research + improvement cycle."""
    from agents.deepagents.cycles.research_cycle import run_research_cycle

    result = run_research_cycle(topic=topic, cycles=cycles, dry_run=dry_run)

    if dry_run:
        typer.echo(result)
    else:
        typer.echo(result)


if __name__ == "__main__":
    app()
