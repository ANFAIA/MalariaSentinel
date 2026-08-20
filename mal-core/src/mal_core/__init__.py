"""MalariaSentinel — stable core pipeline."""

__version__ = "0.2.0"

# Heavy submodules (training -> torch, server -> fastapi, prediction) are
# imported lazily so that `import mal_core` (and any subcommand such as
# `abm` / `download` / `ingest`) does not force torch/fastapi to load.
# `__getattr__` resolves them only when accessed, preserving the public
# names in `__all__` below.

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

_LAZY = {
    # name -> (module_path, attribute_name)
    "UNet": (".training.model", "UNet"),
    "combined_loss": (".training.model", "combined_loss"),
    "eval_dice": (".training.model", "eval_dice"),
    "RolloutDataset": (".training.dataset", "RolloutDataset"),
    "get_dataloaders": (".training.dataset", "get_dataloaders"),
    "train_unet": (".training.trainer", "train_unet"),
    "UNetWrapper": (".training.wrapper", "UNetWrapper"),
    "make_aoi": (".prediction.aggregator", "make_aoi"),
    "get_aggregator": (".prediction.aggregator", "get_aggregator"),
    "grid_shape": (".prediction.aggregator", "grid_shape"),
    "RegionalAggregator": (".prediction.aggregator", "RegionalAggregator"),
    "NationalAggregator": (".prediction.aggregator", "NationalAggregator"),
    "ContinentalAggregator": (".prediction.aggregator", "ContinentalAggregator"),
    "ModelRegistry": (".prediction.registry", "ModelRegistry"),
    "ModelManifest": (".prediction.registry", "ModelManifest"),
    "DummyModel": (".prediction.registry", "DummyModel"),
    "run_prediction": (".prediction.predictor", "run_prediction"),
    "get_latest_prediction": (".prediction.predictor", "get_latest_prediction"),
    "get_prediction_metadata": (".prediction.predictor", "get_prediction_metadata"),
    "ScenarioConfig": (".scenario", "ScenarioConfig"),
    "InterventionConfig": (".scenario", "InterventionConfig"),
    "ClimateConfig": (".scenario", "ClimateConfig"),
    "load_scenario": (".scenario", "load_scenario"),
    "interventions_to_params": (".scenario", "interventions_to_params"),
    "fastapi_app": (".server", "app"),
}

# Lightweight import kept eager: the CLI entrypoint is always needed.
from .cli import main as cli_main  # noqa: E402


def __getattr__(name: str):
    entry = _LAZY.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_path, attr = entry
    import importlib

    mod = importlib.import_module(mod_path, __name__)
    value = getattr(mod, attr)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
