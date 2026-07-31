"""Plugins package — plugin ABC and built-in plugin implementations."""

from agents.janus.plugins.base import Plugin
from agents.janus.plugins.edit import EditPlugin
from agents.janus.plugins.readonly import ReadOnlyPlugin
from agents.janus.plugins.research import ResearchPlugin
from agents.janus.plugins.scoring import ScorerPlugin
from agents.janus.plugins.download import DownloadPlugin
from agents.janus.plugins.ingest import IngestPlugin
from agents.janus.plugins.training import TrainingPlugin
from agents.janus.plugins.prediction import PredictionPlugin
from agents.janus.plugins.data import DataPlugin
from agents.janus.plugins.commonlib import CommonlibPlugin

PLUGIN_REGISTRY: dict[str, type[Plugin]] = {
    "edit": EditPlugin,
    "readonly": ReadOnlyPlugin,
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
    "EditPlugin",
    "ReadOnlyPlugin",
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
