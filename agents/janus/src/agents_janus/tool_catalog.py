"""Resolve declarative agent tool policies against discovered MCP tools."""
from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from typing import Any

from agents_janus.agent_config import AgentConfiguration, AgentSpec


RUNTIME_TOOLS = frozenset({
    "execute",
    "ls",
    "glob",
    "grep",
    "read_file",
    "write_file",
    "edit_file",
    "delete_file",
})


def _name(tool: Any) -> str:
    return tool.get("name", "") if isinstance(tool, dict) else getattr(tool, "name", "")


def _matches(patterns: Iterable[str], name: str) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def resolve_tools(
    tools: list[Any],
    spec: AgentSpec,
    configuration: AgentConfiguration,
) -> list[Any]:
    """Return exactly tools declared for one agent.

    Default deny is intentional. Unknown configured tools fail at startup rather
    than silently shrinking an agent's capabilities.
    """
    available = {_name(tool): tool for tool in tools if _name(tool)}
    requested = list(spec.tools)
    denied = tuple(configuration.defaults.global_deny_tools) + tuple(spec.deny_tools)
    selected: list[Any] = []
    missing: list[str] = []

    for pattern in requested:
        matches = [name for name in available if fnmatch.fnmatchcase(name, pattern)]
        if not matches and pattern in RUNTIME_TOOLS:
            # DeepAgents injects backend tools after create_deep_agent(). The
            # exposure middleware applies their policy later.
            continue
        if not matches:
            missing.append(pattern)
            continue
        for name in matches:
            if not _matches(denied, name) and name not in {_name(t) for t in selected}:
                selected.append(available[name])

    if missing and configuration.defaults.fail_on_missing_tools:
        raise LookupError(f"{spec.name}: configured tools not discovered: {missing}")
    return selected
