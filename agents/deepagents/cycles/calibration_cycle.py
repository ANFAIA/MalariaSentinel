"""ABM improvement cycle — understand, plan, spawn, review, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run an ABM improvement cycle (max {max_iterations} iterations).

PHASE 1 — UNDERSTAND THE PROBLEM:
Before doing anything, gather context. The goal determines what you need to read.

1. memory_recall_kg(query="{goal}", k=5) — check knowledge base for related patterns, pitfalls, architecture
2. opencode_search(query="{goal} malaria ABM anopheles") — search web for scientific context
3. Read relevant files in the repo. Use grep/glob to find them. Examples:
   - If goal is about mortality → grep for MORT_BASAL, ADULT_SIGMA in mal-core/src/mal_core/abm/
   - If goal is about dispersal → grep for DISPERSE_PROB, MRR in the same directory
   - If goal is about a new feature → read the relevant .hpp/.cpp files
   - If goal mentions a specific behavior → find where that behavior is implemented
4. Read papers/ directory if the goal relates to biological mechanisms
5. pipeline_run_calibration(seed=1, days=30, n_rollouts=1) — establish baseline (skip if goal is not about calibration)

You now have context: what the code does, what the science says, what the baseline is.

PHASE 2 — PLAN & DELEGATE:
6. Formulate a specific hypothesis: "To fix <goal>, I need to change <X> because <Y>"
7. gitagent_init()
8. gitagent_start(feature="<descriptive-name>")  — pick a unique name
9. gitagent_spawn(feature="<descriptive-name>", agent_id="worker-1", role="abm")
10. task(subagent_type="abm-worker", description="<YOUR DETAILED TASK>")

The task description should include:
- What you found in your research (papers, web, knowledge base)
- What files need to change and why
- What the expected behavior should be
- How to verify the change (tests, simulation, scoring)
- The feature name for gitagent propose

PHASE 3 — REVIEW:
11. gitagent_proposals(feature="<descriptive-name>") — if none: STOP
12. gitagent_diff(proposal_id, feature="<descriptive-name>") — review changes carefully
13. Accept if the change makes sense scientifically and technically
14. If revision needed: gitagent_revise(feature="<descriptive-name>", feedback="specific feedback") → back to step 10

PHASE 5 — VERIFY & FINALIZE:
15. Verify the change: run tests, check simulation, compare scores
16. If improved: gitagent_integrate(feature="<descriptive-name>") → gitagent_finalize(feature="<descriptive-name>", message="<description>")
17. If not improved: record what failed, try new approach

RULES:
- You are NOT limited to parameter changes. You can modify ANY C++ code.
- You can add new behaviors, remove broken ones, restructure code.
- Always verify scientifically: does the change match real biology?
- Always verify technically: do tests pass? Does the simulation make sense?
-Iterations unlimited — keep going until the goal is achieved."""


def run_calibration_cycle(
    goal: str,
    max_iterations: int = 10,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "calibration-session",
    dry_run: bool = False,
) -> str:
    """Run the ABM calibration improvement cycle.

    Args:
        goal: The objective for this calibration run.
        max_iterations: Maximum number of improvement iterations.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = CALIBRATION_PROMPT.format(goal=goal, max_iterations=max_iterations)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "max_iterations": max_iterations,
        })

    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"calibration cycle, goal={goal}, max_iterations={max_iterations}")

    try:
        agent = agent_mod.create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        # Use stream to capture full conversation including LLM reasoning
        full_messages = []
        for event in agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode="messages",
        ):
            # event is a tuple: (message, metadata)
            if isinstance(event, tuple) and len(event) == 2:
                msg, metadata = event
                # Log AI messages (reasoning) and tool messages (results)
                if hasattr(msg, "content") and msg.content:
                    msg_type = type(msg).__name__
                    full_messages.append({
                        "type": msg_type,
                        "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                    })

        # Log the full conversation to session.jsonl
        logger.log_conversation(full_messages)

        # Get the final response
        final_content = full_messages[-1]["content"] if full_messages else "No response"
        logger.log_summary(final_content)
        return final_content
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None
