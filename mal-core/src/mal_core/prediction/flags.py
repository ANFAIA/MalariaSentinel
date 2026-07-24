from typing import TypedDict, Any

class PredictionFlags(TypedDict, total=False):
    model: str
    model_version: str

PREDICTION_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "model": {"type": str, "default": "dummy", "help": "Model name from registry"},
    "model_version": {"type": str, "default": None, "help": "Model version"},
}
