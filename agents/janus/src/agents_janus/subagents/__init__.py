"""Subagents package — specs, resolution, builder, registry."""

from agents_janus.subagents.base import ResolvedSubagent, SubagentSpec
from agents_janus.subagents.builder import build_resolved as build_subagent
from agents_janus.subagents.registry import Registry, load_registry

__all__ = [
    "SubagentSpec",
    "ResolvedSubagent",
    "Registry",
    "load_registry",
    "build_subagent",
]
