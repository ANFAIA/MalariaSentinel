"""Live terminal panel for janus runs — real-time visibility into agent activity.

Wraps `rich.Live` to render the current state of a janus run while `agent.stream()`
is consuming events. Shows:

- Current LLM step + token count
- Last tool call + result preview
- Running totals: prompt/completion tokens, elapsed time
- Status icons: 🧠 thinking, 🔧 tool, ✅ done, ❌ error
- Idle watchdog: 30s without an event triggers a "stuck" warning in the panel

Also handles Ctrl-C gracefully — aborts the run, flushes the SessionLogger,
calls `langfuse.flush()` if wired, prints a one-line summary, exits 130.

Usage:
    with LivePanel(session_id="janus-...", quiet=False) as panel:
        for event in agent.stream(..., stream_mode="updates"):
            panel.on_event(event)

    # OR for an explicit abort:
    panel.abort(reason="user_ctrl_c")

The `--quiet` flag (off by default for improve/run) disables the rich render
but keeps the watchdog + abort hooks active so JSONL + langfuse still get
clean shutdown signals.
"""
from __future__ import annotations

import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


IDLE_WARN_S: float = 30.0


@dataclass
class PanelState:
    """Mutable state the panel renders. Updated by `on_event`."""

    session_id: str = ""
    started_at: float = 0.0
    current_step: int = 0
    current_model: str = ""
    last_llm_preview: str = ""
    last_tool_name: str = ""
    last_tool_input_preview: str = ""
    last_tool_output_preview: str = ""
    last_tool_latency_s: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    last_event_at: float = 0.0
    last_event_kind: str = ""
    stuck_warning: str | None = None
    aborted: bool = False
    abort_reason: str | None = None

    def update(self, event: dict[str, Any]) -> None:
        """Apply a stream event to the state. Best-effort, unknown events ignored."""
        kind = event.get("event", "")
        self.last_event_at = time.monotonic()
        self.last_event_kind = kind
        self.stuck_warning = None  # any new event clears the warning

        if kind == "agent_start":
            self.current_step = 0
        elif kind in ("llm_call", "llm_call_start"):
            self.current_step = event.get("step", self.current_step + 1)
            self.current_model = event.get("model", self.current_model) or "unknown"
            self.total_llm_calls += 1
            self.total_prompt_tokens += event.get("prompt_tokens", 0) or 0
            self.total_completion_tokens += event.get("completion_tokens", 0) or 0
            preview = event.get("response_preview") or event.get("content_preview") or ""
            if preview:
                self.last_llm_preview = preview
        elif kind in ("tool_call", "tool_call_detailed"):
            self.total_tool_calls += 1
            self.last_tool_name = event.get("tool", "unknown")
            inp = event.get("input", {})
            self.last_tool_input_preview = _preview_dict(inp, max_chars=120)
            out = event.get("output_preview") or event.get("output", "")
            self.last_tool_output_preview = _preview_value(out, max_chars=160)
            self.last_tool_latency_s = event.get("latency_s", 0.0) or 0.0
        elif kind == "tool_error":
            self.last_tool_name = event.get("tool", "unknown")
            self.last_tool_output_preview = f"❌ {event.get('error_type', 'Error')}: {event.get('error', '')[:160]}"
        elif kind == "agent_end":
            self.current_step = event.get("step", self.current_step)


def _preview_dict(d: Any, max_chars: int) -> str:
    """Compact one-line preview of a dict or any value."""
    if isinstance(d, dict):
        s = ", ".join(f"{k}={_preview_value(v, 40)}" for k, v in list(d.items())[:4])
        if len(d) > 4:
            s += f", +{len(d) - 4} more"
    else:
        s = _preview_value(d, max_chars)
    return s[:max_chars]


def _preview_value(v: Any, max_chars: int) -> str:
    if isinstance(v, str):
        return v[:max_chars]
    return str(v)[:max_chars]


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_elapsed(s: float) -> str:
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


class LivePanel:
    """Context manager wrapping rich.Live with janus-specific state + watchdog.

    Args:
        session_id: Used in the panel header. Usually the SessionLogger dir name.
        quiet: If True, skip rich.Live rendering but keep watchdog + abort hooks.
        on_abort: Optional callback invoked before SIGINT raises. The callback
            is the right place to call SessionLogger.close() and langfuse.flush().
            Signature: `() -> None`.
    """

    def __init__(
        self,
        session_id: str = "",
        quiet: bool = False,
        on_abort: Callable[[], None] | None = None,
    ):
        self.state = PanelState(session_id=session_id, started_at=time.monotonic())
        self.quiet = quiet
        self._on_abort = on_abort
        self._console = Console()
        self._live: Live | None = None
        self._sigint_count = 0
        self._prev_sigint_handler: Any = None
        self._warned_idle = False

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "LivePanel":
        if not self.quiet:
            self._live = Live(
                self._render(),
                console=self._console,
                refresh_per_second=4,
                transient=False,
                redirect_stdout=False,
                redirect_stderr=False,
            )
            self._live.__enter__()
        self._install_sigint_handler()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._restore_sigint_handler()
        if self._live is not None:
            try:
                self._live.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass
            self._live = None

    # ------------------------------------------------------------------
    # Public hooks
    # ------------------------------------------------------------------

    def on_event(self, event: dict[str, Any]) -> None:
        """Apply a stream event to the panel state and trigger a refresh."""
        try:
            self.state.update(event)
        except Exception:
            pass  # never let a render bug kill the run
        self._warned_idle = False
        self._refresh()

    def abort(self, reason: str = "user_ctrl_c") -> None:
        """Mark the run as aborted, fire the on_abort callback, and re-raise.

        Idempotent — second calls are no-ops.
        """
        if self.state.aborted:
            return
        self.state.aborted = True
        self.state.abort_reason = reason
        if self._on_abort is not None:
            try:
                self._on_abort()
            except Exception as e:
                self._console.print(f"[yellow]⚠ on_abort callback raised: {e}[/yellow]")
        self._refresh()
        self._console.print(
            f"\n[yellow]⚠ session aborted ({reason}). "
            f"logs at runs/{self.state.session_id}/session.jsonl. exit 130[/yellow]"
        )
        raise KeyboardInterrupt()

    def render_for_test(self) -> RenderableType:
        """Public render accessor for tests; same output as the live panel."""
        return self._render()

    # ------------------------------------------------------------------
    # Watchdog + render
    # ------------------------------------------------------------------

    def _tick_idle_watchdog(self) -> None:
        """Called from the render path; updates stuck_warning if idle too long."""
        if self.state.last_event_at == 0.0:
            return
        idle = time.monotonic() - self.state.last_event_at
        if idle >= IDLE_WARN_S and not self._warned_idle:
            self.state.stuck_warning = (
                f"⏱ idle {int(idle)}s — agent may be waiting on tool or stuck "
                f"(Ctrl-C to abort)"
            )
            self._warned_idle = True

    def _render(self) -> RenderableType:
        self._tick_idle_watchdog()
        elapsed = time.monotonic() - self.state.started_at
        border = "red" if self.state.stuck_warning else "cyan"
        if self.state.aborted:
            border = "yellow"

        header = Text()
        header.append("🩺 janus", style="bold cyan")
        header.append(f" · session={self.state.session_id}", style="dim")
        header.append(f" · elapsed={_fmt_elapsed(elapsed)}", style="dim")
        if self.state.last_event_kind:
            header.append(f" · last={self.state.last_event_kind}", style="dim")

        lines: list[RenderableType] = [header, Text("")]

        # LLM block
        llm = Text()
        if self.state.current_step > 0 or self.state.current_model:
            llm.append(f"🧠 step {self.state.current_step}", style="bold")
            llm.append(f" · model={self.state.current_model or 'unknown'}", style="dim")
            lines.append(llm)
            if self.state.last_llm_preview:
                preview = self.state.last_llm_preview.replace("\n", " ").strip()
                if len(preview) > 280:
                    preview = preview[:280] + "…"
                lines.append(Text(f"   Last: \"{preview}\"", style="italic dim"))
            lines.append(Text(""))

        # Tool block
        tool = Text()
        if self.state.last_tool_name:
            tool.append(f"🔧 last tool · {self.state.last_tool_name}", style="bold")
            tool.append(f" · {self.state.last_tool_latency_s:.2f}s", style="dim")
            if self.state.last_tool_input_preview:
                tool.append(f"\n   input: {self.state.last_tool_input_preview}", style="dim")
            if self.state.last_tool_output_preview:
                out = self.state.last_tool_output_preview.replace("\n", " ").strip()
                if len(out) > 280:
                    out = out[:280] + "…"
                tool.append(f"\n   output: {out}", style="dim")
            lines.append(tool)
            lines.append(Text(""))

        # Tokens block
        tokens = Text()
        tokens.append("📊 tokens", style="bold")
        tokens.append(
            f" · prompt={_fmt_tokens(self.state.total_prompt_tokens)}"
            f" · completion={_fmt_tokens(self.state.total_completion_tokens)}"
            f" · llm_calls={self.state.total_llm_calls}"
            f" · tool_calls={self.state.total_tool_calls}",
            style="dim",
        )
        lines.append(tokens)

        if self.state.stuck_warning:
            lines.append(Text(""))
            lines.append(Text(f"   {self.state.stuck_warning}", style="bold red"))

        if self.state.aborted:
            lines.append(Text(""))
            lines.append(Text(f"   ⚠ aborting — {self.state.abort_reason}", style="bold yellow"))

        title = "janus"
        return Panel(Group(*lines), title=title, border_style=border, padding=(0, 1))

    def _refresh(self) -> None:
        if self._live is not None:
            try:
                self._live.update(self._render())
            except Exception:
                pass

    # ------------------------------------------------------------------
    # SIGINT handler
    # ------------------------------------------------------------------

    def _install_sigint_handler(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return  # signal.signal only works in main thread
        self._prev_sigint_handler = signal.getsignal(signal.SIGINT)

        def _handler(signum: int, frame: Any) -> None:
            self._sigint_count += 1
            if self._sigint_count == 1:
                # First Ctrl-C: graceful abort via the panel.
                try:
                    self.abort(reason="user_ctrl_c")
                except KeyboardInterrupt:
                    # Re-raise using the original handler so the process exits 130.
                    if callable(self._prev_sigint_handler):
                        self._prev_sigint_handler(signum, frame)
                    else:
                        raise
            else:
                # Second Ctrl-C: hard kill.
                if callable(self._prev_sigint_handler):
                    self._prev_sigint_handler(signum, frame)
                else:
                    raise KeyboardInterrupt()

        signal.signal(signal.SIGINT, _handler)

    def _restore_sigint_handler(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return  # no handler was installed, nothing to restore
        if self._prev_sigint_handler is not None:
            try:
                signal.signal(signal.SIGINT, self._prev_sigint_handler)
            except Exception:
                pass
            self._prev_sigint_handler = None


class MultiAgentPanel:
    """Multi-agent status panel. Shows one row per active specialist.

    Each row: agent_id, role, current_intent, last_edit, inbox_status.
    Updated from gawt MCP list_agents + list_edits + list_intents.
    """

    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self._agents: dict[str, dict] = {}  # agent_id → state
        self._console = Console()
        self._live: Live | None = None

    def __enter__(self) -> "MultiAgentPanel":
        if not self.quiet:
            self._live = Live(
                self._render(),
                console=self._console,
                refresh_per_second=2,
                transient=False,
            )
            self._live.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._live is not None:
            try:
                self._live.__exit__(*args)
            except Exception:
                pass
            self._live = None

    def update_agent(self, agent_id: str, role: str, intent: str = "", last_edit: str = "", inbox_count: int = 0):
        """Update or add an agent's status."""
        self._agents[agent_id] = {
            "role": role,
            "intent": intent,
            "last_edit": last_edit,
            "inbox_count": inbox_count,
        }
        self._refresh()

    def remove_agent(self, agent_id: str):
        """Remove an agent (when it unregisters)."""
        self._agents.pop(agent_id, None)
        self._refresh()

    def _render(self) -> RenderableType:
        header = Text()
        header.append("🩺 janus · multi-agent", style="bold cyan")

        lines: list[RenderableType] = [header, Text("")]

        if not self._agents:
            lines.append(Text("  No active specialists", style="dim"))
        else:
            for agent_id, state in self._agents.items():
                row = Text()
                row.append(f"  ● {agent_id}", style="bold green")
                row.append(f" [{state['role']}]", style="bold")
                if state["intent"]:
                    intent_short = state["intent"][:60]
                    row.append(f"  {intent_short}", style="dim")
                if state["last_edit"]:
                    row.append(f"  last: {state['last_edit']}", style="dim")
                if state["inbox_count"] > 0:
                    row.append(f"  ⚠ {state['inbox_count']} inbox", style="yellow")
                lines.append(row)

        return Panel(Group(*lines), title="agents", border_style="cyan", padding=(0, 1))

    def _refresh(self) -> None:
        if self._live is not None:
            try:
                self._live.update(self._render())
            except Exception:
                pass


def now_iso() -> str:
    """UTC ISO timestamp — handy for tests that want to assert log entries."""
    return datetime.now(timezone.utc).isoformat()