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
    """Legacy tier choice (calibration pytest harness)."""

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
    debug: bool = typer.Option(False, "--debug", help="Post-run debug visualisation: hosts-vs-vectors overlay GIF (humans green, livestock brown, mosquitoes blue, I_V red)."),
    compile: bool = typer.Option(False, "--compile", "-c", help="Compile the C++ ABM engine (mal_abm_fast) from source."),
    clean: bool = typer.Option(False, "--clean", help="Clean build directory before compiling (used with --compile)."),
    worktree: Path | None = typer.Option(
        None,
        "--worktree",
        "-w",
        help="Path to gawt worktree (e.g. .gitagent/worktree) for isolated compile and run.",
    ),
    seeding_mode: str = typer.Option("random-viable", "--seeding-mode", help="Initial mosquito seeding mode: 'uniform' | 'random-viable' | 'explicit' | 'host-weighted'."),
    init_frac: float = typer.Option(0.30, "--init-frac", help="UNIFORM mode: fraction of K seeded per patch (0.0-1.0). Higher = faster vector warm-up, same equilibrium."),
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
    human_outbreak_min_density: float = typer.Option(0.0, "--human-outbreak-min-density", help="Adaptive trigger: outbreak waits until best viable cell reaches this normalized mosquito density (agents/K_MAX; 0.1 ~ 100 females). 0 = exact day."),
    human_cluster_max_core_pop: float = typer.Option(0.0, "--human-cluster-max-core-pop", help="Cluster core population cap: denser cells are not cores (vectors dilute, R<<1). 0 = no cap."),
    initial_human_prevalence: float = typer.Option(0.05, "--initial-human-prevalence", help="Initial infectious fraction of human population (used in uniform-legacy mode)."),
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
        seeding_mode=seeding_mode,
        init_frac=init_frac,
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
    )
    typer.echo(f"ABM result: {result}")

    if gif:
        _render_animation(
            aoi=aoi,
            seed=seed,
            output_dir=output_dir,
            cohort_log=cohort_log,
        enable_transmission=enable_transmission,
        transmission_snapshot_every=transmission_snapshot_every,
        )

    if debug:
        from .abm.scripts.overlay_hosts import render_overlay
        try:
            render_overlay(output_dir, aoi, output_dir / "overlay_hosts.gif")
        except Exception as e:  # noqa: BLE001 — debug aid must never fail the run
            typer.echo(f"overlay debug GIF failed (run unaffected): {e}")


def _render_animation(
    aoi: str,
    seed: int,
    output_dir: Path,
    cohort_log: Path | None,
    enable_transmission: bool = False,
) -> None:
    """Generate animation GIFs for an ABM run (used by --gif)."""
    import shutil
    from .abm.scripts.visualize_state import main as visualize_vectors
    from .abm.scripts.visualize_transmission import main as visualize_trans

    run_dir = Path(output_dir)
    vector_gif = run_dir / f"{aoi}_abm_seed{seed:04d}_vectors.gif"
    default_gif = run_dir / f"{aoi}_abm_seed{seed:04d}.gif"
    cohort_path = cohort_log or run_dir / f"{aoi}_abm_seed{seed:04d}_cohort.json"

    # 1. Vector Dynamics GIF
    argv_v = ["--run-dir", str(run_dir), "--output", str(vector_gif)]
    if cohort_path.exists():
        argv_v += ["--cohort-log", str(cohort_path)]
    try:
        visualize_vectors(argv_v)
        if vector_gif.exists():
            shutil.copyfile(vector_gif, default_gif)
        typer.echo(f"Vector animation saved: {vector_gif}")
    except SystemExit as e:
        typer.echo(f"Vector animation failed (exit {e.code}): no state snapshots?", err=True)

    # 2. Transmission Dynamics GIF (if transmission was enabled or transmission rasters exist)
    trans_files = list(run_dir.glob("*transmission*.tif"))
    if enable_transmission or len(trans_files) > 0:
        trans_gif = run_dir / f"{aoi}_abm_seed{seed:04d}_transmission.gif"
        argv_t = ["--run-dir", str(run_dir), "--output", str(trans_gif)]
        try:
            visualize_trans(argv_t)
            typer.echo(f"Transmission animation saved: {trans_gif}")
        except SystemExit as e:
            typer.echo(f"Transmission animation failed (exit {e.code}): no transmission snapshots?", err=True)


@app.command("score")
def score_cmd(
    run_dir: Path = typer.Option(..., "--run-dir", help="Directory with ABM outputs"),
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
def validate_cases(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug (explicit; dataset-dependent, ghana-only score)"),
    start_year: int = typer.Option(2022, "--start-year", help="First simulation year (warm-up)"),
    n_years: int = typer.Option(2, "--n-years", help="Number of years to simulate (last year = contrast)"),
    seed: int = typer.Option(1, "--seed", help="PRNG seed"),
    warmup_months: int = typer.Option(12, "--warmup-months", help="Initial months discarded before the comparison"),
    init_frac: float = typer.Option(0.30, "--init-frac", help="UNIFORM seeding: fraction of K seeded per patch"),
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
        init_frac=init_frac,
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

    data_dir = P("data") / aoi
    y_min, y_max = min(years), max(years)
    env_nc = data_dir / f"{aoi}_regional_{y_min}_{y_max}_env.nc"
    if env_nc.exists():
        return env_nc
    if skip:
        raise FileNotFoundError(f"env NC missing and --skip-download set: {env_nc}")

    from .download import run_download
    from .ingest.daily_nc import build_daily_env_nc

    typer.echo(f"Auto-download: raw datasets for {y_min}-{y_max}...")
    # Only what build_daily_env_nc + the engine actually consume:
    # rainfall (chirps daily), water_temp + wind (era5), ndvi (modis),
    # water_frac (jrc), twi/k_capacity (dem), land_mask (coastline),
    # hosts/mobility inputs (worldpop, glw, ghsl, buildings, wildlife).
    run_download(
        aoi=aoi,
        datasets=["chirps", "era5", "modis"],
        outputs=["rainfall_daily", "water_temp", "wind_6hourly", "ndvi"],
        years=years,
        months=None,
        output_dir=data_dir,
    )
    for dataset, outputs in (
        ("jrc_gsw", ["water_occurrence"]),
        ("dem", ["elevation"]),
        ("worldpop", ["population"]),
        ("glw", ["cattle", "goats", "sheep", "pigs", "chickens"]),
        ("ghsl", ["urban_class"]),
        ("buildings", ["building_fraction"]),
        ("wildlife", ["wildlife_host_proxy"]),
        ("coastline", ["land_mask"]),
    ):
        run_download(aoi=aoi, datasets=[dataset], outputs=outputs, years=None, months=None, output_dir=data_dir)

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
    """Ensure habitat patches, host grid and mobility matrices exist."""
    from mal_commonlib.aoi import AOI
    from .ingest import build_host_dataset, build_mobility_dataset

    habitat = data_dir / f"{aoi}_habitat_patches.gpkg"
    if not habitat.exists():
        from .ingest import build_env_tensor

        typer.echo("Building habitat patches (env builder)...")
        build_env_tensor(
            aoi=aoi,
            year=2024,
            month=1,
            output_dir=data_dir,
            data_root=data_dir.parent,
        )
        built = data_dir / f"{aoi}_regional_2024_01_habitat_patches.gpkg"
        if not habitat.exists():
            if built.exists():
                built.replace(habitat)
            else:
                raise FileNotFoundError("habitat patch gpkg build failed")

    hosts = data_dir / f"{aoi}_host_static.nc"
    if not hosts.exists():
        typer.echo("Building host grid (WorldPop + livestock)...")
        build_host_dataset(AOI.from_slug(aoi), output_dir=data_dir)

    csr = list(data_dir.glob(f"{aoi}_mobility_*.csr"))
    if len(csr) < 2:
        typer.echo("Building mobility matrices (this can take a while)...")
        build_mobility_dataset(
            hosts_path=hosts, output_dir=data_dir, aoi_slug=aoi
        )


@app.command()
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


@app.command()
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
