"""Pipeline orchestrator — runs the full SDSS pipeline end-to-end."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .stages import Stage

def run_stage(stage: Stage, aoi: str, year: int, month: int, output_dir: Path, seed: int = 1, days: int = 30, n_rollouts: int = 1, stage_flags: dict[str, Any] | None = None, **stage_flags_raw) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    extra = dict(stage_flags_raw)
    if stage_flags:
        # _global flags apply to all stages; stage-specific flags override
        extra.update(stage_flags.get("_global", {}))
        extra.update(stage_flags.get(stage.value, {}))
    if stage == Stage.DOWNLOAD:
        from mal_core.download import run_download
        ds = extra.pop("datasets", "")
        datasets = [s.strip() for s in ds.split(",") if s.strip()] if ds else None
        os = extra.pop("outputs", "")
        out_list = [s.strip() for s in os.split(",") if s.strip()] if os else None
        ys = extra.pop("years", "")
        years = [int(y.strip()) for y in ys.split(",") if y.strip()] if ys else None
        # Fix: fall back to year/month pipeline params when years/months not provided
        if not years and year is not None:
            years = [year]
        ms = extra.pop("months", "")
        months = [m.strip() for m in ms.split(",") if m.strip()] if ms else None
        if not months and month is not None:
            months = [str(month)]
        output_dir = output_dir / "download"
        output_dir.mkdir(parents=True, exist_ok=True)
        return run_download(aoi=aoi, datasets=datasets, outputs=out_list, years=years, months=months, output_dir=output_dir, **extra)
    elif stage == Stage.INGEST:
        from mal_core.ingest import build_env_tensor
        return build_env_tensor(aoi=aoi, year=year, month=month, output_dir=output_dir / "ingest", **extra)
    elif stage == Stage.BUILD_HOSTS:
        from mal_core.ingest.hosts import build_host_dataset
        return build_host_dataset(aoi=aoi, output_dir=output_dir / "hosts", **extra)
    elif stage == Stage.BUILD_MOBILITY:
        from mal_core.ingest.mobility import build_mobility_dataset
        hosts_path = output_dir / "hosts" / f"{aoi}_host_static.nc"
        if not hosts_path.exists():
            hosts_path = output_dir / "abm" / "hosts" / f"{aoi}_host_static.nc"
        return build_mobility_dataset(aoi_slug=aoi, hosts_path=hosts_path, output_dir=output_dir / "mobility", **extra)
    elif stage == Stage.ABM:
        from mal_core.abm.wrapper import run_abm_from_manifest
        return run_abm_from_manifest(aoi=aoi, year=year, month=month, days=days, seed=seed, n_rollouts=n_rollouts, output_dir=output_dir / "abm", **extra)
    elif stage == Stage.SCORING:
        from mal_core.scoring import run_calibration
        return run_calibration(run_dir=output_dir / "abm", output_dir=output_dir / "scoring", **extra)
    elif stage == Stage.TRAINING:
        from mal_core.training import train_unet
        return {"best_dice": train_unet(run_dir=output_dir / "abm", output_dir=output_dir / "training", **extra)}
    elif stage == Stage.PREDICTION:
        from mal_core.prediction import run_prediction
        from mal_commonlib.aoi import Scale
        out = run_prediction(aoi_slug=aoi, scale=Scale.REGIONAL, year=year, month=month, output_dir=output_dir / "prediction", **extra)
        return {"prediction_path": str(out)}
    else:
        raise ValueError(f"Unknown stage: {stage}")

def run_pipeline(aoi: str, year: int, month: int, seed: int = 1, days: int = 30, n_rollouts: int = 1, stages: list[Stage] | None = None, output_dir: Path = Path("runs/pipeline"), resume: bool = True, stage_flags: dict[str, Any] | None = None, **stage_flags_raw) -> dict[str, Any]:
    stages = stages or list(Stage)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {"stages_run": [], "stages_skipped": [], "artifacts": {}, "errors": {}}
    for stage in stages:
        stage_dir = output_dir / stage.value
        if resume and stage_dir.exists() and any(stage_dir.iterdir()):
            results["stages_skipped"].append(stage.value)
            continue
        try:
            result = run_stage(stage=stage, aoi=aoi, year=year, month=month, output_dir=output_dir, seed=seed, days=days, n_rollouts=n_rollouts, stage_flags=stage_flags, **stage_flags_raw)
            results["stages_run"].append(stage.value)
            results["artifacts"][stage.value] = result
        except Exception as e:
            results["errors"][stage.value] = str(e)
            if not resume:
                raise
    return results
