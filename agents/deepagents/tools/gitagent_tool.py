"""GitAgent CLI wrappers for worktree isolation and proposal management."""
import json
import subprocess
from pathlib import Path


def _run_gitagent(args: list[str], timeout: int = 60) -> dict:
    """Run a gitagent command and return parsed output."""
    try:
        result = subprocess.run(
            ["gitagent"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}
    except FileNotFoundError:
        return {"returncode": -1, "stdout": "", "stderr": "gitagent CLI not found"}


def gitagent_spawn(
    feature: str,
    agent_id: str,
    role: str,
    brief: str,
) -> str:
    """Spawn a worker agent in an isolated gitagent worktree.

    Args:
        feature: The feature name (e.g. "deepagents-orchestrator").
        agent_id: Unique agent identifier (e.g. "abm-worker-1").
        role: Short role description.
        brief: The task brief for the worker.

    Returns:
        JSON with agent_id, worktree path, and status.
    """
    # Ensure feature session exists
    _run_gitagent(["start", "--feature", feature])

    # Spawn the agent
    result = _run_gitagent([
        "spawn", "--feature", feature,
        "--id", agent_id, "--role", role,
    ])

    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})

    # Parse worktree path from output — look for a line containing the worktree path
    worktree_path = None
    for line in result["stdout"].splitlines():
        if "worktree" in line.lower() or "/" in line:
            # Try to extract path
            parts = line.split()
            for p in parts:
                if Path(p).is_dir():
                    worktree_path = p
                    break
        if worktree_path:
            break

    # Write the brief to the worktree if path found
    brief_file = None
    if worktree_path:
        brief_file = Path(worktree_path) / "BRIEF.md"
        brief_file.write_text(f"# Worker Brief: {agent_id}\n\n{brief}\n")

    return json.dumps({
        "agent_id": agent_id,
        "worktree": worktree_path,
        "status": "spawned",
        "brief_file": str(brief_file) if worktree_path else None,
        "raw_output": result["stdout"],
    })


def gitagent_proposals(feature: str) -> str:
    """List all proposals for a feature.

    Args:
        feature: The feature name.

    Returns:
        JSON list of proposals with their status.
    """
    result = _run_gitagent(["proposals", "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"proposals": result["stdout"], "status": "ok"})


def gitagent_integrate(feature: str) -> str:
    """Apply all accepted proposals onto the integration worktree.

    Args:
        feature: The feature name.

    Returns:
        JSON with integration result.
    """
    result = _run_gitagent(["integrate", "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"result": result["stdout"], "status": "integrated"})


def gitagent_finalize(feature: str, message: str) -> str:
    """Create one clean commit on main from all accepted proposals.

    Args:
        feature: The feature name.
        message: The commit message.

    Returns:
        JSON with finalize result.
    """
    result = _run_gitagent([
        "finalize", "--feature", feature,
        "--message", message,
    ])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"result": result["stdout"], "status": "finalized"})
