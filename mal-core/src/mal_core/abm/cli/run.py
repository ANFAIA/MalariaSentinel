"""CLI entry point for running ABM simulations."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from mal_core.abm.runner import run_abm

app = typer.Typer(help="Run an ABM simulation.")


@app.command()
def run(
    aoi: str = typer.Option("ghana", help="Area of interest."),
    year: int = typer.Option(2024, help="Simulation year."),
    month: int = typer.Option(1, help="Simulation start month."),
    days: int = typer.Option(365, help="Number of simulation days."),
    n_rollouts: int = typer.Option(1, help="Number of rollouts."),
    seed: int = typer.Option(1, help="Random seed."),
    snapshot_every: int = typer.Option(1, help="Snapshot interval in days (1=daily)."),
    output_dir: Path | None = typer.Option(None, help="Output directory."),
    timeout: int | None = typer.Option(None, help="Optional subprocess timeout in seconds (default: None)."),
) -> None:
    """Run an ABM simulation and print the result as JSON."""
    result = run_abm(
        aoi=aoi,
        year=year,
        month=month,
        days=days,
        n_rollouts=n_rollouts,
        seed=seed,
        snapshot_every=snapshot_every,
        output_dir=output_dir,
        timeout=timeout,
    )
    typer.echo(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    app()
