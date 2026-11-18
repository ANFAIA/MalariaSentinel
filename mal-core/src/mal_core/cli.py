"""Typer CLI — command-line interface to the SDSS.

Pipeline order (each stage reads artefacts from the previous one):
    1. malariasim download --aoi {aoi} --datasets era5,chirps
    2. malariasim ingest --aoi {aoi} --year {year} --month {month}
    3. malariasim abm --aoi {aoi} --days 30
    4. malariasim score --run-dir {dir}
    5. malariasim train --run-dir {dir} --epochs 50
    6. malariasim predict --aoi {aoi} --scale {regional|national|continental} --year {year}

Standalone commands (no ordering required):
    malariasim feedback --run-dir {dir}
    malariasim status --aoi {aoi}
    malariasim serve --host {host} --port {port}
"""
from __future__ import annotations

import functools
from pathlib import Path

import typer
from typer.core import TyperCommand

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


# `--gif` must work both as `--gif <path>` and as a bare flag (default
# artifact name). Typer drops click's optional-value support (`is_flag=False`
# + `flag_value`), so the subcommand rewrites a valueless `--gif` into
# `--gif=<sentinel>` before click parses it; the sentinel then collapses back
# to "use the default path" in the command body.
_GIF_DEFAULT_SENTINEL = "__malariasim_gif_default__"


def _normalise_gif_args(args: list[str]) -> list[str]:
    """Rewrite a value-less ``--gif`` to ``--gif=<sentinel>``.

    Leaves ``--gif PATH`` and ``--gif=PATH`` untouched. A following token that
    starts with ``-`` counts as "no value given".
    """
    out: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--gif":
            nxt = args[i + 1] if i + 1 < len(args) else None
            if nxt is None or nxt.startswith("-"):
                out.append(f"--gif={_GIF_DEFAULT_SENTINEL}")
            else:
                out.extend(["--gif", nxt])
                i += 1
        else:
            out.append(arg)
        i += 1
    return out


class _GifAwareCommand(TyperCommand):
    """TyperCommand that accepts ``--gif`` with or without a value."""

    def parse_args(self, ctx, args):  # type: ignore[override]
        """Parse the command arguments, accepting ``--gif`` with or without a value."""
        return super().parse_args(ctx, _normalise_gif_args(list(args)))


def _validate_model_constants() -> None:
    """Gate every command on the single YAML validator (R2).

    One helper, applied through the ``_requires_model_constants``
    decorator: no command duplicates the check and ``--help`` stays
    side-effect free.
    """
    from .config_validation import SchemaError, resolve_path, validate_model_config

    path = resolve_path()
    try:
        validate_model_config(path)
    except SchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"model_constants: {path}", err=True)


def _requires_model_constants(fn):
    """Wrap a Typer command so the YAML is validated before it runs."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        """Validate the model constants, then run the wrapped command."""
        _validate_model_constants()
        return fn(*args, **kwargs)

    return wrapper


@app.command()
@_requires_model_constants
def predict(
    aoi: str | None = typer.Option(None, "--aoi", help="AOI slug (e.g. ghana)"),
    scale: Scale = typer.Option(Scale.REGIONAL, "--scale", help="Prediction scale"),
    year: int = typer.Option(2026, "--year", help="Simulation year"),
    month: int = typer.Option(1, "--month", help="Simulation month"),
    model: str = typer.Option("dummy", "--model", help="Model name from registry"),
    scenario_path: Path | None = typer.Option(
        None, "--scenario", "-s", help="Path to scenario YAML"
    ),
    rollout_dir: Path | None = typer.Option(
        None, "--rollout-dir", help="Optional path to directory with ABM rollout snapshots"
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
        rollout_dir=rollout_dir,
    )
    typer.echo(f"Prediction saved: {out}")


@app.command()
@_requires_model_constants
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
@_requires_model_constants
def ingest(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug"),
    year: int = typer.Option(2024, "--year", help="Year"),
    month: int = typer.Option(6, "--month", help="Month"),
    output_dir: Path = typer.Option(Path("runs/ingest"), "--output-dir"),
    data_dir: Path | None = typer.Option(None, "--data-dir", help="Downloaded AOI directory"),
    what: str = typer.Option("all", "--what", help="What to build: env, hosts, mobility, all"),
) -> None:
    """Build ABM-ready artifacts for an AOI.

    Builds environmental tensors, host density grids, and mobility matrices.
    Use --what to build a specific component.

    Key parameters:
      --what: env (daily env NC + habitat), hosts (host_static.nc),
              mobility (CSR OD matrices), or all (default)
    """
    from .ingest import build_env_tensor, build_host_dataset, build_mobility_dataset

    results = {}
    from mal_commonlib.aoi import AOI as _AOI
    aoi_obj = _AOI.from_slug(aoi) if isinstance(aoi, str) else aoi
    if what in ("env", "all"):
        chosen_data_dir = data_dir or output_dir
        result = build_env_tensor(aoi=aoi, year=year, month=month, output_dir=chosen_data_dir, data_root=chosen_data_dir.parent)
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


@app.command(cls=_GifAwareCommand)
@_requires_model_constants
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
    bbox: str | None = typer.Option(None, "--bbox", help="Custom AOI bbox 'lon_min,lat_min,lon_max,lat_max' (required for non-catalog AOI slugs)."),
    gif: str | None = typer.Option(None, "--gif", help="Render a native in-process GIF of the run (one frame per --gif-every days). Optional path: bare --gif writes <output-dir>/<aoi>_abm_seedNNNN.gif."),
    gif_every: int = typer.Option(1, "--gif-every", help="Emit one GIF frame every N simulated days."),
    gif_fps: int = typer.Option(6, "--gif-fps", help="GIF playback rate in frames per second."),
    gif_max_width: int = typer.Option(1280, "--gif-max-width", help="GIF canvas width in pixels (clamped to 640..2048; height = 0.60 × width)."),
    compile: bool = typer.Option(False, "--compile", "-c", help="Compile the C++ ABM engine (mal_abm_fast) from source."),
    clean: bool = typer.Option(False, "--clean", help="Clean build directory before compiling (used with --compile)."),
    worktree: Path | None = typer.Option(
        None,
        "--worktree",
        "-w",
        help="Path to gawt worktree (e.g. .gitagent/worktree) for isolated compile and run.",
    ),
    seeding_mode: str = typer.Option("random-viable", "--seeding-mode", help="Initial mosquito seeding mode: 'uniform' | 'random-viable' | 'explicit' | 'host-weighted'."),
    seed_adults_per_patch: int = typer.Option(30, "--seed-adults-per-patch", help="UNIFORM mode: adult mosquitoes seeded per candidate patch (explicit count; 30/270 reproduces the retired capacity-fraction mixing)."),
    seed_immatures_per_patch: int = typer.Option(270, "--seed-immatures-per-patch", help="UNIFORM mode: immatures (eggs+larvae+pupae) seeded per candidate patch."),
    host_seeding_radius_km: float = typer.Option(5.0, "--host-seeding-radius-km", help="HOST_WEIGHTED mode: radius (km) around each patch to weight nearby host abundance."),
    n_detections: int = typer.Option(3, "--n-detections", help="Number of patches to seed. RANDOM_VIABLE / HOST_WEIGHTED modes."),
    n_adults_per_detection: int = typer.Option(50, "--n-adults-per-detection", help="Adult mosquitoes per seeded patch."),
    n_larvae_per_detection: int = typer.Option(30, "--n-larvae-per-detection", help="Larvae per seeded patch."),
    detection_points: str = typer.Option("", "--detection-points", help="EXPLICIT mode: lat/lon points 'lat,lon;lat,lon;...' (e.g. Accra '5.6037,-0.1870')."),
    detection_radius_km: float = typer.Option(5.0, "--detection-radius-km", help="EXPLICIT mode: max snap distance (km) from each point to the nearest habitat patch."),
    enable_transmission: bool = typer.Option(False, "--enable-transmission", help="Enable spatial SEIR-SEI malaria transmission model (M7.4)."),
    transmission_snapshot_every: int = typer.Option(0, "--transmission-snapshot-every", help="Transmission snapshot interval in days (0=final only)."),
    human_seeding_mode: str = typer.Option("random-viable", "--human-seeding-mode", help="Human infection seeding mode: 'random-viable' | 'explicit' | 'uniform-legacy' | 'none'."),
    human_outbreak_day: int = typer.Option(0, "--human-outbreak-day", help="Day of simulation to trigger human outbreak (e.g. 60 for 2-month warm-up)."),
    human_outbreak_foci: int = typer.Option(3, "--human-outbreak-foci", help="Number of random foci for human outbreak."),
    human_outbreak_cases: float = typer.Option(50.0, "--human-outbreak-cases", help="Infectious human cases seeded per focus."),
    human_min_cell_pop: float = typer.Option(50.0, "--human-min-cell-pop", help="Minimum cell population to qualify as candidate focus."),
    human_foci_coords: str = typer.Option("", "--human-foci-coords", help="Explicit foci coordinates 'r1,c1:N1;r2,c2:N2'."),
    human_cluster_radius_km: float = typer.Option(0.0, "--human-cluster-radius-km", help="Concentrated-outbreak mode: ONE spatial cluster (core = max-pop viable cell or explicit coord), cases split ~ cell population within this radius. 0 = independent foci."),
    human_outbreak_min_density: float = typer.Option(0.0, "--human-outbreak-min-density", help="Adaptive trigger: outbreak waits until best viable cell reaches this many adult mosquitoes (individuals/cell; the retired normalized 0.5 ≈ 500 adults). 0 = exact day."),
    human_cluster_max_core_pop: float = typer.Option(0.0, "--human-cluster-max-core-pop", help="Cluster core population cap: denser cells are not cores (vectors dilute, R<<1). 0 = no cap."),
    initial_human_prevalence: float | None = typer.Option(None, "--initial-human-prevalence", help="Initial infectious fraction of human population (used in uniform-legacy mode). Default: model_constants.yaml transmission.initial_human_prevalence."),
    initial_vector_infected_frac: float | None = typer.Option(None, "--initial-vector-infected-frac", help="Initial infectious fraction of female mosquitoes. Default: model_constants.yaml transmission.initial_vector_infected_frac."),
    beta_hv: float | None = typer.Option(None, "--beta-hv", help="Human-to-vector transmission probability per bite. Default: model_constants.yaml transmission.beta_hv."),
    beta_vh: float | None = typer.Option(None, "--beta-vh", help="Vector-to-human transmission probability per bite. Default: model_constants.yaml transmission.beta_vh."),
    human_incubation_days: int | None = typer.Option(None, "--human-incubation-days", help="Human intrinsic incubation period in days. Default: model_constants.yaml transmission.human_incubation_days."),
    human_infectious_days: int | None = typer.Option(None, "--human-infectious-days", help="Human infectious duration in days. Default: model_constants.yaml transmission.human_infectious_days."),
    immunity_duration_days: int | None = typer.Option(None, "--immunity-duration-days", help="Duration of temporary human immunity in days. Default: model_constants.yaml transmission.human_immunity_days."),
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
      --gif: Native in-process animation GIF (one frame per --gif-every days)
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

    # The C++ engine needs an explicit bbox for AOI slugs it does not know.
    bbox_kwargs = {"bbox": bbox} if bbox else {}

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
        seeding_mode=seeding_mode,
        seed_adults_per_patch=seed_adults_per_patch,
        seed_immatures_per_patch=seed_immatures_per_patch,
        host_seeding_radius_km=host_seeding_radius_km,
        n_detections=n_detections,
        n_adults_per_detection=n_adults_per_detection,
        n_larvae_per_detection=n_larvae_per_detection,
        detection_points=detection_points or None,
        detection_radius_km=detection_radius_km,
        enable_transmission=enable_transmission,
        human_seeding_mode=human_seeding_mode,
        human_outbreak_day=human_outbreak_day,
        human_outbreak_foci=human_outbreak_foci,
        human_outbreak_cases=human_outbreak_cases,
        human_min_cell_pop=human_min_cell_pop,
        human_foci_coords=human_foci_coords,
        human_cluster_radius_km=human_cluster_radius_km,
        human_outbreak_min_density=human_outbreak_min_density,
        human_cluster_max_core_pop=human_cluster_max_core_pop,
        initial_human_prevalence=initial_human_prevalence,
        initial_vector_infected_frac=initial_vector_infected_frac,
        beta_hv=beta_hv,
        beta_vh=beta_vh,
        human_incubation_days=human_incubation_days,
        human_infectious_days=human_infectious_days,
        immunity_duration_days=immunity_duration_days,
        enable_immunity=enable_immunity,
        transmission_snapshot_every=transmission_snapshot_every,
        gif=("" if gif == _GIF_DEFAULT_SENTINEL else gif),
        gif_every=gif_every,
        gif_fps=gif_fps,
        gif_max_width=gif_max_width,
        **bbox_kwargs,
    )
    typer.echo(f"ABM result: {result}")

    rc = result.get("returncode")
    if rc not in (0, None):
        typer.echo(
            f"ABM engine failed (rc={rc}):\n{result.get('stderr', '')[-1500:]}",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command("score")
@_requires_model_constants
def score_cmd(
    run_dir: Path | None = typer.Option(None, "--run-dir", help="Directory with ABM outputs"),
    aoi: str | None = typer.Option(None, "--aoi", help="AOI slug (auto-detected from run metadata if omitted)"),
    only: str = typer.Option("", "--only", help="Comma-separated scorer names to run (e.g. d2,d15)"),
    skip: str = typer.Option("", "--skip", help="Comma-separated scorer names to exclude"),
    enable: str = typer.Option("", "--enable", help="Comma-separated MANUAL (AOI-dependent) scorers to activate, e.g. d16_suitability_auc,d25_occurrence_auc"),
    config: Path | None = typer.Option(None, "--config", help="Optional scorers YAML config"),
    list_scorers: bool = typer.Option(False, "--list", help="List registered scorers and exit"),
) -> None:
    """Score a completed ABM run and save scorecard.json inside the run dir.

    Runs every registered scorer against the run's artifacts (state COGs,
    cohort/aquatic JSONs), computes the composite (weighted geometric mean
    of biological + external-validation dimensions), reports binary gates
    apart, and writes scorecard.json into --run-dir.

    AOI-dependent scorers (occurrence AUC, urban ratio, case-data match)
    are MANUAL: they never run unless explicitly activated with --enable
    or enabled: true in a scoring YAML — they need per-AOI datasets that
    not every AOI has.

    Examples:
      malariasim score --run-dir runs/abm/2024-2025-seed0001
      malariasim score --run-dir runs/abm --only d2_survival,d15_persistence
      malariasim score --run-dir runs/abm --enable d25_occurrence_auc
      malariasim score --run-dir runs/abm --skip g24_urban_ratio --list
    """
    from .scoring import format_summary, list_scorers as ls, run_scoring

    if list_scorers:
        for row in ls():
            typer.echo(
                f"{row['kind']:9s} {row['name']:28s} w={row['weight']} "
                f"manual={row['manual']}  {row['description']}"
            )
        return

    if run_dir is None:
        typer.echo("Error: --run-dir is required (or pass --list)", err=True)
        raise typer.Exit(code=1)

    only_list = [s.strip() for s in only.split(",") if s.strip()] or None
    skip_list = [s.strip() for s in skip.split(",") if s.strip()] or None
    enable_list = [s.strip() for s in enable.split(",") if s.strip()] or None
    scorecard = run_scoring(
        run_dir=run_dir,
        aoi=aoi,
        config_path=config,
        only=only_list,
        skip=skip_list,
        enable=enable_list,
    )
    typer.echo(format_summary(scorecard))


@app.command("validate-detections")
@_requires_model_constants
def validate_detections(
    aoi: str = typer.Option(..., "--aoi", help="AOI slug (explicit; e.g. ghana)"),
    occurrence: Path | None = typer.Option(
        None, "--occurrence", help="Detection spots TSV (default: AOI occurrence dataset)"
    ),
    days: int = typer.Option(365, "--days", help="Simulation length (>= 365 recommended)"),
    year: int = typer.Option(2024, "--year", help="Simulation start year"),
    seed: int = typer.Option(1, "--seed", help="PRNG seed"),
    radius_km: float = typer.Option(5.0, "--radius-km", help="Seed snap + coverage radius (km)"),
    n_adults: int = typer.Option(500, "--n-adults-per-detection", help="Adults seeded per spot"),
    n_larvae: int = typer.Option(200, "--n-larvae-per-detection", help="Larvae seeded per spot"),
    snapshot_every: int = typer.Option(30, "--snapshot-every", help="Snapshot interval in days"),
    output_dir: Path = typer.Option(
        Path("runs/validate-detections"), "--output-dir", help="Where to place the run"
    ),
    compile: bool = typer.Option(False, "--compile", "-c", help="Compile the engine first"),
) -> None:
    """Launch-and-measure detection coverage validation (feeds D16).

    Seeds mosquitoes at the AOI's real detection spots (explicit seeding
    mode), runs the ABM for --days, then scores D16_detection_coverage:
    the fraction of spots whose surroundings (radius_km) hold simulated
    adults in the final state. This is the only validation that RUNS a
    simulation instead of scoring an existing run.

    Example:
      malariasim validate-detections --aoi ghana --days 365 --seed 1
    """
    from .scoring import format_summary, run_scoring
    from .scoring.scorers.base import load_occurrence_spots

    if occurrence is None:
        for pattern in (
            f"data/{aoi}/{aoi}_occurrence.txt",
            f"data/{aoi}_idit/occurrence.txt",
        ):
            p = Path(pattern)
            if p.exists():
                occurrence = p
                break
    if occurrence is None or not occurrence.exists():
        typer.echo(f"Error: occurrence dataset not found for AOI {aoi!r}", err=True)
        raise typer.Exit(code=1)

    lats, lons = load_occurrence_spots(occurrence)
    if len(lats) == 0:
        typer.echo("Error: no valid detection spots in occurrence dataset", err=True)
        raise typer.Exit(code=1)
    detection_points = ";".join(f"{la:.6f},{lo:.6f}" for la, lo in zip(lats, lons))
    typer.echo(f"Seeding {len(lats)} detection spots (radius {radius_km} km)...")

    if compile:
        from .abm import compile_abm

        success, message = compile_abm()
        if not success:
            typer.echo(f"Compilation failed:\n{message}", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Compilation successful: {message}")

    from .abm import run_abm_from_manifest

    run_dir = output_dir / f"{aoi}-{days}d-seed{seed:04d}"
    result = run_abm_from_manifest(
        aoi=aoi,
        year=year,
        month=1,
        seed=seed,
        days=days,
        n_rollouts=1,
        snapshot_every=snapshot_every,
        timeout=None,
        output_dir=run_dir,
        data_root=None,
        worktree=None,
        seeding_mode="explicit",
        detection_points=detection_points,
        detection_radius_km=radius_km,
        n_adults_per_detection=n_adults,
        n_larvae_per_detection=n_larvae,
    )
    typer.echo(f"Validation run complete: {result}")

    scorecard = run_scoring(
        run_dir=run_dir,
        aoi=aoi,
        enable=["D16_detection_coverage"],
    )
    typer.echo(format_summary(scorecard))


@app.command("validate-cases")
@_requires_model_constants
def validate_cases(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug (explicit; dataset-dependent, ghana-only score)"),
    start_year: int = typer.Option(2022, "--start-year", help="First simulation year (warm-up)"),
    n_years: int = typer.Option(2, "--n-years", help="Number of years to simulate (last year = contrast)"),
    seed: int = typer.Option(1, "--seed", help="PRNG seed"),
    warmup_months: int = typer.Option(12, "--warmup-months", help="Initial months discarded before the comparison"),
    seed_adults_per_patch: int = typer.Option(30, "--seed-adults-per-patch", help="UNIFORM seeding: adults per candidate patch (explicit count)"),
    seed_immatures_per_patch: int = typer.Option(270, "--seed-immatures-per-patch", help="UNIFORM seeding: immatures per candidate patch"),
    vector_infected_frac: float = typer.Option(1.0, "--vector-infected-frac", help="Initial infected fraction of the vector pool"),
    snapshot_every: int = typer.Option(30, "--snapshot-every", help="Snapshot interval in days"),
    output_dir: Path = typer.Option(Path("runs/validate-cases"), "--output-dir", help="Output root"),
    compile: bool = typer.Option(False, "--compile", "-c", help="Compile the engine first"),
    skip_download: bool = typer.Option(False, "--skip-download", help="Skip the auto download/ingest step"),
) -> None:
    """Launch-and-measure reported-cases validation (feeds D25).

    Runs the ABM with country-wide uniform mosquito seeding and the whole
    vector pool initially infected (--enable-transmission), for
    --n-years. The first --warmup-months are warm-up; the last full
    simulated year is compared against the DHIMS-II reported cases of
    the SAME calendar year (Ghana-only dataset, auto-downloaded).

    Example:
      malariasim validate-cases --aoi ghana --start-year 2022 --n-years 2
    """
    from .scoring import format_summary, run_scoring

    years = [start_year + i for i in range(n_years)]
    env_nc = _ensure_env_stack(aoi, years, skip=skip_download)
    typer.echo(f"Env stack ready: {env_nc}")

    if compile:
        from .abm import compile_abm

        success, message = compile_abm()
        if not success:
            typer.echo(f"Compilation failed:\n{message}", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Compilation successful: {message}")

    from .abm import run_abm_from_manifest

    run_dir = output_dir / f"{aoi}-{years[0]}-{years[-1]}-seed{seed:04d}"
    result = run_abm_from_manifest(
        aoi=aoi,
        year=start_year,
        month=1,
        days=n_years * 365,
        seed=seed,
        n_rollouts=1,
        snapshot_every=snapshot_every,
        timeout=None,
        output_dir=run_dir,
        data_root=None,
        worktree=None,
        seeding_mode="uniform",
        seed_adults_per_patch=seed_adults_per_patch,
        seed_immatures_per_patch=seed_immatures_per_patch,
        enable_transmission=True,
        human_seeding_mode="none",
        initial_vector_infected_frac=vector_infected_frac,
        env=str(env_nc),
    )
    rc = result.get("returncode")
    if rc not in (0, None):
        typer.echo(
            f"ABM engine failed (rc={rc}):\n{result.get('stderr','')[-1500:]}",
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(f"Validation run complete: {result['output_path']}")

    scorecard = run_scoring(
        run_dir=run_dir,
        aoi=aoi,
        enable=["D25_cases_ghana"],
        ctx_extras={"warmup_months": warmup_months},
    )
    typer.echo(format_summary(scorecard))


def _ensure_env_stack(aoi: str, years: list[int], skip: bool = False) -> Path:
    """Ensure the env NC covering ``years`` (and ABM inputs) exist.

    Downloads raw datasets via the plugin registry and builds the daily
    env NC + habitat/hosts/mobility artifacts when missing. Returns the
    env NC path.
    """
    from pathlib import Path as P
    from .download.manifest import resolve_dataset_file

    data_dir = P("data") / aoi
    y_min, y_max = min(years), max(years)
    # Manifest-first cache check: the env NC the manifest declares (any
    # declared entry whose period covers the years) is the cached artifact;
    # the constructed conventional name is only the pre-manifest fallback.
    env_nc = resolve_dataset_file(aoi, "env", year=y_min, data_dir=data_dir)
    if env_nc is None:
        env_nc = data_dir / f"{aoi}_regional_{y_min}_{y_max}_env.nc"
    if env_nc.exists():
        return env_nc
    if skip:
        raise FileNotFoundError(f"env NC missing and --skip-download set: {env_nc}")

    from .download import run_download
    from .ingest.daily_nc import build_daily_env_nc

    typer.echo(f"Auto-download: raw datasets for {y_min}-{y_max}...")
    # Only what build_daily_env_nc + the engine actually consume under
    # contract v3.0: rainfall (chirps daily), air temperature (era5),
    # water/wetland/built/crop/open fractions (jrc + dynamic world),
    # land_mask (coastline), hosts/mobility inputs
    # (worldpop, glw, wildlife — ghsl/buildings retained as independent
    # host-density consumers).
    run_download(
        aoi=aoi,
        datasets=["chirps", "era5"],
        outputs=["rainfall_daily", "air_temp_daily", "wind_6hourly"],
        years=years,
        months=None,
        output_dir=data_dir,
    )
    for dataset, outputs in (
        ("jrc_gsw", ["habitat_features"]),
        ("dynamic_world", ["class_fractions"]),
        ("worldpop", ["population"]),
        ("glw", ["cattle", "goats", "sheep", "pigs", "chickens"]),
        ("ghsl", ["urban_class"]),
        ("buildings", ["building_fraction"]),
        ("wildlife", ["wildlife_host_proxy"]),
        ("coastline", ["land_mask"]),
    ):
        run_download(aoi=aoi, datasets=[dataset], outputs=outputs, years=years, months=None, output_dir=data_dir)

    typer.echo("Building daily env NC...")
    info = build_daily_env_nc(aoi=aoi, data_dir=data_dir)
    built = P(str(info.get("env_path", env_nc)))
    if not env_nc.exists() and built.exists():
        env_nc = built
    if not env_nc.exists():
        raise FileNotFoundError(f"env NC build failed: {built}")

    _ensure_abm_inputs(aoi, data_dir)
    return env_nc


def _ensure_abm_inputs(aoi: str, data_dir: Path) -> None:
    """Ensure habitat patches, host grid and mobility matrices exist.

    Presence checks go through the catalog (manifest = single source of
    truth; identity keys from INGEST_ARTIFACTS). Production keeps writing
    the conventional names — register_existing/migration covers dirs that
    predate manifests.
    """
    from mal_commonlib.aoi import AOI
    from .download.catalog import INGEST_ARTIFACTS, resolve
    from .ingest import build_host_dataset, build_mobility_dataset

    habitat = resolve(
        aoi, INGEST_ARTIFACTS["habitat"].key, data_dir=data_dir
    )
    if habitat is None:
        # Not registered yet: build the env stack (registers env+habitat).
        from .ingest import build_env_tensor

        typer.echo("Building habitat patches (env builder)...")
        build_env_tensor(
            aoi=aoi,
            year=2024,
            month=1,
            output_dir=data_dir,
            data_root=data_dir.parent,
        )
        habitat = resolve(
            aoi, INGEST_ARTIFACTS["habitat"].key, data_dir=data_dir
        )
        if habitat is None:
            raise FileNotFoundError(
                "habitat patch gpkg build failed "
                f"(manifest key '{INGEST_ARTIFACTS['habitat'].key}')"
            )

    hosts = resolve(
        aoi, INGEST_ARTIFACTS["host_static"].key, data_dir=data_dir
    )
    if hosts is None:
        typer.echo("Building host grid (WorldPop + livestock)...")
        build_host_dataset(AOI.from_slug(aoi), output_dir=data_dir)
        hosts = resolve(
            aoi, INGEST_ARTIFACTS["host_static"].key, data_dir=data_dir
        )
        if hosts is None:
            raise FileNotFoundError(
                "host grid build failed "
                f"(manifest key '{INGEST_ARTIFACTS['host_static'].key}')"
            )

    day_csr = resolve(
        aoi, INGEST_ARTIFACTS["mobility_day"].key, data_dir=data_dir
    )
    night_csr = resolve(
        aoi, INGEST_ARTIFACTS["mobility_night"].key, data_dir=data_dir
    )
    if day_csr is None or night_csr is None:
        typer.echo("Building mobility matrices (this can take a while)...")
        build_mobility_dataset(
            hosts_path=hosts, output_dir=data_dir, aoi_slug=aoi
        )


@app.command()
@_requires_model_constants
def train(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM rollout outputs"),
    output_dir: Path = typer.Option(Path("runs/training"), "--output-dir", help="Model output directory"),
    epochs: int = typer.Option(50, "--epochs", help="Training epochs"),
    batch_size: int = typer.Option(16, "--batch-size", help="Batch size"),
    lr: float = typer.Option(1e-3, "--lr", help="Learning rate"),
    include_transmission: bool = typer.Option(True, "--include-transmission/--no-transmission", help="Include transmission state rasters in training data"),
    env_path: Path | None = typer.Option(None, "--env-path", help="Optional environmental NetCDF/GeoTIFF raster path"),
) -> None:
    """Train the U-Net surrogate model.

    Trains a U-Net to predict ABM outcomes from environmental tensors,
    enabling fast inference without full ABM runs.

    Key parameters:
      --run-dir: ABM output directory (training data source)
      --epochs: Number of training epochs (default 50)
      --batch-size: Mini-batch size (default 16)
      --lr: Initial learning rate (default 1e-3)
      --include-transmission: Include SEIR transmission states (default True)
      --env-path: Path to climate NetCDF/GeoTIFF raster
    """
    from .training import train_unet

    best_dice = train_unet(
        run_dir=run_dir,
        output_dir=output_dir,
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        include_transmission=include_transmission,
        env_path=env_path,
    )
    typer.echo(f"Training complete. Best val_dice: {best_dice:.4f}")


@app.command("datasets")
@_requires_model_constants
def datasets_cmd(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug"),
    missing_only: bool = typer.Option(False, "--missing", help="Show only rows not fully registered+on disk"),
) -> None:
    """Dataset catalog: loaders + ingest artifacts vs manifest vs disk.

    One row per known manifest key (download datasets derive from each
    loader's manifest_keys; ingest artifacts from INGEST_ARTIFACTS).
    'disk' shows whether the manifest-declared file actually exists.
    """
    from .download.catalog import catalog_status

    rows = catalog_status(aoi)
    typer.echo(
        f"{'kind':9s} {'key':30s} {'source':44s} {'abm':4s} "
        f"{'manifest':9s} {'disk':6s} file"
    )
    typer.echo("-" * 130)
    for r in rows:
        if missing_only and (r["in_manifest"] and r["on_disk"]):
            continue
        fname = Path(r["path"]).name if r["path"] else "-"
        typer.echo(
            f"{r['kind']:9s} {r['key']:30s} {r['source']:44s} "
            f"{'yes' if r['required_for_abm'] else '-':4s} "
            f"{'yes' if r['in_manifest'] else 'no':9s} "
            f"{'yes' if r['on_disk'] else 'no':6s} {fname}"
        )


@app.command()
@_requires_model_constants
def feedback(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
    baseline_dir: Path | None = typer.Option(None, "--baseline", help="Baseline for comparison"),
) -> None:
    """Generate feedback from scoring results.

    Produces a human-readable summary of the weakest dimensions, failed
    gates, and optional baseline comparison.

    Key parameters:
      --run-dir: Path to a scored ABM output directory
      --baseline: Optional baseline run directory for comparison
    """
    from .scoring import get_feedback, run_scoring

    scorecard = run_scoring(run_dir=run_dir)
    baseline = run_scoring(run_dir=baseline_dir) if baseline_dir else None
    fb = get_feedback(scorecard, baseline)
    typer.echo(fb)


@app.command()
@_requires_model_constants
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
@_requires_model_constants
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="Bind port"),
) -> None:
    """Start the SDSS FastAPI server."""
    import uvicorn

    from .server import app as fastapi_app

    typer.echo(f"Starting SDSS server on {host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


# --- papers: paper-corpus tool (docs/plans/in-process/papers-corpus.md, §6.5) ---
# Commands import mal_core.papers lazily; a bad manifest or config exits with code 2.

papers_app = typer.Typer(
    name="papers",
    help="Paper corpus: fetch PDFs, extract with docling, generate REFERENCES.md, check the assertions.",
    no_args_is_help=True,
)
app.add_typer(papers_app, name="papers")

_PAPERS_ROOT_HELP = "Corpus root (default: output_root in mal-core/config/papers.yaml)"


def _papers_context(papers_root: Path | None):
    """(config, corpus root, manifest). Exits with code 2 on a bad config or manifest."""
    from .papers.config import load_config
    from .papers.manifest import ManifestError, load_manifest

    try:
        cfg = load_config()
        root = papers_root or cfg.papers_root()
        return cfg, root, load_manifest(root / "manifest.json")
    except (ManifestError, ValueError) as exc:
        typer.echo(f"papers: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@papers_app.command("fetch")
def papers_fetch(
    theme: str | None = typer.Option(None, "--theme", help="Only this theme folder"),
    paper_id: str | None = typer.Option(None, "--id", help="Only this manifest id"),
    force: bool = typer.Option(False, "--force", help="Re-download even if the PDF is present"),
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
) -> None:
    """Download obtainable PDFs (Crossref -> Unpaywall -> Europe PMC).

    Unobtainable papers are recorded as pending_* in their provenance.yaml and
    the run continues. The exit code stays 0 for them.
    """
    from collections import Counter

    from .papers.fetch import fetch_entry, urllib_downloader
    from .papers.resolve import iter_candidates, urllib_json_getter, user_agent

    cfg, root, manifest = _papers_context(papers_root)
    ua = user_agent(cfg.unpaywall_email)
    get_json = urllib_json_getter(user_agent_value=ua)
    downloader = urllib_downloader(user_agent_value=ua)
    counts: Counter[str] = Counter()
    for entry in manifest.select(theme=theme, paper_id=paper_id):
        attempts: list = []
        candidates = (
            iter_candidates(entry.doi, get_json=get_json, email=cfg.unpaywall_email, attempts=attempts)
            if entry.doi
            else ()
        )
        result = fetch_entry(entry, root, candidates=candidates, downloader=downloader, attempts=attempts, force=force)
        counts[result.observed_status] += 1
        typer.echo(f"{entry.id}  {result.observed_status}")
    typer.echo("fetch summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


@papers_app.command("rescue-list")
def papers_rescue_list(
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
    paper_id: str | None = typer.Option(None, "--id", help="Only this manifest id"),
) -> None:
    """JSON list of pending_paywalled papers that have an open-licence candidate URL.

    Input for the papers-rescue agent. Closed-access papers are never listed.
    """
    import json

    from .papers.resolve import urllib_json_getter, user_agent
    from .papers.rescue import rescue_candidates

    cfg, root, manifest = _papers_context(papers_root)
    get_json = urllib_json_getter(user_agent_value=user_agent(cfg.unpaywall_email))
    entries = manifest.select(paper_id=paper_id) if paper_id else manifest.entries
    items = rescue_candidates(manifest, root, get_json=get_json, email=cfg.unpaywall_email, entries=entries)
    payload = [
        {
            "id": item.entry.id,
            "theme": item.entry.theme,
            "slug": item.entry.slug,
            "doi": item.entry.doi,
            "pdf_sha256": item.entry.pdf_sha256,
            "candidates": [
                {"resolver": c.resolver, "url": c.url, "licence": c.licence} for c in item.candidates
            ],
        }
        for item in items
    ]
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@papers_app.command("adopt")
def papers_adopt(
    paper_id: str = typer.Option(..., "--id", help="Manifest id"),
    pdf_file: Path = typer.Option(..., "--file", help="PDF obtained by the rescue agent"),
    source_url: str = typer.Option(..., "--source-url", help="URL the PDF was obtained from"),
    licence: str = typer.Option(..., "--licence", help="Open licence URL or name, as observed"),
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
) -> None:
    """Record a rescued PDF after the same checks as fetch. Refuses invalid input untouched."""
    from .papers.rescue import adopt_pdf

    _cfg, root, manifest = _papers_context(papers_root)
    try:
        entry = manifest.get(paper_id)
        result = adopt_pdf(entry, root, pdf_file, source_url=source_url, licence=licence)
    except (KeyError, ValueError) as exc:
        typer.echo(f"papers adopt: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"{entry.id}  {result.observed_status}  {result.pdf_path or ''}".rstrip())
    if result.observed_status != "ok":
        raise typer.Exit(code=1)


@papers_app.command("extract")
def papers_extract(
    theme: str | None = typer.Option(None, "--theme", help="Only this theme folder"),
    paper_id: str | None = typer.Option(None, "--id", help="Only this manifest id"),
    device: str | None = typer.Option(None, "--device", help="cpu (default, from config) or mps (opt-in)"),
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
) -> None:
    """Convert each downloaded PDF to Markdown with docling (--tables --ocr, no picture description)."""
    import shutil

    from .papers.extract import extract_entry, validate_device

    cfg, root, manifest = _papers_context(papers_root)
    try:
        dev = validate_device(device or cfg.device)
    except ValueError as exc:
        typer.echo(f"papers: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    if shutil.which("docling") is None:
        typer.echo("papers: docling not found on PATH; install the group: uv sync --package mal-core --group papers", err=True)
        raise typer.Exit(code=2)
    for entry in manifest.select(theme=theme, paper_id=paper_id):
        result = extract_entry(entry, root, device=dev)
        typer.echo(f"{entry.id}  {result.status}  {result.detail}".rstrip())


@papers_app.command("generate")
def papers_generate(
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
    out: Path | None = typer.Option(None, "--out", help="Output file (default: <corpus root>/REFERENCES.md)"),
    check: bool = typer.Option(False, "--check", help="Do not write; exit 1 if the file differs from the manifest"),
) -> None:
    """Render REFERENCES.md from the manifest (deterministic; drift gate with --check)."""
    from .papers.generate import is_up_to_date, write_references

    _cfg, root, manifest = _papers_context(papers_root)
    target = out or root / "REFERENCES.md"
    if check:
        if is_up_to_date(manifest, target):
            typer.echo(f"{target}: up to date")
            return
        typer.echo(f"{target}: differs from the manifest; run without --check to regenerate", err=True)
        raise typer.Exit(code=1)
    changed = write_references(manifest, target)
    typer.echo(f"{target}: {'written' if changed else 'unchanged'}")


@papers_app.command("check")
def papers_check(
    papers_root: Path | None = typer.Option(None, "--papers-root", help=_PAPERS_ROOT_HELP),
    resolve_dois: bool = typer.Option(False, "--resolve-dois", help="Resolve every DOI at doi.org (network; local only)"),
) -> None:
    """Run the assertions of plan §7 (a: DOIs, b: doi: tokens, c: sha256, d: tracked files)."""
    from .papers.check import git_tracked_files, read_documents, run_checks
    from .papers.config import REPO_ROOT

    _cfg, root, manifest = _papers_context(papers_root)
    try:
        prefix = root.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        typer.echo("papers check: the corpus root must be inside the repository", err=True)
        raise typer.Exit(code=2) from exc

    tracked = git_tracked_files(REPO_ROOT)

    def size_of(rel: str) -> int:
        path = REPO_ROOT / rel
        return path.stat().st_size if path.is_file() else 0

    report = run_checks(
        manifest,
        papers_root=root,
        prefix=prefix,
        documents=read_documents(REPO_ROOT, tracked),
        tracked=tracked,
        size_of=size_of,
        resolve=resolve_dois,
    )
    for line in report.failures:
        typer.echo(f"FAIL  {line}")
    for line in report.warnings:
        typer.echo(f"WARN  {line}")
    for line in report.notes:
        typer.echo(f"NOTE  {line}")
    verdict = "PASS" if report.ok else "FAIL"
    typer.echo(f"{verdict}: {len(report.failures)} failure(s), {len(report.warnings)} warning(s)")
    if not report.ok:
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point of the ``malariasim`` console script: runs the Typer application."""
    app()
