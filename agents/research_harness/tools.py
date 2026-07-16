"""File operation tools for the research harness.

These are custom tools for reading/writing to the papers/ directory.
NO web search tools — OpenCode has Exa via websearch.
"""

from pathlib import Path

from .config import PAPERS_DIR


def read_papers_directory() -> str:
    """List all files in the papers/ directory recursively."""
    if not PAPERS_DIR.exists():
        return "papers/ directory does not exist."

    files = []
    for path in sorted(PAPERS_DIR.rglob("*")):
        if path.is_file():
            rel = path.relative_to(PAPERS_DIR)
            files.append(str(rel))

    if not files:
        return "papers/ directory is empty."

    return "\n".join(files)


def read_paper(file_path: str) -> str:
    """Read a specific paper from the papers/ directory.

    Args:
        file_path: Relative path within papers/ (e.g. 'spatial-analysis/paper.md')
    """
    paper = PAPERS_DIR / file_path
    if not paper.exists():
        return f"File not found: {file_path}"
    if not paper.is_file():
        return f"Not a file: {file_path}"

    return paper.read_text(encoding="utf-8")


def write_paper(file_path: str, content: str) -> str:
    """Write content to a file in the papers/ directory.

    Only writes within papers/ — rejects paths that escape that directory.

    Args:
        file_path: Relative path within papers/ (e.g. 'spatial-analysis/paper.md')
        content: File content to write
    """
    target = (PAPERS_DIR / file_path).resolve()
    if not str(target).startswith(str(PAPERS_DIR.resolve())):
        return f"Rejected: path escapes papers/ directory: {file_path}"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written: {file_path} ({len(content)} chars)"


def check_knowledge_gaps() -> str:
    """Analyse existing papers and identify knowledge gaps."""
    if not PAPERS_DIR.exists():
        return "No papers/ directory — all topics are gaps."

    topics = set()
    for path in PAPERS_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        for keyword in ["malaria", "anopheles", "abm", "geospatial", "sdss",
                        "transmission", "mosquito", "elimination", "surveillance"]:
            if keyword in text:
                topics.add(keyword)

    core_keywords = {"malaria", "anopheles", "abm", "geospatial", "sdss",
                     "transmission", "elimination"}
    gaps = core_keywords - topics

    if not gaps:
        return "All core topics covered. No obvious gaps."

    return f"Knowledge gaps identified: {', '.join(sorted(gaps))}"


def generate_hypothesis(topic: str) -> str:
    """Generate a structured hypothesis prompt for a given topic."""
    return (
        f"Research Hypothesis: {topic}\n\n"
        f"Generate 3-5 testable hypotheses related to: {topic}\n\n"
        "For each hypothesis provide:\n"
        "1. A clear statement\n"
        "2. Supporting evidence or rationale\n"
        "3. How it could be tested with the MalariaSentinel framework\n"
        "4. Expected impact on malaria elimination\n"
    )
