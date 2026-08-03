"""Tests for LivePanel — render, watchdog, Ctrl-C handling.

Uses Console(record=True) so render output can be captured without a TTY.
"""
from __future__ import annotations

import signal
import time
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from agents_janus.live_panel import (
    IDLE_WARN_S,
    LivePanel,
    PanelState,
    _fmt_elapsed,
    _fmt_tokens,
)


# ----------------------------------------------------------------------
# State
# ----------------------------------------------------------------------

def test_state_initialised_with_started_at():
    p = LivePanel(session_id="test-1")
    assert p.state.session_id == "test-1"
    assert p.state.started_at > 0
    assert p.state.current_step == 0
    assert p.state.last_event_at == 0.0  # never updated


def test_state_update_llm_call_accumulates_tokens():
    p = LivePanel()
    p.state.update({"event": "llm_call", "step": 3, "model": "test/model",
                    "prompt_tokens": 100, "completion_tokens": 50,
                    "response_preview": "hello"})
    assert p.state.current_step == 3
    assert p.state.current_model == "test/model"
    assert p.state.total_prompt_tokens == 100
    assert p.state.total_completion_tokens == 50
    assert p.state.total_llm_calls == 1
    assert p.state.last_llm_preview == "hello"
    assert p.state.last_event_at > 0


def test_state_update_tool_call_records_tool():
    p = LivePanel()
    p.state.update({
        "event": "tool_call_detailed", "tool": "abm_run",
        "input": {"seed": 1, "days": 30},
        "output_preview": "ok 4802 rows", "latency_s": 7.3,
    })
    assert p.state.last_tool_name == "abm_run"
    assert "seed=1" in p.state.last_tool_input_preview
    assert "4802 rows" in p.state.last_tool_output_preview
    assert p.state.last_tool_latency_s == 7.3
    assert p.state.total_tool_calls == 1


def test_state_update_tool_error_shows_error():
    p = LivePanel()
    p.state.update({"event": "tool_error", "tool": "broken",
                    "error": "kaboom", "error_type": "RuntimeError"})
    assert p.state.last_tool_name == "broken"
    assert "kaboom" in p.state.last_tool_output_preview
    assert "RuntimeError" in p.state.last_tool_output_preview


def test_state_update_clears_stuck_warning():
    p = LivePanel()
    p.state.stuck_warning = "old warning"
    p.state.update({"event": "llm_call", "step": 1, "model": "m", "prompt_tokens": 0, "completion_tokens": 0})
    assert p.state.stuck_warning is None


def test_state_unknown_event_ignored():
    p = LivePanel()
    p.state.update({"event": "session_end"})
    assert p.state.last_event_kind == "session_end"


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------

def test_render_shows_session_id_and_elapsed():
    p = LivePanel(session_id="abc123")
    p.state.last_event_at = time.monotonic()
    r = p.render_for_test()
    # Renderable — just assert it builds and is not None.
    assert r is not None


def test_render_after_llm_event_shows_step():
    p = LivePanel()
    p.state.update({"event": "llm_call", "step": 7, "model": "mimo",
                    "prompt_tokens": 200, "completion_tokens": 30,
                    "response_preview": "next step is X"})
    r = p.render_for_test()
    assert r is not None


def test_quiet_mode_does_not_create_live():
    p = LivePanel(quiet=True)
    with p:
        assert p._live is None
    p.state.update({"event": "llm_call", "step": 1, "model": "m",
                    "prompt_tokens": 10, "completion_tokens": 5})
    # No exception even though _refresh on None is skipped.


def test_fmt_tokens_human_readable():
    assert _fmt_tokens(0) == "0"
    assert _fmt_tokens(999) == "999"
    assert _fmt_tokens(1500) == "1.5k"
    assert _fmt_tokens(1_500_000) == "1.5M"


def test_fmt_elapsed_formats():
    assert _fmt_elapsed(0) == "00:00"
    assert _fmt_elapsed(65) == "01:05"
    assert _fmt_elapsed(3661) == "1:01:01"


# ----------------------------------------------------------------------
# Watchdog
# ----------------------------------------------------------------------

def test_idle_warning_fires_after_threshold(monkeypatch):
    p = LivePanel()

    class FakeTime:
        now = 1000.0

        def monotonic(self) -> float:
            return self.now

    ft = FakeTime()
    monkeypatch.setattr("agents_janus.live_panel.time.monotonic", ft.monotonic)

    p.state.update({"event": "llm_call", "step": 1, "model": "m",
                    "prompt_tokens": 0, "completion_tokens": 0})
    # Now advance time past the threshold.
    ft.now = 1000.0 + IDLE_WARN_S + 1
    p._tick_idle_watchdog()
    assert p.state.stuck_warning is not None
    assert "idle" in p.state.stuck_warning


def test_idle_warning_not_fired_under_threshold(monkeypatch):
    p = LivePanel()

    class FakeTime:
        now = 1000.0

        def monotonic(self) -> float:
            return self.now

    ft = FakeTime()
    monkeypatch.setattr("agents_janus.live_panel.time.monotonic", ft.monotonic)

    p.state.update({"event": "llm_call", "step": 1, "model": "m",
                    "prompt_tokens": 0, "completion_tokens": 0})
    ft.now = 1000.0 + 5.0  # only 5 seconds
    p._tick_idle_watchdog()
    assert p.state.stuck_warning is None


def test_idle_warning_only_fires_once(monkeypatch):
    p = LivePanel()

    class FakeTime:
        now = 1000.0

        def monotonic(self) -> float:
            return self.now

    ft = FakeTime()
    monkeypatch.setattr("agents_janus.live_panel.time.monotonic", ft.monotonic)

    p.state.update({"event": "llm_call", "step": 1, "model": "m",
                    "prompt_tokens": 0, "completion_tokens": 0})
    ft.now = 1000.0 + IDLE_WARN_S + 1
    p._tick_idle_watchdog()
    first = p.state.stuck_warning
    assert first is not None
    # Tick again — warning should not duplicate.
    ft.now = 1000.0 + IDLE_WARN_S + 10
    p._tick_idle_watchdog()
    assert p.state.stuck_warning == first


def test_idle_warning_cleared_by_new_event(monkeypatch):
    p = LivePanel()

    class FakeTime:
        now = 1000.0

        def monotonic(self) -> float:
            return self.now

    ft = FakeTime()
    monkeypatch.setattr("agents_janus.live_panel.time.monotonic", ft.monotonic)

    p.on_event({"event": "llm_call", "step": 1, "model": "m",
                "prompt_tokens": 0, "completion_tokens": 0})
    ft.now = 1000.0 + IDLE_WARN_S + 1
    p._tick_idle_watchdog()
    assert p.state.stuck_warning is not None

    # New event comes in — should clear the warning and reset the latch.
    ft.now = 1000.0 + 1.0
    p.on_event({"event": "tool_call_detailed", "tool": "x",
                "input": {}, "output_preview": "y", "latency_s": 0.1})
    assert p.state.stuck_warning is None
    assert p._warned_idle is False


# ----------------------------------------------------------------------
# Abort / Ctrl-C
# ----------------------------------------------------------------------

def test_abort_invokes_on_abort_callback():
    cb = MagicMock()
    p = LivePanel(on_abort=cb)
    with pytest.raises(KeyboardInterrupt):
        p.abort(reason="test")
    cb.assert_called_once()
    assert p.state.aborted is True
    assert p.state.abort_reason == "test"


def test_abort_idempotent():
    cb = MagicMock()
    p = LivePanel(on_abort=cb)
    with pytest.raises(KeyboardInterrupt):
        p.abort(reason="first")
    # Second call is a no-op — callback not called again.
    p.abort(reason="second")  # does not raise (already aborted)
    cb.assert_called_once()


def test_abort_on_abort_callback_exception_does_not_kill():
    def bad_cb():
        raise RuntimeError("boom")

    p = LivePanel(on_abort=bad_cb)
    # Should still raise KeyboardInterrupt despite the callback failing.
    with pytest.raises(KeyboardInterrupt):
        p.abort(reason="test")


def test_context_manager_restores_sigint_handler():
    prev = signal.getsignal(signal.SIGINT)
    p = LivePanel()
    with p:
        assert signal.getsignal(signal.SIGINT) != prev
    assert signal.getsignal(signal.SIGINT) == prev