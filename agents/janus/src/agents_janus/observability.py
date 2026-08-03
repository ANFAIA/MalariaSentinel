"""ObservabilityMiddleware — hooks into deepagents lifecycle for full tracing.

Captures: LLM calls (model, tokens, latency), tool calls (name, args, result, errors),
agent lifecycle events, and cumulative token usage.

Sinks (fan-out):
1. SessionLogger → JSONL in `runs/<session>/session.jsonl` (always on)
2. langfuse.Langfuse → self-hosted langfuse UI (opt-in via --tracing langfuse)

A sink failure never aborts the run — errors are logged to JSONL and ignored.
"""
from __future__ import annotations

import time
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


def _safe_call(fn, *args, **kwargs):
    """Call a langfuse function and swallow any exception.

    Langfuse SDK can raise (network down, malformed event). We log the error
    to the SessionLogger (best-effort) and continue — langfuse outages must
    never abort a janus run.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return _LangfuseErrorMarker(error=e)


class _LangfuseErrorMarker:
    """Sentinel returned by _safe_call so the caller can detect a failure."""

    def __init__(self, error: Exception):
        self.error = error


class ObservabilityMiddleware(AgentMiddleware):
    """Logs every LLM call, tool call, and agent lifecycle event to SessionLogger.

    Optionally also streams the same events to a Langfuse client (one trace per
    session, with nested generations for LLM calls and spans for tool calls).
    """

    def __init__(self, session_logger, langfuse_client=None):
        self.logger = session_logger
        self.langfuse = langfuse_client
        self._llm_call_count = 0
        self._tool_call_count = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._agent_start_time: float | None = None

        # Langfuse handle holders — one trace per session, nested observations
        # per LLM call / tool call. Stored in plain dicts keyed by step number
        # so we can .end() them when the corresponding event lands.
        self._lf_trace_id: str | None = None
        self._lf_open_generations: dict[int, Any] = {}
        self._lf_open_tool_spans: dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_langfuse_error(self, where: str, marker: _LangfuseErrorMarker) -> None:
        """Best-effort: log a langfuse SDK error to JSONL."""
        try:
            self.logger._append({
                "event": "langfuse_error",
                "ts": self.logger._now_iso(),
                "where": where,
                "error": str(marker.error),
                "error_type": type(marker.error).__name__,
            })
        except Exception:
            pass

    def _new_span_context(self) -> Any:
        """Return a fresh span context if langfuse is active, else None."""
        if not self.langfuse:
            return None
        # langfuse v3: span() returns the span object whose context manager is
        # the span itself; we don't actually use the cm — we call .end()
        # explicitly on the returned handle. Keeping the call shape simple.
        try:
            return self.langfuse.span(name="tool_call")
        except Exception as e:
            self._log_langfuse_error("span()", _LangfuseErrorMarker(e))
            return None

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def before_agent(self, state, runtime):
        self._agent_start_time = time.monotonic()
        messages = state.get("messages", [])
        self.logger.log_agent_event(
            "start",
            detail=f"initial_messages={len(messages)}",
        )

        if self.langfuse:
            try:
                session_id = self.logger.session_dir.name
                initial_content = ""
                if messages and hasattr(messages[-1], "content"):
                    content = messages[-1].content
                    initial_content = content if isinstance(content, str) else str(content)
                # Update the current trace with metadata. Langfuse v3 creates a
                # trace implicitly on first observation; we don't pre-create it.
                self.langfuse.update_current_observation(
                    metadata={
                        "session_id": session_id,
                        "initial_message_preview": initial_content[:500],
                    },
                )
            except Exception as e:
                self._log_langfuse_error("before_agent.update", _LangfuseErrorMarker(e))

    def after_agent(self, state, runtime):
        elapsed = time.monotonic() - self._agent_start_time if self._agent_start_time else 0
        self.logger.log_agent_event(
            "end",
            detail=(
                f"llm_calls={self._llm_call_count}, "
                f"tool_calls={self._tool_call_count}, "
                f"prompt_tokens={self._total_prompt_tokens}, "
                f"completion_tokens={self._total_completion_tokens}, "
                f"elapsed_s={round(elapsed, 1)}"
            ),
        )
        self.logger.log_token_summary(
            total_prompt=self._total_prompt_tokens,
            total_completion=self._total_completion_tokens,
            llm_calls=self._llm_call_count,
        )

        if self.langfuse:
            try:
                self.langfuse.update_current_observation(
                    metadata={
                        "llm_calls": self._llm_call_count,
                        "tool_calls": self._tool_call_count,
                        "total_prompt_tokens": self._total_prompt_tokens,
                        "total_completion_tokens": self._total_completion_tokens,
                        "elapsed_s": round(elapsed, 1),
                    },
                )
                # CRITICAL: ship buffered spans before the run ends.
                self.langfuse.flush()
            except Exception as e:
                self._log_langfuse_error("after_agent.flush", _LangfuseErrorMarker(e))

    # ------------------------------------------------------------------
    # LLM calls
    # ------------------------------------------------------------------

    def before_model(self, state, runtime):
        messages = state.get("messages", [])
        model_name = getattr(runtime, "model_name", None) or "unknown"
        self.logger._append({
            "event": "llm_call_start",
            "ts": self.logger._now_iso(),
            "llm_call_index": self._llm_call_count,
            "message_count": len(messages),
            "model": model_name,
        })

    def wrap_model_call(self, request, handler):
        start = time.monotonic()
        response = handler(request)
        elapsed = time.monotonic() - start

        # Extract token usage from AIMessage
        prompt_tokens = 0
        completion_tokens = 0
        response_preview = ""
        model_name = "unknown"

        if hasattr(request, "model"):
            model_name = getattr(request.model, "model_name", None) or str(request.model)

        if hasattr(response, "result") and response.result:
            for msg in response.result:
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    prompt_tokens += msg.usage_metadata.get("input_tokens", 0)
                    completion_tokens += msg.usage_metadata.get("output_tokens", 0)
                if hasattr(msg, "content") and msg.content:
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    response_preview = content[:500]

        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._llm_call_count += 1

        self.logger.log_llm_call(
            step=self._llm_call_count,
            model_name=model_name,
            message_count=len(request.messages),
            latency_s=elapsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            response_preview=response_preview,
        )

        # Langfuse: emit a generation observation for this LLM call
        if self.langfuse:
            try:
                gen = self.langfuse.generation(
                    name="llm_call",
                    model=model_name,
                    input=[{"role": "user", "content": str(m.content)[:300]}
                           for m in request.messages[-3:] if hasattr(m, "content")],
                    output=response_preview,
                    usage={
                        "input": prompt_tokens,
                        "output": completion_tokens,
                        "total": prompt_tokens + completion_tokens,
                    },
                    metadata={
                        "latency_s": round(elapsed, 3),
                        "step": self._llm_call_count,
                    },
                )
                # end the generation explicitly so timing is captured
                try:
                    gen.end()
                except Exception:
                    pass
            except Exception as e:
                self._log_langfuse_error("generation()", _LangfuseErrorMarker(e))

        return response

    def after_model(self, state, runtime):
        messages = state.get("messages", [])
        if messages:
            last = messages[-1]
            content = ""
            if hasattr(last, "content") and last.content:
                content = last.content if isinstance(last.content, str) else str(last.content)
            self.logger._append({
                "event": "llm_response",
                "ts": self.logger._now_iso(),
                "llm_call_index": self._llm_call_count,
                "role": type(last).__name__,
                "content_preview": content[:300],
                "has_tool_calls": hasattr(last, "tool_calls") and bool(getattr(last, "tool_calls", None)),
            })

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------

    def wrap_tool_call(self, request, handler):
        start = time.monotonic()
        tool_name = "unknown"
        tool_args = {}

        try:
            if hasattr(request, "tool_call") and hasattr(request.tool_call, "name"):
                tool_name = request.tool_call.name
                tool_args = request.tool_call.args
            elif isinstance(request, dict):
                tool_name = request.get("name", request.get("tool", "unknown"))
                tool_args = request.get("args", request.get("input", {}))
            elif hasattr(request, "name"):
                tool_name = request.name
                tool_args = getattr(request, "args", {})
        except Exception:
            pass

        # Langfuse: open a span for this tool call (closed on success/error below)
        tool_span = None
        if self.langfuse:
            try:
                tool_span = self.langfuse.span(
                    name=f"tool:{tool_name}",
                    input={"args": _safe_repr(tool_args)},
                )
            except Exception as e:
                self._log_langfuse_error("tool.span", _LangfuseErrorMarker(e))

        error = None
        try:
            result = handler(request)
        except Exception as e:
            error = e
            result = None

        elapsed = time.monotonic() - start
        self._tool_call_count += 1

        if error:
            self.logger._append({
                "event": "tool_error",
                "ts": self.logger._now_iso(),
                "tool": tool_name,
                "input": tool_args,
                "error": str(error),
                "error_type": type(error).__name__,
                "latency_s": round(elapsed, 3),
            })

            # Langfuse: mark the span as failed
            if tool_span is not None:
                try:
                    tool_span.update(
                        output={"error": str(error), "error_type": type(error).__name__},
                        level="ERROR",
                        status_message=str(error)[:200],
                    )
                    tool_span.end()
                except Exception as e:
                    self._log_langfuse_error("tool.span.end(error)", _LangfuseErrorMarker(e))

            raise error

        # Log successful tool call
        output_preview = ""
        if hasattr(result, "content") and result.content:
            output_preview = result.content[:500] if isinstance(result.content, str) else str(result.content)[:500]

        self.logger._append({
            "event": "tool_call_detailed",
            "ts": self.logger._now_iso(),
            "tool": tool_name,
            "input": tool_args,
            "output_preview": output_preview,
            "latency_s": round(elapsed, 3),
        })

        # Langfuse: close the tool span with the result
        if tool_span is not None:
            try:
                tool_span.update(
                    output={"preview": output_preview[:500]},
                    metadata={"latency_s": round(elapsed, 3)},
                )
                tool_span.end()
            except Exception as e:
                self._log_langfuse_error("tool.span.end(ok)", _LangfuseErrorMarker(e))

        return result


def _safe_repr(value: Any, max_len: int = 2000) -> str:
    """Compact repr for langfuse input fields — keep spans small."""
    try:
        s = repr(value)
    except Exception:
        s = str(value)
    if len(s) > max_len:
        s = s[:max_len] + f"... ({len(s) - max_len} chars truncated)"
    return s