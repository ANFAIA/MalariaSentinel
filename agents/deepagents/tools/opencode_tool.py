"""OpenCode CLI wrapper for web search via Exa."""
import subprocess
import json


def opencode_search(query: str, num_results: int = 5) -> str:
    """Search the web using OpenCode's Exa integration.

    Args:
        query: The search query.
        num_results: Maximum number of results to return.

    Returns:
        Structured search results as a string.
    """
    try:
        result = subprocess.run(
            [
                "opencode", "run", "--auto",
                "--agent", "research-runner",
                "--model", "openrouter:xiaomi/mimo-v2.5",
                f"Search for: {query}. Return up to {num_results} structured findings with sources.",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"Search failed (exit {result.returncode}): {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Search timed out after 300 seconds."
    except FileNotFoundError:
        return "OpenCode CLI not found. Ensure 'opencode' is on PATH."
