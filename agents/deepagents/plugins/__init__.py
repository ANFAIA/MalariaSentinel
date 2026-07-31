"""Plugins package — plugin ABC and built-in plugin implementations."""

from agents.deepagents.plugins.base import Plugin
from agents.deepagents.plugins.edit import EditPlugin
from agents.deepagents.plugins.readonly import ReadOnlyPlugin
from agents.deepagents.plugins.research import ResearchPlugin
from agents.deepagents.plugins.scoring import ScorerPlugin
from agents.deepagents.plugins.download import DownloadPlugin
from agents.deepagents.plugins.ingest import IngestPlugin
from agents.deepagents.plugins.training import TrainingPlugin
from agents.deepagents.plugins.prediction import PredictionPlugin
from agents.deepagents.plugins.data import DataPlugin
from agents.deepagents.plugins.commonlib import CommonlibPlugin

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
