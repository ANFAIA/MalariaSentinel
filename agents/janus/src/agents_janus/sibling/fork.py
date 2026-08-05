"""Fork sub-context — branched sessions for sibling negotiation."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ForkContext:
    """A sub-session branched from the parent at a specific message."""
    parent_sibling_id: str
    fork_id: str
    task_brief: str
    instructions: str
    created_at: str
    result: str = ""
    merged: bool = False


@dataclass
class ReadOnlyChatContext:
    """Read-only view of a parent sibling's session history."""
    _messages: list[dict] = field(default_factory=list)

    def peek(self, last_n: int = 10) -> list[dict]:
        """Return the last N messages from the parent context (read-only)."""
        return self._messages[-last_n:]

    def add_message(self, role: str, content: str) -> None:
        """Add a message (only called by the parent, not the fork)."""
        self._messages.append({"role": role, "content": content})


def fork_brief(
    parent_sibling_id: str,
    instructions: str,
    task_brief: str,
) -> ForkContext:
    """Create a forked sub-context. O(1) via parent pointer, no message duplication."""
    return ForkContext(
        parent_sibling_id=parent_sibling_id,
        fork_id=str(uuid.uuid4()),
        task_brief=task_brief,
        instructions=instructions,
        created_at=_now_iso(),
    )


def merge_result(
    fork: ForkContext,
    result: str,
    *,
    use_summary: bool = False,
    max_tokens: int = 500,
) -> str:
    """Return a summary to inject into the parent context.

    Args:
        fork: The fork context to merge.
        result: The full result from the fork's work.
        use_summary: If True, truncate to max_tokens. If False, return raw.
        max_tokens: Maximum tokens in the merged result (default 500).

    Returns:
        A string of at most max_tokens worth of content.
    """
    if use_summary:
        words = result.split()
        if len(words) > max_tokens:
            return " ".join(words[:max_tokens]) + "..."
        return result
    return result[:max_tokens * 4]  # rough char estimate


def create_readonly_context(parent_messages: list[dict]) -> ReadOnlyChatContext:
    """Create a read-only context from parent's message history."""
    ctx = ReadOnlyChatContext()
    for msg in parent_messages:
        ctx.add_message(msg.get("role", ""), msg.get("content", ""))
    return ctx
