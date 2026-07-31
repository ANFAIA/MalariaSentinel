from __future__ import annotations

from agents.deepagents.plugins.base import Plugin
from agents.deepagents.subagents.base import SubagentSpec


class ReadOnlyPlugin(Plugin):
    name = "readonly"

    def permissions(self, spec: SubagentSpec) -> list:
        return [
            {"operations": ["read"], "paths": ["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], "mode": "deny"},
            {"operations": ["write"], "paths": ["/**"], "mode": "deny"},
            {"operations": ["read"], "paths": ["/**"], "mode": "allow"},
        ]

    def preamble(self, spec: SubagentSpec) -> str:
        return (
            "You are READ-ONLY. Do not modify any files. "
            "Report findings, run read-only commands, and suggest changes to the orchestrator."
        )
