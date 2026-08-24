from typing import TypedDict, Any

class TrainingFlags(TypedDict, total=False):
    epochs: int
    batch_size: int
    lr: float
    subsample: float
    include_transmission: bool
    env_path: str | None

TRAINING_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "epochs": {"type": int, "default": 50, "help": "Training epochs"},
    "batch_size": {"type": int, "default": 16, "help": "Batch size"},
    "lr": {"type": float, "default": 1e-3, "help": "Learning rate"},
    "subsample": {"type": float, "default": 1.0, "help": "Dataset subsample fraction"},
    "include_transmission": {"type": bool, "default": True, "help": "Include 4-band SEIR-SEI transmission states in dataset"},
    "env_path": {"type": str, "default": None, "help": "Optional path to NetCDF/GeoTIFF environmental raster"},
}
