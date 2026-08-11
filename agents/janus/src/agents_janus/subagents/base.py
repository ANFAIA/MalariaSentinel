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
    mailbox_inbox: str  # kept for backwards compat, replaced by gawt inbox
    edits_allow: tuple[str, ...]
    thread_id_prefix: str = "sub-"
    gawt_role: str = ""  # gawt register_agent role (defaults to name if empty)
