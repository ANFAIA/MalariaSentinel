"""Typer CLI — command-line interface to the SDSS.

Commands:
    malariasim run --aoi {aoi} --stages abm,score --abm-days 30
    malariasim ingest --aoi {aoi} --year {year} --month {month}
    malariasim abm --aoi {aoi} --days 30
    malariasim score --run-dir {dir}
    malariasim predict --aoi {aoi} --scale {regional|national|continental} --year {year}
    malariasim feedback --run-dir {dir}
    malariasim status --aoi {aoi}
    malariasim serve --host {host} --port {port}
"""
from __future__ import annotations

from pathlib import Path

import typer

from mal_commonlib.aoi import Scale

from .prediction.predictor import get_prediction_metadata, run_prediction
from .scenario import load_scenario

app = typer.Typer(name="malariasim", help="MalariaSentinel SDSS CLI", no_args_is_help=True)


@app.command()
def predict(
    aoi: str | None = typer.Option(None, "--aoi", help="AOI slug (e.g. ghana)"),
    scale: Scale = typer.Option(Scale.REGIONAL, "--scale", help="Prediction scale"),
    year: int = typer.Option(2026, "--year", help="Simulation year"),
    month: int = typer.Option(1, "--month", help="Simulation month"),
    model: str = typer.Option("dummy", "--model", help="Model name from registry"),
    scenario_path: Path | None = typer.Option(
        None, "--scenario", "-s", help="Path to scenario YAML"
    ),
) -> None:
    scenario = None
    if scenario_path is not None:
        scenario = load_scenario(scenario_path)
        aoi = scenario.aoi
        scale = scenario.scale
        year = scenario.year
        month = scenario.month

    if aoi is None:
        typer.echo("Error: --aoi is required when --scenario is not provided", err=True)
        raise typer.Exit(code=1)

    out = run_prediction(
        aoi_slug=aoi,
        scale=scale,
        year=year,
        month=month,
        model_name=model,
        scenario=scenario,
    )
    typer.echo(f"Prediction saved: {out}")


@app.command()
def run(
    aoi: str = typer.Option(..., "--aoi", help="AOI slug (e.g. ghana)"),
    year: int = typer.Option(2024, "--year", help="Simulation year"),
    month: int = typer.Option(1, "--month", help="Simulation month"),
    seed: int = typer.Option(1, "--seed", help="Random seed"),
    days: int = typer.Option(30, "--days", help="ABM simulation days"),
    n_rollouts: int = typer.Option(1, "--n-rollouts", help="Number of ABM rollouts"),
    stages: str = typer.Option("ingest,abm,score,train,predict", "--stages", help="Comma-separated stages"),
    output_dir: Path = typer.Option(Path("runs/pipeline"), "--output-dir", help="Output directory"),
    resume: bool = typer.Option(True, "--resume/--no-resume", help="Skip completed stages"),
) -> None:
    """Run the full SDSS pipeline or selected stages."""
    from .pipeline.runner import run_pipeline
    from .pipeline.stages import Stage

    stage_list = [Stage(s.strip()) for s in stages.split(",")]
    result = run_pipeline(
        aoi=aoi, year=year, month=month, seed=seed,
        days=days, n_rollouts=n_rollouts,
        stages=stage_list, output_dir=output_dir, resume=resume,
    )
    typer.echo(f"Pipeline result: {result}")


@app.command()
def ingest(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug"),
    year: int = typer.Option(2024, "--year", help="Year"),
    month: int = typer.Option(6, "--month", help="Month"),
    output_dir: Path = typer.Option(Path("runs/ingest"), "--output-dir"),
    scale: str = typer.Option("regional", "--scale"),
) -> None:
    """Build environmental tensors for an AOI."""
    from .ingest import build_environment

    result = build_environment(aoi=aoi, year=year, month=month, output_dir=output_dir, scale=scale)
    typer.echo(f"Ingest result: {result}")


@app.command()
def abm(
    aoi: str = typer.Option(..., "--aoi", help="AOI slug"),
    year: int = typer.Option(2024, "--year"),
    month: int = typer.Option(1, "--month"),
    seed: int = typer.Option(1, "--seed"),
    days: int = typer.Option(30, "--days"),
    n_rollouts: int = typer.Option(1, "--n-rollouts"),
    output_dir: Path = typer.Option(Path("runs/abm"), "--output-dir"),
) -> None:
    """Run the ABM simulation."""
    from .abm import run_abm

    result = run_abm(aoi=aoi, year=year, month=month, seed=seed, days=days, n_rollouts=n_rollouts, output_dir=output_dir)
    typer.echo(f"ABM result: {result}")


@app.command()
def score(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
    tier: str = typer.Option("fast", "--tier", help="Test tier (fast/full)"),
) -> None:
    """Run calibration scorers."""
    from .scoring import run_calibration

    result = run_calibration(run_dir=run_dir, tier=tier)
    typer.echo(f"Scoring result: {result}")


@app.command()
def train(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM rollout outputs"),
    output_dir: Path = typer.Option(Path("runs/training"), "--output-dir", help="Model output directory"),
    epochs: int = typer.Option(50, "--epochs", help="Training epochs"),
    batch_size: int = typer.Option(16, "--batch-size", help="Batch size"),
    lr: float = typer.Option(1e-3, "--lr", help="Learning rate"),
) -> None:
    """Train the U-Net surrogate model."""
    from .training import train_unet

    best_dice = train_unet(run_dir=run_dir, output_dir=output_dir, epochs=epochs, batch_size=batch_size, lr=lr)
    typer.echo(f"Training complete. Best val_dice: {best_dice:.4f}")


@app.command()
def feedback(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
    baseline_dir: Path | None = typer.Option(None, "--baseline", help="Baseline for comparison"),
) -> None:
    """Generate feedback from calibration results."""
    from .scoring import get_feedback, run_calibration

    scorecard = run_calibration(run_dir=run_dir)
    baseline = run_calibration(run_dir=baseline_dir) if baseline_dir else None
    fb = get_feedback(scorecard, baseline)
    typer.echo(fb)


@app.command()
def status(
    aoi: str = typer.Option(..., "--aoi", help="AOI slug"),
) -> None:
    meta = get_prediction_metadata(aoi)
    if meta is None:
        typer.echo(f"No predictions found for AOI {aoi!r}")
        raise typer.Exit(code=1)
    for k, v in meta.items():
        typer.echo(f"  {k}: {v}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="Bind port"),
) -> None:
    import uvicorn

    from .server import app as fastapi_app

    typer.echo(f"Starting SDSS server on {host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


def main() -> None:
    app()
