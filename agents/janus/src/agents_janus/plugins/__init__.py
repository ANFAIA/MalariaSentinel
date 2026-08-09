"""Plugins package — plugin ABC and built-in plugin implementations."""

from agents_janus.plugins.base import Plugin
from agents_janus.plugins.research import ResearchPlugin
from agents_janus.plugins.scoring import ScorerPlugin
from agents_janus.plugins.download import DownloadPlugin
from agents_janus.plugins.ingest import IngestPlugin
from agents_janus.plugins.training import TrainingPlugin
from agents_janus.plugins.prediction import PredictionPlugin
from agents_janus.plugins.data import DataPlugin
from agents_janus.plugins.commonlib import CommonlibPlugin

PLUGIN_REGISTRY: dict[str, type[Plugin]] = {
    "research": ResearchPlugin,
    "scoring": ScorerPlugin,
    "download": DownloadPlugin,
    "ingest": IngestPlugin,
    "training": TrainingPlugin,
    "prediction": PredictionPlugin,
    "data": DataPlugin,
    "commonlib": CommonlibPlugin,
}

__all__ = [
    "Plugin",
    "ResearchPlugin",
    "ScorerPlugin",
    "DownloadPlugin",
    "IngestPlugin",
    "TrainingPlugin",
    "PredictionPlugin",
    "DataPlugin",
    "CommonlibPlugin",
    "PLUGIN_REGISTRY",
]
