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

Tags (color-coded in Langfuse UI):
    agent:<role>    — orchestrator, abm, scoring, ingest, download, ...
    stage:<phase>   — start, decompose, dispatch, execute, monitor, finalize
    tool:<category> — gawt, abm, memory, user, pipeline, other
    env:<env>       — dev, staging, production
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


# ── Tool category mapping ──────────────────────────────────────────────
# Maps tool names to visual categories for Langfuse tags.
_TOOL_CATEGORIES: dict[str, str] = {
    # gawt MCP tools
    "mcp__gitagent__start_session": "gawt",
    "mcp__gitagent__finalize_session": "gawt",
    "mcp__gitagent__register_agent": "gawt",
    "mcp__gitagent__edit_file": "gawt",
    "mcp__gitagent__write_file": "gawt",
    "mcp__gitagent__read_file": "gawt",
    "mcp__gitagent__delete_file": "gawt",
    "mcp__gitagent__check_inbox": "gawt",
    "mcp__gitagent__send_message": "gawt",
    "mcp__gitagent__list_agents": "gawt",
    "mcp__gitagent__list_edits": "gawt",
    "mcp__gitagent__list_intents": "gawt",
    "mcp__gitagent__start_intent": "gawt",
    "mcp__gitagent__repurpose": "gawt",
    "mcp__gitagent__unregister_agent": "gawt",
    # ABM tools
    "abm_run": "abm",
    "abm_test": "abm",
    "abm_score": "abm",
    # Pipeline tools
    "pipeline_run_calibration": "pipeline",
    "pipeline_compare_scorecards": "pipeline",
    # Memory tools
    "memory_recall_kg": "memory",
    "memory_node": "memory",
    "memory_rel": "memory",
    "memory_query": "memory",
    # User interaction
    "ask_user": "user",
    # Dispatch delegation
    "delegate_to_dispatcher": "dispatch",
    "onboard_ask_subagent": "user",
    "onboard_run_abm": "pipeline",
    "onboard_run_stage": "pipeline",
    "onboard_run_pipeline": "pipeline",
    "onboard_status": "pipeline",
    "onboard_diagnose": "pipeline",
    "onboard_list_components": "pipeline",
    # Prompt tools
    "improve_prompt": "other",
    "opencode_search": "other",
}


def _categorize_tool(tool_name: str) -> str:
    """Return the visual category for a tool name."""
    if tool_name in _TOOL_CATEGORIES:
        return _TOOL_CATEGORIES[tool_name]
    # Heuristic: gawt MCP tools start with mcp__gitagent__
    if tool_name.startswith("mcp__gitagent__"):
        return "gawt"
    return "other"


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

    Langfuse traces are enriched with:
    - Tags: agent:<role>, stage:<phase>, tool:<category>, env:<env>
    - Metadata: session_id, goal, thread_id, iteration (propagated to children)
    - Scores: latency_s, token_efficiency, error_rate
    - Dispatch spans: one per subagent dispatch, nested under the root
    """

    def __init__(
        self,
        session_logger,
        langfuse_client=None,
        *,
        goal: str = "",
        thread_id: str = "",
        env: str = "",
        iteration: int = 0,
        mode: str = "dispatcher",
    ):
        self.logger = session_logger
        self.langfuse = langfuse_client
        self._llm_call_count = 0
        self._tool_call_count = 0
        self._error_count = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._agent_start_time: float | None = None

        # Session context (enriches tags + metadata)
        self._goal = goal
        self._thread_id = thread_id
        self._env = env or os.environ.get("JANUS_ENV", "dev")
        self._iteration = iteration
        self._mode = mode  # centinela | dispatcher

        # Thread-local agent role — each subagent thread gets its own role
        # without cross-contamination when dispatching in parallel.
        self._thread_local = threading.local()

        # Langfuse handle holders
        self._lf_root_cm: Any = None
        self._lf_root_span: Any = None
        self._lf_trace_id: str | None = None
        self._lf_root_span_id: str | None = None
        self._trace_context: Any = None

        # Dispatch spans — one per specialist, keyed by agent_role
        self._lf_dispatch_spans: dict[str, Any] = {}
        self._lf_dispatch_cms: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public: set current agent role (called by orchestrator before dispatch)
    # ------------------------------------------------------------------

    @property
    def _current_agent_role(self) -> str:
        """Thread-local agent role. Each subagent thread has its own."""
        return getattr(self._thread_local, "agent_role", "orchestrator")

    @_current_agent_role.setter
    def _current_agent_role(self, role: str) -> None:
        self._thread_local.agent_role = role

    def set_agent_role(self, role: str) -> None:
        """Set the current agent role for tag coloring.

        Call this before each subagent dispatch so LLM calls and tool calls
        get the right `agent:<role>` tag in Langfuse.
        """
        self._current_agent_role = role

    def get_trace_url(self) -> str | None:
        """Return the Langfuse trace URL for this session, or None."""
        if not self.langfuse or not self._lf_trace_id:
            return None
        host = getattr(self.langfuse, "base_url", None) or os.environ.get(
            "LANGFUSE_HOST", os.environ.get("LANGFUSE_BASE_URL", "")
        )
        if not host:
            return None
        return f"{host.rstrip('/')}/trace/{self._lf_trace_id}"

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

    def _build_base_tags(self, extra: list[str] | None = None) -> list[str]:
        """Build the base tag set for the current agent role + env."""
        tags = [
            f"agent:{self._current_agent_role}",
            f"env:{self._env}",
            f"mode:{self._mode}",
        ]
        if extra:
            tags.extend(extra)
        return tags

    # ------------------------------------------------------------------
    # Dispatch spans — one per specialist
    # ------------------------------------------------------------------

    def start_dispatch_span(self, agent_role: str, task: str = "") -> None:
        """Open a Langfuse span for a specialist dispatch.

        Call this in the orchestrator when dispatching a specialist. All
        LLM calls and tool calls from that specialist will be nested under
        this span (via trace_context parent re-pointing).
        """
        if not self.langfuse or self._trace_context is None:
            return
        try:
            cm = self.langfuse.start_as_current_observation(
                as_type="span",
                name=f"dispatch:{agent_role}",
                input={"task": task[:500]} if task else None,
                metadata={
                    "agent_role": agent_role,
                    "stage": "dispatch",
                    "tags": [f"agent:{agent_role}", f"env:{self._env}", "stage:dispatch"],
                },
                trace_context=self._trace_context,
            )
            span = cm.__enter__()
            self._lf_dispatch_cms[agent_role] = cm
            self._lf_dispatch_spans[agent_role] = span
        except Exception as e:
            self._log_langfuse_error(f"start_dispatch({agent_role})", _LangfuseErrorMarker(e))

    def end_dispatch_span(self, agent_role: str, *, error: str = "") -> None:
        """Close the dispatch span for a specialist."""
        cm = self._lf_dispatch_cms.pop(agent_role, None)
        span = self._lf_dispatch_spans.pop(agent_role, None)
        if cm is None or span is None:
            return
        try:
            if error:
                span.update(
                    output={"error": error[:500]},
                    level="ERROR",
                    status_message=error[:200],
                )
            cm.__exit__(None, None, None)
        except Exception as e:
            self._log_langfuse_error(f"end_dispatch({agent_role})", _LangfuseErrorMarker(e))

    def _get_dispatch_context(self, agent_role: str) -> Any:
        """Return the trace_context for a dispatch span, or fall back to root."""
        span = self._lf_dispatch_spans.get(agent_role)
        if span is not None:
            try:
                from langfuse.types import TraceContext
                return TraceContext(
                    trace_id=self._lf_trace_id,
                    parent_span_id=getattr(span, "id", self._lf_root_span_id),
                )
            except ImportError:
                return self._trace_context
        return self._trace_context

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

                base_tags = [
                    "agent:orchestrator",
                    f"env:{self._env}",
                    f"mode:{self._mode}",
                    "stage:start",
                ]
                if self._goal:
                    base_tags.append(f"goal:{_slugify(self._goal[:50])}")

                root_metadata = {
                    "session_id": session_id,
                    "initial_message_preview": initial_content[:500],
                    "env": self._env,
                }
                if self._goal:
                    root_metadata["goal"] = self._goal[:500]
                if self._thread_id:
                    root_metadata["thread_id"] = self._thread_id
                if self._iteration:
                    root_metadata["iteration"] = self._iteration

                # Open the top-level span as a context manager.
                root_metadata["tags"] = base_tags
                self._lf_root_cm = self.langfuse.start_as_current_observation(
                    as_type="span",
                    name="janus_session",
                    metadata=root_metadata,
                )
                self._lf_root_span = self._lf_root_cm.__enter__()
                self._lf_trace_id = getattr(self._lf_root_span, "trace_id", None)
                self._lf_root_span_id = getattr(self._lf_root_span, "id", None)

                if self._lf_trace_id:
                    try:
                        from langfuse.types import TraceContext
                        self._trace_context = TraceContext(
                            trace_id=self._lf_trace_id,
                            parent_span_id=self._lf_root_span_id,
                        )
                    except ImportError:
                        self._trace_context = None
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
                    summary_metadata = {
                        "llm_calls": self._llm_call_count,
                        "tool_calls": self._tool_call_count,
                        "error_count": self._error_count,
                        "total_prompt_tokens": self._total_prompt_tokens,
                        "total_completion_tokens": self._total_completion_tokens,
                        "elapsed_s": round(elapsed, 1),
                    }
                    self._lf_root_span.update(
                        metadata=summary_metadata,
                        output={"summary": f"Session completed in {round(elapsed, 1)}s"},
                    )

                    # Emit session-level scores
                    try:
                        self.langfuse.score(
                            name="latency_s",
                            value=round(elapsed, 2),
                            comment=f"Total session latency: {round(elapsed, 1)}s",
                            trace_id=self._lf_trace_id,
                        )
                    except Exception:
                        pass

                    total_tokens = self._total_prompt_tokens + self._total_completion_tokens
                    if self._tool_call_count > 0:
                        try:
                            self.langfuse.score(
                                name="token_efficiency",
                                value=round(total_tokens / self._tool_call_count, 1),
                                comment=f"{total_tokens} tokens / {self._tool_call_count} tool calls",
                                trace_id=self._lf_trace_id,
                            )
                        except Exception:
                            pass

                    total_calls = self._llm_call_count + self._tool_call_count
                    if total_calls > 0:
                        try:
                            self.langfuse.score(
                                name="error_rate",
                                value=round(self._error_count / total_calls, 4),
                                comment=f"{self._error_count} errors / {total_calls} total calls",
                                trace_id=self._lf_trace_id,
                            )
                        except Exception:
                            pass

                # Exit the root span context
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
            "agent_role": self._current_agent_role,
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

        # Langfuse: emit a generation observation with tags
        if self.langfuse and self._trace_context is not None:
            try:
                tags = self._build_base_tags(["stage:execute", "tool:llm"])

                ctx = self._get_dispatch_context(self._current_agent_role)

                gen = self.langfuse.start_observation(
                    as_type="generation",
                    name=f"llm:{self._current_agent_role}",
                    model=model_name,
                    input=[{"role": "system", "content": str(request.system_message)[:500]}
                           ] + [{"role": "user", "content": str(m.content)[:300]}
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
                        "agent_role": self._current_agent_role,
                        "tags": tags,
                    },
                    trace_context=ctx,
                )
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
                "agent_role": self._current_agent_role,
            })

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------

    def wrap_tool_call(self, request, handler):
        start = time.monotonic()
        tool_name = "unknown"
        tool_args: dict = {}

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

        tool_category = _categorize_tool(tool_name)

        # Langfuse: open a span for this tool call
        tool_span = None
        if self.langfuse and self._trace_context is not None:
            try:
                tags = self._build_base_tags([
                    "stage:execute",
                    f"tool:{tool_category}",
                ])

                ctx = self._get_dispatch_context(self._current_agent_role)

                tool_span = self.langfuse.start_observation(
                    as_type="span",
                    name=f"tool:{tool_name}",
                    input={"args": _safe_repr(tool_args)},
                    metadata={
                        "tool_name": tool_name,
                        "tool_category": tool_category,
                        "agent_role": self._current_agent_role,
                        "tags": tags,
                    },
                    trace_context=ctx,
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
            self._error_count += 1
            self.logger._append({
                "event": "tool_error",
                "ts": self.logger._now_iso(),
                "tool": tool_name,
                "input": tool_args,
                "error": str(error),
                "error_type": type(error).__name__,
                "latency_s": round(elapsed, 3),
                "agent_role": self._current_agent_role,
            })

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

        output_preview = _extract_content_preview(result)

        self.logger._append({
            "event": "tool_call_detailed",
            "ts": self.logger._now_iso(),
            "tool": tool_name,
            "input": tool_args,
            "output_preview": output_preview,
            "latency_s": round(elapsed, 3),
            "agent_role": self._current_agent_role,
            "tool_category": tool_category,
        })

        if tool_span is not None:
            try:
                tool_span.update(
                    output={"preview": output_preview[:500]},
                    metadata={
                        "latency_s": round(elapsed, 3),
                        "tool_category": tool_category,
                    },
                )
                tool_span.end()
            except Exception as e:
                self._log_langfuse_error("tool.span.end(ok)", _LangfuseErrorMarker(e))

        return result


class SubAgentObservabilityMiddleware(AgentMiddleware):
    """Thin wrapper that delegates to ObservabilityMiddleware with auto role-set.

    When a subagent is invoked, deepagents calls before_agent/wrap_model_call/etc
    on this middleware. We detect the subagent name from state metadata and call
    set_agent_role on the shared ObservabilityMiddleware instance, so Langfuse
    observations get the correct agent:<role> tag and nest under the dispatch span.

    IMPORTANT: This middleware does NOT open/close root spans — the orchestrator's
    ObservabilityMiddleware handles that. We only manage:
    - set_agent_role (for tag coloring)
    - dispatch span open/close
    - LLM call / tool call delegation (which uses _get_dispatch_context)
    """

    def __init__(self, obs: ObservabilityMiddleware, agent_role: str):
        self._obs = obs
        self._agent_role = agent_role

    def before_agent(self, state, runtime):
        self._obs.set_agent_role(self._agent_role)
        self._obs._agent_start_time = time.monotonic()
        self._obs.logger.log_agent_event(
            "start",
            detail=f"subagent={self._agent_role}",
        )
        # Open dispatch span in Langfuse (nested under root span via trace_context)
        self._obs.start_dispatch_span(self._agent_role)

    def after_agent(self, state, runtime):
        elapsed = time.monotonic() - self._obs._agent_start_time if self._obs._agent_start_time else 0
        self._obs.logger.log_agent_event(
            "end",
            detail=f"subagent={self._agent_role}, elapsed_s={round(elapsed, 1)}",
        )
        self._obs.end_dispatch_span(self._agent_role)
        # Restore orchestrator's root trace context (subagent overwrote it)
        self._obs.set_agent_role("orchestrator")

    def before_model(self, state, runtime):
        self._obs.before_model(state, runtime)

    def after_model(self, state, runtime):
        self._obs.after_model(state, runtime)

    def wrap_model_call(self, request, handler):
        return self._obs.wrap_model_call(request, handler)

    def wrap_tool_call(self, request, handler):
        return self._obs.wrap_tool_call(request, handler)


# ── Utility functions ───────────────────────────────────────────────────


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
        content = getattr(result, "content", None)
        if content is None and isinstance(result, dict):
            content = result.get("content") or result.get("output") or result.get("result")
        if content is None:
            content = str(result)[:max_len]

        if isinstance(content, str):
            return content[:max_len]
        if isinstance(content, list):
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


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug for use in Langfuse tags."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:50]
