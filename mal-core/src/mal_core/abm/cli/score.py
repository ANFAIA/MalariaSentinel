"""CLI entry point for scoring an ABM run directory."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from mal_core.abm.tests.calibration.scorers.score import score_run

app = typer.Typer(help="Score an ABM run directory.")


@app.command()
def score(
    run_dir: Path = typer.Option(..., help="Path to the run directory."),
    include_llm_verdict: bool = typer.Option(False, help="Also run the LLM verdict scorer."),
    experiment: str = typer.Option("default", help="Experiment name from registry."),
) -> None:
    """Score a run directory and print the scorecard as JSON."""
    if not run_dir.is_dir():
        typer.echo(f"Error: {run_dir} is not a directory", err=True)
        raise typer.Exit(1)

    try:
        from mal_core.abm.tests.calibration.experiments.registry import EXPERIMENTS

        exp = EXPERIMENTS.get(experiment)
        exp_dict = exp.to_dict() if hasattr(exp, "to_dict") else {
            "name": experiment,
            "params": {},
            "n_days": 90,
            "n_seeds": 1,
        }
    except Exception:
        exp_dict = {"name": experiment, "params": {}, "n_days": 90, "n_seeds": 1}

    scorecard = score_run(run_dir, exp_dict)

    if include_llm_verdict:
        from mal_core.abm.tests.calibration.scorers.llm_scorer import score_with_llm

        scorecard["llm_verdict"] = score_with_llm(scorecard)

    typer.echo(json.dumps(scorecard, indent=2, default=str))


if __name__ == "__main__":
    app()
