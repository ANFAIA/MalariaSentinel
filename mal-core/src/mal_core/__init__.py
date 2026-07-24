"""MalariaSentinel — stable core pipeline."""
__version__ = "0.2.0"

# Backwards-compatible imports
from .training.model import UNet, combined_loss, eval_dice
from .training.dataset import RolloutDataset, get_dataloaders
from .training.trainer import train_unet
from .training.wrapper import UNetWrapper
from .prediction.aggregator import make_aoi, get_aggregator, grid_shape, RegionalAggregator, NationalAggregator, ContinentalAggregator
from .prediction.registry import ModelRegistry, ModelManifest, DummyModel
from .prediction.predictor import run_prediction, get_latest_prediction, get_prediction_metadata
from .scenario import ScenarioConfig, InterventionConfig, ClimateConfig, load_scenario, interventions_to_params
from .server import app as fastapi_app
from .cli import main as cli_main

__all__ = [
    "UNet", "combined_loss", "eval_dice",
    "RolloutDataset", "get_dataloaders",
    "train_unet", "UNetWrapper",
    "make_aoi", "get_aggregator", "grid_shape",
    "RegionalAggregator", "NationalAggregator", "ContinentalAggregator",
    "ScenarioConfig", "InterventionConfig", "ClimateConfig",
    "load_scenario", "interventions_to_params",
    "ModelRegistry", "ModelManifest", "DummyModel",
    "run_prediction", "get_latest_prediction", "get_prediction_metadata",
    "fastapi_app", "cli_main",
]
