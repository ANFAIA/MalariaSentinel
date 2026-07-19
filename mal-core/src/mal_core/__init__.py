"""MalariaSentinel — stable core pipeline."""
__version__ = "0.1.0"

from .unet import UNet, combined_loss, eval_dice
from .dataset import RolloutDataset, get_dataloaders
from .train import train_unet
from .unet_wrapper import UNetWrapper
from .aoi import make_aoi, get_aggregator, grid_shape, RegionalAggregator, NationalAggregator, ContinentalAggregator
from .scenario import ScenarioConfig, InterventionConfig, ClimateConfig, load_scenario, interventions_to_params
from .registry import ModelRegistry, ModelManifest, DummyModel
from .predict import run_prediction, get_latest_prediction, get_prediction_metadata
from .server import app as fastapi_app
from .cli import main as cli_main

__all__ = [
    "UNet",
    "combined_loss",
    "eval_dice",
    "RolloutDataset",
    "get_dataloaders",
    "train_unet",
    "UNetWrapper",
    "make_aoi",
    "get_aggregator",
    "grid_shape",
    "RegionalAggregator",
    "NationalAggregator",
    "ContinentalAggregator",
    "ScenarioConfig",
    "InterventionConfig",
    "ClimateConfig",
    "load_scenario",
    "interventions_to_params",
    "ModelRegistry",
    "ModelManifest",
    "DummyModel",
    "run_prediction",
    "get_latest_prediction",
    "get_prediction_metadata",
    "fastapi_app",
    "cli_main",
]