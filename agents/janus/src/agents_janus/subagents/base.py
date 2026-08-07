from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    description: str
    model: str
    provider: str
    spec_path: Path | None
    skills: tuple[str, ...]
    mailbox_inbox: str  # kept for backwards compat, replaced by gawt inbox
    edits_allow: tuple[str, ...]
    plugins: tuple[str, ...]
    thread_id_prefix: str = "sub-"
    gawt_role: str = ""  # gawt register_agent role (defaults to name if empty)


@dataclass(frozen=True)
class ResolvedSubagent:
    spec: SubagentSpec
    tools: tuple[Callable, ...]
    permissions: tuple[Any, ...]
    preamble: str
    hooks: dict[str, Callable]
