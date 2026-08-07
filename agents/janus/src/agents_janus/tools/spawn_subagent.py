"""spawn_subagent — local Python tool for cross-specialist delegation.

Used by specialists when they discover they need another specialist.
NOT a gitagent tool. NOT an MCP server. Just a function.

Internally uses:
  - mcp__gitagent__register_agent (gawt MCP)
  - deepagents task (same process as caller)
  - read/write manifest (.gitagent/sessions/<feature>/plan.json)
"""
from __future__ import annotations

import json
from pathlib import Path


def spawn_subagent(
    feature: str,
    requested_agent_id: str,
    role: str,
    task: str,
    context: dict | None = None,
    return_blocking: bool = True,
) -> str:
    """Spawn a new specialist agent under the current gawt session.

    Args:
        feature: The gawt session feature key (matches the manifest directory).
        requested_agent_id: A hint for the agent's ID. gawt assigns the real one.
        role: The specialist role (e.g., "abm", "scoring", "ingest").
        task: The task description for the new agent.
        context: Optional context dict (aoi, params, etc.).
        return_blocking: If True, wait for the new agent to finish.

    Returns:
        JSON with agent_id, summary, diff (if blocking).

    Flow:
      1. mcp__gitagent__register_agent(role=role) → real agent_id
      2. Append entry to .gitagent/sessions/<feature>/plan.json
      3. Spawn the specialist as a deepagents task (sync or async)
      4. If return_blocking: await completion, return {summary, diff}
    """
    from agents_janus.manifest import append_agent, get_manifest_path

    # NOTE: In the deepagents runtime, mcp__gitagent__register_agent is
    # available as an MCP tool. This function is called by specialists
    # who have access to the MCP tools. The actual registration is done
    # by the specialist's LLM calling mcp__gitagent__register_agent.
    #
    # This function orchestrates the manifest update and task spawn.
    # The actual MCP call and deepagents task call happen in the
    # specialist's runtime context.

    # 1. Update manifest with the new agent entry
    manifest_path = get_manifest_path(feature)
    append_agent(
        manifest_path,
        {
            "requested_id": requested_agent_id,
            "agent_id": None,  # filled by the specialist after register_agent
            "role": role,
            "task": task,
            "context": context or {},
            "spawned_by": "subagent",
            "propose_order": None,
            "depends_on": [],
            "status": "spawned",
        },
    )

    # 2. Return instructions for the specialist to complete the spawn
    # The specialist will:
    #   a. Call mcp__gitagent__register_agent(role=role) to get agent_id
    #   b. Call mcp__gitagent__start_intent(agent_id, task)
    #   c. Execute the task
    #   d. Return the result
    return json.dumps({
        "status": "spawn_requested",
        "requested_agent_id": requested_agent_id,
        "role": role,
        "task": task,
        "manifest_path": str(manifest_path),
        "blocking": return_blocking,
        "instructions": (
            f"Register with gawt: mcp__gitagent__register_agent(role='{role}'). "
            f"Then set intent: mcp__gitagent__start_intent(agent_id, '{task}'). "
            f"Then execute the task. When done, unregister: "
            f"mcp__gitagent__unregister_agent(agent_id)."
        ),
    })
