"""Subagents package — specs, builder, registry."""

from agents_janus.subagents.base import SubagentSpec
from agents_janus.subagents.builder import build_subagent_prompt
from agents_janus.subagents.registry import Registry, load_registry

__all__ = [
    "SubagentSpec",
    "Registry",
    "load_registry",
    "build_subagent_prompt",
]
