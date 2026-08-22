"""Build a deepagents subagent prompt from a SubagentSpec."""

from __future__ import annotations

from pathlib import Path
from jinja2 import Template

from agents_janus.subagents.base import SubagentSpec

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


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
    all_specs: dict[str, SubagentSpec] | None = None,
    coordinator_mode: str = "implementation",
) -> str:
    """Compose the full system prompt from three layers.

    Layer A: behavioral spec (from docs/specs/<X>/spec.md)
    Layer B: specialist template (runtime identity is injected by Janus)
    Layer C: per-subagent domain clarifications
    """
    # Layer A: behavioral spec
    spec_text = ""
    if spec.spec_path:
        full_path = Path(__file__).resolve().parent.parent.parent.parent / spec.spec_path
        if full_path.exists():
            spec_text = full_path.read_text()

    # Layer B: specialist template
    gawt_role = spec.effective_gawt_role
    specialist_text = _render_template(
        "specialist.md.tmpl",
        role=gawt_role,
        task=spec.description,
        manifest_path="agents/janus/src/agents_janus/config/agents.yaml",
        edits_allow=list(spec.edits_allow),
        edits_deny=list(spec.edits_deny),
        skills=list(spec.skills),
        depends_on=[],
        spec_text=spec_text,
        coordinator_mode=coordinator_mode,
    )

    # Layer C: per-subagent domain clarifications
    per_subagent_text = _render_template(
        f"per_subagent/{spec.name}.md.j2",
        spec=spec,
    )

    # Assemble
    parts = []
    if specialist_text:
        parts.append(specialist_text)
    if per_subagent_text:
        parts.append(per_subagent_text)

    return "\n\n".join(parts)
