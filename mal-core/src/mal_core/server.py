"""FastAPI server — programmatic access to the SDSS prediction pipeline.

Endpoints:
    POST /predict — accepts state + scenario, returns prediction
    GET  /aoi/{name}/risk — latest prediction for an AOI
    GET  /aoi/{name}/status — metadata (last update, coverage, model version)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mal_commonlib.aoi import Scale

from .predict import get_latest_prediction, get_prediction_metadata, run_prediction
from .scenario import (
    ClimateConfig,
    InterventionConfig,
    ScenarioConfig,
    interventions_to_params,
)

app = FastAPI(title="MalariaSentinel SDSS", version="0.1.0")


class PredictRequest(BaseModel):
    aoi: str
    scale: Scale = Scale.REGIONAL
    year: int = 2026
    month: int = 1
    model_name: str = "dummy"
    model_version: str | None = None
    interventions: list[InterventionConfig] = Field(default_factory=list)
    climate: ClimateConfig = Field(default_factory=ClimateConfig)


class PredictResponse(BaseModel):
    output_path: str
    aoi: str
    scale: str
    year: int
    month: int
    model_name: str


class StatusResponse(BaseModel):
    aoi: str
    has_prediction: bool
    metadata: dict | None = None


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    scenario = ScenarioConfig(
        aoi=req.aoi,
        scale=req.scale,
        year=req.year,
        month=req.month,
        interventions=req.interventions,
        climate=req.climate,
    )
    try:
        out = run_prediction(
            aoi_slug=req.aoi,
            scale=req.scale,
            year=req.year,
            month=req.month,
            model_name=req.model_name,
            model_version=req.model_version,
            scenario=scenario,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PredictResponse(
        output_path=str(out),
        aoi=req.aoi,
        scale=req.scale.value,
        year=req.year,
        month=req.month,
        model_name=req.model_name,
    )


@app.get("/aoi/{name}/risk")
def aoi_risk(name: str):
    latest = get_latest_prediction(name)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"No prediction for AOI {name!r}")
    return {"aoi": name, "path": str(latest), "exists": True}


@app.get("/aoi/{name}/status", response_model=StatusResponse)
def aoi_status(name: str) -> StatusResponse:
    meta = get_prediction_metadata(name)
    return StatusResponse(
        aoi=name,
        has_prediction=meta is not None,
        metadata=meta,
    )
