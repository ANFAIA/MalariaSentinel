"""ObservabilityMiddleware — hooks into deepagents lifecycle for full tracing.

Captures: LLM calls (model, tokens, latency), tool calls (name, args, result, errors),
agent lifecycle events, and cumulative token usage.
"""
from __future__ import annotations

import time
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


class ObservabilityMiddleware(AgentMiddleware):
    """Logs every LLM call, tool call, and agent lifecycle event to SessionLogger."""

    def __init__(self, session_logger):
        self.logger = session_logger
        self._llm_call_count = 0
        self._tool_call_count = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._agent_start_time: float | None = None

    def before_agent(self, state, runtime):
        self._agent_start_time = time.monotonic()
        messages = state.get("messages", [])
        self.logger.log_agent_event(
            "start",
            detail=f"initial_messages={len(messages)}",
        )

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

        return result

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
