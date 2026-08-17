from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    description: str
    model: str
    provider: str
    spec_path: Path | None
    skills: tuple[str, ...]
    edits_allow: tuple[str, ...]
    thread_id_prefix: str = "sub-"
    gawt_role: str = ""  # gawt register_agent role (defaults to name if empty)
    kind: str = "specialist"
    servers: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    middleware: tuple[str, ...] = ()

    @property
    def effective_gawt_role(self) -> str:
        return self.gawt_role or self.name
