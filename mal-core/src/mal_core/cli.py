"""Typer CLI — command-line interface to the SDSS.

Pipeline order (each stage reads artefacts from the previous one):
    1. malariasim download --aoi {aoi} --datasets era5,chirps
    2. malariasim ingest --aoi {aoi} --year {year} --month {month}
    3. malariasim abm --aoi {aoi} --days 30
    4. malariasim score --run-dir {dir} --tier fast
    5. malariasim train --run-dir {dir} --epochs 50
    6. malariasim predict --aoi {aoi} --scale {regional|national|continental} --year {year}

Standalone commands (no ordering required):
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

app = typer.Typer(
    name="malariasim",
    help="MalariaSentinel SDSS CLI\n\n"
         "Pipeline order: download → ingest → abm → score → train → predict\n"
         "Each stage reads artefacts written by the previous one.",
    no_args_is_help=True,
)


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
def download(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug"),
    datasets: str = typer.Option("", "--datasets", help="Comma-separated dataset names (empty = all registered)"),
    outputs: str = typer.Option("", "--outputs", help="Comma-separated output names (empty = all)"),
    years: str = typer.Option("", "--years", help="Comma-separated years"),
    months: str = typer.Option("", "--months", help="Comma-separated months"),
    output_dir: Path = typer.Option(Path("data"), "--output-dir", help="Output root directory"),
) -> None:
    """Download datasets for an AOI via the plugin registry.

    Auto-discovers all registered downloaders and invokes them.
    Updates data/<aoi>/manifest.json after each successful download.

    Examples:
      malariasim download --aoi ghana --datasets era5
      malariasim download --aoi ghana --datasets era5 --outputs wind_6hourly --years 2024,2025
      malariasim download --aoi ghana --all
    """
    from .download import run_download

    ds_list = [s.strip() for s in datasets.split(",") if s.strip()] if datasets else None
    out_list = [s.strip() for s in outputs.split(",") if s.strip()] if outputs else None
    year_list = [int(y.strip()) for y in years.split(",") if y.strip()] if years else None
    month_list = [int(m.strip()) for m in months.split(",") if m.strip()] if months else None

    result = run_download(
        aoi=aoi,
        datasets=ds_list,
        outputs=out_list,
        years=year_list,
        months=month_list,
        output_dir=output_dir / aoi,
    )
    for name, info in result.items():
        status = info.get("status", "unknown")
        typer.echo(f"  {name}: {status}")
    typer.echo(f"Download complete: {len(result)} datasets processed")


@app.command()
def ingest(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug"),
    year: int = typer.Option(2024, "--year", help="Year"),
    month: int = typer.Option(6, "--month", help="Month"),
    output_dir: Path = typer.Option(Path("runs/ingest"), "--output-dir"),
    data_dir: Path | None = typer.Option(None, "--data-dir", help="Downloaded AOI directory"),
    scale: str = typer.Option("regional", "--scale"),
    what: str = typer.Option("all", "--what", help="What to build: env, hosts, mobility, all"),
) -> None:
    """Build ABM-ready artifacts for an AOI.

    Builds environmental tensors, host density grids, and mobility matrices.
    Use --what to build a specific component.

    Key parameters:
      --what: env (4-band tensor + habitat), hosts (host_static.nc),
              mobility (CSR OD matrices), or all (default)
    """
    from .ingest import build_env_tensor, build_host_dataset, build_mobility_dataset

    results = {}
    from mal_commonlib.aoi import AOI as _AOI
    aoi_obj = _AOI.from_slug(aoi) if isinstance(aoi, str) else aoi
    if what in ("env", "all"):
        chosen_data_dir = data_dir or output_dir
        result = build_env_tensor(aoi=aoi, year=year, month=month, output_dir=chosen_data_dir, scale=scale, data_root=chosen_data_dir.parent)
        results["env"] = result
    if what in ("hosts", "all"):
        result = build_host_dataset(aoi=aoi_obj, output_dir=output_dir)
        results["hosts"] = result
    if what in ("mobility", "all"):
        from pathlib import Path as P
        hosts_path = output_dir / f"{aoi}_host_static.nc"
        if not hosts_path.exists():
            hosts_path = P("data") / aoi / f"{aoi}_host_static.nc"
        if hosts_path.exists():
            mobility_out = P("data") / aoi
            result = build_mobility_dataset(hosts_path=hosts_path, output_dir=mobility_out, aoi_slug=aoi)
            results["mobility"] = result
        else:
            typer.echo(f"Warning: host_static.nc not found, skipping mobility build", err=True)

    typer.echo(f"Ingest results: {list(results.keys())}")


@app.command()
def abm(
    aoi: str | None = typer.Option(None, "--aoi", help="AOI slug (e.g. ghana). Required for simulation."),
    year: int = typer.Option(2024, "--year", help="Simulation start year."),
    month: int = typer.Option(1, "--month", help="Simulation start month."),
    seed: int = typer.Option(1, "--seed", help="PRNG seed for reproducibility."),
    days: int = typer.Option(30, "--days", help="Simulation duration in days."),
    n_rollouts: int = typer.Option(1, "--n-rollouts", help="Parallel rollouts for ensemble runs."),
    snapshot_every: int = typer.Option(1, "--snapshot-every", help="Snapshot interval in days (0=final only)."),
    cohort_log: Path | None = typer.Option(None, "--cohort-log", help="Daily cohort JSON path."),
    timeout: int | None = typer.Option(None, "--timeout", help="Optional subprocess timeout in seconds (default: None)."),
    output_dir: Path = typer.Option(Path("runs/abm"), "--output-dir", help="Output directory for simulation results."),
    data_root: Path | None = typer.Option(None, "--data-root", help="Root containing AOI manifest."),
    gif: bool = typer.Option(False, "--gif", help="Auto-generate an animation GIF after the run."),
    compile: bool = typer.Option(False, "--compile", "-c", help="Compile the C++ ABM engine (mal_abm_fast) from source."),
    clean: bool = typer.Option(False, "--clean", help="Clean build directory before compiling (used with --compile)."),
    worktree: Path | None = typer.Option(
        None,
        "--worktree",
        "-w",
        help="Path to gawt worktree (e.g. .gitagent/worktree) for isolated compile and run.",
    ),
    enable_transmission: bool = typer.Option(False, "--enable-transmission", help="Enable spatial SEIR-SEI malaria transmission model (M7.4)."),
    initial_human_prevalence: float = typer.Option(0.05, "--initial-human-prevalence", help="Initial infectious fraction of human population."),
    initial_vector_infected_frac: float = typer.Option(0.0, "--initial-vector-infected-frac", help="Initial infectious fraction of female mosquitoes."),
    beta_hv: float = typer.Option(0.40, "--beta-hv", help="Human-to-vector transmission probability per bite."),
    beta_vh: float = typer.Option(0.50, "--beta-vh", help="Vector-to-human transmission probability per bite."),
    human_incubation_days: int = typer.Option(12, "--human-incubation-days", help="Human intrinsic incubation period in days."),
    human_infectious_days: int = typer.Option(20, "--human-infectious-days", help="Human infectious duration in days."),
    immunity_duration_days: int = typer.Option(180, "--immunity-duration-days", help="Duration of temporary human immunity in days."),
    enable_immunity: bool = typer.Option(False, "--enable-immunity", help="Enable temporary human immunity waning."),
) -> None:
    """Run the agent-based malaria simulation or compile the C++ engine.

    Simulates Anopheles gambiae population dynamics, dispersal,
    and transmission potential using the mal_abm_fast C++ engine.

    Compilation:
      malariasim abm --compile                      # Compile main C++ engine
      malariasim abm --compile --clean              # Clean recompile from scratch
      malariasim abm --compile --worktree <path>    # Compile inside a gawt worktree
      malariasim abm --compile --aoi ghana          # Compile then run simulation

    Worktree isolation:
      malariasim abm --worktree .gitagent/worktree --aoi ghana --days 30

    Simulation parameters:
      --aoi: AOI slug (e.g. ghana; required when not compiling only)
      --days: One continuous simulation (default 30, max 731; 2024+2025 = 731)
      --n-rollouts: Parallel rollouts for ensemble runs
      --seed: PRNG seed for reproducibility
      --snapshot-every: Intermediate output interval
      --cohort-log: Daily eggs/larvae/pupae/adult statistics JSON
      --gif: Auto-generate an animation GIF after the run
      --worktree: Path to gawt worktree for isolated execution

    Use one invocation for multi-year runs. Splitting by month loses
    population, aquatic cohort, and engine state.
    """
    if compile:
        from .abm import compile_abm

        wt_desc = f" in worktree {worktree}" if worktree else ""
        typer.echo(f"Compiling C++ ABM engine (mal_abm_fast){wt_desc}...")
        success, message = compile_abm(worktree=worktree, clean=clean)
        if not success:
            typer.echo(f"Compilation failed:\n{message}", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Compilation successful: {message}")
        if not aoi:
            return

    if not aoi:
        typer.echo(
            "Error: Missing option '--aoi'. Specify --aoi <slug> to run simulation, "
            "or pass --compile to build the engine.",
            err=True,
        )
        raise typer.Exit(code=1)

    from .abm import run_abm_from_manifest

    result = run_abm_from_manifest(
        aoi=aoi,
        year=year,
        month=month,
        seed=seed,
        days=days,
        n_rollouts=n_rollouts,
        snapshot_every=snapshot_every,
        cohort_log=cohort_log,
        timeout=timeout,
        output_dir=output_dir,
        data_root=data_root,
        worktree=worktree,
        enable_transmission=enable_transmission,
        initial_human_prevalence=initial_human_prevalence,
        initial_vector_infected_frac=initial_vector_infected_frac,
        beta_hv=beta_hv,
        beta_vh=beta_vh,
        human_incubation_days=human_incubation_days,
        human_infectious_days=human_infectious_days,
        immunity_duration_days=immunity_duration_days,
        enable_immunity=enable_immunity,
    )
    typer.echo(f"ABM result: {result}")

    if gif:
        _render_animation(aoi=aoi, seed=seed, output_dir=output_dir, cohort_log=cohort_log)


def _render_animation(
    aoi: str,
    seed: int,
    output_dir: Path,
    cohort_log: Path | None,
) -> None:
    """Generate the animation GIF for an ABM run (used by --gif)."""
    from .abm.scripts.visualize_state import main as visualize_main

    run_dir = Path(output_dir)
    gif_path = run_dir / f"{aoi}_abm_seed{seed:04d}.gif"
    cohort_path = cohort_log or run_dir / f"{aoi}_abm_seed{seed:04d}_cohort.json"
    argv = ["--run-dir", str(run_dir), "--output", str(gif_path)]
    if cohort_path.exists():
        argv += ["--cohort-log", str(cohort_path)]
    try:
        visualize_main(argv)
        typer.echo(f"Animation saved: {gif_path}")
    except SystemExit as e:
        typer.echo(f"Animation failed (exit {e.code}): no state_day*.tif snapshots?", err=True)


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
