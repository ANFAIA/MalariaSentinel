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
    mailbox_inbox: str
    edits_allow: tuple[str, ...]
    plugins: tuple[str, ...]  # unique-to-subagent plugins
    thread_id_prefix: str = "sub-"


@dataclass(frozen=True)
class ResolvedSubagent:
    spec: SubagentSpec
    tools: tuple[Callable, ...]
    permissions: tuple[Any, ...]  # FilesystemPermission instances
    preamble: str
    hooks: dict[str, Callable]  # keys: before_task, after_task, after_proposal, before_finalize
