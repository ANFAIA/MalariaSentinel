"""Research + improvement cycle — search, analyze, propose improvements."""
from __future__ import annotations

import json


RESEARCH_PROMPT = """\
Run a research and improvement cycle for topic: {topic}

1. Recall what the knowledge graph already knows about this topic
2. Search the literature using opencode_search for recent findings
3. Analyze how findings relate to the current ABM implementation
4. Identify 2-3 actionable improvements based on the research
5. Spawn workers to implement the most promising improvements
6. Run calibration to measure impact
7. Accept improvements that measurably improve the composite score
8. Record findings and decisions in the knowledge graph
"""


def run_research_cycle(topic: str, cycles: int = 1, dry_run: bool = False) -> str:
    """Run a research + improvement cycle.

    Args:
        topic: Research topic to investigate.
        cycles: Number of research cycles to run.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = RESEARCH_PROMPT.format(topic=topic)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "topic": topic,
            "cycles": cycles,
        })

    from agents.deepagents.agent import create_orchestrator

    agent = create_orchestrator()

    all_results = []
    for i in range(cycles):
        result = agent.invoke({
            "messages": [{"role": "user", "content": prompt}]
        })
        all_results.append(result["messages"][-1].content)

    return "\n\n---\n\n".join(all_results)
