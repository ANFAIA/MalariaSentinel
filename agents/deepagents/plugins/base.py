from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from agents.deepagents.subagents.base import ResolvedSubagent, SubagentSpec


class Plugin(ABC):
    name: str = ""

    def tools(self, spec: SubagentSpec) -> list[Callable]:
        """Return tool functions to add to the resolved subagent."""
        return []

    def permissions(self, spec: SubagentSpec) -> list[Any]:
        """Return FilesystemPermission instances to add."""
        return []

    def preamble(self, spec: SubagentSpec) -> str:
        """Return text prepended to the subagent's system prompt."""
        return ""

    def hooks(self, spec: SubagentSpec) -> dict[str, Callable]:
        """Return lifecycle hooks: before_task, after_task, after_proposal, before_finalize."""
        return {}

    def apply(self, spec: SubagentSpec) -> ResolvedSubagent:
        """Default apply: build a ResolvedSubagent from this plugin's outputs."""
        return ResolvedSubagent(
            spec=spec,
            tools=tuple(self.tools(spec)),
            permissions=tuple(self.permissions(spec)),
            preamble=self.preamble(spec),
            hooks=self.hooks(spec),
        )
