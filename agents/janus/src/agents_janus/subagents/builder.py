"""Build a deepagents subagent from a SubagentSpec + plugin chain."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from jinja2 import Template

from agents_janus.subagents.base import ResolvedSubagent, SubagentSpec

if TYPE_CHECKING:
    from agents_janus.plugins.base import Plugin

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


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


def _render_template(name: str, **kwargs) -> str:
    """Render a Jinja2 template from the prompts directory."""
    template_path = _PROMPTS_DIR / name
    if not template_path.exists():
        return ""
    return Template(template_path.read_text()).render(**kwargs)


def _get_peer_registry_table(self_name: str, all_specs: dict[str, SubagentSpec]) -> str:
    """Generate the peer registry markdown table for a subagent."""
    lines = ["| Specialist | When to call | Scope |"]
    lines.append("|---|---|---|")
    for name, spec in all_specs.items():
        if name == self_name:
            continue
        scope = ", ".join(spec.edits_allow[:2]) if spec.edits_allow else "(read-only)"
        lines.append(f"| `{name}` | {spec.description[:50]} | `{scope}` |")
    return "\n".join(lines)


def build_subagent_prompt(
    spec: SubagentSpec,
    plugin_chain: list[Plugin],
    all_specs: dict[str, SubagentSpec] | None = None,
) -> str:
    """Compose the full system prompt from three layers + plugins.

    Layer A: behavioral spec (from docs/specs/<X>/spec.md)
    Layer B: common role (identical for all subagents)
    Layer C: per-subagent domain clarifications
    Plugins: preambles from plugin chain
    """
    # Layer A: behavioral spec
    spec_text = ""
    if spec.spec_path:
        full_path = Path(__file__).resolve().parent.parent.parent.parent / spec.spec_path
        if full_path.exists():
            spec_text = full_path.read_text()

    # Layer B: common role
    peer_table = _get_peer_registry_table(spec.name, all_specs or {})
    common_text = _render_template(
        "common_role.md.j2",
        subagent_name=spec.name,
        invoker_name="orchestrator",
        model=spec.model,
        mailbox_inbox=spec.mailbox_inbox,
        edits_allow=list(spec.edits_allow),
        skills=list(spec.skills),
        peer_registry_table=peer_table,
    )

    # Layer C: per-subagent domain clarifications
    per_subagent_text = _render_template(
        f"per_subagent/{spec.name}.md.j2",
        spec=spec,
    )

    # Plugin preambles
    plugin_text = "\n\n".join(p.preamble(spec) for p in plugin_chain if p.preamble(spec))

    # Assemble
    parts = []
    if common_text:
        parts.append(common_text)
    if per_subagent_text:
        parts.append(per_subagent_text)
    if spec_text:
        parts.append(f"## Domain behavioral spec\n{spec_text}")
    if plugin_text:
        parts.append(f"## Plugin instructions\n{plugin_text}")

    return "\n\n".join(parts)
