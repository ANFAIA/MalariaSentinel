"""ObservabilityMiddleware — hooks into deepagents lifecycle for full tracing.

Captures: LLM calls (model, tokens, latency), tool calls (name, args, result, errors),
agent lifecycle events, and cumulative token usage.

Sinks (fan-out):
1. SessionLogger → JSONL in `runs/<session>/session.jsonl` (always on)
2. langfuse.Langfuse → self-hosted langfuse UI (opt-in via --tracing langfuse)

A sink failure never aborts the run — errors are logged to JSONL and ignored.

Langfuse SDK: tested against langfuse>=4.0. We use `start_as_current_observation`
to open a top-level span in `before_agent`, capture its `trace_id` and `id`,
then pass `trace_context=TraceContext(trace_id=..., parent_span_id=...)` to
every child observation in `wrap_model_call` / `wrap_tool_call`. This is more
robust than relying on OpenTelemetry context propagation across the langchain
middleware hook boundaries (which doesn't survive the agent's internal
state-machine transitions).
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
        # v4: a top-level span IS the trace. We enter it as a context manager
        # in before_agent so we get a stable trace_id, then pass that trace_id
        # + the root span's id to every child observation via trace_context.
        # We exit the context manager in after_agent.
        self._lf_root_cm: Any = None
        self._lf_root_span: Any = None
        self._lf_trace_id: str | None = None
        self._lf_root_span_id: str | None = None
        self._trace_context: Any = None

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
        # Langfuse v4: use start_observation(as_type=...). Returns a span
        # object with .update() and .end() — we don't enter a cm, we call
        # .end() explicitly when the corresponding tool event lands.
        try:
            return self.langfuse.start_observation(as_type="span", name="tool_call")
        except Exception as e:
            self._log_langfuse_error("start_observation(span)", _LangfuseErrorMarker(e))
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
                # Open the top-level span as a context manager. We need
                # the trace_id and root span id to attach children explicitly
                # — OTel context doesn't propagate reliably across the
                # langchain middleware hook boundaries.
                self._lf_root_cm = self.langfuse.start_as_current_observation(
                    as_type="span",
                    name="janus_session",
                    metadata={
                        "session_id": session_id,
                        "initial_message_preview": initial_content[:500],
                    },
                )
                self._lf_root_span = self._lf_root_cm.__enter__()
                self._lf_trace_id = getattr(self._lf_root_span, "trace_id", None)
                self._lf_root_span_id = getattr(self._lf_root_span, "id", None)
                # Pre-build a TraceContext so children can attach without
                # re-resolving on every call. Import here to keep import
                # cost off the hot path when langfuse is disabled.
                if self._lf_trace_id:
                    from langfuse.types import TraceContext
                    self._trace_context = TraceContext(
                        trace_id=self._lf_trace_id,
                        parent_span_id=self._lf_root_span_id,
                    )
            except Exception as e:
                self._log_langfuse_error("before_agent.root_span", _LangfuseErrorMarker(e))
                self._lf_root_span = None
                self._lf_root_cm = None
                self._lf_trace_id = None
                self._lf_root_span_id = None
                self._trace_context = None

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
                if self._lf_root_span is not None:
                    self._lf_root_span.update(
                        metadata={
                            "llm_calls": self._llm_call_count,
                            "tool_calls": self._tool_call_count,
                            "total_prompt_tokens": self._total_prompt_tokens,
                            "total_completion_tokens": self._total_completion_tokens,
                            "elapsed_s": round(elapsed, 1),
                        },
                    )
                # Exit the root span context (also calls .end() on the span).
                if self._lf_root_cm is not None:
                    self._lf_root_cm.__exit__(None, None, None)
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

        # Langfuse: emit a generation observation for this LLM call.
        # Pass trace_context explicitly so this observation nests under the
        # root span from before_agent — OTel context is unreliable across
        # the langchain middleware boundaries.
        if self.langfuse and self._trace_context is not None:
            try:
                gen = self.langfuse.start_observation(
                    as_type="generation",
                    name="llm_call",
                    model=model_name,
                    input=[{"role": "user", "content": str(m.content)[:300]}
                           for m in request.messages[-3:] if hasattr(m, "content")],
                    output=response_preview,
                    usage_details={
                        "input": prompt_tokens,
                        "output": completion_tokens,
                        "total": prompt_tokens + completion_tokens,
                    },
                    metadata={
                        "latency_s": round(elapsed, 3),
                        "step": self._llm_call_count,
                    },
                    trace_context=self._trace_context,
                )
                # end the generation explicitly so timing is captured
                try:
                    gen.end()
                except Exception:
                    pass
            except Exception as e:
                self._log_langfuse_error("start_observation(generation)", _LangfuseErrorMarker(e))

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
        tool_args: dict = {}

        # Extract tool name and args from the request.
        # request.tool_call is a ToolCall TypedDict (dict), not an object.
        # Access via .get() for safety; fall back to attribute access for
        # any non-dict tool_call implementations.
        try:
            tc = getattr(request, "tool_call", None)
            if tc is None and isinstance(request, dict):
                tc = request.get("tool_call")
            if isinstance(tc, dict):
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("args", {}) or {}
            elif tc is not None:
                tool_name = getattr(tc, "name", "unknown")
                tool_args = getattr(tc, "args", {}) or {}
        except Exception:
            pass

        # Langfuse: open a span for this tool call (closed on success/error below).
        # trace_context forces the span under the root — context propagation
        # is unreliable across the middleware hook boundary.
        tool_span = None
        if self.langfuse and self._trace_context is not None:
            try:
                tool_span = self.langfuse.start_observation(
                    as_type="span",
                    name=f"tool:{tool_name}",
                    input={"args": _safe_repr(tool_args)},
                    trace_context=self._trace_context,
                )
            except Exception as e:
                self._log_langfuse_error("tool.start_observation(span)", _LangfuseErrorMarker(e))

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

        # Extract output preview — result may be ToolMessage (str or list
        # content blocks), a plain string, or something else entirely.
        output_preview = _extract_content_preview(result)

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


def _extract_content_preview(result: Any, max_len: int = 500) -> str:
    """Extract a human-readable preview from a tool result.

    Handles: ToolMessage (str or list content blocks), plain strings,
    dicts with common keys, and anything with a .content attribute.
    """
    try:
        # ToolMessage or anything with .content
        content = getattr(result, "content", None)
        if content is None and isinstance(result, dict):
            content = result.get("content") or result.get("output") or result.get("result")
        if content is None:
            content = str(result)[:max_len]

        # Normalize to string
        if isinstance(content, str):
            return content[:max_len]
        if isinstance(content, list):
            # List of content blocks — extract text parts
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", str(block)))
                else:
                    parts.append(str(block))
            return " ".join(parts)[:max_len]
        return str(content)[:max_len]
    except Exception:
        return ""