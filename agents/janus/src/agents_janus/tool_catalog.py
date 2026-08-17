"""Resolve declarative agent tool policies against discovered MCP tools."""
from __future__ import annotations

import fnmatch
import logging
from collections.abc import Iterable
from typing import Any

from agents_janus.agent_config import AgentConfiguration, AgentSpec


_log = logging.getLogger(__name__)


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
OPTIONAL_TOOL_PATTERNS = ("codebase_*",)


def _name(tool: Any) -> str:
    if isinstance(tool, dict):
        return tool.get("name", "")
    return getattr(tool, "name", "") or getattr(tool, "__name__", "")


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

    optional_missing = [
        name for name in missing
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in OPTIONAL_TOOL_PATTERNS)
    ]
    if optional_missing:
        _log.debug(
            "%s: optional tools unavailable; continuing without %s",
            spec.name,
            optional_missing,
        )
    required_missing = [name for name in missing if name not in optional_missing]
    if required_missing and configuration.defaults.fail_on_missing_tools:
        raise LookupError(f"{spec.name}: configured tools not discovered: {required_missing}")
    return selected
