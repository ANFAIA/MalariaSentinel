"""Expert-knowledge YAML scenario schema.

Parses and validates scenario YAML files that encode intervention plans
and climate assumptions. No developer required — public-health experts
write these YAMLs to explore "what-if" questions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from mal_commonlib.aoi import Scale


class InterventionConfig(BaseModel):
    type: str
    coverage: float = Field(ge=0.0, le=1.0)

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        allowed = {"bednets", "irs", "larviciding", "drug_campaign", "vaccine"}
        if v not in allowed:
            raise ValueError(f"intervention type must be one of {allowed}; got {v!r}")
        return v


class ClimateConfig(BaseModel):
    rainfall_anomaly: float = Field(default=0.0, ge=-1.0, le=1.0)
    temperature_anomaly: float = Field(default=0.0, ge=-5.0, le=5.0)


class ScenarioConfig(BaseModel):
    aoi: str
    scale: Scale = Scale.REGIONAL
    year: int = Field(ge=2000, le=2100)
    month: int = Field(default=1, ge=1, le=12)
    interventions: list[InterventionConfig] = Field(default_factory=list)
    climate: ClimateConfig = Field(default_factory=ClimateConfig)


INTERVENTION_EFFECTS: dict[str, dict[str, float]] = {
    "bednets": {"mortality_multiplier": 0.4, "biting_reduction": 0.6},
    "irs": {"mortality_multiplier": 0.5, "biting_reduction": 0.4},
    "larviciding": {"breeding_reduction": 0.5},
    "drug_campaign": {"clearance_rate": 0.8},
    "vaccine": {"susceptibility_reduction": 0.3},
}


def load_scenario(path: Path | str) -> ScenarioConfig:
    p = Path(path)
    raw = yaml.safe_load(p.read_text())
    if "scenario" in raw:
        raw = raw["scenario"]
    return ScenarioConfig.model_validate(raw)


def interventions_to_params(scenario: ScenarioConfig) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for iv in scenario.interventions:
        effects = INTERVENTION_EFFECTS.get(iv.type, {})
        for key, value in effects.items():
            params[key] = params.get(key, 1.0) * (1.0 - iv.coverage * (1.0 - value))
    params["rainfall_multiplier"] = 1.0 + scenario.climate.rainfall_anomaly
    params["temperature_offset"] = scenario.climate.temperature_anomaly
    return params
