"""Structured JSONL logging for DeepAgent sessions."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionLogger:
    """Append-only JSONL logger for a single DeepAgent session.

    Each line is a JSON object with:
        - ts: ISO-8601 timestamp
        - step: iteration number (0-indexed)
        - tool: tool name
        - input: tool arguments (sanitised)
        - output: tool return value (truncated)
        - latency_s: wall-clock seconds
        - verdict: optional, for calibration results
    """

    def __init__(self, session_dir: Path | str | None = None):
        """Create or resume a session log.

        Args:
            session_dir: Directory for this session. If None, creates
                ``runs/deepagent-<timestamp>/`` under the repo root.
        """
        if session_dir is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            session_dir = repo_root / "runs" / f"deepagent-{ts}"

        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.session_dir / "session.jsonl"
        self._step = 0
        self._session_start = time.monotonic()

        # Write session header
        self._append({
            "event": "session_start",
            "ts": self._now_iso(),
            "session_dir": str(self.session_dir),
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        output: Any,
        latency_s: float,
        *,
        verdict: str | None = None,
    ) -> None:
        """Log a single tool call."""
        self._append({
            "event": "tool_call",
            "ts": self._now_iso(),
            "step": self._step,
            "tool": tool_name,
            "input": _sanitise(tool_input),
            "output": _truncate(output, max_chars=4000),
            "latency_s": round(latency_s, 3),
            "verdict": verdict,
        })
        self._step += 1

    def log_decision(self, decision: str, reason: str) -> None:
        """Log an orchestrator decision (e.g. 'picked improvement X')."""
        self._append({
            "event": "decision",
            "ts": self._now_iso(),
            "step": self._step,
            "decision": decision,
            "reason": reason,
        })

    def log_approval(self, action: str, approved: bool, detail: str = "") -> None:
        """Log a human approval gate."""
        self._append({
            "event": "approval",
            "ts": self._now_iso(),
            "step": self._step,
            "action": action,
            "approved": approved,
            "detail": detail,
        })

    def log_summary(self, summary: str) -> None:
        """Log a free-form summary at the end of a step."""
        self._append({
            "event": "summary",
            "ts": self._now_iso(),
            "step": self._step,
            "summary": summary,
        })

    def log_conversation(self, messages: list[dict]) -> None:
        """Log the full conversation (LLM reasoning + tool results).

        Args:
            messages: List of {"type": "AIMessage"|"ToolMessage"|"HumanMessage", "content": "..."}
        """
        self._append({
            "event": "conversation",
            "ts": self._now_iso(),
            "step": self._step,
            "message_count": len(messages),
            "messages": [
                {"type": m["type"], "content": _truncate(m["content"], max_chars=2000)}
                for m in messages
            ],
        })

    def log_llm_call(
        self,
        step: int,
        model_name: str,
        message_count: int,
        latency_s: float,
        prompt_tokens: int,
        completion_tokens: int,
        response_preview: str = "",
    ) -> None:
        """Log a single LLM call with token usage."""
        self._append({
            "event": "llm_call",
            "ts": self._now_iso(),
            "step": step,
            "model": model_name,
            "message_count": message_count,
            "latency_s": round(latency_s, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "response_preview": _truncate(response_preview, max_chars=500),
        })

    def log_agent_event(self, event_type: str, detail: str = "") -> None:
        """Log agent lifecycle event (start, end, error)."""
        self._append({
            "event": f"agent_{event_type}",
            "ts": self._now_iso(),
            "detail": detail,
        })

    def log_token_summary(
        self,
        total_prompt: int,
        total_completion: int,
        llm_calls: int,
    ) -> None:
        """Log cumulative token usage at session end."""
        self._append({
            "event": "token_summary",
            "ts": self._now_iso(),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_llm_calls": llm_calls,
        })

    def log_graph_steps(self, steps: list[dict]) -> None:
        """Log graph node execution steps from streaming."""
        self._append({
            "event": "graph_steps",
            "ts": self._now_iso(),
            "step_count": len(steps),
            "steps": steps,
        })

    def close(self) -> None:
        """Write session end marker."""
        elapsed = time.monotonic() - self._session_start
        self._append({
            "event": "session_end",
            "ts": self._now_iso(),
            "total_steps": self._step,
            "elapsed_s": round(elapsed, 1),
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append(self, record: dict) -> None:
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def _sanitise(data: dict) -> dict:
    """Remove or mask sensitive fields."""
    out = {}
    for k, v in data.items():
        if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower():
            out[k] = "***"
        elif isinstance(v, str) and len(v) > 500:
            out[k] = v[:500] + "..."
        else:
            out[k] = v
    return out


def _truncate(value: Any, max_chars: int = 4000) -> Any:
    """Truncate long strings in tool output."""
    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + f"\n... ({len(value) - max_chars} chars truncated)"
    return value
