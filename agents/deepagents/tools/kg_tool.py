"""Knowledge graph recall tool using project memory scripts."""
import subprocess
import json
from pathlib import Path


def memory_recall_kg(query: str, k: int = 5) -> str:
    """Recall patterns, pitfalls, and best practices from the knowledge graph.

    Uses the project's Neo4j memory system via the memory_recall script.

    Args:
        query: Natural language query to search the knowledge graph.
        k: Maximum number of results to return.

    Returns:
        JSON string with recalled nodes and their details.
    """
    # Try using the memory_recall custom tool script if it exists
    recall_script = Path("agents/memory/scripts/recall.sh")

    if recall_script.exists():
        try:
            result = subprocess.run(
                ["bash", str(recall_script), query, str(k)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return json.dumps({
                    "status": "ok",
                    "query": query,
                    "results": result.stdout.strip(),
                })
            return json.dumps({
                "status": "script_error",
                "error": result.stderr.strip(),
                "query": query,
            })
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "timeout", "query": query})

    # Fallback: try the memory_query Cypher approach via the CLI
    return json.dumps({
        "status": "no_backend",
        "query": query,
        "message": "No recall backend available. Ensure agents/memory/ is configured and Neo4j is running.",
    })
