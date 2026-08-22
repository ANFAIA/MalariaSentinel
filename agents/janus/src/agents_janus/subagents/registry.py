"""Registry facade over the single declarative agents.yaml."""

from __future__ import annotations

from pathlib import Path

from agents_janus.agent_config import load_agent_configuration
from agents_janus.subagents.base import SubagentSpec

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agents.yaml"


class Registry:
    """Registry of subagent specs loaded from YAML."""

    def __init__(self, specs: dict[str, SubagentSpec]):
        self._specs = specs

    def get(self, name: str) -> SubagentSpec:
        if name not in self._specs:
            raise KeyError(f"Unknown subagent: {name}. Available: {list(self._specs)}")
        return self._specs[name]

    def all(self) -> dict[str, SubagentSpec]:
        return dict(self._specs)

    def find_owner(self, path: str) -> str | None:
        """Find which subagent owns a given file path (by edits_allow glob match).
        Returns the subagent name or None if no owner."""
        import fnmatch

        for name, spec in self._specs.items():
            for pattern in spec.edits_allow:
                if fnmatch.fnmatch(path, pattern):
                    return name
        return None


def load_registry(config_path: Path | None = None) -> Registry:
    """Load specialist specs from the single agents.yaml config."""
    path = config_path or _CONFIG_PATH
    configuration = load_agent_configuration(path)
    specs: dict[str, SubagentSpec] = {}
    defaults = configuration.defaults
    for name, entry in configuration.agents.items():
        if entry.kind != "specialist":
            continue
        specs[name] = SubagentSpec(
            name=name,
            description=entry.description,
            model=entry.model or defaults.model,
            provider=entry.provider or defaults.provider,
            spec_path=entry.spec,
            skills=tuple(entry.skills),
            edits_allow=tuple(entry.edits_allow),
            edits_deny=tuple(entry.edits_deny),
            thread_id_prefix=entry.thread_id_prefix or defaults.thread_id_prefix,
            gawt_role=entry.gawt_role,
            kind=entry.kind,
            servers=tuple(entry.servers),
            tools=tuple(entry.tools),
            middleware=tuple(entry.middleware),
        )

    return Registry(specs)
