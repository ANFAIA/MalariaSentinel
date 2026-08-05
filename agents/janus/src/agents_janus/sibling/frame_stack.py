"""Frame stack — Interrupt-Resumable Thought for sibling negotiation."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Frame:
    goal: str
    steps_completed: list[str] = field(default_factory=list)
    next_step: str = ""
    pushed_at: str = ""
    expires_at: str | None = None


class FrameStack:
    """Stack of frames for interrupt-resumable thought.

    When a peer message arrives, the sibling MUST push its current frame,
    fork, negotiate, return, then pop the frame and emit render_resume()
    before resuming work.
    """

    def __init__(self, sibling_id: str, max_depth: int = 5):
        self.sibling_id = sibling_id
        self.max_depth = max_depth
        self._stack: list[Frame] = []

    @property
    def depth(self) -> int:
        return len(self._stack)

    def push(self, frame: Frame) -> None:
        """Push a frame onto the stack."""
        if not frame.pushed_at:
            frame = Frame(
                goal=frame.goal,
                steps_completed=frame.steps_completed,
                next_step=frame.next_step,
                pushed_at=_now_iso(),
                expires_at=frame.expires_at,
            )
        if len(self._stack) >= self.max_depth:
            raise OverflowError(f"Frame stack overflow: depth {len(self._stack)} >= max {self.max_depth}")
        self._stack.append(frame)

    def pop(self) -> Frame:
        """Pop the top frame."""
        if not self._stack:
            raise IndexError("Frame stack is empty")
        return self._stack.pop()

    def peek(self) -> Frame | None:
        """Look at the top frame without popping."""
        return self._stack[-1] if self._stack else None

    def render_resume(self) -> str:
        """Returns 'back to X — I was at step N/M, doing Y'."""
        top = self._stack[-1] if self._stack else None
        if not top:
            return "[resume] no active frame"
        total = len(top.steps_completed) + 1
        current = len(top.steps_completed) + 1
        return (
            f"[resume] back to '{top.goal}' — "
            f"step {current}/{total} "
            f"({top.next_step or 'next step'})"
        )

    def to_list(self) -> list[dict]:
        """Serialize stack to list of dicts (for SQLite storage)."""
        return [asdict(f) for f in self._stack]

    @classmethod
    def from_list(cls, sibling_id: str, frames: list[dict], max_depth: int = 5) -> FrameStack:
        """Deserialize from list of dicts."""
        stack = cls(sibling_id, max_depth)
        for fd in frames:
            stack._stack.append(Frame(**fd))
        return stack
