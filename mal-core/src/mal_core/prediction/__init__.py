"""Prediction subpackage — model inference, registry, data loaders."""
from .predictor import run_prediction, get_latest_prediction, get_prediction_metadata
from .registry import ModelRegistry, ModelManifest, DummyModel
from .aggregator import make_aoi, get_aggregator, grid_shape, RegionalAggregator, NationalAggregator, ContinentalAggregator

__all__ = ["run_prediction", "get_latest_prediction", "get_prediction_metadata", "ModelRegistry", "ModelManifest", "DummyModel", "make_aoi", "get_aggregator", "grid_shape", "RegionalAggregator", "NationalAggregator", "ContinentalAggregator"]
