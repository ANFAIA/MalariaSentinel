"""Subagents package — specs, resolution, builder, registry."""

from agents.deepagents.plugins import PLUGIN_REGISTRY, Plugin
from agents.deepagents.subagents.base import ResolvedSubagent, SubagentSpec
from agents.deepagents.subagents.builder import build_resolved as build_subagent
from agents.deepagents.subagents.registry import Registry, load_registry

__all__ = [
    "SubagentSpec",
    "ResolvedSubagent",
    "Plugin",
    "Registry",
    "load_registry",
    "build_subagent",
    "PLUGIN_REGISTRY",
]
