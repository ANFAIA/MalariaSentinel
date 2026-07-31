from __future__ import annotations

from agents.janus.plugins.base import Plugin
from agents.janus.subagents.base import SubagentSpec


class EditPlugin(Plugin):
    name = "edit"

    def permissions(self, spec: SubagentSpec) -> list:
        return [
            {"operations": ["read"], "paths": ["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], "mode": "deny"},
            {"operations": ["write"], "paths": ["/data/**"], "mode": "deny"},
            {"operations": ["write"], "paths": ["/.git/**"], "mode": "deny"},
            {"operations": ["write"], "paths": ["/.gitagent/features/*/agents/*/worktree/**"], "mode": "allow"},
            {"operations": ["write"], "paths": ["/**"], "mode": "deny"},
            {"operations": ["read"], "paths": ["/**"], "mode": "allow"},
        ]

    def preamble(self, spec: SubagentSpec) -> str:
        return (
            "You work in an isolated gitagent worktree. All edits go through gitagent propose. "
            "Never run git add or git commit directly. "
            "When done, run: gitagent propose --agent <id> --title '...' --summary '...' --confidence 0.8 --feature <name>"
        )
