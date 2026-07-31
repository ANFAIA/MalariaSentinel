"""Build a deepagents subagent from a SubagentSpec + plugin chain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents.deepagents.subagents.base import ResolvedSubagent, SubagentSpec

if TYPE_CHECKING:
    from agents.deepagents.plugins.base import Plugin


def build_resolved(spec: SubagentSpec, plugins: list[Plugin]) -> ResolvedSubagent:
    """Apply a plugin chain to a SubagentSpec, returning a ResolvedSubagent.

    Plugins are applied in order. Each plugin's apply() is called on the spec,
    producing a ResolvedSubagent. Then the next plugin's outputs are merged:
    - tools: concatenated
    - permissions: concatenated
    - preamble: concatenated (newline-joined)
    - hooks: merged (later plugin wins on key conflict)
    """
    all_tools: list = []
    all_permissions: list = []
    preambles: list[str] = []
    all_hooks: dict = {}

    for plugin in plugins:
        resolved = plugin.apply(spec)
        all_tools.extend(resolved.tools)
        all_permissions.extend(resolved.permissions)
        if resolved.preamble:
            preambles.append(resolved.preamble)
        all_hooks.update(resolved.hooks)

    return ResolvedSubagent(
        spec=spec,
        tools=tuple(all_tools),
        permissions=tuple(all_permissions),
        preamble="\n\n".join(preambles),
        hooks=all_hooks,
    )
