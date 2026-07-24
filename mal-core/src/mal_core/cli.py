"""Typer CLI — command-line interface to the SDSS.

Commands:
    malariasim predict --aoi {aoi} --scale {regional|national|continental} --year {year}
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
