"""GitAgent CLI wrappers for worktree isolation and proposal management."""
import json
import subprocess
from pathlib import Path


def _run_gitagent(args: list[str], timeout: int = 120) -> dict:
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


# ── Session management ──────────────────────────────────────────────

def gitagent_init() -> str:
    """Initialize gitagent in the repo. Idempotent (errors on re-run but that's OK)."""
    result = _run_gitagent(["init"])
    if result["returncode"] != 0 and "already initialized" in result["stderr"].lower():
        return json.dumps({"status": "already_initialized"})
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"status": "initialized"})


def gitagent_start(feature: str) -> str:
    """Open a session for a feature. Errors if session already active."""
    result = _run_gitagent(["start", "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"status": "started", "feature": feature, "raw": result["stdout"]})


# ── Agent management ────────────────────────────────────────────────

def gitagent_spawn(feature: str, agent_id: str, role: str = "") -> str:
    """Spawn a worker agent in an isolated gitagent worktree.

    Returns JSON with agent_id, worktree path, and status.
    The worktree path is parsed from the CLI output.
    """
    args = ["spawn", "--feature", feature, "--id", agent_id]
    if role:
        args.extend(["--role", role])

    result = _run_gitagent(args)
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})

    # Parse worktree path from output
    # Output format: "Agent <id> -> \n<path>"
    worktree_path = None
    for line in result["stdout"].splitlines():
        line = line.strip()
        if "/" in line and Path(line).is_dir():
            worktree_path = line
            break
        # Also try: line after "->"
        if "->" in line:
            candidate = line.split("->", 1)[1].strip()
            if candidate and Path(candidate).is_dir():
                worktree_path = candidate
                break

    return json.dumps({
        "agent_id": agent_id,
        "worktree": worktree_path,
        "status": "spawned",
        "feature": feature,
        "raw": result["stdout"],
    })


def gitagent_list_agents(feature: str) -> str:
    """List agents in a feature's session. Uses --json."""
    result = _run_gitagent(["list-agents", "--feature", feature, "--json"])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    try:
        return json.dumps({"agents": json.loads(result["stdout"]), "status": "ok"})
    except json.JSONDecodeError:
        return json.dumps({"raw": result["stdout"], "status": "ok"})


def gitagent_kill(agent_id: str, feature: str) -> str:
    """Kill a zombie agent's worktree."""
    result = _run_gitagent(["kill", agent_id, "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"agent_id": agent_id, "status": "killed", "feature": feature})


# ── Proposals ───────────────────────────────────────────────────────

def gitagent_proposals(feature: str) -> str:
    """List all proposals for a feature. Uses --json."""
    result = _run_gitagent(["proposals", "--feature", feature, "--json"])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    try:
        proposals = json.loads(result["stdout"])
        return json.dumps({"proposals": proposals, "count": len(proposals), "status": "ok"})
    except json.JSONDecodeError:
        return json.dumps({"raw": result["stdout"], "status": "ok"})


def gitagent_diff(proposal_id: str, feature: str) -> str:
    """Get raw diff for a proposal (pipe-friendly)."""
    result = _run_gitagent(["diff", proposal_id, "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"diff": result["stdout"], "proposal_id": proposal_id, "status": "ok"})


# ── Decision commands (no apply) ────────────────────────────────────

def gitagent_accept(proposal_id: str, feature: str) -> str:
    """Mark a proposal as accepted (decision only, does NOT apply)."""
    result = _run_gitagent(["accept", proposal_id, "--feature", feature])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"proposal_id": proposal_id, "status": "accepted", "feature": feature})


def gitagent_reject(proposal_id: str, feature: str, reason: str = "") -> str:
    """Reject a proposal (patch is not applied)."""
    args = ["reject", proposal_id, "--feature", feature]
    if reason:
        args.extend(["--reason", reason])
    result = _run_gitagent(args)
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"proposal_id": proposal_id, "status": "rejected", "feature": feature, "reason": reason})


def gitagent_revise(proposal_id: str, feature: str, feedback: str) -> str:
    """Send a proposal back for another iteration."""
    result = _run_gitagent([
        "revise", proposal_id,
        "--feature", feature,
        "--feedback", feedback,
    ])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"proposal_id": proposal_id, "status": "revised", "feature": feature, "feedback": feedback})


# ── Integration and finalization ────────────────────────────────────

def gitagent_integrate(feature: str) -> str:
    """Apply all accepted proposals onto the integration worktree. Uses --json."""
    result = _run_gitagent(["integrate", "--feature", feature, "--json"])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    try:
        return json.dumps({**json.loads(result["stdout"]), "status": "ok"})
    except json.JSONDecodeError:
        return json.dumps({"raw": result["stdout"], "status": "ok"})


def gitagent_finalize(feature: str, message: str, *, verify: bool = True) -> str:
    """Create one clean commit on main from all accepted proposals.

    Args:
        feature: The feature name.
        message: The commit message.
        verify: If True (default), show proposals and require user confirmation.
            If False, skip the approval prompt.
    """
    if verify:
        # Show what will be finalized
        proposals_result = _run_gitagent(["proposals", "--feature", feature, "--json"])
        summary = proposals_result.get("stdout", "No proposals found.")
        try:
            proposals = json.loads(summary)
            pending = [p for p in proposals if p.get("review", {}).get("state") == "pending"]
            accepted = [p for p in proposals if p.get("review", {}).get("state") == "accepted"]
            integrated = [p for p in proposals if p.get("review", {}).get("state") == "integrated"]
        except (json.JSONDecodeError, TypeError):
            pending, accepted, integrated = [], [], []
            summary = proposals_result.get("stdout", "")

        print("\n" + "=" * 60)
        print("FINALIZE REQUIRES APPROVAL")
        print("=" * 60)
        print(f"Feature:    {feature}")
        print(f"Message:    {message}")
        print(f"Pending:    {len(pending)}")
        print(f"Accepted:   {len(accepted)}")
        print(f"Integrated: {len(integrated)}")
        print("=" * 60)

        answer = input("Proceed with finalize? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            return json.dumps({
                "status": "aborted",
                "reason": "User rejected finalize",
                "feature": feature,
            })

    result = _run_gitagent(["finalize", "--feature", feature, "--message", message])
    if result["returncode"] != 0:
        return json.dumps({"error": result["stderr"], "status": "failed"})
    return json.dumps({"result": result["stdout"], "status": "finalized", "feature": feature})
