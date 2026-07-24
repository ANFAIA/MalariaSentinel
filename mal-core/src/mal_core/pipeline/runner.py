"""Pipeline orchestrator — runs the full SDSS pipeline end-to-end."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .stages import Stage

def run_stage(stage: Stage, aoi: str, year: int, month: int, output_dir: Path, seed: int = 1, days: int = 30, n_rollouts: int = 1, **stage_flags) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if stage == Stage.INGEST:
        from mal_core.ingest import build_environment
        return build_environment(aoi=aoi, year=year, month=month, output_dir=output_dir / "ingest", **stage_flags)
    elif stage == Stage.ABM:
        from mal_core.abm import run_abm
        return run_abm(aoi=aoi, year=year, month=month, seed=seed, days=days, n_rollouts=n_rollouts, output_dir=output_dir / "abm", **stage_flags)
    elif stage == Stage.SCORE:
        from mal_core.scoring import run_calibration
        return run_calibration(run_dir=output_dir / "abm", output_dir=output_dir / "scoring", **stage_flags)
    elif stage == Stage.TRAIN:
        from mal_core.training import train_unet
        return {"best_dice": train_unet(run_dir=output_dir / "abm", output_dir=output_dir / "training", **stage_flags)}
    elif stage == Stage.PREDICT:
        from mal_core.prediction import run_prediction
        from mal_commonlib.aoi import Scale
        out = run_prediction(aoi_slug=aoi, scale=Scale.REGIONAL, year=year, month=month, output_dir=output_dir / "prediction", **stage_flags)
        return {"prediction_path": str(out)}
    else:
        raise ValueError(f"Unknown stage: {stage}")

def run_pipeline(aoi: str, year: int, month: int, seed: int = 1, days: int = 30, n_rollouts: int = 1, stages: list[Stage] | None = None, output_dir: Path = Path("runs/pipeline"), resume: bool = True, **stage_flags) -> dict[str, Any]:
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
            result = run_stage(stage=stage, aoi=aoi, year=year, month=month, output_dir=output_dir, seed=seed, days=days, n_rollouts=n_rollouts, **stage_flags)
            results["stages_run"].append(stage.value)
            results["artifacts"][stage.value] = result
        except Exception as e:
            results["errors"][stage.value] = str(e)
            if not resume:
                raise
    return results
