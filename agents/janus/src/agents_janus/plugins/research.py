from __future__ import annotations

from agents_janus.plugins.base import Plugin
from agents_janus.subagents.base import SubagentSpec


class ResearchPlugin(Plugin):
    name = "research"

    def permissions(self, spec: SubagentSpec) -> list:
        return [
            {"operations": ["write"], "paths": ["/**"], "mode": "deny"},
            {"operations": ["read"], "paths": ["/**"], "mode": "allow"},
        ]

    def preamble(self, spec: SubagentSpec) -> str:
        return (
            "You are a READ-ONLY research worker. Search papers, web, and knowledge base. "
            "Report structured findings. Never modify code."
        )
