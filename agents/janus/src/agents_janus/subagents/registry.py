"""Subagent registry — loads SubagentSpec instances from config/subagents.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from agents_janus.subagents.base import SubagentSpec

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "subagents.yaml"


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
    """Load the registry from YAML config."""
    path = config_path or _CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Subagent config not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    defaults = data.get("defaults", {})
    specs: dict[str, SubagentSpec] = {}

    for name, entry in data.get("subagents", {}).items():
        spec_path_str = entry.get("spec")
        spec_path = Path(spec_path_str) if spec_path_str else None

        specs[name] = SubagentSpec(
            name=name,
            description=entry.get("description", ""),
            model=entry.get("model", defaults.get("model", "xiaomi/mimo-v2.5")),
            provider=entry.get("provider", defaults.get("provider", "openrouter")),
            spec_path=spec_path,
            skills=tuple(entry.get("skills", [])),
            mailbox_inbox=entry.get("mailbox_inbox", f"inbox-{name}"),
            edits_allow=tuple(entry.get("edits_allow", [])),
            thread_id_prefix=entry.get("thread_id_prefix", defaults.get("thread_id_prefix", "sub-")),
            gawt_role=entry.get("gawt_role", ""),
        )

    return Registry(specs)
