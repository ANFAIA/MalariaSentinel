"""Self-improvement tool for patching worker prompts based on failures."""
import json
import subprocess
from datetime import date
from pathlib import Path

PROMPTS_DIR = Path("agents/deepagents/prompts/templates")


def improve_prompt(
    agent_type: str,
    failure_analysis: str,
    proposed_patch: str,
    confidence: float = 0.7,
) -> str:
    """Patch a worker agent's prompt based on failure analysis.

    This is the self-improvement mechanism: when a worker fails,
    the orchestrator analyzes WHY and patches the prompt to prevent
    the same failure in future iterations.

    Args:
        agent_type: One of "abm_worker", "scorer_worker", "feature_worker".
        failure_analysis: Description of what went wrong and why.
        proposed_patch: The instruction to add to the prompt.
        confidence: Confidence in this patch (0.0 to 1.0).

    Returns:
        JSON with patch status and details.
    """
    if agent_type not in ("abm_worker", "scorer_worker", "feature_worker"):
        return json.dumps({
            "error": f"Unknown agent_type: {agent_type}. Must be abm_worker, scorer_worker, or feature_worker.",
            "status": "failed",
        })

    prompt_file = PROMPTS_DIR / f"{agent_type}.md"

    # Read current prompt
    if prompt_file.exists():
        current = prompt_file.read_text()
    else:
        current = f"# {agent_type.replace('_', ' ').title()} Prompt\n\nAuto-generated prompt template.\n"

    # Append the improvement patch
    patch_entry = (
        f"\n\n## Self-Improvement Patch ({date.today().isoformat()})\n\n"
        f"**Failure**: {failure_analysis}\n\n"
        f"**Patch**: {proposed_patch}\n\n"
        f"**Confidence**: {confidence}\n"
    )
    updated = current + patch_entry

    # Write updated prompt
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(updated)

    # Record in knowledge graph (best-effort, don't fail if KG is down)
    kg_status = _record_improvement(agent_type, failure_analysis, proposed_patch, confidence)

    return json.dumps({
        "status": "patched",
        "agent_type": agent_type,
        "file": str(prompt_file),
        "patch_length": len(patch_entry),
        "kg_recorded": kg_status,
    })


def _record_improvement(
    agent_type: str,
    failure: str,
    patch: str,
    confidence: float,
) -> bool:
    """Record the improvement in the knowledge graph. Returns True on success."""
    summary = (
        f"Self-improvement patch for {agent_type}. "
        f"Failure: {failure}. "
        f"Patch: {patch}. "
        f"Confidence: {confidence}"
    )
    try:
        result = subprocess.run(
            [
                "bash", "agents/memory/scripts/memory.sh", "node",
                "--type", "Pattern",
                "--name", f"Self-improvement: {agent_type} ({date.today()})",
                "--summary", summary,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
