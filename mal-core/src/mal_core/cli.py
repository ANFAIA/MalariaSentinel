"""Typer CLI — command-line interface to the SDSS.

Commands:
    malariasim run --aoi {aoi} --stages abm,scoring --stage-flags "abm.days=60"
    malariasim ingest --aoi {aoi} --year {year} --month {month}
    malariasim abm --aoi {aoi} --days 30
    malariasim score --run-dir {dir} --tier fast
    malariasim predict --aoi {aoi} --scale {regional|national|continental} --year {year}
    malariasim feedback --run-dir {dir}
    malariasim status --aoi {aoi}
    malariasim serve --host {host} --port {port}
"""
from __future__ import annotations

from pathlib import Path
from enum import Enum

import typer

from mal_commonlib.aoi import Scale

from .prediction.predictor import get_prediction_metadata, run_prediction
from .scenario import load_scenario

app = typer.Typer(name="malariasim", help="MalariaSentinel SDSS CLI", no_args_is_help=True)


class Tier(str, Enum):
    """Tier choice for calibration scoring."""
    FAST = "fast"
    FULL = "full"


def _parse_stage_flags(raw: str | None) -> dict[str, dict[str, str]]:
    """Parse 'abm.days=60,training.epochs=100,flag=val' into nested dict.

    Flags with a stage prefix (e.g. 'abm.days=60') are routed to that stage.
    Flags without a prefix (e.g. 'seed=42') are placed under '_global' and
    forwarded to all stages.
    """
    if not raw:
        return {}
    flags: dict[str, dict[str, str]] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            continue  # skip malformed tokens
        if "." in token.split("=")[0]:
            stage, rest = token.split(".", 1)
            key, _, value = rest.partition("=")
            flags.setdefault(stage.strip(), {})[key.strip()] = value.strip()
        else:
            key, _, value = token.partition("=")
            flags.setdefault("_global", {})[key.strip()] = value.strip()
    return flags


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
    """Generate malaria risk predictions for an AOI.

    Runs a trained model (or dummy predictor) over environmental tensors
    to produce a classified risk map.

    Key parameters:
      --aoi: Area of interest slug
      --scale: regional, national, or continental
      --year/--month: Time window for the prediction
      --model: Name from the prediction model registry
    """
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
    stages: str = typer.Option("ingest,abm,scoring,training,prediction", "--stages", help="Comma-separated stages"),
    output_dir: Path = typer.Option(Path("runs/pipeline"), "--output-dir", help="Output directory"),
    resume: bool = typer.Option(True, "--resume/--no-resume", help="Skip completed stages"),
    stage_flags: str | None = typer.Option(None, "--stage-flags", help="Stage-specific params as comma-separated key=value pairs (e.g. 'abm.days=60,training.epochs=100')"),
) -> None:
    """Run the full SDSS pipeline or selected stages.

    Stages run in order: ingest → abm → scoring → training → prediction.
    Use --stages to run a subset, and --stage-flags to pass parameters
    to specific stages.

    Key parameters:
      --stages: Comma-separated stage names (ingest,abm,scoring,training,prediction)
      --stage-flags: Stage-specific overrides as 'stage.key=value' pairs
      --resume: Skip stages whose output directory is non-empty
      --output-dir: Root directory for all stage outputs
    """
    from .pipeline.runner import run_pipeline
    from .pipeline.stages import Stage

    stage_list = [Stage(s.strip()) for s in stages.split(",")]
    parsed_flags = _parse_stage_flags(stage_flags)
    result = run_pipeline(
        aoi=aoi, year=year, month=month, seed=seed,
        days=days, n_rollouts=n_rollouts,
        stages=stage_list, output_dir=output_dir, resume=resume,
        stage_flags=parsed_flags if parsed_flags else None,
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
    """Build environmental tensors for an AOI.

    Ingests terrain, climate, and land-cover data to produce the
    multi-band raster stack used by the ABM and prediction stages.

    Key parameters:
      --aoi: Area of interest slug
      --year/--month: Time window for the environmental data
      --scale: regional, national, or continental resolution
    """
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
    """Run the agent-based malaria simulation.

    Simulates Anopheles gambiae population dynamics, dispersal,
    and transmission potential using the mal_abm_fast C++ engine.

    Key parameters:
      --days: Simulation duration (default 30, max 730)
      --n-rollouts: Parallel rollouts for ensemble runs
      --seed: PRNG seed for reproducibility
      --snapshot-every: Intermediate output interval
    """
    from .abm import run_abm

    result = run_abm(aoi=aoi, year=year, month=month, seed=seed, days=days, n_rollouts=n_rollouts, output_dir=output_dir)
    typer.echo(f"ABM result: {result}")


@app.command()
def score(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
    tier: Tier = typer.Option(Tier.FAST, "--tier", help="Test tier: fast (10 scorers) or full (+LLM)"),
) -> None:
    """Run calibration scorers against ABM outputs.

    Compares simulated epidemic curves, seasonality, and spatial patterns
    against observed data to produce a composite score.

    Key parameters:
      --run-dir: Path to ABM output directory
      --tier: 'fast' (10 scorers, ~1s) or 'full' (10 scorers + LLM, ~30s)
    """
    from .scoring import run_calibration

    result = run_calibration(run_dir=run_dir, tier=tier.value)
    typer.echo(f"Scoring result: {result}")


@app.command()
def train(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM rollout outputs"),
    output_dir: Path = typer.Option(Path("runs/training"), "--output-dir", help="Model output directory"),
    epochs: int = typer.Option(50, "--epochs", help="Training epochs"),
    batch_size: int = typer.Option(16, "--batch-size", help="Batch size"),
    lr: float = typer.Option(1e-3, "--lr", help="Learning rate"),
) -> None:
    """Train the U-Net surrogate model.

    Trains a U-Net to predict ABM outcomes from environmental tensors,
    enabling fast inference without full ABM runs.

    Key parameters:
      --run-dir: ABM output directory (training data source)
      --epochs: Number of training epochs (default 50)
      --batch-size: Mini-batch size (default 16)
      --lr: Initial learning rate (default 1e-3)
    """
    from .training import train_unet

    best_dice = train_unet(run_dir=run_dir, output_dir=output_dir, epochs=epochs, batch_size=batch_size, lr=lr)
    typer.echo(f"Training complete. Best val_dice: {best_dice:.4f}")


@app.command()
def feedback(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
    baseline_dir: Path | None = typer.Option(None, "--baseline", help="Baseline for comparison"),
) -> None:
    """Generate feedback from calibration results.

    Produces a human-readable summary of where the simulation diverges
    from observed data, with optional baseline comparison.

    Key parameters:
      --run-dir: Path to scored ABM output directory
      --baseline: Optional baseline run directory for comparison
    """
    from .scoring import get_feedback, run_calibration

    scorecard = run_calibration(run_dir=run_dir)
    baseline = run_calibration(run_dir=baseline_dir) if baseline_dir else None
    fb = get_feedback(scorecard, baseline)
    typer.echo(fb)


@app.command()
def status(
    aoi: str = typer.Option(..., "--aoi", help="AOI slug"),
) -> None:
    """Show prediction metadata for an AOI."""
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
    """Start the SDSS FastAPI server."""
    import uvicorn

    from .server import app as fastapi_app

    typer.echo(f"Starting SDSS server on {host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


def main() -> None:
    app()
