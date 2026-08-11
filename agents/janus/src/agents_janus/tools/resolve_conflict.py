"""resolve_conflict — self-fork tool for peer coordination.

When an agent receives a conflict (via InboxCheckMiddleware's CONFLICT
DETECTED marker), it calls this tool to:

1. Fork its current conversation into an isolated thread
2. Run conflict resolution (SCAN evaluation, peer communication)
3. Extract a structured resolution document
4. Inject the resolution into the original thread
5. Clean up the fork thread
6. Return the resolution summary

The tool uses a lazy agent reference — the agent graph is captured after
creation via set_agent_ref(). The tool cannot be created before the agent.

Architecture:
- Factory function make_resolve_conflict_tool() creates the tool
- set_agent_ref() is called after create_deep_agent() to provide the agent
- The tool forks via agent.get_state() + agent.update_state() + agent.invoke()
- Recursion guard prevents nested fork calls
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger("agents_janus.tools.resolve_conflict")

# Standardized conflict resolution document schema
CONFLICT_RESOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "resolution_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "conflict": {
            "type": "object",
            "properties": {
                "from_agent": {"type": "string"},
                "message": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["from_agent", "message", "files"],
        },
        "scan_evaluation": {
            "type": "object",
            "properties": {
                "peer_intent": {"type": "string"},
                "peer_edits_summary": {"type": "string"},
                "my_goal": {"type": "string"},
                "decision_rationale": {"type": "string"},
            },
        },
        "decision": {
            "type": "string",
            "enum": ["adapt", "counter_propose", "both", "escalate"],
        },
        "actions_taken": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "target": {"type": "string"},
                    "result": {"type": "string"},
                },
            },
        },
        "files_kept_by_me": {"type": "array", "items": {"type": "string"}},
        "files_reverted_by_me": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "resolution_id",
        "timestamp",
        "conflict",
        "decision",
        "summary",
    ],
}

# Module-level mutable container for lazy agent reference.
# Set by set_agent_ref() after create_deep_agent() returns.
_agent_ref: dict[str, Any] = {"agent": None, "config": None}

# Recursion guard — prevents nested fork calls
_fork_depth: int = 0
_MAX_FORK_DEPTH = 1


def set_agent_ref(agent: Any, config: dict) -> None:
    """Set the agent graph and config reference. Called after create_deep_agent."""
    _agent_ref["agent"] = agent
    _agent_ref["config"] = config


def make_resolve_conflict_tool():
    """Create a resolve_conflict tool bound to the agent's own graph.

    The tool uses a lazy reference to the agent — the agent graph is captured
    after creation via set_agent_ref(). The tool cannot run until the ref is set.
    """
    from langchain_core.tools import tool

    @tool
    def resolve_conflict(conflict_message: str, files: list[str]) -> str:
        """Fork your conversation, resolve the conflict, merge back, and clean up.

        Use this tool IMMEDIATELY when you see a CONFLICT DETECTED marker
        in a tool result. The tool:

        1. Forks your current conversation into an isolated thread
        2. Runs conflict resolution (SCAN evaluation, peer communication)
        3. Extracts a structured resolution document
        4. Injects the resolution into your current thread
        5. Cleans up the fork thread (memory freed)
        6. Returns the resolution summary so you can continue your task

        Args:
            conflict_message: The conflict description from the peer agent
            files: List of files involved in the conflict

        Returns:
            A structured JSON document (see CONFLICT_RESOLUTION_SCHEMA)
            containing the resolution summary, decisions, and next steps.
        """
        global _fork_depth

        agent = _agent_ref.get("agent")
        config = _agent_ref.get("config")

        if agent is None or config is None:
            return json.dumps({
                "resolution_id": f"no-agent-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "conflict": {
                    "from_agent": "unknown",
                    "message": conflict_message,
                    "files": files,
                },
                "decision": "escalate",
                "summary": "Agent reference not available. Escalating to orchestrator.",
                "actions_taken": [],
            })

        # Recursion guard
        if _fork_depth >= _MAX_FORK_DEPTH:
            return json.dumps({
                "resolution_id": f"recursive-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "conflict": {
                    "from_agent": "unknown",
                    "message": conflict_message,
                    "files": files,
                },
                "decision": "escalate",
                "summary": "Nested conflict detected. Escalating to orchestrator.",
                "actions_taken": [],
            })

        _fork_depth += 1
        fork_thread_id = f"conflict-{uuid.uuid4().hex[:8]}"

        try:
            resolution_doc = _run_fork_resolution(
                agent, config, conflict_message, files, fork_thread_id
            )
        except Exception as e:
            _log.error("Fork resolution failed: %s", e)
            resolution_doc = _make_escalation_doc(
                conflict_message, files, f"Fork resolution failed: {e}"
            )
        finally:
            _fork_depth -= 1
            # Best-effort cleanup
            try:
                if hasattr(agent, "get_checkpointer"):
                    cp = agent.get_checkpointer()
                    if cp and hasattr(cp, "delete_thread"):
                        cp.delete_thread(fork_thread_id)
            except Exception:
                pass

        # Inject resolution into original thread
        try:
            from langchain_core.messages import SystemMessage
            agent.update_state(config, {
                "messages": [SystemMessage(content=(
                    "CONFLICT RESOLVED via self-fork.\n\n"
                    f"Resolution document:\n{json.dumps(resolution_doc, indent=2)}\n\n"
                    "Continue your original task. The conflict has been resolved."
                ))]
            })
        except Exception as e:
            _log.warning("Could not inject resolution into original thread: %s", e)

        return json.dumps(resolution_doc, indent=2)

    return resolve_conflict


def _run_fork_resolution(
    agent: Any,
    config: dict,
    conflict_message: str,
    files: list[str],
    fork_thread_id: str,
) -> dict:
    """Run conflict resolution in an isolated fork thread."""
    from langchain_core.messages import HumanMessage

    # 1. Snapshot current state
    snapshot = agent.get_state(config)

    # 2. Create fork thread
    fork_config = {"configurable": {"thread_id": fork_thread_id}}

    # 3. Copy state to fork
    agent.update_state(fork_config, snapshot.values)

    # 4. Build resolution prompt with SCAN 7-question framework
    resolution_prompt = (
        "CONFLICT RESOLUTION MODE\n\n"
        f"Peer message: {conflict_message}\n"
        f"Affected files: {', '.join(files)}\n\n"
        "You are in an isolated fork. Do NOT trigger further conflicts.\n"
        "Do NOT edit any files directly from this fork — only communicate.\n\n"
        "Steps:\n"
        "1. Read peer intent via mcp__gitagent__list_intents()\n"
        "2. Read peer edits via mcp__gitagent__list_edits()\n"
        "3. Evaluate using SCAN framework (7 questions):\n"
        "   - What is the other agent trying to achieve?\n"
        "   - What is MY original goal?\n"
        "   - What exactly did they change?\n"
        "   - Options: A) Adapt, B) Counter-propose, C) Both\n"
        "   - Which rules are at risk?\n"
        "   - Failure mode?\n"
        "   - Negotiation vocabulary?\n"
        "4. Decide: adapt / counter-propose / both / escalate\n"
        "5. Communicate via mcp__gitagent__send_message()\n"
        "6. Provide your resolution as a JSON document matching this schema:\n"
        f"{json.dumps(CONFLICT_RESOLUTION_SCHEMA, indent=2)}\n\n"
        "Your FINAL message must be ONLY the JSON document."
    )

    agent.update_state(fork_config, {
        "messages": [HumanMessage(content=resolution_prompt)]
    })

    # 5. Run resolution in fork
    result = agent.invoke(None, fork_config)
    resolution_text = result["messages"][-1].content

    # 6. Parse resolution document
    try:
        resolution_doc = json.loads(resolution_text)
    except json.JSONDecodeError:
        resolution_doc = {
            "resolution_id": f"unstructured-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "conflict": {
                "from_agent": "unknown",
                "message": conflict_message,
                "files": files,
            },
            "decision": "unclear",
            "summary": resolution_text,
            "actions_taken": [],
        }

    return resolution_doc


def _make_escalation_doc(
    conflict_message: str,
    files: list[str],
    reason: str,
) -> dict:
    """Create an escalation document when fork resolution fails."""
    return {
        "resolution_id": f"escalation-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conflict": {
            "from_agent": "unknown",
            "message": conflict_message,
            "files": files,
        },
        "decision": "escalate",
        "summary": reason,
        "actions_taken": [],
    }
